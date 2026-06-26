"""Deterministic session metrics (CEFR engine Layer A — no LLM).

Computed from the learner's messages + the mistakes persisted during one conversation session.
Cheap, reproducible signal that feeds the session summary, the space/global profiles, and (PR11.4)
the LLM CEFR assessment. No OpenAI call here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import LinguisticCategory, Mistake, MistakeSeverity

PILLARS: list[str] = [c.value for c in LinguisticCategory]

# Severity-weighted penalty subtracted from a pillar's 100 baseline (mirrors the old client mock).
_PENALTY: dict[MistakeSeverity, int] = {
    MistakeSeverity.minor: 3,
    MistakeSeverity.moderate: 7,
    MistakeSeverity.major: 12,
}
_PILLAR_FLOOR = 40  # a single rough session shouldn't tank a pillar below this

_WORD_RE = re.compile(r"[A-Za-z']+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class SessionMetrics:
    message_count: int
    mistakes_total: int
    error_frequency: float  # mistakes per learner message
    avg_sentence_length: float  # words per learner message
    vocabulary_diversity: float  # type-token ratio (0..1)
    pillar_scores: dict[str, int]  # 0..100 per pillar
    pillar_counts: dict[str, int]  # mistake count per pillar
    subtype_counts: dict[str, int]  # mistake count per subtype
    repeated_subtypes: list[str]  # subtypes seen more than once
    most_common_subtype: str | None


def compute_session_metrics(
    user_messages: list[str], mistakes: list[Mistake]
) -> SessionMetrics:
    message_count = len(user_messages)

    all_words: list[str] = []
    for msg in user_messages:
        all_words.extend(_words(msg))
    total_words = len(all_words)
    unique_words = len(set(all_words))

    avg_sentence_length = round(total_words / message_count, 1) if message_count else 0.0
    vocabulary_diversity = round(unique_words / total_words, 2) if total_words else 0.0

    pillar_scores: dict[str, int] = {p: 100 for p in PILLARS}
    pillar_counts: dict[str, int] = {p: 0 for p in PILLARS}
    subtype_counts: dict[str, int] = {}

    for m in mistakes:
        pillar = m.category.value
        severity = m.severity or MistakeSeverity.moderate
        pillar_scores[pillar] = max(_PILLAR_FLOOR, pillar_scores[pillar] - _PENALTY[severity])
        pillar_counts[pillar] = pillar_counts.get(pillar, 0) + 1
        if m.subtype is not None:
            subtype_counts[m.subtype.value] = subtype_counts.get(m.subtype.value, 0) + 1

    repeated_subtypes = sorted(s for s, n in subtype_counts.items() if n > 1)
    most_common_subtype = (
        max(subtype_counts, key=lambda s: subtype_counts[s]) if subtype_counts else None
    )
    mistakes_total = len(mistakes)
    error_frequency = round(mistakes_total / message_count, 2) if message_count else 0.0

    return SessionMetrics(
        message_count=message_count,
        mistakes_total=mistakes_total,
        error_frequency=error_frequency,
        avg_sentence_length=avg_sentence_length,
        vocabulary_diversity=vocabulary_diversity,
        pillar_scores=pillar_scores,
        pillar_counts=pillar_counts,
        subtype_counts=subtype_counts,
        repeated_subtypes=repeated_subtypes,
        most_common_subtype=most_common_subtype,
    )
