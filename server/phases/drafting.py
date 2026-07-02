from __future__ import annotations

from collections.abc import AsyncIterator

from server.domain import events
from server.domain.phases import Phase, PhaseFile
from server.domain.schemas import ActivityEvent
from server.phases import prompt_assembly
from server.phases.base import PhaseAborted, emit_event, stream_llm_completion
from server.storage import projects


async def generate(project_id: str, instructions: str | None) -> AsyncIterator[ActivityEvent]:
    phase = Phase.DRAFTING
    async with projects.get_project_lock(project_id):
        metadata = projects.get_project(project_id)
        ideation_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
        structure_file = projects.read_state_file(project_id, PhaseFile.STRUCTURE)

        missing = [
            name
            for name, content in (
                (PhaseFile.IDEATION.value, ideation_file),
                (PhaseFile.STRUCTURE.value, structure_file),
            )
            if not content.strip()
        ]
        if missing:
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "missing_prerequisites", "missing": missing},
            )
            return

        draft_parts: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "drafting.generate",
                prompt_assembly.drafting_messages(
                    metadata.content_type,
                    ideation_file,
                    structure_file,
                    instructions,
                ),
                0.4,
                draft_parts,
            ):
                yield event
        except PhaseAborted:
            return

        draft_text = "".join(draft_parts).strip() + "\n"
        projects.write_state_file(project_id, PhaseFile.DRAFT, draft_text)
        yield await emit_event(
            project_id,
            events.FILE_CHANGED,
            phase,
            {"name": PhaseFile.DRAFT.value, "content_chars": len(draft_text)},
        )
        yield await emit_event(project_id, events.DONE, phase, {"ok": True})
