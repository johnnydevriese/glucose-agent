# backend/main.py
import datetime
from typing import List, Optional

import logfire
import os
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.usage import Usage, UsageLimits
from dotenv import load_dotenv

load_dotenv()

# Configure Logfire
logfire.configure(
    token=os.getenv("LOGFIRE_API_KEY"), send_to_logfire="if-token-present"
)

app = FastAPI(title="Glucose Buddy API")

# # Enable CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:5173"],  # SvelteKit default dev server
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Enable CORS - Updated configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # SvelteKit default dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,  # Caching preflight requests for 24 hours
)


# Models
class MealStatus(str, Enum):
    """Status indicating whether reading was taken while fasting or after a meal."""

    FASTING = "fasting"
    PRANDIAL = "prandial"  # after meal


class BloodSugarReading(BaseModel):
    """Details of a blood sugar reading."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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


class ChatMessage(BaseModel):
    """A message in the chat."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for a chat interaction."""

    message: str
    session_id: str


class ChatResponse(BaseModel):
    """Response from a chat interaction."""

    response: str
    extracted_reading: Optional[BloodSugarReading] = None
    needs_confirmation: bool = False


class ConfirmReadingRequest(BaseModel):
    """Request to confirm a reading."""

    session_id: str
    reading_id: str
    confirm: bool


class ReadingStats(BaseModel):
    """Statistics about blood sugar readings."""

    average_fasting: Optional[float] = None
    average_prandial: Optional[float] = None
    total_readings: int


# In-memory database
class Database:
    def __init__(self):
        self.readings: dict[str, list[BloodSugarReading]] = {}
        self.message_history: dict[str, list[ModelMessage]] = {}
        self.pending_readings: dict[str, BloodSugarReading] = {}

    def get_readings(self, user_id: str) -> list[BloodSugarReading]:
        return self.readings.get(user_id, [])

    def add_reading(self, user_id: str, reading: BloodSugarReading) -> str:
        if user_id not in self.readings:
            self.readings[user_id] = []
        self.readings[user_id].append(reading)
        return reading.id

    def get_message_history(self, session_id: str) -> list[ModelMessage]:
        return self.message_history.get(session_id, [])

    def set_message_history(self, session_id: str, history: list[ModelMessage]):
        self.message_history[session_id] = history

    def set_pending_reading(self, session_id: str, reading: BloodSugarReading):
        self.pending_readings[session_id] = reading

    def get_pending_reading(self, session_id: str) -> Optional[BloodSugarReading]:
        return self.pending_readings.get(session_id)

    def clear_pending_reading(self, session_id: str):
        if session_id in self.pending_readings:
            del self.pending_readings[session_id]


# Initialize database
db = Database()


# Initialize agents
class Deps:
    """Dependencies for the blood sugar agent."""

    def __init__(
        self, today: datetime.date, previous_readings: List[BloodSugarReading]
    ):
        self.today = today
        self.previous_readings = previous_readings


# Main conversational agent
conversation_agent = Agent[Deps, str](
    "gemini-1.5-flash",
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

# Extraction agent
extraction_agent = Agent(
    "gemini-1.5-flash",
    result_type=BloodSugarReading | InvalidReading,  # type: ignore
    system_prompt=(
        "Extract blood sugar reading details from the user's natural language input. "
        "Blood sugar is measured in mg/dL (for US users). Normal values are typically "
        "between 70-100 mg/dL when fasting and less than 140 mg/dL two hours after meals. "
        "Identify: glucose level, date, and whether it was fasting or after meal (prandial). "
        "If any information is missing, return InvalidReading with a reason."
    ),
)


# Agent tools
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


# Usage limits
usage_limits = UsageLimits(request_limit=15)


# API Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Glucose Buddy API"}


@app.middleware("http")
async def handle_options(request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=200)
    return await call_next(request)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_id = request.session_id
    message = request.message

    # Check for exit command
    if message.lower() in ("exit", "quit", "bye"):
        return ChatResponse(
            response="Take care! Remember to check your blood sugar regularly."
        )

    # Process the conversation
    deps = Deps(
        today=datetime.date.today(),
        previous_readings=db.get_readings(user_id),
    )

    usage = Usage()
    message_history = db.get_message_history(request.session_id)

    result = await conversation_agent.run(
        message,
        deps=deps,
        usage=usage,
        message_history=message_history,
        usage_limits=usage_limits,
    )

    # Save updated message history
    db.set_message_history(request.session_id, result.all_messages())

    # Try to extract a reading
    pending_reading = db.get_pending_reading(request.session_id)
    if not pending_reading:
        extracted = await extraction_agent.run(message, usage=usage)

        if isinstance(extracted.data, BloodSugarReading):
            db.set_pending_reading(request.session_id, extracted.data)
            return ChatResponse(
                response=f"I see you've shared a reading of {extracted.data.glucose_level} mg/dL "
                f"({extracted.data.meal_status.value}) on {extracted.data.date}. "
                f"Is this correct?",
                extracted_reading=extracted.data,
                needs_confirmation=True,
            )

    return ChatResponse(response=result.data)


@app.post("/confirm-reading")
async def confirm_reading(request: ConfirmReadingRequest):
    user_id = request.session_id
    reading = db.get_pending_reading(request.session_id)

    if not reading:
        raise HTTPException(status_code=404, detail="No pending reading found")

    if request.confirm:
        # Save the reading
        db.add_reading(user_id, reading)
        db.clear_pending_reading(request.session_id)

        # Analyze trend
        deps = Deps(
            today=datetime.date.today(),
            previous_readings=db.get_readings(user_id),
        )
        usage = Usage()
        trend = await analyze_trend(RunContext(deps=deps, usage=usage), reading)

        return {"message": f"Great! I've saved your reading. {trend}"}
    else:
        db.clear_pending_reading(request.session_id)
        return {"message": "No problem, let's try again. What was your reading?"}


@app.get("/readings/{user_id}", response_model=List[BloodSugarReading])
async def get_readings(user_id: str):
    return db.get_readings(user_id)


@app.get("/stats/{user_id}", response_model=ReadingStats)
async def get_stats(user_id: str):
    readings = db.get_readings(user_id)

    if not readings:
        return ReadingStats(total_readings=0)

    fasting_readings = [r for r in readings if r.meal_status == MealStatus.FASTING]
    prandial_readings = [r for r in readings if r.meal_status == MealStatus.PRANDIAL]

    avg_fasting = None
    if fasting_readings:
        avg_fasting = sum(r.glucose_level for r in fasting_readings) / len(
            fasting_readings
        )

    avg_prandial = None
    if prandial_readings:
        avg_prandial = sum(r.glucose_level for r in prandial_readings) / len(
            prandial_readings
        )

    return ReadingStats(
        average_fasting=avg_fasting,
        average_prandial=avg_prandial,
        total_readings=len(readings),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
