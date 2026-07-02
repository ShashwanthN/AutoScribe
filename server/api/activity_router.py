from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from server.activity.log import history, subscribe
from server.domain.schemas import ActivityEvent
from server.sse import encode_sse
from server.storage import projects

router = APIRouter(prefix="/projects/{project_id}/activity", tags=["activity"])


@router.get("", response_model=list[ActivityEvent])
async def get_activity(project_id: str, after_id: str | None = None) -> list[ActivityEvent]:
    try:
        projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None
    return await history(project_id, after_id)


@router.get("/stream")
async def stream_activity(project_id: str, request: Request) -> StreamingResponse:
    try:
        projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    async def body() -> AsyncIterator[str]:
        event_iter = subscribe(project_id).__aiter__()
        while not await request.is_disconnected():
            try:
                event = await asyncio.wait_for(event_iter.__anext__(), timeout=20)
                yield encode_sse(event.type, event.model_dump(mode="json"), event.id)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
            except StopAsyncIteration:
                break

    return StreamingResponse(body(), media_type="text/event-stream")
