# minimal_backend.py
import datetime
import sqlite3
import uuid
import logging
from typing import Optional, List
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.usage import Usage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("glucose-buddy")

load_dotenv()

app = FastAPI(title="Minimal Glucose Buddy API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class MealStatus(str, Enum):
    FASTING = "fasting"
    PRANDIAL = "prandial"


class BloodSugarReading(BaseModel):
    id: Optional[str] = None
    glucose_level: float
    date: datetime.date
    meal_status: MealStatus
    notes: Optional[str] = None


class InvalidReading(BaseModel):
    reason: str


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    extracted_reading: Optional[BloodSugarReading] = None
    needs_confirmation: bool = False


class ConfirmReadingRequest(BaseModel):
    session_id: str
    reading_id: str
    confirm: bool


# Initialize LLM agents
conversation_agent = Agent[dict, str](
    "gemini-1.5-flash",
    result_type=str,
    system_prompt=(
        "You are a friendly and helpful diabetes management assistant named Glucose Buddy. "
        "Your job is to have natural conversations with users about their blood sugar readings. "
        "Be supportive, empathetic, and provide gentle encouragement."
    ),
)

extraction_agent = Agent(
    "gemini-1.5-flash",
    result_type=BloodSugarReading | InvalidReading,
    system_prompt=(
        "Extract blood sugar reading details from the user's natural language input. "
        "Blood sugar is measured in mg/dL (for US users). Normal values are typically "
        "between 70-100 mg/dL when fasting and less than 140 mg/dL two hours after meals. "
        "Identify: 1) glucose level, 2) whether it was fasting or after meal (prandial), and 3) date if mentioned. "
        "If the user mentions a specific date (like 'yesterday', 'last Monday', 'May 15'), extract that date. "
        "If no date is mentioned, use today's date. "
        "If the glucose level cannot be extracted, return InvalidReading with a reason."
    ),
)


# Database setup
def init_db():
    conn = sqlite3.connect("glucose_buddy.db")
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS readings (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        glucose_level REAL NOT NULL,
        date TEXT NOT NULL,
        meal_status TEXT NOT NULL,
        notes TEXT,
        confirmed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    conn.commit()
    conn.close()


# Initialize database
init_db()


# Create fresh connection for each request
def get_db_connection():
    conn = sqlite3.connect("glucose_buddy.db")
    conn.row_factory = sqlite3.Row
    return conn


# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to Minimal Glucose Buddy API"}


@app.post("/chat")
async def chat(request: ChatRequest):
    logger.info(f"Received chat request from session: {request.session_id}")
    try:
        # Create a new database connection for this request
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Ensure user exists
            cursor.execute(
                "INSERT OR IGNORE INTO users (session_id) VALUES (?)",
                (request.session_id,),
            )
            conn.commit()
            logger.info(f"User session {request.session_id} saved or already exists")

            # Get LLM response
            logger.info(f"Sending message to LLM: {request.message}")
            usage = Usage()
            result = await conversation_agent.run(request.message, deps={}, usage=usage)
            logger.info("LLM response received")

            # Try to extract a reading
            try:
                logger.info("Attempting to extract blood sugar reading")
                extracted = await extraction_agent.run(request.message, usage=usage)

                if isinstance(extracted.data, BloodSugarReading):
                    logger.info(f"Successfully extracted reading: {extracted.data}")

                    # Generate ID for reading
                    reading_id = str(uuid.uuid4())

                    # Use the extracted date if available, otherwise use today's date
                    reading_date = extracted.data.date
                    # If the date seems to be in the future or far in the past (more than 90 days), use today's date
                    today = datetime.date.today()
                    if reading_date > today or (today - reading_date).days > 90:
                        logger.info(
                            f"Invalid date detected: {reading_date}, using today's date instead"
                        )
                        reading_date = today

                    # Save to database as pending
                    try:
                        cursor.execute(
                            "INSERT INTO readings (id, session_id, glucose_level, date, meal_status, notes) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                reading_id,
                                request.session_id,
                                extracted.data.glucose_level,
                                reading_date.isoformat(),  # Use the appropriate date
                                extracted.data.meal_status,
                                extracted.data.notes,
                            ),
                        )
                        conn.commit()
                        logger.info(
                            f"Saved pending reading to database with ID: {reading_id}"
                        )
                    except Exception as e:
                        logger.error(f"Database error saving reading: {str(e)}")

                    # Create response with reading
                    extracted_with_id = BloodSugarReading(
                        id=reading_id,
                        glucose_level=extracted.data.glucose_level,
                        date=reading_date,  # Use the appropriate date
                        meal_status=extracted.data.meal_status,
                        notes=extracted.data.notes,
                    )

                    # Close the connection before returning
                    conn.close()
                    logger.info("Database connection closed")

                    return ChatResponse(
                        response=f"I see you've shared a reading of {extracted.data.glucose_level} mg/dL "
                        f"({extracted.data.meal_status}) on {reading_date.strftime('%Y-%m-%d')}. "
                        f"Is this correct?",
                        extracted_reading=extracted_with_id,
                        needs_confirmation=True,
                    )
                else:
                    logger.info("No valid reading extracted")
            except Exception as e:
                logger.error(f"Extraction error: {str(e)}")

            # Close the connection before returning
            conn.close()
            logger.info("Database connection closed")

            # Return conversation response if no reading was extracted
            return ChatResponse(response=result.data)

        except Exception as e:
            # Make sure to close connection on error
            conn.close()
            logger.error(f"Error during chat processing: {str(e)}")
            raise e

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/confirm-reading")
async def confirm_reading(request: ConfirmReadingRequest):
    try:
        # Create a new connection for this request
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if request.confirm:
                # Update the reading to confirmed
                cursor.execute(
                    "UPDATE readings SET confirmed = 1 WHERE id = ? AND session_id = ?",
                    (request.reading_id, request.session_id),
                )
                conn.commit()

                conn.close()
                return {"message": "Great! I've saved your reading."}
            else:
                # Delete the rejected reading
                cursor.execute(
                    "DELETE FROM readings WHERE id = ?", (request.reading_id,)
                )
                conn.commit()

                conn.close()
                return {
                    "message": "No problem, let's try again. What was your reading?"
                }
        except Exception as e:
            conn.close()
            raise e

    except Exception as e:
        print(f"Confirm reading error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/readings/{session_id}")
async def get_readings(session_id: str):
    try:
        # Create a new connection for this request
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM readings WHERE session_id = ? AND confirmed = 1 ORDER BY date DESC",
                (session_id,),
            )
            rows = cursor.fetchall()

            readings = []
            for row in rows:
                reading = {
                    "id": row["id"],
                    "glucose_level": row["glucose_level"],
                    "date": row["date"],
                    "meal_status": row["meal_status"],
                    "notes": row["notes"],
                }
                readings.append(reading)

            conn.close()
            return readings
        except Exception as e:
            conn.close()
            raise e

    except Exception as e:
        print(f"Get readings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("minimal_backend:app", host="0.0.0.0", port=8000, reload=True)
