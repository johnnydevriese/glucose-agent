from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _cors_origins() -> List[str]:
    raw = os.getenv("GLUCOSE_CORS_ORIGINS")
    if not raw:
        return ["http://localhost:5173"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass
class AppSettings:
    app_name: str = "Glucose Buddy API"
    cors_allowed_origins: List[str] = field(default_factory=_cors_origins)
    logfire_token: str = os.getenv("LOGFIRE_API_KEY", "")
    google_api_key: str = os.getenv("GEMINI_API_KEY", "") or os.getenv(
        "GOOGLE_API_KEY", ""
    )
    google_model: str = os.getenv("GLUCOSE_MODEL", "gemini-2.5-flash")
    request_limit: int = int(os.getenv("GLUCOSE_REQUEST_LIMIT", "12"))
    history_limit: int = int(os.getenv("GLUCOSE_HISTORY_LIMIT", "20"))
    data_file: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "GLUCOSE_DATA_FILE",
                Path(__file__).resolve().parent.parent / "data" / "glucose_state.json",
            )
        )
    )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.google_api_key)


settings = AppSettings()
