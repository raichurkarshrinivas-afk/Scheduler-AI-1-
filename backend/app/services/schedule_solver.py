import time
from typing import Dict, Any, List, Tuple, Optional
from ortools.sat.python import cp_model


class ScheduleSolverError(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


class ScheduleSolver:
    """
    Combinatorial Academic Timetable Solver utilizing Google OR-Tools CP-SAT.
    Enforces all hard institutional constraints and minimizes preference penalties.
    """
    MODEL_VERSION = "1.0.0"
    RULE_VERSION = "1.0.0"
    SOLVER_VERSION = "ortools-9.15"

    UNSUPPORTED_RULES = {
        "floating_lunch",
        "multi_campus_transit",
        "fractional_coteaching",
        "dynamic_section_partitioning",
        "multi_tenant_sharing",
    }

    @classmethod
    def feasibility_precheck(cls, snapshot: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Executes fast deterministic checks before starting the solver.
        Detects structural impossibilities and unsupported institutional rules.
        """
        rules = snapshot.get("rules", {})
        for r_code in rules:
            if r_code in cls.UNSUPPORTED_RULES:
                return (
                    False,
                    "UNSUPPORTED_RULE",
                    f"Institutional rule '{r_code}' is mathematically non-deterministic and explicitly rejected.",
                )

        sessions = snapshot.get("sessions", [])
        rooms = snapshot.get("rooms", [])
        days = snapshot.get("days", [0, 1, 2, 3, 4])
        periods_per_day = snapshot.get("periods_per_day", 8)
        total_periods_week = len(days) * periods_per_day

        max_room_cap = max((r.get("capacity", 0) for r in rooms), default=0)

        # Section hours check
        section_hours: Dict[str, int] = {}
        teacher_hours: Dict[str, int] = {}

        for s in sessions:
            dur = s.get("duration", 1)
            # Duration check
            if dur > periods_per_day:
                return (
                    False,
                    "DURATION_EXCEEDS_DAY",
                    f"Session '{s.get('id')}' duration ({dur}) exceeds periods per day ({periods_per_day}).",
                )

            # Capacity check
            min_cap = s.get("min_capacity", 0)
            if min_cap > max_room_cap:
                return (
                    False,
                    "CAPACITY_UNSATISFIABLE",
                    f"Session '{s.get('id')}' requires capacity {min_cap}, but largest room has capacity {max_room_cap}.",
                )

            # Room type / features check
            req_type = s.get("room_type_required")
            req_feats = set(s.get("required_features", []))
            matching_rooms = [
                r for r in rooms
                if (not req_type or r.get("room_type") == req_type)
                and req_feats.issubset(set(r.get("features", [])))
                and r.get("capacity", 0) >= min_cap
            ]
            if not matching_rooms:
                return (
                    False,
                    "NO_SUITABLE_ROOMS",
                    f"No room satisfies type '{req_type}' and features {list(req_feats)} with capacity >= {min_cap} for session '{s.get('id')}'.",
                )

            # Section total load
            sec = s.get("section_id")
            if sec:
                section_hours[sec] = section_hours.get(sec, 0) + dur

            # Teacher total load
            t = s.get("teacher_id")
            if t:
                teacher_hours[t] = teacher_hours.get(t, 0) + dur

        for sec, total_dur in section_hours.items():
            if total_dur > total_periods_week:
                return (
                    False,
                    "SECTION_OVERLOADED",
                    f"Section '{sec}' requires {total_dur} periods, which exceeds total periods in the week ({total_periods_week}).",
                )

        for tid, total_dur in teacher_hours.items():
            if total_dur > total_periods_week:
                return (
                    False,
                    "TEACHER_OVERLOADED",
                    f"Teacher '{tid}' requires {total_dur} periods, which exceeds total periods in the week ({total_periods_week}).",
                )

        # Locked session conflict check
        locked_by_slot: Dict[Tuple[int, int, str], str] = {}
        for s in sessions:
            locked = s.get("locked")
            if locked:
                d = locked.get("day")
                p = locked.get("period")
                dur = s.get("duration", 1)
                for offset in range(dur):
                    slot_teacher = (d, p + offset, f"teacher:{s.get('teacher_id')}")
                    if slot_teacher in locked_by_slot:
                        return (
                            False,
                            "LOCKED_CONFLICT",
                            f"Locked sessions conflict on teacher '{s.get('teacher_id')}' at day {d}, period {p + offset}.",
                        )
                    locked_by_slot[slot_teacher] = s["id"]

                    if locked.get("room_id"):
                        slot_room = (d, p + offset, f"room:{locked.get('room_id')}")
                        if slot_room in locked_by_slot:
                            return (
                                False,
                                "LOCKED_CONFLICT",
                                f"Locked sessions conflict on room '{locked.get('room_id')}' at day {d}, period {p + offset}.",
                            )
                        locked_by_slot[slot_room] = s["id"]

        return (True, None, None)

    @classmethod
    def solve(
        cls,
        snapshot: Dict[str, Any],
        time_limit_seconds: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Builds and solves the CP-SAT timetable model.
        Returns solution assignments and metadata.
        """
        # Step 1: Pre-checks
        is_feasible, err_code, err_msg = cls.feasibility_precheck(snapshot)
        if not is_feasible:
            return {
                "solver_status": "MODEL_INVALID",
                "runtime_seconds": 0.0,
                "objective_value": None,
                "best_bound": None,
                "assignments": [],
                "error_code": err_code,
                "error_message": err_msg,
                "model_version": cls.MODEL_VERSION,
                "rule_version": cls.RULE_VERSION,
                "checker_version": "1.0.0",
                "solver_version": cls.SOLVER_VERSION,
            }

        sessions = snapshot.get("sessions", [])
        rooms = snapshot.get("rooms", [])
        days = snapshot.get("days", [0, 1, 2, 3, 4])
        periods_per_day = snapshot.get("periods_per_day", 8)
        break_periods = set(snapshot.get("break_periods", []))  # e.g. [3] for lunch

        unavail_teachers = set()
        for u in snapshot.get("teacher_unavailability", []):
            unavail_teachers.add((u["teacher_id"], u["day"], u["period"]))

        unavail_rooms = set()
        for u in snapshot.get("room_unavailability", []):
            unavail_rooms.add((u["room_id"], u["day"], u["period"]))

        # Step 2: Build Candidate Assignments per session
        # candidates[s_id] = list of (day, period, room_id)
        candidates_by_session: Dict[str, List[Tuple[int, int, str]]] = {}

        for s in sessions:
            sid = s["id"]
            dur = s.get("duration", 1)
            min_cap = s.get("min_capacity", 0)
            req_type = s.get("room_type_required")
            req_feats = set(s.get("required_features", []))
            tid = s.get("teacher_id")
            locked = s.get("locked")

            cands: List[Tuple[int, int, str]] = []

            for d in days:
                for p in range(periods_per_day - dur + 1):
                    # Check break overlap
                    if any((p + offset) in break_periods for offset in range(dur)):
                        continue

                    # Check teacher availability
                    if tid and any((tid, d, p + offset) in unavail_teachers for offset in range(dur)):
                        continue

                    for r in rooms:
                        rid = r["id"]
                        # Capacity
                        if r.get("capacity", 0) < min_cap:
                            continue
                        # Room type
                        if req_type and r.get("room_type") != req_type:
                            continue
                        # Features
                        if not req_feats.issubset(set(r.get("features", []))):
                            continue
                        # Room availability
                        if any((rid, d, p + offset) in unavail_rooms for offset in range(dur)):
                            continue

                        # Locked check
                        if locked:
                            if (
                                locked.get("day") != d
                                or locked.get("period") != p
                                or (locked.get("room_id") and locked.get("room_id") != rid)
                            ):
                                continue

                        cands.append((d, p, rid))

            if not cands:
                return {
                    "solver_status": "INFEASIBLE",
                    "runtime_seconds": 0.0,
                    "objective_value": None,
                    "best_bound": None,
                    "assignments": [],
                    "error_code": "EMPTY_CANDIDATE_SET",
                    "error_message": f"Session '{s.get('name', sid)}' has zero valid candidate assignments.",
                    "model_version": cls.MODEL_VERSION,
                    "rule_version": cls.RULE_VERSION,
                    "checker_version": "1.0.0",
                    "solver_version": cls.SOLVER_VERSION,
                }

            candidates_by_session[sid] = cands

        # Step 3: Formulate CP-SAT Model
        model = cp_model.CpModel()
        x: Dict[Tuple[str, int, int, str], cp_model.IntVar] = {}

        for s in sessions:
            sid = s["id"]
            for (d, p, rid) in candidates_by_session[sid]:
                var_name = f"x_{sid[:6]}_{d}_{p}_{rid[:6]}"
                x[(sid, d, p, rid)] = model.NewBoolVar(var_name)

        # Constraint (C1): Exactly one assignment per session
        for s in sessions:
            sid = s["id"]
            cands = candidates_by_session[sid]
            model.AddExactlyOne(x[(sid, d, p, rid)] for (d, p, rid) in cands)

        # Helper mapping to build resource occupancy expressions
        # For each (d, pi): collect active session vars
        session_durations = {s["id"]: s.get("duration", 1) for s in sessions}
        session_teachers = {s["id"]: s.get("teacher_id") for s in sessions}
        session_sections = {s["id"]: s.get("section_id") for s in sessions}

        for d in days:
            for pi in range(periods_per_day):
                # Room non-overlap
                for r in rooms:
                    rid = r["id"]
                    active_room_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and r_cand == rid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_room_vars.append(var)
                    if len(active_room_vars) > 1:
                        model.Add(sum(active_room_vars) <= 1)

                # Teacher non-overlap
                teachers_in_snapshot = {s.get("teacher_id") for s in sessions if s.get("teacher_id")}
                for tid in teachers_in_snapshot:
                    active_teacher_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and session_teachers[sid] == tid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_teacher_vars.append(var)
                    if len(active_teacher_vars) > 1:
                        model.Add(sum(active_teacher_vars) <= 1)

                # Section non-overlap
                sections_in_snapshot = {s.get("section_id") for s in sessions if s.get("section_id")}
                for gid in sections_in_snapshot:
                    active_section_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and session_sections[sid] == gid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_section_vars.append(var)
                    if len(active_section_vars) > 1:
                        model.Add(sum(active_section_vars) <= 1)

        # Step 4: Objective - Minimize preference penalties
        penalties = []
        for (sid, d, p, rid), var in x.items():
            cost = 0
            # Penalty for late afternoon periods
            if p >= periods_per_day - 2:
                cost += 5
            # Friday afternoon penalty
            if d == 4 and p >= periods_per_day - 3:
                cost += 10
            if cost > 0:
                penalties.append(cost * var)

        if penalties:
            model.Minimize(sum(penalties))

        # Step 5: Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        solver.parameters.num_search_workers = 2

        start_wall_time = time.time()
        sat_status = solver.Solve(model)
        runtime = round(time.time() - start_wall_time, 3)

        if sat_status == cp_model.OPTIMAL:
            status_str = "OPTIMAL"
        elif sat_status == cp_model.FEASIBLE:
            status_str = "FEASIBLE"
        elif sat_status == cp_model.INFEASIBLE:
            status_str = "INFEASIBLE"
        elif sat_status == cp_model.UNKNOWN:
            status_str = "UNKNOWN"
        else:
            status_str = "MODEL_INVALID"

        assignments: List[Dict[str, Any]] = []
        if status_str in ("OPTIMAL", "FEASIBLE"):
            for (sid, d, p, rid), var in x.items():
                if solver.Value(var) == 1:
                    assignments.append({
                        "session_id": sid,
                        "day": d,
                        "period": p,
                        "room_id": rid,
                        "duration": session_durations[sid],
                        "teacher_id": session_teachers[sid],
                        "section_id": session_sections[sid],
                    })

        return {
            "solver_status": status_str,
            "runtime_seconds": runtime,
            "objective_value": solver.ObjectiveValue() if status_str in ("OPTIMAL", "FEASIBLE") else None,
            "best_bound": solver.BestObjectiveBound() if status_str in ("OPTIMAL", "FEASIBLE") else None,
            "assignments": assignments,
            "error_code": None if status_str in ("OPTIMAL", "FEASIBLE") else f"SOLVER_{status_str}",
            "error_message": None if status_str in ("OPTIMAL", "FEASIBLE") else f"CP-SAT solver terminated with status {status_str}.",
            "model_version": cls.MODEL_VERSION,
            "rule_version": cls.RULE_VERSION,
            "checker_version": "1.0.0",
            "solver_version": cls.SOLVER_VERSION,
        }

    @classmethod
    def repair(
        cls,
        snapshot: Dict[str, Any],
        baseline_assignments: List[Dict[str, Any]],
        time_limit_seconds: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Executes minimal-change repair on a timetable draft using CP-SAT.
        Enforces all hard institutional constraints and locked sessions,
        while minimizing disruption costs against existing baseline assignments.
        """
        is_feasible, err_code, err_msg = cls.feasibility_precheck(snapshot)
        if not is_feasible:
            return {
                "solver_status": "MODEL_INVALID",
                "runtime_seconds": 0.0,
                "assignments": baseline_assignments,
                "changes": [],
                "change_count": 0,
                "error_code": err_code,
                "error_message": err_msg,
            }

        sessions = snapshot.get("sessions", [])
        rooms = snapshot.get("rooms", [])
        days = snapshot.get("days", [0, 1, 2, 3, 4])
        periods_per_day = snapshot.get("periods_per_day", 8)
        break_periods = set(snapshot.get("break_periods", []))

        unavail_teachers = set()
        for u in snapshot.get("teacher_unavailability", []):
            unavail_teachers.add((u["teacher_id"], u["day"], u["period"]))

        unavail_rooms = set()
        for u in snapshot.get("room_unavailability", []):
            unavail_rooms.add((u["room_id"], u["day"], u["period"]))

        baseline_by_session: Dict[str, Dict[str, Any]] = {}
        for a in baseline_assignments:
            sid = a.get("session_id")
            if sid:
                baseline_by_session[sid] = a

        candidates_by_session: Dict[str, List[Tuple[int, int, str]]] = {}
        session_names = {s["id"]: s.get("name", s["id"]) for s in sessions}
        session_durations = {s["id"]: s.get("duration", 1) for s in sessions}
        session_teachers = {s["id"]: s.get("teacher_id") for s in sessions}
        session_sections = {s["id"]: s.get("section_id") for s in sessions}

        for s in sessions:
            sid = s["id"]
            dur = session_durations[sid]
            min_cap = s.get("min_capacity", 0)
            req_type = s.get("room_type_required")
            req_feats = set(s.get("required_features", []))
            tid = session_teachers.get(sid)

            locked = s.get("locked")
            b_assign = baseline_by_session.get(sid)
            if not locked and b_assign and b_assign.get("is_locked"):
                b_p = b_assign.get("period") if b_assign.get("period") is not None else b_assign.get("start_period")
                locked = {
                    "day": b_assign.get("day"),
                    "period": b_p,
                    "room_id": b_assign.get("room_id"),
                }

            cands: List[Tuple[int, int, str]] = []
            for d in days:
                for p in range(periods_per_day - dur + 1):
                    if any((p + offset) in break_periods for offset in range(dur)):
                        continue

                    if tid and any((tid, d, p + offset) in unavail_teachers for offset in range(dur)):
                        continue

                    for r in rooms:
                        rid = r["id"]
                        if r.get("capacity", 0) < min_cap:
                            continue
                        if req_type and r.get("room_type") != req_type:
                            continue
                        if not req_feats.issubset(set(r.get("features", []))):
                            continue
                        if any((rid, d, p + offset) in unavail_rooms for offset in range(dur)):
                            continue

                        if locked:
                            if (
                                locked.get("day") != d
                                or locked.get("period") != p
                                or (locked.get("room_id") and locked.get("room_id") != rid)
                            ):
                                continue

                        cands.append((d, p, rid))

            if not cands:
                return {
                    "solver_status": "INFEASIBLE",
                    "runtime_seconds": 0.0,
                    "assignments": baseline_assignments,
                    "changes": [],
                    "change_count": 0,
                    "error_code": "EMPTY_CANDIDATE_SET",
                    "error_message": f"Session '{session_names.get(sid, sid)}' has zero valid candidate assignments.",
                }

            candidates_by_session[sid] = cands

        model = cp_model.CpModel()
        x: Dict[Tuple[str, int, int, str], cp_model.IntVar] = {}

        for s in sessions:
            sid = s["id"]
            for (d, p, rid) in candidates_by_session[sid]:
                var_name = f"rep_{sid[:6]}_{d}_{p}_{rid[:6]}"
                x[(sid, d, p, rid)] = model.NewBoolVar(var_name)

        for s in sessions:
            sid = s["id"]
            cands = candidates_by_session[sid]
            model.AddExactlyOne(x[(sid, d, p, rid)] for (d, p, rid) in cands)

        for d in days:
            for pi in range(periods_per_day):
                for r in rooms:
                    rid = r["id"]
                    active_room_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and r_cand == rid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_room_vars.append(var)
                    if len(active_room_vars) > 1:
                        model.Add(sum(active_room_vars) <= 1)

                teachers_in_snapshot = {s.get("teacher_id") for s in sessions if s.get("teacher_id")}
                for tid in teachers_in_snapshot:
                    active_teacher_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and session_teachers[sid] == tid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_teacher_vars.append(var)
                    if len(active_teacher_vars) > 1:
                        model.Add(sum(active_teacher_vars) <= 1)

                sections_in_snapshot = {s.get("section_id") for s in sessions if s.get("section_id")}
                for gid in sections_in_snapshot:
                    active_section_vars = []
                    for (sid, d_cand, p_cand, r_cand), var in x.items():
                        if d_cand == d and session_sections[sid] == gid:
                            dur = session_durations[sid]
                            if p_cand <= pi < p_cand + dur:
                                active_section_vars.append(var)
                    if len(active_section_vars) > 1:
                        model.Add(sum(active_section_vars) <= 1)

        disruption_penalties = []
        for (sid, d, p, rid), var in x.items():
            b = baseline_by_session.get(sid)
            if b:
                b_d = b.get("day")
                b_p = b.get("period") if b.get("period") is not None else b.get("start_period")
                b_r = b.get("room_id")
                d_cost = 0
                time_changed = (d != b_d or p != b_p)
                room_changed = (rid != b_r)
                if time_changed and room_changed:
                    d_cost = 25
                elif time_changed:
                    d_cost = 20
                elif room_changed:
                    d_cost = 5
                else:
                    d_cost = 0
            else:
                d_cost = 15

            cost = d_cost * 100
            if p >= periods_per_day - 2:
                cost += 1
            if cost > 0:
                disruption_penalties.append(cost * var)

        if disruption_penalties:
            model.Minimize(sum(disruption_penalties))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        solver.parameters.num_search_workers = 2

        start_wall_time = time.time()
        sat_status = solver.Solve(model)
        runtime = round(time.time() - start_wall_time, 3)

        if sat_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status_str = "OPTIMAL" if sat_status == cp_model.OPTIMAL else "FEASIBLE"
            repaired_assignments = []
            changes = []

            for (sid, d, p, rid), var in x.items():
                if solver.Value(var) == 1:
                    b = baseline_by_session.get(sid)
                    is_locked = bool(b.get("is_locked")) if b else False
                    new_assign = {
                        "session_id": sid,
                        "day": d,
                        "period": p,
                        "room_id": rid,
                        "duration": session_durations[sid],
                        "teacher_id": session_teachers[sid],
                        "section_id": session_sections[sid],
                        "is_locked": is_locked,
                    }
                    repaired_assignments.append(new_assign)

                    if b:
                        b_d = b.get("day")
                        b_p = b.get("period") if b.get("period") is not None else b.get("start_period")
                        b_r = b.get("room_id")
                        time_moved = (d != b_d or p != b_p)
                        room_changed = (rid != b_r)
                        if time_moved or room_changed:
                            changes.append({
                                "session_id": sid,
                                "session_name": session_names.get(sid, sid),
                                "teacher_id": session_teachers.get(sid),
                                "section_id": session_sections.get(sid),
                                "before": {"day": b_d, "period": b_p, "room_id": b_r},
                                "after": {"day": d, "period": p, "room_id": rid},
                                "time_moved": time_moved,
                                "room_changed": room_changed,
                                "reason": "Resolved overlap/conflict with minimal disruption",
                            })
                    else:
                        changes.append({
                            "session_id": sid,
                            "session_name": session_names.get(sid, sid),
                            "teacher_id": session_teachers.get(sid),
                            "section_id": session_sections.get(sid),
                            "before": {},
                            "after": {"day": d, "period": p, "room_id": rid},
                            "time_moved": True,
                            "room_changed": True,
                            "reason": "Assigned previously unallocated session",
                        })

            return {
                "solver_status": status_str,
                "runtime_seconds": runtime,
                "assignments": repaired_assignments,
                "changes": changes,
                "change_count": len(changes),
                "error_code": None,
                "error_message": None,
            }
        else:
            status_str = "INFEASIBLE" if sat_status == cp_model.INFEASIBLE else "UNKNOWN"
            return {
                "solver_status": status_str,
                "runtime_seconds": runtime,
                "assignments": baseline_assignments,
                "changes": [],
                "change_count": 0,
                "error_code": f"SOLVER_{status_str}",
                "error_message": f"CP-SAT solver could not repair schedule; status: {status_str}.",
            }
