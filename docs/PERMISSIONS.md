# Scheduler Permission Matrix & Authentication Architecture

## 1. Overview & Security Principles

Access control in Scheduler is strictly role-based, institution-bounded, and enforced at the API dependency injection and repository layers.

### The Five Governed Roles
1. **Institution Administrator (`INSTITUTION_ADMINISTRATOR`)**: Oversees institutional configuration, academic departments, terms, user membership provisioning, facilities, administrative resets, and security triage.
2. **Timetable Coordinator (`TIMETABLE_COORDINATOR`)**: Designs and manages academic and practical class timetables, curricula, sections, teacher availabilities, and advances timetables through the Draft &rarr; Check &rarr; Review &rarr; Publish lifecycle.
3. **Exam Controller (`EXAM_CONTROLLER`)**: Configures fixed exam dates/periods, practical examination sittings, physical theory exam desk matrices, anti-cheating seating allocations, and publishes seating charts.
4. **Teacher (`TEACHER`)**: Manages individual availability and unavailability preferences, views assigned teaching timetables and exam invigilation duties, and submits schedule feedback.
5. **Student (`STUDENT`)**: Enjoys strictly read-only access to authorised published timetables for enrolled sections, personal exam hall tickets, and seat allocation desk labels.

---

## 2. Resource Permission Matrix

| Resource / Entity | Operation | Institution Administrator | Timetable Coordinator | Exam Controller | Teacher | Student |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Institutions** | Read Profile | Yes | Yes | Yes | Yes | Yes |
| | Update Settings | Yes | No | No | No | No |
| **Users & Memberships** | View User Directory | Yes | Yes (Staff) | Yes (Staff) | Department Only | No |
| | Provision / Revoke Roles | Yes | No | No | No | No |
| | Administrative Password Reset | Yes (Tenant Only) | No | No | No | No |
| **Authentication & Sessions**| Login (`POST /api/v1/auth/login`) | Yes | Yes | Yes | Yes | Yes |
| | Logout (`POST /api/v1/auth/logout`)| Yes | Yes | Yes | Yes | Yes |
| | Change Password (`POST /api/v1/auth/change-password`)| Self | Self | Self | Self | Self |
| | View Profile (`GET /api/v1/me`)| Self | Self | Self | Self | Self |
| | View Active Sessions (`GET /api/v1/me/sessions`)| Self | Self | Self | Self | Self |
| | Revoke Session (`DELETE /api/v1/me/sessions/{id}`)| Self | Self | Self | Self | Self |
| **Departments & Terms** | Create / Update / Delete | Yes | Read Only | Read Only | Read Only | Read Only |
| | Set Term Dates / Timezone | Yes | Read Only | Read Only | Read Only | Read Only |
| **Curriculum & Subjects** | Create / Update Subjects | Yes | Yes | Read Only | Read Only | Read Only |
| | Define Course Offerings | Yes | Yes | Read Only | Read Only | Read Only |
| **Sections & Enrolments** | Create / Manage Sections | Yes | Yes | Read Only | Read Only | Read Only |
| | Enrol Students | Yes | Yes | Read Only | No | Self Read |
| **Faculty & Eligibility** | Manage Teacher Records | Yes | Yes | Read Only | Self Profile | No |
| | Define Subject Qualifications | Yes | Yes | Read Only | Read Only | No |
| | Submit Unavailability Rules | Yes (Admin) | Yes | No | Self Only | No |
| **Facilities & Rooms** | Define Buildings / Rooms | Yes | Read Only | Read Only | Read Only | Read Only |
| | Configure Room Exam Benches | Yes | Read Only | Yes | Read Only | Read Only |
| | Configure Lab Workstations | Yes | Read Only | Yes | Read Only | Read Only |
| **Academic Timetables** | Create Draft / Check Clashes | Yes | Yes | No | No | No |
| | Review / Modify Assignments | Yes | Yes | No | Feedback Only | No |
| | Publish Timetable | Yes | Yes | No | No | No |
| | View Draft Timetables | Yes | Yes | No | No | **Forbidden** |
| | View Published Timetables | Yes | Yes | Yes | Assigned / Enrolled | Enrolled Only |
| **Examination Sittings** | Define Exam Periods & Dates | Yes | No | Yes | Read Only | Read Only |
| | Generate Seating Layouts | Yes | No | Yes | No | No |
| | View Draft Seating Layouts | Yes | No | Yes | No | **Forbidden** |
| | Publish Exam Seating | Yes | No | Yes | No | No |
| | View Personal Hall Ticket / Seat | Yes | Yes | Yes | Assigned Duties | Self Seat Only |
| **Calendar Exceptions** | Add Holiday / Blackout Date | Yes | Yes | Yes | Read Only | Read Only |
| **Constraint Rules** | Configure Weights & Hard Rules | Yes | Yes | Yes | Read Only | No |
| **Audit Events** | View Immutable System Audit Log | Yes | No | No | No | No |
| **Feedback & Triage** | Submit Schedule Feedback | Yes | Yes | Yes | Yes | Yes |
| | Triage / Resolve Feedback | Yes | Yes | Yes | No | No |

---

## 3. Strict Student Authorization Boundaries

1. **Zero Access to Drafts**: Under no circumstances can a user with role `STUDENT` query or view session or exam seating records in `DRAFT`, `CHECKED`, or `REVIEWED` status.
2. **Enrolled Section Scoping**: A student can only view published class timetables for course sections in which their `student_id` possesses an active `ENROLLED` record.
3. **Private Seating Allocation & Record Ownership**: A student can only retrieve their own student record (`GET /api/v1/students/{id}`) and assigned bench label (`SeatAssignment` / desk label). Accessing any record where `record.student_id != current_user.student.id` is rejected immediately with `HTTP 403 Forbidden`.
4. **Tenant Isolation**: Access tokens and sessions are strictly scoped to the authenticated institution. Attempting to access an entity belonging to another institution yields `HTTP 404 Not Found` (or `403 Forbidden`).

---

## 4. Server-Side Browser Session Mechanics

### Token Generation & Storage
- **Cryptographic Randomness**: Session tokens are generated using Python's `secrets.token_urlsafe(32)`, providing 256 bits of high-entropy randomness.
- **Digest-Only Database Storage**: The raw token is **never** stored in the database. Instead, only its `SHA-256` hexadecimal digest (`hash_session_token(token)`) is persisted in `user_sessions.session_token_hash`. If the database is compromised, active session credentials cannot be extracted.
- **Cookie Transport**: The raw token is sent to the browser via an `HttpOnly` cookie named `scheduler_session`.
- **Zero LocalStorage Policy**: The frontend never stores session tokens, bearer tokens, or user credentials in `localStorage` or `sessionStorage`. All browser requests automatically attach the session cookie via `credentials: 'include'`.

### Cookie Security & Deployment Configuration
- **HttpOnly**: Guaranteed to prevent JavaScript access and protect against cross-site scripting (XSS) exfiltration.
- **SameSite**: Configured to `SameSite=lax` (or `strict`), mitigating Cross-Site Request Forgery (CSRF) across external origins while maintaining expected top-level browser navigation.
- **Secure Flag**:
  - In Production: `COOKIE_SECURE=True`. The browser will only transmit the cookie over encrypted `https://` connections.
  - In Development: `COOKIE_SECURE=False` (explicitly documented setting) to allow local testing over `http://localhost`.

### Session Lifecycle & Invalidation Rules
- **Configurable Expiry**: Sessions are created with an explicit expiration timestamp (default: 86,400 seconds / 24 hours), validated on every request.
- **Activity Tracking**: Each authenticated request updates `last_activity_at` for idle session auditing.
- **Session Rotation**:
  - A brand-new session token is generated upon login (`POST /api/v1/auth/login`).
  - When a user changes their password (`POST /api/v1/auth/change-password`), **all other active sessions** for that user are immediately revoked (`revoked_at = utc_now`), while the current session rotates to a fresh token.
- **Explicit Logout**: Calling `POST /api/v1/auth/logout` sets `revoked_at` in the database and dispatches response headers that expire the cookies (`max_age=0`).
- **Selective Revocation**: Users can inspect all active devices and sessions via `GET /api/v1/me/sessions` and selectively revoke any session via `DELETE /api/v1/me/sessions/{id}`.

---

## 5. CSRF Protection Architecture

Scheduler implements a strict **Double-Submit Cookie Pattern** coupled with session-bound CSRF token validation:
1. **CSRF Cookie**: On authentication, a cryptographically random CSRF token (`secrets.token_hex(24)`) is stored in `user_sessions.csrf_token` and sent in a non-HttpOnly cookie `scheduler_csrf` (`SameSite=lax`).
2. **Request Header**: For all state-changing HTTP methods (`POST`, `PUT`, `PATCH`, `DELETE`), the frontend client must supply the token in the `X-CSRF-Token` header.
3. **Backend Validation**: `verify_csrf_token` dependency compares the header token against the active session's stored `csrf_token` using constant-time comparison (`secrets.compare_digest`). If missing or mismatched, the request is rejected with `HTTP 403 Forbidden`. Safe methods (`GET`, `HEAD`, `OPTIONS`) bypass CSRF checks.

---

## 6. Password Hashing & Administrative Reset Workflow

### Argon2id Hashing
- Standardized on Argon2id via `argon2-cffi` adhering to RFC 9106 recommended interactive parameters:
  - `time_cost = 3`
  - `memory_cost = 65536` (64 MiB RAM)
  - `parallelism = 4`
  - `hash_len = 32`
- Legacy or insecure algorithms (`md5`, `sha1`, plain `bcrypt`) are strictly prohibited.

### Generic Login Failures & Timing-Attack Mitigation
- Login requires three fields: `institution_code`, `identifier` (Email, Teacher Employee ID, or Student PRN), and `password`.
- If the institution does not exist, the user is not found, or the password does not match, the API always returns an identical, generic error:
  `HTTP 401 Unauthorized: "Invalid institution, identifier, or password."`
- To prevent side-channel timing attacks that could disclose whether an identifier exists, the backend executes a dummy Argon2id hash verification (`_DUMMY_ARGON2_HASH`) whenever a user or institution lookup fails.

### Forced Password Change on Temporary Credentials
- Users created by administrative provisioning or reset are flagged with `must_change_password = True`.
- All protected application endpoints reject requests with `HTTP 403 Forbidden` and header `X-Error-Code: PASSWORD_CHANGE_REQUIRED` until the user completes `POST /api/v1/auth/change-password`.
- Password policy enforces:
  - Minimum 10 characters.
  - At least one uppercase letter (`A-Z`).
  - At least one lowercase letter (`a-z`).
  - At least one number (`0-9`).
  - At least one special symbol.

### Administrative Reset Workflow
- Institution administrators reset member credentials via `POST /api/v1/admin/users/{id}/reset-password`.
- Generates a secure, temporary 14-character alphanumeric password and sets `must_change_password = True`.
- Institution administrators **cannot** reset passwords for users in other institutions or platform superusers.
- The platform avoids spoofable, external email-based self-recovery in favor of verified institutional in-person / helpdesk administrative reset.

---

## 7. Rate-Limiting Architecture

### Interface & Abstract Contract
Scheduler defines an extensible rate-limiting interface in `backend/app/core/rate_limit.py`:
```python
class BaseRateLimiter(ABC):
    @abstractmethod
    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int, int]:
        """Returns (is_limited, current_count, retry_after_seconds)"""
        pass
```

### Single-Instance Implementation: In-Memory Sliding Window
- `InMemorySlidingWindowRateLimiter` tracks timestamped access occurrences in a thread-safe sliding window deque (`collections.defaultdict(deque)` protected by a threading `Lock`).
- Automatically expires entries older than the evaluation window.
- Applied to sensitive auth endpoints:
  - `POST /api/v1/auth/login`: 5 attempts per minute per IP + institution combination.
  - `POST /api/v1/auth/change-password`: 5 attempts per minute.
  - `POST /api/v1/admin/users/{id}/reset-password`: 10 attempts per minute.

### Documented Multi-Instance Distributed Limitations
> [!IMPORTANT]
> The default in-memory sliding window limiter is designed exclusively for single-process ASGI deployments.
> When scaling horizontally across multiple web nodes behind a load balancer:
> 1. In-memory windows are isolated to each individual worker process and do not share state.
> 2. An attacker could bypass rate limits by distributing requests across round-robin backend instances.
> 3. Production multi-node deployments MUST configure a distributed backend (such as Redis or Memcached) by implementing `BaseRateLimiter` using atomic sliding window transactions (`ZADD` / `ZREMRANGEBYSCORE`).

---

## 8. Audit Logging Policy

All security, authentication, and administrative actions generate an immutable record in `audit_events`:
- **Audited Events**:
  - `AUTH_LOGIN_SUCCESS`
  - `AUTH_LOGIN_FAILED`
  - `AUTH_LOGOUT`
  - `AUTH_PASSWORD_CHANGE`
  - `AUTH_PASSWORD_RESET_ADMIN`
  - `AUTH_SESSION_REVOKED`
- **Zero-Secret Guarantee**:
  - Client IP address and User-Agent are recorded.
  - Plaintext passwords, temporary passwords, raw session tokens, and CSRF tokens are **strictly omitted** or redacted from event payloads.
