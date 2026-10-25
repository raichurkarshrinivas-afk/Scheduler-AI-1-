# Architectural Decision Records (ADRs)

## ADR 001: Multi-Tenancy via Row-Level Institution Isolation
- **Status**: Accepted
- **Context**: The scheduler serves multiple educational institutions with strict regulatory and privacy requirements (student privacy, exam integrity). Data must never cross institutional boundaries.
- **Decision**: Implement multi-tenancy using a shared database schema where all tenant-scoped tables have a mandatory `institution_id` foreign key. Query-level isolation is enforced via FastAPI dependency injection (`require_institution`) and repository layer query filtering.
- **Consequences**:
  - Single database migration pipeline via Alembic.
  - Efficient resource utilization.
  - Test suites must verify that cross-tenant queries return HTTP 404/403 and never leak data.

---

## ADR 002: Combinatorial Constraint Engine (OR-Tools CP-SAT) with AI-Free Operation
- **Status**: Accepted
- **Context**: Scheduling academic timetables and exam seating are mathematically rigid constraint satisfaction problems. Relying on non-deterministic external LLMs or third-party AI APIs introduces unpredictable schedules, hallucinated constraints, latency spikes, rate limits, ongoing operational costs, and privacy vulnerabilities.
- **Decision**: Standardize on Google OR-Tools CP-SAT (Constraint Programming — Satisfiability) combined with deterministic heuristic backtracking algorithms.
- **Consequences**:
  - 100% reproducible, auditable, and mathematically optimal outputs.
  - Zero external cloud/API costs.
  - 100% offline and air-gap capable for secure examination environments.

---

## ADR 003: Persistence & Driver Selection (SQLAlchemy 2.x, PostgreSQL 16, Psycopg 3)
- **Status**: Accepted
- **Context**: The application requires high concurrency, connection pooling, and strict schema integrity.
- **Decision**: Standardize on PostgreSQL 16 as the production relational engine, accessed through modern Psycopg 3 (`psycopg[binary]`) driver and SQLAlchemy 2.x ORM with declarative typed mappings. Alembic manages schema migrations. Local testing and development support fallback SQLite with WAL mode.
- **Consequences**:
  - Full compatibility with modern Python 3.12+ async and typed drivers.
  - Production deployments use containerized PostgreSQL via `compose.yaml`.

---

## ADR 004: Server-Side Cookie Sessions for Authentication
- **Status**: Accepted
- **Context**: Session state must be secure against Cross-Site Scripting (XSS) and token exfiltration.
- **Decision**: Use server-side cookie sessions (`HttpOnly`, `SameSite=Lax`, `Secure` in production) rather than vulnerable client-stored JWT tokens in `localStorage`.
- **Consequences**:
  - Mitigates XSS token theft.
  - Enables instant revocation of sessions by institutional administrators.

---

## ADR 005: Minimalist Light Design System & Accessibility Primitives
- **Status**: Accepted
- **Context**: Academic schedulers and exam controllers spend hours configuring dense scheduling grids. Dark or novelty themes cause eye strain during daytime operations. Interface states must be accessible to users with visual impairments.
- **Decision**: Standardize on a minimalist light interface utilizing:
  - Curated color tokens: `#F7F8FA` (background), `#FFFFFF` (surface), `#14213D` (text/navy), `#0E7C66` (primary teal), `#F2B134` (warning amber), `#D9480F` (conflict coral).
  - Soft borders and restrained shadows.
  - **No emoji interface icons**: Standardize exclusively on scalable SVG icons (Lucide React).
  - **Multi-modal state**: Never rely on color alone for state; pair every color indicator with clear text labels and ARIA status attributes.
  - **Non-drag alternatives**: Provide explicit keyboard, modal, and dropdown controls as alternatives to drag-and-drop operations.
- **Consequences**:
  - Clean, high-legibility interface conforming to WCAG AA accessibility standards.

---

## ADR 006: Asynchronous Offloading to Separate PostgreSQL-Backed Worker Process
- **Status**: Accepted
- **Context**: Timetable generation and exam seating layout solvers can consume several minutes of CPU time for large universities with hundreds of cohorts. Running solvers inside HTTP request handlers causes gateway timeouts.
- **Decision**: Offload solving workloads to a dedicated background worker process backed by PostgreSQL transactional queues.
- **Consequences**:
  - FastAPI web workers remain instantly responsive.
  - Solvers run with progress tracking and can be cancelled gracefully.

---

## ADR 007: Health Probes Decoupling (Liveness vs. Readiness)
- **Status**: Accepted
- **Context**: Kubernetes, Docker Compose, and load balancers require distinct health signals to manage restarts versus traffic routing.
- **Decision**: Decouple `GET /health/live` and `GET /health/ready`:
  - `GET /health/live`: Evaluates only ASGI process responsiveness. Does not query database.
  - `GET /health/ready`: Actively tests database connectivity (`SELECT 1`). Returns HTTP 503 if disconnected.
- **Consequences**:
  - A transient database blip will take the service out of rotation (readiness fail) without triggering harmful container crashloops (liveness pass).

---

## ADR 008: Strict Dependency Locking & Zero Floating Versions Policy
- **Status**: Accepted
- **Context**: Floating dependency versions (`^`, `~`, `>=`) introduce silent build breakage, unintended transitive changes, and security discrepancies across environments.
- **Decision**: Enforce exact version pinning (`==` in Python `requirements.txt` and exact versions in `package.json`). Commit immutable lockfiles (`requirements.lock` and `package-lock.json`).
- **Consequences**:
  - Fully reproducible, deterministic builds across development, CI/CD, and production container runs.

---

## ADR 009: Argon2id Password Hashing & SHA-256 Digest-Only Session Storage
- **Status**: Accepted
- **Context**: Modern authentication systems must protect credentials against offline cracking and credential leaks from database backups. Raw tokens stored in databases allow attackers with database read access to impersonate active users.
- **Decision**:
  - Standardize on Argon2id via `argon2-cffi` with RFC 9106 recommended interactive parameters (`time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`).
  - Generate 32-byte cryptographically random session tokens using `secrets.token_urlsafe(32)`.
  - Store only the `SHA-256` hexadecimal digest of session tokens in `user_sessions.session_token_hash`. The raw token exists solely in the client's `HttpOnly` browser cookie jar.
- **Consequences**:
  - In the event of a database compromise, attacker cannot recover plaintext passwords or authenticate with active session digests.
  - Zero storage of credentials or tokens in browser `localStorage`.

---

## ADR 010: Double-Submit Cookie CSRF Defense & Strict Cookie Policies
- **Status**: Accepted
- **Context**: Using cookie-based browser sessions exposes the application to Cross-Site Request Forgery (CSRF) unless mutating browser requests are strictly verified.
- **Decision**:
  - Implement the Double-Submit Cookie pattern coupled with session-bound server verification.
  - Dispatch a session-unique CSRF token in a `SameSite=lax` cookie (`scheduler_csrf`).
  - Require the frontend to include an identical `X-CSRF-Token` header on all mutating HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`).
  - Enforce `HttpOnly`, `SameSite=lax` (or strict), and configurable `Secure` flags (`COOKIE_SECURE=True` in production HTTPS, `COOKIE_SECURE=False` explicitly documented for local development).
- **Consequences**:
  - Third-party websites cannot forge state-changing actions.
  - Safe methods (`GET`, `HEAD`, `OPTIONS`) remain unhindered.

---

## ADR 011: Rate-Limiting Contract with Documented Single-Instance Implementation
- **Status**: Accepted
- **Context**: Authentication endpoints (`/login`, `/change-password`, `/admin/.../reset-password`) are vulnerable to credential stuffing, brute force, and denial of service.
- **Decision**:
  - Define an extensible `BaseRateLimiter` abstract base class.
  - Implement a thread-safe `InMemorySlidingWindowRateLimiter` as the default single-instance rate limiter.
  - Explicitly document single-process memory boundaries and provide architecture requirements for multi-instance distributed clusters (e.g., Redis).
- **Consequences**:
  - Brute-force and credential stuffing attacks are throttled with HTTP 429 and `Retry-After` headers.
  - Zero required external infrastructure for single-instance setups, with clean decoupling for multi-node deployments.

---

## ADR 012: Administrative Reset Workflow & Anti-Enumeration Generic Login Failures
- **Status**: Accepted
- **Context**: Public self-registration and automated email password reset links introduce account enumeration vulnerabilities and phishing risks in academic institutions.
- **Decision**:
  - Disallow public self-registration. All accounts are provisioned by institution administrators.
  - Implement an administrative reset workflow where administrators generate temporary credentials with mandatory password change (`must_change_password=True`).
  - Standardize login failure responses: always return generic `HTTP 401: "Invalid institution, identifier, or password."` regardless of whether the institution, username, or password failed.
  - Execute constant-time dummy Argon2id verification (`_DUMMY_ARGON2_HASH`) on failed lookups to prevent side-channel timing attacks.
- **Consequences**:
  - Eliminates email recovery spoofing.
  - Eliminates username/email enumeration across institutions.

---

## ADR 013: Procedural 3D Landing Scene & WebGL Fallback Architecture
- **Status**: Accepted
- **Context**: The public landing page should convey spatial sophistication and precision without bloating bundle sizes, draining GPU resources, or compromising accessibility.
- **Decision**:
  - Standardize on Three.js via React Three Fiber (`@react-three/fiber`) and Drei (`@react-three/drei`) restricted to a single lazy-loaded Canvas on the landing-page hero.
  - Procedural geometry only: construct the floating weekly timetable, seating grid, lab board, and validation token programmatically using basic geometries. Zero external 3D asset downloads.
  - Non-intrusive motion: subtle pointer parallax clamped to a small angle (`< 0.15 rad`), idle animation paused on off-screen scroll (`IntersectionObserver`) and hidden tab state.
  - Full fallback guarantees: Error boundary wrapper, WebGL context loss recovery, and a locally generated matching SVG illustration when WebGL is unsupported or disabled by `prefers-reduced-motion: reduce`.
- **Consequences**:
  - Keeps 3D bundles isolated from operational authenticated routes.
  - Ensures zero broken experiences on low-power devices, screen readers, or restricted enterprise browsers.

---

## ADR 014: 2D Operational Role-Aware Application Shells and Restrained Typography
- **Status**: Accepted
- **Context**: Enterprise scheduling and exam administration require maximum density, visual clarity, and rapid scanning. 3D tilts or complex skews impair reading timetable grids and desk assignments.
- **Decision**:
  - Enforce strictly 2D, planar layouts across authenticated staff and student application shells.
  - Typography: Sora for headings, DM Sans for body and interface labels, with resilient system fallbacks.
  - Standardize role-aware navigation dividing staff capabilities (Overview, Timetables, Examinations, Resources, Publish & History, Reports, Feedback, Settings) from student self-service (Home, Timetable, Practicals, Exams/Seats, Notifications, Profile).
  - Explicit "Not implemented yet" panels for future phase modules to maintain integrity and prevent fake success states.
- **Consequences**:
  - High operational legibility conforming to WCAG AA accessibility.
  - Eliminates cognitive overhead and prevents misleading UI states.

---

## ADR 015: PostgreSQL-Backed Leased Background Job System with Fencing and Idempotent Finalization
- **Status**: Accepted
- **Context**: Long-running scheduling operations (combinatorial solving, exam seating optimization, and high-density PDF exports) require durable background processing that survives API process restarts, recovers from worker node crashes, prevents dual execution, and respects per-institution resource limits.
- **Decision**:
  - Implement a PostgreSQL-backed job persistence model (`jobs` table) with state lifecycle (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`).
  - **Short Transactions for Claims**: Use atomic transactions with `FOR UPDATE SKIP LOCKED` (on PostgreSQL) to claim candidate jobs without blocking concurrent workers. Close the transaction immediately upon acquiring the lease token. CPU-heavy solver execution occurs completely outside database transactions.
  - **Heartbeats & Strict Fencing**: Background thread updates `heartbeat_at` and `lease_expiry` every 5 seconds. Every state mutation checks `WHERE id = :job_id AND lease_token = :lease_token`. If a worker's lease expires and another worker recovers the job, the stale worker's heartbeat/finalization fails (affected rows = 0), preventing split-brain corruption.
  - **Concurrency & Retry Controls**: Enforce per-institution concurrency caps (e.g. max 2 running jobs per tenant simultaneously) to prevent noisy-neighbor starvation. Failed attempts execute exponential retry backoff up to `max_attempts` (default 3), transitioning to `FAILED` with structured error codes (`MAX_ATTEMPTS_EXCEEDED`, `TIMEOUT`, `SOLVER_INFEASIBLE`).
  - **Graceful Shutdown**: Background worker catches `SIGINT`/`SIGTERM`/`SIGBREAK`, stops polling, allows in-flight jobs to complete or clean up leases, and exits cleanly.
  - **Meaningful Phase Reporting**: UI displays meaningful operational progress phase strings (`phase_label`) and elapsed timer (`elapsed_seconds`), strictly avoiding fake completion percentages.
- **Consequences**:
  - Zero external queue infrastructure required (no Redis or RabbitMQ dependency for single-cluster setups).
  - Resilient to worker crashes, process restarts, and network partitions.
  - Full multi-tenant isolation and strict auditability.
