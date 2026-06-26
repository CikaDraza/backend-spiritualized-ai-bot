"""Pattern detection over the learner's mistake history (PR12).

Turns the raw, per-session mistake counts into long-term signal:
- **mastered**: subtypes the learner used to get wrong but hasn't in the recent window (improved out),
- **recurring**: subtypes that keep appearing across recent sessions (the real priorities),
- **improving**: subtypes still present but trending down,
and a few human-readable **recommendations**. Pure (no DB / no LLM) → easy to test. The results are
cached on the global LearningProfile at session-complete and flow into the adaptive prompt + summary.
"""

from __future__ import annotations

from dataclasses import dataclass

_RECENT_WINDOW = 3  # how many of the most recent sessions count as "recent"
_MASTERY_MIN_OLD = 2  # must have erred at least this many times earlier to count as mastered
_RECURRING_MIN_SESSIONS = 2  # present in >= this many recent sessions to be "recurring"


@dataclass
class PatternReport:
    mastered: list[str]
    recurring: list[str]
    improving: list[str]
    recommendations: list[str]


def _label(subtype: str) -> str:
    return subtype.replace("_", " ")


def _present(sessions: list[dict[str, int]], subtype: str) -> int:
    return sum(1 for s in sessions if s.get(subtype, 0) > 0)


def _total(sessions: list[dict[str, int]], subtype: str) -> int:
    return sum(s.get(subtype, 0) for s in sessions)


def _recommendations(
    recurring: list[str], mastered: list[str], improving: list[str]
) -> list[str]:
    recs: list[str] = []
    if recurring:
        top = ", ".join(_label(s) for s in recurring[:2])
        recs.append(f"Keep targeting {top} — it keeps coming up across recent sessions.")
    if improving:
        recs.append(f"Your {_label(improving[0])} is improving — keep it up.")
    if mastered:
        recs.append(f"Great progress: you've stopped making {_label(mastered[0])} mistakes.")
    if not recs:
        recs.append("You're doing great — keep the conversations going.")
    return recs[:3]


def detect_patterns(history: list[dict[str, int]]) -> PatternReport:
    """`history` is per-session {subtype: count}, oldest first, newest last."""
    if not history:
        return PatternReport([], [], [], _recommendations([], [], []))

    recent = history[-_RECENT_WINDOW:]
    older = history[: -_RECENT_WINDOW] if len(history) > _RECENT_WINDOW else []

    subtypes: set[str] = set()
    for session in history:
        subtypes.update(session.keys())

    mastered: list[str] = []
    recurring: list[str] = []
    improving: list[str] = []

    for subtype in subtypes:
        recent_total = _total(recent, subtype)
        older_total = _total(older, subtype)

        if older and older_total >= _MASTERY_MIN_OLD and recent_total == 0:
            mastered.append(subtype)
        elif _present(recent, subtype) >= _RECURRING_MIN_SESSIONS:
            recurring.append(subtype)
        elif older and recent_total > 0:
            older_avg = older_total / len(older)
            recent_avg = recent_total / len(recent)
            if recent_avg < older_avg:
                improving.append(subtype)

    recurring.sort(key=lambda s: _total(recent, s), reverse=True)
    mastered.sort(key=lambda s: _total(older, s), reverse=True)
    improving.sort(key=lambda s: _total(recent, s), reverse=True)

    return PatternReport(
        mastered=mastered,
        recurring=recurring,
        improving=improving,
        recommendations=_recommendations(recurring, mastered, improving),
    )
