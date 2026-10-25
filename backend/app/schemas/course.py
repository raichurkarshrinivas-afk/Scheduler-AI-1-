from pydantic import BaseModel, Field, ConfigDict


class CourseCreate(BaseModel):
    department_id: str
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    weekly_hours: int = Field(default=3, gt=0, le=20)
    course_type: str = Field(default="LECTURE")


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    department_id: str
    code: str
    name: str
    weekly_hours: int
    course_type: str


class InstructorAvailabilityCreate(BaseModel):
    instructor_id: str
    day_of_week: str
    time_slot_id: str
    is_available: bool = False
    reason: str = "Unavailable"


class InstructorAvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    instructor_id: str
    day_of_week: str
    time_slot_id: str
    is_available: bool
    reason: str
