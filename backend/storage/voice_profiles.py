from __future__ import annotations

import base64
import re
from pathlib import Path

from backend import settings
from backend.domain.schemas import VoiceProfile, VoiceProfileDetail

ITER_RE = re.compile(r"iter_(\d+)_style_prompt\.txt$")
VOICE_ITER_RE = re.compile(r"iter_(\d+)_voice_prompt\.txt$")


def _voice_id_for(path: Path) -> str:
    relative = path.relative_to(settings.ROOT_DIR).as_posix()
    encoded = base64.urlsafe_b64encode(relative.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _path_for_voice_id(voice_id: str) -> Path:
    padding = "=" * (-len(voice_id) % 4)
    try:
        relative = base64.urlsafe_b64decode(f"{voice_id}{padding}").decode("utf-8")
    except Exception as exc:
        raise KeyError(voice_id) from exc
    path = (settings.ROOT_DIR / relative).resolve()
    if not (
        path.is_relative_to(settings.OUTPUTS_DIR.resolve())
        or path.is_relative_to(settings.VOICES_DIR.resolve())
    ):
        raise KeyError(voice_id)
    return path


def _preview(text: str, limit: int = 320) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."


def _profile_from_path(
    run_dir: Path,
    prompt_path: Path,
    source: str,
    iteration: int | None,
    label: str | None = None,
) -> VoiceProfile:
    text = prompt_path.read_text(encoding="utf-8")
    run_id = run_dir.name
    label_suffix = "final" if source in ("final", "person") else f"iter {iteration:02d}"
    return VoiceProfile(
        id=_voice_id_for(prompt_path),
        run_id=run_id,
        label=label or f"{run_id} ({label_suffix})",
        path=prompt_path.relative_to(settings.ROOT_DIR).as_posix(),
        source=source,
        iteration=iteration,
        mtime=prompt_path.stat().st_mtime,
        preview=_preview(text),
    )


def _latest_prompt_path(run_dir: Path) -> tuple[Path, str, int | None] | None:
    """Locate the prompt file to use as a reusable voice.

    Prefers the content-agnostic ``*_voice_prompt.txt`` artifacts (pure voice
    profile, no training-run skeleton baked in) so a saved voice can be
    applied to any future draft. Falls back to the older ``*_style_prompt.txt``
    artifacts (which embed the training run's content skeleton) for runs
    produced before this distinction existed.
    """
    final_voice_path = run_dir / "final_voice_prompt.txt"
    if final_voice_path.exists():
        return final_voice_path, "final", None

    latest_voice_iter: tuple[int, Path] | None = None
    for iter_path in run_dir.glob("iter_*_voice_prompt.txt"):
        match = VOICE_ITER_RE.match(iter_path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        if latest_voice_iter is None or iteration > latest_voice_iter[0]:
            latest_voice_iter = (iteration, iter_path)

    if latest_voice_iter is not None:
        iteration, iter_path = latest_voice_iter
        return iter_path, "iter", iteration

    final_path = run_dir / "final_style_prompt.txt"
    if final_path.exists():
        return final_path, "final", None

    latest_iter: tuple[int, Path] | None = None
    for iter_path in run_dir.glob("iter_*_style_prompt.txt"):
        match = ITER_RE.match(iter_path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        if latest_iter is None or iteration > latest_iter[0]:
            latest_iter = (iteration, iter_path)

    if latest_iter is not None:
        iteration, iter_path = latest_iter
        return iter_path, "iter", iteration
    return None


def _list_legacy_profiles() -> list[VoiceProfile]:
    profiles: list[VoiceProfile] = []
    if not settings.OUTPUTS_DIR.exists():
        return profiles

    for run_dir in sorted(settings.OUTPUTS_DIR.glob("run_two_stage_*"), reverse=True):
        if not run_dir.is_dir():
            continue
        found = _latest_prompt_path(run_dir)
        if found is not None:
            prompt_path, source, iteration = found
            profiles.append(_profile_from_path(run_dir, prompt_path, source, iteration))

    return profiles


def _list_person_profiles() -> list[VoiceProfile]:
    from backend.voices import storage as voice_storage

    profiles: list[VoiceProfile] = []
    if not settings.VOICES_DIR.exists():
        return profiles

    for person_dir in sorted(settings.VOICES_DIR.glob("person_*"), reverse=True):
        if not person_dir.is_dir():
            continue
        try:
            person = voice_storage.get_person(person_dir.name)
        except Exception:
            continue
        if not person.current_run_id:
            continue
        run_dir = voice_storage.runs_dir(person.id) / person.current_run_id
        found = _latest_prompt_path(run_dir)
        if found is None:
            continue
        prompt_path, source, iteration = found
        profiles.append(
            _profile_from_path(run_dir, prompt_path, "person", iteration, label=person.name)
        )

    return profiles


def list_voice_profiles() -> list[VoiceProfile]:
    return _list_person_profiles() + _list_legacy_profiles()


def get_voice_profile(voice_id: str) -> VoiceProfileDetail:
    requested_path = _path_for_voice_id(voice_id)
    for profile in list_voice_profiles():
        if profile.id != voice_id:
            continue
        prompt_path = settings.ROOT_DIR / profile.path
        if prompt_path.resolve() != requested_path.resolve():
            raise KeyError(voice_id)
        return VoiceProfileDetail(
            **profile.model_dump(),
            prompt=prompt_path.read_text(encoding="utf-8"),
        )
    raise KeyError(voice_id)
