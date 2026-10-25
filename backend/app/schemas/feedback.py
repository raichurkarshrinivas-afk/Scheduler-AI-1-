import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PublicContactCreate(BaseModel):
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[str] = Field(None, max_length=255)
    category: str = Field("GENERAL_INQUIRY", max_length=50)
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    honeypot: Optional[str] = None


class PublicContactResponse(BaseModel):
    success: bool
    reference_code: str
    message: str


class AuthenticatedFeedbackCreate(BaseModel):
    category: str = Field(..., max_length=50)
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    page_reference: Optional[str] = Field(None, max_length=255)


class FeedbackInternalNoteCreate(BaseModel):
    note: str = Field(..., min_length=1, max_length=3000)


class FeedbackInternalNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author_user_id: str
    author_name: Optional[str] = None
    note: str
    created_at: datetime.datetime


class FeedbackSubmissionUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_code: str
    category: str
    subject: str
    message: str
    page_reference: Optional[str] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class FeedbackSubmissionManageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference_code: str
    institution_id: Optional[str] = None
    submitting_user_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    category: str
    subject: str
    message: str
    page_reference: Optional[str] = None
    status: str
    assigned_reviewer_id: Optional[str] = None
    assigned_reviewer_name: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    internal_notes: List[FeedbackInternalNoteResponse] = []


class FeedbackManageListResponse(BaseModel):
    items: List[FeedbackSubmissionManageResponse]
    total: int


class FeedbackStatusUpdate(BaseModel):
    status: str
    assigned_reviewer_id: Optional[str] = None
