from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from threading import Lock
from typing import Dict, List

from .schemas import BloodSugarReading, ChatMessage, MealStatus, SessionState


class GlucoseRepository:
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self._lock = Lock()
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self._write(
                {
                    "readings": [reading.model_dump(mode="json") for reading in _demo_readings()],
                    "sessions": {},
                }
            )

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


def _demo_readings() -> List[BloodSugarReading]:
    today = dt.date.today()
    return [
        BloodSugarReading(
            glucose_level=101,
            date=today - dt.timedelta(days=10),
            meal_status=MealStatus.FASTING,
            notes="Solid baseline before breakfast.",
        ),
        BloodSugarReading(
            glucose_level=134,
            date=today - dt.timedelta(days=9),
            meal_status=MealStatus.PRANDIAL,
            notes="Two hours after oatmeal and fruit.",
        ),
        BloodSugarReading(
            glucose_level=96,
            date=today - dt.timedelta(days=7),
            meal_status=MealStatus.FASTING,
            notes="Felt rested and hydrated.",
        ),
        BloodSugarReading(
            glucose_level=142,
            date=today - dt.timedelta(days=6),
            meal_status=MealStatus.PRANDIAL,
            notes="After lunch meeting and a larger meal.",
        ),
        BloodSugarReading(
            glucose_level=104,
            date=today - dt.timedelta(days=4),
            meal_status=MealStatus.FASTING,
            notes="Slightly elevated after a late dinner.",
        ),
        BloodSugarReading(
            glucose_level=128,
            date=today - dt.timedelta(days=3),
            meal_status=MealStatus.PRANDIAL,
            notes="Steadier after a walk.",
        ),
        BloodSugarReading(
            glucose_level=99,
            date=today - dt.timedelta(days=1),
            meal_status=MealStatus.FASTING,
            notes="Back in the usual range.",
        ),
    ]
