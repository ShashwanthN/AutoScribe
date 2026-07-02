from __future__ import annotations

from enum import Enum
from pathlib import Path

from server import settings


class ContentType(str, Enum):
    LINKEDIN_POST = "linkedin_post"
    BLOG_POST = "blog_post"
    CASE_STUDY = "case_study"
    USE_CASE = "use_case"
    ARTICLE = "article"


FRAMEWORK_FILES: dict[ContentType, tuple[str, ...]] = {
    ContentType.LINKEDIN_POST: (
        "3-Drafting/LinkedIn-Post.md",
        "3-Drafting/LinkedIn-Framework.md",
    ),
    ContentType.BLOG_POST: ("3-Drafting/Blog-Post.md",),
    ContentType.CASE_STUDY: ("3-Drafting/Case-Study-Post.md",),
    ContentType.USE_CASE: ("3-Drafting/Use-Case-Post.md",),
    ContentType.ARTICLE: ("3-Drafting/Article-Framework.md",),
}


def framework_files_for(content_type: ContentType) -> list[Path]:
    files: list[Path] = []
    for relative in FRAMEWORK_FILES[content_type]:
        path = settings.PROMPT_SKILLS_DIR / relative
        if not path.exists():
            raise FileNotFoundError(f"Missing framework file: {path}")
        files.append(path)
    return files
