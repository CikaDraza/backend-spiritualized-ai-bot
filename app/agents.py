"""Persona registry for the orchestrator.

A persona is purely character/tone/voice — it is orthogonal to the four linguistic pillars.
Every persona analyzes all four pillars; only the *tone* of the conversation differs. Slugs match
the avatar assets in the frontend `public/agents/` folder so the UI can resolve the image.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    slug: str
    name: str
    avatar: str
    tone: str


PERSONAS: dict[str, Persona] = {
    "viktor": Persona(
        slug="viktor",
        name="Viktor",
        avatar="/agents/viktor.png",
        tone="calm, precise and philosophical; explains slowly and values exact wording",
    ),
    "maria-deep": Persona(
        slug="maria-deep",
        name="Maria Deep",
        avatar="/agents/maria-deep.png",
        tone="warm, reflective and deeply empathetic; connects language to feeling and meaning",
    ),
    "kiki": Persona(
        slug="kiki",
        name="Kiki",
        avatar="/agents/kiki.png",
        tone="playful, upbeat and encouraging; keeps the learner motivated with light humor",
    ),
    "claudia-makelele": Persona(
        slug="claudia-makelele",
        name="Claudia Makelele",
        avatar="/agents/claudia-makelele.png",
        tone="direct, motivational and no-nonsense; pushes for clarity and momentum",
    ),
}

DEFAULT_PERSONA_SLUG = "viktor"


def get_persona(slug: str | None) -> Persona:
    if slug and slug in PERSONAS:
        return PERSONAS[slug]
    return PERSONAS[DEFAULT_PERSONA_SLUG]


def list_personas() -> list[Persona]:
    return list(PERSONAS.values())
