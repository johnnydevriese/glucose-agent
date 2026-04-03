from __future__ import annotations

from typing import List

from .schemas import BloodSugarReading, MealStatus, ReadingStats, TrendInsight


def build_stats(readings: List[BloodSugarReading]) -> ReadingStats:
    if not readings:
        return ReadingStats()

    fasting = [reading for reading in readings if reading.meal_status == MealStatus.FASTING]
    prandial = [
        reading for reading in readings if reading.meal_status == MealStatus.PRANDIAL
    ]

    return ReadingStats(
        total_readings=len(readings),
        has_fasting=bool(fasting),
        has_prandial=bool(prandial),
        avg_fasting=round(sum(r.glucose_level for r in fasting) / len(fasting), 1)
        if fasting
        else None,
        avg_prandial=round(sum(r.glucose_level for r in prandial) / len(prandial), 1)
        if prandial
        else None,
        latest_fasting=fasting[-1] if fasting else None,
        latest_prandial=prandial[-1] if prandial else None,
    )


def build_trend_insight(
    readings: List[BloodSugarReading], new_reading: BloodSugarReading
) -> TrendInsight:
    comparable = [
        reading
        for reading in readings
        if reading.meal_status == new_reading.meal_status and reading != new_reading
    ]
    if not comparable:
        return TrendInsight(
            summary="This is your first recorded reading in that category.",
            in_expected_range=_in_expected_range(new_reading),
        )

    average = sum(reading.glucose_level for reading in comparable) / len(comparable)
    delta = round(new_reading.glucose_level - average, 1)

    if abs(delta) < 10:
        summary = (
            "This reading is close to your usual "
            f"{new_reading.meal_status.value} pattern."
        )
    elif delta > 0:
        summary = (
            f"This is {delta:.1f} mg/dL above your average "
            f"{new_reading.meal_status.value} reading."
        )
    else:
        summary = (
            f"This is {abs(delta):.1f} mg/dL below your average "
            f"{new_reading.meal_status.value} reading."
        )

    return TrendInsight(
        summary=summary,
        average=round(average, 1),
        delta=delta,
        in_expected_range=_in_expected_range(new_reading),
    )


def _in_expected_range(reading: BloodSugarReading) -> bool:
    if reading.meal_status == MealStatus.FASTING:
        return 70 <= reading.glucose_level <= 100
    return reading.glucose_level < 140

