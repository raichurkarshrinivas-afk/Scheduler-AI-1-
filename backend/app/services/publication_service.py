import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.schedule import TimetableDraft
from app.models.academic import AcademicTerm
from app.models.exam import ExamSitting, ExamType
from app.models.publication import (
    Publication,
    PublicationType,
    SharedResourceReservation,
    CommunicationOutbox,
    OutboxEventStatus,
)
from app.services.schedule_checker import ScheduleChecker
from app.services.theory_seating_engine import TheorySeatingEngine
from app.services.practical_exam_engine import PracticalExamEngine


class PublicationService:
    """
    Manages controlled, transactionally safe publications, scope locking,
    active resource reservation collision checks, version diffs, and safe rollback/restores.
    """

    @staticmethod
    def calculate_timetable_diff(
        old_assignments: List[Dict[str, Any]],
        new_assignments: List[Dict[str, Any]],
        input_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculates difference between two assignment sets."""
        old_map = {a["session_id"]: a for a in old_assignments if "session_id" in a}
        new_map = {a["session_id"]: a for a in new_assignments if "session_id" in a}

        changed_sessions = []
        added_sessions = []
        removed_sessions = []
        affected_teachers = set()
        affected_sections = set()

        sessions_meta = {s["id"]: s for s in input_snapshot.get("sessions", [])}

        for sid, new_a in new_map.items():
            if sid not in old_map:
                added_sessions.append(new_a)
                s_meta = sessions_meta.get(sid, {})
                if s_meta.get("teacher_id"):
                    affected_teachers.add(s_meta["teacher_id"])
                if s_meta.get("section_id"):
                    affected_sections.add(s_meta["section_id"])
            else:
                old_a = old_map[sid]
                if (
                    old_a.get("day") != new_a.get("day")
                    or old_a.get("period") != new_a.get("period")
                    or old_a.get("room_id") != new_a.get("room_id")
                ):
                    changed_sessions.append({
                        "session_id": sid,
                        "session_name": sessions_meta.get(sid, {}).get("name", sid),
                        "before": {"day": old_a.get("day"), "period": old_a.get("period"), "room_id": old_a.get("room_id")},
                        "after": {"day": new_a.get("day"), "period": new_a.get("period"), "room_id": new_a.get("room_id")},
                    })
                    s_meta = sessions_meta.get(sid, {})
                    if s_meta.get("teacher_id"):
                        affected_teachers.add(s_meta["teacher_id"])
                    if s_meta.get("section_id"):
                        affected_sections.add(s_meta["section_id"])

        for sid, old_a in old_map.items():
            if sid not in new_map:
                removed_sessions.append(old_a)
                s_meta = sessions_meta.get(sid, {})
                if s_meta.get("teacher_id"):
                    affected_teachers.add(s_meta["teacher_id"])
                if s_meta.get("section_id"):
                    affected_sections.add(s_meta["section_id"])

        return {
            "changed_sessions": changed_sessions,
            "added_sessions": added_sessions,
            "removed_sessions": removed_sessions,
            "changed_count": len(changed_sessions) + len(added_sessions) + len(removed_sessions),
            "affected_teachers": sorted(list(affected_teachers)),
            "affected_sections": sorted(list(affected_sections)),
        }

    @staticmethod
    def pre_publish_review(db: Session, draft: TimetableDraft) -> Dict[str, Any]:
        """Provides pre-publication analysis, diff against active publication, and validation."""
        # 1. Run independent verifier
        report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)

        # 2. Find currently active publication
        prev_pub = (
            db.query(Publication)
            .filter(
                Publication.academic_term_id == draft.academic_term_id,
                Publication.publication_type == PublicationType.TIMETABLE,
                Publication.is_active == True,
            )
            .first()
        )

        old_assignments = prev_pub.snapshot.get("output_assignments", []) if prev_pub else []
        diff = PublicationService.calculate_timetable_diff(
            old_assignments, draft.output_assignments, draft.input_snapshot
        )

        # 3. Check for reservation collisions against OTHER publications
        exclude_pub_id = prev_pub.id if (prev_pub and prev_pub.source_id == draft.id) else ""
        active_reservations = (
            db.query(SharedResourceReservation)
            .filter(
                SharedResourceReservation.academic_term_id == draft.academic_term_id,
                SharedResourceReservation.is_active == True,
                SharedResourceReservation.publication_id != exclude_pub_id,
            )
            .all()
        )

        reservation_conflicts = []
        res_map = {(r.resource_id, r.day_of_week, r.period): r for r in active_reservations}
        for a in draft.output_assignments:
            key = (a.get("room_id"), a.get("day"), a.get("period"))
            if key in res_map:
                res = res_map[key]
                reservation_conflicts.append({
                    "resource_id": a.get("room_id"),
                    "day": a.get("day"),
                    "period": a.get("period"),
                    "conflicting_publication_id": res.publication_id,
                    "session_title": res.session_title,
                })

        can_publish = report["is_valid"] and len(reservation_conflicts) == 0

        return {
            "can_publish": can_publish,
            "draft_id": draft.id,
            "revision": draft.revision,
            "validation_report": report,
            "changed_sessions_count": len(diff["changed_sessions"]),
            "affected_teachers_count": len(diff["affected_teachers"]),
            "affected_students_count": len(diff["affected_sections"]),
            "unmet_preferences_count": len(report.get("warnings", [])),
            "warnings": report.get("warnings", []),
            "potential_reservation_conflicts": reservation_conflicts,
            "previous_active_version": prev_pub.version_number if prev_pub else None,
        }

    @staticmethod
    def publish_timetable(
        db: Session,
        draft: TimetableDraft,
        user_id: str,
        expected_revision: int,
        publication_note: str,
    ) -> Publication:
        """
        Executes atomic 9-step publication transaction:
        1. Authorise publisher (handled by dependency)
        2. Verify expected draft revision
        3. Lock publication scope
        4. Validate against current active shared-resource reservations
        5. Verify complete draft
        6. Write immutable publication records
        7. Update active reservations
        8. Write communication outbox events
        9. Commit
        """
        # Step 2: Verify expected draft revision
        if draft.revision != expected_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stale revision: Draft has revision {draft.revision}, but expected revision was {expected_revision}.",
            )

        # Step 3: Lock publication scope
        term = db.query(AcademicTerm).filter(AcademicTerm.id == draft.academic_term_id).with_for_update().first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic term not found.")

        # Step 4: Validate against current active shared-resource reservations from competing publications
        prev_pub = (
            db.query(Publication)
            .filter(
                Publication.academic_term_id == draft.academic_term_id,
                Publication.publication_type == PublicationType.TIMETABLE,
                Publication.is_active == True,
            )
            .first()
        )

        exclude_pub_id = prev_pub.id if (prev_pub and prev_pub.source_id == draft.id) else ""
        active_reservations = (
            db.query(SharedResourceReservation)
            .filter(
                SharedResourceReservation.academic_term_id == draft.academic_term_id,
                SharedResourceReservation.is_active == True,
                SharedResourceReservation.publication_id != exclude_pub_id,
            )
            .all()
        )

        res_map = {(r.resource_id, r.day_of_week, r.period): r for r in active_reservations}
        for a in draft.output_assignments:
            key = (a.get("room_id"), a.get("day"), a.get("period"))
            if key in res_map:
                res = res_map[key]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"RESOURCE_RESERVATION_CONFLICT: Shared resource '{key[0]}' is already reserved on Day {key[1]}, Period {key[2]} by publication '{res.publication_id}'.",
                )

        # Step 5: Verify complete draft
        report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)
        if not report["is_valid"]:
            violations_str = "; ".join(v.get("message", "Violation") for v in report.get("violations", []))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot publish draft with constraint violations: {violations_str}",
            )

        # Step 6: Write immutable publication records
        latest_pub = (
            db.query(Publication)
            .filter(
                Publication.academic_term_id == draft.academic_term_id,
                Publication.publication_type == PublicationType.TIMETABLE,
            )
            .order_by(Publication.version_number.desc())
            .first()
        )
        version_num = (latest_pub.version_number + 1) if latest_pub else 1

        old_assignments = prev_pub.snapshot.get("output_assignments", []) if prev_pub else []
        diff = PublicationService.calculate_timetable_diff(
            old_assignments, draft.output_assignments, draft.input_snapshot
        )

        if prev_pub:
            prev_pub.is_active = False

        pub = Publication(
            institution_id=draft.institution_id,
            academic_term_id=draft.academic_term_id,
            publication_type=PublicationType.TIMETABLE,
            source_id=draft.id,
            version_number=version_num,
            published_by_user_id=user_id,
            publication_note=publication_note or f"Official timetable release version {version_num}",
            published_at=datetime.now(timezone.utc),
            snapshot={
                "input_snapshot": draft.input_snapshot,
                "output_assignments": draft.output_assignments,
                "parameters": draft.parameters,
            },
            diff_summary=diff,
            checker_report=report,
            is_active=True,
        )
        db.add(pub)
        db.flush()

        draft.is_published = True
        draft.published_at = pub.published_at
        draft.status = "PUBLISHED"

        # Step 7: Update active reservations
        if prev_pub:
            db.query(SharedResourceReservation).filter(
                SharedResourceReservation.publication_id == prev_pub.id
            ).update({"is_active": False})

        rooms_meta = {r["id"]: r for r in draft.input_snapshot.get("rooms", [])}
        sessions_meta = {s["id"]: s for s in draft.input_snapshot.get("sessions", [])}

        for a in draft.output_assignments:
            s_meta = sessions_meta.get(a.get("session_id"), {})
            res = SharedResourceReservation(
                institution_id=draft.institution_id,
                academic_term_id=draft.academic_term_id,
                publication_id=pub.id,
                resource_type="ROOM",
                resource_id=a.get("room_id"),
                day_of_week=a.get("day"),
                period=a.get("period"),
                session_title=s_meta.get("name", "Session"),
                is_active=True,
            )
            db.add(res)

        # Step 8: Write communication outbox events (NO external I/O!)
        outbox_event = CommunicationOutbox(
            institution_id=draft.institution_id,
            publication_id=pub.id,
            event_type="TIMETABLE_PUBLISHED",
            recipient_role="ALL",
            payload={
                "version_number": version_num,
                "publication_note": pub.publication_note,
                "affected_teachers": diff.get("affected_teachers", []),
                "affected_sections": diff.get("affected_sections", []),
                "changed_count": diff.get("changed_count", 0),
            },
            status=OutboxEventStatus.PENDING,
        )
        db.add(outbox_event)

        # Step 9: Commit
        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def publish_exam_sitting(
        db: Session,
        sitting: ExamSitting,
        user_id: str,
        expected_revision: int,
        publication_note: str,
    ) -> Publication:
        """
        Executes atomic publication for theory seating or practical workstations.
        """
        if sitting.revision != expected_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Stale revision: Exam sitting has revision {sitting.revision}, expected {expected_revision}.",
            )

        term = db.query(AcademicTerm).filter(AcademicTerm.id == sitting.academic_term_id).with_for_update().first()
        if not term:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Academic term not found.")

        # Independent verification
        if sitting.exam_type == ExamType.THEORY:
            report = TheorySeatingEngine.verify_theory_seating(sitting.input_snapshot, sitting.output_allocations)
            pub_type = PublicationType.EXAM_THEORY
        else:
            report = PracticalExamEngine.verify_practical_allocation(sitting.input_snapshot, sitting.output_allocations)
            pub_type = PublicationType.EXAM_PRACTICAL

        if not report["is_valid"]:
            violations = "; ".join(v.get("message", "Violation") for v in report.get("violations", []))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot publish exam sitting with constraint violations: {violations}",
            )

        prev_pub = (
            db.query(Publication)
            .filter(
                Publication.academic_term_id == sitting.academic_term_id,
                Publication.publication_type == pub_type,
                Publication.source_id == sitting.id,
                Publication.is_active == True,
            )
            .first()
        )

        latest_pub = (
            db.query(Publication)
            .filter(
                Publication.academic_term_id == sitting.academic_term_id,
                Publication.publication_type == pub_type,
            )
            .order_by(Publication.version_number.desc())
            .first()
        )
        version_num = (latest_pub.version_number + 1) if latest_pub else 1

        if prev_pub:
            prev_pub.is_active = False

        pub = Publication(
            institution_id=sitting.institution_id,
            academic_term_id=sitting.academic_term_id,
            publication_type=pub_type,
            source_id=sitting.id,
            version_number=version_num,
            published_by_user_id=user_id,
            publication_note=publication_note or f"Official exam release version {version_num}",
            published_at=datetime.now(timezone.utc),
            snapshot={
                "name": sitting.name,
                "start_datetime": sitting.start_datetime.isoformat() if sitting.start_datetime else None,
                "duration_minutes": sitting.duration_minutes,
                "buffer_minutes": sitting.buffer_minutes,
                "input_snapshot": sitting.input_snapshot,
                "output_allocations": sitting.output_allocations,
            },
            diff_summary={"allocated_count": len(sitting.output_allocations)},
            checker_report=report,
            is_active=True,
        )
        db.add(pub)
        db.flush()

        sitting.is_published = True
        sitting.published_at = pub.published_at
        sitting.status = "PUBLISHED"

        outbox_event = CommunicationOutbox(
            institution_id=sitting.institution_id,
            publication_id=pub.id,
            event_type="EXAM_PUBLISHED",
            recipient_role="STUDENT",
            payload={"version_number": version_num, "sitting_name": sitting.name},
            status=OutboxEventStatus.PENDING,
        )
        db.add(outbox_event)

        db.commit()
        db.refresh(pub)
        return pub

    @staticmethod
    def restore_publication_as_draft(
        db: Session,
        publication_id: str,
        user_id: str,
    ) -> TimetableDraft:
        """
        Restores an old publication as a NEW draft:
        - NEVER deletes publication history!
        - Clones snapshot and assignments into a new draft with revision 1
        - Re-validates restored content using independent checker
        - Marks status as DRAFT / CHECKED so it must be reviewed before publishing
        """
        pub = db.query(Publication).filter(Publication.id == publication_id).first()
        if not pub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication record not found.")

        if pub.publication_type != PublicationType.TIMETABLE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only timetable publications can be restored via this endpoint.")

        input_snapshot = pub.snapshot.get("input_snapshot", {})
        output_assignments = pub.snapshot.get("output_assignments", [])
        parameters = pub.snapshot.get("parameters", {})

        input_hash = hashlib.sha256(json.dumps(input_snapshot, sort_keys=True).encode()).hexdigest()

        # Independent re-validation of restored content
        report = ScheduleChecker.validate(input_snapshot, output_assignments)

        new_draft = TimetableDraft(
            institution_id=pub.institution_id,
            academic_term_id=pub.academic_term_id,
            name=f"Restored from Publication Version {pub.version_number}",
            status="CHECKED" if report["is_valid"] else "INVALID",
            revision=1,
            input_hash=input_hash,
            input_snapshot=input_snapshot,
            parameters=parameters,
            output_assignments=output_assignments,
            validation_report=report,
            is_published=False,
        )
        db.add(new_draft)
        db.commit()
        db.refresh(new_draft)
        return new_draft
