"""Hybrid CEFR engine (PR11.4).

Layer A — deterministic baseline from session metrics (no LLM).
Layer B — one LLM assessment at session end: a compact metrics summary + a few example sentences
          (NOT the whole chat) → {estimated_cefr, confidence, reasoning, next_goal}. Skipped when no
          OpenAI key (dev-fallback uses the baseline) so the loop costs zero tokens locally.
Layer C — smoothing (`decide_cefr`): `committed` only moves after N consecutive confirming sessions;
          `emerging` tracks the latest estimate. Prevents the shown level from jumping every session.
"""

from __future__ import annotations

import json
import logging

from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .ai import get_client
from .config import settings
from .schemas import CefrAssessment
from .session_metrics import SessionMetrics

logger = logging.getLogger("spiritualized.cefr")

MODEL = "gpt-4o-mini"
LEVELS = ["A1", "A2", "B1", "B2", "C1"]
_PROMOTE_AFTER = 2  # consecutive confirming sessions before `committed` moves


def _avg_pillar_score(metrics: SessionMetrics) -> float:
    scores = list(metrics.pillar_scores.values())
    return sum(scores) / len(scores) if scores else 100.0


def _deterministic_cefr(metrics: SessionMetrics, space_level: str) -> CefrAssessment:
    base = LEVELS.index(space_level) if space_level in LEVELS else LEVELS.index("B1")
    avg = _avg_pillar_score(metrics)

    if metrics.message_count < 3:
        idx, confidence = base, 0.3  # too little data → assume the space's target level
    elif avg >= 90 and metrics.error_frequency < 0.5:
        idx, confidence = base, min(0.8, 0.4 + metrics.message_count * 0.04)
    elif avg < 70 or metrics.error_frequency > 1.5:
        idx, confidence = max(0, base - 1), min(0.75, 0.35 + metrics.message_count * 0.04)
    else:
        idx, confidence = base, min(0.7, 0.35 + metrics.message_count * 0.04)

    return CefrAssessment(
        estimated_cefr=LEVELS[idx],
        confidence=round(confidence, 2),
        reasoning="deterministic baseline (no LLM)",
        next_goal=LEVELS[min(len(LEVELS) - 1, idx + 1)],
    )


def _metrics_payload(metrics: SessionMetrics, examples: list[str]) -> str:
    return json.dumps(
        {
            "grammar_accuracy": round(_avg_pillar_score(metrics)),
            "vocabulary_diversity": metrics.vocabulary_diversity,
            "average_sentence_length": metrics.avg_sentence_length,
            "messages": metrics.message_count,
            "error_frequency": metrics.error_frequency,
            "common_errors": list(metrics.subtype_counts.keys())[:5],
            "examples": examples[:3],
        },
        ensure_ascii=False,
    )


async def assess_cefr(
    metrics: SessionMetrics, space_level: str, examples: list[str]
) -> CefrAssessment:
    """Estimate the learner's CEFR for one finished session. LLM-refined when a key is present,
    otherwise the deterministic baseline."""
    baseline = _deterministic_cefr(metrics, space_level)
    if not settings.OPENAI_API_KEY:
        return baseline

    system = (
        "You are a CEFR assessor for English learners. Given summary metrics and a few example "
        "sentences from one short session, estimate the learner's current CEFR level. Reply with "
        'STRICT JSON only: {"estimated_cefr":"<A1|A2|B1|B2|C1>","confidence":<0..1>,'
        '"reasoning":"<one short sentence>","next_goal":"<A1|A2|B1|B2|C1>"}'
    )
    try:
        response = await get_client().chat.completions.create(
            model=MODEL,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system),
                ChatCompletionUserMessageParam(
                    role="user", content=_metrics_payload(metrics, examples)
                ),
            ],
            temperature=0.2,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = CefrAssessment.model_validate_json(raw)
    except Exception as exc:  # never fail session-complete because of the rater
        logger.warning("CEFR LLM assessment failed, using baseline: %s", exc)
        return baseline

    if parsed.estimated_cefr not in LEVELS:
        return baseline
    parsed.confidence = max(0.0, min(1.0, parsed.confidence))
    if parsed.next_goal not in LEVELS:
        parsed.next_goal = baseline.next_goal
    return parsed


def decide_cefr(
    committed: str | None, history: list[dict[str, object]]
) -> tuple[str | None, str | None]:
    """Layer C smoothing. `history` is newest-last and already includes the current assessment.
    Returns (new_committed, new_emerging)."""
    if not history:
        return committed, committed
    latest = str(history[-1].get("level") or "")
    if not latest:
        return committed, committed
    if committed is None:
        return latest, latest

    consecutive = 0
    for entry in reversed(history):
        if str(entry.get("level") or "") == latest:
            consecutive += 1
        else:
            break

    if latest != committed and consecutive >= _PROMOTE_AFTER:
        return latest, latest
    return committed, latest
