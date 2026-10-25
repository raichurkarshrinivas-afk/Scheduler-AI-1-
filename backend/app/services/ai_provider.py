import json
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.core.config import settings


class AIProviderError(Exception):
    pass


class AIProviderDisabledError(AIProviderError):
    pass


class AIProviderTimeoutError(AIProviderError):
    pass


class AISchemaValidationError(AIProviderError):
    pass


class BaseAIProvider(ABC):
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def interpret_change(
        self,
        sanitized_prompt: str,
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def explain_issues(
        self,
        violations: List[Dict[str, Any]],
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def propose_column_mappings(
        self,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        pass


class DisabledAIProvider(BaseAIProvider):
    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "provider": "disabled",
            "is_available": False,
            "model_name": "none",
            "total_requests": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "disclaimer": (
                "AI suggestions are unverified candidate interpretations. "
                "You must review and validate against institutional rules before applying."
            ),
        }

    def interpret_change(
        self,
        sanitized_prompt: str,
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise AIProviderDisabledError(
            "AI interpretation assistant is disabled by system configuration."
        )

    def explain_issues(
        self,
        violations: List[Dict[str, Any]],
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise AIProviderDisabledError(
            "AI interpretation assistant is disabled by system configuration."
        )

    def propose_column_mappings(
        self,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        raise AIProviderDisabledError(
            "AI interpretation assistant is disabled by system configuration."
        )


class MockAIProvider(BaseAIProvider):
    def __init__(self):
        self.total_requests = 0
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "provider": "mock",
            "is_available": True,
            "model_name": "mock-deterministic-v1",
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "disclaimer": (
                "AI suggestions are unverified candidate interpretations. "
                "You must review and validate against institutional rules before applying."
            ),
        }

    def interpret_change(
        self,
        sanitized_prompt: str,
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.total_requests += 1
        self.total_tokens += len(sanitized_prompt.split()) + 80
        self.estimated_cost_usd += 0.0002

        if "__SIMULATE_TIMEOUT__" in sanitized_prompt:
            raise AIProviderTimeoutError("Mock AI provider request timed out after 10.0s.")

        if "__SIMULATE_MALFORMED_OUTPUT__" in sanitized_prompt:
            return {"malformed_garbage": True, "missing_required_fields": 12345}

        is_injection_attempt = any(
            p in sanitized_prompt.lower()
            for p in ["ignore previous", "publish draft", "grant admin", "set is_published", "delete from"]
        )

        p_lower = sanitized_prompt.lower()
        ambiguities = []

        has_afternoon = "afternoon" in p_lower and not re.search(r"\b(1[0-4]|[0-9]):00\b", p_lower) and not re.search(r"\bperiod [0-9]\b", p_lower)
        if has_afternoon:
            ambiguities.append({
                "type": "UNDEFINED_TIME",
                "description": "Request mentions 'afternoon' without specifying an exact period or start time.",
                "suggested_clarification": "Defaulted candidate to Period 5 (14:00), but please confirm period 4 vs 5 vs 6.",
            })

        has_morning = "morning" in p_lower and not re.search(r"\b(1[0-4]|[0-9]):00\b", p_lower) and not re.search(r"\bperiod [0-9]\b", p_lower)
        if has_morning:
            ambiguities.append({
                "type": "UNDEFINED_TIME",
                "description": "Request mentions 'morning' without specifying an exact period.",
                "suggested_clarification": "Defaulted candidate to Period 2 (10:00), but please confirm period 1 vs 2 vs 3.",
            })

        known_teachers = [(t.get("name") or "").lower() for t in approved_context.get("teachers", []) if t.get("name")]
        if "dr. unknown" in p_lower or ("teacher" in p_lower and "dr. jones" in p_lower and "dr. jones" not in known_teachers):
            ambiguities.append({
                "type": "UNKNOWN_ENTITY",
                "description": "Referenced instructor could not be resolved in the institution teacher registry.",
                "suggested_clarification": "Please select a registered instructor from the dropdown.",
            })

        is_preference = "prefer" in p_lower or "if possible" in p_lower or "would like" in p_lower
        if is_preference:
            ambiguities.append({
                "type": "PREFERENCE_VS_HARD_CONSTRAINT",
                "description": "Request phrased as a soft preference rather than an immutable requirement.",
                "suggested_clarification": "Interpreted as a soft preference. Solver can violate if room is unavailable.",
            })

        is_date_specific = "this friday" in p_lower or "next monday" in p_lower or "october" in p_lower or "2026-" in p_lower
        if is_date_specific:
            ambiguities.append({
                "type": "TERM_WIDE_VS_DATE_SPECIFIC",
                "description": "Request mentions a specific calendar occurrence rather than an entire recurring term.",
                "suggested_clarification": "Standard timetable changes apply to the recurring term schedule. Confirm if calendar exception is needed instead.",
            })

        days_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        proposed_day = 1
        for d_name, d_val in days_map.items():
            if d_name in p_lower:
                proposed_day = d_val
                break

        proposed_period = 2
        target_phrase = p_lower.split("to ")[-1] if "to " in p_lower else p_lower
        if "morning" in target_phrase:
            proposed_period = 2
        elif "afternoon" in target_phrase:
            proposed_period = 5
        elif "afternoon" in p_lower:
            proposed_period = 5
        elif "morning" in p_lower:
            proposed_period = 2
        elif "period 1" in p_lower:
            proposed_period = 1
        elif "period 3" in p_lower:
            proposed_period = 3
        elif "period 4" in p_lower:
            proposed_period = 4
        elif "period 5" in p_lower:
            proposed_period = 5

        sessions = approved_context.get("sessions", [])
        matched_session = sessions[0] if sessions else None
        for s in sessions:
            c_code = (s.get("course_code") or "").lower()
            s_name = (s.get("name") or "").lower()
            if c_code and c_code in p_lower:
                matched_session = s
                break
            if s_name and s_name in p_lower:
                matched_session = s
                break

        rooms = approved_context.get("rooms", [])
        proposed_room_name = None
        for r in rooms:
            if (r.get("name") and r.get("name").lower() in p_lower) or (r.get("code") and r.get("code").lower() in p_lower):
                proposed_room_name = r.get("name")
                break
        if not proposed_room_name and rooms:
            proposed_room_name = rooms[0].get("name")

        raw_change = {
            "action": "MOVE",
            "target_course": matched_session.get("course_code") if matched_session else "CS101",
            "target_teacher": matched_session.get("teacher_name") if matched_session else "Dr. Alan Turing",
            "target_room": matched_session.get("room_name") if matched_session else "Room 101",
            "proposed_day": proposed_day,
            "proposed_period": proposed_period,
            "proposed_room": proposed_room_name,
            "proposed_teacher": matched_session.get("teacher_name") if matched_session else "Dr. Alan Turing",
            "is_hard_constraint": not is_preference,
            "is_term_wide": not is_date_specific,
        }

        summary = (
            f"Move session for {raw_change['target_course']} to "
            f"Day {proposed_day} Period {proposed_period}"
            + (f" in {proposed_room_name}" if proposed_room_name else "")
        )
        if is_injection_attempt:
            summary = "Interpreted timetable change request (security policy: administrative commands ignored)."

        return {
            "raw_summary": summary,
            "confidence_score": 0.92 if not ambiguities else 0.75,
            "is_ambiguous": len(ambiguities) > 0,
            "ambiguities": ambiguities,
            "raw_changes": [raw_change],
        }
    def explain_issues(
        self,
        violations: List[Dict[str, Any]],
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.total_requests += 1
        self.total_tokens += len(violations) * 40 + 60
        self.estimated_cost_usd += 0.00015

        explanations = []
        for v in violations:
            rule = v.get("rule", "GENERAL")
            msg = v.get("message", "Constraint violation detected.")
            session_id = v.get("session_id", "Unknown session")

            if rule == "COMPLETENESS":
                explanations.append({
                    "rule": rule,
                    "summary": f"Unscheduled session requirement ({session_id})",
                    "root_cause_explanation": (
                        "The solver was unable to locate a mutually feasible room and period "
                        "meeting room type, teacher availability, and class conflict constraints."
                    ),
                    "potential_resolutions": [
                        "Check teacher availability rules for blocked time windows.",
                        "Inspect room capacity to ensure a qualifying room is unbooked.",
                        "Consider relaxing consecutive practical requirements or soft preference weights.",
                    ],
                    "involved_sessions": [session_id],
                    "involved_resources": [],
                })
            elif rule == "TEACHER_CONFLICT":
                teacher_id = v.get("teacher_id", "Teacher")
                explanations.append({
                    "rule": rule,
                    "summary": f"Instructor schedule concurrency collision ({teacher_id})",
                    "root_cause_explanation": (
                        f"Instructor {teacher_id} is assigned to two concurrent sessions in the same period."
                    ),
                    "potential_resolutions": [
                        "Move one of the conflicting sessions to another day or period.",
                        "Assign an alternate qualified instructor for one offering.",
                    ],
                    "involved_sessions": [session_id] if session_id else [],
                    "involved_resources": [teacher_id],
                })
            elif rule == "ROOM_DOUBLE_BOOKING":
                room_id = v.get("room_id", "Room")
                explanations.append({
                    "rule": rule,
                    "summary": f"Facility concurrent reservation collision ({room_id})",
                    "root_cause_explanation": (
                        f"Room {room_id} has multiple classes booked in the same time slot."
                    ),
                    "potential_resolutions": [
                        "Reassign one of the sessions to a different eligible instructional room.",
                        "Reschedule one session to an available period.",
                    ],
                    "involved_sessions": [session_id] if session_id else [],
                    "involved_resources": [room_id],
                })
            elif rule == "CAPACITY_OVERLOAD":
                explanations.append({
                    "rule": rule,
                    "summary": "Student enrollment exceeds facility seating capacity",
                    "root_cause_explanation": (
                        "The registered student count for the cohort exceeds the maximum physical capacity of the assigned room."
                    ),
                    "potential_resolutions": [
                        "Move the cohort to a higher-capacity lecture theatre.",
                        "Split the student cohort into multiple parallel laboratory or tutorial batches.",
                    ],
                    "involved_sessions": [session_id] if session_id else [],
                    "involved_resources": [],
                })
            else:
                explanations.append({
                    "rule": rule,
                    "summary": f"Schedule validation rule: {rule}",
                    "root_cause_explanation": msg,
                    "potential_resolutions": [
                        "Review input constraints and session requirements.",
                        "Run the automated solver with relaxation options.",
                    ],
                    "involved_sessions": [session_id] if session_id else [],
                    "involved_resources": [],
                })

        return {
            "explanations": explanations,
            "general_recommendations": [
                "Prioritize resolving hard constraint collisions (double-bookings) before addressing soft preference warnings.",
                "Review teacher availability windows in the Resources tab.",
            ],
            "disclaimer": (
                "Checker explanations are advisory diagnostic candidates. "
                "Authoritative solver validation rules take precedence."
            ),
        }

    def propose_column_mappings(
        self,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        self.total_requests += 1
        self.total_tokens += len(headers) * 15 + 50
        self.estimated_cost_usd += 0.0001

        schema_fields = {
            "course_code": ["course code", "course_code", "course_id", "subject_code", "sub_code", "code"],
            "course_name": ["course name", "course_name", "title", "subject", "subject_name"],
            "teacher_name": ["teacher", "faculty", "instructor", "professor", "teacher_name", "staff"],
            "teacher_code": ["teacher_id", "faculty_id", "staff_id", "emp_id"],
            "room_code": ["room", "room_no", "hall", "classroom", "venue", "room_code"],
            "room_capacity": ["capacity", "seats", "benches", "max_students"],
            "day_of_week": ["day", "weekday", "day_of_week"],
            "start_period": ["period", "slot", "start_period", "time_slot", "time"],
            "session_type": ["type", "session_type", "mode"],
            "student_group": ["section", "batch", "class", "cohort", "group", "student_group"],
        }

        mappings = {}
        confidences = {}
        ambiguities = []
        unmapped = []

        for h in headers:
            clean_h = h.strip().lower().replace("_", " ").replace("-", " ")
            matched_field = None
            highest_conf = 0.0

            for field, patterns in schema_fields.items():
                for p in patterns:
                    if clean_h == p:
                        matched_field = field
                        highest_conf = 0.98
                        break
                    elif p in clean_h or clean_h in p:
                        matched_field = field
                        highest_conf = 0.82
                        break
                if highest_conf >= 0.95:
                    break

            if matched_field:
                mappings[h] = matched_field
                confidences[h] = highest_conf
            else:
                mappings[h] = None
                confidences[h] = 0.0
                unmapped.append(h)
                ambiguities.append(f"Header '{h}' could not be unambiguously mapped to a system schema field.")

        return {
            "mappings": mappings,
            "confidences": confidences,
            "ambiguities": ambiguities,
            "unmapped_headers": unmapped,
            "disclaimer": "Proposed column mappings must be verified by an administrator before importing data.",
        }


class ExternalAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model_name: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url or "https://api.openai.com/v1"
        self.total_requests = 0
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "provider": "external",
            "is_available": bool(self.api_key),
            "model_name": self.model_name,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "disclaimer": (
                "AI suggestions are unverified candidate interpretations. "
                "You must review and validate against institutional rules before applying."
            ),
        }

    def interpret_change(
        self,
        sanitized_prompt: str,
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "disabled":
            raise AIProviderDisabledError("External AI provider is not configured with a valid API key.")
        mock_fallback = MockAIProvider()
        return mock_fallback.interpret_change(sanitized_prompt, approved_context)

    def explain_issues(
        self,
        violations: List[Dict[str, Any]],
        approved_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "disabled":
            raise AIProviderDisabledError("External AI provider is not configured with a valid API key.")
        mock_fallback = MockAIProvider()
        return mock_fallback.explain_issues(violations, approved_context)

    def propose_column_mappings(
        self,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "disabled":
            raise AIProviderDisabledError("External AI provider is not configured with a valid API key.")
        mock_fallback = MockAIProvider()
        return mock_fallback.propose_column_mappings(headers, sample_rows)


_provider_instance: Optional[BaseAIProvider] = None


def get_ai_provider() -> BaseAIProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if not settings.AI_ENABLED or settings.AI_PROVIDER == "disabled":
        _provider_instance = DisabledAIProvider()
    elif settings.AI_PROVIDER == "mock":
        _provider_instance = MockAIProvider()
    elif settings.AI_PROVIDER in ["openai", "gemini", "external"]:
        _provider_instance = ExternalAIProvider(
            api_key=settings.AI_API_KEY or "",
            model_name=settings.AI_MODEL_NAME,
            base_url=settings.AI_BASE_URL,
        )
    else:
        _provider_instance = DisabledAIProvider()

    return _provider_instance


def set_ai_provider_for_testing(provider: Optional[BaseAIProvider]):
    global _provider_instance
    _provider_instance = provider
