from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_password_hash, verify_password
from .models import EmailVerificationToken, RefreshToken, User
from .schemas import UserCreate


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
