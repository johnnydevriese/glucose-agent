from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class MealStatus(str, Enum):
    FASTING = "fasting"
    PRANDIAL = "prandial"


class ReadingSource(str, Enum):
    USER = "user"
    AGENT = "agent"


class BloodSugarReading(BaseModel):
    glucose_level: float = Field(ge=30, le=600, description="Blood glucose in mg/dL")
    date: dt.date
    meal_status: MealStatus
    notes: Optional[str] = None
    source: ReadingSource = ReadingSource.USER


class InvalidReading(BaseModel):
    reason: str


class ReadingCandidate(BaseModel):
    glucose_level: Optional[float] = None
    date: Optional[dt.date] = None
    meal_status: Optional[MealStatus] = None
    notes: Optional[str] = None


class TrendInsight(BaseModel):
    summary: str
    average: Optional[float] = None
    delta: Optional[float] = None
    in_expected_range: Optional[bool] = None


class ReadingStats(BaseModel):
    total_readings: int = 0
    has_fasting: bool = False
    has_prandial: bool = False
    avg_fasting: Optional[float] = None
    avg_prandial: Optional[float] = None
    latest_fasting: Optional[BloodSugarReading] = None
    latest_prandial: Optional[BloodSugarReading] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class SessionState(BaseModel):
    session_id: str
    history: List[ChatMessage] = Field(default_factory=list)
    pending_reading: Optional[BloodSugarReading] = None


class MessageEvent(BaseModel):
    type: Literal["message"] = "message"
    message: str


class ReadingExtractedEvent(BaseModel):
    type: Literal["reading_extracted"] = "reading_extracted"
    reading: BloodSugarReading


class HistoryUpdateEvent(BaseModel):
    type: Literal["history_update"] = "history_update"
    readings: List[BloodSugarReading]


class StatsUpdateEvent(BaseModel):
    type: Literal["stats_update"] = "stats_update"
    stats: ReadingStats


WebSocketEvent = Union[
    MessageEvent,
    ReadingExtractedEvent,
    HistoryUpdateEvent,
    StatsUpdateEvent,
]


class WebSocketAction(BaseModel):
    action: str
    message: Optional[str] = None
    reading: Optional[BloodSugarReading] = None
    notes: Optional[str] = None
    session_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    llm_enabled: bool


class ErrorEvent(BaseModel):
    type: Literal["message"] = "message"
    message: str


class RouterResult(BaseModel):
    intent: Literal["log_reading", "trend_question", "education", "general_chat"]
    reasoning: str


JsonDict = Dict[str, Any]
