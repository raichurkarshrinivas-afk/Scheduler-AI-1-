from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: str
    user_id: str
    roll_number: str
    full_name: str
    email: str
    department_name: Optional[str] = None
    admission_year: int
    is_active: bool


class DatedOccurrenceOut(BaseModel):
    session_id: str
    title: str
    subject_code: str
    subject_name: Optional[str] = None
    section_name: Optional[str] = None
    date: str  # YYYY-MM-DD
    day_of_week: int  # 0 = Monday ... 6 = Sunday
    period: int
    start_time: str
    end_time: str
    room_name: str
    building_name: Optional[str] = None
    teacher_name: str
    is_cancelled: bool = False
    cancellation_reason: Optional[str] = None
    term_timezone: str


class StudentTimetableResponse(BaseModel):
    is_published: bool
    academic_term_id: Optional[str] = None
    term_name: Optional[str] = None
    term_timezone: str = "UTC"
    week_start_date: str
    occurrences: List[DatedOccurrenceOut]
    calendar_exceptions: List[Dict[str, Any]]
    publication_version: Optional[int] = None
    publication_note: Optional[str] = None


class StudentExamSeatOut(BaseModel):
    sitting_id: str
    exam_name: str
    paper_code: str
    paper_name: Optional[str] = None
    start_datetime: Optional[datetime] = None
    duration_minutes: int
    hall_name: str
    bench_label: str
    row_num: int
    col_num: int
    is_accessible: bool
    accessibility_notes: Optional[str] = None


class StudentPracticalOut(BaseModel):
    sitting_id: str
    exam_name: str
    lab_name: str
    station_code: str
    os: Optional[str] = None
    installed_features: List[str] = []
    batch_name: str
    start_time: str
    duration_minutes: int
    turnaround_buffer_minutes: int
    examiner_name: Optional[str] = None


class StudentChangeNoticeOut(BaseModel):
    id: str
    published_at: datetime
    version_number: int
    event_type: str
    note: str
    summary: Dict[str, Any]


class StudentHomeOut(BaseModel):
    profile: StudentProfileOut
    is_published: bool
    next_up: Optional[DatedOccurrenceOut] = None
    today_schedule: List[DatedOccurrenceOut] = []
    upcoming_exams: List[StudentExamSeatOut] = []
    practical_sessions: List[StudentPracticalOut] = []
    recent_changes: List[StudentChangeNoticeOut] = []
    publication_version: Optional[int] = None
