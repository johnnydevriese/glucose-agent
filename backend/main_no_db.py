# simple_backend.py
import datetime
from typing import Optional, List
from enum import Enum

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import Usage

load_dotenv()

app = FastAPI(title="Simple Glucose Buddy API")

# Enable CORS with comprehensive configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# Simple models
class MealStatus(str, Enum):
    FASTING = "fasting"
    PRANDIAL = "prandial"


class BloodSugarReading(BaseModel):
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
    reason: str


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    extracted_reading: Optional[BloodSugarReading] = None
    needs_confirmation: bool = False


# Initialize the main conversation agent
conversation_agent = Agent[dict, str](
    "gemini-1.5-flash",
    result_type=str,
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

# Initialize the extraction agent
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


# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Simple Glucose Buddy API"}


@app.options("/chat")
async def options_chat():
    return {}  # Empty response for OPTIONS requests


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Process the conversation
        usage = Usage()
        result = await conversation_agent.run(
            request.message, deps={}, usage=usage  # Empty dependencies
        )

        # Try to extract a reading
        try:
            print(f"Attempting to extract reading from: {request.message}")
            extracted = await extraction_agent.run(request.message, usage=usage)

            if isinstance(extracted.data, BloodSugarReading):
                print(f"Successfully extracted reading: {extracted.data}")
                # Return with the extracted reading
                return ChatResponse(
                    response=f"I see you've shared a reading of {extracted.data.glucose_level} mg/dL "
                    f"({extracted.data.meal_status.value}) on {extracted.data.date}. "
                    f"Is this correct?",
                    extracted_reading=extracted.data,
                    needs_confirmation=True,
                )
            else:
                print(f"Extraction returned InvalidReading: {extracted.data.reason}")
        except Exception as extract_error:
            # If extraction fails, just continue with the conversation
            print(f"Error during extraction: {str(extract_error)}")

        # If no reading was extracted or extraction failed, just return the conversation response
        return ChatResponse(response=result.data)
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("simple_backend:app", host="0.0.0.0", port=8000, reload=True)
