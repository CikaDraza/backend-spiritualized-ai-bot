"""Learning profile engine.

Orchestrates end-of-session rollup: read the session transcript + mistakes, compute deterministic
metrics, fold them into the Layer-2 Learning Space Profile, and build the SessionSummary the UI
renders. (Layer-3 global profile + CEFR reassessment are added in PR11.4.)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .cefr_engine import assess_cefr, decide_cefr
from .crud import (
    get_or_create_transcript,
    get_profile,
    get_space_profile,
    mistake_history,
    mistake_stats,
    session_mistakes,
)
from .models import LearningProfile, LearningSpace, LearningSpaceProfile, User
from .pattern_engine import detect_patterns
from .schemas import CefrAssessment, PillarScores, SessionSummary
from .session_metrics import PILLARS, SessionMetrics, compute_session_metrics

# How much a fresh session moves the running space score (exponential moving average).
_EMA_ALPHA = 0.4

_LEVELS = ["A1", "A2", "B1", "B2", "C1"]
_PILLAR_LABELS = {
    "semantics": "Semantics",
    "syntax": "Syntax",
    "orthography": "Spelling",
    "living_communication": "Communication",
}


def _level_below(level: str) -> str:
    i = _LEVELS.index(level) if level in _LEVELS else 0
    return _LEVELS[max(0, i - 1)]


def _duration_min(messages: list[dict[str, object]]) -> int:
    stamps = [str(m["ts"]) for m in messages if m.get("ts")]
    if len(stamps) < 2:
        return 1
    try:
        first = datetime.fromisoformat(stamps[0])
        last = datetime.fromisoformat(stamps[-1])
    except ValueError:
        return 1
    return max(1, round((last - first).total_seconds() / 60))


def _top_keys(counts: dict[str, int], n: int) -> list[str]:
    return [k for k, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]]


async def _update_space_profile(
    db: AsyncSession,
    user_id: int,
    space_id: int,
    metrics: SessionMetrics,
    weak_subtypes: list[str],
) -> None:
    profile = await get_space_profile(db, user_id, space_id)
    session_scores = metrics.pillar_scores
    if profile is None:
        profile = LearningSpaceProfile(
            user_id=user_id,
            space_id=space_id,
            pillar_scores=dict(session_scores),
            weak_areas=weak_subtypes,
            sessions_completed=1,
        )
        db.add(profile)
    else:
        old = profile.pillar_scores or {}
        merged: dict[str, int] = {}
        for pillar in PILLARS:
            current = session_scores[pillar]
            prev = old.get(pillar)
            merged[pillar] = (
                round(_EMA_ALPHA * current + (1 - _EMA_ALPHA) * prev)
                if prev is not None
                else current
            )
        profile.pillar_scores = merged
        profile.weak_areas = weak_subtypes
        profile.sessions_completed = (profile.sessions_completed or 0) + 1
    await db.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _update_global_profile(
    db: AsyncSession,
    user_id: int,
    metrics: SessionMetrics,
    global_stats: dict[str, dict[str, int]],
    assessment: CefrAssessment,
) -> tuple[str | None, list[str]]:
    """Fold the session into the Layer-3 global profile: aggregates, pattern detection (PR12), and
    CEFR smoothing. Returns (committed CEFR, recommendations)."""
    profile = await get_profile(db, user_id)
    if profile is None:
        profile = LearningProfile(user_id=user_id)
        db.add(profile)

    by_pillar = global_stats["by_pillar"]
    by_subtype = global_stats["by_subtype"]
    freq = sorted(by_subtype.items(), key=lambda kv: kv[1], reverse=True)

    profile.totals = {"by_pillar": by_pillar, "by_subtype": by_subtype}
    profile.frequent_mistakes = [{"subtype": s, "count": n} for s, n in freq[:5]]
    # Deterministic "strengths" proxy: pillars with the fewest mistakes (refined by the LLM later).
    profile.strengths = sorted(PILLARS, key=lambda p: by_pillar.get(p, 0))[:2]
    profile.sessions_completed = (profile.sessions_completed or 0) + 1

    # Pattern detection (PR12): mastered / recurring / improving + recommendations over time.
    report = detect_patterns(await mistake_history(db, user_id))
    profile.mastered = report.mastered
    profile.recommendations = report.recommendations
    profile.patterns = {"recurring": report.recurring, "improving": report.improving}
    # Prioritize recurring patterns as the weak areas, then fill with other frequent subtypes.
    others = [s for s, _ in freq if s not in report.recurring]
    profile.weaknesses = (report.recurring + others)[:3]

    history = list(profile.cefr_history or [])
    history.append(
        {"level": assessment.estimated_cefr, "confidence": assessment.confidence, "ts": _now_iso()}
    )
    history = history[-20:]
    new_committed, new_emerging = decide_cefr(profile.committed_cefr, history)
    profile.cefr_history = history
    profile.committed_cefr = new_committed
    profile.emerging_cefr = new_emerging
    profile.cefr_confidence = assessment.confidence
    profile.target_cefr = assessment.next_goal

    await db.commit()
    return new_committed, report.recommendations


def _build_summary(
    space: LearningSpace,
    metrics: SessionMetrics,
    duration_min: int,
    current_level: str,
    recommendation: str | None = None,
) -> SessionSummary:
    scores = metrics.pillar_scores
    target = space.level.value
    by_score_desc = sorted(PILLARS, key=lambda p: scores[p], reverse=True)
    by_score_asc = sorted(PILLARS, key=lambda p: scores[p])

    strong = [_PILLAR_LABELS[p] for p in by_score_desc if scores[p] >= 80][:2]
    weak = [_PILLAR_LABELS[p] for p in by_score_asc if scores[p] < 90][:2]

    most_pillar = (
        max(metrics.pillar_counts, key=lambda p: metrics.pillar_counts[p])
        if any(metrics.pillar_counts.values())
        else None
    )
    most_common = _PILLAR_LABELS[most_pillar] if most_pillar else "—"

    if recommendation is None:
        # Cold start (no pattern recommendation yet): fall back to the weakest-pillar heuristic.
        weakest = by_score_asc[0]
        scenario_phrase = space.scenario_type.value.replace("_", " ")
        recommendation = (
            f"Focus on {_PILLAR_LABELS[weakest].lower()}. Keep practicing {scenario_phrase}."
        )

    return SessionSummary(
        current_level=current_level,
        target_level=target,
        pillar_scores=PillarScores(
            semantics=scores["semantics"],
            syntax=scores["syntax"],
            orthography=scores["orthography"],
            living_communication=scores["living_communication"],
        ),
        duration_min=duration_min,
        message_count=metrics.message_count,
        strong_areas=strong,
        weak_areas=weak,
        most_common_correction=most_common,
        recommendation=recommendation,
    )


async def complete_session(
    db: AsyncSession, user: User, space: LearningSpace, session_id: str
) -> SessionSummary:
    """Roll up one finished session: metrics → Layer-2 space profile → SessionSummary."""
    transcript = await get_or_create_transcript(db, user.id, session_id, space.id)
    user_messages = [
        str(m.get("content", "")) for m in transcript.messages if m.get("role") == "user"
    ]
    mistakes = await session_mistakes(db, user.id, session_id)
    metrics = compute_session_metrics(user_messages, mistakes)

    # Layer 2: per-space (domain) profile
    space_stats = await mistake_stats(db, user.id, space_id=space.id)
    weak_subtypes = _top_keys(space_stats["by_subtype"], 3)
    await _update_space_profile(db, user.id, space.id, metrics, weak_subtypes)

    # Layer 3: global profile + pattern detection + hybrid CEFR reassessment (smoothed)
    global_stats = await mistake_stats(db, user.id)
    assessment = await assess_cefr(metrics, space.level.value, user_messages)
    committed, recommendations = await _update_global_profile(
        db, user.id, metrics, global_stats, assessment
    )

    current_level = committed or _level_below(space.level.value)
    recommendation = recommendations[0] if recommendations else None
    return _build_summary(
        space, metrics, _duration_min(transcript.messages), current_level, recommendation
    )
