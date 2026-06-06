from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .ai import generate_spiritual_response
from .auth import create_access_token, decode_access_token
from .crud import authenticate_user, create_user, get_user_by_id, get_user_by_email
from .database import Base, engine, get_db
from .models import User
from .schemas import (
    ChatRequest,
    ChatResponse,
    Token,
    UserCreate,
    UserLogin,
    UserProfile,
)

app = FastAPI(
    title="Spiritualized AI Mentor",
    description="FastAPI backend for the Spiritualized bilingual English mentor bot.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Spiritualized Backend API is running",
        "version": "0.1.0",
    }


async def get_current_user_optional(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    token_data = decode_access_token(token)
    if not token_data or not token_data.user_id:
        return None

    return await get_user_by_id(db, token_data.user_id)


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    current_user = await get_current_user_optional(authorization, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return current_user


@app.post("/auth/register", response_model=Token)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = await create_user(db, user)
    access_token = create_access_token({"sub": db_user.email, "user_id": db_user.id})
    return Token(access_token=access_token)


@app.post("/auth/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    db_user = await authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": db_user.email, "user_id": db_user.id})
    return Token(access_token=access_token)


@app.get("/auth/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user)) -> UserProfile:
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
    )


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
