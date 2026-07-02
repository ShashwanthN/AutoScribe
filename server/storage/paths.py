from __future__ import annotations

import re
from pathlib import Path

from server import settings
from server.domain.phases import Phase, PhaseFile

PROJECT_ID_RE = re.compile(r"^proj_[0-9]{8}_[0-9]{6}_[a-z0-9-]+$")

STATE_FILES: dict[PhaseFile, str] = {
    PhaseFile.IDEATION: "ideation.md",
    PhaseFile.STRUCTURE: "structure.md",
    PhaseFile.DRAFT: "draft.md",
    PhaseFile.FINAL_CONTENT: "final_content.md",
}

TRANSCRIPT_FILES: dict[Phase, str] = {
    Phase.IDEATION: "chat_ideation.jsonl",
    Phase.STRUCTURE: "chat_structure.jsonl",
}


def validate_project_id(project_id: str) -> str:
    if not PROJECT_ID_RE.match(project_id):
        raise ValueError(f"Invalid project id: {project_id}")
    return project_id


def projects_root() -> Path:
    settings.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.PROJECTS_DIR


def project_dir(project_id: str) -> Path:
    validate_project_id(project_id)
    return projects_root() / project_id


def metadata_path(project_id: str) -> Path:
    return project_dir(project_id) / "metadata.json"


def activity_path(project_id: str) -> Path:
    return project_dir(project_id) / "activity.jsonl"


def state_file_path(project_id: str, name: PhaseFile) -> Path:
    return project_dir(project_id) / STATE_FILES[name]


def transcript_file_path(project_id: str, phase: Phase) -> Path:
    if phase not in TRANSCRIPT_FILES:
        raise ValueError(f"No transcript file for phase: {phase}")
    return project_dir(project_id) / TRANSCRIPT_FILES[phase]


def regen_marker_path(project_id: str, phase: Phase) -> Path:
    return project_dir(project_id) / f".{phase.value}_regen_marker.json"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def file_is_nonempty(path: Path) -> bool:
    return path.exists() and bool(path.read_text(encoding="utf-8").strip())
