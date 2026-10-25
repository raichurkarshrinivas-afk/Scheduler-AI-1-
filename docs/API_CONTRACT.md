# Scheduler API Contract (v1)

## 1. Overview & Proxy Conventions

### 1.1 Base URL & Environment Routing
- **Local Development**:
  - Frontend Address: `http://localhost:5173`
  - Same-Origin Proxy: `/api/*` and `/health/*` &rarr; forwarded by Vite dev proxy to `http://127.0.0.1:8000`.
  - Backend Direct Address: `http://127.0.0.1:8000`
- **Production Container Routing**:
  - Reverse Proxy (Nginx): Listens on port `80` (or `443` with TLS).
  - `/api/*` &rarr; routed to `http://backend:8000/api/*`.
  - `/health` and `/health/*` &rarr; routed to `http://backend:8000/health/*`.
  - All other routes &rarr; routed to static frontend SPA container (`http://frontend:80`).

---

## 2. Platform Health & Readiness Endpoints (Phase 1 Implemented)

### `GET /health/live` and `GET /api/health/live`
- **Purpose**: Liveness probe for orchestrators (Kubernetes, Docker Swarm, systemd). Verifies that the ASGI process is running and accepting TCP sockets.
- **Database Dependency**: **None** (must succeed even if database is down).
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "ok",
      "live": true,
      "service": "Scheduler",
      "version": "1.0.0"
    }
    ```

### `GET /health/ready` and `GET /api/health/ready`
- **Purpose**: Readiness probe. Validates that the application is ready to accept user requests by verifying active database round-trip connectivity (`SELECT 1` via SQLAlchemy 2.x and Psycopg 3).
- **Database Dependency**: **Mandatory**.
- **Responses**:
  - `200 OK` (Database reachable):
    ```json
    {
      "status": "ok",
      "ready": true,
      "database": "connected",
      "service": "Scheduler",
      "version": "1.0.0"
    }
    ```
  - `503 Service Unavailable` (Database unreachable):
    ```json
    {
      "status": "unavailable",
      "ready": false,
      "database": "disconnected",
      "detail": "connection to server at 'localhost' failed",
      "service": "Scheduler",
      "version": "1.0.0"
    }
    ```

### `GET /health` and `GET /api/health`
- **Purpose**: Composite telemetry endpoint reporting aggregate status, liveness, and database connection state.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "ok",
      "live": true,
      "ready": true,
      "database": "connected",
      "service": "Scheduler",
      "version": "1.0.0"
    }
    ```

---

## 3. Planned Endpoints (Phase 2 Roadmap)

> Note: Per Phase 1 requirements, authentication and scheduling endpoints are intentionally deferred from active implementation to keep the foundation minimal and verifiable. The schemas below represent the planned contract specifications.

### 3.1 Authentication & Session Management
- `POST /api/v1/auth/login`: Issues server-side cookie session (`HttpOnly`, `SameSite=Lax`).
- `POST /api/v1/auth/logout`: Clears session cookie.
- `GET /api/v1/auth/me`: Returns current authenticated user and institutional role.

### 3.2 Academic Structure & Facilities
- `GET /api/v1/institutions/{id}`: Returns institution profile.
- `GET /api/v1/facilities/classrooms`: Lists classrooms and laboratory physical grid capacities.
- `POST /api/v1/facilities/classrooms`: Creates classroom with rows, columns, and usable bench limits.
- `GET /api/v1/courses`: Lists course definitions.

### 3.3 Timetable Scheduling (Draft &rarr; Check &rarr; Review &rarr; Publish)
- `GET /api/v1/timetables/drafts`: Lists timetable drafts for an academic term.
- `POST /api/v1/timetables/check`: Executes automated clash detection without committing.
- `POST /api/v1/timetables/solve`: Dispatches OR-Tools CP-SAT solving task to worker process.
- `POST /api/v1/timetables/{id}/publish`: Locks timetable and publishes to teachers and students.

### 3.4 Examination Sittings & Theory Seating
- `POST /api/v1/exams/sessions`: Registers fixed exam date and period.
- `POST /api/v1/exams/{id}/seating/solve`: Allocates one candidate per usable bench with orthogonal spacing.
- `GET /api/v1/exams/{id}/seating`: Retrieves room-by-room seating grids and desk labels.
- `GET /api/v1/exams/{id}/export-pdf`: Generates printable ReportLab seating charts and hall tickets.

### 3.5 Feedback & Administrative Triage
- `POST /api/v1/feedback`: Submits teacher or student feedback on timetable or exam seating.
- `GET /api/v1/feedback/triage`: Lists open feedback items for coordinator/administrator triage.
- `PATCH /api/v1/feedback/{id}`: Updates status (`INVESTIGATING`, `RESOLVED`, `REJECTED`).
---

## 4. Background Job Processing Endpoints (Phase 6 Implemented)

### `GET /api/v1/jobs/{id}`
- **Purpose**: Retrieves status, phase label, attempt count, elapsed runtime, and result references for a background job.
- **Authorization**: Session cookie required. Enforces tenant boundary (`verify_institution_ownership`). Cross-tenant access returns `404 Not Found`.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "id": "b34d314b-40b7-457a-aff7-62cb978c412a",
      "institution_id": "962bff7a-...",
      "job_type": "TIMETABLE_SOLVE",
      "status": "RUNNING",
      "phase_label": "Formulating OR-Tools CP-SAT multi-dimensional constraint model",
      "attempt_count": 1,
      "max_attempts": 3,
      "available_at": "2026-10-22T06:00:00Z",
      "started_at": "2026-10-22T06:00:01Z",
      "finished_at": null,
      "elapsed_seconds": 12.4,
      "lease_owner": "worker-prod-1",
      "heartbeat_at": "2026-10-22T06:00:10Z",
      "result_reference": null,
      "error_code": null,
      "error_message": null,
      "cancellation_requested": false,
      "created_at": "2026-10-22T06:00:00Z",
      "updated_at": "2026-10-22T06:00:10Z"
    }
    ```
  - `404 Not Found`: Job does not exist or belongs to another institution.

### `POST /api/v1/jobs/{id}/cancel`
- **Purpose**: Requests cancellation of an active or queued job.
- **Authorization**: Session cookie required. Role must be `INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, or `EXAM_CONTROLLER`. Requires valid `X-CSRF-Token`.
- **Behavior**:
  - If `QUEUED`: transitions immediately to `CANCELLED`.
  - If `RUNNING`: sets `cancellation_requested = true`. Worker aborts at the next checkpoint/heartbeat and transitions to `CANCELLED`.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "job_id": "b34d314b-40b7-457a-aff7-62cb978c412a",
      "status": "CANCELLED",
      "cancellation_requested": true,
      "message": "Job b34d314b-... cancellation status: Cancelled before execution began."
    }
    ```
  - `404 Not Found`: Job does not exist or belongs to another institution.
  - `403 Forbidden`: User lacks role permissions or CSRF token is invalid.

### `POST /api/v1/jobs`
- **Purpose**: Enqueues a new background job for the authenticated institution.
- **Authorization**: Same roles as cancellation + CSRF token.
- **Request Body**:
  ```json
  {
    "job_type": "TIMETABLE_SOLVE",
    "input_reference": {"cohort": "CS-A", "term": "Autumn 2026"},
    "max_attempts": 3
  }
  ```
- **Responses**:
  - `201 Created`: Returns `JobOut` payload with status `QUEUED`.

### `GET /api/v1/jobs`
- **Purpose**: Lists recent background jobs scoped to the caller's institution with optional `status_filter`.
- **Authorization**: Active session membership.
- **Responses**:
  - `200 OK`: Array of `JobOut` records.

---

## 5. Timetable Generation & Verification Endpoints (Phase 7 Implemented)

### `POST /api/v1/timetable-drafts`
- **Purpose**: Creates a new immutable timetable input snapshot and draft record. Computes SHA-256 input hash and version identifiers.
- **Authorization**: Session cookie required. Role must be `INSTITUTION_ADMINISTRATOR` or `TIMETABLE_COORDINATOR`. Requires valid `X-CSRF-Token`.
- **Request Body**:
  ```json
  {
    "academic_term_id": "7f13b631-...",
    "name": "Fall 2026 CS Draft 1",
    "input_snapshot": {
      "rules": {"max_periods_per_day": 8, "allow_unsupported_rules": false},
      "sessions": [
        {
          "id": "sess-1",
          "subject_id": "sub-1",
          "teacher_id": "teach-1",
          "section_id": "sec-a",
          "duration_periods": 1,
          "capacity_required": 30,
          "room_type": "THEORY",
          "required_features": []
        }
      ],
      "rooms": [
        {
          "id": "room-101",
          "name": "Hall 101",
          "capacity": 50,
          "type": "THEORY",
          "features": []
        }
      ],
      "days": [0, 1, 2, 3, 4],
      "periods": [0, 1, 2, 3, 4, 5, 6, 7],
      "unavailability": [],
      "breaks": [],
      "locked_assignments": [],
      "preferences": []
    }
  }
  ```
- **Responses**:
  - `201 Created`: Returns `TimetableDraftOut` with `status: "DRAFT"` and SHA-256 `input_hash`.
  - `400 Bad Request`: If unsupported rule configurations are requested (e.g. `floating_lunch_breaks`, `multi_campus_transit`).

### `POST /api/v1/timetable-drafts/{id}/generate`
- **Purpose**: Dispatches an asynchronous timetabling solve job to the background worker using Google OR-Tools CP-SAT.
- **Status Code**: `202 Accepted`
- **Authorization**: Session cookie required. Role must be `INSTITUTION_ADMINISTRATOR` or `TIMETABLE_COORDINATOR`. Requires valid `X-CSRF-Token`.
- **Request Body** (optional):
  ```json
  {
    "time_limit_seconds": 60,
    "num_workers": 4
  }
  ```
- **Responses**:
  - `202 Accepted`:
    ```json
    {
      "draft_id": "c83b1a20-...",
      "job_id": "b34d314b-...",
      "message": "Timetable generation job enqueued. Monitor status via /api/v1/jobs/{job_id} or poll /api/v1/timetable-drafts/{draft_id}.",
      "status": "QUEUED"
    }
    ```
  - `400 Bad Request`: If draft is already `PUBLISHED` (published state cannot be modified by generation).
  - `404 Not Found`: Draft does not exist or belongs to another institution.

### `POST /api/v1/timetable-drafts/{id}/check`
- **Purpose**: Executes independent verification checker against the draft's assignments without invoking model construction code.
- **Authorization**: Session cookie required. Role must be `INSTITUTION_ADMINISTRATOR` or `TIMETABLE_COORDINATOR`. Requires valid `X-CSRF-Token`.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "is_valid": true,
      "violations": [],
      "checked_at": "2026-10-22T06:30:00Z",
      "checker_version": "1.0.0",
      "status": "CHECKED"
    }
    ```
  - `400 Bad Request`: If verification reveals conflicts, duplicates, missing sessions, or room capacity/feature violations.

### `GET /api/v1/timetable-drafts/{id}`
- **Purpose**: Retrieves draft status, solver status (`OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`), version metadata, parameters, runtime metrics, assignments, and validation report.
- **Authorization**: Active session membership within the institution.
- **Responses**:
  - `200 OK`: Returns full `TimetableDraftOut` entity.
  - `404 Not Found`: Draft does not exist or tenant boundary violated.

### `PATCH /api/v1/timetable-drafts/{id}/assignments/{assignment_id}`
- **Purpose**: Updates an individual session assignment within a draft timetable.
- **Authorization**: Session cookie required. Role must be `INSTITUTION_ADMINISTRATOR` or `TIMETABLE_COORDINATOR`. Requires valid `X-CSRF-Token`.
- **Optimistic Locking**: Requires `expected_revision`. If `draft.revision != expected_revision`, returns `409 Conflict`.
- **Immutability Safeguard**: Rejects modifications on published drafts (`HTTP 400 Bad Request`).
- **Request Body**:
  ```json
  {
    "expected_revision": 1,
    "day": 2,
    "period": 4,
    "room_id": "room-102",
    "is_locked": true
  }
  ```
- **Responses**:
  - `200 OK`: Returns updated `TimetableDraftOut` with incremented `revision`, updated `status` (`CHECKED` or `INVALID`), and authoritative `validation_report`.
  - `400 Bad Request`: If draft is already published.
  - `404 Not Found`: Draft or assignment ID not found.
  - `409 Conflict`: Stale edit detected (revision mismatch).

### `POST /api/v1/timetable-drafts/{id}/repair`
- **Purpose**: Executes minimal-change schedule repair using CP-SAT. Preserves locked commitments, minimizes disruption costs, and returns before/after comparisons.
- **Authorization**: Session cookie required. Same roles as assignment updates + CSRF token.
- **Optimistic Locking**: Requires `expected_revision`.
- **Request Body**:
  ```json
  {
    "expected_revision": 2,
    "time_limit_seconds": 30
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "draft_id": "c83b1a20-...",
      "revision": 3,
      "status": "CHECKED",
      "is_valid": true,
      "change_count": 1,
      "changes": [
        {
          "session_id": "sess-cs202",
          "session_name": "Computer Architecture",
          "teacher_id": "prof-turing",
          "section_id": "CS-A",
          "before": {"day": 0, "period": 0, "room_id": "room-204"},
          "after": {"day": 1, "period": 1, "room_id": "room-204"},
          "time_moved": true,
          "room_changed": false,
          "reason": "Resolved room overlap with minimal disruption"
        }
      ],
      "validation_report": {"is_valid": true, "violations": []},
      "output_assignments": [...]
    }
    ```
  - `400 Bad Request`: If draft is already published.
  - `409 Conflict`: Stale edit revision mismatch.
  - `422 Unprocessable Entity`: If mathematically impossible to satisfy constraints without relaxing rules or unlocking sessions.


---

## Exam Allocation & Logistics Endpoints (Phase 9)

### 1. Theory Examination Seating

- **`GET /api/v1/exams/sittings`**
  - **Query Parameters**: `exam_type` ('THEORY' | 'PRACTICAL'), `academic_term_id`.
  - **Response `200 OK`**: List of `ExamSittingOut` records.

- **`POST /api/v1/exams/theory/sittings`**
  - **Roles**: `INSTITUTION_ADMINISTRATOR`, `EXAM_CONTROLLER`, `TIMETABLE_COORDINATOR`.
  - **CSRF Protected**: Yes (`X-CSRF-Token`).
  - **Request Body**:
    ```json
    {
      "name": "End-Term Theory Examination",
      "academic_term_id": "uuid-term",
      "duration_minutes": 180,
      "buffer_minutes": 15,
      "input_snapshot": {
        "candidates": [
          {"id": "cand-1", "roll_number": "2026-CS-001", "paper_code": "CS101", "requires_accessible_seat": false}
        ],
        "rooms": [
          {
            "id": "hall-a",
            "name": "Hall Alpha",
            "seats": [
              {"id": "b-1", "row_num": 1, "col_num": 1, "bench_label": "A1", "is_usable_for_exam": true, "is_blocked": false, "is_accessible": true}
            ]
          }
        ]
      },
      "parameters": {
        "hard_paper_adjacency": false,
        "batch_grouping_policy": true,
        "use_optimisation": false
      }
    }
    ```
  - **Response `201 Created`**: `ExamSittingOut` object.

- **`POST /api/v1/exams/theory/sittings/{id}/allocate`**
  - **Roles**: `INSTITUTION_ADMINISTRATOR`, `EXAM_CONTROLLER`.
  - **Description**: Executes deterministic or CP-SAT seating allocation.
  - **Response `200 OK`**: `ExamSittingOut` with populated `output_allocations` and `validation_report`.
  - **Response `422 Unprocessable Entity`**: If capacity is insufficient or hard paper adjacency cannot be satisfied.

- **`POST /api/v1/exams/theory/sittings/{id}/validate`**
  - **Description**: Independent verification of seating constraints.
  - **Response `200 OK`**: `{"is_valid": true, "violations": [], "warnings": [], "checker_version": "1.0.0"}`.

- **`PATCH /api/v1/exams/theory/sittings/{id}/seats/{candidate_id}`**
  - **Description**: Reassigns candidate to vacant bench or swaps with target candidate.
  - **Request Body**:
    ```json
    {
      "expected_revision": 2,
      "seat_id": "b-2",
      "room_id": "hall-a",
      "target_candidate_id": "cand-2"
    }
    ```
  - **Response `200 OK`**: Updated `ExamSittingOut` with revision incremented.
  - **Response `409 Conflict`**: Revision mismatch on concurrent edits.

### 2. Practical Examination Logistics

- **`POST /api/v1/exams/practical/sittings`**
  - **Description**: Creates practical sitting with candidate batches, labs, and turnaround buffers.
  - **Response `201 Created`**: `ExamSittingOut`.

- **`POST /api/v1/exams/practical/sittings/{id}/allocate`**
  - **Description**: Allocates workstations respecting hardware/OS features and turnaround buffers.
  - **Response `200 OK`**: `ExamSittingOut`.
  - **Response `422 Unprocessable Entity`**: If examiner clashes, lab overlaps, or workstation incompatibility occurs.

- **`PATCH /api/v1/exams/practical/sittings/{id}/workstations/{candidate_id}`**
  - **Description**: Validated workstation reassignment with expected revision checking.

### 3. Authenticated Cryptographic Exports (Privacy-Preserved)

- **`GET /api/v1/exams/theory/sittings/{id}/export/seat-plan?room_id={room_id}`**
  - **Description**: Exports public hall seating plan.
  - **Privacy Guarantee**: `private_accommodations` notes are strictly omitted from output.
  - **Response `200 OK`**:
    ```json
    {
      "document_type": "HALL_SEAT_PLAN",
      "sitting_id": "...",
      "status_label": "DRAFT",
      "revision": 2,
      "generated_at": "2026-10-22T13:00:00Z",
      "export_token": "exp-hmac-...",
      "expires_at": "2026-10-22T14:00:00Z",
      "seats": [...]
    }
    ```

- **`GET /api/v1/exams/theory/sittings/{id}/export/candidate-list`**
  - **Description**: Alphabetical/roll-ordered candidate desk assignment list.

- **`GET /api/v1/exams/theory/sittings/{id}/export/attendance-sheet?room_id={room_id}`**
  - **Description**: Invigilator attendance verification sheet with signature placeholders.

- **`GET /api/v1/exams/practical/sittings/{id}/export/workstation-list`**
  - **Description**: Practical batch workstation roster.

---

## 8. Controlled Publication & Student Portal Endpoints (Phase 10 Implemented)

### 8.1 Controlled Publication (Strict 9-Step Transaction)

Publication is an atomic database transaction. Zero external services are invoked within the transaction boundary.

#### Process:
1. **Authorise publisher** (Role checked: `INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, or `EXAM_CONTROLLER`).
2. **Verify expected draft revision** (Rejects stale revisions with HTTP 409).
3. **Lock the documented publication scope** (Exclusive lock on academic term).
4. **Validate against current active shared-resource reservations** (Rejects competing publications with HTTP 409).
5. **Verify the complete draft** (Independent verifier: `ScheduleChecker.validate` or seating engine verifier).
6. **Write immutable publication records** (`Publication` table with snapshots, diffs, and checker reports).
7. **Update active reservations** (`SharedResourceReservation` table).
8. **Write communication outbox events** (`CommunicationOutbox` transactional outbox).
9. **Commit**.

#### Endpoints:

- **`GET /api/v1/publications/pre-publish-review/{draft_id}`**
  - **Roles**: Staff (`TIMETABLE_COORDINATOR`, `INSTITUTION_ADMINISTRATOR`).
  - **Description**: Computes independent checker report, changed sessions/seats, affected teachers & students, unmet soft preferences, and reservation conflict probe before publishing.
  - **Response `200 OK`**: `PrePublishReviewOut`.

- **`POST /api/v1/publications/publish`**
  - **Roles**: Staff (`TIMETABLE_COORDINATOR`, `INSTITUTION_ADMINISTRATOR`, `EXAM_CONTROLLER`).
  - **Request Body**:
    ```json
    {
      "draft_id": "draft-id-123",
      "publication_type": "TIMETABLE",
      "expected_revision": 2,
      "publication_note": "Official Autumn 2026 Release v1"
    }
    ```
  - **Response `201 Created`**: `PublicationOut` with immutable snapshot, diff summary, and SHA-256 audit checksum.
  - **Response `409 Conflict`**: Stale revision (`STALE_REVISION`) or resource double-booking collision (`RESOURCE_RESERVATION_CONFLICT`).

- **`GET /api/v1/publications`**
  - **Parameters**: `publication_type` (optional), `academic_term_id` (optional).
  - **Response `200 OK`**: `List[PublicationSummaryOut]`.

- **`GET /api/v1/publications/{id}`**
  - **Response `200 OK`**: Full `PublicationOut` with snapshots.

- **`GET /api/v1/publications/{id}/diff/{compare_id}`**
  - **Response `200 OK`**: `PublicationDiffOut` with granular added, modified, and removed sessions.

- **`POST /api/v1/publications/{id}/restore`**
  - **Description**: Non-destructive rollback. Creates a brand new editable draft (Rev #1) from the publication's immutable snapshot and immediately revalidates it with the independent checker. **Never deletes publication history**.
  - **Response `200 OK`**: `TimetableDraftOut` with `revision = 1` and `status = 'CHECKED'` (or `'INVALID'`).

---

### 8.2 Real Student Portal Endpoints (Session-Derived Identity)

**Security Rule**: Student identity is derived exclusively from the authenticated server session token (`req.state.current_user` -> `Student` profile). Own-data endpoints accept zero student ID parameters and authoritatively reject cross-student queries with HTTP 403. Students can never view unpublished drafts.

- **`GET /api/v1/student/me`**
  - **Response `200 OK`**: `StudentProfileOut` (candidate roll number, department, name, email).

- **`GET /api/v1/student/home`**
  - **Response `200 OK`**: `StudentHomeOut` (profile, `is_published`, `next_up` occurrence, `today_schedule`, `upcoming_exams`, `practical_sessions`, `recent_changes`, `publication_version`).

- **`GET /api/v1/student/timetable?week_start_date=YYYY-MM-DD`**
  - **Description**: Server-derived dated occurrences for student's enrolled courses with term timezone and date-specific calendar exception overrides.
  - **Response `200 OK`**: `StudentTimetableResponse` (occurrences with `is_cancelled` and `cancellation_reason` if holiday).

- **`GET /api/v1/student/exams`**
  - **Description**: Theory examination seating hall tickets with exact bench labels (`bench_label`), hall names, date/times, and accessibility compliance. Confidential medical notes stripped.
  - **Response `200 OK`**: `List[StudentExamSeatOut]`.

- **`GET /api/v1/student/practicals`**
  - **Description**: Laboratory workstation allocations with hardware terminal labels, operating system, and invigilator details.
  - **Response `200 OK`**: `List[StudentPracticalOut]`.

- **`GET /api/v1/student/recent-changes`**
  - **Description**: Immutable audit change log of published timetable updates and seating notices.
  - **Response `200 OK`**: `List[StudentChangeNoticeOut]`.

- **`POST /api/v1/student/change-password`**
  - **Request Body**: `{"current_password": "...", "new_password": "..."}`.
  - **Response `200 OK`**: `{"message": "Password changed successfully."}`.


---

## 11. Communication, Outbox & Calendar API (Phase 11)

### `GET /api/v1/communication/notifications`
- **Auth**: Requires authenticated user session.
- **Query Parameters**:
  - `category` (optional): Filter by `ACADEMIC_CHANGE`, `OPERATIONAL_ALERT`, `SECURITY_EVENT`, `SCHEDULED_REMINDER`.
  - `unread_only` (optional, boolean): If true, filters only unread notifications.
  - `limit` (int, default 50)
  - `offset` (int, default 0)
- **Response**: `NotificationListResponse` containing `items: AppNotification[]`, `total: int`, `unread_count: int`.

### `GET /api/v1/communication/notifications/unread-count`
- **Auth**: Requires authenticated user session.
- **Response**: `{"unread_count": int}`.

### `POST /api/v1/communication/notifications/{id}/read`
- **Auth**: Requires authenticated user session (user must be recipient).
- **Response**: Updated `AppNotification` with `is_read: true` and `read_at: timestamp`.

### `POST /api/v1/communication/notifications/mark-all-read`
- **Auth**: Requires authenticated user session.
- **Response**: `{"marked_count": int}`.

### `GET /api/v1/communication/preferences`
- **Auth**: Requires authenticated user session.
- **Response**: `NotificationPreferencesResponse` with `quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`, category flags, email, and calendar sync flags.

### `PUT /api/v1/communication/preferences`
- **Auth**: Requires authenticated user session.
- **Body**: Partial `NotificationPreferencesUpdate`.
- **Response**: Updated `NotificationPreferencesResponse`.

### `GET /api/v1/communication/events/stream`
- **Auth**: Authenticated via same-origin session cookie or Authorization header. **Zero session tokens in URLs**.
- **Headers**:
  - `Last-Event-ID` (optional): Replays missed events from in-memory ring buffer upon reconnection.
- **Response**: `text/event-stream` emitting `NOTIFICATION_NEW`, `PUBLICATION_UPDATED`, and `JOB_STATUS_UPDATED` events scoped to institution and user.

### `GET /api/v1/communication/events/poll`
- **Auth**: Requires authenticated user session.
- **Query Parameters**: `since: int` (last received event ID).
- **Response**: `{"events": SSEEvent[]}` (polling fallback when SSE connection drops).

### `GET /api/v1/communication/outbox`
- **Auth**: Requires authorized staff (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`).
- **Query Parameters**: `status` (optional: `PENDING`, `DISPATCHED`, `FAILED`), `limit: int`.
- **Response**: `OutboxEventResponse[]` with status, retry counts, error details, and next retry timestamp.

### `POST /api/v1/communication/outbox/{id}/retry`
- **Auth**: Requires authorized staff.
- **Response**: Updated `OutboxEventResponse`. Idempotent delivery guarantees zero duplicate notifications or calendar events.

### `GET /api/v1/communication/calendar/status`
- **Auth**: Requires authenticated user session.
- **Response**: `CalendarStatusResponse`. If `GOOGLE_CALENDAR_ENABLED` is false or credentials absent, returns `configured: false`, `status: "NOT_CONFIGURED"` and setup guidance instructions.

### `GET /api/v1/communication/calendar/auth-url`
- **Auth**: Requires authenticated user session.
- **Response**: `{"auth_url": string, "state": string}` (cryptographically signed state token with CSRF protection).

### `GET /api/v1/communication/calendar/callback`
- **Query Parameters**: `code: string`, `state: string`.
- **Response**: `{"success": true, "message": string}`. Encrypts tokens with Fernet and links secondary "Scheduler - Academic Calendar".

### `POST /api/v1/communication/calendar/sync`
- **Auth**: Requires authenticated user session.
- **Response**: `{"synced": bool, "count": int}`. Authoritative one-way sync. Calendar failures never undo publications.

### `POST /api/v1/communication/calendar/disconnect`
- **Auth**: Requires authenticated user session.
- **Response**: `{"disconnected": true}`. Deletes encrypted tokens and unlinks calendar.

---

## 13. Feedback & Contact Endpoints (`/api/v1/feedback`)

### 13.1 Submit Public Contact Inquiry
- **Endpoint**: `POST /api/v1/feedback/public`
- **Auth**: Public (Unauthenticated / Anonymous permitted)
- **Rate Limit**: 10 requests / hour / IP
- **Request Body**:
  ```json
  {
    "name": "Dr. Arthur Pendelton",
    "email": "arthur@institution.edu",
    "category": "GENERAL_INQUIRY",
    "subject": "Inquiry regarding pilot timetable integration",
    "message": "We would like to test the scheduler with our faculty...",
    "honeypot": ""
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "reference_code": "FB-X9Y2Z1W8",
    "message": "Thank you for contacting us. Your message has been received securely."
  }
  ```

### 13.2 Submit Authenticated Feedback
- **Endpoint**: `POST /api/v1/feedback/submit`
- **Auth**: Authenticated User (Student, Teacher, Coordinator, Admin)
- **Request Body**:
  ```json
  {
    "category": "BUG_REPORT",
    "subject": "Audio jack in Lecture Hall B broken",
    "message": "Podium 3.5mm microphone audio jack is loose and crackles.",
    "page_reference": "Timetables -> Hall B"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "reference_code": "FB-K4J8M2N1",
    "message": "Your feedback has been logged securely and will be reviewed by your institution administrators.",
    "submission": {
      "id": "uuid-...",
      "reference_code": "FB-K4J8M2N1",
      "category": "BUG_REPORT",
      "subject": "Audio jack in Lecture Hall B broken",
      "message": "Podium 3.5mm microphone audio jack is loose and crackles.",
      "page_reference": "Timetables -> Hall B",
      "status": "new",
      "created_at": "2026-10-22T21:00:00Z"
    }
  }
  ```

### 13.3 Submitter's Own Feedback List
- **Endpoint**: `GET /api/v1/feedback/my-submissions`
- **Auth**: Authenticated Submitter
- **Response** (`200 OK`): List of `UserSubmittedFeedback` (strictly excludes internal notes and reviewer identity).

### 13.4 Administrative Feedback Triage List
- **Endpoint**: `GET /api/v1/feedback/manage`
- **Auth**: Institutional Reviewers (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`, or platform reviewer)
- **Query Params**: `status`, `category`, `search`, `include_public`, `limit`, `offset`
- **Response** (`200 OK`): List of `FeedbackManageItem` scoped to reviewer's institution.

### 13.5 Administrative Detail & Internal Notes
- **Endpoint**: `GET /api/v1/feedback/manage/{id}`
- **Endpoint**: `PUT /api/v1/feedback/manage/{id}/status`
- **Endpoint**: `POST /api/v1/feedback/manage/{id}/notes`
- **Auth**: Institutional Reviewers (Cross-institution access returns `403 Forbidden`)


---

## 14. AI-Assisted Interpretation & Diagnostic Endpoints (`/api/v1/ai`)

### 14.1 Operational Status & Configuration Visibility
- **Endpoint**: `GET /api/v1/ai/status`
- **Auth**: Authenticated User (`Membership` required)
- **Response** (`200 OK`):
  ```json
  {
    "enabled": true,
    "is_available": true,
    "provider": "mock",
    "model_name": "mock-deterministic-v1",
    "total_requests": 14,
    "total_tokens_processed": 5120,
    "estimated_cost_usd": 0.0,
    "notice": "Air-gap compliant deterministic provider. No SQL execution or tool privileges permitted.",
    "disclaimer": "AI suggestions are unverified interpretations. You must review and validate against institutional rules before applying."
  }
  ```

### 14.2 Interpret Timetable Change Request
- **Endpoint**: `POST /api/v1/ai/interpret-change`
- **Auth**: Authorized Staff (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`) + CSRF token
- **Request Body**:
  ```json
  {
    "draft_id": "uuid-...",
    "request_text": "Move Dr. Alan Turing CS101 Friday afternoon class to Tuesday morning in Room 101"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "raw_summary": "Move session for CS101 to Day 1 Period 2 in Room 101",
    "confidence_score": 0.85,
    "is_ambiguous": true,
    "ambiguities": [
      {
        "type": "UNDEFINED_TIME",
        "description": "Request mentions 'afternoon' without specifying an exact period or start time.",
        "suggested_clarification": "Defaulted candidate to Period 5 (14:00), but please confirm period 4 vs 5 vs 6."
      }
    ],
    "proposed_changes": [
      {
        "session_id": "sess-cs101",
        "session_name": "Computer Science I Lecture",
        "course_code": "CS101",
        "original_day": 4,
        "original_period": 5,
        "original_room_id": "r-101",
        "original_room_name": "Room 101",
        "original_teacher_id": "t-alan",
        "original_teacher_name": "Dr. Alan Turing",
        "proposed_day": 1,
        "proposed_period": 2,
        "proposed_room_id": "r-101",
        "proposed_room_name": "Room 101",
        "proposed_teacher_id": "t-alan",
        "proposed_teacher_name": "Dr. Alan Turing",
        "is_hard_constraint": true,
        "is_term_wide": true,
        "is_resolved": true,
        "resolution_notes": []
      }
    ],
    "draft_id": "uuid-...",
    "draft_revision": 1,
    "disclaimer": "AI suggestions are unverified candidate interpretations. You must review and validate against institutional rules before applying."
  }
  ```

### 14.3 Approve & Apply Interpreted Changes to Draft
- **Endpoint**: `POST /api/v1/ai/apply-change`
- **Auth**: Authorized Staff (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`) + CSRF token
- **Optimistic Concurrency**: Rejects with `409 Conflict` if `draft.revision != expected_revision`.
- **Request Body**:
  ```json
  {
    "draft_id": "uuid-...",
    "expected_revision": 1,
    "changes": [ ... ]
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "draft_id": "uuid-...",
    "new_revision": 2,
    "applied_count": 1,
    "checker_report": {
      "is_valid": true,
      "total_required": 14,
      "total_assigned": 14,
      "violations_count": 0,
      "violations": []
    },
    "status": "CHECKED",
    "message": "Successfully applied 1 interpreted changes to draft revision 2. Independent validation status: CHECKED."
  }
  ```

### 14.4 Explain Checker Violations
- **Endpoint**: `POST /api/v1/ai/explain-checker`
- **Auth**: Authorized Staff + CSRF token
- **Request Body**:
  ```json
  {
    "draft_id": "uuid-...",
    "violations": [ ... ]
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "explanations": [
      {
        "violation_code": "TEACHER_CONFLICT",
        "severity": "HARD",
        "plain_explanation": "Dr. Alan Turing is assigned to teach two classes simultaneously on Tuesday Period 2.",
        "root_cause": "Concurrent session overlap across Cohort CS-A and CS-B.",
        "actionable_resolutions": [
          "Move CS-B lecture to Tuesday Period 4.",
          "Reassign CS-A lecture to another available lecturer."
        ]
      }
    ],
    "general_recommendations": [ ... ],
    "disclaimer": "Checker explanations are advisory diagnostic candidates. Authoritative solver validation rules take precedence."
  }
  ```

### 14.5 Propose Tabular Import Column Mappings
- **Endpoint**: `POST /api/v1/ai/propose-mappings`
- **Auth**: Authorized Staff + CSRF token
- **Request Body**:
  ```json
  {
    "headers": ["Subject Code", "Lecturer", "Hall", "Period", "Day of Week"],
    "sample_rows": [["CS101", "Dr. Alan Turing", "Room 101", "2", "Tuesday"]]
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "mappings": {
      "Subject Code": "course_code",
      "Lecturer": "teacher_name",
      "Hall": "room_code",
      "Period": "period",
      "Day of Week": "day_of_week"
    },
    "confidence_scores": {
      "Subject Code": 0.95,
      "Lecturer": 0.95,
      "Hall": 0.85,
      "Period": 0.98,
      "Day of Week": 0.98
    },
    "unmapped_columns": [],
    "notes": [ ... ]
  }
  ```
