from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from backend.activity.log import append_event
from backend.domain import events
from backend.domain.phases import Phase, PhaseFile
from backend.domain.schemas import FilePayload, FileUpdate
from backend.storage import paths, projects

router = APIRouter(prefix="/projects/{project_id}", tags=["files"])


def _phase_file_from_name(name: str) -> PhaseFile:
    try:
        return PhaseFile(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown file: {name}") from exc


def _phase_from_name(name: str) -> Phase:
    try:
        return Phase(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown phase: {name}") from exc


@router.get("/files/{name}", response_model=FilePayload)
async def get_file(project_id: str, name: str) -> FilePayload:
    phase_file = _phase_file_from_name(name)
    try:
        content = projects.read_state_file(project_id, phase_file)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    return FilePayload(
        name=phase_file.value,
        content=content,
        updated_at=projects.state_file_updated_at(project_id, phase_file),
    )


@router.put("/files/{name}", response_model=FilePayload)
async def put_file(project_id: str, name: str, payload: FileUpdate) -> FilePayload:
    phase_file = _phase_file_from_name(name)
    try:
        async with projects.get_project_lock(project_id):
            projects.write_state_file(project_id, phase_file, payload.content)
            updated_at = projects.state_file_updated_at(project_id, phase_file)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}") from None

    await append_event(
        project_id,
        events.FILE_CHANGED,
        None,
        {"name": phase_file.value, "updated_at": updated_at.isoformat() if updated_at else None},
    )
    return FilePayload(name=phase_file.value, content=payload.content, updated_at=updated_at)


@router.get("/transcript/{phase}")
async def get_transcript(project_id: str, phase: str) -> list[dict]:
    phase_value = _phase_from_name(phase)
    try:
        projects.get_project(project_id)
        path = paths.transcript_file_path(project_id, phase_value)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Transcript not found") from None

    if not path.exists():
        return []
    messages: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            messages.append(json.loads(line))
    return messages
