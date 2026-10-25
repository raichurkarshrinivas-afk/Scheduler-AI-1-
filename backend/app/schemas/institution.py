from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    is_active: bool
    created_at: datetime


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
