from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import Request

from backend.domain.schemas import ActivityEvent


def encode_sse(event: str, data: dict, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    payload = json.dumps(data, ensure_ascii=False)
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines) + "\n"


async def encode_event_stream(events: AsyncIterator[ActivityEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield encode_sse(event.type, event.model_dump(mode="json"), event.id)


async def stream_with_disconnect_guard(
    request: Request,
    source: AsyncIterator[ActivityEvent],
) -> AsyncIterator[str]:
    """Encode `source` as SSE, cancelling the underlying async generator (and
    the in-flight LLM call it holds open) as soon as the client disconnects.

    Without this, an abandoned client connection leaves the phase handler's
    LLM call running indefinitely server-side, retrying through rate limits
    for a request nobody is listening to anymore.
    """
    agen = source.__aiter__()
    next_task: asyncio.Task[ActivityEvent] | None = None
    try:
        while True:
            if next_task is None:
                next_task = asyncio.ensure_future(agen.__anext__())

            done, _ = await asyncio.wait({next_task}, timeout=1.0)

            if next_task in done:
                task, next_task = next_task, None
                try:
                    event = task.result()
                except StopAsyncIteration:
                    break
                yield encode_sse(event.type, event.model_dump(mode="json"), event.id)
                continue

            if await request.is_disconnected():
                next_task.cancel()
                break
    finally:
        if next_task is not None and not next_task.done():
            next_task.cancel()
        await agen.aclose()
