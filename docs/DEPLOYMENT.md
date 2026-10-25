# Scheduler - Deployment Guide

This document details the deployable container architecture, operating environments, controlled migration release process, and HTTPS configuration for the **Scheduler** academic timetable and examination scheduling system.

---

## 1. System Architecture

The deployment topology unifies the static frontend Single Page Application (SPA), the REST API, Server-Sent Events (SSE) notification streams, durable background worker processes, and relational storage under a single origin reverse proxy:

```
                  ┌─────────────────────────────────────────┐
                  │          Client Web Browser             │
                  └────────────────────┬────────────────────┘
                                       │ HTTPS (Port 443 / 80)
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          Nginx Reverse Proxy            │
                  │   - Unified origin routing              │
                  │   - SSE stream buffering disabled       │
                  │   - Security headers & TLS termination  │
                  └────────────┬───────────────┬────────────┘
         / (SPA static)        │               │ /api/ (REST & SSE)
                               ▼               ▼
        ┌─────────────────────────┐   ┌─────────────────────────────┐
        │    Frontend Service     │   │      FastAPI Backend        │
        │    (Nginx static SPA)   │   │  (Uvicorn - UID 1000)       │
        └─────────────────────────┘   └──────────────┬──────────────┘
                                                     │
                                                     │ Database Connection Pool
                                                     ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│  Dedicated Worker Service   │       │   PostgreSQL 16 Database    │
│    (Python - UID 1000)      │◄──────┤    (Persistent Volume)      │
│  - Durable solver execution │       └─────────────────────────────┘
│  - Lease heartbeat/fencing  │
└─────────────────────────────┘
```

---

## 2. Deployment Modes

### Mode 1: Local / Demonstration Setup
* **Target Audience**: Institutional evaluation, local testing, offline development.
* **Architecture**: All services (API, background worker, database, frontend, and reverse proxy) execute on a single physical host or developer workstation via Docker Compose.
* **Infrastructure Requirements**:
  * 4 CPU cores (x86_64 or ARM64).
  * 4 GB RAM minimum (6 GB recommended).
  * 20 GB free disk storage.
  * Docker Engine 24+ and Docker Compose v2.
* **Networking**: Accessible via `http://localhost` or host LAN IP.

### Mode 2: Always-On Institution / Pilot Setup
* **Target Audience**: Production pilot, multi-department academic scheduling, multi-user coordinator concurrency.
* **Architecture**: Supervised containers on dedicated virtual or bare-metal Linux infrastructure (Ubuntu 22.04 LTS / Debian 12 / RHEL 9), persistent Docker volumes, TLS/HTTPS termination via Let's Encrypt / automated reverse proxy, and offsite cryptographic backups.
* **Infrastructure Requirements**:
  * 4+ vCPUs (dedicated recommended for solver execution).
  * 8 GB+ RAM.
  * 50 GB+ SSD storage (NVMe recommended).
  * Static public IPv4/IPv6 address and registered institutional domain/subdomain.
* **Notice on Hosting**:
  > [!IMPORTANT]
  > **No free tier provider offers permanent, uninterrupted, always-on operation without idle spin-downs, maintenance windows, or ephemeral filesystem resets.**
  > Production institutional pilots require dedicated, persistent cloud or on-premise compute infrastructure.
  > Under strict policy: **Do not deploy publicly, purchase cloud services, alter DNS, or bind real external institutional accounts without explicit authorization.**

---

## 3. Container Packaging Specifications

### 3.1 Non-Root Runtime Security
Both API (`scheduler_backend`) and background worker (`scheduler_worker`) containers execute as an unprivileged system user:
* **Username**: `appuser` (Group: `appgroup`).
* **UID / GID**: `1000:1000`.
* Persistent directory permissions (`/app/storage`, `/app/logs`, `/app/exports`) are pre-assigned to `1000:1000` during image assembly.

### 3.2 Resource Limits
Configured in `compose.yaml`:
| Service | CPU Reservation | CPU Limit | RAM Reservation | RAM Limit | Stop Grace Period |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **db** (PostgreSQL 16) | 0.25 vCPU | 1.5 vCPU | 256 MB | 1024 MB | 20s |
| **backend** (FastAPI) | 0.25 vCPU | 2.0 vCPU | 256 MB | 1536 MB | 30s |
| **worker** (Solver) | 0.25 vCPU | 2.0 vCPU | 256 MB | 2048 MB | 45s |
| **frontend** (SPA) | 0.10 vCPU | 0.5 vCPU | 64 MB | 256 MB | 10s |
| **proxy** (Nginx) | 0.10 vCPU | 1.0 vCPU | 128 MB | 512 MB | 15s |

### 3.3 Explicit Persistent Storage Volumes
State is never stored in ephemeral container layers:
* `scheduler_postgres_data`: Backs `/var/lib/postgresql/data` for relational ACID persistence.
* `scheduler_storage_data`: Backs `/app/storage` for uploaded student/course CSV imports.
* `scheduler_logs_data`: Backs `/app/logs` for rotated audit and error logs.
* `scheduler_exports_data`: Backs `/app/exports` for published PDF schedules and CSV exports.

---

## 4. Controlled Deployment & Migration Sequence

> [!CAUTION]
> **Schema Race Prevention Rule**:
> Schema migrations (`alembic upgrade head`) MUST NOT be executed automatically in API worker startups.
> Running migrations on multiple parallel application worker startups introduces table locks, transaction deadlocks, and corrupted revision histories.

### The 5-Step Controlled Release Procedure

#### Step 1: Pre-Deployment Backup
Before modifying any configuration or pulling new container images, capture a verified snapshot:
```bash
python scripts/backup.py --output-dir ./backups
```
Ensure the backup archive and manifest checksum succeed.

#### Step 2: Execute Migration Release Command
Run schema migrations in isolation using the dedicated `migration` profile container:
```bash
docker compose --profile migration run --rm migration
```
This starts a one-off ephemeral container, validates database connectivity, applies pending Alembic revisions sequentially to `head`, and terminates with an exit code of `0`.

#### Step 3: Rolling Update of API Backend
Recreate the API backend container without downtime:
```bash
docker compose up -d --no-deps backend
```

#### Step 4: Restart Background Worker
Recreate the worker container to consume updated job contracts:
```bash
docker compose up -d --no-deps worker
```
The previous worker process traps `SIGTERM`, safely completes its current active job step or releases its lease token, and terminates within its 45-second grace window.

#### Step 5: Verify Deployment Health Checks
Verify service health probes:
```bash
# Liveness probe (verifies Uvicorn HTTP loop)
curl -f http://localhost/health/live

# Readiness probe (verifies PostgreSQL database connectivity)
curl -f http://localhost/health/ready
```
Both probes must return HTTP `200 OK` with JSON status payload.

### Rollback Procedure
If Step 2, 3, or 5 fails:
1. Revert container image tags in `compose.yaml` to the previous release.
2. If schema changes failed or caused regressions, restore the database from Step 1 snapshot:
   ```bash
   python scripts/restore.py ./backups/scheduler_backup_<timestamp>.tar.gz --force
   ```
3. Restart containers: `docker compose up -d`.

---

## 5. HTTPS & TLS Termination Guidance

### 5.1 Reverse Proxy TLS Configuration
In production pilot mode, Nginx terminates TLS on port 443. Add the following to `deployment/nginx.conf`:

```nginx
server {
    listen 80;
    server_name scheduler.institution.edu;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name scheduler.institution.edu;

    ssl_certificate /etc/letsencrypt/live/scheduler.institution.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/scheduler.institution.edu/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (Strict-Transport-Security)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy definitions for /api, /health, and /
    # (Include SSE configuration proxy_buffering off)
}
```

### 5.2 Environment Hardening for HTTPS
In `.env`, configure cookie flags:
```env
ENVIRONMENT="production"
COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE="lax"
```
When `COOKIE_SECURE=true`, browsers will refuse to transmit the session authentication cookie over unencrypted HTTP.

---

## 6. Real-Time SSE Reverse Proxy Tuning
The timetable communication subsystem emits live Server-Sent Events (`/api/v1/communication/sse`). Standard Nginx proxies buffer response bodies, breaking real-time dispatch.

The proxy configuration includes the required bypass directives:
```nginx
location ~* ^/api/v1/communication/sse {
    proxy_pass http://backend_upstream;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

---

## 7. Graceful Shutdown Implementation

* **API Backend**: Uvicorn runs with `--timeout-graceful-shutdown 25`. When Docker sends `SIGTERM`, Uvicorn ceases accepting new TCP connections, finishes in-flight HTTP requests within 25 seconds, and exits cleanly before Docker's 30-second `stop_grace_period` expires.
* **Worker**: Catches `SIGINT`, `SIGTERM`, and `SIGBREAK`, setting `stop_requested = True`. The worker loop stops polling for new jobs, heartbeats the currently running job, or finalizes lease cleanup before terminating.
