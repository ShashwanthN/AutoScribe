from __future__ import annotations

import asyncio
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend import settings
from backend.domain.schemas import Article, ArticleCreate, Person, PersonSummary, VoiceRunDetail, VoiceRunSummary
from backend.storage import paths as project_paths

PERSON_ID_RE = re.compile(r"^person_[a-z0-9-]+$")

_PERSON_LOCKS: dict[str, asyncio.Lock] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:48] or "person"


def get_person_lock(person_id: str) -> asyncio.Lock:
    validate_person_id(person_id)
    lock = _PERSON_LOCKS.get(person_id)
    if lock is None:
        lock = asyncio.Lock()
        _PERSON_LOCKS[person_id] = lock
    return lock


def validate_person_id(person_id: str) -> str:
    if not PERSON_ID_RE.match(person_id):
        raise ValueError(f"Invalid person id: {person_id}")
    return person_id


def voices_root() -> Path:
    settings.VOICES_DIR.mkdir(parents=True, exist_ok=True)
    return settings.VOICES_DIR


def person_dir(person_id: str) -> Path:
    validate_person_id(person_id)
    return voices_root() / person_id


def _person_json_path(person_id: str) -> Path:
    return person_dir(person_id) / "person.json"


def _articles_json_path(person_id: str) -> Path:
    return person_dir(person_id) / "articles.json"


def runs_dir(person_id: str) -> Path:
    return person_dir(person_id) / "runs"


def _write_person(person: Person) -> None:
    project_paths.atomic_write_text(
        _person_json_path(person.id),
        json.dumps(person.model_dump(mode="json"), indent=2),
    )


def _read_person(person_id: str) -> Person:
    path = _person_json_path(person_id)
    if not path.exists():
        raise FileNotFoundError(person_id)
    return Person.model_validate_json(path.read_text(encoding="utf-8"))


def _read_articles(person_id: str) -> list[Article]:
    path = _articles_json_path(person_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Article.model_validate(item) for item in data]


def _write_articles(person_id: str, articles: list[Article]) -> None:
    project_paths.atomic_write_text(
        _articles_json_path(person_id),
        json.dumps([a.model_dump(mode="json") for a in articles], indent=2),
    )


def create_person(name: str) -> Person:
    root = voices_root()
    slug = _slugify(name)

    for index in range(1, 100):
        suffix = "" if index == 1 else f"-{index}"
        person_id = f"person_{slug}{suffix}"
        candidate = root / person_id
        if not candidate.exists():
            candidate.mkdir(parents=True)
            break
    else:
        raise RuntimeError("Could not allocate a unique person id")

    now = _now()
    person = Person(
        id=person_id,
        name=name.strip(),
        slug=slug,
        current_run_id=None,
        voice_id=None,
        created_at=now,
        updated_at=now,
    )
    _write_person(person)
    _write_articles(person_id, [])
    runs_dir(person_id).mkdir(parents=True, exist_ok=True)
    return person


def list_persons() -> list[PersonSummary]:
    people: list[PersonSummary] = []
    for path in sorted(voices_root().iterdir(), reverse=True):
        if not path.is_dir():
            continue
        try:
            person = _read_person(path.name)
        except Exception:
            continue
        people.append(summary_for(person))
    return people


def get_person(person_id: str) -> Person:
    return _read_person(person_id)


def summary_for(person: Person) -> PersonSummary:
    run_count = sum(
        1
        for p in runs_dir(person.id).glob("run_two_stage_*")
        if p.is_dir() and (p / "run_meta.json").exists()
    )
    return PersonSummary(
        **person.model_dump(),
        article_count=len(_read_articles(person.id)),
        run_count=run_count,
    )


def rename_person(person_id: str, name: str) -> Person:
    person = _read_person(person_id)
    person.name = name.strip()
    person.updated_at = _now()
    _write_person(person)
    return person


def delete_person(person_id: str) -> None:
    path = person_dir(person_id)
    if not path.exists():
        raise FileNotFoundError(person_id)
    shutil.rmtree(path)
    _PERSON_LOCKS.pop(person_id, None)


def set_current_run(person_id: str, run_id: str, voice_id: str) -> Person:
    person = _read_person(person_id)
    person.current_run_id = run_id
    person.voice_id = voice_id
    person.updated_at = _now()
    _write_person(person)
    return person


def list_articles(person_id: str) -> list[Article]:
    get_person(person_id)
    return _read_articles(person_id)


def add_article(person_id: str, data: ArticleCreate) -> Article:
    get_person(person_id)
    articles = _read_articles(person_id)
    article = Article(
        id=uuid.uuid4().hex[:12],
        title=data.title.strip(),
        text=data.text,
        added_at=_now(),
    )
    articles.append(article)
    _write_articles(person_id, articles)
    return article


def update_article(person_id: str, article_id: str, data: ArticleCreate) -> Article:
    articles = _read_articles(person_id)
    for i, article in enumerate(articles):
        if article.id == article_id:
            updated = Article(
                id=article.id,
                title=data.title.strip(),
                text=data.text,
                added_at=article.added_at,
            )
            articles[i] = updated
            _write_articles(person_id, articles)
            return updated
    raise FileNotFoundError(article_id)


def delete_article(person_id: str, article_id: str) -> None:
    articles = _read_articles(person_id)
    remaining = [a for a in articles if a.id != article_id]
    if len(remaining) == len(articles):
        raise FileNotFoundError(article_id)
    _write_articles(person_id, remaining)


def article_texts(person_id: str) -> list[str]:
    return [a.text for a in _read_articles(person_id) if a.text.strip()]


def _run_meta(run_dir: Path) -> dict:
    meta_path = run_dir / "run_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(run_dir.name)
    return json.loads(meta_path.read_text(encoding="utf-8"))


def list_runs(person_id: str) -> list[VoiceRunSummary]:
    get_person(person_id)
    summaries: list[VoiceRunSummary] = []
    for run_dir in sorted(runs_dir(person_id).glob("run_two_stage_*"), reverse=True):
        if not run_dir.is_dir():
            continue
        try:
            meta = _run_meta(run_dir)
        except FileNotFoundError:
            continue
        summaries.append(VoiceRunSummary.model_validate(meta))
    return summaries


def get_run(person_id: str, run_id: str) -> VoiceRunDetail:
    get_person(person_id)
    run_dir = runs_dir(person_id) / run_id
    meta = _run_meta(run_dir)
    prompt_path = run_dir / "final_style_prompt.txt"
    content_path = run_dir / "final_content.txt"
    return VoiceRunDetail(
        **meta,
        style_prompt=prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None,
        final_content=content_path.read_text(encoding="utf-8") if content_path.exists() else None,
    )


def activate_run(person_id: str, run_id: str) -> Person:
    from backend.storage.voice_profiles import _voice_id_for

    run_dir = runs_dir(person_id) / run_id
    prompt_path = run_dir / "final_style_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(run_id)
    return set_current_run(person_id, run_id, _voice_id_for(prompt_path))


def delete_run(person_id: str, run_id: str) -> None:
    person = get_person(person_id)
    run_dir = runs_dir(person_id) / run_id
    if not run_dir.exists():
        raise FileNotFoundError(run_id)
    shutil.rmtree(run_dir)
    if person.current_run_id == run_id:
        person.current_run_id = None
        person.voice_id = None
        person.updated_at = _now()
        _write_person(person)
