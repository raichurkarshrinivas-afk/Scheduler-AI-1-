# Scheduler - Incident Response Guide

This guide establishes the operational incident response protocols, severity classifications, technical runbooks, and post-mortem procedures for the **Scheduler** platform.

---

## 1. Incident Severity Classifications

| Severity | Definition | Target Response | Target Resolution | Example Scenarios |
| :--- | :--- | :--- | :--- | :--- |
| **P1 - Critical** | Entire application unavailable; database down; data corruption in progress; security breach. | < 15 minutes | < 2 hours | PostgreSQL container crash; API returns 500 on all routes; unauthorized database access. |
| **P2 - Major** | Core workflow blocked for an entire department/institution; worker halted; solver unusable. | < 30 minutes | < 4 hours | Background worker offline; timetable solver failing for all drafts; publication publishing deadlocked. |
| **P3 - Minor** | Degraded performance or secondary feature outage; workaround available. | < 2 hours | < 24 hours | Google Calendar sync throwing 503; public feedback rate limits tripping under spiky load; PDF export formatting bug. |
| **P4 - Low** | Cosmetic issue; minor documentation discrepancy; non-blocking UI glitch. | < 24 hours | Next release | Minor layout misalignment on mobile viewport; localized wording improvement. |

---

## 2. Technical Incident Playbooks

### Playbook 1: Database Connection Failure (P1)
**Symptoms**: `/health/ready` returns HTTP 503; API endpoints return `500 Internal Server Error` with `OperationalError`.

**Diagnosis**:
1. Check database container status:
   ```bash
   docker compose ps db
   ```
2. Check database log output:
   ```bash
   docker compose logs --tail=100 db
   ```
3. Check host disk space: `df -h /var/lib/docker/volumes/scheduler_postgres_data`

**Remediation**:
* If disk is full: Safely prune unused Docker images/volumes (`docker system prune -a --volumes` with care) or resize underlying storage.
* If PostgreSQL process terminated abnormally: Restart PostgreSQL container:
  ```bash
  docker compose restart db
  ```
* If data corruption prevents PostgreSQL startup: Restore from the latest verified backup:
  ```bash
  python scripts/restore.py ./backups/latest.tar.gz --force
  ```

---

### Playbook 2: Background Worker Crash / Unhandled Exception (P2)
**Symptoms**: Solve jobs remain in `QUEUED` indefinitely; `/api/v1/jobs` shows jobs stalled without progressing through phases.

**Diagnosis**:
1. Check worker container status:
   ```bash
   docker compose ps worker
   ```
2. Inspect worker logs for Python tracebacks:
   ```bash
   docker compose logs --tail=200 worker
   ```
3. Inspect database for orphaned jobs with expired leases:
   ```sql
   SELECT id, job_type, status, lease_expires_at 
   FROM jobs 
   WHERE status = 'RUNNING' AND lease_expires_at < NOW();
   ```

**Remediation**:
1. Restart the background worker service:
   ```bash
   docker compose restart worker
   ```
2. Upon restart, `BackgroundWorker` automatically invokes `JobService.recover_expired_leases()`, resetting stalled jobs to `QUEUED` for retry.
3. If an individual solve job causes repeatable segmentation faults in OR-Tools (due to unsolvable recursive constraints), mark the offending job as `FAILED` to unblock subsequent queue items:
   ```sql
   UPDATE jobs 
   SET status = 'FAILED', error_code = 'SOLVER_CRASH', error_message = 'Manually terminated by operator due to unsolvable constraints' 
   WHERE id = '<job_id>';
   ```

---

### Playbook 3: Worker Lease Expiration & Fencing Conflict (P3)
**Symptoms**: Worker logs report `FencedOutException` or `Job <id> lost lease (fenced out)`.

**Root Cause**:
The solve job required more time than the configured lease window without heartbeating, or a network partition caused another worker to steal the lease.

**Remediation**:
1. Check solver parameters: If the academic draft has thousands of constraints, increase the solver time limit parameter (`parameters.time_limit_seconds`).
2. Verify heartbeat interval: Ensure `WORKER_HEARTBEAT_INTERVAL=5.0` is sufficiently smaller than `WORKER_LEASE_DURATION=30`.
3. Check worker host CPU throttling: High CPU starvation can delay the background heartbeat thread. Allocate additional CPU reservations in `compose.yaml`.

---

### Playbook 4: Stale Draft Revision Conflict (P3)
**Symptoms**: Coordinators receive HTTP `409 Conflict` with error detail: `Revision mismatch. The draft was modified by another session.`

**Root Cause**:
Optimistic concurrency control prevented a blind overwrite. Another coordinator edited the draft since the current user loaded it.

**Remediation**:
1. This is expected system behavior protecting timetable data integrity.
2. Instruct the user to refresh their browser tab to load the latest revision (`revision_id`).
3. If a draft is permanently wedged due to a cancelled publication flow, inspect the draft status in the database:
   ```sql
   SELECT id, name, status, revision_id, updated_at FROM timetable_drafts WHERE id = '<draft_id>';
   ```

---

### Playbook 5: Google Calendar 503 / Sync Failure (P3)
**Symptoms**: Communication outbox contains entries with `FAILED` or repeatedly retrying calendar events.

**Diagnosis**:
Inspect the outbox queue:
```sql
SELECT id, event_type, status, retry_count, last_error 
FROM communication_outbox 
WHERE status = 'FAILED' AND event_type = 'CALENDAR_SYNC';
```

**Remediation**:
1. Check Google API quota in Google Cloud Console.
2. Check OAuth token expiration. If the token refresh failed, prompt the institutional administrator to re-authorize the Google Workspace connection in Admin Settings.
3. The outbox processor uses exponential backoff (1s, 2s, 4s, 8s, up to max retries). Failed messages can be re-queued via the admin outbox dashboard.

---

### Playbook 6: Bot Submission Flood / Public Feedback Abuse (P3)
**Symptoms**: High volume of spam entries in `feedback` table; rate limit warnings in logs.

**Remediation**:
1. Verify honeypot and rate limits: The public feedback endpoint enforces 5 submissions per minute per IP and invisible honeypot validation (`website_url` field).
2. If an attacker bypasses with distributed IPs, enable upstream Nginx rate limiting in `deployment/nginx.conf`:
   ```nginx
   limit_req_zone $binary_remote_addr zone=feedback_limit:10m rate=2r/m;
   location /api/v1/feedback/public {
       limit_req zone=feedback_limit burst=3 nodelay;
       proxy_pass http://backend_upstream;
   }
   ```
3. Reload Nginx: `docker compose exec proxy nginx -s reload`.

---

## 3. Incident Communication Template

When a P1 or P2 incident occurs, communicate with institutional stakeholders using this standard format:

```text
INCIDENT STATUS: [Investigating / Identified / Monitoring / Resolved]
INCIDENT ID: INC-2026-XXXX
SEVERITY: [P1 - Critical / P2 - Major]
AFFECTED SERVICES: [Timetable Viewer / Exam Seating / Admin Portal]
IMPACT: [e.g., Staff cannot generate new drafts; published student views remain accessible]
CURRENT ACTIONS: [Engineering is currently inspecting worker container logs]
NEXT UPDATE: [Within 30 minutes]
```

---

## 4. Post-Mortem Report Template

Every P1 and P2 incident requires a blameless post-mortem completed within 48 hours:

```markdown
# Incident Post-Mortem: [INC-YYYY-XXXX] - [Brief Title]

**Date**: YYYY-MM-DD  
**Author**: [Engineer / Administrator Name]  
**Severity**: [P1 / P2]  
**Downtime Duration**: [XX minutes]

## 1. Executive Summary
Brief non-technical overview of what happened, user impact, and resolution.

## 2. Timeline (UTC)
- **HH:MM**: Alert triggered / user reported issue.
- **HH:MM**: First responder acknowledged incident.
- **HH:MM**: Root cause identified.
- **HH:MM**: Fix / mitigation deployed.
- **HH:MM**: System health verified; incident closed.

## 3. Root Cause Analysis
Explain the underlying failure mode (Five Whys method).

## 4. Remediation & Preventive Action Items
| Action Item | Type | Owner | Target Date |
| :--- | :--- | :--- | :--- |
| [e.g., Increase worker memory limit] | Prevent | John Doe | YYYY-MM-DD |
| [e.g., Add disk space alerting rule] | Detect | Jane Smith | YYYY-MM-DD |
```
