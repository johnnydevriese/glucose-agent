from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List

from .schemas import BloodSugarReading, ChatMessage, SessionState


class GlucoseRepository:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self._lock = Lock()
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._write({"readings": [], "sessions": {}})

    def list_readings(self) -> List[BloodSugarReading]:
        payload = self._read()
        return [BloodSugarReading.model_validate(item) for item in payload["readings"]]

    def save_reading(self, reading: BloodSugarReading) -> int:
        with self._lock:
            payload = self._read()
            payload["readings"].append(reading.model_dump(mode="json"))
            self._write(payload)
            return len(payload["readings"])

    def get_session(self, session_id: str) -> SessionState:
        payload = self._read()
        raw = payload["sessions"].get(session_id)
        if raw is None:
            return SessionState(session_id=session_id)
        return SessionState.model_validate(raw)

    def save_session(self, session: SessionState) -> None:
        with self._lock:
            payload = self._read()
            payload["sessions"][session.session_id] = session.model_dump(mode="json")
            self._write(payload)

    def append_message(self, session_id: str, role: str, content: str) -> SessionState:
        session = self.get_session(session_id)
        session.history.append(ChatMessage(role=role, content=content))
        self.save_session(session)
        return session

    def set_pending_reading(
        self, session_id: str, reading: BloodSugarReading | None
    ) -> SessionState:
        session = self.get_session(session_id)
        session.pending_reading = reading
        self.save_session(session)
        return session

    def _read(self) -> Dict:
        if not self.data_file.exists():
            return {"readings": [], "sessions": {}}
        return json.loads(self.data_file.read_text() or '{"readings": [], "sessions": {}}')

    def _write(self, payload: Dict) -> None:
        self.data_file.write_text(json.dumps(payload, indent=2))

