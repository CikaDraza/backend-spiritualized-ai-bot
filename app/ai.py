from __future__ import annotations

from uuid import uuid4

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .config import settings
from .schemas import ChatMessage, ChatRequest


def to_openai_message(role: str, content: str) -> ChatCompletionMessageParam:
    """Map a (role, content) pair to the correct typed OpenAI message param."""
    if role == "assistant":
        return ChatCompletionAssistantMessageParam(role="assistant", content=content)
    if role == "system":
        return ChatCompletionSystemMessageParam(role="system", content=content)
    return ChatCompletionUserMessageParam(role="user", content=content)


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


_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Lazily create the AsyncOpenAI client so importing this module never requires a key."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def build_openai_messages(
    history: list[ChatMessage], message: str
) -> list[ChatCompletionMessageParam]:
    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionSystemMessageParam(role="system", content=DEFAULT_SYSTEM_PROMPT)
    ]
    for item in history:
        messages.append(to_openai_message(item.role, item.content))
    messages.append(ChatCompletionUserMessageParam(role="user", content=message))
    return messages


async def generate_spiritual_response(
    request: ChatRequest,
    user_id: int | None = None,
    session_id: str | None = None,
) -> str:
    # session_id is accepted for forward-compatibility with transcript persistence (PR7).
    session_id = session_id or str(uuid4())

    if not settings.OPENAI_API_KEY:
        return fallback_response(request.message)

    try:
        client = get_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=build_openai_messages(request.history, request.message),
            temperature=0.8,
            max_tokens=700,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        return f"Spiritualized nije mogao da generiše odgovor zbog greške: {exc}"


def fallback_response(user_message: str) -> str:
    return (
        "Dobrodošao! Ako nema OpenAI ključa, mogu ti pomoći sa osnovnom povratnom informacijom. "
        "Pokušaj da napišeš rečenicu na engleskom, a ja ću ti objasniti stil i značenje.\n\n"
        f"Tvoj unos: {user_message}"
    )
