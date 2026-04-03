from __future__ import annotations

import datetime as dt
from typing import List
from uuid import uuid4

from .agents import AgentSuite
from .analytics import build_stats, build_trend_insight
from .parser import validate_candidate
from .repository import GlucoseRepository
from .schemas import (
    BloodSugarReading,
    HistoryUpdateEvent,
    InvalidReading,
    MessageEvent,
    ReadingExtractedEvent,
    SessionState,
    StatsUpdateEvent,
    WebSocketEvent,
)


class GlucoseService:
    def __init__(self, repository: GlucoseRepository, agents: AgentSuite):
        self.repository = repository
        self.agents = agents

    def create_session_id(self) -> str:
        return str(uuid4())

    def get_session(self, session_id: str) -> SessionState:
        return self.repository.get_session(session_id)

    def get_history_event(self) -> HistoryUpdateEvent:
        return HistoryUpdateEvent(readings=self.repository.list_readings())

    def get_stats_event(self) -> StatsUpdateEvent:
        return StatsUpdateEvent(stats=build_stats(self.repository.list_readings()))

    async def welcome_events(self) -> List[WebSocketEvent]:
        return [
            MessageEvent(
                message=(
                    "Hi. I can log glucose readings, explain trends, and answer "
                    "basic blood sugar questions. Try '118 today fasting'."
                )
            )
        ]

    async def handle_message(
        self, session_id: str, text: str
    ) -> List[WebSocketEvent]:
        today = dt.date.today()
        readings = self.repository.list_readings()
        session = self.repository.append_message(session_id, "user", text)

        intent = await self.agents.classify_intent(text, today, readings)
        if intent.intent == "log_reading":
            candidate = await self.agents.extract_reading(text, today)
            issue = validate_candidate(candidate, today)
            if issue is None:
                reading = BloodSugarReading(
                    glucose_level=float(candidate.glucose_level),
                    date=candidate.date,
                    meal_status=candidate.meal_status,
                    notes=candidate.notes,
                )
                self.repository.set_pending_reading(session_id, reading)
                assistant_text = (
                    f"I extracted {reading.glucose_level:.0f} mg/dL for "
                    f"{reading.date.isoformat()} as {reading.meal_status.value}. "
                    "Please confirm it below."
                )
                self.repository.append_message(session_id, "assistant", assistant_text)
                return [
                    ReadingExtractedEvent(reading=reading),
                    MessageEvent(message=assistant_text),
                ]
            return [MessageEvent(message=self._format_invalid_reading(issue))]

        reply = await self.agents.reply(text, today, readings, session.history)
        self.repository.append_message(session_id, "assistant", reply)

        events: List[WebSocketEvent] = [MessageEvent(message=reply)]
        if intent.intent == "trend_question":
            events.append(self.get_stats_event())
        return events

    async def confirm_reading(
        self, session_id: str, reading: BloodSugarReading, notes: str = ""
    ) -> List[WebSocketEvent]:
        stored = reading.model_copy()
        if notes.strip():
            stored.notes = notes.strip()

        self.repository.save_reading(stored)
        self.repository.set_pending_reading(session_id, None)

        updated = self.repository.list_readings()
        insight = build_trend_insight(updated, stored)
        follow_up = (
            "Saved your reading. "
            f"{insight.summary} "
            + self._range_message(stored)
        ).strip()

        self.repository.append_message(session_id, "assistant", follow_up)
        return [
            MessageEvent(message=follow_up),
            self.get_history_event(),
            self.get_stats_event(),
        ]

    def _format_invalid_reading(self, issue: InvalidReading) -> str:
        return (
            "I couldn’t log that yet. "
            f"{issue.reason} "
            "Include the value, when it was taken, and whether it was fasting or after a meal."
        )

    def _range_message(self, reading: BloodSugarReading) -> str:
        if reading.meal_status.value == "fasting":
            target = "Typical fasting targets are often around 70-100 mg/dL."
        else:
            target = "Many after-meal targets are under 140 mg/dL two hours after eating."
        return target

