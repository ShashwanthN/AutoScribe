from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.domain.phases import Phase, is_chat_phase
from backend.domain.schemas import ChatRequest
from backend.phases import ideation, structure
from backend.sse import stream_with_disconnect_guard
from backend.storage import projects

router = APIRouter(prefix="/projects/{project_id}/phases/{phase}", tags=["chat"])


@router.post("/chat")
async def chat(project_id: str, phase: str, payload: ChatRequest, request: Request) -> StreamingResponse:
    try:
        phase_value = Phase(phase)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}") from exc
    if not is_chat_phase(phase_value):
        raise HTTPException(status_code=400, detail=f"Phase does not support chat: {phase}")

    try:
        projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    source = ideation.chat(project_id, payload.message) if phase_value == Phase.IDEATION else structure.chat(project_id, payload.message)

    return StreamingResponse(stream_with_disconnect_guard(request, source), media_type="text/event-stream")


@router.post("/start")
async def start_phase(project_id: str, phase: str, request: Request) -> StreamingResponse:
    try:
        phase_value = Phase(phase)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}") from exc
    if not is_chat_phase(phase_value):
        raise HTTPException(status_code=400, detail=f"Phase does not support chat: {phase}")

    try:
        projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    source = ideation.start(project_id) if phase_value == Phase.IDEATION else structure.start(project_id)

    return StreamingResponse(stream_with_disconnect_guard(request, source), media_type="text/event-stream")
