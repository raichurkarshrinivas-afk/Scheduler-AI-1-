import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AmbiguityType(str, enum.Enum):
    UNDEFINED_TIME = "UNDEFINED_TIME"
    UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
    PREFERENCE_VS_HARD_CONSTRAINT = "PREFERENCE_VS_HARD_CONSTRAINT"
    TERM_WIDE_VS_DATE_SPECIFIC = "TERM_WIDE_VS_DATE_SPECIFIC"
    OTHER = "OTHER"


class AmbiguityFlag(BaseModel):
    type: AmbiguityType
    description: str
    suggested_clarification: str


class AIStatusOut(BaseModel):
    enabled: bool
    provider: str
    is_available: bool
    model_name: str
    total_requests: int
    total_tokens: int
    estimated_cost_usd: float
    disclaimer: str = (
        "AI suggestions are unverified candidate interpretations. "
        "You must review and validate against institutional rules before applying."
    )


class ChangeRequestInterpretIn(BaseModel):
    draft_id: str
    request_text: str = Field(..., min_length=3, max_length=2000)


class RawSessionChange(BaseModel):
    action: str = "MOVE"
    target_course: Optional[str] = None
    target_teacher: Optional[str] = None
    target_room: Optional[str] = None
    proposed_day: Optional[int] = None
    proposed_period: Optional[int] = None
    proposed_room: Optional[str] = None
    proposed_teacher: Optional[str] = None
    is_hard_constraint: bool = False
    is_term_wide: bool = True


class ResolvedSessionChange(BaseModel):
    session_id: str
    session_name: str
    course_code: str
    original_day: int
    original_period: int
    original_room_id: Optional[str] = None
    original_room_name: Optional[str] = None
    original_teacher_id: Optional[str] = None
    original_teacher_name: Optional[str] = None
    proposed_day: int
    proposed_period: int
    proposed_room_id: Optional[str] = None
    proposed_room_name: Optional[str] = None
    proposed_teacher_id: Optional[str] = None
    proposed_teacher_name: Optional[str] = None
    is_hard_constraint: bool = False
    is_term_wide: bool = True
    is_resolved: bool = True
    resolution_notes: List[str] = Field(default_factory=list)


class TimetableInterpretationResponse(BaseModel):
    success: bool
    raw_summary: str
    confidence_score: float
    is_ambiguous: bool
    ambiguities: List[AmbiguityFlag] = Field(default_factory=list)
    proposed_changes: List[ResolvedSessionChange] = Field(default_factory=list)
    draft_id: str
    draft_revision: int
    disclaimer: str = (
        "AI suggestions are unverified candidate interpretations. "
        "You must review and validate against institutional rules before applying."
    )


class ApplyInterpretedChangesIn(BaseModel):
    draft_id: str
    expected_revision: int
    changes: List[ResolvedSessionChange]


class ApplyInterpretedChangesOut(BaseModel):
    success: bool
    draft_id: str
    new_revision: int
    applied_count: int
    checker_report: Dict[str, Any]
    status: str
    message: str


class ExplainCheckerIssuesIn(BaseModel):
    draft_id: str
    violations: Optional[List[Dict[str, Any]]] = None


class CheckerIssueExplanation(BaseModel):
    rule: str
    summary: str
    root_cause_explanation: str
    potential_resolutions: List[str] = Field(default_factory=list)
    involved_sessions: List[str] = Field(default_factory=list)
    involved_resources: List[str] = Field(default_factory=list)


class ExplainCheckerIssuesOut(BaseModel):
    success: bool
    explanations: List[CheckerIssueExplanation] = Field(default_factory=list)
    general_recommendations: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Checker explanations are advisory diagnostic candidates. "
        "Institutional policies and authoritative checker rules take precedence."
    )


class ColumnMappingProposalIn(BaseModel):
    headers: List[str] = Field(..., max_length=50)
    sample_rows: Optional[List[List[str]]] = None


class ColumnMappingProposalOut(BaseModel):
    success: bool
    mappings: Dict[str, Optional[str]]
    confidences: Dict[str, float]
    ambiguities: List[str] = Field(default_factory=list)
    unmapped_headers: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Proposed column mappings must be verified by an administrator before importing data."
    )
