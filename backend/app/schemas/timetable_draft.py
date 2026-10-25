from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TimetableDraftCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    academic_term_id: str
    input_snapshot: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TimetableDraftGenerateResponse(BaseModel):
    draft_id: str
    job_id: str
    status: str
    message: str


class AssignmentUpdate(BaseModel):
    expected_revision: int
    day: Optional[int] = None
    period: Optional[int] = None
    start_period: Optional[int] = None
    room_id: Optional[str] = None
    is_locked: Optional[bool] = None


class RepairRequest(BaseModel):
    expected_revision: int
    time_limit_seconds: Optional[int] = 30


class AssignmentChange(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    teacher_id: Optional[str] = None
    section_id: Optional[str] = None
    before: Dict[str, Any]
    after: Dict[str, Any]
    time_moved: bool
    room_changed: bool
    reason: str


class RepairResponse(BaseModel):
    draft_id: str
    revision: int
    status: str
    is_valid: bool
    changes: List[AssignmentChange]
    change_count: int
    validation_report: Optional[Dict[str, Any]] = None
    output_assignments: List[Dict[str, Any]]


class TimetableDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    academic_term_id: str
    name: str
    status: str
    revision: int = 1
    input_hash: str
    input_snapshot: Dict[str, Any]
    parameters: Dict[str, Any]
    output_assignments: List[Dict[str, Any]]
    solver_status: Optional[str] = None
    solver_runtime_seconds: Optional[float] = None
    solver_objective: Optional[float] = None
    solver_best_bound: Optional[float] = None
    model_version: str
    rule_version: str
    checker_version: str
    solver_version: str
    validation_report: Optional[Dict[str, Any]] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime
