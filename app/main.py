from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .ai import generate_spiritual_response
from .auth import (
    clear_auth_cookies,
    create_access_token,
    decode_access_token,
    email_verification_expiry,
    generate_refresh_token,
    generate_verification_token,
    hash_token,
    refresh_token_expiry,
    set_auth_cookies,
)
from .config import settings
from .crud import (
    authenticate_user,
    create_email_verification_token,
    create_refresh_token,
    create_user,
    delete_unused_verification_tokens,
    get_email_verification_token,
    get_refresh_token,
    get_user_by_email,
    get_user_by_id,
    is_refresh_token_valid,
    is_verification_token_usable,
    mark_email_verified,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
)
from .database import get_db
from .email import send_verification_email
from .models import User
from .schemas import (
    ChatRequest,
    ChatResponse,
    UserCreate,
    UserLogin,
    UserProfile,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by Alembic migrations (`alembic upgrade head`), not Base.metadata.create_all.
    # Startup/shutdown resources (Redis pool, etc.) will be wired here in later PRs.
    yield


app = FastAPI(
    title="Spiritualized AI Mentor",
    description="FastAPI backend for the Spiritualized bilingual English mentor bot.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


async def _start_session(db: AsyncSession, response: Response, user: User) -> UserProfile:
    """Issue an access JWT + a rotating refresh token, persist the refresh hash, set cookies."""
    access_token = create_access_token({"sub": user.email, "user_id": user.id})
    raw_refresh = generate_refresh_token()
    await create_refresh_token(db, user.id, hash_token(raw_refresh), refresh_token_expiry())
    set_auth_cookies(response, access_token, raw_refresh)
    return _profile(user)


async def _issue_verification(db: AsyncSession, user: User) -> None:
    """Replace any pending token with a fresh one, then send it (or log it in dev-fallback)."""
    raw_token = generate_verification_token()
    await delete_unused_verification_tokens(db, user.id)
    await create_email_verification_token(
        db, user.id, hash_token(raw_token), email_verification_expiry()
    )
    await send_verification_email(user.email, raw_token)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Spiritualized Backend API is running",
        "version": "0.1.0",
    }


async def get_current_user_optional(
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = access_token
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    token_data = decode_access_token(token)
    if not token_data or not token_data.user_id:
        return None

    return await get_user_by_id(db, token_data.user_id)


async def get_current_user(
    current_user: User | None = Depends(get_current_user_optional),
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return current_user


async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Gate for tutor features that require a confirmed email (scenarios/tests/orchestrator)."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Check your inbox or resend the verification link.",
        )
    return current_user


@app.post("/auth/register", response_model=UserProfile)
async def register(
    user: UserCreate, response: Response, db: AsyncSession = Depends(get_db)
) -> UserProfile:
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = await create_user(db, user)
    await _issue_verification(db, db_user)
    return await _start_session(db, response, db_user)


@app.post("/auth/login", response_model=UserProfile)
async def login(
    user: UserLogin, response: Response, db: AsyncSession = Depends(get_db)
) -> UserProfile:
    db_user = await authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return await _start_session(db, response, db_user)


@app.post("/auth/refresh", response_model=UserProfile)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token = await get_refresh_token(db, hash_token(refresh_token))
    if token is None:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Reuse of an already-rotated/expired token is treated as compromise: revoke the whole family.
    if not is_refresh_token_valid(token):
        await revoke_all_user_refresh_tokens(db, token.user_id)
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token no longer valid")

    user = await get_user_by_id(db, token.user_id)
    if user is None:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User not found")

    await revoke_refresh_token(db, token)  # rotation
    return await _start_session(db, response, user)


@app.post("/auth/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        token = await get_refresh_token(db, hash_token(refresh_token))
        if token is not None and not token.revoked:
            await revoke_refresh_token(db, token)
    clear_auth_cookies(response)
    return {"status": "logged_out"}


@app.get("/auth/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)) -> UserProfile:
    return _profile(current_user)


@app.get("/auth/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    record = await get_email_verification_token(db, hash_token(token))
    if record is None:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if not is_verification_token_usable(record):
        raise HTTPException(
            status_code=400, detail="Verification token expired or already used"
        )
    await mark_email_verified(db, record)
    return {"status": "verified"}


@app.post("/auth/resend-verification")
async def resend_verification(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if current_user.is_verified:
        return {"status": "already_verified"}
    await _issue_verification(db, current_user)
    return {"status": "sent"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User | None = Depends(get_current_user_optional),
) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    try:
        assistant_text = await generate_spiritual_response(
            request,
            user_id=current_user.id if current_user else None,
            session_id=session_id,
        )
        return ChatResponse(assistant=assistant_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
