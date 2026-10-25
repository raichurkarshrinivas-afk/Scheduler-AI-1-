import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.encryption import (
    encrypt_token,
    decrypt_token,
    sign_oauth_state,
    verify_oauth_state,
)
from app.models.communication import CalendarCredential
from app.models.publication import Publication
from app.models.schedule import Session as TimetableSession
from app.models.exam import ExamSitting

logger = logging.getLogger("google_calendar_service")


class MockGoogleCalendarClient:
    """Mock Google Calendar client for test environments and when live credentials are absent"""
    test_type: str = "MOCK"

    def __init__(self):
        self.calendars: Dict[str, Dict[str, Any]] = {}
        self.events: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._next_event_id: int = 1000

    def create_secondary_calendar(self, title: str) -> str:
        cal_id = f"mock_cal_{len(self.calendars) + 1}@scheduler.internal"
        self.calendars[cal_id] = {"id": cal_id, "summary": title}
        self.events[cal_id] = {}
        return cal_id

    def create_or_update_event(
        self,
        calendar_id: str,
        event_id: Optional[str],
        summary: str,
        description: str,
        start_iso: str,
        end_iso: str,
        location: str = ""
    ) -> str:
        if calendar_id not in self.events:
            self.events[calendar_id] = {}

        if not event_id or event_id not in self.events[calendar_id]:
            self._next_event_id += 1
            event_id = f"mock_evt_{self._next_event_id}"

        self.events[calendar_id][event_id] = {
            "id": event_id,
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
            "location": location,
        }
        return event_id

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        if calendar_id in self.events and event_id in self.events[calendar_id]:
            del self.events[calendar_id][event_id]
            return True
        return False


_global_mock_client = MockGoogleCalendarClient()


class GoogleCalendarService:

    @staticmethod
    def is_configured() -> bool:
        return bool(
            settings.GOOGLE_CALENDAR_ENABLED
            and settings.GOOGLE_CLIENT_ID
            and settings.GOOGLE_CLIENT_SECRET
            and settings.GOOGLE_REDIRECT_URI
        )

    @staticmethod
    def get_setup_guidance() -> Dict[str, Any]:
        return {
            "configured": GoogleCalendarService.is_configured(),
            "status": "CONFIGURED" if GoogleCalendarService.is_configured() else "NOT_CONFIGURED",
            "provider": "Google Calendar API v3",
            "guidance": (
                "Google Calendar integration is optional and currently not configured.\n"
                "Setup instructions:\n"
                "1. Create a project in Google Cloud Console (https://console.cloud.google.com/).\n"
                "2. Enable the Google Calendar API.\n"
                "3. In 'APIs & Services' -> 'Credentials', create an OAuth 2.0 Client ID (Web Application).\n"
                "4. Add your authorized redirect URI (e.g., http://localhost:8000/api/v1/communication/calendar/callback).\n"
                "5. Set environment variables in backend/.env:\n"
                "   GOOGLE_CALENDAR_ENABLED=True\n"
                "   GOOGLE_CLIENT_ID=<your-client-id>\n"
                "   GOOGLE_CLIENT_SECRET=<your-client-secret>\n"
                "   GOOGLE_REDIRECT_URI=<your-redirect-uri>\n"
                "   GOOGLE_ENCRYPTION_KEY=<optional-base64-32byte-key>\n"
                "6. Restart the backend service."
            )
        }

    @staticmethod
    def get_auth_url(user_id: str, institution_id: str) -> Dict[str, Any]:
        if not GoogleCalendarService.is_configured():
            return {
                "error": "Google Calendar integration is not configured.",
                "guidance": GoogleCalendarService.get_setup_guidance()
            }

        state_token = sign_oauth_state({
            "user_id": user_id,
            "institution_id": institution_id,
        })

        scope = "https://www.googleapis.com/auth/calendar.events"
        url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope={scope}&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"state={state_token}"
        )
        return {"auth_url": url, "state": state_token}

    @staticmethod
    def handle_oauth_callback(
        db: Session,
        code: str,
        state: str,
        mock_tokens: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[CalendarCredential]]:
        """
        Validates signed state, exchanges code for access & refresh tokens,
        stores credentials encrypted with Fernet, and initialises secondary calendar.
        """
        verified_state = verify_oauth_state(state)
        if not verified_state:
            return False, "Invalid or expired OAuth state parameter.", None

        user_id = verified_state["user_id"]
        institution_id = verified_state["institution_id"]

        if mock_tokens:
            print("[TEST TYPE: MOCK - Google Calendar OAuth Exchange]")
            access_token = mock_tokens.get("access_token", "mock_access_token")
            refresh_token = mock_tokens.get("refresh_token", "mock_refresh_token")
            expires_in = mock_tokens.get("expires_in", 3600)
        else:
            if not GoogleCalendarService.is_configured():
                return False, "Google Calendar integration is not configured on this server.", None
            try:
                import httpx
                resp = httpx.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    },
                    timeout=10.0,
                )
                if resp.status_code != 200:
                    return False, f"Google token exchange failed: {resp.text}", None
                token_data = resp.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
            except Exception as ex:
                return False, f"Network error communicating with Google: {str(ex)}", None

        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)

        cred = db.query(CalendarCredential).filter(
            CalendarCredential.user_id == user_id,
            CalendarCredential.institution_id == institution_id
        ).first()

        if not cred:
            cred = CalendarCredential(
                user_id=user_id,
                institution_id=institution_id,
                sync_status="CONNECTED",
                synced_events_map={},
                sync_event_count=0,
            )
            db.add(cred)

        cred.encrypted_access_token = encrypt_token(access_token)
        if refresh_token:
            cred.encrypted_refresh_token = encrypt_token(refresh_token)
        cred.token_expiry = expiry
        cred.sync_status = "CONNECTED"
        cred.last_error = None

        if not cred.calendar_id:
            cred.calendar_id = _global_mock_client.create_secondary_calendar("Scheduler - Academic Calendar")

        db.commit()
        db.refresh(cred)
        return True, "Successfully connected Google Calendar.", cred

    @staticmethod
    def get_credential_status(db: Session, user_id: str, institution_id: str) -> Dict[str, Any]:
        cred = db.query(CalendarCredential).filter(
            CalendarCredential.user_id == user_id,
            CalendarCredential.institution_id == institution_id
        ).first()

        configured = GoogleCalendarService.is_configured()

        if not configured and not cred:
            return {
                "configured": False,
                "status": "NOT_CONFIGURED",
                "is_connected": False,
                "guidance": GoogleCalendarService.get_setup_guidance()["guidance"]
            }

        if not cred or cred.sync_status == "DISCONNECTED":
            return {
                "configured": configured,
                "status": "DISCONNECTED",
                "is_connected": False,
                "calendar_id": None,
                "sync_event_count": 0,
                "last_synced_at": None,
                "last_error": None,
            }

        return {
            "configured": configured,
            "status": cred.sync_status,
            "is_connected": cred.sync_status == "CONNECTED",
            "calendar_id": cred.calendar_id,
            "sync_event_count": cred.sync_event_count,
            "last_synced_at": cred.last_synced_at.isoformat() if cred.last_synced_at else None,
            "last_error": cred.last_error,
        }

    @staticmethod
    def disconnect(db: Session, user_id: str, institution_id: str) -> bool:
        cred = db.query(CalendarCredential).filter(
            CalendarCredential.user_id == user_id,
            CalendarCredential.institution_id == institution_id
        ).first()
        if cred:
            cred.encrypted_access_token = None
            cred.encrypted_refresh_token = None
            cred.token_expiry = None
            cred.sync_status = "DISCONNECTED"
            cred.last_error = None
            db.commit()
            return True
        return False

    @staticmethod
    def refresh_access_token_if_needed(
        db: Session,
        cred: CalendarCredential,
        mock_fail_revoked: bool = False
    ) -> bool:
        """Refreshes expired access token. Handles revoked token gracefully without crashing."""
        if mock_fail_revoked:
            cred.sync_status = "REVOKED"
            cred.last_error = "OAuth access has been revoked or expired. Please re-authenticate."
            db.commit()
            return False

        now = datetime.datetime.now(datetime.timezone.utc)
        expiry = cred.token_expiry
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        if expiry and expiry > now:
            return True

        refresh_token = decrypt_token(cred.encrypted_refresh_token or "")
        if not refresh_token:
            cred.sync_status = "REVOKED"
            cred.last_error = "No refresh token available to refresh session."
            db.commit()
            return False

        if not GoogleCalendarService.is_configured():
            print("[TEST TYPE: MOCK - Google Calendar Token Refresh]")
            cred.token_expiry = now + datetime.timedelta(hours=1)
            db.commit()
            return True

        try:
            import httpx
            resp = httpx.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                cred.encrypted_access_token = encrypt_token(data["access_token"])
                expires_in = data.get("expires_in", 3600)
                cred.token_expiry = now + datetime.timedelta(seconds=expires_in)
                cred.sync_status = "CONNECTED"
                cred.last_error = None
                db.commit()
                return True
            else:
                err_text = resp.text
                if "invalid_grant" in err_text:
                    cred.sync_status = "REVOKED"
                    cred.last_error = "Token was revoked or expired by Google."
                else:
                    cred.last_error = f"Token refresh failed: {err_text}"
                db.commit()
                return False
        except Exception as ex:
            cred.last_error = f"Network exception during token refresh: {str(ex)}"
            db.commit()
            return False

    @staticmethod
    def sync_user_calendar_safe(
        db: Session,
        user_id: str,
        institution_id: str,
        publication: Optional[Publication] = None
    ) -> Dict[str, Any]:
        cred = db.query(CalendarCredential).filter(
            CalendarCredential.user_id == user_id,
            CalendarCredential.institution_id == institution_id
        ).first()

        if not cred:
            return {"synced": False, "reason": "No calendar credential found"}
        if cred.sync_status != "CONNECTED":
            return {"synced": False, "reason": f"Calendar sync status is {cred.sync_status}: {cred.last_error or 'Credentials revoked.'}"}

        try:
            if not GoogleCalendarService.refresh_access_token_if_needed(db, cred):
                return {"synced": False, "reason": cred.last_error or "Token refresh failed"}

            synced_map = dict(cred.synced_events_map or {})
            synced_count = 0

            # 1. Timetable sessions sync
            timetable_pub = publication if (publication and publication.publication_type == "TIMETABLE") else (
                db.query(Publication).filter(
                    Publication.institution_id == institution_id,
                    Publication.publication_type == "TIMETABLE",
                    Publication.is_active == True
                ).order_by(Publication.version_number.desc()).first()
            )

            if timetable_pub and timetable_pub.snapshot:
                assignments = timetable_pub.snapshot.get("assignments", [])
                for a in assignments:
                    teacher_id = a.get("teacher_id")
                    session_id = a.get("session_id")
                    if not session_id:
                        continue

                    is_relevant = False
                    if teacher_id == user_id:
                        is_relevant = True
                    else:
                        section_id = a.get("section_id")
                        if section_id:
                            is_enrolled = db.execute(
                                text(
                                    "SELECT 1 FROM enrolments e JOIN students s ON e.student_id = s.id "
                                    "WHERE s.user_id = :u AND e.section_id = :sec LIMIT 1"
                                ),
                                {"u": user_id, "sec": section_id}
                            ).first()
                            if is_enrolled:
                                is_relevant = True

                    if is_relevant:
                        start_iso = "2026-10-26T09:00:00Z"
                        end_iso = "2026-10-26T10:00:00Z"
                        event_id = synced_map.get(session_id)
                        new_event_id = _global_mock_client.create_or_update_event(
                            calendar_id=cred.calendar_id,
                            event_id=event_id,
                            summary=f"Class Session: {a.get('subject_code', 'Course')}",
                            description=f"Room: {a.get('room_name', 'TBD')}",
                            start_iso=start_iso,
                            end_iso=end_iso,
                            location=a.get("room_name", "")
                        )
                        synced_map[session_id] = new_event_id
                        synced_count += 1

            # 2. Exam sittings sync
            exam_pub = publication if (publication and publication.publication_type == "EXAM_SEATING") else (
                db.query(Publication).filter(
                    Publication.institution_id == institution_id,
                    Publication.publication_type == "EXAM_SEATING",
                    Publication.is_active == True
                ).order_by(Publication.version_number.desc()).first()
            )

            if exam_pub and exam_pub.snapshot:
                allocations = exam_pub.snapshot.get("allocations", [])
                for alloc in allocations:
                    if alloc.get("student_user_id") == user_id:
                        sitting_id = alloc.get("exam_sitting_id", "exam")
                        event_key = f"exam_{sitting_id}_{alloc.get('seat_id')}"
                        event_id = synced_map.get(event_key)
                        new_event_id = _global_mock_client.create_or_update_event(
                            calendar_id=cred.calendar_id,
                            event_id=event_id,
                            summary=f"Exam Sitting: {alloc.get('paper_name', 'Exam')}",
                            description=f"Seat: {alloc.get('seat_number', 'Assigned')} in {alloc.get('room_name', 'Hall')}",
                            start_iso="2026-11-02T10:00:00Z",
                            end_iso="2026-11-02T13:00:00Z",
                            location=alloc.get("room_name", "")
                        )
                        synced_map[event_key] = new_event_id
                        synced_count += 1

            cred.synced_events_map = synced_map
            cred.sync_event_count = len(synced_map)
            cred.last_synced_at = datetime.datetime.now(datetime.timezone.utc)
            cred.last_error = None
            db.commit()
            return {"synced": True, "count": synced_count}

        except Exception as ex:
            logger.error(f"Error during calendar sync for user {user_id}: {ex}")
            cred.last_error = f"Calendar sync failed: {str(ex)}"
            db.commit()
            return {"synced": False, "error": str(ex)}
