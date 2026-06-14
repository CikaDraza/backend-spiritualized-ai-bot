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


# Slugs match the LearningSpace persona enum (mila/viktor/nora/maria) so a space's chosen tutor
# resolves directly. Persona only colors tone; every persona still analyzes all four pillars.
PERSONAS: dict[str, Persona] = {
    "mila": Persona(
        slug="mila",
        name="Mila",
        avatar="/agents/mila.png",
        tone="warm, friendly and upbeat; encouraging and keeps the learner motivated with light humor",
    ),
    "viktor": Persona(
        slug="viktor",
        name="Viktor",
        avatar="/agents/viktor.png",
        tone="calm, precise and philosophical; explains slowly and values exact wording",
    ),
    "nora": Persona(
        slug="nora",
        name="Nora",
        avatar="/agents/nora.png",
        tone="clear, structured and patient; breaks ideas down step by step",
    ),
    "maria": Persona(
        slug="maria",
        name="Maria",
        avatar="/agents/maria.png",
        tone="warm, reflective and deeply empathetic; connects language to feeling and meaning",
    ),
}

DEFAULT_PERSONA_SLUG = "viktor"


def get_persona(slug: str | None) -> Persona:
    if slug and slug in PERSONAS:
        return PERSONAS[slug]
    return PERSONAS[DEFAULT_PERSONA_SLUG]


def list_personas() -> list[Persona]:
    return list(PERSONAS.values())
