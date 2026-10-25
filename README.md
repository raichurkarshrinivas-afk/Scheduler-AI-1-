# Scheduler — Educational Timetabling & Examination Seating Logistics

Scheduler is a high-reliability, deterministic scheduling platform engineered for multi-tenant educational institutions (universities, colleges, and training academies).

The system automates:
1. **Academic Class & Practical Timetables**: Conflict-free weekly schedules resolving multi-dimensional constraints across instructors, rooms, student batches, and course requirements.
2. **Practical Examination Sittings**: Laboratory-based exam rotations, workstation allocations, equipment provisioning, and invigilation.
3. **Theory Examination Seating**: Desk layouts and seating plans enforcing a strict **one candidate per usable bench** rule and orthogonal anti-cheating distance isolation.

All core scheduling and seating engines operate **deterministically without external AI services**, guaranteeing auditable, reproducible, and private operations.

---

## Architecture & Technology Stack

| Layer | Technologies |
| :--- | :----------- |
| **Frontend** | React 18, TypeScript 5, Vite 5, Tailwind CSS, TanStack Query v5, Lucide React (SVG icons, zero emoji) |
| **Backend** | FastAPI, Python 3.12+, Uvicorn ASGI |
| **Persistence** | PostgreSQL 16, SQLAlchemy 2.x ORM, modern Psycopg 3 driver (`psycopg[binary]`), Alembic |
| **Constraint Solver** | Google OR-Tools CP-SAT with deterministic heuristic backtracking |
| **Background Worker** | Dedicated PostgreSQL-backed worker process for asynchronous solving jobs |
| **Security & Auth** | Server-side cookie sessions (`HttpOnly`, `SameSite=Lax`, `Secure`) |
| **Document Export** | ReportLab for printable PDF timetables and exam desk labels |
| **Testing** | pytest with HTTPX TestClient for backend; Playwright for browser tests |

---

## Directory Structure

```
Scheduler/
├── backend/                  # FastAPI backend service
│   ├── alembic/              # Database migration versions and environment
│   ├── app/                  # Application code
│   │   ├── api/              # API routers (health, v1 endpoints)
│   │   ├── core/             # Configuration, database engine, security
│   │   ├── models/           # SQLAlchemy 2.x declarative models
│   │   └── schemas/          # Pydantic v2 validation contracts
│   ├── tests/                # Pytest suites (health, isolation, engines)
│   ├── requirements.txt      # Exact pinned dependencies (zero floating versions)
│   └── requirements.lock     # Full frozen dependency lockfile
├── frontend/                 # React SPA
│   ├── src/                  # Components, pages, hooks, design tokens
│   │   ├── App.tsx           # Real-time health dashboard & scope overview
│   │   ├── index.css         # Minimalist light theme tokens & Tailwind directives
│   │   └── main.tsx          # TanStack Query client & root render
│   ├── package.json          # Exact pinned frontend dependencies
│   ├── package-lock.json     # Deterministic lockfile
│   ├── tailwind.config.js    # Custom design palette & typography
│   └── vite.config.ts        # Vite configuration with same-origin /api proxy
├── deployment/               # Container & reverse proxy configurations
│   ├── Dockerfile.backend    # Multi-stage Python 3.12 backend container
│   ├── Dockerfile.frontend   # Node 20 build + Nginx static server
│   ├── nginx.conf            # Production reverse proxy (ports 80/443)
│   └── nginx-spa.conf        # Single-page application router
├── docs/                     # Engineering documentation
│   ├── API_CONTRACT.md       # REST contracts & proxy conventions
│   ├── BUILD_STATUS.md       # Implementation & verification logs
│   ├── DECISIONS.md          # Architectural Decision Records (ADRs)
│   └── TEST_PLAN.md          # Multi-tier testing strategy & execution guide
├── compose.yaml              # Local multi-container orchestration
├── .env.example              # Environment variables template
├── .gitignore                # Repository ignore rules
├── README.md                 # Project documentation & startup guide
└── SPEC.md                   # Complete technical specification
```

---

## Exact Startup Commands

### Option A: Local Development (Host Backend & Frontend with Proxy)

This is the fastest workflow for development. PostgreSQL runs in Docker, while backend and frontend run natively with hot-reloading.

#### 1. Start PostgreSQL Database
```bash
# From project root
docker compose up -d db
```
*PostgreSQL will be accessible on `localhost:5432` (database: `scheduler`, user: `scheduler_user`, password: `scheduler_password`).*

#### 2. Start FastAPI Backend
```bash
cd backend

# Install pinned dependencies
python -m pip install -r requirements.txt

# Run migrations (if needed)
python -m alembic upgrade head

# Launch Uvicorn dev server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*Backend interactive docs: `http://127.0.0.1:8000/api/v1/docs`*  
*Liveness endpoint: `http://127.0.0.1:8000/health/live`*  
*Readiness endpoint: `http://127.0.0.1:8000/health/ready`*

#### 3. Start Vite Frontend
```bash
cd frontend

# Install exact dependencies
npm install

# Start Vite dev server
npm run dev
```
*Frontend opens at `http://localhost:5173`.*  
*All `/api/*` and `/health/*` calls are automatically forwarded to `http://127.0.0.1:8000` through the same-origin development proxy.*

---

### Option B: Full Containerized Deployment (Docker Compose)

Run the entire stack (PostgreSQL, Backend, Frontend, and Nginx reverse proxy) in isolated containers:

```bash
# Build and start all services
docker compose up --build
```

- **Application URL**: `http://localhost`
- **Backend API**: `http://localhost/api/v1`
- **Health Telemetry**: `http://localhost/health/live` and `http://localhost/health/ready`
- **Stop containers**: `docker compose down`
- **Stop and remove volumes**: `docker compose down -v`

---

## Running Verification Tests

### Backend Unit & Integration Tests (pytest)
```bash
cd backend
python -m pytest -v
```
To run only the health telemetry tests:
```bash
python -m pytest tests/test_health.py -v
```

### Frontend Type-Check & Production Build
```bash
cd frontend
npm run build
```
This runs TypeScript compilation (`tsc`) and Vite bundling into `frontend/dist/`.

---

## Health & Readiness Telemetry Endpoints

- **`GET /health/live`**: Process liveness probe. Returns HTTP 200 as long as the FastAPI process is responsive. Does **not** require database connectivity.
- **`GET /health/ready`**: Database readiness probe. Performs an active query (`SELECT 1`) using SQLAlchemy 2.x and Psycopg 3. Returns HTTP 200 when connected, or HTTP 503 when disconnected.
- Both endpoints are also available under `/api/health/live` and `/api/health/ready` to support same-origin proxy setups.

---

## Network Routing Architecture

### Local Development Routing
```
[Browser Client]
       │
       ▼ (http://localhost:5173)
[Vite Dev Server Proxy]
       │
       ├── /api/*   ────► [FastAPI Backend @ 127.0.0.1:8000]
       ├── /health/* ───► [FastAPI Backend @ 127.0.0.1:8000]
       └── /*        ───► [React SPA @ localhost:5173]
```

### Production Routing
```
[Internet Traffic]
       │
       ▼ (Port 80/443)
[Nginx Reverse Proxy]
       │
       ├── /api/*   ────► [FastAPI Backend Container:8000]
       ├── /health* ────► [FastAPI Backend Container:8000]
       └── /*        ───► [Nginx Frontend Static Container:80]
```

---

## Design System & Interface Standards

- **Minimalist Light Palette**:
  - Background: `#F7F8FA`
  - Surface: `#FFFFFF`
  - Text / Navy: `#14213D`
  - Primary Teal: `#0E7C66`
  - Warning Amber: `#F2B134`
  - Conflict Coral: `#D9480F`
  - Soft Borders: `#E2E6EC` / `#CBD2DC`
- **No Emoji Interface Icons**: UI strictly employs scalable SVG icons via Lucide React.
- **State Accessibility**: State is never communicated with color alone; all badges pair color with text labels (e.g. `[LIVE]`, `[OFFLINE]`, `[CONNECTED]`) and ARIA roles.
- **Non-Drag Alternatives**: Accessible dropdown selectors, keyboard hotkeys, and coordinate modals are provided for all grid and scheduling operations.

## Background Worker Startup & Operating Limits (Phase 6)

Scheduler includes a dedicated, fault-tolerant background worker process that claims and executes long-running optimization tasks (such as OR-Tools timetabling solves and anti-cheating seating allocations) using PostgreSQL row-level locks and fencing tokens.

### Starting the Worker

From the `backend/` directory:
```bash
python -m app.worker
```

With custom operational parameters:
```bash
python -m app.worker --worker-id worker-node-01 --poll-interval 2.0 --lease-duration 30 --heartbeat-interval 5.0 --max-concurrency 2
```

### Configuration Options & Operating Limits

| Parameter | CLI Flag | Env Var | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Worker Identifier** | `--worker-id` | `WORKER_ID` | `worker-<host>-<pid>-<hash>` | Unique identifier registered as `lease_owner` |
| **Poll Interval** | `--poll-interval` | `WORKER_POLL_INTERVAL` | `2.0` sec | Time between database polls when idle |
| **Lease Duration** | `--lease-duration` | `WORKER_LEASE_DURATION` | `30` sec | Initial lease validity window granted to a worker |
| **Heartbeat Interval** | `--heartbeat-interval` | `WORKER_HEARTBEAT_INTERVAL` | `5.0` sec | Frequency of lease renewal heartbeats |
| **Tenant Concurrency** | `--max-concurrency` | `MAX_INSTITUTION_CONCURRENCY` | `2` | Maximum simultaneous active jobs per tenant |
| **Max Attempts** | Per-Job | `max_attempts` | `3` | Maximum retry attempts before marking `FAILED` |
| **Retry Backoff** | Engine Rule | `calculate_backoff` | `5s * 2^(n-1)` | Exponential backoff delay between retry attempts |

### Operating Safeguards
- **Short Transactions**: Job claims commit immediately. Heavy compute runs completely outside database transactions.
- **Fencing Protection**: All updates verify `WHERE id = :id AND lease_token = :token`. Stale workers whose lease expired cannot overwrite newer attempts.
- **Graceful Shutdown**: On `SIGINT`, `SIGTERM`, or `SIGBREAK`, the worker stops polling, allows in-flight jobs to complete or safely release their lease, and shuts down cleanly.
- **Multi-Tenant Boundaries**: Jobs are strictly scoped to `institution_id`. Cross-tenant queries return `404 Not Found`.
