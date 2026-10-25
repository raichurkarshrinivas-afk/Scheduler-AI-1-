import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class SSEEvent:
    def __init__(self, event_id: int, institution_id: str, event_type: str, payload: Dict[str, Any], target_user_id: Optional[str] = None):
        self.id = event_id
        self.institution_id = institution_id
        self.event_type = event_type
        self.payload = payload
        self.target_user_id = target_user_id
        self.created_at = time.time()

    def to_sse_message(self) -> str:
        data_str = json.dumps({
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        })
        return f"id: {self.id}\nevent: {self.event_type}\ndata: {data_str}\n\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at,
        }


class SSEManager:
    _instance = None

    def __init__(self, max_buffer_size: int = 500):
        self._max_buffer_size = max_buffer_size
        self._next_id: int = 1
        self._event_buffer: List[SSEEvent] = []
        self._subscribers: Dict[Tuple[str, str], Set[asyncio.Queue]] = {}

    @classmethod
    def get_instance(cls) -> "SSEManager":
        if cls._instance is None:
            cls._instance = SSEManager()
        return cls._instance

    def _next_event_id(self) -> int:
        eid = self._next_id
        self._next_id += 1
        return eid

    def publish_event_sync(
        self,
        institution_id: str,
        event_type: str,
        payload: Dict[str, Any],
        target_user_id: Optional[str] = None
    ) -> SSEEvent:
        event = SSEEvent(
            event_id=self._next_event_id(),
            institution_id=institution_id,
            event_type=event_type,
            payload=payload,
            target_user_id=target_user_id
        )
        self._event_buffer.append(event)
        if len(self._event_buffer) > self._max_buffer_size:
            self._event_buffer.pop(0)

        for (sub_inst, sub_user), queues in list(self._subscribers.items()):
            if sub_inst != institution_id:
                continue
            if target_user_id is None or target_user_id == sub_user:
                for q in list(queues):
                    try:
                        q.put_nowait(event)
                    except Exception:
                        pass
        return event

    async def publish_event(
        self,
        institution_id: str,
        event_type: str,
        payload: Dict[str, Any],
        target_user_id: Optional[str] = None
    ) -> SSEEvent:
        return self.publish_event_sync(institution_id, event_type, payload, target_user_id)

    async def register_subscriber(self, institution_id: str, user_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        key = (institution_id, user_id)
        if key not in self._subscribers:
            self._subscribers[key] = set()
        self._subscribers[key].add(q)
        return q

    async def unregister_subscriber(self, institution_id: str, user_id: str, q: asyncio.Queue):
        key = (institution_id, user_id)
        if key in self._subscribers:
            self._subscribers[key].discard(q)
            if not self._subscribers[key]:
                del self._subscribers[key]

    def get_events_since(
        self,
        institution_id: str,
        user_id: str,
        since_id: int
    ) -> List[Dict[str, Any]]:
        results = []
        for ev in self._event_buffer:
            if ev.id > since_id and ev.institution_id == institution_id:
                if ev.target_user_id is None or ev.target_user_id == user_id:
                    results.append(ev.to_dict())
        return results

    def get_missed_sse_messages(
        self,
        institution_id: str,
        user_id: str,
        last_event_id: int
    ) -> List[str]:
        messages = []
        for ev in self._event_buffer:
            if ev.id > last_event_id and ev.institution_id == institution_id:
                if ev.target_user_id is None or ev.target_user_id == user_id:
                    messages.append(ev.to_sse_message())
        return messages


sse_manager = SSEManager.get_instance()
