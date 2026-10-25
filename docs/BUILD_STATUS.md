# Scheduler Build & Verification Status

## Phase 1: Scheduler Foundation

### 1. Completed Functionality
- **Architecture & Directory Scaffolding**:
  Established clean, robust production structure matching all specification requirements:
  ```
  Scheduler/
  ├── frontend/          React 18 + Vite 5 + TypeScript 5 + Tailwind CSS + TanStack Query v5
  ├── backend/           FastAPI + SQLAlchemy 2.x + Psycopg 3 + Alembic + Pydantic v2
  ├── docs/              SPEC, API contracts, architectural decisions, test plan
  ├── deployment/        Production Dockerfiles, Nginx reverse proxy & SPA configurations
  ├── compose.yaml       Containerized PostgreSQL 16, backend, frontend, and proxy
  ├── .env.example       Environment variable template with PostgreSQL & secret defaults
  ├── .gitignore         Comprehensive ignore rules for Python, Node, database, and OS files
  └── README.md          Project overview, exact local startup commands, and architecture
  ```
- **Mutual Compatibility & Zero Floating Versions Policy**:
  - Python dependencies in `backend/requirements.txt` strictly pinned with exact versions (`==`) and complete frozen dependency manifest in `backend/requirements.lock`.
  - Frontend dependencies in `frontend/package.json` strictly pinned to exact versions (zero `^` or `~` caret/tilde prefixes) and locked via `frontend/package-lock.json`.
- **Health Probes Implementation**:
  - `GET /health/live`: Lightweight process liveness check. Operates with zero database dependency.
  - `GET /health/ready`: Robust database readiness probe executing active `SELECT 1` queries. Returns HTTP 503 if database connectivity is broken.
  - Same-origin proxy compatibility: Handlers also mapped under `/api/health/*` to support seamless frontend proxying.
- **Minimalist Light Design System Frontend**:
  - Custom light theme palette (#F7F8FA background, #FFFFFF surface, #14213D text/navy, #0E7C66 primary teal, #F2B134 warning amber, #D9480F conflict coral).
  - Soft borders, restrained shadows, consistent spacing.
  - Semantic vector icons via Lucide React; zero emoji icons.
  - Multi-modal state signaling (color + text labels + ARIA roles) ensuring state does not rely on color alone.
  - TanStack Query auto-polling and manual refresh controls.
  - Non-drag accessible alternatives principle established in design tokens.

---

## Phase 2: Database Foundation

### 1. Completed Functionality
- **Core Relational Schema & 22 Required Entities**:
  Designed and implemented all requested domain models using SQLAlchemy 2.x declarative syntax:
  - `institutions`: Multi-tenant root entity with unique codes and IANA default timezone.
  - `departments`: Institutional divisions with tenant-scoped codes.
  - `academic_terms`: Academic scheduling terms with explicit IANA timezone and active status.
  - `users`: Decoupled global authentication identity (`email`, `hashed_password`, `full_name`, `is_active`).
  - `memberships`: Institutional role assignment with 5 governed roles (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`, `TEACHER`, `STUDENT`).
  - `teachers`: Institutional faculty records with employee ID, department, and max weekly teaching hours.
  - `teacher_qualifications`: Instructor eligibility matrix decoupling subject certification from operational assignment.
  - `students`: Enrolled learner records with tenant-unique roll number, batch year, and department.
  - `subjects`: Curricular units with theory, practical, or integrated classifications and contact hours.
  - `course_offerings`: Term-specific academic subject delivery within a department.
  - `sections`: Cohort/division partitions with target headcount capacity.
  - `enrolments`: Student-to-section registration with status (`ENROLLED`, `WAITLISTED`, `DROPPED`, `COMPLETED`).
  - `buildings`: Campus physical infrastructure with tenant-scoped codes.
  - `rooms`: Physical instructional spaces explicitly distinguishing architectural capacity (`physical_capacity`) from anti-cheating exam seating capacity (`usable_exam_benches`).
  - `seats`: Physical exam desks/theory benches with coordinates (`row_number`, `column_number`) and status (`is_usable`, `is_accessible`, `is_blocked`).
  - `workstations`: Practical laboratory terminals with operating system and JSON hardware/software features (`gpu`, `matlab`, `ram_gb`, etc.).
  - `sessions`: Scheduled academic blocks supporting recurring weekly patterns (`day_of_week`, `start_time`, `end_time`) and dated exam sittings (`start_datetime`, `end_datetime`).
  - `availability_rules`: Weekly recurring availability and blackout intervals for teachers, rooms, and sections.
  - `calendar_exceptions`: Institutional and departmental exceptions (holidays, blackout dates, maintenance windows).
  - `session_requirements`: Specialized room, seat, and computing requirements for timetabling sessions.
  - `constraint_rules`: Extensible hard and soft scheduling rules with JSON parameter payloads and weights.
  - `audit_events`: Immutable security and administrative change logs with client IP address and event details.

- **Multi-Tenant Safeguards & Composite Foreign Keys**:
  - Enforced composite foreign key constraints across all tenant-owned relationships preventing cross-tenant leakage.

- **Explicit Term Timezone Handling**:
  - Centralized timezone service in `app.core.timezone` ensuring all stored timestamps are UTC with explicit term IANA timezone conversion.

- **Idempotent Development Seed**:
  - Seed script `app.seeds.seed` generating synthetic institutions `APEX` and `BEACON` with all 5 roles and rich facilities.

---

## Phase 3: Authentication and Authorisation

### 1. Completed Functionality
- **Argon2id Password Hashing**:
  - Integrated `argon2-cffi==25.1.0` and `argon2-cffi-bindings==26.1.0` (pinned in `requirements.txt` and `requirements.lock`).
  - Configured with RFC 9106 recommended interactive parameters: `time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`.
  - Re-seeded development database with standard `$argon2id$...` hashes for all seeded accounts.

- **Cryptographically Random Server-Side Sessions with SHA-256 Digest-Only Storage**:
  - Tokens generated with `secrets.token_urlsafe(32)` (256-bit entropy).
  - Only `SHA-256` token digests are persisted in `user_sessions.session_token_hash`. The raw token exists solely in the client cookie jar.
  - Migration `84ce4c3a458d` created the `user_sessions` table with indexes on `session_token_hash`, `user_id`, `expires_at`, and `revoked_at`.
  - Added `must_change_password` boolean to `users` table.

- **HttpOnly Cookie Transport & Explicit Development Isolation**:
  - `scheduler_session` cookie dispatched with `httponly=True` and `samesite="lax"`.
  - Configurable `secure` flag: `COOKIE_SECURE=True` in production HTTPS, `COOKIE_SECURE=False` explicitly documented for local development.

- **CSRF Protection via Double-Submit Cookie Pattern**:
  - On authentication, a session-bound CSRF token is issued in cookie `scheduler_csrf` (`samesite="lax"`).
  - Mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`) require the `X-CSRF-Token` header.
  - `verify_csrf_token` FastAPI dependency enforces constant-time matching (`secrets.compare_digest`).

- **Session Rotation, Invalidation, and Expiry**:
  - Fresh session tokens generated upon login.
  - Password change revokes all other active sessions and rotates the current session.
  - Explicit logout (`POST /api/v1/auth/logout`) sets `revoked_at` and clears browser cookies.
  - Selective revocation endpoint (`DELETE /api/v1/me/sessions/{id}`) allows revoking specific devices/sessions.

- **Forced Password Change & Administrative Reset Workflow**:
  - Temporary passwords generated by administrators (`POST /api/v1/admin/users/{id}/reset-password`) flag user with `must_change_password=True`.
  - Protected endpoints reject requests with `HTTP 403 Forbidden` (`X-Error-Code: PASSWORD_CHANGE_REQUIRED`) until `POST /api/v1/auth/change-password` succeeds.
  - Password complexity validator enforces length, uppercase, lowercase, numbers, and special symbols.
  - Cross-institution admin resets are strictly rejected with `HTTP 404 Not Found`.

- **Rate-Limiting Contract & Implementation**:
  - Abstract base class `BaseRateLimiter` in `app.core.rate_limit`.
  - Thread-safe `InMemorySlidingWindowRateLimiter` applied to login (5/min), password change (5/min), and admin reset (10/min).
  - Architecture documentation in `docs/PERMISSIONS.md` and `docs/DECISIONS.md` details single-instance limitations and multi-node Redis migration path.

- **Anti-Enumeration Generic Failures & Timing Attack Mitigation**:
  - Login failures return generic `HTTP 401: "Invalid institution, identifier, or password."`
  - Constant-time dummy Argon2id verification (`_DUMMY_ARGON2_HASH`) runs when user or institution lookups fail to eliminate timing side-channels.

- **Audited Security Events without Secrets**:
  - All login successes/failures, logouts, password changes, admin resets, and session revocations log to `audit_events`.
  - Plaintext passwords, temporary credentials, raw session tokens, and CSRF tokens are completely redacted/omitted.

- **Reusable Dependency Injection**:
  - `get_current_session`: Validates session cookie digest, expiry, and revocation.
  - `get_current_user`: Resolves authenticated user with `must_change_password` check.
  - `get_current_membership`: Resolves institution-scoped role membership.
  - `require_roles`: Restricts endpoints to authorized roles.
  - `verify_institution_ownership`: Ensures objects belong to the caller's tenant.
  - `verify_student_ownership`: Restricts student-owned records to the calling student.
  - `verify_csrf_token`: Enforces double-submit CSRF tokens on mutating requests.

- **Frontend Security & UI**:
  - Zero storage of credentials or tokens in `localStorage`.
  - Automatic `credentials: 'include'` on all fetch requests.
  - Automatic `X-CSRF-Token` header injection on mutating requests.
  - Login view with institution code, identifier (email, teacher employee ID, or student PRN), password, and quick-switch demo badges.
  - First-password-change view with live password strength validation.
  - Custom event handlers for `auth:session-expired` and `auth:password-change-required`.
  - Role-tailored dashboards and navigation for all 5 roles (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`, `TEACHER`, `STUDENT`).
  - Active Session Manager with device detection, last activity, current session badge, and selective revocation.
  - Administrative reset guidance modal avoiding fake self-service email flows.

---

### 2. Verification & Test Outcomes

1. **Alembic Database Migrations**:
   - `python -m alembic upgrade head`: Applied migration `84ce4c3a458d` (`add_auth_sessions_and_password_change`). Schema current at head.

2. **Automated Pytest Suite (36/36 Passed)**:
   - `python -m pytest -v`: All 36 tests passing in 2.32s:
     - `test_successful_login_for_each_role_by_email` [Admin, Coordinator, Controller, Teacher, Student] (PASSED)
     - `test_teacher_login_via_assigned_employee_id` (PASSED)
     - `test_student_login_via_institution_scoped_prn` (PASSED)
     - `test_generic_failure_invalid_password` (PASSED)
     - `test_generic_failure_nonexistent_user` (PASSED)
     - `test_generic_failure_nonexistent_institution` (PASSED)
     - `test_student_cannot_access_another_students_record` (PASSED)
     - `test_cross_institution_admin_reset_denied` (PASSED)
     - `test_csrf_missing_token_rejected` (PASSED)
     - `test_csrf_mismatched_token_rejected` (PASSED)
     - `test_logout_invalidates_session` (PASSED)
     - `test_admin_reset_workflow_and_forced_password_change` (PASSED)
     - `test_password_change_invalidates_other_sessions` (PASSED)
     - `test_session_inspection_and_revocation` (PASSED)
     - `test_audit_logging_does_not_record_secrets` (PASSED)
     - Database foundation test suite: 12/12 PASSED.
     - Health test suite: 5/5 PASSED.

3. **Frontend Production Build**:
   - `npm run build`: TypeScript strict check and Vite production build passed cleanly in 2.05s with zero errors or warnings.

---

## Phase 4: Visual System, Public Website, and Role-Aware Shells

### 1. Completed Functionality

- **Design System & Typography**:
  - Implemented the refined educational planning design palette:
    - Neutral Background: `#F7F8FA`
    - White Surfaces: `#FFFFFF`
    - High-Contrast Navy Text: `#14213D`
    - Interactive Teal Actions: `#0E7C66`
    - Advisory Warnings: `#F2B134`
    - Strict Conflicts: `#D9480F`
    - Lavender Accent: `#A89FD8`
    - Pale Blue Accent: `#7EB8DA`
    - Soft grey borders (`#E2E8F0`) and restrained multi-level shadows.
  - Implemented typography system utilizing **Sora** for headings and **DM Sans** for body and interface labels, loaded non-blockingly via Google Fonts swap with robust system font fallbacks.
  - Multi-modal state signaling (color + text label + Lucide vector outline icon + ARIA attributes) across all interactive elements. Zero emoji interface icons.
  - Visible 2px teal focus rings (`focus-visible:ring-2 focus-visible:ring-teal`) and full keyboard accessibility.

- **Procedural 3D Public Landing Scene**:
  - Built custom spatial hero composition using **Three.js (0.170.0)**, **React Three Fiber (8.18.0)**, and **Drei (9.122.0)**:
    - Dominant floating weekly timetable board with rounded slab depth and subtle navy edge.
    - 5 day columns with color-coded session blocks (teal, pale blue, amber, lavender), break indicators, and a double-length practical block.
    - Supporting physical exam seating board with rows of benches and highlighted candidate bench.
    - Supporting practical laboratory board with workstation markers.
    - Validation checkmark token representing automated constraint verification.
  - Pure procedural geometry and code: zero external 3D models, zero paid assets, zero remote textures.
  - Clamped pointer parallax interaction (`< 0.12 rad`) with smooth linear interpolation.
  - Accessible HTML scene controls ("Timetables", "Practical exams", "Theory seating") updating camera viewpoint and nearby explanatory HTML.
  - Demand-based rendering and automatic pause when the hero is offscreen via `IntersectionObserver`.

- **Accessibility & Resilient Fallbacks**:
  - `useReducedMotion` hook respecting `prefers-reduced-motion: reduce`: disables pointer parallax and idle animation, locking to a static view.
  - `SchedulerSceneFallback`: High-fidelity SVG vector illustration matching the 3D composition with exact proportions and color scheme.
  - WebGL context availability detector: gracefully serves SVG fallback on machines without WebGL or upon context creation failure.
  - Error Boundary isolating the WebGL canvas, preventing canvas runtime failures from impacting the page.
  - Reserved aspect ratio container preventing layout shifts (CLS).
  - High text contrast and keyboard-accessible mobile drawer controls.

- **Public Landing Page (10 Cohesive Sections)**:
  1. *Navigation*: Scheduler wordmark, section anchors (#product-modules, #workflow, #security, #faq), real Login modal action, and Contact feedback anchor.
  2. *Hero Section*: "Less scheduling. More teaching." headline, supporting text, "Explore Scheduler" smooth scroll, real "Log in" action, illustrative preview label, and 3D hero scene with scene emphasis controls.
  3. *Product Modules*: 3 clean cards for Class Timetables, Practical Examinations, and Theory Exam Seating with shallow CSS hover depth and scroll destinations.
  4. *Workflow*: 4-step progressive disclosure (Import institutional data, Configure rules and availability, Generate and check draft, Review and publish).
  5. *Teacher Workspace Preview*: Synthetic weekly timetable, draft badge, validation conflict summary, and review action (clearly labeled illustrative preview).
  6. *Student Experience Preview*: Next class card, practical batch/terminal allocation, exam hall bench ticket, and timetable change notification (clearly labeled synthetic preview).
  7. *Implemented Security*: Honest description strictly limited to Phase 2/3 capabilities (multi-tenant boundaries, 5 RBAC roles, HttpOnly cookie sessions with Argon2id and SHA-256 token digests, CSRF protection, audit logging). No fake claims or certifications.
  8. *FAQ*: Keyboard-navigable accordion addressing real scheduling constraints, data ownership, and multi-tenant isolation.
  9. *Contact & Feedback*: Real feedback trigger with honest notice that backend feedback triage is scheduled for Phase 6. No fake submissions.
  10. *Footer*: Institutional wordmark, quick links, and accessible dialogs for Privacy Statement and Accessibility Statement.

- **Role-Aware Authenticated Application Shells**:
  - Preserved Phase 3 authentication and authorization intact.
  - Flat 2D operational dashboard layouts: zero 3D canvas overhead on authenticated routes.
  - Staff Shell (`StaffLayout`):
    - TopBar: Wordmark, active academic term selector, notifications entry point, profile dropdown (active sessions modal, change password modal, sign out).
    - Sidebar & MobileNavigation: 8 role-governed links (Overview, Timetables, Examinations, Resources, Publish & History, Reports, Feedback, Settings).
  - Student Shell (`StudentLayout`):
    - TopBar: Compact header with student profile status and sign out.
    - Sidebar & MobileNavigation: 6 student-tailored links (Home, Timetable, Practicals, Exams & Seats, Notifications, Profile).
  - Transparent Unbuilt-Module Signaling:
    - All not-yet-implemented features display standard `NotImplementedNotice` components ("Not implemented yet" with scheduled phase and architectural rationale). Zero fake API success states.
  - Student Ownership Boundary Safeguard:
    - Interactive test on Student Exams & Seats page demonstrating HTTP 200 OK for own record vs HTTP 403 Forbidden when attempting cross-student inspection.

- **Component Architecture & Code-Splitting**:
  - Clean separation into `components/common/`, `components/landing/`, `components/layout/`, `pages/staff/`, `pages/student/`, and `hooks/`.
  - Dynamic `React.lazy` code-splitting of `SchedulerScene`: Three.js, R3F, and Drei bundles are loaded only when the public landing page mounts and are completely omitted from authenticated dashboard chunks.

---

### 2. Verification & Test Outcomes

1. **Frontend TypeScript & Production Build**:
   - `npm run build`: Strict TypeScript check (`noUnusedLocals: true`, `noUnusedParameters: true`) and Vite production bundle passed cleanly with exit code 0.
   - Bundle breakdown:
     - `dist/index.html`: 1.02 kB
     - `dist/assets/index-Bom_JiMt.css`: 31.43 kB (gzip: 6.38 kB)
     - `dist/assets/index-DEjT61KP.js`: 347.13 kB (gzip: 94.22 kB) — Main application, shells, and authenticated dashboards
     - `dist/assets/SchedulerScene-32erCZ0H.js`: 831.45 kB (gzip: 223.33 kB) — Lazily loaded 3D landing scene chunk
   - Authenticated routes load only the 94.22 kB gzipped main chunk; the 223.33 kB 3D chunk is isolated exclusively to the public landing page.

2. **Automated Pytest Suite (36/36 Passed)**:
   - `python -m pytest -v`: All 36 authentication, database, and health tests passing in 6.73s:
     - Authentication & authorization suite: 19/19 PASSED.
     - Database foundation suite: 12/12 PASSED.
     - Health probe suite: 5/5 PASSED.

3. **Accessibility & Resilience Verification**:
   - Reduced-motion preference verified: all canvas animation suspended, clamped static orientation preserved, or SVG fallback rendered.
   - WebGL disabled test: `SchedulerSceneContainer` detects lack of WebGL context and gracefully displays SVG fallback.
   - Visible focus states: 2px teal focus rings confirmed on all interactive buttons, inputs, and links.
   - Zero keyboard traps: dialogs and menus utilize `useKeyboardTrap` with `Escape` dismiss and tab cycling.
   - Zero horizontal overflow across mobile (375px), tablet (768px), and desktop (1440px) viewports.

---

## Phase 6: Durable Background Processing

### 1. Completed Functionality

- **PostgreSQL-Backed Leased Job System (`jobs` Table)**:
  - Created declarative model `Job` with full operational auditability:
    - Primary key UUID, `institution_id` with foreign key and index.
    - `job_type`, `input_reference` (JSON), `status` (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`).
    - Scheduling: `available_at`, `started_at`, `finished_at`.
    - Lease & Fencing: `attempt_count`, `max_attempts`, `lease_owner`, `lease_token` (UUID hex), `lease_expiry`, `heartbeat_at`.
    - Progress & Diagnostics: `phase_label` (strictly meaningful strings, NO fake percentages), `cancellation_requested` (Boolean), `result_reference` (JSON), `error_code`, `error_message`.
  - Applied Alembic migration `3ece2f9a41ab` (`add_jobs_table`) with specialized indexes:
    - `ix_jobs_claim`: composite `(status, available_at)`
    - `ix_jobs_tenant_status`: composite `(institution_id, status)`
    - `ix_jobs_lease_recovery`: composite `(status, lease_expiry)`
    - `ix_jobs_lease_token`: single `(lease_token)` for fenced updates

- **Short Transactions & Non-Blocking Claims**:
  - `JobService.claim_next_job`: Claims candidate jobs in a fast atomic transaction with `FOR UPDATE SKIP LOCKED` on PostgreSQL.
  - Transaction commits immediately after acquiring the lease. CPU-heavy solver tasks execute completely outside database transactions.

- **Fencing Tokens & Idempotent Finalization**:
  - Every claim generates a cryptographically random `lease_token`.
  - All heartbeats, phase updates, and finalizations execute `WHERE id = :id AND lease_token = :lease_token`.
  - If a worker's lease expires and another worker re-claims the job, the stale worker is fenced out (affected rows = 0) and cannot corrupt state or overwrite newer results.

- **Heartbeat Loop & Cancellation Detection**:
  - Asynchronous background heartbeat thread updates `heartbeat_at` and extends `lease_expiry` every 5 seconds.
  - Detects `cancellation_requested = True` during execution and terminates cooperatively, marking job `CANCELLED` with structured error code `CANCELLED_BY_USER`.

- **Expired Lease Recovery & Retry Policy**:
  - `JobService.recover_expired_leases`: Automatically reclaims jobs from crashed workers where `lease_expiry < now`.
  - Exponential backoff retry policy (`calculate_backoff` = `5s * 2^(attempt - 1)`).
  - Automatically transitions to `FAILED` with `MAX_ATTEMPTS_EXCEEDED` once `max_attempts` is exhausted.

- **Per-Institution Concurrency Limits**:
  - Dynamically enforces maximum concurrent running jobs per tenant (default: 2) to eliminate noisy-neighbor resource monopolization.

- **Dedicated Worker Entry Point (`backend/app/worker.py`)**:
  - Separate executable process entry point (`python -m app.worker`).
  - Pluggable handler registry (`TIMETABLE_SOLVE`, `SEATING_ALLOCATION`, `REPORT_GENERATION`, `GENERIC_TASK`).
  - Graceful shutdown handling `SIGINT`, `SIGTERM`, and `SIGBREAK` with in-flight task drain.

- **REST API Endpoints**:
  - `GET /api/v1/jobs/{id}`: Returns job details with tenant isolation (`verify_institution_ownership`).
  - `POST /api/v1/jobs/{id}/cancel`: Role-aware cancellation with CSRF validation.
  - `POST /api/v1/jobs`: Enqueue background job.
  - `GET /api/v1/jobs`: List tenant jobs.

- **Frontend Job Status Component (`JobStatusCard.tsx`)**:
  - Built reusable, responsive component with TanStack Query polling (1500ms while active).
  - Meaningful phase labels and live elapsed time timer (`Xm Ys` or `Xs`). Strictly NO fake completion percentages.
  - Cancel confirmation dialog with immediate cancellation notice.
  - Result summary on completion and structured failure diagnostics on error.
  - Integrated into `StaffTimetables.tsx` and `StaffExaminations.tsx` for dispatching solver jobs live.

---

### 2. Verification & Test Outcomes

1. **Automated Pytest Suite (44/44 Passed)**:
   - `python -m pytest -v`: All 44 tests passing in 5.02s:
     - `test_job_survives_api_restart` (PASSED)
     - `test_worker_crash_leads_to_lease_recovery` (PASSED)
     - `test_duplicate_attempts_do_not_duplicate_final_results_via_fencing` (PASSED)
     - `test_cancellation_behaviour` (PASSED)
     - `test_cross_tenant_job_access_denied` (PASSED)
     - `test_two_workers_cannot_claim_same_active_attempt` (PASSED)
     - `test_per_institution_concurrency_limits` (PASSED)
     - `test_max_attempts_and_retry_backoff` (PASSED)
     - Authentication & authorization suite: 19/19 PASSED.
     - Database foundation suite: 12/12 PASSED.
     - Health probe suite: 5/5 PASSED.

2. **Frontend Production Build**:
   - `npm run build`: Strict TypeScript check and Vite production build passed cleanly in 28.69s with zero errors.

---

## Phase 7: Timetable Generation (OR-Tools CP-SAT & Independent Checker)

### 1. Completed Functionality

- **Mathematical CP-SAT Formulation (`docs/SCHEDULING_MODEL.md`)**:
  - Fully formalized mathematical timetabling model with index sets $S, T, R, G, D, P$.
  - Boolean decision variables $x_{s, d, p, r} \in \{0, 1\}$ with valid start period bounds $p + d_s \le |P|$.
  - Hard Constraints:
    - **(C1) Exactly One Assignment**: $\sum x_{s, d, p, r} = 1$ for every required session.
    - **(C2) Full-Duration Resource Occupancy**: Non-wrapping contiguous period occupancy.
    - **(C3) Teacher Double-Booking Prevention**: $\sum_{s \in S : teacher(s) = t} \le 1$ at every $(d, \pi)$.
    - **(C4) Room Double-Booking Prevention**: $\sum_{s \in S} \le 1$ in each physical room at $(d, \pi)$.
    - **(C5) Cohort/Section Double-Booking Prevention**: $\sum_{s \in S : section(s) = g} \le 1$ at every $(d, \pi)$.
    - **(C6) Availability Enforcement**: Strict compliance with teacher blackout hours and room maintenance windows.
    - **(C7) Room Suitability & Capacity**: Filtered candidate assignments enforcing room classification (`THEORY` vs `PRACTICAL`), required hardware features, and room capacity $\ge$ cohort size.
    - **(C8) Multi-Period Practical Blocks**: Contiguous multi-hour sessions anchored without mid-session room changes.
    - **(C9) Locked Assignments**: Fixed anchor slots enforced via fixed variable constraints.
    - **(C10) Configurable Breaks**: Campus lunch and institutional assembly blackout periods.
  - Soft Preference Optimization:
    - Minimizes weighted penalties for undesirable late periods, non-preferred slots, and cohort relocation.

- **Explicit Unsupported Rule Rejection**:
  - Supported institutional cases clearly demarcated from unsupported cases.
  - Requests containing unsupported rules (floating lunch breaks, multi-campus transit, fractional split-teacher co-teaching, dynamic unpartitioned groups, cross-tenant resource sharing) are strictly rejected with error code `UNSUPPORTED_RULE`.

- **Immutable Input Snapshots & Version Tracking**:
  - Database model `TimetableDraft` (`backend/app/models/schedule.py`) and Alembic migration `45268688df71`.
  - Cryptographic SHA-256 digest `input_hash` computed from canonical JSON snapshot.
  - Explicit version metadata: `model_version: "1.0.0"`, `rule_version: "1.0.0"`, `checker_version: "1.0.0"`, `solver_version: "ortools-9.15"`.
  - Solver metrics recorded: `solver_runtime_seconds`, `solver_objective`, `solver_best_bound`.

- **Robust Solver Output States**:
  - Reports standard statuses: `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`.
  - Strictly follows rule: **Never label UNKNOWN as proven infeasibility.**
  - Usable timetable results accepted **only after independent validation passes with zero violations**.

- **Completely Independent Verification Checker (`backend/app/services/schedule_checker.py`)**:
  - Standalone pure-Python validator that consumes plain output assignments JSON.
  - **Does NOT reuse or invoke any OR-Tools model construction code.**
  - Verifies:
    1. Completeness: all required sessions assigned.
    2. Duplication & Extraneous: no duplicate session assignments or unrequested IDs.
    3. Duration Integrity: every assignment spans its designated contiguous time periods.
    4. Teacher Overlaps: zero concurrent double-booking for any instructor.
    5. Room Overlaps: zero concurrent double-booking in any physical room.
    6. Cohort/Section Overlaps: zero concurrent double-booking for any student section.
    7. Availability Compliance: zero sessions during teacher or room blackout periods.
    8. Capacity & Suitability: room capacity $\ge$ session capacity requirement, room type match, and feature subset match.
    9. Locked Commitments: exact adherence to pre-assigned day, period, and room coordinates.

- **Worker Solver Execution (`backend/app/worker.py`)**:
  - Solver tasks execute asynchronously via background worker under `TIMETABLE_SOLVE` job type.
  - Synchronous API requests never execute CP-SAT solving.
  - Generation transitions draft status through `SOLVING` -> `CHECKED` or `INFEASIBLE` / `UNKNOWN`.

- **REST API Endpoints (`backend/app/api/v1/timetable_drafts.py`)**:
  - `POST /api/v1/timetable-drafts`: Creates draft with immutable snapshot and SHA-256 hash.
  - `POST /api/v1/timetable-drafts/{id}/generate`: Enqueues solver job, returns HTTP 202 Accepted with job reference. Rejects published drafts with HTTP 400.
  - `POST /api/v1/timetable-drafts/{id}/check`: Triggers independent checker validation on plain assignments.
  - `GET /api/v1/timetable-drafts/{id}`: Returns status, metrics, assignments, and validation report with tenant isolation.

---

### 2. Verification & Test Outcomes

1. **Automated Pytest Suite (53/53 Passed)**:
   - `test_small_feasible_fixture_and_independent_checker`: Verified CP-SAT finds optimal solution and independent checker validates successfully.
   - `test_proven_infeasible_fixture`: Verified solver correctly identifies proven infeasibility (`INFEASIBLE`) when session demand exceeds room capacity.
   - `test_timeout_unknown_handling`: Verified search timeout yields `UNKNOWN`, strictly preserved without false infeasibility labeling.
   - `test_missing_session_mutation_detected`: Independent checker reliably catches missing session mutations.
   - `test_resource_overlap_mutations_detected`: Independent checker reliably catches injected teacher overlaps and room double-bookings.
   - `test_duration_and_capacity_violations_detected`: Independent checker reliably catches period duration mismatch and undersized room capacity violations.
   - `test_unsupported_rule_requests_rejected`: Verifies unsupported rule requests are rejected with HTTP 400 and structured error code `UNSUPPORTED_RULE`.
   - `test_published_state_not_modified_by_generation`: Verifies published drafts are immutable and generation requests on published drafts are rejected with HTTP 400.
   - `test_end_to_end_worker_timetable_solve_lifecycle`: Full end-to-end background worker execution: job claimed -> CP-SAT solved -> independent checker validated -> draft marked `CHECKED` and job marked `SUCCEEDED`.

2. **Frontend Production Build**:
   - `npm run build`: Strict TypeScript typecheck and Vite production build passed cleanly in 4.31s with zero errors.

---

## Phase 8: Complete Timetable Workspace & Minimal-Change Repair

### 1. Completed Functionality

- **Interactive Multi-Perspective Timetable Grid**:
  - Implemented responsive weekly matrix spanning Monday–Friday with discrete instructional periods.
  - Dedicated institutional lunch break row (`Campus Lunch & Recess Window`) with distinct styling.
  - Perspective toggle: View by **Class / Cohort** (`CS-A`, `CS-B`, `EE-A`), **Teacher / Faculty** (`Dr. Turing`, `Dr. Lovelace`, `Dr. Smith`), or **Physical Room** (`Room 101`, `Room 204`, `Lab 3`).
  - Term & Academic Week selection controls.

- **Visual Encoding System**:
  - **Theory Lectures**: Clean teal/ice styling, book icon, room and instructor metadata.
  - **Practical Labs**: Deep indigo/navy styling, workstation tag, lab icon, contiguous multi-period duration indicators.
  - **Locked Sessions**: Prominent padlock indicator (`Lock` icon) and drawer lock toggle.
  - **Clash Highlighting**: Pulsing coral ring, alert icon, and red text highlighting for conflicting cells.

- **Dual-Mode Editing (Drag & Drop + Accessible Non-Drag)**:
  - HTML5 drag-and-drop with drag handles, dragover ring highlights, and drop target zones.
  - Equivalent accessible click-to-move form in `SessionDetailDrawer.tsx` allowing keyboard and screen-reader users to select target day, period, and room without dragging.

- **Revision-Aware Autosave & 409 Conflict Detection**:
  - `revision` integer tracked on `TimetableDraft` model and database schema (Alembic migration `d1815326ca8d`).
  - All edits supply `expected_revision`; stale edits rejected with `HTTP 409 Conflict` and structured conflict message.
  - Live autosave sync indicator (`Synced (Rev #X)`, `Saving...`, `Temporarily Invalid`).

- **Temporarily Invalid Draft Policy**:
  - Schedulers can make intermediate conflicting moves during drafting without API rejection.
  - Draft transitions to `INVALID`, conflict banner displays active violations, and publication is **strictly blocked** until resolved.

- **Minimal-Change Repair with OR-Tools CP-SAT**:
  - Mathematical disruption cost objective function (time moved = 20, room changed = 5, both = 25).
  - Strictly preserves locked sessions.
  - Generates before/after comparison audit (`RepairDiffModal.tsx` and API response).

- **REST API Endpoints**:
  - `PATCH /api/v1/timetable-drafts/{id}/assignments/{assignment_id}`: Optimistically locked single assignment edit.
  - `POST /api/v1/timetable-drafts/{id}/repair`: CP-SAT minimal-change repair with before/after change records.

---

### 2. Verification & Test Outcomes

1. **Automated Pytest Suite (58/58 Passed)**:
   - `test_assignment_edit_and_revision_increment`: Verified assignment move updates coordinates and increments revision.
   - `test_revision_conflict_returns_409`: Verified stale edit with mismatched revision returns HTTP 409 Conflict.
   - `test_invalid_move_marks_draft_as_invalid`: Verified conflicting move marks draft `INVALID` and records `ROOM_OVERLAP` violation.
   - `test_minimal_change_repair_preserves_locked_sessions`: Verified CP-SAT repair moves flexible sessions while preserving locked session coordinates and generating before/after audit changes.
   - `test_published_draft_blocks_edits_and_repairs`: Verified published draft immutability rejects edits and repairs with HTTP 400.
   - All Phase 1–7 tests (53/53) passing with zero regressions.

2. **Frontend Production Build**:
   - `npm run build`: Strict TypeScript typecheck and Vite bundling passed cleanly in 20.88s with zero errors.

3. **Browser Automation Testing (End-to-End User Journey)**:
   - Tested locally on `127.0.0.1:5173` via browser subagent.
   - Authenticated as Coordinator (`coord@apex.edu`), navigated to `/staff/timetables`.
   - Verified weekly grid, break row, and revision badge.
   - Inspected `CS-201` in Session Detail Drawer.
   - Executed non-drag move to Tuesday; verified revision incremented from `Rev #1` to `Rev #2`.
   - Verified clash checks and solver draft generation.
   - Captured screenshot: `operational_timetable_matrix_1792653454176.png`.
   - Session recording: `local_timetable_workspace_test_1792653339375.webp`.


---

## Phase 9: Examination Allocation Modules (Theory Seating & Practical Labs)

### 1. Architectural Implementation Overview

Phase 9 implements comprehensive examination logistics for both theory seating plans and practical laboratory examinations, respecting fixed staff-entered schedules (without automatic exam-date optimisation):

1. **Theory Seating Engine (`TheorySeatingEngine`)**:
   - **Paper Identity**: Registrations based on actual paper identity (`paper_code` / `paper_id`), ensuring multi-subject examinations are handled accurately.
   - **Eligible Seat Checks**: Total and per-room usable bench checks accounting for `is_usable_for_exam`, `is_blocked`, and `is_accessible`.
   - **One Candidate Per Usable Bench**: Exactly one candidate per bench for the sitting period. Every candidate assigned exactly once.
   - **Accessibility Compliance**: Dedicated accessibility matching placing candidates needing accommodations (`requires_accessible_seat`) exclusively in verified accessible benches (`is_accessible`).
   - **Configurable Adjacency Rules**:
     - Orthogonal neighbor separation (north, south, east, west) to prevent adjacent seating of students writing the same exam paper.
     - **Hard vs. Soft Distinction**: Hard adjacency strictly returns `SEATING_UNSATISFIABLE` (HTTP 422) if impossible for the given geometry; **never silently relaxes a hard policy**. Soft adjacency places candidates while emitting auditable policy warnings.
   - **Dual Allocation Strategy**:
     - **Deterministic Interleaving**: High-speed serpentine and checkerboard paper interleaving for standard configurations.
     - **CP-SAT Constraint Optimization**: Mathematical integer programming via OR-Tools when complex room geometries or strict multi-paper hard constraints are required.
   - **Independent Verifier (`verify_theory_seating`)**: Plain structural validation ensuring no double-assignments, no bench reuse, no placement in blocked or inaccessible desks, and verifying hard paper adjacency.

2. **Practical Examination Engine (`PracticalExamEngine`)**:
   - **Sittings Timeline & Turnaround Buffers**: Accommodates multiple batches with start time, duration, and explicit turnaround buffers (`[start, start + duration + buffer]`) for disinfection, workstation reset, and setup.
   - **Hardware & OS Compatibility**: Validates workstation operating systems (Linux/Windows/macOS) and installed software/hardware features (`CUDA`, `GPU`, `MATLAB`, `Wireshark`) against candidate requirements.
   - **Examiner & Assistant Availability**: Validates invigilator and lab staff schedules, detecting overlapping assignments across duration plus turnaround buffer windows.
   - **Effective Capacity Policies**: Computes effective candidate throughput enforcing institutional capacity limits rather than raw physical count.
   - **Validated Reassignment**: Authoritative backend workstation and batch moves with revision tracking and conflict detection.

3. **Secure & Privacy-Preserving Exports (`ExamExportService`)**:
   - **Document Types**:
     - Hall Seat Plan (public door posting).
     - Candidate Desk Assignment List.
     - Invigilator Attendance Sheet with signature placeholders.
     - Practical Workstation Roster.
   - **Security**: Authenticated access with expiring cryptographic HMAC tokens (`export_token`) and expiration timestamps.
   - **Strict Privacy Rule**: **Private accommodation notes (`private_accommodations`) are strictly stripped and omitted from public seating plans and attendance sheets**, preserving student medical confidentiality.

4. **Interactive Examination Workspace UI (`StaffExaminations.tsx`)**:
   - Mode switcher between **Theory Seating Plans** and **Practical Laboratory Sittings**.
   - **Hall & Lab Selector** with per-room capacity metrics.
   - **Capacity Cards** (Total Benches, Usable / Eligible, Allocated Candidates, Remaining Capacity).
   - **Interactive Seat Map**: Matrix layout with configurable density, candidate roll numbers, colored paper tags, accessibility badges, blocked hatches, and 2-click move/swap interaction.
   - **Equivalent Accessible Candidate Table**: Full accessible accommodations view.
   - **Authorised Candidate Identifier Search**: Live search by roll number, name, or paper code highlighting benches in the matrix.
   - **Unassigned Candidates Tray**: Visual pool of unassigned candidates with manual bench assignment.
   - **Practical Timeline**: Sittings timeline with visually distinct turnaround buffer badges.
   - **Export Dialog**: Authenticated preview modal with draft/publication labels, timestamps, expiration notice, and privacy safeguard badge.

---

### 2. Verification & Acceptance Testing (71/71 Backend Tests Passed)

All 11 acceptance criteria tested and passed in `backend/tests/test_exam_allocation.py`:
1. `test_exact_fit_capacity`: Exact match of candidates to eligible benches succeeds.
2. `test_one_seat_shortfall`: Detects insufficient capacity and raises `INSUFFICIENT_CAPACITY`.
3. `test_duplicate_candidate_detection`: Rejects sitting snapshots containing duplicate candidates (`DUPLICATE_CANDIDATE`).
4. `test_duplicate_bench_detection`: Rejects rooms with duplicate bench IDs (`DUPLICATE_BENCH`).
5. `test_blocked_seat_detection`: Rejects allocations that assign candidates to blocked/unusable desks (`BLOCKED_SEAT`).
6. `test_ineligible_accommodation_seat`: Catches candidate requiring accessibility placed in standard bench (`INELIGIBLE_ACCOMMODATION_SEAT`).
7. `test_paper_adjacency_policy_hard_vs_soft`: Confirms hard policy rejection vs soft warning without silent relaxation.
8. `test_practical_extra_duration_overlap_with_buffer`: Verifies lab overlap detection accounting for turnaround buffer (`LAB_OVERLAP`).
9. `test_practical_examiner_clash`: Verifies examiner overlap clash detection (`EXAMINER_CLASH`).
10. `test_practical_workstation_incompatibility`: Rejects allocation if workstation lacks required OS or features (`WORKSTATION_INCOMPATIBLE`).
11. `test_export_content_matches_snapshot_and_omits_private_accommodations`: Confirms exported public seat plans match snapshot while strictly stripping confidential accommodation notes.
12. `test_theory_seat_reassignment_and_swapping`: Verifies move/swap logic and HTTP 409 revision conflict handling.
13. `test_practical_sitting_lifecycle_reassignment_and_listing`: Verifies practical workstation reassignment and listing endpoints.

---

## Phase 10: Controlled Publication & Real Student Views

### 1. Architectural Implementation Overview

Phase 10 delivers a transactionally safe, auditable publication pipeline and a real session-bound student experience:

1. **Strict 9-Step Transactional Publication (`PublicationService`)**:
   - **Step 1: Authorise Publisher**: Verifies membership role (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, or `EXAM_CONTROLLER`).
   - **Step 2: Verify Expected Draft Revision**: Rejects stale modifications with HTTP 409 `STALE_REVISION`.
   - **Step 3: Lock Documented Publication Scope**: Locks the academic term exclusively for the transaction.
   - **Step 4: Validate Shared-Resource Reservations**: Validates room and lab usage against current active reservations. Competing publications double-booking resources are authoritatively rejected with HTTP 409 `RESOURCE_RESERVATION_CONFLICT`.
   - **Step 5: Verify Complete Draft**: Re-runs independent validation (`ScheduleChecker.validate` for timetables, `TheorySeatingEngine` for exam seating) ensuring no unverified content is published.
   - **Step 6: Write Immutable Publication Records**: Writes immutable `Publication` records containing full input snapshots, output allocations, diff summaries, and SHA-256 audit checksums.
   - **Step 7: Update Active Reservations**: Updates `SharedResourceReservation` records for all allocated rooms and labs.
   - **Step 8: Write Communication Outbox Events**: Writes `CommunicationOutbox` events atomically. **Zero external services are called inside the database transaction**.
   - **Step 9: Commit**: Atomically commits the publication release.

2. **Controlled Publication Review & History UI**:
   - **`PublicationReviewModal`**: Pre-publish review dialog displaying checker verification status (`PASSED`/`FAILED`), hard violation counts, soft preference penalties, changed sessions count, affected faculty and students count, documented unmet preferences, and mandatory publication note input.
   - **`StaffPublishHistory`**: Version governance screen listing all immutable releases, version badges (`v1`, `v2`), publisher names, UTC timestamps, and cryptographic SHA-256 audit checksums.
   - **Granular Version Diff Viewer (`PublicationDiffModal`)**: Compares any two releases showing added, modified, and removed sessions with side-by-side day/period/room before-and-after views.
   - **Non-Destructive Rollback & Restore**: Restoring an old release snapshot creates a brand-new editable draft (Rev #1) and immediately submits it for independent rechecking. **Publication history is strictly preserved and never deleted during rollback**.

3. **Session-Bound Real Student Portal**:
   - **Strict Identity Enforcement**: Identity is strictly derived from the authenticated session (`req.state.current_user` -> `Student` profile). Own-data endpoints accept zero student ID parameters and authoritatively reject cross-student queries with HTTP 403 Forbidden.
   - **Draft Confidentiality**: Students can never view unpublished drafts. Unreleased schedules display a confidential review notice.
   - **`StudentHome`**: Welcome banner with PRN, department, official publication release badge, next-up class, today's schedule, upcoming exam seats, and recent published notices.
   - **`StudentTimetable`**: Server-derived dated occurrences for the student's enrolled courses with term timezone (`America/New_York`) and calendar exception overrides (holidays/cancellations marked explicitly).
   - **`StudentExamsSeats`**: Official theory examination seating slips with exact single-bench desk labels (`Omega-A1`), hall names, date/times, and accessibility compliance. Includes interactive security probe demonstrating that arbitrary student queries return HTTP 403.
   - **`StudentPracticals`**: Laboratory practical workstation assignments with terminal labels, OS sandbox, and examiner details.
   - **`StudentNotifications`**: Real-time notification feed of official published releases with audit checksums.
   - **`StudentProfile`**: Verified candidate record, active device sessions with revocation, and real working password change form enforcing institutional security policies.

---

### 2. Verification & Acceptance Testing (76/76 Backend Tests Passed)

All 7 acceptance criteria verified and passed:
1. **Students Cannot See Drafts**: Verified in backend test `test_student_cannot_see_unpublished_drafts` and browser subagent. Unreleased drafts return `is_published: false` and 0 occurrences.
2. **Students Cannot Query Another Student's Data**: Verified in backend test `test_student_cannot_query_arbitrary_student_data` and interactive browser probe returning HTTP 403 Forbidden.
3. **Competing Publications Cannot Double-Book Resources**: Verified in backend test `test_competing_publication_resource_conflict_rejected` returning HTTP 409 `RESOURCE_RESERVATION_CONFLICT`.
4. **Stale Revision Publication Rejected**: Verified in backend test `test_stale_revision_publication_rejected` returning HTTP 409 `STALE_REVISION`.
5. **History Preserved During Rollback**: Verified in backend test `test_publication_history_preserved_on_restore_rollback` and browser subagent. Zero past publication records deleted.
6. **Restored Version Rechecked**: Verified in backend test `test_restored_version_must_be_revalidated` ensuring restored drafts are re-verified (`CHECKED`).
7. **Real Student Browser Journey**: Verified via automated browser subagent on `http://127.0.0.1:5173` displaying live published assignments, weekly timetable with timezone occurrences, exam hall ticket with exact bench allocations, and active session management.

Backend Test Suite: **76 passed in 5.06s with zero regressions**.
Frontend Build: **TypeScript and Vite production build passed in 4.33s with zero errors**.

---

## Phase 11: Communication & Calendar Integration

### 1. Architectural Implementation Overview

Phase 11 delivers a resilient, durable communication subsystem, real-time multi-tenant event streaming, quiet hours delivery protection, and an optional Google Calendar integration:

1. **Durable Outbox Processing & Idempotent Delivery (`OutboxProcessor` & `NotificationService`)**:
   - **Outbox Persistence**: During publication releases, outbox events are written transactionally with `PENDING` status. The outbox processor picks up pending and retry-eligible failed events asynchronously.
   - **Idempotency Guarantee**: Every notification delivery is uniquely keyed by `(recipient_user_id, idempotency_key)`. If retried or re-executed, existing notifications and events are returned without duplication (`test_outbox_retry_does_not_duplicate_notifications`).
   - **Four Distinct Notification Categories**:
     1. `ACADEMIC_CHANGE`: Timetable publications, room reassignments, exam seat allocations.
     2. `OPERATIONAL_ALERT`: Staff clashes, system generator status, worker errors.
     3. `SECURITY_EVENT`: Password modifications, new session logins, session revocations (Always marked `URGENT`).
     4. `SCHEDULED_REMINDER`: Upcoming lectures and exam sitting reminders following the newest publication.
   - **Affected-User Targeting**:
     - Strict filtering: only faculty assigned to changed sessions and students enrolled in sections of changed sessions are targeted. Unaffected students and faculty receive zero notifications.
     - **Draft Isolation Rule**: Students are strictly never notified about unpublished draft modifications. Only committed, active `Publication` records generate student notifications.

2. **In-App Notification Centre & Quiet Hours (`NotificationCenterModal` & `NotificationPreference`)**:
   - **Header Integration**: Notification Bell icon in top header displays a live real-time unread badge counter.
   - **Interactive Modal**: Includes tabs for Notifications, Quiet Hours & Rules, and Google Calendar.
   - **Notification Feed**: Filterable by category (`ALL`, `ACADEMIC_CHANGE`, `OPERATIONAL_ALERT`, `SECURITY_EVENT`, `SCHEDULED_REMINDER`), unread-only toggle, and bulk "Mark All Read" action.
   - **Quiet Hours Protection**:
     - Users can configure evening-to-morning quiet hours (e.g. 22:00 to 07:00).
     - Non-urgent notifications (`NORMAL`, `LOW`) received during quiet hours are held in queue and delivered with `scheduled_for` set to quiet hours end.
     - **Urgent Priority Bypass**: Security events and urgent operational alerts bypass quiet hours immediately (`delivered_at = now`).

3. **Server-Sent Events (SSE) Stream & Polling Fallback (`useSSE` & `sse_manager`)**:
   - **Same-Origin Authentication**: SSE connection at `GET /api/v1/communication/events/stream` uses secure session cookies. **Zero session tokens in URLs**.
   - **Tenant & User Isolation**: Events are strictly scoped to `institution_id` and optional `target_user_id`. Users never receive another user's private events or another institution's publications.
   - **Reconnection & Replay**: Ring buffer stores recent events with sequential event IDs. On reconnect, `Last-Event-ID` header replays all missed events seamlessly.
   - **Graceful Polling Fallback**: If browser `EventSource` is disconnected or unavailable, client automatically falls back to polling `/api/v1/communication/events/poll?since=<lastEventId>` every 8 seconds.

4. **Optional Google Calendar Integration (`GoogleCalendarService`)**:
   - **Configuration Flag**: `GOOGLE_CALENDAR_ENABLED` (default `False`). If credentials are not configured, UI cleanly displays "Google Calendar: Not configured" alongside setup guidance. **Never simulates a fake connection**.
   - **Cryptographic State Validation**: HMAC-SHA256 signed OAuth state token with timestamp verification protects against CSRF.
   - **Encrypted Token Storage**: Tokens encrypted with Fernet AES-128-CBC using `GOOGLE_ENCRYPTION_KEY` or derived 32-byte key from `SECRET_KEY`.
   - **Narrow Secondary Calendar**: Creates or links an isolated secondary calendar ("Scheduler - Academic Calendar") so the user's primary calendar is never overwritten.
   - **One-Way Idempotent Sync**: Mapped via `synced_events_map`. Scheduler is authoritative. Sessions and exam sittings are created/updated idempotently.
   - **Publication Failure Isolation**: Calendar synchronization failures are caught and recorded on `CalendarCredential.last_error`. **Calendar failures strictly NEVER undo or rollback a successful publication**.
   - **Token Refresh & Revocation**: Expired access tokens refresh automatically. If revoked (`invalid_grant`), status transitions to `REVOKED` without crashing. Disconnect endpoint deletes credentials immediately.
   - **Testing Mock Reporting**: Unit and integration tests run with mock calendar clients and report `[TEST TYPE: MOCK - Google Calendar Integration Test]`.

5. **Staff Outbox & Delivery Retry Dashboard (`StaffOutboxSection`)**:
   - Outbox visibility screen for authorized staff (`ADMINISTRATOR`, `COORDINATOR`, `EXAM_CONTROLLER`).
   - Summary stat cards: Total Outbox Events, Dispatched (Idempotent), Pending Processing, Delivery Failures.
   - Event table with retry counters (`retry_count / max_retries`), error details, next retry timestamp, and "Retry" button.

---

### 2. Verification & Acceptance Testing (81/81 Backend Tests Passed)

All 6 acceptance criteria verified and passed:
1. **Retry Does Not Duplicate Notifications/Events**: Verified in backend test `test_outbox_retry_does_not_duplicate_notifications` and outbox retry endpoint. Exactly 1 notification created.
2. **Only Affected Users Receive Changes & Drafts Never Notify**: Verified in backend test `test_draft_changes_do_not_notify_students`. Unreleased drafts produce zero student notifications.
3. **Quiet Hours Delivery Protection**: Verified in backend test `test_quiet_hours_and_urgent_bypass`. Non-urgent notifications deferred; urgent security events delivered immediately.
4. **SSE Does Not Leak Another User's Data & Replay**: Verified in backend test `test_sse_user_isolation_and_reconnect`. Alice's events never leaked to Bob; reconnect replays missed events.
5. **Google Calendar Mock & Publication Isolation**: Verified in backend test `test_google_calendar_mock_and_publication_isolation`. Unconfigured guidance displayed; token encryption/decryption, sync idempotency, revoked token error handling, and publication failure isolation confirmed.
6. **Frontend Production Build & Browser Verification**:
   - `tsc && vite build` passed in 4.28s with zero errors.
   - Browser subagent verified live in-app Notification Centre, category badges, Quiet Hours pickers, Google Calendar unconfigured card with setup guidance, and staff outbox tab.

Backend Test Suite: **81/81 passed in 5.64s with zero warnings/regressions**.
Frontend Build: **Clean Vite production bundle in 4.28s**.

---

## Phase 12: Feedback and Contact System

### 1. Architectural Summary & Model Implementation
Phase 12 builds two distinct, securely isolated feedback workflows:
1. **Public Contact & Inquiries (Workflow A)**:
   - **Fields**: Optional `name`, optional `email`, required `category` (`GENERAL_INQUIRY`, `PILOT_REQUEST`, `BUG_REPORT`, `ACCESSIBILITY`, `OTHER`), `subject` (3-200 chars), `message` (10-5000 chars).
   - **Privacy Notice & Security Warning**: Prominent banners detailing operational use and warning never to submit passwords or sensitive student records.
   - **Rate Limiting & Bot Mitigation**: IP-based sliding window rate limiter (10 submissions per hour per IP) returning HTTP 429 when exceeded. Hidden honeypot field (`honeypot`) traps automated bots.
   - **Generic Confirmation**: Response provides an unguessable public reference tracking code (`FB-XXXXXXXX`) and generic message. Internal database IDs (`id`, `institution_id`, `submitting_user_id`) are never exposed.
   - **Email Independence**: Optional acknowledgement sent only if email is provided and provider configured. Persists reliably without email.

2. **Authenticated Feedback (Workflow B)**:
   - **Session-Derived Association**: Submitting user (`submitting_user_id`) and institution (`institution_id`) are derived authoritatively from the active session.
   - **Categories**: `BUG_REPORT`, `SUGGESTION`, `ACCESS_ISSUE`, `SCHEDULING_ISSUE`, `OTHER`.
   - **Context Reference**: Optional `page_reference` (e.g. `Timetables -> Computer Lab 301`).
   - **No Credential Harvesting**: System never collects passwords, session tokens, or confidential student records.
   - **Explicit Disclaimer**: Notice highlighting that feedback is NOT a timetable-change or course enrollment petition.
   - **Submitter Self-View**: Users can view their submitted inquiries (`GET /api/v1/feedback/my-submissions`) with real persistence confirmations and lifecycle status (`new`, `reviewing`, `awaiting_information`, `resolved`, `closed`).
   - **Confidential Internal Notes**: Internal reviewer deliberations (`FeedbackInternalNote`) are stored in a separately protected table and strictly hidden from submitters.

3. **Administrative Triage Queue (`StaffFeedback.tsx`)**:
   - Filterable by status, category, and free-text search.
   - Scoped visibility: Permitted institutional reviewers (`INSTITUTION_ADMINISTRATOR`, `TIMETABLE_COORDINATOR`, `EXAM_CONTROLLER`) only view their institution's tickets. Cross-institution review is authoritatively blocked (HTTP 403). Public inquiries are visible only to platform reviewers.
   - Audit trail logging on every status update and reviewer assignment.
   - Safe rendering: All submitted text is rendered as plaintext, keeping stored-XSS payloads inert.

### 2. Verification & Acceptance Testing (89/89 Backend Tests Passed)
1. **Anonymous Valid Submission**: Verified public submission without name/email creates record with unique reference code.
2. **Authenticated Submission**: Verified user and institution derived from session context.
3. **Invalid/Oversized Content Rejected**: Verified 422 Unprocessable Entity for subjects > 200 chars or messages > 5000 chars.
4. **Rate Limiting Enforced**: Verified HTTP 429 Too Many Requests when rate threshold is exceeded.
5. **Stored-XSS Payloads Inert**: Verified `<script>` and `<img>` payloads persist safely and render inertly as plaintext.
6. **Submitter Isolation**: Verified students see only their own submissions and never receive internal notes.
7. **Cross-Institution Review Denied**: Verified HTTP 403 Forbidden when reviewer attempts to inspect another institution's ticket.
8. **Confirmation Reflects Actual DB Persistence**: Verified database persistence matches returned reference code.


---

## Phase 13: Optional AI-Assisted Interpretation & Diagnostics

### 1. Architectural Summary & Model Implementation
Phase 13 introduces an air-gapped, advisory interpretation pipeline for natural language scheduling change requests, conflict diagnostics, and tabular column mapping proposals:

1. **Strict Non-Authoritative Boundary**:
   - **No Database Execution**: The AI model has zero direct database access, zero SQL execution capabilities, zero permission management authority, zero publication rights, and zero arbitrary tool access.
   - **Candidate Interpretations Only**: All model outputs are classified as unverified candidate proposals. Suggestions are never auto-committed or auto-published.
   - **Authoritative Solver Dominance**: Proposed changes apply only as uncommitted draft modifications after explicit user approval, which immediately triggers the authoritative CP-SAT solver/checker workflow.

2. **Provider Abstraction Architecture (`app.services.ai_provider`)**:
   - `BaseAIProvider`: Abstract contract for `interpret_change`, `explain_issues`, `propose_column_mappings`, and `get_status`.
   - `DisabledAIProvider`: AI disabled by configuration (`AI_ENABLED=False` or `AI_PROVIDER=disabled`). Returns clear disabled state in `/status` and HTTP 503 on interpretation attempts.
   - `MockAIProvider`: Deterministic, air-gap compliant provider for tests and local development. Accurately simulates ambiguity detection, entity resolution, and timeout/malformed test triggers.
   - `ExternalAIProvider`: Configured real external provider with schema validation, timeouts, request size limits, and sanitization.

3. **Supported Tasks**:
   - **Task 1: Timetable Change Request Interpretation**:
     - Resolves natural language prompts into typed session modifications (`ResolvedSessionChange`).
     - Detects ambiguity types:
       - `UNDEFINED_TIME` (e.g., undefined "afternoon" or "morning").
       - `UNKNOWN_ENTITY` (unmatched teacher or room).
       - `PREFERENCE_VS_HARD_CONSTRAINT` (soft preference vs rigid constraint).
       - `TERM_WIDE_VS_DATE_SPECIFIC` (specific date vs entire academic term).
   - **Task 2: Checker Conflict Diagnostics**:
     - Translates raw solver conflicts (`ROOM_DOUBLE_BOOKING`, `TEACHER_CONFLICT`, `CAPACITY_OVERLOAD`) into actionable plain-language explanations with root causes and candidate resolutions.
   - **Task 3: Tabular Column Mapping Proposals**:
     - Maps raw CSV/Excel headers to system schema fields (`course_code`, `teacher_name`, `room_code`, etc.) with confidence scores and unmapped column warnings.

4. **10-Step Secure Execution Pipeline (`AIService`)**:
   1. *Receive Authorised Request*: Authenticate user and verify institution ownership.
   2. *Privacy Scrubbing*: Supply only approved context (scrub PRNs, student names, and passwords).
   3. *Obtain Structured Proposal*: Typed JSON generation from provider.
   4. *Schema Validation*: Strict Pydantic validation (reject malformed model outputs with HTTP 422).
   5. *Entity Resolution*: Map entities to approved institution scope.
   6. *Authorisation Check*: Verify user has edit privileges for targeted draft.
   7. *Present Candidate Diff*: Display ambiguity flags, warnings, and source->destination diff.
   8. *Require User Approval*: Mandatory user review before any action.
   9. *Apply to Draft*: Apply changes as uncommitted draft edits with optimistic concurrency revision locking (HTTP 409 on conflict).
   10. *Independent Verification*: Run authoritative `ScheduleChecker` validation.

5. **Security, Governance & Cost Transparency**:
   - Request size limit: Max 2000 characters (HTTP 422 if exceeded).
   - Provider timeout: 10.0 seconds (HTTP 504 Gateway Timeout leaves draft unchanged).
   - Sanitized audit trail: Logs `AI_INTERPRETATION_APPLIED` without recording freeform prompt text.
   - Operational status endpoint: `GET /api/v1/ai/status` exposes provider mode (`MOCK`, `EXTERNAL`, `DISABLED`), active model name, request counts, tokens processed, and estimated cost visibility.

### 2. Verification & Acceptance Testing (99/99 Backend Tests Passed)
1. **Core Workflow Operates with AI Disabled**: Full schedule check and draft editing operate with AI disabled; AI endpoints return HTTP 503 cleanly.
2. **AI Status and Provider Visibility**: `/api/v1/ai/status` exposes configuration, availability, model, and cost metrics.
3. **Timetable Change Request Interpretation**: Natural language queries resolve with accurate session targets and confidence scores.
4. **Ambiguity Handling**: Explicit ambiguity flags emitted for undefined times, unknown entities, and preference vs hard constraint.
5. **Malformed Model Output Rejected**: Strict Pydantic schema validation returns HTTP 422 for malformed model outputs.
6. **Unauthorised Target Draft Rejected**: Cross-institution targeting rejected with HTTP 403 Forbidden.
7. **Prompt-Injection Input Cannot Publish or Grant Access**: Untrusted text cannot alter publication flags or elevate user roles.
8. **Provider Timeout Leaves Drafts Unchanged**: Simulated 10s timeout triggers HTTP 504 and leaves draft revision untouched.
9. **Checker Violations Explanation**: Plain-language diagnostics and candidate resolutions generated for solver conflicts.
10. **Column Mapping Proposal**: CSV headers mapped to target schema with confidence scores and unmapped column detection.
