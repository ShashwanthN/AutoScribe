from __future__ import annotations
from pathlib import Path
from typing import Optional

from llm.client import LLMClient
from models.ai_signature import AISignatureResult
from models.style_profile import StyleProfile

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ai_signature_detector.txt"
_GENERATED_SAMPLE_CHARS = 6000


def _sample_generated(text: str, max_chars: int = _GENERATED_SAMPLE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    third = max_chars // 3
    opening = text[:third]
    mid_start = len(text) // 2 - third // 2
    middle = text[mid_start: mid_start + third]
    ending = text[-third:]
    return f"{opening}\n\n[... middle sample ...]\n\n{middle}\n\n[... end sample ...]\n\n{ending}"


class AISignatureDetector:
    """
    Detects model-introduced style artifacts: patterns the generator applied
    that the original writer never uses. Distinct from generic AI vocabulary
    detection (AITellsChecker) — this is profile-aware style mismatch detection.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def detect(
        self,
        article_text: str,
        generated_text: str,
        style_profile: StyleProfile,
    ) -> AISignatureResult:
        generated_sample = _sample_generated(generated_text)
        neg_space = (
            "\n".join(f"- {item}" for item in style_profile.negative_space)
            if style_profile.negative_space
            else "none documented"
        )

        user_prompt = (
            f"ORIGINAL ARTICLE (reference — do not quote in output):\n"
            f"---\n{article_text}\n---\n\n"
            f"GENERATED TEXT{' (sampled)' if len(generated_text) > _GENERATED_SAMPLE_CHARS else ''}:\n"
            f"---\n{generated_sample}\n---\n\n"
            f"NEGATIVE SPACE — things the writer NEVER DOES:\n"
            f"{neg_space}\n\n"
            f"Identify model-introduced style artifacts. Produce AISignatureResult JSON."
        )
        return self.client.complete_structured(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=AISignatureResult,
            temperature=0.1,
        )
