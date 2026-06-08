from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_password_hash, verify_password
from .models import (
    EmailVerificationToken,
    LearningSpace,
    Level,
    LinguisticCategory,
    Mistake,
    Persona,
    RefreshToken,
    ScenarioType,
    TestSlot,
    Transcript,
    User,
)
from .schemas import MistakeItem, UserCreate


# --- Users ------------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password, full_name=user.full_name)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


# --- Refresh tokens ---------------------------------------------------------
def is_refresh_token_valid(token: RefreshToken) -> bool:
    if token.revoked:
        return False
    expires_at = token.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at is None or expires_at > datetime.now(timezone.utc)


async def create_refresh_token(
    db: AsyncSession, user_id: int, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_refresh_token(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Look up by hash regardless of revoked/expiry, so callers can detect token reuse."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return result.scalars().first()


async def revoke_refresh_token(db: AsyncSession, token: RefreshToken) -> None:
    token.revoked = True
    await db.commit()


async def revoke_all_user_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    await db.commit()


# --- Email verification tokens ----------------------------------------------
def is_verification_token_usable(token: EmailVerificationToken) -> bool:
    if token.used_at is not None:
        return False
    expires_at = token.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at is None or expires_at > datetime.now(timezone.utc)


async def delete_unused_verification_tokens(db: AsyncSession, user_id: int) -> None:
    """Keep at most one active verification token per user (called before issuing a new one)."""
    await db.execute(
        delete(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
    )
    await db.commit()


async def create_email_verification_token(
    db: AsyncSession, user_id: int, token_hash: str, expires_at: datetime
) -> EmailVerificationToken:
    token = EmailVerificationToken(
        user_id=user_id, token_hash=token_hash, expires_at=expires_at
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_email_verification_token(
    db: AsyncSession, token_hash: str
) -> EmailVerificationToken | None:
    result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
    )
    return result.scalars().first()


async def mark_email_verified(
    db: AsyncSession, token: EmailVerificationToken
) -> User | None:
    """Consume the token and flip the owning user's is_verified flag."""
    token.used_at = datetime.now(timezone.utc)
    user = await get_user_by_id(db, token.user_id)
    if user is not None:
        user.is_verified = True
    await db.commit()
    return user


# --- Learning Spaces --------------------------------------------------------
async def list_spaces(db: AsyncSession, user_id: int) -> list[LearningSpace]:
    """Active spaces only (soft-deleted are hidden)."""
    result = await db.execute(
        select(LearningSpace)
        .where(LearningSpace.user_id == user_id, LearningSpace.is_active.is_(True))
        .order_by(LearningSpace.created_at.desc())
    )
    return list(result.scalars().all())


async def count_active_spaces(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(LearningSpace)
        .where(LearningSpace.user_id == user_id, LearningSpace.is_active.is_(True))
    )
    return int(result.scalar_one())


async def get_space(db: AsyncSession, space_id: int) -> LearningSpace | None:
    result = await db.execute(
        select(LearningSpace).where(LearningSpace.id == space_id)
    )
    return result.scalars().first()


async def create_space(
    db: AsyncSession,
    user_id: int,
    title: str,
    scenario_type: ScenarioType,
    level: Level,
    persona: Persona,
) -> LearningSpace:
    space = LearningSpace(
        user_id=user_id,
        title=title,
        scenario_type=scenario_type,
        level=level,
        persona=persona,
    )
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return space


async def soft_delete_space(db: AsyncSession, space: LearningSpace) -> None:
    """Soft delete: keep the row, flip is_active=false (no hard delete for now)."""
    space.is_active = False
    await db.commit()


# --- Test slots -------------------------------------------------------------
async def list_test_slots(db: AsyncSession, user_id: int) -> list[TestSlot]:
    result = await db.execute(
        select(TestSlot)
        .where(TestSlot.user_id == user_id)
        .order_by(TestSlot.created_at.desc())
    )
    return list(result.scalars().all())


async def count_test_slots(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(TestSlot).where(TestSlot.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_test_slot(db: AsyncSession, test_id: int) -> TestSlot | None:
    result = await db.execute(select(TestSlot).where(TestSlot.id == test_id))
    return result.scalars().first()


async def create_test_slot(
    db: AsyncSession,
    user_id: int,
    title: str,
    scenario_id: Optional[int],
    payload: dict[str, Any],
) -> TestSlot:
    slot = TestSlot(
        user_id=user_id, title=title, scenario_id=scenario_id, payload=payload
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


async def delete_test_slot(db: AsyncSession, slot: TestSlot) -> None:
    await db.delete(slot)
    await db.commit()


# --- Transcripts & mistakes (orchestrator) ----------------------------------
async def get_or_create_transcript(
    db: AsyncSession, user_id: int, session_id: str, scenario_id: Optional[int] = None
) -> Transcript:
    result = await db.execute(
        select(Transcript).where(
            Transcript.user_id == user_id, Transcript.session_id == session_id
        )
    )
    transcript = result.scalars().first()
    if transcript is None:
        transcript = Transcript(
            user_id=user_id, session_id=session_id, scenario_id=scenario_id, messages=[]
        )
        db.add(transcript)
        await db.commit()
        await db.refresh(transcript)
    return transcript


async def append_transcript_messages(
    db: AsyncSession, transcript: Transcript, new_messages: list[dict[str, Any]]
) -> Transcript:
    # Reassign (not in-place mutate) so SQLAlchemy detects the JSONB change.
    transcript.messages = list(transcript.messages or []) + new_messages
    await db.commit()
    await db.refresh(transcript)
    return transcript


async def create_mistakes(
    db: AsyncSession,
    user_id: int,
    transcript_id: Optional[int],
    session_id: str,
    items: list[MistakeItem],
) -> None:
    for item in items:
        db.add(
            Mistake(
                user_id=user_id,
                transcript_id=transcript_id,
                session_id=session_id,
                category=item.category,
                original=item.original,
                correction=item.correction,
                explanation=item.explanation,
            )
        )
    await db.commit()


async def mistakes_summary(
    db: AsyncSession, user_id: int
) -> list[tuple[LinguisticCategory, int]]:
    result = await db.execute(
        select(Mistake.category, func.count())
        .where(Mistake.user_id == user_id)
        .group_by(Mistake.category)
    )
    return [(row[0], int(row[1])) for row in result.all()]
