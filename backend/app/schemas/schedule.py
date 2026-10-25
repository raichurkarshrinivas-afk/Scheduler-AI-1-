from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TimeSlotCreate(BaseModel):
    day_of_week: str = Field(..., pattern="^(MON|TUE|WED|THU|FRI|SAT|SUN)$")
    slot_name: str = Field(..., min_length=2, max_length=50)
    start_time: str = Field(..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: str = Field(..., pattern="^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")


class TimeSlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    day_of_week: str
    slot_name: str
    start_time: str
    end_time: str


class ScheduleSessionCreate(BaseModel):
    academic_term_id: str
    course_id: str
    batch_id: str
    instructor_id: str
    classroom_id: str
    time_slot_id: str


class ScheduleSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    academic_term_id: str
    course_id: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    batch_id: str
    batch_name: Optional[str] = None
    instructor_id: str
    instructor_name: Optional[str] = None
    classroom_id: str
    classroom_name: Optional[str] = None
    time_slot_id: str
    time_slot_name: Optional[str] = None
    day_of_week: Optional[str] = None


class ConflictDetail(BaseModel):
    conflict_type: str
    message: str
    conflicting_entity_id: Optional[str] = None


class ScheduleValidationResponse(BaseModel):
    is_valid: bool
    conflicts: List[ConflictDetail] = []


class AutoScheduleRequest(BaseModel):
    academic_term_id: str


class AutoScheduleResponse(BaseModel):
    status: str
    scheduled_count: int
    unscheduled_count: int
    unscheduled_items: List[str] = []
    message: str
