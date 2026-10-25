# Scheduler - Operations & Runbook Guide

This runbook provides institutional system administrators and DevOps engineers with operational procedures for daily monitoring, capacity planning, background worker operations, safe logging, and cryptographic key rotation.

---

## 1. Daily Health & Monitoring Checklist

### 1.1 Automated Health Probes
Scheduler provides distinct endpoints for orchestrators (Kubernetes, Docker Swarm, Nomad, AWS ECS):

| Endpoint | Probe Type | Checks Performed | Expected Response | Remediation if Failing |
| :--- | :--- | :--- | :--- | :--- |
| `GET /health/live` | **Liveness** | Uvicorn event loop responsiveness. Does NOT touch database. | `200 OK` `{"live": true}` | Container is locked/deadlocked; restart container. |
| `GET /health/ready` | **Readiness** | Executes `SELECT 1` against PostgreSQL connection pool. | `200 OK` `{"ready": true, "database": "connected"}` | Database unreachable or pool exhausted; inspect DB service. |
| `GET /health` | **Overview** | Overall operational summary. | `200 OK` (or `503` if degraded) | Check logs for downstream component failure. |

### 1.2 Routine Morning Checks
Run the following checks daily or automate via alerting rules:
1. **Container Status**: `docker compose ps` (all services should be `Up (healthy)`).
2. **Database Connectivity**: `curl -s http://localhost/health/ready | jq .`
3. **Storage Utilization**: Verify disk usage on persistent volume mounts:
   ```bash
   df -h /var/lib/docker/volumes/scheduler_*
   ```
4. **Recent Failed Background Jobs**:
   ```sql
   SELECT id, job_type, error_code, error_message, updated_at 
   FROM jobs 
   WHERE status = 'FAILED' AND updated_at > NOW() - INTERVAL '24 HOURS';
   ```

---

## 2. Resource Limits & Capacity Management

The containerized stack enforces explicit resource limits in `compose.yaml`:
* **CPU Sizing**:
  * The SAT/OR-Tools timetable solver is compute-intensive and can utilize up to 2 dedicated vCPUs per solve job.
  * Worker container CPU limits must be adjusted proportionally if multiple concurrent solve jobs are configured (`WORKER_MAX_CONCURRENCY`).
* **Memory Limits**:
  * Database: 1024 MB maximum.
  * API: 1536 MB maximum.
  * Worker: 2048 MB maximum (ensures large multi-period exam seating matrices do not trigger OOM).
* **Database Connection Pool**:
  * Backend API pool size: Default 20 connections, max overflow 10.
  * Ensure PostgreSQL `max_connections` is configured to at least `100` to accommodate API pools, worker pools, and administrative sessions.

---

## 3. Background Worker Operations & Concurrency

The background worker subsystem (`python -m app.worker`) executes asynchronous tasks including timetable generation, exam seating calculations, export bundling, and notification fanout.

### 3.1 Lease Heartbeats & Fencing Tokens
To prevent split-brain execution across multiple workers or during network partitions:
1. When a worker claims a queued job, it acquires a **30-second lease** and generates a unique cryptographic `lease_token`.
2. A background thread heartbeats the lease every **5.0 seconds**, extending the expiration timestamp.
3. If a worker process hangs or crashes, its lease expires after 30 seconds.
4. Another worker automatically recovers the expired job (`JobService.recover_expired_leases()`).
5. If the original hanging worker wakes up, any subsequent write attempt is **fenced out** (`FencedOutException`), discarding stale solver results.

### 3.2 Concurrency Throttling
To protect institutional fairness and database load, worker concurrency is throttled per institution:
* Setting: `WORKER_MAX_CONCURRENCY=2` (in `.env`).
* If Institution A already has 2 solve jobs running, subsequent jobs remain safely queued until one completes.

---

## 4. Safe Logging Practices

Scheduler enforces strict log sanitization via `SensitiveDataFilter` (`backend/app/core/logging_config.py`).

### 4.1 Data Redaction Standards
The following data categories are **never logged in cleartext**:
* Passwords, salt hashes, and authorization credentials.
* JWT bearer tokens and session cookie strings.
* Encryption keys and API secrets.
* Student personally identifiable information (PII) including individual exam accommodations or medical notes.

Example log output:
```text
[2026-10-22 17:30:15] [INFO] [scheduler.auth] User coordinator@apex.edu authenticated with password: [REDACTED]
[2026-10-22 17:30:18] [INFO] [scheduler.worker] Claimed timetable solve job with lease token: [REDACTED]
```

### 4.2 Log File Rotation
When logging to disk (`LOG_FILE=/app/logs/scheduler.log`), configure `logrotate` on the host:
```text
/var/lib/docker/volumes/scheduler_logs_data/_data/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
```

---

## 5. Cryptographic Keys & Secrets Rotation Procedures

### 5.1 Key Generation Commands
To generate cryptographically secure keys:
```bash
# Generate 32-byte URL-safe base64 secret (for SECRET_KEY)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate 32-byte (256-bit) hex key (for ENCRYPTION_KEY)
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5.2 `SECRET_KEY` Rotation Procedure
`SECRET_KEY` is used to sign JSON Web Tokens (JWT) for user sessions and CSRF validation.

> [!WARNING]
> **Operational Consequence of Rotating `SECRET_KEY`**:
> Rotating `SECRET_KEY` immediately and irrevocably **invalidates all active sessions across the institution**.
> Every logged-in user (administrators, coordinators, teachers, students) will be disconnected and required to re-enter their credentials.

**Rotation Steps**:
1. Schedule a planned maintenance window (preferably outside academic class hours).
2. Generate a new 32-byte secret key.
3. Update `SECRET_KEY` in `.env`.
4. Gracefully restart the backend container:
   ```bash
   docker compose up -d --no-deps backend
   ```
5. Notify institutional staff that active sessions have been refreshed.

### 5.3 `ENCRYPTION_KEY` Rotation Procedure
`ENCRYPTION_KEY` is used to encrypt third-party integration secrets (such as Google Calendar OAuth client secrets) at rest.

> [!CAUTION]
> **Operational Consequence of Rotating `ENCRYPTION_KEY`**:
> If `ENCRYPTION_KEY` is modified in `.env` without re-encrypting existing ciphertext in the database, **all existing encrypted credentials will become permanently unreadable**.

**Rotation Steps**:
1. Run a pre-rotation database backup: `python scripts/backup.py`.
2. Execute the re-encryption utility with both old and new keys:
   ```bash
   python -m app.scripts.rotate_encryption_key \
     --old-key "$CURRENT_ENCRYPTION_KEY" \
     --new-key "$NEW_ENCRYPTION_KEY"
   ```
3. Update `ENCRYPTION_KEY` in `.env` with the new key.
4. Restart the backend and worker containers:
   ```bash
   docker compose up -d --no-deps backend worker
   ```

### 5.4 PostgreSQL Database Password Rotation
To rotate database credentials without downtime:
1. In PostgreSQL, add the new password as a secondary credential or create a temporary role.
2. Update `POSTGRES_PASSWORD` and `DATABASE_URL` in `.env`.
3. Restart `backend` and `worker` services sequentially.
4. Verify `/health/ready` returns `200 OK`.
5. Revoke the previous password in PostgreSQL.
