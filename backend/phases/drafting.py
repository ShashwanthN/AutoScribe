from __future__ import annotations

from collections.abc import AsyncIterator

from backend.domain import events
from backend.domain.phases import Phase, PhaseFile
from backend.domain.schemas import ActivityEvent
from backend.phases import prompt_assembly, regen_agent
from backend.phases.base import (
    PhaseAborted,
    append_transcript_message,
    emit_event,
    load_transcript,
    messages_since_marker,
    read_regen_marker,
    split_regen_signal,
    stream_llm_completion,
)
from backend.storage import projects


async def start(project_id: str) -> AsyncIterator[ActivityEvent]:
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

        if load_transcript(project_id, phase):
            # Already started
            return

        try:
            async for event in regen_agent.regen_state_file(
                project_id,
                phase,
                PhaseFile.DRAFT,
                "drafting.generate",
                prompt_assembly.drafting_initial_messages(
                    metadata.content_type,
                    ideation_file,
                    structure_file,
                ),
                marker_count=0,
            ):
                yield event
        except PhaseAborted:
            return

        intro_text = "I've generated the initial draft based on our structure! Review it in the preview panel on the right. Let me know if you want to expand any sections, change the order, or tweak the arguments before we move to the final generation phase."
        append_transcript_message(project_id, phase, "assistant", intro_text)
        yield await emit_event(project_id, events.DONE, phase, {"ok": True})


async def chat(project_id: str, message: str) -> AsyncIterator[ActivityEvent]:
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

        append_transcript_message(project_id, phase, "user", message)
        transcript = load_transcript(project_id, phase)

        reply_parts: list[str] = []
        model_info: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "drafting.reply",
                prompt_assembly.drafting_reply_messages(
                    metadata.content_type,
                    ideation_file,
                    structure_file,
                    transcript,
                ),
                0.7,
                reply_parts,
                model_info,
            ):
                yield event
        except PhaseAborted:
            return

        visible_text, should_regen = split_regen_signal("".join(reply_parts))
        model_name = model_info[0] if model_info else None
        append_transcript_message(project_id, phase, "assistant", visible_text, model_name=model_name)

        if should_regen:
            transcript = load_transcript(project_id, phase)
            marker = read_regen_marker(project_id, phase)
            delta = messages_since_marker(transcript, marker)
            current_file = projects.read_state_file(project_id, PhaseFile.DRAFT)
            try:
                async for event in regen_agent.regen_state_file(
                    project_id,
                    phase,
                    PhaseFile.DRAFT,
                    "drafting.state_regen",
                    prompt_assembly.drafting_regen_messages(
                        metadata.content_type,
                        ideation_file,
                        structure_file,
                        current_file,
                        delta,
                    ),
                    marker_count=len(transcript),
                ):
                    yield event
            except PhaseAborted:
                return

        yield await emit_event(project_id, events.DONE, phase, {"ok": True})
