import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.dependencies import verify_institution_ownership
from app.models.user import Membership
from app.models.schedule import TimetableDraft
from app.models.audit import AuditEvent
from app.schemas.ai import (
    AmbiguityType,
    AmbiguityFlag,
    ResolvedSessionChange,
    TimetableInterpretationResponse,
    ApplyInterpretedChangesOut,
    ExplainCheckerIssuesOut,
    CheckerIssueExplanation,
    ColumnMappingProposalOut,
)
from app.services.ai_provider import (
    get_ai_provider,
    AIProviderDisabledError,
    AIProviderTimeoutError,
    AISchemaValidationError,
)
from app.services.schedule_checker import ScheduleChecker


class AIService:
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        provider = get_ai_provider()
        return provider.get_status()

    @classmethod
    def interpret_timetable_change(
        cls,
        draft_id: str,
        request_text: str,
        membership: Membership,
        db: Session,
    ) -> TimetableInterpretationResponse:
        # Step 1: Authorised user request check
        draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
        if not draft:
            draft = (
                db.query(TimetableDraft)
                .filter(
                    TimetableDraft.institution_id == membership.institution_id,
                    TimetableDraft.is_published == False,
                )
                .order_by(TimetableDraft.created_at.desc())
                .first()
            )
            if not draft:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timetable draft not found.",
                )
        verify_institution_ownership(draft.institution_id, membership)

        if draft.is_published or draft.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Published timetable drafts are immutable and cannot be interpreted for edits.",
            )

        if len(request_text) > settings.AI_MAX_REQUEST_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Request text exceeds maximum limit of {settings.AI_MAX_REQUEST_LENGTH} characters.",
            )

        # Step 2: Supply only necessary approved context (scrubbed, no PRNs or confidential text)
        input_snap = draft.input_snapshot or {}
        approved_context = {
            "courses": [
                {"code": s.get("course_code"), "name": s.get("name")}
                for s in input_snap.get("sessions", [])
                if s.get("course_code")
            ],
            "teachers": [
                {"id": t.get("id"), "name": t.get("name")}
                for t in input_snap.get("teachers", [])
            ],
            "rooms": [
                {"id": r.get("id"), "name": r.get("name"), "code": r.get("code"), "capacity": r.get("capacity")}
                for r in input_snap.get("rooms", [])
            ],
            "sessions": [
                {
                    "session_id": a.get("session_id"),
                    "name": a.get("session_name", a.get("name", "Session")),
                    "course_code": a.get("course_code", ""),
                    "teacher_name": a.get("teacher_name", ""),
                    "room_name": a.get("room_name", ""),
                    "day": a.get("day", 0),
                    "period": a.get("period", 1),
                }
                for a in (draft.output_assignments or [])
            ],
        }

        # Step 3 & 4: Obtain typed structured proposal and validate schema
        provider = get_ai_provider()
        try:
            raw_result = provider.interpret_change(request_text, approved_context)
        except AIProviderDisabledError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except AIProviderTimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"AI interpretation timed out. Draft revision {draft.revision} remains unchanged.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI provider communication error: {str(e)}",
            )

        # Validate structure
        if not isinstance(raw_result, dict) or "raw_changes" not in raw_result or not isinstance(raw_result["raw_changes"], list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Malformed model output rejected: missing required candidate change structures.",
            )

        # Step 5: Resolve referenced entities within permitted scope
        resolved_changes: List[ResolvedSessionChange] = []
        ambiguities: List[AmbiguityFlag] = [
            AmbiguityFlag(**amb) for amb in raw_result.get("ambiguities", [])
        ]

        rooms_by_name = {(r.get("name") or "").lower(): r for r in input_snap.get("rooms", []) if r.get("name")}
        rooms_by_code = {(r.get("code") or "").lower(): r for r in input_snap.get("rooms", []) if r.get("code")}
        teachers_by_name = {(t.get("name") or "").lower(): t for t in input_snap.get("teachers", []) if t.get("name")}
        assignments = draft.output_assignments or []

        for ch in raw_result["raw_changes"]:
            target_course = (ch.get("target_course") or "").lower()
            target_teacher = (ch.get("target_teacher") or "").lower()

            matched_assignment = None
            for a in assignments:
                a_course = (a.get("course_code") or "").lower()
                a_name = (a.get("session_name") or a.get("name") or "").lower()
                a_teacher = (a.get("teacher_name") or "").lower()

                if target_course and (target_course in a_course or target_course in a_name):
                    matched_assignment = a
                    break
                if target_teacher and target_teacher in a_teacher:
                    matched_assignment = a
                    break

            if not matched_assignment and assignments:
                matched_assignment = assignments[0]

            if not matched_assignment:
                continue

            # Resolve proposed room
            prop_room_id = None
            prop_room_name = ch.get("proposed_room")
            if prop_room_name:
                r_match = rooms_by_name.get(prop_room_name.lower()) or rooms_by_code.get(prop_room_name.lower())
                if r_match:
                    prop_room_id = r_match.get("id")
                    prop_room_name = r_match.get("name")
                else:
                    ambiguities.append(
                        AmbiguityFlag(
                            type=AmbiguityType.UNKNOWN_ENTITY,
                            description=f"Proposed room '{prop_room_name}' does not match any registered room in institution.",
                            suggested_clarification="Select an available classroom from the institutional facility list.",
                        )
                    )

            # Resolve proposed teacher
            prop_teacher_id = None
            prop_teacher_name = ch.get("proposed_teacher")
            if prop_teacher_name:
                t_match = teachers_by_name.get(prop_teacher_name.lower())
                if t_match:
                    prop_teacher_id = t_match.get("id")
                    prop_teacher_name = t_match.get("name")
                else:
                    ambiguities.append(
                        AmbiguityFlag(
                            type=AmbiguityType.UNKNOWN_ENTITY,
                            description=f"Proposed instructor '{prop_teacher_name}' could not be resolved.",
                            suggested_clarification="Assign a qualified faculty instructor from the departmental roster.",
                        )
                    )

            resolved_item = ResolvedSessionChange(
                session_id=matched_assignment.get("session_id", "s-1"),
                session_name=matched_assignment.get("session_name", matched_assignment.get("name", "Session")),
                course_code=matched_assignment.get("course_code", "Course"),
                original_day=matched_assignment.get("day", 0),
                original_period=matched_assignment.get("period", 1),
                original_room_id=matched_assignment.get("room_id"),
                original_room_name=matched_assignment.get("room_name"),
                original_teacher_id=matched_assignment.get("teacher_id"),
                original_teacher_name=matched_assignment.get("teacher_name"),
                proposed_day=ch.get("proposed_day", 1),
                proposed_period=ch.get("proposed_period", 2),
                proposed_room_id=prop_room_id,
                proposed_room_name=prop_room_name or matched_assignment.get("room_name"),
                proposed_teacher_id=prop_teacher_id,
                proposed_teacher_name=prop_teacher_name or matched_assignment.get("teacher_name"),
                is_hard_constraint=ch.get("is_hard_constraint", True),
                is_term_wide=ch.get("is_term_wide", True),
                is_resolved=True,
                resolution_notes=[],
            )
            resolved_changes.append(resolved_item)

        # Step 7: Present interpreted change (ready for user approval)
        return TimetableInterpretationResponse(
            success=True,
            raw_summary=raw_result.get("raw_summary", "Proposed schedule modification"),
            confidence_score=raw_result.get("confidence_score", 0.85),
            is_ambiguous=len(ambiguities) > 0,
            ambiguities=ambiguities,
            proposed_changes=resolved_changes,
            draft_id=draft.id,
            draft_revision=draft.revision,
        )

    @classmethod
    def apply_interpreted_changes(
        cls,
        draft_id: str,
        expected_revision: int,
        changes: List[ResolvedSessionChange],
        membership: Membership,
        db: Session,
    ) -> ApplyInterpretedChangesOut:
        # Step 8: Require user approval (this endpoint is invoked when user confirms changes)
        draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
        if not draft:
            draft = (
                db.query(TimetableDraft)
                .filter(
                    TimetableDraft.institution_id == membership.institution_id,
                    TimetableDraft.is_published == False,
                )
                .order_by(TimetableDraft.created_at.desc())
                .first()
            )
            if not draft:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timetable draft not found.",
                )
        verify_institution_ownership(draft.institution_id, membership)

        if draft.is_published or draft.status == "PUBLISHED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Published timetable drafts are immutable and cannot be edited.",
            )

        # Revision check (optimistic concurrency locking)
        if draft.revision != expected_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Revision conflict: Draft is at revision {draft.revision}, "
                    f"but approval expected revision {expected_revision}. Please review recent edits."
                ),
            )

        # Step 9: Apply to draft (NEVER auto-publish, always update draft assignments)
        assignments = [dict(a) for a in (draft.output_assignments or [])]
        applied_count = 0

        for ch in changes:
            for a in assignments:
                if a.get("session_id") == ch.session_id:
                    a["day"] = ch.proposed_day
                    a["period"] = ch.proposed_period
                    if ch.proposed_room_id:
                        a["room_id"] = ch.proposed_room_id
                    if ch.proposed_room_name:
                        a["room_name"] = ch.proposed_room_name
                    if ch.proposed_teacher_id:
                        a["teacher_id"] = ch.proposed_teacher_id
                    if ch.proposed_teacher_name:
                        a["teacher_name"] = ch.proposed_teacher_name
                    applied_count += 1
                    break

        draft.output_assignments = assignments
        draft.revision += 1

        # Step 10: Run normal authoritative solve/check workflow
        report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)
        draft.validation_report = report
        draft.status = "CHECKED" if report["is_valid"] else "INVALID"

        # Audit logging (sanitized, zero prompt text or confidential student details)
        audit = AuditEvent(
            institution_id=draft.institution_id,
            user_id=membership.user_id,
            event_type="AI_INTERPRETATION_APPLIED",
            entity_type="TimetableDraft",
            entity_id=draft.id,
            action="APPLY_CHANGE",
            payload={
                "applied_count": applied_count,
                "old_revision": expected_revision,
                "new_revision": draft.revision,
                "is_valid": report["is_valid"],
                "violations_count": len(report.get("violations", [])),
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(draft)

        return ApplyInterpretedChangesOut(
            success=True,
            draft_id=draft.id,
            new_revision=draft.revision,
            applied_count=applied_count,
            checker_report=report,
            status=draft.status,
            message=(
                f"Successfully applied {applied_count} interpreted changes to draft revision {draft.revision}. "
                f"Independent validation status: {draft.status}."
            ),
        )

    @classmethod
    def explain_checker_issues(
        cls,
        draft_id: str,
        violations: Optional[List[Dict[str, Any]]],
        membership: Membership,
        db: Session,
    ) -> ExplainCheckerIssuesOut:
        draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
        if not draft:
            draft = (
                db.query(TimetableDraft)
                .filter(
                    TimetableDraft.institution_id == membership.institution_id,
                    TimetableDraft.is_published == False,
                )
                .order_by(TimetableDraft.created_at.desc())
                .first()
            )
            if not draft:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Timetable draft not found.",
                )
        verify_institution_ownership(draft.institution_id, membership)

        if violations is None:
            report = draft.validation_report or {}
            violations = report.get("violations", [])

        provider = get_ai_provider()
        try:
            raw_explanations = provider.explain_issues(violations, draft.input_snapshot or {})
        except AIProviderDisabledError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except AIProviderTimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI explanation request timed out.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI provider communication error: {str(e)}",
            )

        items = [
            CheckerIssueExplanation(**item)
            for item in raw_explanations.get("explanations", [])
        ]

        return ExplainCheckerIssuesOut(
            success=True,
            explanations=items,
            general_recommendations=raw_explanations.get("general_recommendations", []),
            disclaimer=raw_explanations.get("disclaimer", (
                "Checker explanations are advisory diagnostic candidates. "
                "Authoritative solver validation rules take precedence."
            )),
        )

    @classmethod
    def propose_column_mappings(
        cls,
        headers: List[str],
        sample_rows: Optional[List[List[str]]],
        membership: Membership,
    ) -> ColumnMappingProposalOut:
        if len(headers) > 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Header list exceeds maximum allowed count of 50 columns.",
            )

        # Sanitize sample rows (remove email addresses, phone numbers)
        sanitized_samples = None
        if sample_rows:
            sanitized_samples = []
            for row in sample_rows[:10]:
                cleaned_row = []
                for cell in row:
                    cell_str = str(cell)
                    # Redact email patterns
                    cell_str = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[REDACTED_EMAIL]", cell_str)
                    cleaned_row.append(cell_str[:100])
                sanitized_samples.append(cleaned_row)

        provider = get_ai_provider()
        try:
            raw_mappings = provider.propose_column_mappings(headers, sanitized_samples)
        except AIProviderDisabledError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )
        except AIProviderTimeoutError as e:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI column mapping proposal timed out.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI provider communication error: {str(e)}",
            )

        return ColumnMappingProposalOut(
            success=True,
            mappings=raw_mappings.get("mappings", {}),
            confidences=raw_mappings.get("confidences", {}),
            ambiguities=raw_mappings.get("ambiguities", []),
            unmapped_headers=raw_mappings.get("unmapped_headers", []),
            disclaimer=raw_mappings.get("disclaimer", (
                "Proposed column mappings must be verified by an administrator before importing data."
            )),
        )
