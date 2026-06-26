from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from .models import Level, LinguisticCategory, MistakeSubtype, Persona, ScenarioType
from .taxonomy import pillar_for


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
    """One learner mistake. The LLM emits `subtype`; `category` (the pillar) is always derived from
    it via the taxonomy, never trusted from the model. Explanation is in Serbian."""

    subtype: MistakeSubtype = MistakeSubtype.other
    category: LinguisticCategory = LinguisticCategory.semantics
    original: str = ""
    correction: str = ""
    explanation: str = ""
    severity: Severity = "moderate"

    @model_validator(mode="after")
    def _derive_category(self) -> "MistakeItem":
        # Single source of truth: the pillar is computed from the subtype, overriding any value the
        # model may have guessed.
        self.category = pillar_for(self.subtype)
        return self


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


# --- Session summary (PR11.3) -----------------------------------------------
class PillarScores(BaseModel):
    """0..100 score per linguistic pillar for one session."""

    semantics: int
    syntax: int
    orthography: int
    living_communication: int


class SessionSummary(BaseModel):
    """End-of-session rollup the frontend drawer renders (computed server-side; replaces the old
    client mock heuristic)."""

    current_level: str
    target_level: str
    pillar_scores: PillarScores
    duration_min: int
    message_count: int
    strong_areas: list[str]
    weak_areas: list[str]
    most_common_correction: str
    recommendation: str


class SessionCompleteRequest(BaseModel):
    session_id: str
    scenario_id: int


class CefrAssessment(BaseModel):
    """Hybrid CEFR engine output (PR11.4). The LLM (Layer B) returns these; the deterministic
    baseline (Layer A) fills the same shape when no key is set."""

    estimated_cefr: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    next_goal: str = ""
