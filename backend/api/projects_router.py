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

            from backend.domain.phases import is_chat_phase, Phase, PhaseFile
            if is_chat_phase(before.phase):
                from backend.phases.base import load_transcript, read_regen_marker, messages_since_marker, PhaseAborted
                from backend.phases.prompt_assembly import ideation_regen_messages, structure_regen_messages, drafting_regen_messages
                from backend.phases.regen_agent import regen_state_file

                transcript = load_transcript(project_id, before.phase)
                marker = read_regen_marker(project_id, before.phase)
                if marker < len(transcript):
                    delta = messages_since_marker(transcript, marker)
                    file_name = None
                    label = ""
                    prompts = []

                    if before.phase == Phase.IDEATION:
                        current_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
                        prompts = ideation_regen_messages(current_file, delta)
                        file_name = PhaseFile.IDEATION
                        label = "ideation.state_regen"
                    elif before.phase == Phase.STRUCTURE:
                        ideation_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
                        current_file = projects.read_state_file(project_id, PhaseFile.STRUCTURE)
                        prompts = structure_regen_messages(before.content_type, ideation_file, current_file, delta)
                        file_name = PhaseFile.STRUCTURE
                        label = "structure.state_regen"
                    elif before.phase == Phase.DRAFTING:
                        ideation_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
                        structure_file = projects.read_state_file(project_id, PhaseFile.STRUCTURE)
                        current_file = projects.read_state_file(project_id, PhaseFile.DRAFT)
                        prompts = drafting_regen_messages(before.content_type, ideation_file, structure_file, current_file, delta)
                        file_name = PhaseFile.DRAFT
                        label = "drafting.state_regen"

                    if file_name:
                        try:
                            async for _ in regen_state_file(project_id, before.phase, file_name, label, prompts, len(transcript)):
                                pass
                        except PhaseAborted:
                            raise ValueError("Failed to complete pending file regeneration. Please try again.")

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
