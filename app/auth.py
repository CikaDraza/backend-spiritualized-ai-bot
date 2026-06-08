from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Response
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pydantic import BaseModel

from .config import settings

# argon2id via pwdlib (replaces the unmaintained passlib).
password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# Refresh cookie is scoped to /auth so it is only sent to refresh/logout, not to /chat etc.
REFRESH_COOKIE_PATH = "/auth"


class TokenData(BaseModel):
    email: str | None = None
    user_id: int | None = None


# --- Passwords --------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


# --- Access tokens (JWT) ----------------------------------------------------
def create_access_token(data: dict[str, object], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenData | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(email=payload.get("sub"), user_id=payload.get("user_id"))
    except JWTError:
        return None


# --- Refresh tokens (opaque, stored hashed) ---------------------------------
def generate_refresh_token() -> str:
    """Raw refresh token handed to the client; only its hash is persisted."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


# --- Email verification tokens (opaque, stored hashed) ----------------------
def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)


def email_verification_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
    )


# --- Cookies ----------------------------------------------------------------
def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, domain=settings.COOKIE_DOMAIN)
