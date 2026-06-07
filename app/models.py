import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    """Timezone-aware UTC now (datetime.utcnow is deprecated)."""
    return datetime.now(timezone.utc)


class LinguisticCategory(str, enum.Enum):
    """The four linguistic pillars (GUIDE.md) used to bucket learner mistakes."""

    semantics = "semantics"
    syntax = "syntax"
    orthography = "orthography"
    living_communication = "living_communication"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)

    scenarios = relationship(
        "Scenario", back_populates="owner", cascade="all, delete-orphan"
    )
    chat_sessions = relationship(
        "ChatSession", back_populates="owner", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    test_slots = relationship(
        "TestSlot", back_populates="owner", cascade="all, delete-orphan"
    )
    transcripts = relationship(
        "Transcript", back_populates="owner", cascade="all, delete-orphan"
    )
    mistakes = relationship(
        "Mistake", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Rotating refresh token (PR3). Only the hash is stored, never the raw token."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    """Single-use email verification token stored in Postgres for an audit trail (PR4)."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="email_verification_tokens")


class Scenario(Base):
    """A learning scenario/course. GUIDE.md treats 'scenario/course' as one concept, so this
    supersedes the old `courses` table. Max MAX_ACTIVE_SCENARIOS active per user (enforced in
    CRUD, PR6 — no FIFO)."""

    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="scenarios")
    test_slots = relationship("TestSlot", back_populates="scenario")
    transcripts = relationship("Transcript", back_populates="scenario")


class TestSlot(Base):
    """A saved test/quiz. Max MAX_TEST_SLOTS per user (enforced in CRUD, PR6 — no FIFO)."""

    __tablename__ = "test_slots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_id = Column(
        Integer, ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(128), nullable=False)
    payload = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    owner = relationship("User", back_populates="test_slots")
    scenario = relationship("Scenario", back_populates="test_slots")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_name = Column(String(128), nullable=True)
    current_topic = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="chat_sessions")


class Transcript(Base):
    """Conversation transcript as a JSONB message array — Postgres stand-in for the deferred
    Mongo transcript store. One row per chat session_id."""

    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_id = Column(
        Integer, ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id = Column(String(64), nullable=False, index=True)
    messages = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="transcripts")
    scenario = relationship("Scenario", back_populates="transcripts")
    mistakes = relationship("Mistake", back_populates="transcript")


class Mistake(Base):
    """A single learner mistake bucketed by linguistic pillar, for progress tracking (PR7)."""

    __tablename__ = "mistakes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transcript_id = Column(
        Integer, ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id = Column(String(64), nullable=True, index=True)
    category = Column(
        Enum(LinguisticCategory, name="linguistic_category"), nullable=False, index=True
    )
    original = Column(Text, nullable=True)
    correction = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="mistakes")
    transcript = relationship("Transcript", back_populates="mistakes")
