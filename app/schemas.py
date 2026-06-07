from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import LinguisticCategory


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


# --- Scenarios --------------------------------------------------------------
class ScenarioCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None


class ScenarioUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=128)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- Test slots -------------------------------------------------------------
class TestSlotCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    scenario_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TestSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    scenario_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


# --- Orchestrator / tutor ---------------------------------------------------
class MistakeItem(BaseModel):
    """One learner mistake, bucketed by linguistic pillar. Explanation is in Serbian."""

    category: LinguisticCategory
    original: str = ""
    correction: str = ""
    explanation: str = ""


class ErrorAnalysis(BaseModel):
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


class TutorTurnResponse(BaseModel):
    assistant: str
    persona: str
    session_id: str
    mistakes: List[MistakeItem] = []


class ProgressItem(BaseModel):
    category: LinguisticCategory
    count: int
