from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

try:
    import logfire
except ImportError:  # pragma: no cover - optional dependency in lightweight dev envs
    logfire = None
from pydantic_ai import Agent

from .analytics import build_stats
from .parser import extract_candidate_from_text, validate_candidate
from .schemas import (
    BloodSugarReading,
    ChatMessage,
    InvalidReading,
    MealStatus,
    ReadingCandidate,
    RouterResult,
)
from .settings import AppSettings


@dataclass
class AgentDeps:
    today: dt.date
    readings: List[BloodSugarReading]


def configure_observability(settings: AppSettings) -> None:
    if logfire is None:
        return
    logfire.configure(
        token=settings.logfire_token or None,
        send_to_logfire="if-token-present",
        service_name="glucose-buddy",
    )


def build_agents(settings: AppSettings) -> "AgentSuite":
    if not settings.llm_enabled:
        return AgentSuite(settings=settings)

    model = "google-gla:{name}".format(name=settings.google_model)

    router = Agent(
        model,
        output_type=RouterResult,
        instructions=(
            "Route the user request to one of four intents: "
            "log_reading, trend_question, education, or general_chat. "
            "Choose log_reading if the message appears to include a glucose value or "
            "a request to record/update a reading."
        ),
    )

    extraction = Agent(
        model,
        output_type=ReadingCandidate,
        instructions=(
            "Extract a glucose reading candidate from the user's message. "
            "Return glucose_level, date, and meal_status when present. "
            "Use today's date from context for relative dates like today or yesterday. "
            "Do not invent missing values."
        ),
    )

    conversation = Agent(
        model,
        deps_type=AgentDeps,
        output_type=str,
        instructions=(
            "You are Glucose Buddy, a careful diabetes logging assistant. "
            "You help users record glucose readings, explain trends in plain language, "
            "and answer general educational questions. "
            "You are not a doctor and should not prescribe medication changes. "
            "When discussing readings, be concise, supportive, and specific."
        ),
    )

    return AgentSuite(
        settings=settings,
        router_agent=router,
        extraction_agent=extraction,
        conversation_agent=conversation,
    )


class AgentSuite:
    def __init__(
        self,
        settings: AppSettings,
        router_agent: Optional[Agent] = None,
        extraction_agent: Optional[Agent] = None,
        conversation_agent: Optional[Agent] = None,
    ):
        self.settings = settings
        self.router_agent = router_agent
        self.extraction_agent = extraction_agent
        self.conversation_agent = conversation_agent

    async def classify_intent(
        self, text: str, today: dt.date, readings: List[BloodSugarReading]
    ) -> RouterResult:
        parsed = extract_candidate_from_text(text, today)
        if parsed.glucose_level is not None:
            return RouterResult(
                intent="log_reading",
                reasoning="Detected a likely glucose measurement in the message.",
            )
        lowered = text.lower()
        if any(word in lowered for word in ["trend", "average", "history", "compare"]):
            return RouterResult(
                intent="trend_question",
                reasoning="The user is asking about prior readings or summary patterns.",
            )
        if any(word in lowered for word in ["normal", "target", "what should", "range"]):
            return RouterResult(
                intent="education",
                reasoning="The user is asking an educational glucose question.",
            )
        if self.router_agent is None:
            return RouterResult(
                intent="general_chat",
                reasoning="Using deterministic fallback classification.",
            )
        result = await self.router_agent.run(text)
        return result.output

    async def extract_reading(
        self, text: str, today: dt.date
    ) -> ReadingCandidate:
        parsed = extract_candidate_from_text(text, today)
        issue = validate_candidate(parsed, today)
        if issue is None:
            return parsed

        if self.extraction_agent is None:
            return parsed

        result = await self.extraction_agent.run(
            "today is {today}\nmessage: {text}".format(today=today.isoformat(), text=text)
        )
        candidate = result.output
        if candidate.notes is None:
            candidate.notes = text.strip()
        return candidate

    async def reply(
        self,
        user_message: str,
        today: dt.date,
        readings: List[BloodSugarReading],
        history: List[ChatMessage],
    ) -> str:
        if self.conversation_agent is None:
            return self._fallback_reply(user_message, readings)

        prompt = user_message
        if readings:
            stats = build_stats(readings)
            prompt = (
                f"User message: {user_message}\n"
                f"Stats: total={stats.total_readings}, "
                f"avg_fasting={stats.avg_fasting}, avg_prandial={stats.avg_prandial}"
            )

        result = await self.conversation_agent.run(
            prompt,
            deps=AgentDeps(today=today, readings=readings),
            message_history=[],
        )
        return result.output

    def _fallback_reply(
        self, user_message: str, readings: List[BloodSugarReading]
    ) -> str:
        lowered = user_message.lower()
        if "normal" in lowered or "range" in lowered:
            return (
                "Typical fasting glucose is about 70-100 mg/dL, and many after-meal "
                "targets are under 140 mg/dL two hours after eating."
            )
        if readings:
            stats = build_stats(readings)
            return (
                f"You have {stats.total_readings} readings recorded. "
                "Share a reading like '118 today fasting' and I can log it."
            )
        return (
            "Share a reading like 'My blood sugar was 118 today fasting' or ask about "
            "your recent trends."
        )
