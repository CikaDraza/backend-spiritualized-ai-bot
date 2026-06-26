import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow is deprecated)."""
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    """User role: clients learn; admins manage global scenarios/lessons/personas."""

    client = "client"
    admin = "admin"


class LinguisticCategory(str, enum.Enum):
    """The four linguistic pillars (GUIDE.md) used to bucket learner mistakes."""

    semantics = "semantics"
    syntax = "syntax"
    orthography = "orthography"
    living_communication = "living_communication"


class MistakeSubtype(str, enum.Enum):
    """Granular mistake label the LLM emits per error. The backend deterministically maps each
    subtype to one of the four pillars (LinguisticCategory) via app.taxonomy — the model never
    picks the pillar itself. `pronunciation` is dormant until Voice (PR16)."""

    articles = "articles"
    prepositions = "prepositions"
    verb_tenses = "verb_tenses"
    word_order = "word_order"
    vocabulary = "vocabulary"
    clarity = "clarity"
    spelling = "spelling"
    pronunciation = "pronunciation"
    idioms = "idioms"
    naturalness = "naturalness"
    other = "other"


class MistakeSeverity(str, enum.Enum):
    """How serious a single mistake is — drives correction-card colors and profile weighting."""

    minor = "minor"
    moderate = "moderate"
    major = "major"


# --- Learning Space enums (per-user course; admin "Scenario" catalog is separate, later) ----
class ScenarioType(str, enum.Enum):
    business_communication = "business_communication"
    everyday_conversation = "everyday_conversation"
    job_interview = "job_interview"
    shopping = "shopping"
    travel = "travel"


class Level(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


class Persona(str, enum.Enum):
    mila = "mila"
    viktor = "viktor"
    nora = "nora"
    maria = "maria"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role"),
        default=Role.client,
        server_default="client",
        index=True,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    spaces: Mapped[list["LearningSpace"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    test_slots: Mapped[list["TestSlot"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    transcripts: Mapped[list["Transcript"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    mistakes: Mapped[list["Mistake"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Rotating refresh token (PR3). Only the hash is stored, never the raw token."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    """Single-use email verification token stored in Postgres for an audit trail (PR4)."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="email_verification_tokens")


class LearningSpace(Base):
    """A per-user personalized course = scenario_type + level + persona (max 5 active per user).
    Title is auto-generated ("Job Interview · B1 · Viktor"). The admin/global "Scenario" catalog
    is a separate concept (later). Delete is soft (is_active=false)."""

    __tablename__ = "learning_spaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    scenario_type: Mapped[ScenarioType] = mapped_column(
        Enum(ScenarioType, name="space_scenario_type")
    )
    level: Mapped[Level] = mapped_column(Enum(Level, name="space_level"))
    persona: Mapped[Persona] = mapped_column(Enum(Persona, name="space_persona"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="spaces")
    test_slots: Mapped[list["TestSlot"]] = relationship(back_populates="space")
    transcripts: Mapped[list["Transcript"]] = relationship(back_populates="space")


class TestSlot(Base):
    """A saved test/quiz. Max MAX_TEST_SLOTS per user (enforced in CRUD, PR6 — no FIFO)."""

    __tablename__ = "test_slots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # FK column keeps the name scenario_id but references learning_spaces (legacy name).
    scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="test_slots")
    space: Mapped[Optional["LearningSpace"]] = relationship(back_populates="test_slots")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_name: Mapped[Optional[str]] = mapped_column(String(128))
    current_topic: Mapped[Optional[str]] = mapped_column(String(256))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="chat_sessions")


class Transcript(Base):
    """Conversation transcript as a JSONB message array — Postgres stand-in for the deferred
    Mongo transcript store. One row per chat session_id."""

    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # FK column keeps the name scenario_id but references learning_spaces (legacy name).
    scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    messages: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="transcripts")
    space: Mapped[Optional["LearningSpace"]] = relationship(back_populates="transcripts")
    mistakes: Mapped[list["Mistake"]] = relationship(back_populates="transcript")


class Mistake(Base):
    """A single learner mistake bucketed by linguistic pillar, for progress tracking (PR7)."""

    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    transcript_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("transcripts.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    category: Mapped[LinguisticCategory] = mapped_column(
        Enum(LinguisticCategory, name="linguistic_category"), index=True
    )
    # Granular label + seriousness (PR11.2). Nullable so pre-PR11 rows stay valid.
    subtype: Mapped[Optional[MistakeSubtype]] = mapped_column(
        Enum(MistakeSubtype, name="mistake_subtype"), nullable=True, index=True
    )
    severity: Mapped[Optional[MistakeSeverity]] = mapped_column(
        Enum(MistakeSeverity, name="mistake_severity"), nullable=True, index=True
    )
    original: Mapped[Optional[str]] = mapped_column(Text)
    correction: Mapped[Optional[str]] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="mistakes")
    transcript: Mapped[Optional["Transcript"]] = relationship(back_populates="mistakes")


class LearningSpaceProfile(Base):
    """Layer 2 memory (PR11.3): how a learner performs *within one Learning Space* (domain).
    One row per (user, space); evolves on each completed session. Distinct from the per-user
    Global Learning Profile (Layer 3)."""

    __tablename__ = "learning_space_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "space_id", name="uq_space_profile_user_space"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    space_id: Mapped[int] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), index=True
    )
    # per-pillar score 0..100, an EMA across this space's sessions
    pillar_scores: Mapped[dict[str, int]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    # subtypes the learner errs on most in this domain (most-frequent first)
    weak_areas: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    # domain vocabulary strengths — filled by the LLM assessment (PR11.4)
    domain_vocabulary: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    sessions_completed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class LearningProfile(Base):
    """Layer 3 memory (PR11.4): the learner's global identity across all spaces — a smoothed CEFR
    estimate, recurring mistakes, strengths/weaknesses, learning style. One row per user. CEFR
    levels are stored as 2-char strings (A1..C1) to avoid a second Postgres enum type."""

    __tablename__ = "learning_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Smoothed CEFR (Layer C): committed is the stable shown level; emerging is the latest candidate.
    committed_cefr: Mapped[Optional[str]] = mapped_column(String(2))
    emerging_cefr: Mapped[Optional[str]] = mapped_column(String(2))
    target_cefr: Mapped[Optional[str]] = mapped_column(String(2))
    cefr_confidence: Mapped[float] = mapped_column(
        Float, default=0.0, server_default=text("0")
    )
    cefr_history: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    # Global aggregates (machine form: raw pillar/subtype keys).
    strengths: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    weaknesses: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    frequent_mistakes: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    mastered: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    # Adaptive recommendations + structured pattern report (PR12): {recurring:[], improving:[]}.
    recommendations: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    patterns: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    # Filled by a later LLM pass; nullable for now.
    learning_style: Mapped[Optional[dict[str, object]]] = mapped_column(JSONB, nullable=True)
    totals: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    sessions_completed: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
