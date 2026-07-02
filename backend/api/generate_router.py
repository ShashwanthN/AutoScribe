from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.domain.phases import Phase, is_generate_phase
from backend.domain.schemas import GenerateRequest
from backend.phases import drafting, final_content
from backend.sse import stream_with_disconnect_guard
from backend.storage import projects

router = APIRouter(prefix="/projects/{project_id}/phases/{phase}", tags=["generate"])


@router.post("/generate")
async def generate(project_id: str, phase: str, payload: GenerateRequest, request: Request) -> StreamingResponse:
    try:
        phase_value = Phase(phase)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown phase: {phase}") from exc
    if not is_generate_phase(phase_value):
        raise HTTPException(status_code=400, detail=f"Phase does not support generation: {phase}")

    try:
        projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    source = (
        drafting.generate(project_id, payload.instructions)
        if phase_value == Phase.DRAFTING
        else final_content.generate(project_id, payload.instructions, payload.voice_id)
    )

    return StreamingResponse(stream_with_disconnect_guard(request, source), media_type="text/event-stream")
