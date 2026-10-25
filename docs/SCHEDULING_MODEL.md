# Scheduler Timetabling Constraint Model Specification (Phase 7)

## 1. Overview & Problem Definition

The Scheduler Timetabling Engine solves the multi-dimensional, constrained academic timetable assignment problem for educational institutions. The goal is to assign every required academic session (lectures, tutorials, practicals) to a valid day, start time period, and physical facility while strictly satisfying all institutional hard constraints (teacher, room, and student cohort overlaps, availability, room suitability, capacity, and locked commitments) and minimizing preference penalties.

Solving is executed asynchronously via **Google OR-Tools CP-SAT (Constraint Programming — Satisfiability)** in a dedicated background worker, completely decoupled from synchronous HTTP API request cycles.

---

## 2. Mathematical CP-SAT Formulation

### 2.1 Index Sets & Dimensions

| Set | Symbol | Description |
| :--- | :---: | :--- |
| **Sessions** | $S$ | Set of required academic course sessions to schedule. |
| **Teachers** | $T$ | Set of faculty instructors. Each session $s \in S$ has primary teacher $teacher(s) \in T$. |
| **Rooms** | $R$ | Set of physical classrooms, lecture halls, and laboratories. |
| **Sections** | $G$ | Set of student cohorts/sections. Each session $s \in S$ belongs to section $section(s) \in G$. |
| **Days** | $D$ | Scheduling days in the academic week, typically $\{0, 1, 2, 3, 4\}$ (Mon-Fri). |
| **Time Periods** | $P$ | Discrete time periods per day, $\{0, 1, \dots, |P|-1\}$ (e.g., 0=09:00, 1=10:00, etc.). |

### 2.2 Parameters & Domain Attributes

- $d_s \in \mathbb{N}^+$: Duration of session $s$ in consecutive time periods (e.g., $d_s = 1$ for standard lecture, $d_s = 2$ or $3$ for practical laboratory blocks).
- $cap_s \in \mathbb{N}^+$: Minimum student capacity required for session $s$ (determined by cohort student count).
- $type_s \in \{	ext{THEORY}, 	ext{PRACTICAL}\}$: Room classification required by session $s$.
- $feat_s \subseteq 	ext{Features}$: Set of required workstation or room hardware features (e.g., `{"Linux", "GPU"}`).
- $cap(r) \in \mathbb{N}^+$: Usable student capacity of room $r \in R$.
- $type(r) \in \{	ext{THEORY}, 	ext{PRACTICAL}\}$: Classification of room $r \in R$.
- $feat(r) \subseteq 	ext{Features}$: Hardware/software capabilities installed in room $r \in R$.
- $Locked(s) = (d^*, p^*, r^*)$: Optional locked pre-assignment fixing session $s$ to day $d^*$, period $p^*$, and room $r^*$.
- $Avail_T(t, d, p) \in \{0, 1\}$: Teacher availability parameter ($0 = 	ext{unavailable}$, $1 = 	ext{available}$).
- $Avail_R(r, d, p) \in \{0, 1\}$: Room availability parameter ($0 = 	ext{blackout/maintenance}$, $1 = 	ext{available}$).
- $Break(d, p) \in \{0, 1\}$: Institutional break/lunch window ($1 = 	ext{break interval}$).

### 2.3 Decision Variables

For each session $s \in S$ and each candidate assignment $(d, p, r) \in CandidateAssignments(s)$:
$$x_{s, d, p, r} \in \{0, 1\}$$
where $x_{s, d, p, r} = 1$ if session $s$ starts on day $d$ at period $p$ in room $r$, and $0$ otherwise.

A period $p$ is a valid start period for session $s$ only if:
$$p + d_s \le |P|$$
ensuring that multi-period sessions do not wrap around past the end of the instructional day.

### 2.4 Hard Constraints

#### (C1) Exactly One Assignment per Required Session
Every required academic session must be scheduled exactly once:
$$orall s \in S: \quad \sum_{(d, p, r) \in CandidateAssignments(s)} x_{s, d, p, r} = 1$$

#### (C2) Full-Duration Occupancy & Non-Wrapping
A session $s$ scheduled at $(d, p, r)$ with duration $d_s$ occupies periods:
$$Occ(s, d, p) = \{ (d, p + 	au) \mid 0 \le 	au < d_s \}$$
Every occupied period $(d, p + 	au)$ must be within valid daytime bounds and must not overlap institutional break windows if breaks are strictly enforced.

#### (C3) Teacher Conflict-Free (No Double-Booking)
An instructor cannot teach more than one session concurrently at any given day and period:
$$orall t \in T, orall d \in D, orall \pi \in P: \quad \sum_{s \in S : teacher(s) = t} \sum_{r \in R} \sum_{p : p \le \pi < p + d_s} x_{s, d, p, r} \le 1$$

#### (C4) Room Conflict-Free (No Physical Room Double-Booking)
A physical room cannot host more than one session simultaneously:
$$orall r \in R, orall d \in D, orall \pi \in P: \quad \sum_{s \in S} \sum_{p : p \le \pi < p + d_s} x_{s, d, p, r} \le 1$$

#### (C5) Student Cohort Conflict-Free (No Section Double-Booking)
A student section cannot be scheduled for two concurrent sessions:
$$orall g \in G, orall d \in D, orall \pi \in P: \quad \sum_{s \in S : section(s) = g} \sum_{r \in R} \sum_{p : p \le \pi < p + d_s} x_{s, d, p, r} \le 1$$

#### (C6) Teacher & Facility Availability Constraints
Sessions cannot be assigned during unavailable teacher hours or room maintenance windows:
$$	ext{If } Avail_T(teacher(s), d, p + 	au) = 0 	ext{ for any } 0 \le 	au < d_s \implies x_{s, d, p, r} = 0$$
$$	ext{If } Avail_R(r, d, p + 	au) = 0 	ext{ for any } 0 \le 	au < d_s \implies x_{s, d, p, r} = 0$$

#### (C7) Room Suitability & Capacity Pre-Filtering
Candidate assignments prune non-compliant rooms during model variable generation:
$$(d, p, r) \in CandidateAssignments(s) \implies cap(r) \ge cap_s \quad \land \quad type(r) == type_s \quad \land \quad feat_s \subseteq feat(r)$$

#### (C8) Consecutive Multi-Period Practical Blocks
Practical laboratories requiring $d_s > 1$ periods are modeled as contiguous interval variables or consecutive period blocks in the same room without mid-session relocation.

#### (C9) Locked Session Commitments
Pre-assigned or coordinator-locked sessions fix the decision variable:
$$	ext{If } Locked(s) = (d^*, p^*, r^*) \implies x_{s, d^*, p^*, r^*} = 1 \quad 	ext{and all other candidate variables for } s 	ext{ are 0.}$$

#### (C10) Configurable Institutional Breaks
If strict breaks are enabled:
$$orall s \in S, orall (d, p, r) \in CandidateAssignments(s): \quad \left( \exists 	au \in [0, d_s - 1] 	ext{ s.t. } Break(d, p + 	au) = 1 
ight) \implies x_{s, d, p, r} = 0$$

### 2.5 Soft Constraints & Objective Optimization

The objective function minimizes total penalty points:
$$\min \sum_{s \in S} \sum_{(d, p, r)} 	ext{Penalty}(s, d, p, r) \cdot x_{s, d, p, r}$$
where $	ext{Penalty}(s, d, p, r)$ is the sum of weighted soft preference violations:
- **Late Afternoon Penalty**: Penalty for assigning sessions in the final period of the day.
- **Preferred Slot Penalty**: Penalty for deviating from faculty-requested preferred time slots.
- **Room Change Penalty**: Penalty for splitting consecutive cohorts across distant rooms.

---

## 3. Supported vs. Unsupported Institutional Cases

### 3.1 Supported Institutional Cases
1. **Recurring Weekly Curricula**: Weekly class schedules spanning fixed days and uniform periods.
2. **Single & Multi-Period Durations**: Standard 1-period lectures and 2-to-3 period contiguous practical blocks.
3. **Dedicated Physical Rooms**: Exact match on room type (`THEORY` vs `PRACTICAL`) and hardware workstation features (GPU, Linux, specialized software).
4. **Capacity Enforcement**: Strict verification that classroom capacity meets or exceeds cohort student size.
5. **Teacher & Room Unavailability**: Full support for recurring faculty leaves, research days, and room maintenance windows.
6. **Pre-Assigned Locked Commitments**: Fixed academic sessions that the solver must treat as immutable anchor points.
7. **Configurable Campus Breaks**: Dedicated daily lunch and institutional assembly blackout windows.
8. **Soft Preference Tuning**: Configurable penalty weights for non-standard hours.

### 3.2 Unsupported Institutional Cases (Explicitly Rejected)
To maintain deterministic mathematical guarantees and avoid unpredictable solver behavior, the following cases are explicitly rejected with structured error code `UNSUPPORTED_RULE`:
1. **Dynamic Floating Lunch Breaks**: Floating breaks where individual students take lunch at variable, uncoordinated hours within the same section.
2. **Multi-Campus Travel Transit Windows**: Scheduling sessions across geographically separated campuses requiring variable driving/transit travel time within the same hour.
3. **Fractional Split-Teacher Co-Teaching**: Splitting a single 1-hour session into fractional percentage shares across multiple co-teachers.
4. **Dynamic Section Partitioning**: Dynamically dividing a cohort into arbitrary sub-groups during solver execution without pre-defined section entities.
5. **Multi-Tenant Resource Sharing**: Sharing instructors or classrooms across different institution tenants.

---

## 4. Solver Output Protocol

The solver reports one of five strictly defined statuses:
1. `OPTIMAL`: Feasible schedule found and proven mathematically minimal with respect to the objective function.
2. `FEASIBLE`: Valid schedule found satisfying 100% of hard constraints; optimality bound not yet closed within the time limit.
3. `INFEASIBLE`: Mathematically proven that no schedule exists satisfying all hard constraints.
4. `UNKNOWN`: The solver search reached the configured time limit without finding a feasible solution or proving infeasibility. **Rule: Never label UNKNOWN as proven infeasibility.**
5. `MODEL_INVALID`: Pre-check failed or input configuration violated structural invariants before solver invocation.

---

## 5. Independent Verification Checker Architecture

Per design guidelines, verification **must not call the model construction code**. The checker (`app.services.schedule_checker`) is an independent component that consumes plain assignment JSON and validates:
1. **Completeness**: Every required session in the input snapshot is assigned.
2. **Uniqueness**: No duplicate session assignments or extraneous session IDs.
3. **Duration Integrity**: Every assignment spans its exact required continuous periods.
4. **Teacher Overlaps**: Zero concurrent overlaps for any instructor.
5. **Room Overlaps**: Zero concurrent overlaps for any physical room.
6. **Cohort Overlaps**: Zero concurrent overlaps for any student section.
7. **Availability Compliance**: No session scheduled during teacher or room blackout periods.
8. **Capacity & Suitability**: All assigned rooms satisfy capacity, classification, and hardware feature requirements.
9. **Locked Commitments**: All locked sessions match their designated day, period, and room coordinates.

A draft timetable is promoted to `CHECKED` **only if the independent checker returns zero violations**.

---

## 6. Provenance & Version Tracking

Every draft snapshot and generated solution stores:
- `input_hash`: Cryptographic SHA-256 digest of the input snapshot JSON.
- `model_version`: "1.0.0"
- `rule_version`: "1.0.0"
- `checker_version`: "1.0.0"
- `solver_version`: "ortools-9.15"
- `solver_runtime_seconds`: Exact wall-clock solve time.
- `solver_objective`: Objective value (if solved).
- `solver_best_bound`: Mathematical lower bound (if solved).

---

## 7. Minimal-Change Repair & Editing Policies (Phase 8 Implemented)

### 7.1 Temporarily Invalid Draft Policy
- **Decision**: Temporarily invalid timetable drafts are **explicitly supported**.
- **Rationale**: Academic schedulers regularly execute multi-step swaps (e.g. moving Session A to Slot X before moving conflicting Session B out of Slot X). Forcing instantaneous validity at every intermediate edit would obstruct practical human scheduling workflows.
- **Safeguards**:
  - Edits that create clashes or exceed resource capacities transition the draft status to `INVALID`.
  - The independent checker records all active collisions in `validation_report`.
  - The UI displays a persistent coral conflict alert bar, highlights invalid cells, and shows an `INVALID` status badge.
  - **Publication is strictly blocked**: Any request to publish an `INVALID` draft is rejected with `HTTP 400 Bad Request` until all conflicts are resolved or repaired.

### 7.2 Minimal-Change Repair Formulation & Disruption Costs
When invoking `POST /api/v1/timetable-drafts/{id}/repair`, CP-SAT formulates a repair optimization model that strictly enforces all hard institutional constraints while minimizing schedule disruption:
- **Locked Commitment Preservation**: Locked sessions are pinned to their exact designated coordinates and cannot be moved by the solver.
- **Disruption Cost Function**:
  $$\text{DisruptionCost}(s) = \begin{cases} 0 & \text{if } (d, p) == (d_0, p_0) \land r == r_0 \\ 20 & \text{if } (d, p) \ne (d_0, p_0) \land r == r_0 \text{ (Time moved)} \\ 5 & \text{if } (d, p) == (d_0, p_0) \land r \ne r_0 \text{ (Room changed)} \\ 25 & \text{if } (d, p) \ne (d_0, p_0) \land r \ne r_0 \text{ (Both moved)} \\ 15 & \text{if } s \text{ was unassigned} \end{cases}$$
- **Objective Dominance**: Disruption costs are scaled by 100 in the CP-SAT objective so that preserving existing assignments strictly dominates soft preference penalties.
- **Before/After Audit**: Every adjusted session is recorded with before/after coordinates, moved flags, and justification.
