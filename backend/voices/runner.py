from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from backend.domain.schemas import VoiceGenerateRequest
from backend.storage.voice_profiles import _voice_id_for
from backend.voices import storage, templates
from models.pipeline_state import PipelineConfig, PipelineState
from pipeline.two_stage_runner import TwoStageRunner

_DEFAULT_TEMPLATE_ID = "product-market-fit"


async def generate(person_id: str, request: VoiceGenerateRequest) -> AsyncIterator[dict]:
    """Run the voice pipeline for a person, yielding progress dicts as SSE-ready events.

    Drives TwoStageRunner (a synchronous, long-running CPU/network-bound
    pipeline) in a worker thread and bridges its progress_cb callbacks back to
    this async generator via an asyncio.Queue + call_soon_threadsafe, since
    the callback fires from the worker thread, not the event loop.
    """
    person = storage.get_person(person_id)

    if request.draft_source == "template":
        template_id = request.template_id or _DEFAULT_TEMPLATE_ID
        try:
            template = templates.get_template(template_id)
        except KeyError:
            yield {"type": "error", "error": "template_not_found", "template_id": template_id}
            return
        draft = template.content
        topic = template.label
    elif request.draft_source == "custom":
        draft = (request.custom_draft or "").strip()
        if not draft:
            yield {
                "type": "error",
                "error": "missing_draft",
                "message": "custom_draft is required when draft_source=custom",
            }
            return
        topic = f"{person.name} — custom draft"
    else:
        yield {"type": "error", "error": "invalid_draft_source", "draft_source": request.draft_source}
        return

    original_writing = storage.article_texts(person_id)
    if not original_writing:
        yield {
            "type": "error",
            "error": "missing_articles",
            "message": "Add at least one article before generating a voice",
        }
        return

    config = PipelineConfig(
        topic=topic,
        article_hash="",
        max_iterations=request.max_iterations,
        output_dir=str(storage.runs_dir(person_id)),
        context="",
    )
    runner = TwoStageRunner(config)

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    def progress_cb(event: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    def run_sync() -> PipelineState:
        return runner.run(original_writing, draft, draft=draft, progress_cb=progress_cb)

    async def worker() -> None:
        try:
            state = await asyncio.to_thread(run_sync)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an error event
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "__error__", "exc": exc})
        else:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "__done__", "state": state})

    task = asyncio.create_task(worker())

    yield {"type": "queued", "person_id": person_id, "max_iterations": request.max_iterations}

    state: PipelineState | None = None
    try:
        while True:
            event = await queue.get()
            if event["type"] == "__done__":
                state = event["state"]
                break
            if event["type"] == "__error__":
                exc = event["exc"]
                yield {"type": "error", "error": type(exc).__name__, "message": str(exc)}
                return
            yield event
    finally:
        await task

    run_dir = Path(config.output_dir) / state.run_id
    prompt_path = run_dir / "final_voice_prompt.txt"
    voice_id = _voice_id_for(prompt_path)

    run_meta = {
        "run_id": state.run_id,
        "person_id": person_id,
        "draft_source": request.draft_source,
        "max_iterations": request.max_iterations,
        "status": "completed",
        "best_score": state.best_score,
        "best_iteration": state.best_iteration,
        "exit_reason": state.exit_reason,
        "started_at": state.started_at,
        "completed_at": state.completed_at,
    }
    (run_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    storage.set_current_run(person_id, state.run_id, voice_id)

    yield {
        "type": "done",
        "run_id": state.run_id,
        "best_score": state.best_score,
        "best_iteration": state.best_iteration,
        "voice_id": voice_id,
    }
