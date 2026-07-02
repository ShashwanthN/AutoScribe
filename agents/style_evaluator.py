from __future__ import annotations
from pathlib import Path
from typing import Optional

from llm.client import LLMClient
from models.evaluation_observations import EvaluationObservations, AISignatureResult
from models.ai_tells_result import AITellsResult
from models.style_profile import StyleProfile
from agents.ai_signature_detector import AISignatureDetector
from agents.ai_tells_checker import AITellsChecker

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "style_evaluator.txt"
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


class StyleEvaluator:
    """
    Stage 1 of the comparator pipeline.

    Runs two LLM calls in parallel:
    - DimensionEvaluator: pure qualitative observations per dimension (no scores)
    - AISignatureDetector: model-introduced style artifacts

    Returns (EvaluationObservations, AISignatureResult).
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()
        self._sig_detector = AISignatureDetector(client)
        self._tells_checker = AITellsChecker(client)

    def evaluate(
        self,
        article_text: str,
        generated_text: str,
        style_profile: StyleProfile,
        skeleton: Optional[str] = None,
        generation_prompt: Optional[str] = None,
    ) -> tuple[EvaluationObservations, AISignatureResult, AITellsResult]:
        generated_sample = _sample_generated(generated_text)
        profile_text = style_profile.to_prompt_text()

        if generation_prompt:
            context_block = (
                f"GENERATION PROMPT (sent to the generator — SKELETON IS IMMUTABLE):\n"
                f"---\n{generation_prompt}\n---\n\n"
            )
        elif skeleton:
            context_block = (
                f"CONTENT SKELETON (structural reference — check if generated text follows it):\n"
                f"---\n{skeleton}\n---\n\n"
            )
        else:
            context_block = ""

        evaluator_user_prompt = (
            f"TARGET VOICE PROFILE:\n{profile_text}\n\n"
            f"ORIGINAL ARTICLE — full text (reference voice — do not quote in output):\n"
            f"---\n{article_text}\n---\n\n"
            f"{context_block}"
            f"GENERATED TEXT{' (sampled)' if len(generated_text) > _GENERATED_SAMPLE_CHARS else ''}:\n"
            f"---\n{generated_sample}\n---\n\n"
            f"Produce EvaluationObservations JSON. Pure observation only — no numeric scores."
        )

        observations: EvaluationObservations = self.client.complete_structured(
            self._system_prompt,
            evaluator_user_prompt,
            EvaluationObservations,
            0.1,
        )
        sig_result: AISignatureResult = self._sig_detector.detect(
            article_text,
            generated_text,
            style_profile,
        )
        tells_result: AITellsResult = self._tells_checker.check(generated_text)

        return observations, sig_result, tells_result
