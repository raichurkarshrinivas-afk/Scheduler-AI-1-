# Scheduler — Technical Specification

## 1. Product Definition
**Scheduler** is a robust, deterministic educational scheduling platform designed to manage:
1. **Academic Class & Practical Timetables**: Conflict-free weekly schedules for lectures, tutorials, and laboratory practical sessions.
2. **Practical Examination Sittings**: Laboratory-based exam rotations, workstation allocations, equipment provisioning, and invigilation.
3. **Theory Examination Seating**: Room layouts and desk seating plans for written examinations ensuring physical separation and anti-cheating distance rules.

---

## 2. Initial Scope & Boundaries

### 2.1 Multi-Tenant Isolation
- The system supports one or more completely isolated educational institutions.
- Multi-tenancy is enforced at the database query and dependency injection layers via strict `institution_id` boundaries.
- Cross-tenant data access attempts are rejected immediately with HTTP 404/403 to prevent information disclosure.

### 2.2 Exam Dates & Periods
- Examination dates, session times, and testing periods are entered directly and fixed by institutional staff (Exam Controllers / Timetable Coordinators).
- Scheduling engines operate within user-defined calendar parameters rather than guessing arbitrary dates.

### 2.3 Physical Seating Principle
- **One candidate per usable bench / desk**: In theory examination halls, only one candidate is allocated per usable physical bench.
- Anti-cheating orthogonal spacing prevents candidates taking the same subject or from the same cohort from occupying adjacent desks (left, right, front, or behind).

### 2.4 Autonomous, AI-Free Core Engine
- All timetable solving, conflict checking, and seating allocations run deterministically using combinatorial constraint programming (Google OR-Tools CP-SAT) and graph-based heuristics.
- Core operation requires **no external artificial intelligence (AI) services**, paid model APIs, or opaque LLM calls, guaranteeing predictable, auditable, and reproducible outputs.

### 2.5 Schedule Lifecycle: Draft, Check, Review, Publish
Every timetable and examination seating plan advances through four governed stages:
1. **Draft**: Initial configuration and automated generation by coordinators.
2. **Check**: Automated constraint verification, clash detection, and capacity validation.
3. **Review**: Administrative and departmental stakeholder review, adjustments, and sign-off.
4. **Publish**: Formal release to the institution. Once published, the schedule is locked against casual modification.

### 2.6 Student Access Governance
- Students have **read-only access strictly to authorised, published information** for their enrolled cohort and registered courses.
- Students cannot view internal drafts, unallocated faculty notes, cross-departmental administrative records, or other students' private seat allocations.

### 2.7 Feedback Submission & Administrative Triage
- Teachers and students can submit contextual feedback and conflict notices against published or review-stage schedules.
- Coordinators and administrators triage, investigate, prioritize, and resolve feedback via an audit-logged workflow.

---

## 3. User Roles & Permissions

The platform enforces five distinct roles across each institution:

| Role | Core Responsibilities & Permissions |
| :--- | :---------------------------------- |
| **Institution Administrator** | Manages institution profile, academic years/terms, departments, user provisioning, global facility definitions, and feedback triage escalations. |
| **Timetable Coordinator** | Configures time slots, courses, instructor assignments, batches, runs timetable solver, and advances timetables through Draft &rarr; Check &rarr; Review &rarr; Publish. |
| **Exam Controller** | Configures exam periods, registers candidate enrollments, assigns exam rooms, defines physical bench layouts, runs seating solver, and publishes seating charts. |
| **Teacher** | Specifies availability preferences and unavailability constraints, views assigned class/practical timetables, views invigilation duties, and submits feedback. |
| **Student** | Views published class/practical timetables for their enrolled batch, views individual examination hall tickets, seat assignments, and desk labels, and submits inquiries/feedback. |

---

## 4. Technology Stack

### 4.1 Frontend Architecture
- **Framework & Language**: React 18 with TypeScript 5, bundled via Vite.
- **Styling**: Tailwind CSS with custom design tokens for light theme consistency.
- **3D Visualization (Public Landing Hero Only)**: Three.js via React Three Fiber (`@react-three/fiber`) and Drei (`@react-three/drei`) with procedural geometry.
- **Server State Management**: TanStack Query (React Query v5) for asynchronous caching, stale-time invalidation, and real-time polling.
- **Accessible UI Primitives**: Accessible headless primitives with full ARIA landmarks, focus management, screen-reader text, and keyboard navigation.
- **Icons**: Semantic SVG icons via Lucide React. **No emoji interface icons**.

### 4.2 Backend Architecture
- **API Framework**: FastAPI (Python 3.12 / 3.14 compatible) with ASGI server Uvicorn.
- **Persistence Layer**: SQLAlchemy 2.x ORM with declarative models and type annotations.
- **Database Driver**: Modern Psycopg 3 (`psycopg[binary]`) for high-performance PostgreSQL interaction.
- **Database Engine**: PostgreSQL 16 relational database with row-level tenant indexing.
- **Schema Migrations**: Alembic for version-controlled, auditable database migrations.
- **Validation & Serialization**: Pydantic v2 and `pydantic-settings` for strict request/response data contracts.
- **Constraint Programming Engine**: Google OR-Tools CP-SAT (Constraint Programming — Satisfiability) for multi-dimensional timetable scheduling and exam seating optimization.
- **Background Worker (Phase 6)**: Dedicated PostgreSQL-backed asynchronous worker process (`app.worker`) for long-running solving and allocation jobs:
  - Leased execution model with short claim transactions (`FOR UPDATE SKIP LOCKED`).
  - Periodic worker heartbeats extending lease expiry every 5 seconds.
  - Strict fencing via unique attempt `lease_token` to prevent stale workers from overwriting newer attempts.
  - Automatic expired-lease recovery and exponential backoff retries up to `max_attempts`.
  - Enforced per-institution concurrency caps (default 2 simultaneous jobs) to prevent tenant monopolization.
  - Signal-aware graceful shutdown (`SIGINT`, `SIGTERM`, `SIGBREAK`) allowing in-flight jobs to complete or safely release leases.
- **Authentication & Sessions**: Server-side cookie sessions (`HttpOnly`, `SameSite=Lax`, secure cookie flags) to protect authentication tokens.
- **Document Export Engine**: ReportLab for generating high-fidelity, printable PDF timetables and exam desk labels.
- **Testing Suites**: pytest with HTTPX TestClient for backend API and engine verification.

---

## 5. Design System & Interface Guidelines

The design follows a clean, minimalist, high-contrast light interface optimized for institutional productivity:

### 5.1 Color Palette
- **Background**: `#F7F8FA` (Soft neutral background)
- **Surface**: `#FFFFFF` (Clean white cards, panels, and modal dialogs)
- **Text / Navy**: `#14213D` (Deep readable navy for primary typography and headers)
- **Primary Teal**: `#0E7C66` (Primary action buttons, active navigation states, verified indicators)
- **Warning Amber**: `#F2B134` (Soft warnings, pending review stages, capacity alerts)
- **Conflict Coral**: `#D9480F` (Critical hard conflicts, double-booking errors, disconnected status)
- **Borders & Dividers**: `#E2E6EC` (Subtle dividers) and `#CBD2DC` (Active borders)

### 5.2 Aesthetic & Ergonomic Principles
- **Soft Borders & Restrained Shadows**: Crisp 1px borders paired with subtle, low-opacity elevation shadows (`0 1px 3px rgba(20, 33, 61, 0.05)`).
- **No Emoji Interface Icons**: All indicators use curated, scalable vector icons (SVG) with consistent stroke widths.
- **Multi-Modal State Signaling (Do Not Rely on Color Alone)**: Every status indicator pairs color with explicit text labels (e.g. `[LIVE]`, `[OFFLINE]`, `[PUBLISHED]`, `[DRAFT]`) and ARIA status attributes.
- **Accessible Alternatives for Drag Operations**: Where timetables or seat arrangements support drag-and-drop interactions, equivalent keyboard accessible modals, dropdown selectors, and manual coordinate inputs must always be provided.

### 5.3 Typography System
- **Headings**: Sora (`'Sora', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`).
- **Body & Interface Labels**: DM Sans (`'DM Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`).
- **Resilient Fallbacks**: Font stacks provide seamless system fallbacks to prevent blocking network font dependencies during local or air-gapped deployments.

### 5.4 3D Presentation & Visual Intent (Phase 4 Approved Direction)
- **Product Atmosphere**: Minimalist, spatial, and interactive educational planning environment—distinct from marketing landing pages or gaming aesthetics.
- **Isolated 3D Boundary**: 3D is strictly confined to a single, lazily loaded Canvas within the public landing page hero section.
- **2D Operational Shells**: Authenticated staff and student dashboards remain strictly 2D and task-focused. Perspective transforms, mouse tilts, or depth skews are never applied to operational timetable matrices, tables, seat maps, or forms.
- **Procedural Geometry Only**: The 3D scene is constructed entirely from mathematical primitives and procedural meshes in code (box slabs, cylinders, rounded blocks) without external model downloads, paid assets, or external textures.
- **Content Hierarchy**: Headings, navigation, explanatory text, and buttons reside in semantic HTML outside the WebGL canvas.
- **Motion & Accessibility Rules**:
  - Parallax rotation is clamped to subtle angles (max `0.15 rad`).
  - Scroll hijacking is strictly forbidden.
  - Idle animation is paused when the hero is off-screen (`IntersectionObserver`) or when the browser tab is hidden.
  - When `prefers-reduced-motion: reduce` is enabled, pointer tracking and floating motions are disabled, rendering a static scene or SVG fallback.
- **Fault-Tolerant Fallbacks**: Canvas is wrapped in an Error Boundary and paired with a local vector SVG fallback illustration matching the scene composition if WebGL is unavailable.
- **Unimplemented Modules Policy**: Unbuilt features (e.g. solver executions or PDF exports scheduled for subsequent phases) are labelled transparently with "Not implemented yet" panels; fake success states are strictly prohibited.

---

## 6. Health & Telemetry Contracts

### 6.1 Liveness Probe (`GET /health/live`)
- **Requirement**: Evaluates process responsiveness. Must **not** require database connectivity.
- **Success Status**: `200 OK`

### 6.2 Readiness Probe (`GET /health/ready`)
- **Requirement**: Evaluates active end-to-end database connectivity via a round-trip test query (`SELECT 1`).
- **Success Status**: `200 OK`
- **Failure Status**: `503 Service Unavailable`

---

## 7. Development & Production Network Routing

### 7.1 Local Development Proxy
- The frontend dev server runs on `http://localhost:5173`.
- The browser dispatches API requests to same-origin path `/api/*` and `/health/*`.
- Vite reverse-proxies `/api` and `/health` requests to `http://127.0.0.1:8000`.

### 7.2 Production Routing
- An Nginx reverse proxy listens on public port 80/443.
- Requests matching `/api/*` and `/health/*` are forwarded upstream to the FastAPI backend service (`http://backend:8000`).
- All other requests are routed upstream to the static single-page application server (`http://frontend:80`) with fallback to `index.html`.
