from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Level, LinguisticCategory, Persona, ScenarioType


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    assistant: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool = False
    role: str = "client"


# --- Learning Spaces (per-user course = scenario_type + level + persona) -----
class SpaceCreate(BaseModel):
    scenario_type: ScenarioType
    level: Level
    persona: Persona


class SpaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    scenario_type: ScenarioType
    level: Level
    persona: Persona
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Test slots -------------------------------------------------------------
class TestSlotCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    scenario_id: Optional[int] = None
    payload: Dict[str, object] = Field(default_factory=dict)


class TestSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    scenario_id: Optional[int] = None
    payload: Dict[str, object] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


# --- Orchestrator / tutor ---------------------------------------------------
Severity = Literal["minor", "moderate", "major"]


class MistakeItem(BaseModel):
    """One learner mistake, bucketed by linguistic pillar. Explanation is in Serbian."""

    category: LinguisticCategory
    original: str = ""
    correction: str = ""
    explanation: str = ""
    severity: Severity = "moderate"


class ErrorAnalysis(BaseModel):
    mistakes: List[MistakeItem] = []


class TutorTranslation(BaseModel):
    """Serbian translations, shown on demand in the UI."""

    ai_response: str = ""
    correction: str = ""


class TutorTurnResult(BaseModel):
    """The LLM-produced structured turn (before persona/session_id are attached)."""

    ai_response: str = ""
    correction: str = ""
    translation: TutorTranslation = Field(default_factory=TutorTranslation)
    hints: List[str] = []
    mistakes: List[MistakeItem] = []


class PersonaOut(BaseModel):
    slug: str
    name: str
    avatar: str
    tone: str


class TutorTurnRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    session_id: Optional[str] = None
    persona: Optional[str] = None
    scenario_id: Optional[int] = None


class TutorTurnResponse(TutorTurnResult):
    persona: str
    session_id: str


class ProgressItem(BaseModel):
    category: LinguisticCategory
    count: int
