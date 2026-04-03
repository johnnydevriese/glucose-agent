from __future__ import annotations

import json

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from glucose_agent.agents import build_agents, configure_observability
from glucose_agent.repository import GlucoseRepository
from glucose_agent.schemas import HealthResponse, WebSocketAction
from glucose_agent.service import GlucoseService
from glucose_agent.settings import settings


configure_observability(settings)

repository = GlucoseRepository(settings.data_file)
agents = build_agents(settings)
service = GlucoseService(repository=repository, agents=agents)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", llm_enabled=settings.llm_enabled)


@app.get("/api/readings")
async def list_readings():
    return repository.list_readings()


@app.get("/api/stats")
async def get_stats():
    return service.get_stats_event().stats


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = websocket.query_params.get("session_id") or service.create_session_id()
    for event in await service.welcome_events():
        await websocket.send_text(event.model_dump_json())

    try:
        while True:
            payload = WebSocketAction.model_validate_json(await websocket.receive_text())
            if payload.action == "message" and payload.message:
                events = await service.handle_message(session_id, payload.message)
            elif payload.action == "confirm_reading" and payload.reading:
                events = await service.confirm_reading(
                    session_id, payload.reading, payload.notes or ""
                )
            elif payload.action == "get_history":
                events = [service.get_history_event()]
            elif payload.action == "get_stats":
                events = [service.get_stats_event()]
            else:
                events = []

            for event in events:
                await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
