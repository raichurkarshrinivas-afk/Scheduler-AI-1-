from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class PublishRequest(BaseModel):
    draft_id: str
    publication_type: str = "TIMETABLE"  # "TIMETABLE", "EXAM_THEORY", "EXAM_PRACTICAL"
    expected_revision: int
    publication_note: str = Field(default="", max_length=1000)


class PrePublishReviewOut(BaseModel):
    can_publish: bool
    draft_id: str
    revision: int
    validation_report: Dict[str, Any]
    changed_sessions_count: int
    affected_teachers_count: int
    affected_students_count: int
    unmet_preferences_count: int
    warnings: List[Dict[str, Any]]
    potential_reservation_conflicts: List[Dict[str, Any]]
    previous_active_version: Optional[int] = None


class PublicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    academic_term_id: str
    publication_type: str
    source_id: str
    version_number: int
    published_by_user_id: str
    publication_note: str
    published_at: datetime
    snapshot: Dict[str, Any]
    diff_summary: Dict[str, Any]
    checker_report: Dict[str, Any]
    is_active: bool
    created_at: datetime


class PublicationSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    publication_type: str
    version_number: int
    published_at: datetime
    publication_note: str
    is_active: bool
    publisher_name: Optional[str] = None
    change_count: int = 0


class PublicationDiffOut(BaseModel):
    source_version: int
    target_version: int
    changed_sessions: List[Dict[str, Any]]
    added_sessions: List[Dict[str, Any]]
    removed_sessions: List[Dict[str, Any]]
    affected_teachers: List[str]
    affected_sections: List[str]
