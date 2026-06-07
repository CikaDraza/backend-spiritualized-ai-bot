from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .ai import generate_spiritual_response
from .constants import MAX_ACTIVE_SCENARIOS, MAX_TEST_SLOTS
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
    count_active_scenarios,
    count_test_slots,
    create_email_verification_token,
    create_refresh_token,
    create_scenario,
    create_test_slot,
    create_user,
    delete_scenario,
    delete_test_slot,
    delete_unused_verification_tokens,
    get_email_verification_token,
    get_refresh_token,
    get_scenario,
    get_test_slot,
    get_user_by_email,
    get_user_by_id,
    is_refresh_token_valid,
    is_verification_token_usable,
    list_scenarios,
    list_test_slots,
    mark_email_verified,
    mistakes_summary,
    revoke_all_user_refresh_tokens,
    revoke_refresh_token,
    update_scenario,
)
from .database import get_db
from .email import send_verification_email
from .agents import list_personas
from .orchestrator import run_turn
from .rate_limit import rate_limit_chat
from .redis_client import close_redis
from .models import Scenario, TestSlot, User
from .schemas import (
    ChatRequest,
    ChatResponse,
    PersonaOut,
    ProgressItem,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
    TestSlotCreate,
    TestSlotOut,
    TutorTurnRequest,
    TutorTurnResponse,
    UserCreate,
    UserLogin,
    UserProfile,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by Alembic migrations (`alembic upgrade head`), not Base.metadata.create_all.
    yield
    await close_redis()


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
        is_active=bool(user.is_active),
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


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit_chat)])
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


# --- Scenarios (tutor feature — require a verified email) --------------------
async def _scenario_limit_error(db: AsyncSession, user_id: int) -> HTTPException:
    """409 carrying the current scenarios so the UI can ask which to delete (no FIFO)."""
    scenarios = await list_scenarios(db, user_id)
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "scenario_limit_reached",
            "message": (
                f"You already have {MAX_ACTIVE_SCENARIOS} active scenarios. "
                "Delete or deactivate one before creating a new one."
            ),
            "limit": MAX_ACTIVE_SCENARIOS,
            "scenarios": jsonable_encoder(
                [ScenarioOut.model_validate(s) for s in scenarios]
            ),
        },
    )


async def _owned_scenario(
    scenario_id: int, current_user: User, db: AsyncSession
) -> Scenario:
    scenario = await get_scenario(db, scenario_id)
    if scenario is None or scenario.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@app.get("/scenarios", response_model=list[ScenarioOut])
async def list_scenarios_endpoint(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> list[Scenario]:
    return await list_scenarios(db, current_user.id)


@app.post("/scenarios", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario_endpoint(
    payload: ScenarioCreate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Scenario:
    if await count_active_scenarios(db, current_user.id) >= MAX_ACTIVE_SCENARIOS:
        raise await _scenario_limit_error(db, current_user.id)
    return await create_scenario(db, current_user.id, payload.title, payload.description)


@app.patch("/scenarios/{scenario_id}", response_model=ScenarioOut)
async def update_scenario_endpoint(
    scenario_id: int,
    payload: ScenarioUpdate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Scenario:
    scenario = await _owned_scenario(scenario_id, current_user, db)
    # Reactivating an inactive scenario must still respect the active-scenario limit.
    if payload.is_active is True and not scenario.is_active:
        if await count_active_scenarios(db, current_user.id) >= MAX_ACTIVE_SCENARIOS:
            raise await _scenario_limit_error(db, current_user.id)
    return await update_scenario(
        db,
        scenario,
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
    )


@app.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario_endpoint(
    scenario_id: int,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    scenario = await _owned_scenario(scenario_id, current_user, db)
    await delete_scenario(db, scenario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Test slots (tutor feature — require a verified email) -------------------
async def _test_slot_limit_error(db: AsyncSession, user_id: int) -> HTTPException:
    slots = await list_test_slots(db, user_id)
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "test_slot_limit_reached",
            "message": (
                f"You already have {MAX_TEST_SLOTS} saved tests. "
                "Delete one before saving a new test."
            ),
            "limit": MAX_TEST_SLOTS,
            "tests": jsonable_encoder([TestSlotOut.model_validate(s) for s in slots]),
        },
    )


async def _owned_test_slot(
    test_id: int, current_user: User, db: AsyncSession
) -> TestSlot:
    slot = await get_test_slot(db, test_id)
    if slot is None or slot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Test not found")
    return slot


@app.get("/tests", response_model=list[TestSlotOut])
async def list_tests_endpoint(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> list[TestSlot]:
    return await list_test_slots(db, current_user.id)


@app.post("/tests", response_model=TestSlotOut, status_code=status.HTTP_201_CREATED)
async def create_test_endpoint(
    payload: TestSlotCreate,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> TestSlot:
    if await count_test_slots(db, current_user.id) >= MAX_TEST_SLOTS:
        raise await _test_slot_limit_error(db, current_user.id)
    # A scenario_id, when provided, must belong to the caller.
    if payload.scenario_id is not None:
        await _owned_scenario(payload.scenario_id, current_user, db)
    return await create_test_slot(
        db, current_user.id, payload.title, payload.scenario_id, payload.payload
    )


@app.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_endpoint(
    test_id: int,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    slot = await _owned_test_slot(test_id, current_user, db)
    await delete_test_slot(db, slot)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Tutor orchestrator (multi-agent) ---------------------------------------
@app.get("/tutor/personas", response_model=list[PersonaOut])
async def tutor_personas() -> list[PersonaOut]:
    return [
        PersonaOut(slug=p.slug, name=p.name, avatar=p.avatar, tone=p.tone)
        for p in list_personas()
    ]


@app.post(
    "/tutor/turn",
    response_model=TutorTurnResponse,
    dependencies=[Depends(rate_limit_chat)],
)
async def tutor_turn(
    payload: TutorTurnRequest,
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> TutorTurnResponse:
    if payload.scenario_id is not None:
        await _owned_scenario(payload.scenario_id, current_user, db)
    session_id = payload.session_id or str(uuid4())
    try:
        return await run_turn(
            db,
            current_user,
            payload.message,
            payload.history,
            session_id,
            payload.persona,
            payload.scenario_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/tutor/progress", response_model=list[ProgressItem])
async def tutor_progress(
    current_user: User = Depends(get_verified_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProgressItem]:
    summary = await mistakes_summary(db, current_user.id)
    return [ProgressItem(category=cat, count=count) for cat, count in summary]
