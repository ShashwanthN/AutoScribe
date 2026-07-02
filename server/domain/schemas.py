from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from server.domain.content_types import ContentType
from server.domain.phases import Phase


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content_type: ContentType
    voice_id: str | None = None


class ProjectPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content_type: ContentType | None = None
    voice_id: str | None = None


class ProjectMetadata(BaseModel):
    id: str
    title: str
    slug: str
    content_type: ContentType
    phase: Phase = Phase.IDEATION
    voice_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectSummary(ProjectMetadata):
    files: dict[str, bool]


class FilePayload(BaseModel):
    name: str
    content: str
    updated_at: datetime | None = None


class FileUpdate(BaseModel):
    content: str


class VoiceProfile(BaseModel):
    id: str
    run_id: str
    label: str
    path: str
    source: str
    iteration: int | None = None
    mtime: float
    preview: str


class VoiceProfileDetail(VoiceProfile):
    prompt: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    instructions: str | None = None
    voice_id: str | None = None


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ts: datetime
    project_id: str
    type: str
    phase: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
