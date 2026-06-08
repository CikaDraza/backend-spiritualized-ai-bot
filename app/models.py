import enum
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
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

    scenarios: Mapped[list["Scenario"]] = relationship(
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


class Scenario(Base):
    """A learning scenario/course. GUIDE.md treats 'scenario/course' as one concept, so this
    supersedes the old `courses` table. Max MAX_ACTIVE_SCENARIOS active per user (enforced in
    CRUD, PR6 — no FIFO)."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="scenarios")
    test_slots: Mapped[list["TestSlot"]] = relationship(back_populates="scenario")
    transcripts: Mapped[list["Transcript"]] = relationship(back_populates="scenario")


class TestSlot(Base):
    """A saved test/quiz. Max MAX_TEST_SLOTS per user (enforced in CRUD, PR6 — no FIFO)."""

    __tablename__ = "test_slots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scenarios.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="test_slots")
    scenario: Mapped[Optional["Scenario"]] = relationship(back_populates="test_slots")


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
    scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scenarios.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="transcripts")
    scenario: Mapped[Optional["Scenario"]] = relationship(back_populates="transcripts")
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
    original: Mapped[Optional[str]] = mapped_column(Text)
    correction: Mapped[Optional[str]] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="mistakes")
    transcript: Mapped[Optional["Transcript"]] = relationship(back_populates="mistakes")
