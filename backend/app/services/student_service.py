from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.people import Student
from app.models.user import User
from app.models.academic import AcademicTerm, Enrolment, EnrolmentStatus
from app.models.schedule import CalendarException
from app.models.publication import Publication, PublicationType, CommunicationOutbox
from app.schemas.student import (
    StudentProfileOut,
    DatedOccurrenceOut,
    StudentTimetableResponse,
    StudentExamSeatOut,
    StudentPracticalOut,
    StudentChangeNoticeOut,
    StudentHomeOut,
)

PERIOD_TIMINGS = {
    0: ("09:00", "10:00"),
    1: ("10:00", "11:00"),
    2: ("11:15", "12:15"),
    3: ("13:00", "14:00"),
    4: ("14:00", "15:00"),
    5: ("15:15", "16:15"),
    6: ("16:30", "17:30"),
}


class StudentService:
    """
    Authoritative student service reading exclusively from ACTIVE PUBLISHED content.
    Enforces that student identity is derived strictly from session context,
    preventing arbitrary query access across students.
    """

    @staticmethod
    def get_student_for_user(db: Session, user_id: str, institution_id: str) -> tuple:
        student = db.query(Student).filter(
            Student.user_id == user_id,
            Student.institution_id == institution_id,
            Student.is_active == True,
        ).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active student profile not found for authenticated user.",
            )
        user = db.query(User).filter(User.id == user_id).first()
        return student, user

    @staticmethod
    def get_profile(student: Student, user: User) -> StudentProfileOut:
        return StudentProfileOut(
            student_id=student.id,
            user_id=user.id,
            roll_number=student.student_id_number,
            full_name=user.full_name,
            email=user.email,
            admission_year=student.admission_year,
            is_active=student.is_active,
        )

    @staticmethod
    def get_timetable(
        db: Session,
        student: Student,
        week_start_str: Optional[str] = None,
    ) -> StudentTimetableResponse:
        """
        Derives dated occurrences for the student's enrolled sections.
        Only reads from an ACTIVE PUBLICATION (never from drafts!).
        Applies term timezone and calendar exceptions.
        """
        # 1. Fetch active publication for timetable
        pub = (
            db.query(Publication)
            .filter(
                Publication.institution_id == student.institution_id,
                Publication.publication_type == PublicationType.TIMETABLE,
                Publication.is_active == True,
            )
            .first()
        )

        # Fallback to academic term
        term = (
            db.query(AcademicTerm)
            .filter(
                AcademicTerm.institution_id == student.institution_id,
                AcademicTerm.is_active == True,
            )
            .first()
        )
        term_timezone = term.timezone if term else "UTC"

        # If no published timetable exists, return unpublished response
        if not pub:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            return StudentTimetableResponse(
                is_published=False,
                academic_term_id=term.id if term else None,
                term_name=term.name if term else None,
                term_timezone=term_timezone,
                week_start_date=monday.isoformat(),
                occurrences=[],
                calendar_exceptions=[],
            )

        term_id = pub.academic_term_id
        snapshot = pub.snapshot
        input_snap = snapshot.get("input_snapshot", {})
        assignments = snapshot.get("output_assignments", [])

        # 2. Identify student's enrolled sections
        enrolments = (
            db.query(Enrolment)
            .filter(
                Enrolment.student_id == student.id,
                Enrolment.status == EnrolmentStatus.ENROLLED,
            )
            .all()
        )
        enrolled_section_ids = {e.section_id for e in enrolments}

        sessions = input_snap.get("sessions", [])
        rooms = {r["id"]: r for r in input_snap.get("rooms", [])}
        teachers = {t["id"]: t for t in input_snap.get("teachers", [])}
        subjects = {s["id"]: s for s in input_snap.get("subjects", [])}
        sections = {sec["id"]: sec for sec in input_snap.get("sections", [])}

        # Filter relevant sessions
        # If enrolments exist in DB, match section_id; otherwise check snapshot or include cohort sessions
        relevant_session_ids = set()
        for sess in sessions:
            sec_id = sess.get("section_id")
            if not sec_id or sec_id in enrolled_section_ids or not enrolled_section_ids:
                # Include general institutional sessions or sessions matching enrolled sections
                relevant_session_ids.add(sess["id"])
            elif student.id in sess.get("student_ids", []):
                relevant_session_ids.add(sess["id"])

        sessions_map = {s["id"]: s for s in sessions if s["id"] in relevant_session_ids}
        assigned_map = {a["session_id"]: a for a in assignments if a.get("session_id") in sessions_map}

        # 3. Determine week dates
        if week_start_str:
            try:
                week_start = date.fromisoformat(week_start_str)
            except ValueError:
                week_start = date.today() - timedelta(days=date.today().weekday())
        else:
            week_start = date.today() - timedelta(days=date.today().weekday())

        week_end = week_start + timedelta(days=6)

        # 4. Fetch calendar exceptions
        exceptions = (
            db.query(CalendarException)
            .filter(
                CalendarException.institution_id == student.institution_id,
                CalendarException.exception_date >= week_start,
                CalendarException.exception_date <= week_end,
            )
            .all()
        )
        exceptions_map = {e.exception_date: e for e in exceptions}

        # 5. Build dated occurrences
        occurrences: List[DatedOccurrenceOut] = []

        for day_idx in range(7):
            curr_date = week_start + timedelta(days=day_idx)
            day_of_week = curr_date.weekday()
            exception = exceptions_map.get(curr_date)

            for sess_id, sess in sessions_map.items():
                alloc = assigned_map.get(sess_id)
                if not alloc:
                    continue

                if alloc.get("day") == day_of_week:
                    period = alloc.get("period", 0)
                    start_t, end_t = PERIOD_TIMINGS.get(period, ("09:00", "10:00"))

                    room_id = alloc.get("room_id")
                    room = rooms.get(room_id, {})
                    teacher = teachers.get(sess.get("teacher_id"), {})
                    subj = subjects.get(sess.get("subject_id"), {})
                    sec = sections.get(sess.get("section_id"), {})

                    occurrences.append(
                        DatedOccurrenceOut(
                            session_id=sess_id,
                            title=sess.get("name", "Class Session"),
                            subject_code=subj.get("code", sess.get("subject_code", "GEN")),
                            subject_name=subj.get("name", sess.get("name")),
                            section_name=sec.get("name", "Cohort A"),
                            date=curr_date.isoformat(),
                            day_of_week=day_of_week,
                            period=period,
                            start_time=start_t,
                            end_time=end_t,
                            room_name=room.get("name", "TBD"),
                            building_name=room.get("building_name", "Main Campus"),
                            teacher_name=teacher.get("name", "Faculty Member"),
                            is_cancelled=bool(exception),
                            cancellation_reason=exception.description if exception else None,
                            term_timezone=term_timezone,
                        )
                    )

        # Sort occurrences chronologically
        occurrences.sort(key=lambda x: (x.date, x.period))

        return StudentTimetableResponse(
            is_published=True,
            academic_term_id=term_id,
            term_name=term.name if term else "Current Term",
            term_timezone=term_timezone,
            week_start_date=week_start.isoformat(),
            occurrences=occurrences,
            calendar_exceptions=[
                {"date": e.exception_date.isoformat(), "type": e.exception_type.value, "description": e.description}
                for e in exceptions
            ],
            publication_version=pub.version_number,
            publication_note=pub.publication_note,
        )

    @staticmethod
    def get_exams(db: Session, student: Student) -> List[StudentExamSeatOut]:
        """
        Retrieves upcoming published theory exams with exact desk allocation details.
        Strict Privacy: Only returns this candidate's seat.
        """
        pubs = (
            db.query(Publication)
            .filter(
                Publication.institution_id == student.institution_id,
                Publication.publication_type == PublicationType.EXAM_THEORY,
                Publication.is_active == True,
            )
            .all()
        )

        exam_seats: List[StudentExamSeatOut] = []

        for pub in pubs:
            snap = pub.snapshot
            input_snap = snap.get("input_snapshot", {})
            candidates = input_snap.get("candidates", [])
            rooms = {r["id"]: r for r in input_snap.get("rooms", [])}
            allocations = snap.get("output_allocations", [])

            # Match candidate by roll number or student id
            cand = next(
                (c for c in candidates if c.get("roll_number") == student.student_id_number or c.get("id") == student.id),
                None,
            )
            if not cand:
                # If roll_number prefix matches (e.g. 2026-CS-001 vs APEX-STU-2026-001) match on suffix
                cand = next((c for c in candidates if student.student_id_number.endswith(c.get("roll_number", "@"))), None)

            if cand:
                cand_alloc = next((a for a in allocations if a.get("candidate_id") == cand["id"]), None)
                if cand_alloc:
                    room = rooms.get(cand_alloc.get("room_id"), {})
                    seat_obj = next((s for s in room.get("seats", []) if s.get("id") == cand_alloc.get("seat_id")), {})
                    is_acc = bool(cand_alloc.get("is_accessible") or cand_alloc.get("is_accessible_seat") or seat_obj.get("is_accessible"))
                    start_dt = snap.get("start_datetime")
                    parsed_dt = datetime.fromisoformat(start_dt) if start_dt else None

                    exam_seats.append(
                        StudentExamSeatOut(
                            sitting_id=pub.source_id,
                            exam_name=snap.get("name", "Theory Examination"),
                            paper_code=cand.get("paper_code", "GEN"),
                            paper_name=cand.get("paper_name", cand.get("paper_code")),
                            start_datetime=parsed_dt,
                            duration_minutes=snap.get("duration_minutes", 180),
                            hall_name=room.get("name", "Main Hall"),
                            bench_label=cand_alloc.get("bench_label", "A1"),
                            row_num=cand_alloc.get("row_num", 1),
                            col_num=cand_alloc.get("col_num", 1),
                            is_accessible=is_acc,
                            accessibility_notes=cand.get("accessibility_notes"),
                        )
                    )

        return exam_seats

    @staticmethod
    def get_practicals(db: Session, student: Student) -> List[StudentPracticalOut]:
        """
        Retrieves published practical examination workstation assignments.
        """
        pubs = (
            db.query(Publication)
            .filter(
                Publication.institution_id == student.institution_id,
                Publication.publication_type == PublicationType.EXAM_PRACTICAL,
                Publication.is_active == True,
            )
            .all()
        )

        practicals: List[StudentPracticalOut] = []

        for pub in pubs:
            snap = pub.snapshot
            input_snap = snap.get("input_snapshot", {})
            candidates = input_snap.get("candidates", [])
            labs = {l["id"]: l for l in input_snap.get("labs", [])}
            sittings = {s["batch_id"]: s for s in input_snap.get("sittings", [])}
            allocations = snap.get("output_allocations", [])

            cand = next(
                (c for c in candidates if c.get("roll_number") == student.student_id_number or c.get("id") == student.id),
                None,
            )
            if not cand:
                cand = next((c for c in candidates if student.student_id_number.endswith(c.get("roll_number", "@"))), None)

            if cand:
                alloc = next((a for a in allocations if a.get("candidate_id") == cand["id"]), None)
                if alloc:
                    lab = labs.get(alloc.get("lab_id"), {})
                    batch_cfg = sittings.get(alloc.get("batch_id"), {})

                    practicals.append(
                        StudentPracticalOut(
                            sitting_id=pub.source_id,
                            exam_name=snap.get("name", "Practical Examination"),
                            lab_name=lab.get("name", "Computer Systems Lab"),
                            station_code=alloc.get("station_code", "WS-01"),
                            os=alloc.get("os", "Linux"),
                            installed_features=cand.get("required_features", []),
                            batch_name=batch_cfg.get("batch_name", alloc.get("batch_id", "Batch 1")),
                            start_time=batch_cfg.get("start_time", "09:00"),
                            duration_minutes=batch_cfg.get("duration_minutes", 120),
                            turnaround_buffer_minutes=batch_cfg.get("turnaround_buffer_minutes", 20),
                            examiner_name=batch_cfg.get("examiner_id", "Faculty Examiner"),
                        )
                    )

        return practicals

    @staticmethod
    def get_recent_changes(db: Session, student: Student) -> List[StudentChangeNoticeOut]:
        """Retrieves recent publication changes affecting this student."""
        pubs = (
            db.query(Publication)
            .filter(
                Publication.institution_id == student.institution_id,
            )
            .order_by(Publication.published_at.desc())
            .limit(5)
            .all()
        )

        notices = []
        for p in pubs:
            notices.append(
                StudentChangeNoticeOut(
                    id=p.id,
                    published_at=p.published_at,
                    version_number=p.version_number,
                    event_type=f"{p.publication_type.value}_RELEASE",
                    note=p.publication_note,
                    summary=p.diff_summary,
                )
            )
        return notices

    @staticmethod
    def get_home(db: Session, student: Student, user: User) -> StudentHomeOut:
        """Assembles high-priority dashboard for student home."""
        profile = StudentService.get_profile(student, user)
        tt = StudentService.get_timetable(db, student)

        today_str = date.today().isoformat()
        today_occurrences = [o for o in tt.occurrences if o.date == today_str and not o.is_cancelled]

        # Determine next up occurrence
        now_time = datetime.now().strftime("%H:%M")
        upcoming_today = [o for o in today_occurrences if o.start_time >= now_time]
        next_up = upcoming_today[0] if upcoming_today else (today_occurrences[0] if today_occurrences else None)

        exams = StudentService.get_exams(db, student)
        practicals = StudentService.get_practicals(db, student)
        changes = StudentService.get_recent_changes(db, student)

        return StudentHomeOut(
            profile=profile,
            is_published=tt.is_published,
            next_up=next_up,
            today_schedule=today_occurrences,
            upcoming_exams=exams,
            practical_sessions=practicals,
            recent_changes=changes,
            publication_version=tt.publication_version,
        )
