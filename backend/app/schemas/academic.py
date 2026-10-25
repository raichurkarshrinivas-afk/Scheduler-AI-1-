from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AcademicTermCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    start_date: date
    end_date: date
    is_active: bool = True


class AcademicTermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    name: str
    start_date: date
    end_date: date
    is_active: bool


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=1, max_length=20)


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    name: str
    code: str


class ProgramBatchCreate(BaseModel):
    department_id: str
    name: str = Field(..., min_length=2, max_length=100)
    student_count: int = Field(default=30, gt=0)
    semester_level: int = Field(default=1, gt=0)


class ProgramBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    department_id: str
    name: str
    student_count: int
    semester_level: int
