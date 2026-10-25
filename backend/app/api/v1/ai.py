from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    require_roles,
    verify_csrf_token,
)
from app.models.user import UserRole, Membership
from app.schemas.ai import (
    AIStatusOut,
    ChangeRequestInterpretIn,
    TimetableInterpretationResponse,
    ApplyInterpretedChangesIn,
    ApplyInterpretedChangesOut,
    ExplainCheckerIssuesIn,
    ExplainCheckerIssuesOut,
    ColumnMappingProposalIn,
    ColumnMappingProposalOut,
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Interpretation"])


@router.get("/status", response_model=AIStatusOut)
def get_ai_status(
    membership: Membership = Depends(get_current_membership),
):
    """
    Returns the operational configuration, provider status, and cost metrics for AI interpretation.
    Clearly signals whether AI features are enabled, mock, or disabled.
    """
    return AIService.get_status()


@router.post(
    "/interpret-change",
    response_model=TimetableInterpretationResponse,
    status_code=status.HTTP_200_OK,
)
def interpret_timetable_change(
    payload: ChangeRequestInterpretIn,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Interprets natural language timetable change requests into typed structured modifications.
    Enforces privacy scrubbing, entity resolution, and explicit ambiguity identification.
    Does NOT modify the draft or publish anything.
    """
    return AIService.interpret_timetable_change(
        draft_id=payload.draft_id,
        request_text=payload.request_text,
        membership=membership,
        db=db,
    )


@router.post(
    "/apply-change",
    response_model=ApplyInterpretedChangesOut,
    status_code=status.HTTP_200_OK,
)
def apply_interpreted_change(
    payload: ApplyInterpretedChangesIn,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Applies user-approved interpreted changes to the timetable draft.
    Requires optimistic revision match (409 on stale draft).
    Executes authoritative schedule checker validation and records an immutable audit log.
    Never publishes automatically.
    """
    return AIService.apply_interpreted_changes(
        draft_id=payload.draft_id,
        expected_revision=payload.expected_revision,
        changes=payload.changes,
        membership=membership,
        db=db,
    )


@router.post(
    "/explain-checker",
    response_model=ExplainCheckerIssuesOut,
    status_code=status.HTTP_200_OK,
)
def explain_checker_issues(
    payload: ExplainCheckerIssuesIn,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Generates plain-language explanations of solver/checker conflict issues and candidate resolutions.
    Explicitly clarifies that candidate suggestions are advisory diagnostics, not verified fixes.
    """
    return AIService.explain_checker_issues(
        draft_id=payload.draft_id,
        violations=payload.violations,
        membership=membership,
        db=db,
    )


@router.post(
    "/propose-mappings",
    response_model=ColumnMappingProposalOut,
    status_code=status.HTTP_200_OK,
)
def propose_column_mappings(
    payload: ColumnMappingProposalIn,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
):
    """
    Proposes database schema column mappings for raw tabular import files.
    Identifies unmapped columns and flags ambiguities for administrator verification.
    """
    return AIService.propose_column_mappings(
        headers=payload.headers,
        sample_rows=payload.sample_rows,
        membership=membership,
    )
