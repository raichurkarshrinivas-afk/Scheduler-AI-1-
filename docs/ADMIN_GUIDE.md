# Scheduler - Administrator Guide

This guide details administrative functions, user role permissions, data onboarding, draft generation workflows, exam logistics, and publication lifecycle management in **Scheduler**.

---

## 1. Role-Based Access Control (RBAC)

Scheduler enforces strict tenant-isolated, role-based authorization across four tiers:

| Role | Permissions & Scope | Typical Users |
| :--- | :--- | :--- |
| **System Administrator** (`SYSTEM_ADMIN`) | Full tenant administration; user creation; role modification; system configuration; global feedback triage; integration keys. | IT Operations, Registrar, Dean of Academic Affairs. |
| **Timetable Coordinator** (`TIMETABLE_COORDINATOR`) | Create/edit academic terms; import curriculum data; trigger solver jobs; validate checker diagnostics; publish schedules; run exam seating allocations. | Scheduling Officers, Academic Program Directors. |
| **Teacher** (`TEACHER`) | View published master timetables; view personal assigned teaching schedule; request changes via feedback or AI change interpreter. | Professors, Lecturers, Teaching Assistants. |
| **Student** (`STUDENT`) | View published class timetables; view personalized exam hall & bench assignments; submit feedback/inquiries. | Enrolled Students. |

---

## 2. Setting Up an Academic Term

1. Log in as an Administrator or Timetable Coordinator.
2. Navigate to **Academic Terms** (`/staff/terms`).
3. Click **Create Term**:
   * Name: e.g., `Autumn 2026 Semester`.
   * Start Date & End Date: Defines the academic operational calendar.
   * Day Structure: Monday through Friday (or Saturday if 6-day week).
   * Daily Time Slots: Define standard periods (e.g., 08:30 - 09:30, 09:30 - 10:30, Break, etc.).
4. Save and set the term as **Active**.

---

## 3. Data Onboarding & CSV Imports

Scheduler accepts standard CSV imports to populate academic master data:

* **Rooms (`rooms.csv`)**: Room Code, Name, Capacity, Room Type (`LECTURE_HALL`, `LAB`, `SEMINAR`), Equipment (`PROJECTOR`, `COMPUTERS`).
* **Teachers (`teachers.csv`)**: Full Name, Email, Department, Max Daily Hours, Unavailable Time Windows.
* **Student Classes / Cohorts (`classes.csv`)**: Grade/Year, Cohort Code, Total Enrolled Students.
* **Courses & Curriculum (`courses.csv`)**: Course Code, Title, Required Weekly Hours, Assigned Teacher(s), Permitted Room Types.

---

## 4. Timetable Draft Creation & Solver Workflow

```
[Create Draft Snapshot] ──► [Dispatch SAT Solver] ──► [Checker Validation] ──► [Manual Edits] ──► [Controlled Publish]
```

### 4.1 Creating a Snapshot
1. Navigate to **Timetable Drafts** (`/staff/timetables`).
2. Click **Create Draft**.
3. Select the target **Academic Term**.
4. The system automatically creates an immutable **Input Snapshot** capturing the current state of rooms, teachers, classes, and constraints. This guarantees reproducibility even if master records change later.

### 4.2 Running the Solver
1. In the Draft Details screen, click **Generate Timetable**.
2. Set Solver Parameters:
   * **Time Limit**: Default `15.0` seconds (can be increased up to `120.0`s for large institutions).
   * **Teacher Gap Minimization Weight**: Prioritizes compact teacher schedules.
3. Click **Submit**. A background job is dispatched (`QUEUED`).
4. Real-time phase updates appear on screen via SSE notifications:
   * `Initializing solver model`
   * `Building constraint matrices`
   * `Solving SAT model`
   * `Running schedule checker`
   * `Completed successfully`

### 4.3 Schedule Checker Validation
Once solved, the draft moves to `CHECKED` status. The integrated Schedule Checker evaluates:
* **Hard Constraints** (Must be 100% satisfied):
  * No teacher double-booking.
  * No room double-booking.
  * No class cohort double-booking.
  * Room capacity $\ge$ class cohort size.
  * Required equipment match.
* **Soft Constraints** (Quality score):
  * Minimized student free periods / windows.
  * Fair teacher workload distribution.

### 4.4 Manual Edits & Optimistic Concurrency
Coordinators can manually drag-and-drop or reassign slots:
* Every draft tracks an incremental `revision_id`.
* If two coordinators edit concurrently, the second save is rejected with `409 Conflict`, preventing accidental loss of manual modifications.

---

## 5. Controlled Publication & Versioning

> [!IMPORTANT]
> **Immutability of Published Timetables**:
> Once a timetable draft is published, it becomes **permanently read-only**.
> Changes cannot be directly edited into a published version. To update an active schedule, coordinators clone the draft, make edits, and publish a new version (`v1.1`, `v2.0`).

### Publishing Sequence:
1. Ensure the draft status is `CHECKED` with zero hard constraint violations.
2. Click **Publish Timetable**.
3. Select Version Label: `v1.0 (Initial Term Release)`.
4. Enter mandatory publication notes for faculty and students.
5. Confirm. The system:
   * Marks the draft as `PUBLISHED`.
   * Sets this version as the institution's currently active public schedule.
   * Dispatches notifications to affected teachers and students.
   * Generates official static PDF schedules in `/app/exports`.

---

## 6. Examination Logistics & Seating Allocation

Navigate to **Exam Logistics** (`/staff/examinations`):

1. **Exam Period Setup**: Define exam dates and time sessions (Morning / Afternoon).
2. **Subject Scheduling**: Assign courses to sessions ensuring no student has two exams at the same time.
3. **Automated Seating Allocation**:
   * Select Exam Hall.
   * Configure bench grid layout (e.g., 5 rows $\times$ 6 columns).
   * Set alternating strategy: Prevents adjacent students from writing the same exam subject.
   * Accessibility accommodations: Automatically reserves front-row, low-mobility, or quiet-space seating for registered students with accommodations without exposing confidential medical notes.
4. Export official Hall Seating Charts (PDF / CSV) for physical door notices.

---

## 7. AI-Assisted Interpretation (Optional Phase 13)

When enabled, the AI Assistant assists coordinators with routine natural language tasks:
* **Timetable Change Interpretation**: Analyzes teacher change requests (e.g., *"Dr. Smith cannot teach Physics on Tuesday morning due to conference"*), maps entities, and proposes concrete slot swaps.
* **Checker Diagnostic Explanations**: Explains complex constraint conflicts in plain English.
* **Import Column Mapping**: Suggests headers when importing irregular spreadsheets.

> [!CAUTION]
> **AI Safety Controls**:
> * The AI model has **no direct database access**, cannot execute SQL, cannot change permissions, and cannot publish timetables.
> * All AI output is schema-validated structured data.
> * Proposals are strictly advisory and require explicit coordinator approval before being applied to a draft.

---

## 8. Feedback Triage & Management

Navigate to **Feedback Inbox** (`/staff/feedback`):
* View incoming submissions categorized by type: `Bug Report`, `Suggestion`, `Scheduling Conflict`, `Access Issue`.
* Triage status: `NEW`, `IN_REVIEW`, `RESOLVED`, `CLOSED`.
* Filter between authenticated user submissions and public inquiries.
