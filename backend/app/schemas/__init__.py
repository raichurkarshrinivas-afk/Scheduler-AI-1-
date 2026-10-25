from app.schemas.auth import (
    InstitutionRegisterRequest,
    LoginRequest,
    UserOut,
    TokenResponse,
)
from app.schemas.institution import InstitutionOut, InstitutionUpdate
from app.schemas.facility import ClassroomCreate, ClassroomOut
from app.schemas.academic import (
    AcademicTermCreate,
    AcademicTermOut,
    DepartmentCreate,
    DepartmentOut,
    ProgramBatchCreate,
    ProgramBatchOut,
)
from app.schemas.course import (
    CourseCreate,
    CourseOut,
    InstructorAvailabilityCreate,
    InstructorAvailabilityOut,
)
from app.schemas.schedule import (
    TimeSlotCreate,
    TimeSlotOut,
    ScheduleSessionCreate,
    ScheduleSessionOut,
    ConflictDetail,
    ScheduleValidationResponse,
    AutoScheduleRequest,
    AutoScheduleResponse,
)
from app.schemas.seating import (
    ExamSessionCreate,
    ExamSessionOut,
    ExamEnrollmentCreate,
    ExamEnrollmentBulkCreate,
    GenerateSeatingRequest,
    SeatAssignmentOut,
    SeatCell,
    RoomGridOut,
    SeatingArrangementReport,
)

__all__ = [
    "InstitutionRegisterRequest",
    "LoginRequest",
    "UserOut",
    "TokenResponse",
    "InstitutionOut",
    "InstitutionUpdate",
    "ClassroomCreate",
    "ClassroomOut",
    "AcademicTermCreate",
    "AcademicTermOut",
    "DepartmentCreate",
    "DepartmentOut",
    "ProgramBatchCreate",
    "ProgramBatchOut",
    "CourseCreate",
    "CourseOut",
    "InstructorAvailabilityCreate",
    "InstructorAvailabilityOut",
    "TimeSlotCreate",
    "TimeSlotOut",
    "ScheduleSessionCreate",
    "ScheduleSessionOut",
    "ConflictDetail",
    "ScheduleValidationResponse",
    "AutoScheduleRequest",
    "AutoScheduleResponse",
    "ExamSessionCreate",
    "ExamSessionOut",
    "ExamEnrollmentCreate",
    "ExamEnrollmentBulkCreate",
    "GenerateSeatingRequest",
    "SeatAssignmentOut",
    "SeatCell",
    "RoomGridOut",
    "SeatingArrangementReport",
]

from app.schemas.job import JobCreate, JobOut, JobCancelResponse

from app.schemas.timetable_draft import TimetableDraftCreate, TimetableDraftOut, TimetableDraftGenerateResponse
