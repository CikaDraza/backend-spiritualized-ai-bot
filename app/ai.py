from typing import List
from uuid import uuid4

import openai

from .config import settings
from .mongo import log_chat_message
from .schemas import ChatMessage, ChatRequest


openai.api_key = settings.OPENAI_API_KEY


DEFAULT_SYSTEM_PROMPT = """You are Spiritualized, a warm and mindful bilingual English mentor.
You guide the learner through English using gentle corrections in Serbian when needed, while keeping the main conversation in English.
You focus on:
- advanced semantics and subtle meaning differences
- complex English grammar structures that do not exist in Serbian
- idioms, phrasal verbs, and natural spoken style
- empathic explanations and mnemonic support for orthography and spelling

When a student makes a mistake, explain why in Serbian and propose a better phrasing in English.
Always keep tone encouraging, slightly poetic, and deeply human.
"""


def build_openai_messages(history: List[ChatMessage], message: str) -> List[dict]:
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
    ]
    for item in history:
        messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": message})
    return messages


async def generate_spiritual_response(
    request: ChatRequest,
    user_id: int | None = None,
    session_id: str | None = None,
) -> str:
    session_id = session_id or str(uuid4())
    await log_chat_message(user_id, session_id, "user", request.message)

    if not settings.OPENAI_API_KEY:
        assistant_result = fallback_response(request.message)
    else:
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=build_openai_messages(request.history, request.message),
                temperature=0.8,
                max_tokens=700,
            )
            assistant_result = response.choices[0].message.content.strip()
        except Exception as exc:
            assistant_result = f"Spiritualized nije mogao da generiše odgovor zbog greške: {exc}"

    await log_chat_message(user_id, session_id, "assistant", assistant_result)
    return assistant_result


def fallback_response(user_message: str) -> str:
    return (
        "Dobrodošao! Ako nema OpenAI ključa, mogu ti pomoći sa osnovnom povratnom informacijom. "
        "Pokušaj da napišeš rečenicu na engleskom, a ja ću ti objasniti stil i značenje.\n\n"
        f"Tvoj unos: {user_message}"
    )
