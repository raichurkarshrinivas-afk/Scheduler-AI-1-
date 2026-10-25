from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExamSittingCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    academic_term_id: str
    exam_type: str = "THEORY"
    start_datetime: Optional[datetime] = None
    duration_minutes: int = 180
    buffer_minutes: int = 15
    input_snapshot: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SeatReassignRequest(BaseModel):
    expected_revision: int
    seat_id: Optional[str] = None
    room_id: Optional[str] = None
    target_candidate_id: Optional[str] = None


class WorkstationReassignRequest(BaseModel):
    expected_revision: int
    batch_id: Optional[str] = None
    workstation_id: Optional[str] = None
    lab_id: Optional[str] = None


class ExamSittingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    academic_term_id: str
    name: str
    exam_type: str
    status: str
    revision: int
    start_datetime: Optional[datetime] = None
    duration_minutes: int
    buffer_minutes: int
    input_snapshot: Dict[str, Any]
    parameters: Dict[str, Any]
    output_allocations: List[Dict[str, Any]]
    validation_report: Optional[Dict[str, Any]] = None
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
