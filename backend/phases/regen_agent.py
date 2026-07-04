from __future__ import annotations

from collections.abc import AsyncIterator

from backend.domain import events
from backend.domain.phases import Phase, PhaseFile
from backend.domain.schemas import ActivityEvent
from backend.phases.base import emit_event, stream_llm_completion, strip_markdown_code_fences, write_regen_marker
from backend.storage import projects


async def regen_state_file(
    project_id: str,
    phase: Phase,
    file_name: PhaseFile,
    label: str,
    messages: list[dict[str, str]],
    marker_count: int,
) -> AsyncIterator[ActivityEvent]:
    """The dedicated state-file regeneration agent.

    This is a separate agent from the phase's conversational agent (ideation
    reply, structure reply, ...): it never talks to the user, it only ever
    sees the current on-disk state file plus the transcript messages that
    have accumulated since the last successful regen, and its only job is to
    merge those into an updated file. Raises PhaseAborted (via
    stream_llm_completion) if the underlying LLM call fails; the caller is
    responsible for catching that and leaving the regen marker untouched so
    the pending delta is retried on the next successful regen.
    """
    parts: list[str] = []
    async for event in stream_llm_completion(project_id, phase, label, messages, 0.2, parts):
        yield event

    state_text = strip_markdown_code_fences("".join(parts)) + "\n"
    projects.write_state_file(project_id, file_name, state_text)
    write_regen_marker(project_id, phase, marker_count)
    yield await emit_event(
        project_id,
        events.FILE_CHANGED,
        phase,
        {"name": file_name.value, "content_chars": len(state_text)},
    )
