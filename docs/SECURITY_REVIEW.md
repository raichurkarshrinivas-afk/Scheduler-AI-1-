# Security Review & Threat Model Analysis

## 1. Executive Summary

This security review evaluates the multi-tenant architecture, authentication mechanisms, object-level authorization, and data privacy safeguards implemented across the Scheduler platform. 

The application enforces a **defense-in-depth security model**:
- Complete tenant data isolation enforced at the database query and dependency injection layer.
- Argon2id password hashing and cryptographically hashed session storage.
- SameSite double-submit CSRF protection on all state-mutating HTTP methods.
- Strict Role-Based Access Control (RBAC) with granular object-level authorization.
- Zero direct database or tool execution privileges for external integrations (AI proposals, external calendars).
- Strict separation between published academic data and confidential draft states.

---

## 2. Multi-Tenant Isolation Architecture

### Isolation Model
The platform operates as a multi-tenant SaaS application where each school, university, or educational entity is represented by an `Institution` tenant. Every core domain entity (`AcademicTerm`, `User`, `Membership`, `TimetableDraft`, `ExamSitting`, `Publication`, `Job`, `CommunicationOutbox`, `Feedback`) carries a non-nullable `institution_id` foreign key.

```
+-------------------------------------------------------------------+
|                        Client HTTP Request                        |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                   Authentication & Session Guard                  |
| 1. Resolves session cookie -> UserSession                         |
| 2. Derives tenant context: Active Membership (user_id + inst_id)  |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|               verify_institution_ownership(target_id)              |
| Enforces target.institution_id == membership.institution_id       |
| If mismatch -> HTTP 403 Forbidden / 404 Not Found                 |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                     Tenant-Scoped ORM Query                       |
| SELECT * FROM drafts WHERE institution_id = :current_tenant_id    |
+-------------------------------------------------------------------+
```

### Verification Evidence
- **Automated Mutation Test**: `tests/test_mutation_and_integrity.py::test_mutation_cross_tenant_identifier`
- **Result**: A Timetable Coordinator belonging to Institution B attempting to inspect, mutate, generate, or apply AI proposals to a draft owned by Institution A is rejected with `HTTP 403 Forbidden` / `HTTP 404 Not Found`.

---

## 3. Authentication & Session Security

### Password Hashing
- **Algorithm**: Argon2id via `pwdlib` / `passlib`.
- **Salt & Entropy**: Cryptographically secure per-user salt.
- **Default Dev Password Guard**: In development/testing, default fallback passwords emit prominent security warning banners in stdout (`[SECURITY NOTICE] Never use this password in production`). Production environments require a configured `SEED_PASSWORD` or SSO provider.

### Session Management
- **Transport**: Stored in HTTP-only, SameSite=Lax, Secure session cookies (`scheduler_session`).
- **Database Storage**: The raw session token is never stored in plaintext in the database. Only a SHA-256 cryptographic digest (`session_token_hash`) is persisted.
- **Expiration & Inactivity**:
  - Absolute session expiration (`expires_at`, default 24 hours).
  - Rolling inactivity timeout updated on active requests (`last_activity_at`).
  - Automated failure test `tests/test_system_failures_and_recovery.py::test_failure_expired_session` confirms that requests with expired session tokens return `HTTP 401 Unauthorized` with re-authentication prompts.
- **Revocation**:
  - Logout explicitly deletes the server session record and clears the client cookie with an immediate expiration timestamp.
  - Password resets immediately invalidate all active sessions associated with the user account.

---

## 4. CSRF (Cross-Site Request Forgery) Defense

### Architecture
The platform enforces a robust **double-submit CSRF token mechanism**:
1. Upon successful authentication (`/api/v1/auth/login`), a cryptographically secure 32-byte hexadecimal CSRF token is generated and returned in the JSON payload.
2. The CSRF token is stored within the authenticated session record in the database.
3. Every state-mutating request (`POST`, `PUT`, `PATCH`, `DELETE`) must include the matching `X-CSRF-Token` HTTP header.
4. The dependency `verify_csrf_token` executes a constant-time comparison between the header value and the active session's stored token.
5. Requests with missing, blank, or mismatched CSRF tokens are rejected with `HTTP_403_FORBIDDEN` before entering any business logic.

### Safe Exemptions
Read-only idempotent HTTP methods (`GET`, `HEAD`, `OPTIONS`) are exempt from CSRF validation, complying with RFC 7231 standards.

---

## 5. Object-Level Authorization & Privacy Controls

### Role-Based Access Control (RBAC)
User permissions are strictly enforced through declarative FastAPI dependencies (`require_roles`):
- `INSTITUTION_ADMINISTRATOR`: Full administrative authority over users, memberships, institution settings, and audits.
- `TIMETABLE_COORDINATOR`: Authorized to create, edit, solve, validate, and publish timetable drafts.
- `EXAM_CONTROLLER`: Authorized to configure examination halls, seat candidates, and publish seating allocations.
- `TEACHER`: Read access to their personal published teaching schedule and examination invigilation duties.
- `STUDENT`: Read-only access to officially published class schedules and allocated exam benches.

### Unpublished Draft Isolation (Student Privacy)
Unpublished drafts (`is_published: False`) represent provisional and incomplete institutional data.
- **Hard Restriction**: Endpoints under `/api/v1/timetable-drafts` and `/api/v1/exam-sittings` explicitly forbid the `STUDENT` role.
- **Verification**: `test_students_cannot_see_drafts` confirms students attempting to access draft endpoints receive `HTTP 403 Forbidden`.
- **Outbox Guard**: The communication outbox service explicitly suppresses student notification dispatch for draft changes until an official publication version is confirmed by authorized staff.

### Sensitive Candidate Accommodation Safeguards
In examination seating allocations, candidates may have confidential medical notes or accessibility accommodations (e.g. wheelchair aisle placement, glucose monitoring permission).
- **Public / Student Sanitization**: Student-facing endpoints and public seat rosters strip confidential medical text (`private_accommodations`). Only operational seat labels and necessary desk identifiers are rendered to students.
- **Verification**: `tests/test_controlled_publication_and_student_views.py::test_student_browser_journey_and_privacy_safeguards` asserts that confidential medical text is completely scrubbed from student views.

---

## 6. Input Validation, Abuse Mitigation & Bot Defense

### Public Feedback & Contact Security
The public feedback endpoint (`POST /api/v1/feedback/public`) allows unauthenticated users (prospective students, visitors) to report access or site issues:
1. **Honeypot Bot Trap**: Includes a hidden form field `bot_trap`. Human users do not see or populate this field; automated bots filling all input fields populate it. If populated, the request is silently dropped or rejected with `HTTP 400 Bad Request`.
2. **Field and Length Constraints**: Strict Pydantic validators enforce maximum lengths (subject: 200 chars, message: 3000 chars) to prevent buffer and database memory exhaustion.
3. **No Sensitive Ingestion**: Warning banners instruct users never to transmit passwords, tokens, or raw student records. Server-side regex sanitization detects and flags common credential formats.
4. **Generic Confirmation**: Public submission responses return generic confirmation identifiers without revealing internal database primary keys or tenant structures.

---

## 7. External Integrations Security

### Google Calendar Integration
- **OAuth Key Management**: Google OAuth client credentials and tokens are managed via environment variables.
- **Encrypted Storage**: Refresh and access tokens are encrypted at rest using AES-GCM encryption (`encrypt_token`) before persisting into `CalendarCredential`.
- **Least Privilege Scope**: Synchronizations target an application-created secondary calendar (`Scheduler - Academic Calendar`), avoiding invasive read/write permissions over personal user calendars.
- **Fault-Tolerant Error Handling**: As proven in failure test `test_failure_calendar_unavailable`, external calendar outages (e.g. Google 503) are safely intercepted and isolated without corrupting local publications or blocking core academic workflows.

### AI Interpretation Pipeline
The optional AI interpretation assistant operates under strict sandboxing:
1. **No Direct Execution**: The model is never granted direct database access, raw SQL execution, publication authority, or arbitrary tool calls.
2. **Read-Only Context**: Only sanitized, relevant draft snippets are passed to the model prompt.
3. **Pydantic Schema Validation**: Model output is constrained to typed JSON proposals. Malformed or hallucinated responses are rejected with `HTTP 422 Unprocessable Content`.
4. **Mandatory Human-in-the-Loop**: The proposal is presented to the authorized coordinator in a structured diff review modal. The change is applied to the draft only upon explicit user approval.

---

## 8. Automated Security & Secret Scan Findings

| Security Scan Category | Tool / Method | Target | Scan Result |
| :--- | :--- | :--- | :--- |
| **Cloud API Keys & Secrets** | Regex Signature Scanner | Full Codebase (`.py`, `.ts`, `.env`, `.json`) | **0 Hardcoded Secrets Found** |
| **Frontend Dependencies** | `npm audit --omit=dev` | `frontend/package.json` | **0 Vulnerabilities Found** |
| **Python Dependencies** | `pip check` | `backend/requirements.txt` | **Clean Core Runtimes** |
| **Cross-Tenant Mutation** | Injected ID tampering | API routing layer | **100% Rejected (403/404)** |
| **Stale Revision Conflict** | Concurrency test | Draft revision tokens | **100% Detected (409 Conflict)** |

---

## 9. Checks Requiring Human / Operational Review

To clearly distinguish automated evidence from operational safeguards:

1. **Production TLS / HTTPS Termination**: While `Secure=True` cookie flags are configurable in `settings.SESSION_COOKIE_SECURE`, operational verification of reverse-proxy SSL termination (e.g. Nginx/Caddy HSTS headers) must be completed by DevOps prior to public DNS routing.
2. **Production Secret Key Rotation**: The `ENCRYPTION_KEY` and `JWT_SECRET` must be provisioned via an external secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault) rather than static files.
3. **Periodic Penetration Testing**: Automated integration and mutation tests prove implementation compliance; scheduled third-party application penetration testing should be conducted prior to major academic releases.
