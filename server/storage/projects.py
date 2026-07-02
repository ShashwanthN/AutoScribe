from __future__ import annotations

import asyncio
import json
import re
import shutil
from datetime import datetime, timezone

from server.domain.phases import Phase, PhaseFile, next_phase, required_file_for_advance
from server.domain.schemas import ProjectMetadata, ProjectPatch, ProjectSummary
from server.storage import paths

_PROJECT_LOCKS: dict[str, asyncio.Lock] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:48] or "untitled"


def get_project_lock(project_id: str) -> asyncio.Lock:
    paths.validate_project_id(project_id)
    lock = _PROJECT_LOCKS.get(project_id)
    if lock is None:
        lock = asyncio.Lock()
        _PROJECT_LOCKS[project_id] = lock
    return lock


def _write_metadata(metadata: ProjectMetadata) -> None:
    paths.atomic_write_text(
        paths.metadata_path(metadata.id),
        json.dumps(metadata.model_dump(mode="json"), indent=2),
    )


def _read_metadata(project_id: str) -> ProjectMetadata:
    path = paths.metadata_path(project_id)
    if not path.exists():
        raise FileNotFoundError(project_id)
    return ProjectMetadata.model_validate_json(path.read_text(encoding="utf-8"))


def create_project(title: str, content_type, voice_id: str | None = None) -> ProjectMetadata:
    root = paths.projects_root()
    slug = _slugify(title)
    stamp = _now().strftime("%Y%m%d_%H%M%S")

    for index in range(1, 100):
        suffix = "" if index == 1 else f"-{index}"
        project_id = f"proj_{stamp}_{slug}{suffix}"
        project_path = root / project_id
        if not project_path.exists():
            project_path.mkdir(parents=True)
            break
    else:
        raise RuntimeError("Could not allocate a unique project id")

    now = _now()
    metadata = ProjectMetadata(
        id=project_id,
        title=title.strip(),
        slug=slug,
        content_type=content_type,
        phase=Phase.IDEATION,
        voice_id=voice_id,
        created_at=now,
        updated_at=now,
    )
    _write_metadata(metadata)
    paths.activity_path(project_id).touch()
    return metadata


def list_projects() -> list[ProjectSummary]:
    projects: list[ProjectSummary] = []
    for path in sorted(paths.projects_root().iterdir(), reverse=True):
        if not path.is_dir():
            continue
        try:
            metadata = _read_metadata(path.name)
        except Exception:
            continue
        projects.append(summary_for(metadata))
    return projects


def get_project(project_id: str) -> ProjectMetadata:
    return _read_metadata(project_id)


def summary_for(metadata: ProjectMetadata) -> ProjectSummary:
    files = {
        name.value: paths.file_is_nonempty(paths.state_file_path(metadata.id, name))
        for name in PhaseFile
    }
    return ProjectSummary(**metadata.model_dump(), files=files)


def patch_project(project_id: str, patch: ProjectPatch) -> ProjectMetadata:
    metadata = _read_metadata(project_id)
    updates = patch.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(metadata, key, value)
    metadata.updated_at = _now()
    _write_metadata(metadata)
    return metadata


def delete_project(project_id: str) -> None:
    project_path = paths.project_dir(project_id)
    if not project_path.exists():
        raise FileNotFoundError(project_id)
    shutil.rmtree(project_path)
    _PROJECT_LOCKS.pop(project_id, None)


def advance_project(project_id: str) -> ProjectMetadata:
    metadata = _read_metadata(project_id)
    following = next_phase(metadata.phase)
    if following is None:
        return metadata

    required = required_file_for_advance(metadata.phase)
    required_path = paths.state_file_path(project_id, required)
    if not paths.file_is_nonempty(required_path):
        raise ValueError(f"Cannot advance until {required.value} exists and is non-empty")

    metadata.phase = following
    metadata.updated_at = _now()
    _write_metadata(metadata)
    return metadata


def read_state_file(project_id: str, name: PhaseFile) -> str:
    get_project(project_id)
    return paths.read_text_if_exists(paths.state_file_path(project_id, name))


def write_state_file(project_id: str, name: PhaseFile, content: str) -> None:
    get_project(project_id)
    paths.atomic_write_text(paths.state_file_path(project_id, name), content)


def state_file_updated_at(project_id: str, name: PhaseFile) -> datetime | None:
    path = paths.state_file_path(project_id, name)
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
