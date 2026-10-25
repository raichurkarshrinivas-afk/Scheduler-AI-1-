from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ExamSessionCreate(BaseModel):
    academic_term_id: str
    name: str = Field(..., min_length=2, max_length=150)
    exam_date: date
    time_slot_id: str


class ExamSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    academic_term_id: str
    name: str
    exam_date: date
    time_slot_id: str
    status: str


class ExamEnrollmentCreate(BaseModel):
    student_id: str
    course_id: str


class ExamEnrollmentBulkCreate(BaseModel):
    enrollments: List[ExamEnrollmentCreate]


class GenerateSeatingRequest(BaseModel):
    classroom_ids: List[str] = Field(..., min_length=1)


class SeatAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    exam_session_id: str
    classroom_id: str
    classroom_name: Optional[str] = None
    student_id: str
    student_name: Optional[str] = None
    course_id: str
    course_code: Optional[str] = None
    seat_row: int
    seat_col: int
    desk_label: str


class SeatCell(BaseModel):
    row: int
    col: int
    desk_label: str
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    course_code: Optional[str] = None
    is_occupied: bool


class RoomGridOut(BaseModel):
    classroom_id: str
    classroom_name: str
    building: str
    room_number: str
    rows: int
    columns: int
    total_seats: int
    occupied_seats: int
    grid: List[List[SeatCell]]


class SeatingArrangementReport(BaseModel):
    exam_session_id: str
    exam_name: str
    exam_date: date
    total_students: int
    total_seated: int
    rooms: List[RoomGridOut]
