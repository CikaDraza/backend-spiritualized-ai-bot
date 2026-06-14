"""Single-call structured tutor orchestrator.

Per learner turn, one LLM call (JSON mode, Pydantic-validated) returns the whole structured turn:
a concise in-character reply, a correction of the learner's message, Serbian translations, short
hints, and mistakes bucketed by the four linguistic pillars (each with a severity). The turn is
appended to the session transcript (JSONB) and mistakes are written to the `mistakes` table for
progress tracking. There is no per-turn score — scoring belongs to the end-of-session summary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .agents import Persona, get_persona
from .ai import get_client, to_openai_message
from .config import settings
from .crud import (
    append_transcript_messages,
    create_mistakes,
    get_or_create_transcript,
    get_space,
)
from .models import User
from .schemas import ChatMessage, TutorTurnResponse, TutorTurnResult

logger = logging.getLogger("spiritualized.orchestrator")

MODEL = "gpt-4o-mini"

_TURN_SHAPE = """Reply with STRICT JSON only, of EXACTLY this shape:
{
  "ai_response": "<concise, in-character reply that continues the conversation and asks a follow-up question; DO NOT put grammar corrections here>",
  "correction": "<the learner's last message rewritten in correct, natural English; empty string if it was already correct>",
  "translation": {"ai_response": "<Serbian translation of ai_response>", "correction": "<Serbian translation of correction; empty string if there is no correction>"},
  "hints": ["<1 to 3 short, actionable tips in English>"],
  "mistakes": [{"category": "<semantics|syntax|orthography|living_communication>", "original": "<the learner's exact problematic fragment>", "correction": "<the fix>", "explanation": "<short why, in Serbian>", "severity": "<minor|moderate|major>"}]
}
If the learner's message is flawless: correction = "" and mistakes = []. Output JSON only, no extra text."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _system_prompt(persona: Persona, scenario: str, level: str) -> str:
    return (
        f"You are {persona.name}, a warm, encouraging bilingual English tutor for a Serbian "
        f"speaker. Persona tone: {persona.tone}. You are role-playing a '{scenario}' conversation "
        f"at CEFR level {level}; keep ai_response natural, in character, and around that level.\n\n"
        + _TURN_SHAPE
    )


def _turn_messages(
    persona: Persona, scenario: str, level: str, history: list[ChatMessage], message: str
) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionSystemMessageParam(
            role="system", content=_system_prompt(persona, scenario, level)
        )
    ]
    for item in history:
        messages.append(to_openai_message(item.role, item.content))
    messages.append(ChatCompletionUserMessageParam(role="user", content=message))
    return messages


async def _structured_turn(
    persona: Persona, scenario: str, level: str, history: list[ChatMessage], message: str
) -> TutorTurnResult:
    if not settings.OPENAI_API_KEY:
        return TutorTurnResult(
            ai_response=(
                f"[{persona.name}] (dev mode — no OpenAI key) Got it! Tell me more in English."
            ),
        )
    try:
        response = await get_client().chat.completions.create(
            model=MODEL,
            messages=_turn_messages(persona, scenario, level, history, message),
            temperature=0.6,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        result = TutorTurnResult.model_validate_json(raw)
        if not result.ai_response.strip():
            result.ai_response = "Could you tell me a little more?"
        return result
    except Exception as exc:  # never fail the turn because the model hiccupped
        logger.warning("Structured tutor turn failed, returning minimal reply: %s", exc)
        return TutorTurnResult(ai_response="Let's keep going — tell me more.")


async def run_turn(
    db: AsyncSession,
    user: User,
    message: str,
    history: list[ChatMessage],
    session_id: str,
    persona_slug: str | None,
    scenario_id: int | None,
) -> TutorTurnResponse:
    persona = get_persona(persona_slug)
    space = await get_space(db, scenario_id) if scenario_id is not None else None
    scenario = (
        space.scenario_type.value.replace("_", " ") if space else "general English conversation"
    )
    level = space.level.value if space else "B1"

    result = await _structured_turn(persona, scenario, level, history, message)

    transcript = await get_or_create_transcript(db, user.id, session_id, scenario_id)
    new_messages: list[dict[str, object]] = [
        {"role": "user", "content": message, "ts": _now()},
        {
            "role": "assistant",
            "content": result.ai_response,
            "persona": persona.slug,
            "ts": _now(),
        },
    ]
    await append_transcript_messages(db, transcript, new_messages)
    if result.mistakes:
        await create_mistakes(db, user.id, transcript.id, session_id, result.mistakes)

    return TutorTurnResponse(
        ai_response=result.ai_response,
        correction=result.correction,
        translation=result.translation,
        hints=result.hints,
        mistakes=result.mistakes,
        persona=persona.slug,
        session_id=session_id,
    )
