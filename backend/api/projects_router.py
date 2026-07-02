from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.activity.log import append_event
from backend.domain import events
from backend.domain.schemas import ProjectCreate, ProjectMetadata, ProjectPatch, ProjectSummary
from backend.storage import projects

router = APIRouter(prefix="/projects", tags=["projects"])


def _not_found(project_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Project not found: {project_id}")


@router.post("", response_model=ProjectMetadata)
async def create_project(payload: ProjectCreate) -> ProjectMetadata:
    metadata = projects.create_project(payload.title, payload.content_type, payload.voice_id)
    await append_event(
        metadata.id,
        events.PROJECT_CREATED,
        metadata.phase.value,
        {"project": metadata.model_dump(mode="json")},
    )
    return metadata


@router.get("", response_model=list[ProjectSummary])
async def list_projects() -> list[ProjectSummary]:
    return projects.list_projects()


@router.get("/{project_id}", response_model=ProjectSummary)
async def get_project(project_id: str) -> ProjectSummary:
    try:
        metadata = projects.get_project(project_id)
    except (FileNotFoundError, ValueError):
        raise _not_found(project_id) from None
    return projects.summary_for(metadata)


@router.patch("/{project_id}", response_model=ProjectMetadata)
async def patch_project(project_id: str, payload: ProjectPatch) -> ProjectMetadata:
    try:
        async with projects.get_project_lock(project_id):
            metadata = projects.patch_project(project_id, payload)
    except FileNotFoundError:
        raise _not_found(project_id) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await append_event(
        project_id,
        events.PROJECT_UPDATED,
        metadata.phase.value,
        {"project": metadata.model_dump(mode="json")},
    )
    return metadata


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    try:
        async with projects.get_project_lock(project_id):
            projects.delete_project(project_id)
    except FileNotFoundError:
        raise _not_found(project_id) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{project_id}/advance", response_model=ProjectMetadata)
async def advance_project(project_id: str) -> ProjectMetadata:
    try:
        async with projects.get_project_lock(project_id):
            before = projects.get_project(project_id)
            metadata = projects.advance_project(project_id)
    except FileNotFoundError:
        raise _not_found(project_id) from None
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if metadata.phase != before.phase:
        await append_event(
            project_id,
            events.PHASE_ADVANCED,
            metadata.phase.value,
            {
                "from": before.phase.value,
                "to": metadata.phase.value,
                "project": metadata.model_dump(mode="json"),
            },
        )
    return metadata
