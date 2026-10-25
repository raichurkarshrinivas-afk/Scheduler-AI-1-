from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Tuple, Set, Optional


class PracticalExamEngine:
    """
    Practical examination engine.
    Allocates candidates to compatible laboratory workstations across sittings/batches,
    enforcing start times, durations, turnaround buffers, and examiner non-overlap constraints.
    """
    ENGINE_VERSION = "1.0.0"

    @classmethod
    def _parse_time(cls, t_str: str) -> int:
        """Parses 'HH:MM' or ISO string to minutes from midnight."""
        if ":" in t_str and len(t_str.split(":")) >= 2:
            parts = t_str.split(":")
            h = int(parts[0])
            m = int(parts[1][:2])
            return h * 60 + m
        return 0

    @classmethod
    def verify_practical_allocation(
        cls,
        snapshot: Dict[str, Any],
        allocations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Independent verification checker for practical examination allocations.
        Checks workstation feature compatibility, staff overlap (including buffers),
        lab overlap, and student overlaps.
        """
        violations: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        sittings = snapshot.get("sittings", [])
        candidates = snapshot.get("candidates", [])
        labs = snapshot.get("labs", [])

        candidate_map = {c["id"]: c for c in candidates}
        sitting_map = {s["batch_id"]: s for s in sittings}

        # Build workstation map: (lab_id, workstation_id) -> workstation
        workstations_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for lab in labs:
            lid = lab["id"]
            for ws in lab.get("workstations", []):
                workstations_map[(lid, ws["id"])] = ws

        # 1. Staff and Lab Overlaps Across Sittings (including turnaround buffers)
        for i in range(len(sittings)):
            for j in range(i + 1, len(sittings)):
                s1 = sittings[i]
                s2 = sittings[j]

                # Check day match (or date)
                if s1.get("day", 0) != s2.get("day", 0):
                    continue

                start1 = cls._parse_time(s1.get("start_time", "09:00"))
                dur1 = s1.get("duration_minutes", 120)
                buf1 = s1.get("buffer_minutes", 15)
                end1_eff = start1 + dur1 + buf1

                start2 = cls._parse_time(s2.get("start_time", "09:00"))
                dur2 = s2.get("duration_minutes", 120)
                buf2 = s2.get("buffer_minutes", 15)
                end2_eff = start2 + dur2 + buf2

                # Overlap test: max(start1, start2) < min(end1_eff, end2_eff)
                is_overlap = max(start1, start2) < min(end1_eff, end2_eff)

                if is_overlap:
                    # Check Lab overlap
                    if s1.get("lab_id") and s1.get("lab_id") == s2.get("lab_id"):
                        violations.append({
                            "rule": "LAB_OVERLAP",
                            "sittings": [s1["batch_id"], s2["batch_id"]],
                            "lab_id": s1["lab_id"],
                            "message": f"Lab '{s1['lab_id']}' is scheduled for concurrent batches '{s1['batch_id']}' and '{s2['batch_id']}' including turnaround buffers.",
                        })

                    # Check Examiner overlap
                    ex1 = s1.get("chief_examiner_id")
                    ex2 = s2.get("chief_examiner_id")
                    if ex1 and ex2 and ex1 == ex2:
                        violations.append({
                            "rule": "EXAMINER_CLASH",
                            "examiner_id": ex1,
                            "sittings": [s1["batch_id"], s2["batch_id"]],
                            "message": f"Chief Examiner '{ex1}' is scheduled for concurrent practical batches '{s1['batch_id']}' and '{s2['batch_id']}'.",
                        })

                    # Check Assistant overlaps
                    assts1 = set(s1.get("assistant_ids", []))
                    assts2 = set(s2.get("assistant_ids", []))
                    common_assts = assts1.intersection(assts2)
                    for a_id in common_assts:
                        violations.append({
                            "rule": "ASSISTANT_CLASH",
                            "assistant_id": a_id,
                            "sittings": [s1["batch_id"], s2["batch_id"]],
                            "message": f"Lab assistant '{a_id}' is double-booked across concurrent batches '{s1['batch_id']}' and '{s2['batch_id']}'.",
                        })

        # 2. Candidate Allocation Verifications
        used_stations_per_batch: Dict[Tuple[str, str], str] = {}
        assigned_cands_set = set()

        for a in allocations:
            cid = a.get("candidate_id")
            bid = a.get("batch_id")
            lid = a.get("lab_id")
            wsid = a.get("workstation_id")

            # Duplicate candidate assignment
            if cid in assigned_cands_set:
                violations.append({
                    "rule": "DUPLICATE_CANDIDATE",
                    "candidate_id": cid,
                    "message": f"Candidate '{cid}' is allocated to multiple practical workstations.",
                })
            assigned_cands_set.add(cid)

            # Duplicate workstation in same batch
            ws_key = (bid, wsid)
            if ws_key in used_stations_per_batch:
                violations.append({
                    "rule": "DUPLICATE_STATION",
                    "batch_id": bid,
                    "workstation_id": wsid,
                    "message": f"Workstation '{wsid}' is assigned to multiple candidates in batch '{bid}'.",
                })
            used_stations_per_batch[ws_key] = cid

            # Workstation compatibility
            cand = candidate_map.get(cid)
            ws = workstations_map.get((lid, wsid))

            if not ws:
                violations.append({
                    "rule": "UNKNOWN_WORKSTATION",
                    "lab_id": lid,
                    "workstation_id": wsid,
                    "message": f"Workstation '{wsid}' does not exist in lab '{lid}'.",
                })
                continue

            if not ws.get("is_active", True):
                violations.append({
                    "rule": "INACTIVE_WORKSTATION",
                    "workstation_id": wsid,
                    "message": f"Workstation '{wsid}' is marked inactive / broken.",
                })

            if cand:
                req_feats = set(cand.get("required_features", []))
                ws_feats = set(ws.get("features", []))
                if not req_feats.issubset(ws_feats):
                    missing = list(req_feats - ws_feats)
                    violations.append({
                        "rule": "WORKSTATION_INCOMPATIBLE",
                        "candidate_id": cid,
                        "workstation_id": wsid,
                        "missing_features": missing,
                        "message": f"Candidate '{cand.get('roll_number', cid)}' requires features {missing} not equipped on workstation '{ws.get('label', wsid)}'.",
                    })

                req_os = cand.get("required_os")
                if req_os and ws.get("operating_system") and req_os != ws.get("operating_system"):
                    violations.append({
                        "rule": "OS_INCOMPATIBLE",
                        "candidate_id": cid,
                        "workstation_id": wsid,
                        "message": f"Candidate '{cid}' requires OS '{req_os}', but workstation has '{ws.get('operating_system')}'.",
                    })

        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "allocated_count": len(allocations),
            "total_candidates": len(candidates),
            "checker_version": cls.ENGINE_VERSION,
        }

    @classmethod
    def allocate(
        cls,
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Allocates candidates in practical sittings to compatible laboratory workstations.
        Validates effective capacity and compatibility.
        """
        sittings = snapshot.get("sittings", [])
        candidates = snapshot.get("candidates", [])
        labs = snapshot.get("labs", [])

        labs_map = {l["id"]: l for l in labs}
        cands_by_batch: Dict[str, List[Dict[str, Any]]] = {}
        for c in candidates:
            bid = c.get("batch_id", "batch-1")
            cands_by_batch.setdefault(bid, []).append(c)

        allocations: List[Dict[str, Any]] = []

        # Allocate batch by batch
        for sitting in sittings:
            bid = sitting["batch_id"]
            lid = sitting["lab_id"]
            lab = labs_map.get(lid)
            if not lab:
                return {
                    "status": "INVALID_INPUT",
                    "allocations": [],
                    "error_code": "LAB_NOT_FOUND",
                    "error_message": f"Lab '{lid}' not found in snapshot.",
                    "validation_report": {"is_valid": False, "violations": [{"rule": "LAB_NOT_FOUND", "message": f"Lab '{lid}' not found."}], "warnings": []},
                }

            batch_cands = cands_by_batch.get(bid, [])
            active_stations = [
                ws for ws in lab.get("workstations", [])
                if ws.get("is_active", True)
            ]

            # Effective capacity check
            if len(batch_cands) > len(active_stations):
                shortfall = len(batch_cands) - len(active_stations)
                return {
                    "status": "INSUFFICIENT_LAB_CAPACITY",
                    "allocations": [],
                    "error_code": "INSUFFICIENT_LAB_CAPACITY",
                    "error_message": f"Batch '{bid}' requires {len(batch_cands)} workstations, but lab '{lab.get('name', lid)}' only has {len(active_stations)} active terminals (shortfall: {shortfall}).",
                    "validation_report": {
                        "is_valid": False,
                        "violations": [{
                            "rule": "INSUFFICIENT_LAB_CAPACITY",
                            "message": f"Capacity shortfall of {shortfall} workstations in batch '{bid}'.",
                        }],
                        "warnings": [],
                    },
                }

            # Match candidates to compatible stations
            used_stations = set()
            for cand in batch_cands:
                req_feats = set(cand.get("required_features", []))
                req_os = cand.get("required_os")

                # Find first eligible station
                matched_ws = None
                for ws in active_stations:
                    if ws["id"] in used_stations:
                        continue
                    if not req_feats.issubset(set(ws.get("features", []))):
                        continue
                    if req_os and ws.get("operating_system") and ws.get("operating_system") != req_os:
                        continue
                    matched_ws = ws
                    break

                if not matched_ws:
                    return {
                        "status": "WORKSTATION_INCOMPATIBLE",
                        "allocations": [],
                        "error_code": "WORKSTATION_INCOMPATIBLE",
                        "error_message": f"No compatible workstation equipped with {list(req_feats)} available for candidate '{cand.get('roll_number', cand['id'])}' in batch '{bid}'.",
                        "validation_report": {
                            "is_valid": False,
                            "violations": [{
                                "rule": "WORKSTATION_INCOMPATIBLE",
                                "candidate_id": cand["id"],
                                "message": f"Incompatible hardware requirements for candidate '{cand['id']}'.",
                            }],
                            "warnings": [],
                        },
                    }

                used_stations.add(matched_ws["id"])
                allocations.append({
                    "batch_id": bid,
                    "candidate_id": cand["id"],
                    "roll_number": cand.get("roll_number", cand["id"]),
                    "candidate_name": cand.get("name", ""),
                    "lab_id": lid,
                    "workstation_id": matched_ws["id"],
                    "workstation_label": matched_ws.get("label", matched_ws["id"]),
                    "workstation_number": matched_ws.get("workstation_number", 0),
                })

        report = cls.verify_practical_allocation(snapshot, allocations)
        return {
            "status": "ALLOCATED" if report["is_valid"] else "INVALID",
            "allocations": allocations,
            "error_code": None if report["is_valid"] else "ALLOCATION_CONFLICT",
            "error_message": None if report["is_valid"] else "Practical allocations contain scheduling or overlap conflicts.",
            "validation_report": report,
        }
