from __future__ import annotations

from pathlib import Path

import config  # noqa: F401 - loads .env as a side effect

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT_DIR / "outputs"
PROJECTS_DIR = ROOT_DIR / "projects"
VOICES_DIR = ROOT_DIR / "voices"


def _resolve_prompt_skills_dir() -> Path:
    for name in ("Old-pipeline-skills", "old-pipeline-skills"):
        path = ROOT_DIR / name
        if path.exists():
            return path
    return ROOT_DIR / "Old-pipeline-skills"


PROMPT_SKILLS_DIR = _resolve_prompt_skills_dir()

API_HOST = "127.0.0.1"
API_PORT = 8000
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
