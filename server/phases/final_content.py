from __future__ import annotations

from collections.abc import AsyncIterator

from server.domain import events
from server.domain.phases import Phase, PhaseFile
from server.domain.schemas import ActivityEvent
from server.phases import prompt_assembly
from server.phases.base import PhaseAborted, emit_event, stream_llm_completion
from server.storage import projects
from server.storage.voice_profiles import get_voice_profile


async def generate(
    project_id: str,
    instructions: str | None,
    voice_id: str | None,
) -> AsyncIterator[ActivityEvent]:
    phase = Phase.FINAL
    async with projects.get_project_lock(project_id):
        metadata = projects.get_project(project_id)
        draft_file = projects.read_state_file(project_id, PhaseFile.DRAFT)
        if not draft_file.strip():
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "missing_draft", "message": "draft.md must exist before final generation"},
            )
            return

        resolved_voice_id = voice_id or metadata.voice_id
        if not resolved_voice_id:
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "missing_voice", "message": "Select a voice profile before final generation"},
            )
            return

        try:
            voice = get_voice_profile(resolved_voice_id)
        except KeyError:
            yield await emit_event(
                project_id,
                events.ERROR,
                phase,
                {"error": "voice_not_found", "voice_id": resolved_voice_id},
            )
            return

        final_parts: list[str] = []
        try:
            async for event in stream_llm_completion(
                project_id,
                phase,
                "final.generate",
                prompt_assembly.final_messages(voice.prompt, draft_file, instructions),
                0.7,
                final_parts,
            ):
                yield event
        except PhaseAborted:
            return

        final_text = "".join(final_parts).strip() + "\n"
        projects.write_state_file(project_id, PhaseFile.FINAL_CONTENT, final_text)
        yield await emit_event(
            project_id,
            events.FILE_CHANGED,
            phase,
            {"name": PhaseFile.FINAL_CONTENT.value, "content_chars": len(final_text)},
        )
        yield await emit_event(project_id, events.DONE, phase, {"ok": True})
