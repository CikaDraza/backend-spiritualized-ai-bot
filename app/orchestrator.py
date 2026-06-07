"""Minimal multi-agent orchestrator.

Per learner turn the coordinator runs two agents over the same input:
  1. a *conversation* agent that replies in the chosen persona's tone, and
  2. an *error-analyst* agent that returns structured JSON of mistakes bucketed by the four
     linguistic pillars (Pydantic-validated).

The persona only colors the conversation tone; the analyst always covers all four pillars.
Results are persisted: the turn is appended to the session transcript (JSONB) and any mistakes
are written to the `mistakes` table for progress tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from .agents import Persona, get_persona
from .ai import DEFAULT_SYSTEM_PROMPT, get_client
from .config import settings
from .crud import append_transcript_messages, create_mistakes, get_or_create_transcript
from .models import User
from .schemas import ChatMessage, ErrorAnalysis, TutorTurnResponse

logger = logging.getLogger("spiritualized.orchestrator")

MODEL = "gpt-4o-mini"

ANALYST_PROMPT = """You are an English error-analysis engine for a Serbian learner.
Analyze ONLY the learner's latest message. Return STRICT JSON of this exact shape:
{"mistakes": [{"category": "<one of: semantics | syntax | orthography | living_communication>",
"original": "<the learner's exact problematic fragment>",
"correction": "<the corrected English>",
"explanation": "<short explanation in Serbian of why it was wrong>"}]}
If the message is flawless, return {"mistakes": []}. Do not add commentary outside the JSON."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conversation_messages(persona: Persona, history: List[ChatMessage], message: str) -> list[dict]:
    system = (
        f"{DEFAULT_SYSTEM_PROMPT}\n\n"
        f"You are speaking as the persona '{persona.name}'. Tone: {persona.tone}. "
        f"Stay in this tone while keeping the mentoring substance identical."
    )
    messages: list[dict] = [{"role": "system", "content": system}]
    for item in history:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": message})
    return messages


async def _conversation(persona: Persona, history: List[ChatMessage], message: str) -> str:
    if not settings.OPENAI_API_KEY:
        return (
            f"[{persona.name}] (dev mode — bez OpenAI ključa) "
            "Napiši rečenicu na engleskom i analiziraću je."
        )
    response = await get_client().chat.completions.create(
        model=MODEL,
        messages=_conversation_messages(persona, history, message),
        temperature=0.8,
        max_tokens=700,
    )
    return (response.choices[0].message.content or "").strip()


async def _analyze(message: str) -> ErrorAnalysis:
    if not settings.OPENAI_API_KEY:
        return ErrorAnalysis()
    try:
        response = await get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ANALYST_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return ErrorAnalysis.model_validate_json(raw)
    except Exception as exc:  # never fail the turn because analysis hiccupped
        logger.warning("Error analysis failed, returning empty analysis: %s", exc)
        return ErrorAnalysis()


async def run_turn(
    db: AsyncSession,
    user: User,
    message: str,
    history: List[ChatMessage],
    session_id: str,
    persona_slug: str | None,
    scenario_id: int | None,
) -> TutorTurnResponse:
    persona = get_persona(persona_slug)
    assistant_text = await _conversation(persona, history, message)
    analysis = await _analyze(message)

    transcript = await get_or_create_transcript(db, user.id, session_id, scenario_id)
    await append_transcript_messages(
        db,
        transcript,
        [
            {"role": "user", "content": message, "ts": _now()},
            {"role": "assistant", "content": assistant_text, "persona": persona.slug, "ts": _now()},
        ],
    )
    if analysis.mistakes:
        await create_mistakes(db, user.id, transcript.id, session_id, analysis.mistakes)

    return TutorTurnResponse(
        assistant=assistant_text,
        persona=persona.slug,
        session_id=session_id,
        mistakes=analysis.mistakes,
    )
