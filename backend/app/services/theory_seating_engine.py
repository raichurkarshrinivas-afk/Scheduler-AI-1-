import time
from typing import Dict, Any, List, Tuple, Set, Optional
from ortools.sat.python import cp_model


class TheorySeatingEngine:
    """
    Deterministic & CP-SAT Theory Examination Seating Engine.
    Enforces one candidate per usable bench, accessibility requirements,
    and configurable orthogonal paper-based adjacency separation.
    """
    ENGINE_VERSION = "1.0.0"

    @classmethod
    def verify_theory_seating(
        cls,
        snapshot: Dict[str, Any],
        allocations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Independent verification checker for theory examination seating.
        Validates completeness, uniqueness, bench usability, accessibility,
        and paper adjacency compliance.
        """
        violations: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        candidates = snapshot.get("candidates", [])
        rooms = snapshot.get("rooms", [])
        policy = snapshot.get("policy", {})
        hard_adjacency = policy.get("hard_paper_adjacency", False)

        candidate_map = {c["id"]: c for c in candidates}
        
        # Build seat index: (room_id, seat_id) -> seat
        seats_by_room_and_id: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Also map seat coords: (room_id, row, col) -> seat
        seats_by_coord: Dict[Tuple[str, int, int], Dict[str, Any]] = {}

        for r in rooms:
            rid = r["id"]
            for s in r.get("seats", []):
                sid = s["id"]
                seats_by_room_and_id[(rid, sid)] = s
                seats_by_coord[(rid, s["row_num"], s["col_num"])] = s

        # 1. Completeness: every registered candidate assigned exactly once
        assigned_c_ids = [a["candidate_id"] for a in allocations if "candidate_id" in a]
        assigned_c_set = set()

        for c_id in assigned_c_ids:
            if c_id in assigned_c_set:
                violations.append({
                    "rule": "DUPLICATE_CANDIDATE",
                    "candidate_id": c_id,
                    "message": f"Candidate '{c_id}' is assigned to multiple benches.",
                })
            assigned_c_set.add(c_id)

        for c in candidates:
            if c["id"] not in assigned_c_set:
                violations.append({
                    "rule": "UNASSIGNED_CANDIDATE",
                    "candidate_id": c["id"],
                    "message": f"Registered candidate '{c.get('roll_number', c['id'])}' has no seat assignment.",
                })

        # 2. Bench uniqueness & eligibility
        assigned_benches: Set[Tuple[str, str]] = set()

        # Map for adjacency check: (room_id, row, col) -> (candidate_id, paper_id)
        placed_coords: Dict[Tuple[str, int, int], Tuple[str, str]] = {}

        for a in allocations:
            cid = a.get("candidate_id")
            rid = a.get("room_id")
            sid = a.get("seat_id")
            cand = candidate_map.get(cid)

            bench_key = (rid, sid)
            if bench_key in assigned_benches:
                violations.append({
                    "rule": "DUPLICATE_BENCH",
                    "room_id": rid,
                    "seat_id": sid,
                    "message": f"Bench '{sid}' in room '{rid}' is assigned to more than one candidate.",
                })
            assigned_benches.add(bench_key)

            seat = seats_by_room_and_id.get(bench_key)
            if not seat:
                violations.append({
                    "rule": "UNKNOWN_SEAT",
                    "room_id": rid,
                    "seat_id": sid,
                    "message": f"Seat '{sid}' does not exist in room '{rid}'.",
                })
                continue

            # Check 3: Usable & Blocked seats
            if not seat.get("is_usable_for_exam", True) or seat.get("is_blocked", False):
                violations.append({
                    "rule": "BLOCKED_SEAT",
                    "room_id": rid,
                    "seat_id": sid,
                    "candidate_id": cid,
                    "message": f"Candidate '{cid}' is assigned to blocked/unusable bench '{seat.get('bench_label', sid)}'.",
                })

            # Check 4: Accessibility compliance
            if cand and cand.get("requires_accessible_seat"):
                if not seat.get("is_accessible", False):
                    violations.append({
                        "rule": "INELIGIBLE_ACCOMMODATION_SEAT",
                        "candidate_id": cid,
                        "room_id": rid,
                        "seat_id": sid,
                        "message": f"Candidate '{cand.get('roll_number', cid)}' requires accessible seating but bench '{seat.get('bench_label', sid)}' is not accessible.",
                    })

            # Record coordinate for adjacency check
            paper_id = cand.get("paper_id") if cand else a.get("paper_id")
            placed_coords[(rid, seat["row_num"], seat["col_num"])] = (cid, paper_id)

        # 5. Adjacency check: orthogonal neighbors (same row, adjacent col OR same col, adjacent row)
        checked_pairs: Set[Tuple[str, str]] = set()

        for (rid, r_num, c_num), (cid1, p1) in placed_coords.items():
            orthogonal_neighbors = [
                (r_num + 1, c_num),
                (r_num - 1, c_num),
                (r_num, c_num + 1),
                (r_num, c_num - 1),
            ]
            for (nr, nc) in orthogonal_neighbors:
                neighbor_key = (rid, nr, nc)
                if neighbor_key in placed_coords:
                    cid2, p2 = placed_coords[neighbor_key]
                    pair_key = tuple(sorted([cid1, cid2]))
                    if pair_key in checked_pairs:
                        continue
                    checked_pairs.add(pair_key)

                    if p1 and p2 and p1 == p2:
                        msg = f"Candidates '{cid1}' and '{cid2}' writing the same paper ({p1}) sit on adjacent benches in room '{rid}' ({r_num},{c_num} and {nr},{nc})."
                        if hard_adjacency:
                            violations.append({
                                "rule": "PAPER_ADJACENCY_VIOLATION",
                                "candidate_id": cid1,
                                "neighbor_candidate_id": cid2,
                                "paper_id": p1,
                                "room_id": rid,
                                "message": msg,
                            })
                        else:
                            warnings.append({
                                "rule": "PAPER_ADJACENCY_WARNING",
                                "candidate_id": cid1,
                                "neighbor_candidate_id": cid2,
                                "paper_id": p1,
                                "room_id": rid,
                                "message": msg,
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
        use_optimization: Optional[bool] = None,
        time_limit_seconds: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Allocates theory exam seating.
        Uses deterministic heuristic by default.
        Uses OR-Tools CP-SAT if use_optimization is True or hard paper adjacency is required.
        """
        candidates = snapshot.get("candidates", [])
        rooms = snapshot.get("rooms", [])
        policy = snapshot.get("policy", {})
        hard_adjacency = policy.get("hard_paper_adjacency", False)
        batch_grouping = policy.get("batch_grouping", True)

        # Check duplicate candidate input
        seen_cand_ids = set()
        for c in candidates:
            if c["id"] in seen_cand_ids:
                return {
                    "status": "INVALID_INPUT",
                    "allocations": [],
                    "error_code": "DUPLICATE_CANDIDATE",
                    "error_message": f"Duplicate candidate registration '{c['id']}'.",
                    "validation_report": {"is_valid": False, "violations": [{"rule": "DUPLICATE_CANDIDATE", "message": f"Duplicate candidate registration '{c['id']}'."}], "warnings": []},
                }
            seen_cand_ids.add(c["id"])

        # Collect eligible seats (usable and not blocked)
        usable_seats = []
        for r in rooms:
            rid = r["id"]
            for s in r.get("seats", []):
                if s.get("is_usable_for_exam", True) and not s.get("is_blocked", False):
                    usable_seats.append({
                        "room_id": rid,
                        "room_name": r.get("name", rid),
                        "seat_id": s["id"],
                        "bench_label": s.get("bench_label", s["id"]),
                        "row_num": s["row_num"],
                        "col_num": s["col_num"],
                        "is_accessible": bool(s.get("is_accessible", False)),
                    })

        # Check capacity
        if len(candidates) > len(usable_seats):
            shortfall = len(candidates) - len(usable_seats)
            return {
                "status": "INSUFFICIENT_CAPACITY",
                "allocations": [],
                "error_code": "INSUFFICIENT_CAPACITY",
                "error_message": f"Capacity shortfall: {len(candidates)} candidates registered, but only {len(usable_seats)} usable examination benches available (shortfall: {shortfall}).",
                "validation_report": {
                    "is_valid": False,
                    "violations": [{
                        "rule": "INSUFFICIENT_CAPACITY",
                        "message": f"Capacity shortfall of {shortfall} seats.",
                    }],
                    "warnings": [],
                },
            }

        # Check accessibility demand
        accessible_candidates = [c for c in candidates if c.get("requires_accessible_seat")]
        accessible_seats = [s for s in usable_seats if s["is_accessible"]]
        if len(accessible_candidates) > len(accessible_seats):
            return {
                "status": "INSUFFICIENT_ACCESSIBLE_SEATS",
                "allocations": [],
                "error_code": "INSUFFICIENT_ACCESSIBLE_SEATS",
                "error_message": f"{len(accessible_candidates)} candidates require accessible seating, but only {len(accessible_seats)} accessible benches are available.",
                "validation_report": {
                    "is_valid": False,
                    "violations": [{
                        "rule": "INSUFFICIENT_ACCESSIBLE_SEATS",
                        "message": "Not enough accessible examination benches for candidates requiring special accommodations.",
                    }],
                    "warnings": [],
                },
            }

        # Decide solver mode
        should_optimize = use_optimization if use_optimization is not None else (hard_adjacency and len(candidates) > 10)

        if should_optimize:
            return cls._allocate_cpsat(snapshot, candidates, usable_seats, time_limit_seconds)
        else:
            return cls._allocate_deterministic(snapshot, candidates, usable_seats)

    @classmethod
    def _allocate_deterministic(
        cls,
        snapshot: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        usable_seats: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Deterministic allocation algorithm.
        Sorts seats by room, row, column.
        Places accessible candidates first on accessible seats.
        Groups by batch / paper and interleaves papers across benches.
        """
        policy = snapshot.get("policy", {})
        hard_adjacency = policy.get("hard_paper_adjacency", False)

        # Sort seats: accessible seats first, then by (room_id, row_num, col_num)
        seats_sorted = sorted(
            usable_seats,
            key=lambda s: (s["room_id"], s["row_num"], s["col_num"])
        )

        # Partition candidates: accessible candidates first
        acc_cands = [c for c in candidates if c.get("requires_accessible_seat")]
        normal_cands = [c for c in candidates if not c.get("requires_accessible_seat")]

        # Group normal candidates by paper / section
        normal_cands.sort(key=lambda c: (c.get("paper_id", ""), c.get("section_id", ""), c.get("roll_number", "")))

        # Separate papers for checkerboard interleaving if multiple papers
        papers = list({c.get("paper_id") for c in candidates if c.get("paper_id")})
        allocations: List[Dict[str, Any]] = []
        assigned_seat_ids = set()

        # Step 1: Assign accessible candidates to accessible seats
        acc_seats = [s for s in seats_sorted if s["is_accessible"]]
        for idx, c in enumerate(acc_cands):
            seat = acc_seats[idx]
            allocations.append({
                "candidate_id": c["id"],
                "roll_number": c.get("roll_number", c["id"]),
                "candidate_name": c.get("name", ""),
                "paper_id": c.get("paper_id"),
                "room_id": seat["room_id"],
                "seat_id": seat["seat_id"],
                "bench_label": seat["bench_label"],
                "row_num": seat["row_num"],
                "col_num": seat["col_num"],
            })
            assigned_seat_ids.add((seat["room_id"], seat["seat_id"]))

        # Step 2: Assign remaining candidates to remaining seats
        remaining_seats = [s for s in seats_sorted if (s["room_id"], s["seat_id"]) not in assigned_seat_ids]

        if len(papers) > 1 and hard_adjacency:
            # Checkerboard interleaving by (row + col) % len(papers)
            cands_by_paper: Dict[str, List[Dict[str, Any]]] = {p: [] for p in papers}
            for c in normal_cands:
                cands_by_paper[c.get("paper_id", papers[0])].append(c)

            for seat in remaining_seats:
                # determine paper slot preference based on parity
                parity = (seat["row_num"] + seat["col_num"]) % len(papers)
                target_paper = papers[parity]

                c = None
                if cands_by_paper[target_paper]:
                    c = cands_by_paper[target_paper].pop(0)
                else:
                    # pick from any paper with candidates left
                    for p in papers:
                        if cands_by_paper[p]:
                            c = cands_by_paper[p].pop(0)
                            break

                if c:
                    allocations.append({
                        "candidate_id": c["id"],
                        "roll_number": c.get("roll_number", c["id"]),
                        "candidate_name": c.get("name", ""),
                        "paper_id": c.get("paper_id"),
                        "room_id": seat["room_id"],
                        "seat_id": seat["seat_id"],
                        "bench_label": seat["bench_label"],
                        "row_num": seat["row_num"],
                        "col_num": seat["col_num"],
                    })
        else:
            for idx, c in enumerate(normal_cands):
                seat = remaining_seats[idx]
                allocations.append({
                    "candidate_id": c["id"],
                    "roll_number": c.get("roll_number", c["id"]),
                    "candidate_name": c.get("name", ""),
                    "paper_id": c.get("paper_id"),
                    "room_id": seat["room_id"],
                    "seat_id": seat["seat_id"],
                    "bench_label": seat["bench_label"],
                    "row_num": seat["row_num"],
                    "col_num": seat["col_num"],
                })

        # Authoritative independent validation
        report = cls.verify_theory_seating(snapshot, allocations)

        if not report["is_valid"] and hard_adjacency:
            return {
                "status": "SEATING_UNSATISFIABLE",
                "allocations": [],
                "error_code": "SEATING_UNSATISFIABLE",
                "error_message": "Hard paper adjacency policy cannot be satisfied with deterministic allocation without violating orthogonal separation.",
                "validation_report": report,
            }

        return {
            "status": "ALLOCATED",
            "allocations": allocations,
            "error_code": None,
            "error_message": None,
            "validation_report": report,
        }

    @classmethod
    def _allocate_cpsat(
        cls,
        snapshot: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        usable_seats: List[Dict[str, Any]],
        time_limit_seconds: float,
    ) -> Dict[str, Any]:
        """
        Constraint programming seating model using Google OR-Tools CP-SAT.
        Enforces hard orthogonal neighbor paper separation without relaxation.
        """
        model = cp_model.CpModel()
        policy = snapshot.get("policy", {})
        hard_adjacency = policy.get("hard_paper_adjacency", True)

        # Variables: x[c_id, seat_idx]
        x = {}
        for c in candidates:
            cid = c["id"]
            req_acc = c.get("requires_accessible_seat", False)
            for s_idx, seat in enumerate(usable_seats):
                if req_acc and not seat["is_accessible"]:
                    continue  # Ineligible seat
                x[(cid, s_idx)] = model.NewBoolVar(f"x_{cid[:6]}_{s_idx}")

        # (C1) Exactly one seat per candidate
        for c in candidates:
            cid = c["id"]
            model.AddExactlyOne(x[(cid, s_idx)] for s_idx in range(len(usable_seats)) if (cid, s_idx) in x)

        # (C2) At most one candidate per seat
        for s_idx in range(len(usable_seats)):
            active_vars = [x[(c["id"], s_idx)] for c in candidates if (c["id"], s_idx) in x]
            if len(active_vars) > 1:
                model.Add(sum(active_vars) <= 1)

        # (C3) Hard paper adjacency (if enabled)
        if hard_adjacency:
            # Map adjacent seat pairs
            seats_by_coord = {(s["room_id"], s["row_num"], s["col_num"]): idx for idx, s in enumerate(usable_seats)}
            adj_seat_pairs = []
            for (rid, r, c), idx1 in seats_by_coord.items():
                for (nr, nc) in [(r+1, c), (r, c+1)]:
                    if (rid, nr, nc) in seats_by_coord:
                        idx2 = seats_by_coord[(rid, nr, nc)]
                        adj_seat_pairs.append((idx1, idx2))

            # Group candidates by paper
            cands_by_paper: Dict[str, List[str]] = {}
            for c in candidates:
                pid = c.get("paper_id", "")
                if pid:
                    cands_by_paper.setdefault(pid, []).append(c["id"])

            for (idx1, idx2) in adj_seat_pairs:
                for pid, c_ids in cands_by_paper.items():
                    if len(c_ids) > 1:
                        for i in range(len(c_ids)):
                            for j in range(i + 1, len(c_ids)):
                                c1, c2 = c_ids[i], c_ids[j]
                                if (c1, idx1) in x and (c2, idx2) in x:
                                    model.Add(x[(c1, idx1)] + x[(c2, idx2)] <= 1)
                                if (c2, idx1) in x and (c1, idx2) in x:
                                    model.Add(x[(c2, idx1)] + x[(c1, idx2)] <= 1)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        solver.parameters.num_search_workers = 2

        sat_status = solver.Solve(model)

        if sat_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            allocations = []
            cand_map = {c["id"]: c for c in candidates}
            for (cid, s_idx), var in x.items():
                if solver.Value(var) == 1:
                    seat = usable_seats[s_idx]
                    cand = cand_map[cid]
                    allocations.append({
                        "candidate_id": cid,
                        "roll_number": cand.get("roll_number", cid),
                        "candidate_name": cand.get("name", ""),
                        "paper_id": cand.get("paper_id"),
                        "room_id": seat["room_id"],
                        "seat_id": seat["seat_id"],
                        "bench_label": seat["bench_label"],
                        "row_num": seat["row_num"],
                        "col_num": seat["col_num"],
                    })

            report = cls.verify_theory_seating(snapshot, allocations)
            return {
                "status": "ALLOCATED",
                "allocations": allocations,
                "error_code": None,
                "error_message": None,
                "validation_report": report,
            }
        else:
            return {
                "status": "SEATING_UNSATISFIABLE",
                "allocations": [],
                "error_code": "SEATING_UNSATISFIABLE",
                "error_message": "Hard seating constraints and orthogonal paper adjacency cannot be satisfied simultaneously.",
                "validation_report": {
                    "is_valid": False,
                    "violations": [{
                        "rule": "SEATING_UNSATISFIABLE",
                        "message": "Mathematically infeasible under hard paper adjacency rules without relaxing constraints.",
                    }],
                    "warnings": [],
                },
            }
