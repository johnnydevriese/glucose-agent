# backend/main.py
import asyncio
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel, Field

# Import libraries from the original code
import logfire
import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage, UsageLimits
from dotenv import load_dotenv
from pydantic_ai.models.gemini import GeminiModel

# Load environment variables
load_dotenv()

# Configure model
model = GeminiModel("gemini-1.5-flash")

# Configure logfire
logfire.configure(
    token=os.getenv("LOGFIRE_API_KEY"), send_to_logfire="if-token-present"
)


# Define the models
class MealStatus(str, Enum):
    """Status indicating whether reading was taken while fasting or after a meal."""

    FASTING = "fasting"
    PRANDIAL = "prandial"  # after meal


class BloodSugarReading(BaseModel):
    """Details of a blood sugar reading."""

    glucose_level: float = Field(
        ge=30, le=600, description="Blood glucose level in mg/dL"
    )
    date: datetime.date = Field(description="The date when the reading was taken")
    meal_status: MealStatus = Field(
        description="Whether the reading was taken while fasting or after a meal"
    )
    notes: Optional[str] = Field(
        default=None, description="Any additional notes about the reading"
    )


class InvalidReading(BaseModel):
    """When a valid blood sugar reading could not be extracted."""

    reason: str


@dataclass
class Deps:
    """Dependencies for the blood sugar agent."""

    today: datetime.date = datetime.date.today()
    previous_readings: List[BloodSugarReading] = None


# Main conversational agent to guide the user through recording blood sugar
conversation_agent = Agent[Deps, str](
    model,
    result_type=str,
    retries=2,
    system_prompt=(
        "You are a friendly and helpful diabetes management assistant named Glucose Buddy. "
        "Your job is to have natural conversations with users about their blood sugar readings. "
        "Be supportive, empathetic, and provide gentle encouragement. "
        "Ask follow-up questions about their day, diet, exercise, medication, or anything that might "
        "affect their readings. Personalize the conversation based on their history and trends. "
        "When appropriate, offer simple educational tips about diabetes management. "
        "Never be judgmental about high or low readings."
    ),
)


# Extraction agent for parsing blood sugar values from natural language
extraction_agent = Agent(
    model,
    result_type=BloodSugarReading | InvalidReading,  # type: ignore
    system_prompt=(
        "Extract blood sugar reading details from the user's natural language input. "
        "Blood sugar is measured in mg/dL (for US users). Normal values are typically "
        "between 70-100 mg/dL when fasting and less than 140 mg/dL two hours after meals. "
        "Identify: glucose level, date, and whether it was fasting or after meal (prandial). "
        "For dates, parse natural language like 'today', 'yesterday', '2 days ago', etc. "
        "If any information is missing, return InvalidReading with a reason."
    ),
)


@conversation_agent.tool
async def extract_blood_sugar_info(
    ctx: RunContext[Deps], user_input: str
) -> BloodSugarReading | InvalidReading:
    """Extract blood sugar information from user input."""
    result = await extraction_agent.run(user_input, usage=ctx.usage)
    if isinstance(result.data, BloodSugarReading):
        logfire.info("Extracted blood sugar reading: {reading}", reading=result.data)
    return result.data


@conversation_agent.tool
async def validate_blood_sugar(
    ctx: RunContext[Deps], reading: BloodSugarReading
) -> BloodSugarReading | InvalidReading:
    """Validate the blood sugar reading."""
    errors: list[str] = []

    if reading.glucose_level < 30 or reading.glucose_level > 600:
        errors.append(
            f"Blood sugar level {reading.glucose_level} mg/dL is outside typical meter range (30-600 mg/dL)"
        )

    if reading.date > ctx.deps.today:
        errors.append(
            f"Date cannot be in the future: {reading.date} > {ctx.deps.today}"
        )

    if errors:
        return InvalidReading(reason="\n".join(errors))
    else:
        return reading


# This function is used within the conversation agent
@conversation_agent.tool
async def analyze_trend(ctx: RunContext[Deps], new_reading: BloodSugarReading) -> str:
    """Analyze trends in blood sugar readings."""
    if not ctx.deps.previous_readings:
        return "This is your first recorded reading."

    readings = ctx.deps.previous_readings

    # Filter readings based on meal status for fair comparison
    similar_readings = [r for r in readings if r.meal_status == new_reading.meal_status]

    if not similar_readings:
        return f"This is your first {new_reading.meal_status.value} reading."

    # Calculate average
    avg = sum(r.glucose_level for r in similar_readings) / len(similar_readings)

    # Compare with the new reading
    if abs(new_reading.glucose_level - avg) < 10:
        return f"This reading is consistent with your average {new_reading.meal_status.value} level of {avg:.1f} mg/dL."
    elif new_reading.glucose_level > avg:
        return f"This reading is {new_reading.glucose_level - avg:.1f} mg/dL higher than your average {new_reading.meal_status.value} level of {avg:.1f} mg/dL."
    else:
        return f"This reading is {avg - new_reading.glucose_level:.1f} mg/dL lower than your average {new_reading.meal_status.value} level of {avg:.1f} mg/dL."


# Direct validation function that doesn't require RunContext
def validate_reading(
    reading: BloodSugarReading, today: datetime.date
) -> tuple[bool, str]:
    """Validate the blood sugar reading without requiring RunContext.
    Returns (is_valid, error_message)"""
    errors: list[str] = []

    if reading.glucose_level < 30 or reading.glucose_level > 600:
        errors.append(
            f"Blood sugar level {reading.glucose_level} mg/dL is outside typical meter range (30-600 mg/dL)"
        )

    if reading.date > today:
        errors.append(f"Date cannot be in the future: {reading.date} > {today}")

    if errors:
        return False, "\n".join(errors)
    else:
        return True, ""


# Database for storing readings
class BloodSugarDatabase:
    def __init__(self):
        self.readings: list[BloodSugarReading] = []

    def add_reading(self, reading: BloodSugarReading):
        self.readings.append(reading)
        return len(self.readings)

    def get_readings(self):
        return self.readings

    def get_statistics(self):
        """Calculate and return statistics about the readings."""
        if not self.readings:
            return {
                "total_readings": 0,
                "has_fasting": False,
                "has_prandial": False,
            }

        fasting_readings = [
            r for r in self.readings if r.meal_status == MealStatus.FASTING
        ]
        prandial_readings = [
            r for r in self.readings if r.meal_status == MealStatus.PRANDIAL
        ]

        stats = {
            "total_readings": len(self.readings),
            "has_fasting": len(fasting_readings) > 0,
            "has_prandial": len(prandial_readings) > 0,
        }

        if fasting_readings:
            avg_fasting = sum(r.glucose_level for r in fasting_readings) / len(
                fasting_readings
            )
            stats["avg_fasting"] = round(avg_fasting, 1)

        if prandial_readings:
            avg_prandial = sum(r.glucose_level for r in prandial_readings) / len(
                prandial_readings
            )
            stats["avg_prandial"] = round(avg_prandial, 1)

        return stats


# FastAPI application
app = FastAPI()

# Add CORS middleware to allow requests from SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # SvelteKit dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.message_histories: Dict[WebSocket, List[ModelMessage]] = {}
        self.db = BloodSugarDatabase()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.message_histories[websocket] = []

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.message_histories:
            del self.message_histories[websocket]

    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(json.dumps({"type": "message", "message": message}))

    async def send_reading_extracted(
        self, websocket: WebSocket, reading: BloodSugarReading
    ):
        # Convert date to string for JSON serialization
        reading_dict = reading.dict()
        reading_dict["date"] = str(reading_dict["date"])

        await websocket.send_text(
            json.dumps({"type": "reading_extracted", "reading": reading_dict})
        )

    async def send_history_update(self, websocket: WebSocket):
        readings = self.db.get_readings()
        readings_list = []

        for reading in readings:
            reading_dict = reading.dict()
            reading_dict["date"] = str(reading_dict["date"])
            readings_list.append(reading_dict)

        await websocket.send_text(
            json.dumps({"type": "history_update", "readings": readings_list})
        )

    async def send_stats_update(self, websocket: WebSocket):
        stats = self.db.get_statistics()
        await websocket.send_text(json.dumps({"type": "stats_update", "stats": stats}))


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        # Send welcome message when a user connects
        await manager.send_message(
            websocket,
            "Hi there! How can I help you with tracking your blood sugar today?",
        )

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["action"] == "message":
                user_message = message_data["message"]

                # Set up dependencies for the conversation agent
                deps = Deps(
                    today=datetime.date.today(),
                    previous_readings=manager.db.get_readings(),
                )

                usage = Usage()
                usage_limits = UsageLimits(request_limit=15)

                # First, try to extract a reading from the message
                extraction_result = await extraction_agent.run(
                    user_message, usage=usage, usage_limits=usage_limits
                )

                if isinstance(extraction_result.data, BloodSugarReading):
                    # Reading extracted successfully
                    # Perform validation directly without using RunContext
                    reading = extraction_result.data
                    errors = []

                    if reading.glucose_level < 30 or reading.glucose_level > 600:
                        errors.append(
                            f"Blood sugar level {reading.glucose_level} mg/dL is outside typical meter range (30-600 mg/dL)"
                        )

                    if reading.date > deps.today:
                        errors.append(
                            f"Date cannot be in the future: {reading.date} > {deps.today}"
                        )

                    if errors:
                        await manager.send_message(
                            websocket,
                            f"I couldn't validate your reading: {'; '.join(errors)}",
                        )
                    else:
                        # Reading is valid, send for confirmation
                        await manager.send_reading_extracted(websocket, reading)
                else:
                    # No reading extracted, continue with conversation
                    result = await conversation_agent.run(
                        user_message,
                        deps=deps,
                        usage=usage,
                        message_history=manager.message_histories.get(websocket, []),
                        usage_limits=usage_limits,
                    )

                    # Update message history
                    manager.message_histories[websocket] = result.all_messages()

                    # Send response
                    await manager.send_message(websocket, result.data)

            elif message_data["action"] == "confirm_reading":
                # Get the reading from the message
                reading_data = message_data["reading"]
                notes = message_data.get("notes", "")

                # Create a BloodSugarReading object
                reading = BloodSugarReading(
                    glucose_level=reading_data["glucose_level"],
                    date=datetime.date.fromisoformat(reading_data["date"]),
                    meal_status=reading_data["meal_status"],
                    notes=notes if notes else None,
                )

                # Add the reading to the database
                manager.db.add_reading(reading)

                # Run trend analysis directly instead of using RunContext
                readings = manager.db.get_readings()

                # Get trend analysis
                trend_analysis = ""

                if len(readings) <= 1:
                    trend_analysis = "This is your first recorded reading."
                else:
                    # Filter readings based on meal status for fair comparison
                    previous_readings = readings[:-1]  # Exclude the just-added reading
                    similar_readings = [
                        r
                        for r in previous_readings
                        if r.meal_status == reading.meal_status
                    ]

                    if not similar_readings:
                        trend_analysis = (
                            f"This is your first {reading.meal_status.value} reading."
                        )
                    else:
                        # Calculate average
                        avg = sum(r.glucose_level for r in similar_readings) / len(
                            similar_readings
                        )

                        # Compare with the new reading
                        if abs(reading.glucose_level - avg) < 10:
                            trend_analysis = f"This reading is consistent with your average {reading.meal_status.value} level of {avg:.1f} mg/dL."
                        elif reading.glucose_level > avg:
                            trend_analysis = f"This reading is {reading.glucose_level - avg:.1f} mg/dL higher than your average {reading.meal_status.value} level of {avg:.1f} mg/dL."
                        else:
                            trend_analysis = f"This reading is {avg - reading.glucose_level:.1f} mg/dL lower than your average {reading.meal_status.value} level of {avg:.1f} mg/dL."

                # Send response and trend analysis
                await manager.send_message(
                    websocket,
                    f"Great! I've saved your reading. {trend_analysis}\n\nDo you have any other readings to share or questions about your blood sugar?",
                )

            elif message_data["action"] == "get_history":
                # Send history update
                await manager.send_history_update(websocket)

            elif message_data["action"] == "get_stats":
                # Send stats update
                await manager.send_stats_update(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
