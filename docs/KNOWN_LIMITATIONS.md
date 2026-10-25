# Known Limitations & Prioritized Technical Backlog

## 1. Overview

This document transparently records known architectural boundaries, scaling caveats, unsupported scheduling features, and prioritized technical backlog items for the Scheduler platform. 

Every limitation documented below has been verified against the active codebase and measured behavior.

---

## 2. Architectural & Storage Caveats

### 2.1 SQLite vs. Production PostgreSQL
- **Development/Local Execution**: Local development and automated test suites run against SQLite with write-ahead logging (WAL). While SQLite provides deterministic, fast testing (114 tests in 7.2s), SQLite locks the entire database file during write transactions.
- **Production Requirement**: Production enterprise deployments must connect to PostgreSQL (version 15+). The codebase implements standard PostgreSQL row-level locking (`SELECT ... FOR UPDATE` via SQLAlchemy `with_for_update()`) to ensure serializable transaction isolation during 9-step atomic publications and job claiming.
- **Human Verification Required**: While SQLAlchemy abstractions map models to standard SQL types, production schema migrations on PostgreSQL must be validated against a live PostgreSQL staging database with pg_stat_statements enabled.

### 2.2 Server-Sent Events (SSE) In-Memory Bus
- **Current Architecture**: The SSE communication service (`app/services/sse_service.py`) maintains an in-memory client connection set and a circular ring buffer of recent events.
- **Limitation**: In a multi-node or multi-process cluster (e.g., Kubernetes pods running separate Uvicorn workers), clients connected to Node A will not receive SSE messages published by a background worker executing on Node B.
- **Mitigation / Next Step**: Implement an external pub/sub adapter (e.g. Redis Pub/Sub or PostgreSQL `LISTEN` / `NOTIFY`) for cluster-wide broadcast.

### 2.3 Calendar Sync Rate Quotas
- **Current Architecture**: Safe synchronization iterates through user timetable assignments and creates/updates events on Google Calendar.
- **Limitation**: Google Calendar API enforces a default project quota of 500 queries per 100 seconds. For large institutions synchronizing thousands of students simultaneously upon timetable release, synchronous synchronization will hit Google rate limits.
- **Mitigation / Next Step**: Enqueue calendar synchronizations as distributed background jobs throttled at 5 requests/sec per OAuth client.

---

## 3. Solver & Modeling Scope Boundaries

### 3.1 Weekly Horizon vs. Multi-Term Block Schedules
- **Supported Horizon**: The combinatorial solver models standard recurring weekly schedules (typically 5 to 6 days with 6 to 10 periods per day, up to ~80-120 concurrent sessions).
- **Limitation**: Highly irregular block-modular timetables (where schedule patterns change completely every alternating week) require solving multiple independent weekly models sequentially rather than a single monolithic CP-SAT model.

### 3.2 Explicitly Unsupported Rules
In accordance with `SPEC.md`, the solver mathematically pre-checks and explicitly rejects the following rules:
1. `floating_lunch`: Open lunch windows with non-deterministic start times across sections.
2. `multi_campus_transit`: Simultaneous booking across geographical campuses without travel buffer slots.
3. `fractional_coteaching`: Fractional splits of instructors within a single timeslot.
4. `dynamic_section_partitioning`: Real-time splitting of cohorts during the solver search.
5. `multi_tenant_sharing`: Resource booking across independent institutional tenants.

---

## 4. Prioritised Unresolved Issues & Technical Backlog

The following technical tasks are prioritized based on operational impact and architectural maturity:

### Priority 1: High (Required for Horizontally Scaled Multi-Server Deployments)
- **Task**: Distributed Message Bus Adapter for SSE.
- **Description**: Replace the local in-memory event registry in `sse_service.py` with a Redis Pub/Sub or PostgreSQL `LISTEN/NOTIFY` driver so that all web pods receive real-time publication notifications.
- **Impact**: Zero impact on single-node deployments; essential for multi-pod Kubernetes clusters.

### Priority 2: Medium (Large-Cohort Performance Optimization)
- **Task**: Batched Google Calendar Background Dispatcher.
- **Description**: When an institution publishes a timetable with > 500 students, dispatch calendar sync events into a rate-limited background task queue instead of inline execution.
- **Impact**: Prevents Google API HTTP 429 Too Many Requests errors during massive university-wide publication releases.

### Priority 3: Medium (Database Migration Test Harness)
- **Task**: Automated PostgreSQL Alembic Migration Verification.
- **Description**: Add a dedicated CI workflow step that boots a temporary PostgreSQL Docker container, runs `alembic upgrade head`, generates seed fixtures, and asserts schema reflection parity.
- **Impact**: Eliminates SQLite-to-PostgreSQL syntax drift during continuous delivery.

### Priority 4: Low (Frontend Asset Bundle Optimization)
- **Task**: Dynamic Code-Splitting of 3D Canvas Scene.
- **Description**: During `npm run build`, Vite generated a warning that the Three.js 3D visualization scene bundle (`SchedulerScene-*.js`) is 831 kB uncompressed (223 kB gzip).
- **Impact**: Initial page loads on mobile 3G networks can be further improved by converting the 3D scene into a React `lazy()` suspense component loaded only when the user clicks the 3D seating view.

---

## 5. Distinction: Automated Evidence vs. Human Review

| Evaluation Area | Automated Evidence (Verified) | Human / Operational Review Required |
| :--- | :--- | :--- |
| **Solver Correctness** | 100% of generated assignments pass independent `ScheduleChecker.validate` with 0 violations. | Department heads should periodically inspect soft preference weighting satisfaction. |
| **Data Isolation** | Cross-tenant identifier manipulation consistently returns 403/404 across all endpoints. | Database administrators must ensure PostgreSQL database users have no cross-schema superuser grants. |
| **Security Controls** | Zero hardcoded API keys; CSRF tokens enforced; session timeouts verified. | DevOps must confirm SSL/TLS termination and HSTS headers on external ingress controllers. |
| **Frontend Rendering** | Build succeeds with 0 TypeScript errors; accessible HTML landmarks present. | User experience testing with screen readers (NVDA/JAWS) and color vision deficiency filters. |
| **Throughput & Latency** | Actual hardware benchmarks measured and recorded (~89 req/s read, ~17 req/s login). | Capacity planning for peak enrollment day traffic spikes (> 1000 concurrent students). |
