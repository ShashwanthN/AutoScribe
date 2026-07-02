from __future__ import annotations
from pathlib import Path
from typing import Optional

from llm.client import LLMClient
from models.evaluation_observations import ScoredResult, VerdictResult
from models.comparison_result import ComparisonResult, StyleScore

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "style_verdict.txt"
_GENERATED_SAMPLE_CHARS = 6000


def _sample(text: str, max_chars: int = _GENERATED_SAMPLE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    third = max_chars // 3
    opening = text[:third]
    mid_start = len(text) // 2 - third // 2
    middle = text[mid_start: mid_start + third]
    ending = text[-third:]
    return f"{opening}\n\n[... middle sample ...]\n\n{middle}\n\n[... end sample ...]\n\n{ending}"


class StyleVerdict:
    """
    Stage 3 of the comparator pipeline.

    Takes ScoredResult + optional best_generated_text and produces the final
    ComparisonResult by determining relative_verdict, top_priorities,
    holistic_assessment, and convergence.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def verdict(
        self,
        scored: ScoredResult,
        overall_score: float,
        threshold: float,
        best_generated_text: Optional[str] = None,
    ) -> ComparisonResult:
        scored_json = scored.model_dump_json(indent=2)

        best_block = ""
        if best_generated_text:
            best_sample = _sample(best_generated_text)
            best_block = (
                f"BEST PREVIOUS GENERATION (compare new generation against this):\n"
                f"---\n{best_sample}\n---\n\n"
            )

        user_prompt = (
            f"CONVERGENCE THRESHOLD: {threshold}\n"
            f"OVERALL SCORE (computed from weights): {overall_score:.4f}\n\n"
            f"SCORED RESULT:\n{scored_json}\n\n"
            f"{best_block}"
            f"Produce VerdictResult JSON. "
            f"{'Compare new vs best previous generation for relative_verdict.' if best_block else 'No best previous — set relative_verdict=baseline.'}"
        )
        verdict = self.client.complete_structured(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=VerdictResult,
            temperature=0.1,
        )

        return ComparisonResult(
            holistic_assessment=verdict.holistic_assessment,
            voice_breaks=scored.voice_breaks,
            missing_moves=scored.missing_moves,
            overfitting_signals=scored.overfitting_signals,
            score=StyleScore(overall=overall_score, by_dimension=scored.by_dimension),
            dimension_notes=scored.dimension_notes,
            converged=verdict.converged,
            top_priorities=verdict.top_priorities,
            relative_verdict=verdict.relative_verdict,
            improvement_areas=verdict.improvement_areas,
            regression_areas=verdict.regression_areas,
            ai_signature_result=scored.ai_signature_result,
            ai_tells_result=scored.ai_tells_result,
        )
