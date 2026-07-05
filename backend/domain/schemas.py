from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.content_types import ContentType
from backend.domain.phases import Phase


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


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class PersonPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)


class Person(BaseModel):
    id: str
    name: str
    slug: str
    current_run_id: str | None = None
    voice_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PersonSummary(Person):
    article_count: int
    run_count: int


class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)


class Article(BaseModel):
    id: str
    title: str
    text: str
    added_at: datetime


class VoiceTemplate(BaseModel):
    id: str
    label: str
    description: str


class VoiceTemplateDetail(VoiceTemplate):
    content: str


class VoiceGenerateRequest(BaseModel):
    draft_source: str = Field(pattern="^(template|custom)$")
    template_id: str | None = None
    custom_draft: str | None = None
    max_iterations: int = Field(default=4, ge=1, le=10)


class VoiceRunSummary(BaseModel):
    run_id: str
    person_id: str
    draft_source: str
    max_iterations: int
    status: str
    best_score: float | None = None
    best_iteration: int | None = None
    exit_reason: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class VoiceRunDetail(VoiceRunSummary):
    style_prompt: str | None = None
    final_content: str | None = None


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ts: datetime
    project_id: str
    type: str
    phase: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
