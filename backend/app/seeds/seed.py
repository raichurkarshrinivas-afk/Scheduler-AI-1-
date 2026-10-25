import os
import sys
import secrets
from datetime import date, time, datetime, timezone

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.institution import Institution
from app.models.user import User, Membership, UserRole
from app.models.academic import (
    Department,
    AcademicTerm,
    Subject,
    SubjectType,
    CourseOffering,
    Section,
    Enrolment,
    EnrolmentStatus,
)
from app.models.people import Teacher, Student, TeacherQualification
from app.models.facility import Building, Room, RoomType, Seat, Workstation
from app.models.schedule import (
    Session,
    SessionType,
    SessionStatus,
    AvailabilityRule,
    TargetType,
    CalendarException,
    CalendarExceptionType,
    ConstraintRule,
    ConstraintType,
)
from app.models.audit import AuditEvent


def run_seed(db=None):
    """Executes the idempotent database seed.
    Can be run repeatedly without duplicating records or throwing constraint violations.
    """
    is_external_session = db is not None
    if not is_external_session:
        db = SessionLocal()

    try:
        # Determine development credentials
        seed_pwd = os.getenv("SEED_PASSWORD") or os.getenv("DEFAULT_ADMIN_PASSWORD")
        if not seed_pwd:
            seed_pwd = "DevSeed2026!#"
            print(f"[SECURITY NOTICE] SEED_PASSWORD not set. Using default dev password: '{seed_pwd}'")
            print("[SECURITY NOTICE] Never use this password in production or public environments.")
        else:
            print("[SEED] Using password provided via environment variable.")

        hashed_pwd = get_password_hash(seed_pwd)

        # ----------------------------------------------------------------------
        # 1. Institutions
        # ----------------------------------------------------------------------
        inst_a = db.query(Institution).filter_by(code="APEX").first()
        if not inst_a:
            inst_a = Institution(
                name="Apex Institute of Technology",
                slug="apex-tech",
                code="APEX",
                timezone="America/New_York",
                is_active=True,
            )
            db.add(inst_a)
            db.flush()

        inst_b = db.query(Institution).filter_by(code="BEACON").first()
        if not inst_b:
            inst_b = Institution(
                name="Beacon State University",
                slug="beacon-state",
                code="BEACON",
                timezone="Europe/London",
                is_active=True,
            )
            db.add(inst_b)
            db.flush()

        # ----------------------------------------------------------------------
        # 2. Users (Global identity) & Memberships (All 5 Roles)
        # ----------------------------------------------------------------------
        def get_or_create_user(email: str, full_name: str) -> User:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    hashed_password=hashed_pwd,
                    full_name=full_name,
                    is_active=True,
                    must_change_password=False,
                )
                db.add(user)
                db.flush()
            else:
                user.hashed_password = hashed_pwd
                db.flush()
            return user

        def ensure_membership(user_id: str, institution_id: str, role: UserRole):
            m = (
                db.query(Membership)
                .filter_by(institution_id=institution_id, user_id=user_id, role=role)
                .first()
            )
            if not m:
                m = Membership(
                    institution_id=institution_id,
                    user_id=user_id,
                    role=role,
                    is_active=True,
                )
                db.add(m)
                db.flush()
            return m

        # Institution A Users (Covering all 5 roles)
        admin_a_user = get_or_create_user("admin@apex.edu", "Dr. Sarah Connor (Admin)")
        coord_a_user = get_or_create_user("coord@apex.edu", "Prof. Charles Xavier (Coordinator)")
        exam_a_user = get_or_create_user("exam@apex.edu", "Dr. Minerva McGonagall (Exam Controller)")
        teacher_smith_user = get_or_create_user("smith@apex.edu", "Dr. Alan Smith (CS Faculty)")
        teacher_jones_user = get_or_create_user("jones@apex.edu", "Dr. Diana Jones (ME Faculty)")
        student_alice_user = get_or_create_user("alice@apex.edu", "Alice Miller (Student)")
        student_bob_user = get_or_create_user("bob@apex.edu", "Bob Vance (Student)")

        ensure_membership(admin_a_user.id, inst_a.id, UserRole.INSTITUTION_ADMINISTRATOR)
        ensure_membership(coord_a_user.id, inst_a.id, UserRole.TIMETABLE_COORDINATOR)
        ensure_membership(exam_a_user.id, inst_a.id, UserRole.EXAM_CONTROLLER)
        ensure_membership(teacher_smith_user.id, inst_a.id, UserRole.TEACHER)
        ensure_membership(teacher_jones_user.id, inst_a.id, UserRole.TEACHER)
        ensure_membership(student_alice_user.id, inst_a.id, UserRole.STUDENT)
        ensure_membership(student_bob_user.id, inst_a.id, UserRole.STUDENT)

        # Institution B Users (All roles & Cross-membership demonstration)
        admin_b_user = get_or_create_user("admin@beacon.edu", "Prof. Arthur Pendelton (Admin)")
        coord_b_user = get_or_create_user("coord@beacon.edu", "Elena Rostova (Coordinator)")
        exam_b_user = get_or_create_user("exam@beacon.edu", "Garrick Ollivander (Exam Controller)")
        teacher_clark_user = get_or_create_user("clark@beacon.edu", "Dr. Walter Clark (AI Faculty)")
        student_charlie_user = get_or_create_user("charlie@beacon.edu", "Charlie Davis (Student)")

        ensure_membership(admin_b_user.id, inst_b.id, UserRole.INSTITUTION_ADMINISTRATOR)
        ensure_membership(coord_b_user.id, inst_b.id, UserRole.TIMETABLE_COORDINATOR)
        ensure_membership(exam_b_user.id, inst_b.id, UserRole.EXAM_CONTROLLER)
        ensure_membership(teacher_clark_user.id, inst_b.id, UserRole.TEACHER)
        ensure_membership(student_charlie_user.id, inst_b.id, UserRole.STUDENT)

        # ----------------------------------------------------------------------
        # 3. Departments & Terms (with explicit timezone)
        # ----------------------------------------------------------------------
        def get_or_create_dept(inst_id: str, code: str, name: str) -> Department:
            dept = db.query(Department).filter_by(institution_id=inst_id, code=code).first()
            if not dept:
                dept = Department(institution_id=inst_id, code=code, name=name)
                db.add(dept)
                db.flush()
            return dept

        dept_cs = get_or_create_dept(inst_a.id, "CS", "Computer Science & Engineering")
        dept_me = get_or_create_dept(inst_a.id, "ME", "Mechanical & Aerospace Engineering")
        dept_info = get_or_create_dept(inst_b.id, "INFO", "School of Informatics")

        def get_or_create_term(inst_id: str, code: str, name: str, start: date, end: date, tz: str) -> AcademicTerm:
            term = db.query(AcademicTerm).filter_by(institution_id=inst_id, code=code).first()
            if not term:
                term = AcademicTerm(
                    institution_id=inst_id,
                    code=code,
                    name=name,
                    start_date=start,
                    end_date=end,
                    timezone=tz,
                    is_active=True,
                )
                db.add(term)
                db.flush()
            return term

        term_a = get_or_create_term(
            inst_a.id, "2026-FALL", "Fall Semester 2026", date(2026, 9, 1), date(2026, 12, 22), "America/New_York"
        )
        term_b = get_or_create_term(
            inst_b.id, "2026-AUTUMN", "Autumn Term 2026", date(2026, 10, 1), date(2027, 1, 15), "Europe/London"
        )

        # ----------------------------------------------------------------------
        # 4. Teachers, Students, & Instructor Eligibility (Qualifications)
        # ----------------------------------------------------------------------
        def get_or_create_teacher(inst_id: str, user_id: str, dept_id: str, emp_id: str, title: str) -> Teacher:
            t = db.query(Teacher).filter_by(institution_id=inst_id, employee_id=emp_id).first()
            if not t:
                t = Teacher(
                    institution_id=inst_id,
                    user_id=user_id,
                    department_id=dept_id,
                    employee_id=emp_id,
                    designation=title,
                    is_active=True,
                )
                db.add(t)
                db.flush()
            return t

        teacher_smith = get_or_create_teacher(inst_a.id, teacher_smith_user.id, dept_cs.id, "APEX-FAC-101", "Professor of Computer Science")
        teacher_jones = get_or_create_teacher(inst_a.id, teacher_jones_user.id, dept_me.id, "APEX-FAC-102", "Associate Professor of Mechanics")
        teacher_clark = get_or_create_teacher(inst_b.id, teacher_clark_user.id, dept_info.id, "BCN-FAC-201", "Reader in Artificial Intelligence")

        def get_or_create_student(inst_id: str, user_id: str, dept_id: str, sid: str, year: int) -> Student:
            s = db.query(Student).filter_by(institution_id=inst_id, student_id_number=sid).first()
            if not s:
                s = Student(
                    institution_id=inst_id,
                    user_id=user_id,
                    department_id=dept_id,
                    student_id_number=sid,
                    admission_year=year,
                    is_active=True,
                )
                db.add(s)
                db.flush()
            return s

        student_alice = get_or_create_student(inst_a.id, student_alice_user.id, dept_cs.id, "APEX-STU-2026-001", 2026)
        student_bob = get_or_create_student(inst_a.id, student_bob_user.id, dept_cs.id, "APEX-STU-2026-002", 2026)
        student_charlie = get_or_create_student(inst_b.id, student_charlie_user.id, dept_info.id, "BCN-STU-2026-001", 2026)

        # ----------------------------------------------------------------------
        # 5. Subjects, Offerings, Sections, and Enrolments
        # ----------------------------------------------------------------------
        def get_or_create_subject(inst_id: str, dept_id: str, code: str, name: str, stype: SubjectType, lec: int, lab: int) -> Subject:
            subj = db.query(Subject).filter_by(institution_id=inst_id, code=code).first()
            if not subj:
                subj = Subject(
                    institution_id=inst_id,
                    department_id=dept_id,
                    code=code,
                    name=name,
                    subject_type=stype,
                    weekly_lecture_hours=lec,
                    weekly_lab_hours=lab,
                    credits=lec + lab,
                )
                db.add(subj)
                db.flush()
            return subj

        subj_cs101 = get_or_create_subject(inst_a.id, dept_cs.id, "CS101", "Algorithms & Data Structures", SubjectType.THEORY, 3, 0)
        subj_cs102l = get_or_create_subject(inst_a.id, dept_cs.id, "CS102L", "Systems & Networks Lab", SubjectType.PRACTICAL, 0, 3)
        subj_me201 = get_or_create_subject(inst_a.id, dept_me.id, "ME201", "Engineering Thermodynamics", SubjectType.THEORY, 4, 0)
        subj_info101 = get_or_create_subject(inst_b.id, dept_info.id, "INFO101", "Informatics Principles", SubjectType.HYBRID, 2, 2)

        # Qualifications (Instructor Eligibility)
        def ensure_qualification(inst_id: str, teacher_id: str, subject_id: str):
            q = db.query(TeacherQualification).filter_by(institution_id=inst_id, teacher_id=teacher_id, subject_id=subject_id).first()
            if not q:
                q = TeacherQualification(institution_id=inst_id, teacher_id=teacher_id, subject_id=subject_id, is_primary=True)
                db.add(q)
                db.flush()

        ensure_qualification(inst_a.id, teacher_smith.id, subj_cs101.id)
        ensure_qualification(inst_a.id, teacher_smith.id, subj_cs102l.id)
        ensure_qualification(inst_a.id, teacher_jones.id, subj_me201.id)
        ensure_qualification(inst_b.id, teacher_clark.id, subj_info101.id)

        # Course Offerings
        def get_or_create_offering(inst_id: str, subj_id: str, term_id: str) -> CourseOffering:
            off = db.query(CourseOffering).filter_by(institution_id=inst_id, subject_id=subj_id, academic_term_id=term_id).first()
            if not off:
                off = CourseOffering(institution_id=inst_id, subject_id=subj_id, academic_term_id=term_id, is_active=True)
                db.add(off)
                db.flush()
            return off

        off_cs101 = get_or_create_offering(inst_a.id, subj_cs101.id, term_a.id)
        off_cs102l = get_or_create_offering(inst_a.id, subj_cs102l.id, term_a.id)
        off_info101 = get_or_create_offering(inst_b.id, subj_info101.id, term_b.id)

        # Sections (Student Sections vs actual enrolments)
        def get_or_create_section(inst_id: str, off_id: str, name: str, cap: int) -> Section:
            sec = db.query(Section).filter_by(institution_id=inst_id, course_offering_id=off_id, name=name).first()
            if not sec:
                sec = Section(institution_id=inst_id, course_offering_id=off_id, name=name, capacity=cap)
                db.add(sec)
                db.flush()
            return sec

        sec_cs101_a = get_or_create_section(inst_a.id, off_cs101.id, "Section A", 30)
        sec_cs102_lab1 = get_or_create_section(inst_a.id, off_cs102l.id, "Lab Section 1", 20)
        sec_info101_alpha = get_or_create_section(inst_b.id, off_info101.id, "Cohort Alpha", 25)

        # Enrolments
        def ensure_enrolment(inst_id: str, student_id: str, section_id: str):
            enr = db.query(Enrolment).filter_by(institution_id=inst_id, student_id=student_id, section_id=section_id).first()
            if not enr:
                enr = Enrolment(institution_id=inst_id, student_id=student_id, section_id=section_id, status=EnrolmentStatus.ENROLLED)
                db.add(enr)
                db.flush()

        ensure_enrolment(inst_a.id, student_alice.id, sec_cs101_a.id)
        ensure_enrolment(inst_a.id, student_alice.id, sec_cs102_lab1.id)
        ensure_enrolment(inst_a.id, student_bob.id, sec_cs101_a.id)
        ensure_enrolment(inst_b.id, student_charlie.id, sec_info101_alpha.id)

        # ----------------------------------------------------------------------
        # 6. Facilities: Buildings, Rooms, Seats & Workstations
        # ----------------------------------------------------------------------
        def get_or_create_building(inst_id: str, code: str, name: str) -> Building:
            bldg = db.query(Building).filter_by(institution_id=inst_id, code=code).first()
            if not bldg:
                bldg = Building(institution_id=inst_id, code=code, name=name)
                db.add(bldg)
                db.flush()
            return bldg

        bldg_tsc = get_or_create_building(inst_a.id, "TSC", "Turing Science Complex")
        bldg_alb = get_or_create_building(inst_b.id, "ALB", "Ada Lovelace Hall")

        def get_or_create_room(
            inst_id: str, bldg_id: str, rnum: str, name: str, rtype: RoomType, phys_cap: int, exam_cap: int, rows: int, cols: int
        ) -> Room:
            room = db.query(Room).filter_by(institution_id=inst_id, building_id=bldg_id, room_number=rnum).first()
            if not room:
                room = Room(
                    institution_id=inst_id,
                    building_id=bldg_id,
                    room_number=rnum,
                    name=name,
                    room_type=rtype,
                    physical_capacity=phys_cap,
                    usable_exam_benches=exam_cap,
                    grid_rows=rows,
                    grid_cols=cols,
                    is_active=True,
                )
                db.add(room)
                db.flush()
            return room

        # Theory Auditorium: Physical capacity 60, Usable Exam Benches 30
        room_auditorium = get_or_create_room(
            inst_a.id, bldg_tsc.id, "101", "Turing Auditorium", RoomType.LECTURE_HALL, 60, 30, 6, 10
        )
        # Practical Computer Lab: Physical capacity 24, Usable Exam Benches 12
        room_lab = get_or_create_room(
            inst_a.id, bldg_tsc.id, "204", "Advanced Systems Lab", RoomType.COMPUTER_LAB, 24, 12, 4, 6
        )

        # Seed Theory Benches with Usable, Blocked, and Accessible states
        for r in range(1, 4):
            for c in range(1, 11):
                label = f"TSC-R{r}-B{c}"
                seat = db.query(Seat).filter_by(institution_id=inst_a.id, room_id=room_auditorium.id, bench_label=label).first()
                if not seat:
                    is_accessible = (r == 1 and c in (1, 10))  # Front ends are wheelchair accessible
                    is_blocked = (r == 2 and c == 5)           # Broken bench desk
                    is_usable = not is_blocked
                    seat = Seat(
                        institution_id=inst_a.id,
                        room_id=room_auditorium.id,
                        row_num=r,
                        col_num=c,
                        bench_label=label,
                        is_usable_for_exam=is_usable,
                        is_blocked=is_blocked,
                        is_accessible=is_accessible,
                    )
                    db.add(seat)
        db.flush()

        # Seed Workstations with Features in Practical Lab
        ws_specs = [
            (1, "TSC-WS-01", True, "Ubuntu 24.04 LTS", ["NVIDIA RTX 4090", "CUDA", "PyTorch"], True),
            (2, "TSC-WS-02", True, "Ubuntu 24.04 LTS", ["NVIDIA RTX 4090", "CUDA", "PyTorch"], False),
            (3, "TSC-WS-03", True, "Windows 11 Pro", ["SolidWorks", "MATLAB", "LabVIEW"], False),
            (4, "TSC-WS-04", True, "Windows 11 Pro", ["SolidWorks", "MATLAB", "LabVIEW"], False),
        ]
        for ws_num, ws_label, has_comp, os_name, feat_list, is_acc in ws_specs:
            ws = db.query(Workstation).filter_by(institution_id=inst_a.id, room_id=room_lab.id, label=ws_label).first()
            if not ws:
                ws = Workstation(
                    institution_id=inst_a.id,
                    room_id=room_lab.id,
                    workstation_number=ws_num,
                    label=ws_label,
                    has_computer=has_comp,
                    operating_system=os_name,
                    features=feat_list,
                    is_active=True,
                    is_accessible=is_acc,
                )
                db.add(ws)
        db.flush()

        # ----------------------------------------------------------------------
        # 7. Availability Rules & Calendar Exceptions
        # ----------------------------------------------------------------------
        rule_smith = db.query(AvailabilityRule).filter_by(
            institution_id=inst_a.id, teacher_id=teacher_smith.id, day_of_week=0
        ).first()
        if not rule_smith:
            rule_smith = AvailabilityRule(
                institution_id=inst_a.id,
                target_type=TargetType.TEACHER,
                teacher_id=teacher_smith.id,
                day_of_week=0,  # Monday
                start_time=time(8, 0),
                end_time=time(10, 0),
                is_available=False,
                reason="Department Faculty Research Sabbatical Slot",
            )
            db.add(rule_smith)

        exc_thanksgiving = db.query(CalendarException).filter_by(
            institution_id=inst_a.id, exception_date=date(2026, 11, 26)
        ).first()
        if not exc_thanksgiving:
            exc_thanksgiving = CalendarException(
                institution_id=inst_a.id,
                academic_term_id=term_a.id,
                exception_date=date(2026, 11, 26),
                exception_type=CalendarExceptionType.HOLIDAY,
                description="Thanksgiving Break - All Classes Suspended",
            )
            db.add(exc_thanksgiving)

        # ----------------------------------------------------------------------
        # 8. Constraint Rules & Sample Scheduled Sessions
        # ----------------------------------------------------------------------
        rule_codes = [
            ("NO_INSTRUCTOR_DOUBLE_BOOKING", "Instructor Collision Prevention", ConstraintType.HARD, 0, {}),
            ("ANTI_CHEAT_ORTHOGONAL_DISTANCE", "Orthogonal Exam Spacing", ConstraintType.HARD, 0, {"min_distance": 1}),
            ("ONE_CANDIDATE_PER_USABLE_BENCH", "Single Bench Seating Limit", ConstraintType.HARD, 0, {}),
            ("MINIMIZE_FACULTY_IDLE_GAPS", "Faculty Idle Gap Penalty", ConstraintType.SOFT, 50, {"max_gap_hours": 1}),
        ]
        for rcode, rname, rtype, pweight, params in rule_codes:
            cr = db.query(ConstraintRule).filter_by(institution_id=inst_a.id, rule_code=rcode).first()
            if not cr:
                cr = ConstraintRule(
                    institution_id=inst_a.id,
                    rule_code=rcode,
                    rule_name=rname,
                    rule_type=rtype,
                    penalty_weight=pweight,
                    parameters=params,
                    is_enabled=True,
                )
                db.add(cr)

        # Recurring Timetable Session
        sess_lecture = (
            db.query(Session)
            .filter_by(institution_id=inst_a.id, section_id=sec_cs101_a.id, session_type=SessionType.LECTURE)
            .first()
        )
        if not sess_lecture:
            sess_lecture = Session(
                institution_id=inst_a.id,
                academic_term_id=term_a.id,
                section_id=sec_cs101_a.id,
                session_type=SessionType.LECTURE,
                room_id=room_auditorium.id,
                primary_teacher_id=teacher_smith.id,
                day_of_week=0,  # Monday
                start_time=time(10, 0),
                end_time=time(11, 30),
                is_recurring=True,
                status=SessionStatus.PUBLISHED,
            )
            db.add(sess_lecture)

        # Dated Practical Exam Sitting
        sess_exam = (
            db.query(Session)
            .filter_by(institution_id=inst_a.id, section_id=sec_cs102_lab1.id, session_type=SessionType.PRACTICAL_EXAM)
            .first()
        )
        if not sess_exam:
            sess_exam = Session(
                institution_id=inst_a.id,
                academic_term_id=term_a.id,
                section_id=sec_cs102_lab1.id,
                session_type=SessionType.PRACTICAL_EXAM,
                room_id=room_lab.id,
                primary_teacher_id=teacher_smith.id,
                start_datetime=datetime(2026, 12, 15, 9, 0, tzinfo=timezone.utc),
                end_datetime=datetime(2026, 12, 15, 12, 0, tzinfo=timezone.utc),
                is_recurring=False,
                status=SessionStatus.REVIEWED,
            )
            db.add(sess_exam)

        # Audit Event
        audit_rec = (
            db.query(AuditEvent)
            .filter_by(institution_id=inst_a.id, event_type="SEED_DATABASE")
            .first()
        )
        if not audit_rec:
            audit_rec = AuditEvent(
                institution_id=inst_a.id,
                user_id=admin_a_user.id,
                event_type="SEED_DATABASE",
                entity_type="SYSTEM",
                entity_id=None,
                action="INITIALIZE",
                ip_address="127.0.0.1",
                payload={"institutions_seeded": ["APEX", "BEACON"], "status": "COMPLETED"},
            )
            db.add(audit_rec)

        db.commit()
        print("[SEED SUCCESS] Database seeded idempotently with all entities and roles.")
        return True

    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Seed operation encountered an error: {exc}", file=sys.stderr)
        raise exc
    finally:
        if not is_external_session:
            db.close()


if __name__ == "__main__":
    run_seed()