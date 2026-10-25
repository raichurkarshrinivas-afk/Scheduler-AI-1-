from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.user import UserRole


class LoginRequest(BaseModel):
    institution_code: str = Field(..., min_length=2, max_length=50, description="Institution code, e.g. APEX")
    identifier: str = Field(..., min_length=2, max_length=255, description="Email, Teacher Employee ID, or Student Roll Number/PRN")
    password: str = Field(..., min_length=1, description="Account password")


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    must_change_password: bool
    role: UserRole
    institution_id: str
    institution_name: str
    institution_code: str
    teacher_id: Optional[str] = None
    student_id: Optional[str] = None
    employee_id: Optional[str] = None
    roll_number: Optional[str] = None


class LoginResponse(BaseModel):
    user: UserProfile
    csrf_token: str
    must_change_password: bool
    message: str = "Login successful"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class SessionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    is_current: bool = False


class AdminResetPasswordRequest(BaseModel):
    temporary_password: Optional[str] = None


class AdminResetPasswordResponse(BaseModel):
    user_id: str
    temporary_password: str
    must_change_password: bool = True
    message: str = "Password successfully reset. User must change password on next login."


# Backward-compatibility aliases for legacy draft schema references
class InstitutionRegisterRequest(BaseModel):
    institution_name: str = Field(..., min_length=2, max_length=200)
    institution_slug: str = Field(..., min_length=2, max_length=100)
    admin_name: str = Field(..., min_length=2, max_length=255)
    admin_email: str
    password: str = Field(..., min_length=6, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: str
    role: str
    institution_id: str
    institution_name: Optional[str] = None
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
