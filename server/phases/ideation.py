from __future__ import annotations

from collections.abc import AsyncIterator

from server.domain import events
from server.domain.phases import Phase, PhaseFile
from server.domain.schemas import ActivityEvent
from server.phases import prompt_assembly, regen_agent
from server.phases.base import (
    PhaseAborted,
    append_transcript_message,
    emit_event,
    load_transcript,
    messages_since_marker,
    read_regen_marker,
    split_regen_signal,
    stream_llm_completion,
)
from server.storage import projects


async def start(project_id: str) -> AsyncIterator[ActivityEvent]:
    phase = Phase.IDEATION
    async with projects.get_project_lock(project_id):
        projects.get_project(project_id)

        if load_transcript(project_id, phase):
            # Already started (or a concurrent request won the race) — idempotent no-op.
            return

        intro_parts: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "ideation.intro",
                prompt_assembly.ideation_intro_messages(),
                0.7,
                intro_parts,
            ):
                yield event
        except PhaseAborted:
            return

        intro_text = "".join(intro_parts).strip()
        append_transcript_message(project_id, phase, "assistant", intro_text)
        yield await emit_event(project_id, events.DONE, phase, {"ok": True})


async def chat(project_id: str, message: str) -> AsyncIterator[ActivityEvent]:
    phase = Phase.IDEATION
    async with projects.get_project_lock(project_id):
        projects.get_project(project_id)

        append_transcript_message(project_id, phase, "user", message)
        transcript = load_transcript(project_id, phase)

        reply_parts: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "ideation.reply",
                prompt_assembly.ideation_reply_messages(transcript),
                0.7,
                reply_parts,
            ):
                yield event
        except PhaseAborted:
            return

        visible_text, should_regen = split_regen_signal("".join(reply_parts))
        append_transcript_message(project_id, phase, "assistant", visible_text)

        if should_regen:
            transcript = load_transcript(project_id, phase)
            marker = read_regen_marker(project_id, phase)
            delta = messages_since_marker(transcript, marker)
            current_file = projects.read_state_file(project_id, PhaseFile.IDEATION)
            try:
                async for event in regen_agent.regen_state_file(
                    project_id,
                    phase,
                    PhaseFile.IDEATION,
                    "ideation.state_regen",
                    prompt_assembly.ideation_regen_messages(current_file, delta),
                    marker_count=len(transcript),
                ):
                    yield event
            except PhaseAborted:
                return

        yield await emit_event(project_id, events.DONE, phase, {"ok": True})
