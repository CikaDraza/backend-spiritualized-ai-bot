"""Adaptive prompt builder (PR11.5).

Assembles the tutor's system prompt from all three memory layers:
- the persona/scenario/level base,
- the Global Learning Profile (Layer 3): estimated CEFR, recurring weak areas, mastered items,
- the Learning Space Profile (Layer 2): domain weak areas + strong vocabulary,
- the Current Session (Layer 1): subtypes already corrected this session (reinforce, don't nag).

Cold start (no profiles, no session history) degrades gracefully to the original behavior. The JSON
response contract (`_TURN_SHAPE`) is owned here and unchanged.
"""

from __future__ import annotations

from .agents import Persona
from .models import LearningProfile, LearningSpaceProfile

_TURN_SHAPE = """Reply with STRICT JSON only, of EXACTLY this shape:
{
  "ai_response": "<concise, in-character reply that continues the conversation and asks a follow-up question; DO NOT put grammar corrections here>",
  "correction": "<the learner's last message rewritten in correct, natural English; empty string if it was already correct>",
  "translation": {"ai_response": "<Serbian translation of ai_response>", "correction": "<Serbian translation of correction; empty string if there is no correction>"},
  "hints": ["<1 to 3 short, actionable tips in English>"],
  "mistakes": [{"subtype": "<articles|prepositions|verb_tenses|word_order|vocabulary|clarity|spelling|idioms|naturalness|other>", "original": "<the learner's exact problematic fragment>", "correction": "<the fix>", "explanation": "<short why, in Serbian>", "severity": "<minor|moderate|major>"}]
}
Pick the single best `subtype` for each mistake from the list above. If the learner's message is
flawless: correction = "" and mistakes = []. Output JSON only, no extra text."""


def _label(key: str) -> str:
    return key.replace("_", " ")


def _focus(
    global_profile: LearningProfile | None, space_profile: LearningSpaceProfile | None
) -> str:
    candidates: list[str] = []
    if global_profile is not None:
        candidates.extend(str(w) for w in (global_profile.weaknesses or []))
    if space_profile is not None:
        candidates.extend(str(w) for w in (space_profile.weak_areas or []))
    return _label(candidates[0]) if candidates else ""


def _profile_section(
    space_profile: LearningSpaceProfile | None,
    global_profile: LearningProfile | None,
    session_subtypes: list[str],
) -> str:
    lines: list[str] = []

    if global_profile is not None:
        if global_profile.committed_cefr:
            goal = (
                f" (working toward {global_profile.target_cefr})"
                if global_profile.target_cefr
                else ""
            )
            lines.append(f"- Estimated overall level: {global_profile.committed_cefr}{goal}")
        weaknesses = [str(w) for w in (global_profile.weaknesses or [])][:3]
        if weaknesses:
            lines.append(
                "- Recurring weak areas across all topics: "
                + ", ".join(_label(w) for w in weaknesses)
            )
        mastered = [str(m) for m in (global_profile.mastered or [])][:3]
        if mastered:
            lines.append(
                "- Already mastered (don't over-correct these): "
                + ", ".join(_label(m) for m in mastered)
            )

    if space_profile is not None:
        space_weak = [str(w) for w in (space_profile.weak_areas or [])][:3]
        if space_weak:
            lines.append(
                "- Weak areas in this topic: " + ", ".join(_label(w) for w in space_weak)
            )
        vocab = [str(v) for v in (space_profile.domain_vocabulary or [])][:6]
        if vocab:
            lines.append("- Strong domain vocabulary here: " + ", ".join(vocab))

    if session_subtypes:
        lines.append(
            "- Already corrected this session (reinforce gently, don't nag): "
            + ", ".join(_label(s) for s in session_subtypes[:5])
        )

    if not lines:
        return ""

    focus = _focus(global_profile, space_profile)
    if focus:
        lines.append(f"- Recommended focus this turn: {focus}")

    return (
        "\nLearner profile (adapt your teaching to this — keep it natural, never list it back):\n"
        + "\n".join(lines)
        + "\n"
    )


def build_system_prompt(
    persona: Persona,
    scenario: str,
    level: str,
    space_profile: LearningSpaceProfile | None,
    global_profile: LearningProfile | None,
    session_subtypes: list[str],
) -> str:
    base = (
        f"You are {persona.name}, a warm, encouraging bilingual English tutor for a Serbian "
        f"speaker. Persona tone: {persona.tone}. You are role-playing a '{scenario}' conversation "
        f"at CEFR level {level}; keep ai_response natural, in character, and around that level.\n"
        "Teaching order: conversation first, a small correction second, a short explanation third. "
        "Keep the dialogue flowing — never turn into a grammar textbook.\n"
    )
    return base + _profile_section(space_profile, global_profile, session_subtypes) + "\n" + _TURN_SHAPE
