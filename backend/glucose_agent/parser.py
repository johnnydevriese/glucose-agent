from __future__ import annotations

import datetime as dt
import re
from typing import List, Optional

try:
    import dateparser
except ImportError:  # pragma: no cover - optional in minimal environments
    dateparser = None

from .schemas import BloodSugarReading, InvalidReading, MealStatus, ReadingCandidate


MEAL_KEYWORDS = {
    MealStatus.FASTING: [
        "fasting",
        "before breakfast",
        "before eating",
        "empty stomach",
        "woke up",
        "this morning fasting",
    ],
    MealStatus.PRANDIAL: [
        "after breakfast",
        "after lunch",
        "after dinner",
        "post meal",
        "post-meal",
        "after meal",
        "after eating",
        "prandial",
    ],
}

DATE_PHRASES = [
    "today",
    "yesterday",
    "last night",
    "this morning",
    "this afternoon",
    "this evening",
    "two days ago",
    "3 days ago",
]


def extract_reading_from_text(
    text: str, today: dt.date
) -> Optional[BloodSugarReading]:
    candidate = extract_candidate_from_text(text, today)
    if not candidate.glucose_level:
        return None
    if not candidate.date or not candidate.meal_status:
        return None
    return BloodSugarReading(
        glucose_level=candidate.glucose_level,
        date=candidate.date,
        meal_status=candidate.meal_status,
        notes=candidate.notes,
    )


def extract_candidate_from_text(text: str, today: dt.date) -> ReadingCandidate:
    lowered = text.lower()
    glucose_level = _extract_glucose_value(text)
    parsed_date = _extract_date(text, today)
    meal_status = _extract_meal_status(lowered)

    notes = None
    if glucose_level is not None:
        notes = text.strip()

    return ReadingCandidate(
        glucose_level=glucose_level,
        date=parsed_date,
        meal_status=meal_status,
        notes=notes,
    )


def validate_candidate(
    candidate: ReadingCandidate, today: dt.date
) -> Optional[InvalidReading]:
    missing: List[str] = []
    if candidate.glucose_level is None:
        missing.append("glucose level")
    if candidate.date is None:
        missing.append("date")
    if candidate.meal_status is None:
        missing.append("meal status")
    if missing:
        return InvalidReading(reason="Missing " + ", ".join(missing) + ".")

    if candidate.glucose_level is not None and not 30 <= candidate.glucose_level <= 600:
        return InvalidReading(
            reason=(
                "Blood sugar must be within a realistic meter range "
                "between 30 and 600 mg/dL."
            )
        )
    if candidate.date and candidate.date > today:
        return InvalidReading(reason="Date cannot be in the future.")
    return None


def _extract_glucose_value(text: str) -> Optional[float]:
    patterns = [
        r"(\d{2,3}(?:\.\d+)?)\s*(?:mg/?dL|mg dl|mg)\b",
        r"(?:glucose|blood sugar|sugar|reading)\D{0,12}(\d{2,3}(?:\.\d+)?)\b",
        r"\b(?:was|is|at)\s+(\d{2,3}(?:\.\d+)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _extract_date(text: str, today: dt.date) -> Optional[dt.date]:
    lowered = text.lower()
    if "today" in lowered:
        return today
    if "yesterday" in lowered or "last night" in lowered:
        return today - dt.timedelta(days=1)
    relative_match = re.search(r"\b(\d+)\s+days?\s+ago\b", lowered)
    if relative_match:
        return today - dt.timedelta(days=int(relative_match.group(1)))

    candidates = [phrase for phrase in DATE_PHRASES if phrase in lowered]
    candidates.extend(re.findall(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", text))
    candidates.extend(
        re.findall(
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?\b",
            lowered,
        )
    )

    ordered = candidates + [text]
    for chunk in ordered:
        parsed = _parse_date_chunk(chunk, today)
        if parsed is not None:
            return parsed
    return None


def _extract_meal_status(lowered: str) -> Optional[MealStatus]:
    for status, keywords in MEAL_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return status

    if "breakfast" in lowered or "lunch" in lowered or "dinner" in lowered:
        return MealStatus.PRANDIAL
    if "morning" in lowered:
        return MealStatus.FASTING
    return None


def _parse_date_chunk(chunk: str, today: dt.date) -> Optional[dt.date]:
    if dateparser is not None:
        settings = {
            "RELATIVE_BASE": dt.datetime.combine(today, dt.time.min),
            "PREFER_DATES_FROM": "past",
        }
        parsed = dateparser.parse(chunk, settings=settings)
        if parsed:
            return parsed.date()

    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(chunk, fmt).date()
        except ValueError:
            continue

    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d", "%B %d"):
        try:
            parsed = dt.datetime.strptime(chunk.title(), fmt)
            if "%Y" not in fmt:
                return parsed.replace(year=today.year).date()
            return parsed.date()
        except ValueError:
            continue

    return None
