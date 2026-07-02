from __future__ import annotations

import base64
import re
from pathlib import Path

from server import settings
from server.domain.schemas import VoiceProfile, VoiceProfileDetail

ITER_RE = re.compile(r"iter_(\d+)_style_prompt\.txt$")


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
    if not path.is_relative_to(settings.OUTPUTS_DIR.resolve()):
        raise KeyError(voice_id)
    return path


def _preview(text: str, limit: int = 320) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit].rstrip()}..."


def _profile_from_path(run_dir: Path, prompt_path: Path, source: str, iteration: int | None) -> VoiceProfile:
    text = prompt_path.read_text(encoding="utf-8")
    run_id = run_dir.name
    label_suffix = "final" if source == "final" else f"iter {iteration:02d}"
    return VoiceProfile(
        id=_voice_id_for(prompt_path),
        run_id=run_id,
        label=f"{run_id} ({label_suffix})",
        path=prompt_path.relative_to(settings.ROOT_DIR).as_posix(),
        source=source,
        iteration=iteration,
        mtime=prompt_path.stat().st_mtime,
        preview=_preview(text),
    )


def list_voice_profiles() -> list[VoiceProfile]:
    profiles: list[VoiceProfile] = []
    if not settings.OUTPUTS_DIR.exists():
        return profiles

    for run_dir in sorted(settings.OUTPUTS_DIR.glob("run_two_stage_*"), reverse=True):
        if not run_dir.is_dir():
            continue

        final_path = run_dir / "final_style_prompt.txt"
        if final_path.exists():
            profiles.append(_profile_from_path(run_dir, final_path, "final", None))
            continue

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
            profiles.append(_profile_from_path(run_dir, iter_path, "iter", iteration))

    return profiles


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
