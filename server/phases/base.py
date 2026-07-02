from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from server.activity.log import append_event
from server.domain import events
from server.domain.phases import Phase
from server.domain.schemas import ActivityEvent
from server.llm_stream import StreamingLLM, TruncatedResponseError
from server.storage import paths


class PhaseAborted(Exception):
    pass


# Matches a trailing "[[REGEN:YES]]" / "[[REGEN:NO]]" control line the reply
# agent uses to tell the (separate) regen agent whether this turn added
# material worth saving. Anchored to the end of the string so it can only ever
# strip a genuine trailing marker, never an incidental substring mid-reply.
_REGEN_SIGNAL_RE = re.compile(r"\n*\[\[REGEN:(YES|NO)\]\]\s*$")


def split_regen_signal(reply_text: str) -> tuple[str, bool]:
    """Split a reply agent's raw output into (visible_text, should_regen).

    Defaults to should_regen=True when the model omits the marker entirely —
    that keeps the state file from silently going stale if a model ever fails
    to follow the control-line instruction, matching the old always-regen
    behavior as a safe fallback.
    """
    match = _REGEN_SIGNAL_RE.search(reply_text)
    if not match:
        return reply_text.strip(), True
    visible = _REGEN_SIGNAL_RE.sub("", reply_text).strip()
    return visible, match.group(1) == "YES"


def read_regen_marker(project_id: str, phase: Phase) -> int:
    path = paths.regen_marker_path(project_id, phase)
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        count = int(data.get("message_count", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return 0
    return max(count, 0)


def write_regen_marker(project_id: str, phase: Phase, message_count: int) -> None:
    paths.atomic_write_text(
        paths.regen_marker_path(project_id, phase),
        json.dumps({"message_count": message_count}),
    )


def messages_since_marker(transcript: list[dict[str, str]], marker: int) -> list[dict[str, str]]:
    # Clamp defensively: the marker can outrun the transcript if a user
    # manually edits/truncates chat_*.jsonl on disk between requests.
    start = min(max(marker, 0), len(transcript))
    return transcript[start:]


def load_transcript(project_id: str, phase: Phase) -> list[dict[str, str]]:
    path = paths.transcript_file_path(project_id, phase)
    if not path.exists():
        return []

    messages: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        messages.append({"role": item["role"], "content": item["content"]})
    return messages


def append_transcript_message(project_id: str, phase: Phase, role: str, content: str) -> None:
    path = paths.transcript_file_path(project_id, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
        fh.write("\n")


async def emit_event(
    project_id: str,
    event_type: str,
    phase: Phase | str | None,
    payload: dict,
) -> ActivityEvent:
    phase_value = phase.value if isinstance(phase, Phase) else phase
    return await append_event(project_id, event_type, phase_value, payload)


async def stream_llm_completion(
    project_id: str,
    phase: Phase,
    label: str,
    messages: list[dict],
    temperature: float,
    parts: list[str],
) -> AsyncIterator[ActivityEvent]:
    llm = StreamingLLM()
    yield await emit_event(
        project_id,
        events.LLM_CALL,
        phase,
        {
            "label": label,
            "model": llm.model,
            "base_url": llm.base_url,
            "temperature": temperature,
            "max_tokens": llm.max_tokens,
            "messages": messages,
        },
    )

    try:
        async for item in llm.stream(messages, temperature=temperature, label=label):
            if item.type == "token":
                parts.append(item.text)
                yield await emit_event(
                    project_id,
                    events.TOKEN,
                    phase,
                    {"label": label, "kind": "content", "text": item.text},
                )
            elif item.type == "reasoning":
                yield await emit_event(
                    project_id,
                    events.TOKEN,
                    phase,
                    {"label": label, "kind": "reasoning", "text": item.text},
                )
            elif item.type == "done":
                yield await emit_event(
                    project_id,
                    events.ASSISTANT_DONE,
                    phase,
                    {
                        "label": label,
                        "text": item.text,
                        "finish_reason": item.finish_reason,
                    },
                )
    except TruncatedResponseError as exc:
        yield await emit_event(
            project_id,
            events.ERROR,
            phase,
            {
                "label": label,
                "error": "truncated_response",
                "message": str(exc),
                "partial_chars": len(exc.partial),
            },
        )
        raise PhaseAborted from exc
    except Exception as exc:
        yield await emit_event(
            project_id,
            events.ERROR,
            phase,
            {
                "label": label,
                "error": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise PhaseAborted from exc
