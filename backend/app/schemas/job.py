from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, computed_field


class JobCreate(BaseModel):
    job_type: str = Field(..., min_length=2, max_length=100)
    input_reference: Dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)


class JobCancelResponse(BaseModel):
    job_id: str
    status: str
    cancellation_requested: bool
    message: str


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    job_type: str
    input_reference: Dict[str, Any]
    status: str
    phase_label: str
    attempt_count: int
    max_attempts: int
    available_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    lease_owner: Optional[str] = None
    heartbeat_at: Optional[datetime] = None
    result_reference: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    cancellation_requested: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def elapsed_seconds(self) -> Optional[float]:
        if not self.started_at:
            return None
        end_time = self.finished_at or datetime.now(timezone.utc)
        start = self.started_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        return round(max(0.0, (end_time - start).total_seconds()), 1)
