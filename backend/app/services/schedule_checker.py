from typing import Dict, Any, List, Tuple, Set


class ScheduleChecker:
    """
    Independent schedule verification checker.
    Validates plain JSON output assignments against input snapshot specifications.
    Strictly decoupled from model construction or solver code.
    """
    VERSION = "1.0.0"

    @classmethod
    def validate(
        cls,
        input_snapshot: Dict[str, Any],
        output_assignments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        violations: List[Dict[str, Any]] = []

        required_sessions: Dict[str, Dict[str, Any]] = {
            s["id"]: s for s in input_snapshot.get("sessions", [])
        }
        rooms_by_id: Dict[str, Dict[str, Any]] = {
            r["id"]: r for r in input_snapshot.get("rooms", [])
        }
        teachers_by_id: Dict[str, Dict[str, Any]] = {
            t["id"]: t for t in input_snapshot.get("teachers", [])
        }

        # 1. Completeness & Unexpected Sessions
        assigned_session_ids = [a.get("session_id") for a in output_assignments]
        assigned_id_set = set(assigned_session_ids)

        # Check for missing required sessions
        for req_id, req_session in required_sessions.items():
            if req_id not in assigned_id_set:
                violations.append({
                    "rule": "COMPLETENESS",
                    "session_id": req_id,
                    "message": f"Required session '{req_session.get('name', req_id)}' was not assigned.",
                })

        # Check for unexpected or duplicate sessions
        seen_sessions: Set[str] = set()
        for a in output_assignments:
            sid = a.get("session_id")
            if sid not in required_sessions:
                violations.append({
                    "rule": "UNEXPECTED_SESSION",
                    "session_id": sid,
                    "message": f"Assignment contains unknown session ID '{sid}'.",
                })
            elif sid in seen_sessions:
                violations.append({
                    "rule": "DUPLICATE_SESSION",
                    "session_id": sid,
                    "message": f"Session '{sid}' is scheduled more than once.",
                })
            seen_sessions.add(sid)

        # 2. Duration, Overlap, Availability & Capacity Checks
        # Occupancy maps: (day, period, resource_id) -> list of session_ids
        teacher_occupancy: Dict[Tuple[int, int, str], List[str]] = {}
        room_occupancy: Dict[Tuple[int, int, str], List[str]] = {}
        section_occupancy: Dict[Tuple[int, int, str], List[str]] = {}

        unavail_teachers = set()
        for u in input_snapshot.get("teacher_unavailability", []):
            unavail_teachers.add((u["teacher_id"], u["day"], u["period"]))

        unavail_rooms = set()
        for u in input_snapshot.get("room_unavailability", []):
            unavail_rooms.add((u["room_id"], u["day"], u["period"]))

        for a in output_assignments:
            sid = a.get("session_id")
            req = required_sessions.get(sid)
            if not req:
                continue

            day = a.get("day")
            period = a.get("period")
            room_id = a.get("room_id")
            teacher_id = req.get("teacher_id")
            section_id = req.get("section_id")
            expected_duration = req.get("duration", 1)
            actual_duration = a.get("duration", expected_duration)

            # Check 3: Duration check
            if actual_duration != expected_duration:
                violations.append({
                    "rule": "DURATION_MISMATCH",
                    "session_id": sid,
                    "message": f"Session '{sid}' duration is {actual_duration}, expected {expected_duration}.",
                })

            # Check 4: Capacity & Suitability
            room = rooms_by_id.get(room_id)
            if not room:
                violations.append({
                    "rule": "UNKNOWN_ROOM",
                    "session_id": sid,
                    "message": f"Assigned room '{room_id}' does not exist in institution.",
                })
            else:
                # Capacity
                min_cap = req.get("min_capacity", 0)
                room_cap = room.get("capacity", 0)
                if room_cap < min_cap:
                    violations.append({
                        "rule": "CAPACITY_VIOLATION",
                        "session_id": sid,
                        "message": f"Room '{room.get('name', room_id)}' capacity ({room_cap}) < required student capacity ({min_cap}).",
                    })

                # Room type
                req_type = req.get("room_type_required")
                if req_type and room.get("room_type") != req_type:
                    violations.append({
                        "rule": "ROOM_TYPE_MISMATCH",
                        "session_id": sid,
                        "message": f"Room '{room.get('name', room_id)}' is type '{room.get('room_type')}', expected '{req_type}'.",
                    })

                # Features
                req_feats = set(req.get("required_features", []))
                room_feats = set(room.get("features", []))
                if not req_feats.issubset(room_feats):
                    missing = req_feats - room_feats
                    violations.append({
                        "rule": "MISSING_ROOM_FEATURES",
                        "session_id": sid,
                        "message": f"Room '{room.get('name', room_id)}' lacks required features: {list(missing)}.",
                    })

            # Check 5: Locked session commitments
            locked = req.get("locked")
            if locked:
                if (
                    locked.get("day") != day
                    or locked.get("period") != period
                    or (locked.get("room_id") and locked.get("room_id") != room_id)
                ):
                    violations.append({
                        "rule": "LOCKED_COMMITMENT_VIOLATION",
                        "session_id": sid,
                        "message": f"Session '{sid}' is locked to day {locked.get('day')}, period {locked.get('period')}, but assigned to day {day}, period {period}.",
                    })

            # Check 6: Resource Overlaps across all occupied periods
            for offset in range(expected_duration):
                p = period + offset

                # Teacher availability
                if teacher_id and (teacher_id, day, p) in unavail_teachers:
                    violations.append({
                        "rule": "TEACHER_UNAVAILABLE",
                        "session_id": sid,
                        "message": f"Teacher '{teacher_id}' is marked unavailable on day {day}, period {p}.",
                    })

                # Room availability
                if room_id and (room_id, day, p) in unavail_rooms:
                    violations.append({
                        "rule": "ROOM_UNAVAILABLE",
                        "session_id": sid,
                        "message": f"Room '{room_id}' is marked unavailable on day {day}, period {p}.",
                    })

                # Teacher occupancy
                if teacher_id:
                    t_key = (day, p, teacher_id)
                    teacher_occupancy.setdefault(t_key, []).append(sid)

                # Room occupancy
                if room_id:
                    r_key = (day, p, room_id)
                    room_occupancy.setdefault(r_key, []).append(sid)

                # Section occupancy
                if section_id:
                    s_key = (day, p, section_id)
                    section_occupancy.setdefault(s_key, []).append(sid)

        # Evaluate overlaps
        for (day, p, tid), sids in teacher_occupancy.items():
            if len(sids) > 1:
                violations.append({
                    "rule": "TEACHER_OVERLAP",
                    "session_id": sids[0],
                    "message": f"Teacher '{tid}' double-booked on day {day}, period {p} across sessions: {sids}.",
                })

        for (day, p, rid), sids in room_occupancy.items():
            if len(sids) > 1:
                violations.append({
                    "rule": "ROOM_OVERLAP",
                    "session_id": sids[0],
                    "message": f"Room '{rid}' double-booked on day {day}, period {p} across sessions: {sids}.",
                })

        for (day, p, gid), sids in section_occupancy.items():
            if len(sids) > 1:
                violations.append({
                    "rule": "SECTION_OVERLAP",
                    "session_id": sids[0],
                    "message": f"Student section '{gid}' double-booked on day {day}, period {p} across sessions: {sids}.",
                })

        is_valid = len(violations) == 0
        return {
            "is_valid": is_valid,
            "total_required": len(required_sessions),
            "total_assigned": len(output_assignments),
            "violations_count": len(violations),
            "violations": violations,
            "checker_version": cls.VERSION,
        }
