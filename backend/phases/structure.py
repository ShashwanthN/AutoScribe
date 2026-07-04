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
    phase = Phase.STRUCTURE
    async with projects.get_project_lock(project_id):
        metadata = projects.get_project(project_id)
        ideation_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
        if not ideation_file.strip():
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "missing_ideation", "message": "ideation.md must exist before structure chat"},
            )
            return

        if load_transcript(project_id, phase):
            return

        intro_parts: list[str] = []
        model_info: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "structure.intro",
                prompt_assembly.structure_intro_messages(metadata.content_type, ideation_file),
                0.7,
                intro_parts,
                model_info,
            ):
                yield event
        except PhaseAborted:
            return

        intro_text = "".join(intro_parts).strip()
        model_name = model_info[0] if model_info else None
        append_transcript_message(project_id, phase, "assistant", intro_text, model_name=model_name)
        yield await emit_event(project_id, events.DONE, phase, {"ok": True})


async def chat(project_id: str, message: str) -> AsyncIterator[ActivityEvent]:
    phase = Phase.STRUCTURE
    async with projects.get_project_lock(project_id):
        metadata = projects.get_project(project_id)
        ideation_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
        if not ideation_file.strip():
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "missing_ideation", "message": "ideation.md must exist before structure chat"},
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
                "structure.reply",
                prompt_assembly.structure_reply_messages(
                    metadata.content_type,
                    ideation_file,
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
            current_file = projects.read_state_file(project_id, PhaseFile.STRUCTURE)
            try:
                async for event in regen_agent.regen_state_file(
                    project_id,
                    phase,
                    PhaseFile.STRUCTURE,
                    "structure.state_regen",
                    prompt_assembly.structure_regen_messages(
                        metadata.content_type,
                        ideation_file,
                        current_file,
                        delta,
                    ),
                    marker_count=len(transcript),
                ):
                    yield event
            except PhaseAborted:
                return

        yield await emit_event(project_id, events.DONE, phase, {"ok": True})
