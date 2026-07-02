from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncIterator

from pydantic import TypeAdapter

from server.domain.schemas import ActivityEvent
from server.storage import paths

_EVENT_LOCKS: dict[str, asyncio.Lock] = {}
_SUBSCRIBERS: dict[str, set[asyncio.Queue[ActivityEvent]]] = defaultdict(set)
_COUNTER = 0
_EVENT_ADAPTER = TypeAdapter(ActivityEvent)


def _lock_for(project_id: str) -> asyncio.Lock:
    paths.validate_project_id(project_id)
    lock = _EVENT_LOCKS.get(project_id)
    if lock is None:
        lock = asyncio.Lock()
        _EVENT_LOCKS[project_id] = lock
    return lock


def _next_event_id() -> str:
    global _COUNTER
    _COUNTER += 1
    return f"{time.time_ns()}-{_COUNTER}"


async def append_event(
    project_id: str,
    event_type: str,
    phase: str | None,
    payload: dict,
) -> ActivityEvent:
    event = ActivityEvent(
        id=_next_event_id(),
        ts=datetime.now(timezone.utc),
        project_id=project_id,
        type=event_type,
        phase=phase,
        payload=payload,
    )

    async with _lock_for(project_id):
        path = paths.activity_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(mode="json"), separators=(",", ":")))
            fh.write("\n")

    for queue in list(_SUBSCRIBERS.get(project_id, set())):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # A burst of reasoning tokens can fill the queue faster than a
            # slow consumer drains it. Drop the oldest item instead of
            # dropping the subscriber — losing a couple of stale tokens is
            # harmless, but discarding the subscriber used to leave that SSE
            # connection permanently silent (never re-added to _SUBSCRIBERS)
            # for the rest of its lifetime.
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

    return event


async def history(project_id: str, after_id: str | None = None) -> list[ActivityEvent]:
    paths.validate_project_id(project_id)
    path = paths.activity_path(project_id)
    if not path.exists():
        return []

    events: list[ActivityEvent] = []
    seen_after = after_id is None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = _EVENT_ADAPTER.validate_json(line)
        if not seen_after:
            seen_after = event.id == after_id
            continue
        if event.type == "token":
            # Individual tokens are only meaningful while a call is still
            # streaming live. A finished call's full text already lives in
            # its assistant_done event, so replaying every raw token here
            # would both balloon the response and (since callers cap how
            # many events they keep) push finished calls' marker events out
            # of the window entirely.
            continue
        events.append(event)
    return events


async def subscribe(project_id: str) -> AsyncIterator[ActivityEvent]:
    paths.validate_project_id(project_id)
    queue: asyncio.Queue[ActivityEvent] = asyncio.Queue(maxsize=2000)
    _SUBSCRIBERS[project_id].add(queue)
    try:
        while True:
            yield await queue.get()
    finally:
        _SUBSCRIBERS[project_id].discard(queue)
