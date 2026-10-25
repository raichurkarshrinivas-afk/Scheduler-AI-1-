from pydantic import BaseModel, Field, ConfigDict


class ClassroomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    building: str = Field(..., min_length=1, max_length=100)
    room_number: str = Field(..., min_length=1, max_length=50)
    capacity: int = Field(..., gt=0)
    room_type: str = Field(default="LECTURE_HALL")
    rows: int = Field(default=5, gt=0)
    columns: int = Field(default=6, gt=0)


class ClassroomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    name: str
    building: str
    room_number: str
    capacity: int
    room_type: str
    rows: int
    columns: int
