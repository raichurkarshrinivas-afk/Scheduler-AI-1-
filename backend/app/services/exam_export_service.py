import time
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class ExamExportService:
    """
    Export generator for examination logistics.
    Generates verified hall seat plans, candidate lists, attendance sheets,
    and practical batch/workstation allocations with strict privacy safeguards.
    """
    SECRET_KEY = "scheduler-export-auth-token-salt"

    @classmethod
    def generate_export_token(cls, sitting_id: str, expires_in_seconds: int = 3600) -> str:
        """Generates a secure, expiring token for authorized document exports."""
        exp_timestamp = int(time.time()) + expires_in_seconds
        payload = f"{sitting_id}:{exp_timestamp}"
        sig = hmac.new(cls.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    @classmethod
    def verify_export_token(cls, sitting_id: str, token: str) -> bool:
        """Validates that the export token is authentic and not expired."""
        parts = token.split(":")
        if len(parts) != 3:
            return False
        tok_sitting_id, exp_str, sig = parts
        if tok_sitting_id != sitting_id:
            return False
        try:
            exp_timestamp = int(exp_str)
        except ValueError:
            return False
        if time.time() > exp_timestamp:
            return False  # Expired
        expected_payload = f"{tok_sitting_id}:{exp_str}"
        expected_sig = hmac.new(cls.SECRET_KEY.encode(), expected_payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)

    @classmethod
    def generate_theory_hall_seat_plan(
        cls,
        sitting: Any,
        room_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates public hall seating chart.
        CRITICAL PRIVACY RULE: Private accommodation notes are strictly excluded.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        snapshot = sitting.input_snapshot or {}
        allocations = sitting.output_allocations or []
        candidates = {c["id"]: c for c in snapshot.get("candidates", [])}
        rooms = {r["id"]: r for r in snapshot.get("rooms", [])}

        target_allocations = allocations
        if room_id:
            target_allocations = [a for a in allocations if a.get("room_id") == room_id]

        seats_data = []
        for a in target_allocations:
            cid = a.get("candidate_id")
            cand = candidates.get(cid, {})
            # Explicitly omit private_accommodations!
            seats_data.append({
                "bench_label": a.get("bench_label", a.get("seat_id")),
                "row_num": a.get("row_num"),
                "col_num": a.get("col_num"),
                "roll_number": cand.get("roll_number", a.get("roll_number", "N/A")),
                "candidate_name": cand.get("name", a.get("candidate_name", "Candidate")),
                "paper_code": cand.get("paper_code", cand.get("paper_id", "N/A")),
                "room_name": rooms.get(a.get("room_id"), {}).get("name", a.get("room_id")),
                # Private notes omitted for privacy
            })

        seats_data.sort(key=lambda s: (s.get("row_num", 0), s.get("col_num", 0)))

        return {
            "document_type": "HALL_SEAT_PLAN",
            "sitting_id": sitting.id,
            "sitting_name": sitting.name,
            "status_label": "PUBLISHED" if sitting.is_published else "DRAFT",
            "revision": sitting.revision,
            "generated_at": now_utc,
            "room_id": room_id,
            "total_allocated": len(seats_data),
            "seats": seats_data,
        }

    @classmethod
    def generate_candidate_list(
        cls,
        sitting: Any,
    ) -> Dict[str, Any]:
        """Generates candidate index list."""
        now_utc = datetime.now(timezone.utc).isoformat()
        snapshot = sitting.input_snapshot or {}
        allocations = sitting.output_allocations or []
        candidates = {c["id"]: c for c in snapshot.get("candidates", [])}
        rooms = {r["id"]: r for r in snapshot.get("rooms", [])}

        cand_rows = []
        for a in allocations:
            cid = a.get("candidate_id")
            cand = candidates.get(cid, {})
            cand_rows.append({
                "roll_number": cand.get("roll_number", a.get("roll_number", "N/A")),
                "candidate_name": cand.get("name", a.get("candidate_name", "Candidate")),
                "paper_code": cand.get("paper_code", cand.get("paper_id", "N/A")),
                "room_name": rooms.get(a.get("room_id"), {}).get("name", a.get("room_id")),
                "bench_label": a.get("bench_label", a.get("seat_id")),
            })

        cand_rows.sort(key=lambda c: c["roll_number"])

        return {
            "document_type": "CANDIDATE_LIST",
            "sitting_id": sitting.id,
            "sitting_name": sitting.name,
            "status_label": "PUBLISHED" if sitting.is_published else "DRAFT",
            "revision": sitting.revision,
            "generated_at": now_utc,
            "total_candidates": len(cand_rows),
            "candidates": cand_rows,
        }

    @classmethod
    def generate_attendance_sheet(
        cls,
        sitting: Any,
        room_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates official examination attendance verification sheet."""
        now_utc = datetime.now(timezone.utc).isoformat()
        snapshot = sitting.input_snapshot or {}
        allocations = sitting.output_allocations or []
        candidates = {c["id"]: c for c in snapshot.get("candidates", [])}
        rooms = {r["id"]: r for r in snapshot.get("rooms", [])}

        target_allocations = allocations
        if room_id:
            target_allocations = [a for a in allocations if a.get("room_id") == room_id]

        attendance_rows = []
        for a in target_allocations:
            cid = a.get("candidate_id")
            cand = candidates.get(cid, {})
            attendance_rows.append({
                "roll_number": cand.get("roll_number", a.get("roll_number", "N/A")),
                "candidate_name": cand.get("name", a.get("candidate_name", "Candidate")),
                "paper_code": cand.get("paper_code", cand.get("paper_id", "N/A")),
                "bench_label": a.get("bench_label", a.get("seat_id")),
                "room_name": rooms.get(a.get("room_id"), {}).get("name", a.get("room_id")),
                "signature_placeholder": "[ _________________________ ]",
                "present": True,
            })

        attendance_rows.sort(key=lambda r: (r.get("room_name", ""), r.get("bench_label", "")))

        return {
            "document_type": "ATTENDANCE_SHEET",
            "sitting_id": sitting.id,
            "sitting_name": sitting.name,
            "status_label": "PUBLISHED" if sitting.is_published else "DRAFT",
            "revision": sitting.revision,
            "generated_at": now_utc,
            "room_id": room_id,
            "total_candidates": len(attendance_rows),
            "attendance_records": attendance_rows,
        }

    @classmethod
    def generate_practical_workstation_list(
        cls,
        sitting: Any,
    ) -> Dict[str, Any]:
        """Generates laboratory batch and workstation allocation roster."""
        now_utc = datetime.now(timezone.utc).isoformat()
        snapshot = sitting.input_snapshot or {}
        allocations = sitting.output_allocations or []
        candidates = {c["id"]: c for c in snapshot.get("candidates", [])}
        labs = {l["id"]: l for l in snapshot.get("labs", [])}
        sittings_info = {s["batch_id"]: s for s in snapshot.get("sittings", [])}

        workstation_rows = []
        for a in allocations:
            cid = a.get("candidate_id")
            cand = candidates.get(cid, {})
            bid = a.get("batch_id")
            s_info = sittings_info.get(bid, {})
            lid = a.get("lab_id")
            lab = labs.get(lid, {})

            workstation_rows.append({
                "batch_id": bid,
                "start_time": s_info.get("start_time", "N/A"),
                "end_time": s_info.get("end_time", "N/A"),
                "buffer_minutes": s_info.get("buffer_minutes", 15),
                "lab_name": lab.get("name", lid),
                "workstation_number": a.get("workstation_number"),
                "workstation_label": a.get("workstation_label", a.get("workstation_id")),
                "roll_number": cand.get("roll_number", a.get("roll_number", "N/A")),
                "candidate_name": cand.get("name", a.get("candidate_name", "Candidate")),
                "chief_examiner": s_info.get("chief_examiner_id", "N/A"),
            })

        workstation_rows.sort(key=lambda w: (w["batch_id"], w.get("workstation_number", 0)))

        return {
            "document_type": "PRACTICAL_WORKSTATION_ROSTER",
            "sitting_id": sitting.id,
            "sitting_name": sitting.name,
            "status_label": "PUBLISHED" if sitting.is_published else "DRAFT",
            "revision": sitting.revision,
            "generated_at": now_utc,
            "total_allocated": len(workstation_rows),
            "batches": workstation_rows,
        }
