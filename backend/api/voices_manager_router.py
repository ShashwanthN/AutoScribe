from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.domain.schemas import (
    Article,
    ArticleCreate,
    Person,
    PersonCreate,
    PersonPatch,
    PersonSummary,
    VoiceGenerateRequest,
    VoiceRunDetail,
    VoiceRunSummary,
    VoiceTemplate,
)
from backend.voices import runner, storage, templates

router = APIRouter(prefix="/persons", tags=["voice-manager"])
templates_router = APIRouter(prefix="/voice-templates", tags=["voice-manager"])


@templates_router.get("", response_model=list[VoiceTemplate])
async def list_templates() -> list[VoiceTemplate]:
    return templates.list_templates()


@router.post("", response_model=Person)
async def create_person(payload: PersonCreate) -> Person:
    return storage.create_person(payload.name)


@router.get("", response_model=list[PersonSummary])
async def list_persons() -> list[PersonSummary]:
    return storage.list_persons()


@router.get("/{person_id}", response_model=PersonSummary)
async def get_person(person_id: str) -> PersonSummary:
    try:
        return storage.summary_for(storage.get_person(person_id))
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.patch("/{person_id}", response_model=Person)
async def patch_person(person_id: str, payload: PersonPatch) -> Person:
    try:
        if payload.name is not None:
            return storage.rename_person(person_id, payload.name)
        return storage.get_person(person_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: str) -> None:
    try:
        storage.delete_person(person_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.get("/{person_id}/articles", response_model=list[Article])
async def list_articles(person_id: str) -> list[Article]:
    try:
        return storage.list_articles(person_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.post("/{person_id}/articles", response_model=Article)
async def add_article(person_id: str, payload: ArticleCreate) -> Article:
    async with storage.get_person_lock(person_id):
        try:
            return storage.add_article(person_id, payload)
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.put("/{person_id}/articles/{article_id}", response_model=Article)
async def update_article(person_id: str, article_id: str, payload: ArticleCreate) -> Article:
    async with storage.get_person_lock(person_id):
        try:
            return storage.update_article(person_id, article_id, payload)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Article not found: {article_id}") from None


@router.delete("/{person_id}/articles/{article_id}", status_code=204)
async def delete_article(person_id: str, article_id: str) -> None:
    async with storage.get_person_lock(person_id):
        try:
            storage.delete_article(person_id, article_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Article not found: {article_id}") from None


@router.get("/{person_id}/runs", response_model=list[VoiceRunSummary])
async def list_runs(person_id: str) -> list[VoiceRunSummary]:
    try:
        return storage.list_runs(person_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None


@router.get("/{person_id}/runs/{run_id}", response_model=VoiceRunDetail)
async def get_run(person_id: str, run_id: str) -> VoiceRunDetail:
    try:
        return storage.get_run(person_id, run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from None


@router.post("/{person_id}/runs/{run_id}/activate", response_model=Person)
async def activate_run(person_id: str, run_id: str) -> Person:
    async with storage.get_person_lock(person_id):
        try:
            return storage.activate_run(person_id, run_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from None


@router.delete("/{person_id}/runs/{run_id}", status_code=204)
async def delete_run(person_id: str, run_id: str) -> None:
    async with storage.get_person_lock(person_id):
        try:
            storage.delete_run(person_id, run_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from None


def _encode_sse(event: dict) -> str:
    event_type = event.get("type", "message")
    payload = json.dumps(event, ensure_ascii=False)
    lines = [f"event: {event_type}"]
    for line in payload.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines) + "\n"


async def _stream_with_disconnect_guard(request: Request, source: AsyncIterator[dict]) -> AsyncIterator[str]:
    agen = source.__aiter__()
    next_task: asyncio.Task[dict] | None = None
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
                yield _encode_sse(event)
                continue

            if await request.is_disconnected():
                next_task.cancel()
                break
    finally:
        if next_task is not None and not next_task.done():
            next_task.cancel()
        await agen.aclose()


@router.post("/{person_id}/generate")
async def generate(person_id: str, payload: VoiceGenerateRequest, request: Request) -> StreamingResponse:
    try:
        storage.get_person(person_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail=f"Person not found: {person_id}") from None

    source = runner.generate(person_id, payload)
    return StreamingResponse(_stream_with_disconnect_guard(request, source), media_type="text/event-stream")
