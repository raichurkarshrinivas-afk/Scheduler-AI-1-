# Scheduler Comprehensive Test Plan

## 1. Testing Philosophy & Architecture

Scheduler employs a multi-tiered testing strategy ensuring reliability, mathematical correctness of scheduling engines, strict multi-tenant security, and WCAG AA accessibility:

```
                  ┌───────────────────────────────┐
                  │    Playwright Browser E2E     │  (End-to-end workflows,
                  │      (Keyboard, A11y, UI)     │   accessibility, UX)
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │    FastAPI HTTP Integration   │  (API contracts, auth,
                  │      (pytest + TestClient)    │   health probes, headers)
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │   Algorithmic Engine Tests    │  (OR-Tools CP-SAT, clash
                  │    (Seating & Timetable MRV)  │   detection, bench spacing)
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │    Database & Schema Tests    │  (Alembic migrations,
                  │   (Multi-Tenant Isolation)    │   row-level tenancy)
                  └───────────────────────────────┘
```

---

## 2. Phase 1 Verification Suite

### 2.1 Health Probe Telemetry Suite (`backend/tests/test_health.py`)
- **`test_health_live_endpoint`**:
  - Dispatches `GET /health/live`.
  - Asserts HTTP 200 OK.
  - Verifies response payload includes `status: "ok"`, `live: true`, `service: "Scheduler"`, `version: "1.0.0"`.
  - Confirms zero database connection overhead.
- **`test_health_ready_endpoint_success`**:
  - Dispatches `GET /health/ready` against active database.
  - Asserts HTTP 200 OK.
  - Verifies response payload includes `status: "ok"`, `ready: true`, `database: "connected"`.
- **`test_health_ready_endpoint_db_failure`**:
  - Injects database operational disconnection using `unittest.mock.patch("app.api.health.engine.connect")`.
  - Asserts HTTP 503 Service Unavailable.
  - Verifies response payload indicates `ready: false` and `database: "disconnected"`.
- **`test_api_prefixed_health_endpoints`**:
  - Dispatches `GET /api/health/live` and `GET /api/health/ready`.
  - Verifies proxy routing parity with root health paths.
- **`test_general_health_overview`**:
  - Dispatches `GET /health`.
  - Verifies aggregate diagnostic status payload.

### 2.2 Frontend Static Analysis & Bundling Verification
- **TypeScript Typecheck**:
  - Command: `tsc --noEmit`
  - Validates zero type discrepancies across React components, TanStack Query hooks, and Lucide icons.
- **Vite Production Bundler**:
  - Command: `npm run build`
  - Verifies asset generation in `dist/` with zero PostCSS, Tailwind, or bundling warnings.

---

## 3. Algorithmic & Security Testing Suites (Planned for Phase 2+)

### 3.1 Multi-Tenant Isolation Security Suite
- **Cross-Tenant Access Rejection**:
  - Verify that a user from Tenant A attempting to access resources belonging to Tenant B receives HTTP 404 (or 403) and never leaks resource presence.
- **Repository-Level Filtering**:
  - Ensure all database queries automatically append `WHERE institution_id = :tenant_id`.

### 3.2 Timetable Constraint Verification Suite
- **Hard Constraint Clashes**:
  - Instructor double-booking: Two sessions assigned to the same instructor in the same time slot must trigger a validation clash.
  - Classroom double-booking: Two courses assigned to the same room simultaneously must trigger a conflict error.
  - Student batch clash: Overlapping sessions for the same cohort must fail validation.
  - Classroom capacity limits: Enrolling a cohort larger than classroom capacity must be rejected.
  - Instructor unavailability: Sessions scheduled on slots marked unavailable must be flagged.
- **CP-SAT Solver Convergence**:
  - Automated benchmarks verifying that the OR-Tools CP-SAT engine successfully solves a benchmark academic schedule of 100 sessions across 20 rooms in under 5 seconds.

### 3.3 Examination Seating & Anti-Cheating Suite
- **One Candidate per Usable Bench Rule**:
  - Validates that no bench hosts more than one student.
- **Orthogonal Neighbor Isolation**:
  - Asserts that for every seat assignment `(r, c)`, orthogonal neighbors `(r±1, c)` and `(r, c±1)` are NOT enrolled in the same course.
- **Single-Course Checkerboard Spacing**:
  - When an entire room writes a single examination, verifies that alternating empty desk spacing (checkerboard) is enforced.

### 3.4 Lifecycle & Workflow State Machine Suite
- **Draft &rarr; Check &rarr; Review &rarr; Publish**:
  - Validates sequential state transitions.
  - Asserts that unpublished drafts cannot be fetched by Student accounts.
  - Asserts that published timetables cannot be modified without an explicit administrative unlock.

### 3.5 End-to-End Browser Testing with Playwright
- **Accessible Interactions**:
  - Verifies that all status indicators include visible text descriptions alongside icons.
  - Verifies keyboard tab ordering across all buttons, inputs, and modal dialogues.
- **Non-Drag Alternatives**:
  - Tests that timetable slot moves and seat swaps can be completed entirely using keyboard and accessible dropdown select menus without pointer dragging.

---

## 4. Execution Commands

### 4.1 Run Backend Tests
```bash
cd backend
python -m pytest -v
```

### 4.2 Run Specific Health Tests
```bash
cd backend
python -m pytest tests/test_health.py -v
```

### 4.3 Run Frontend Type-Check & Production Build
```bash
cd frontend
npm run build
```

### 4.4 Run Playwright Browser Tests (When Configured)
```bash
cd frontend
npx playwright test
```