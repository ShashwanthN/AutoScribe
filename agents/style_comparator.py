from __future__ import annotations
from pathlib import Path
from typing import Optional

from llm.client import LLMClient
from models.comparison_result import ComparisonResult
from models.style_profile import StyleProfile
from agents.style_evaluator import StyleEvaluator
from agents.style_scorer import StyleScorer
from agents.style_verdict import StyleVerdict

# Dimension weights — must sum to 1.0.
# Changing a weight here automatically changes scoring — no prompt edit needed.
DIMENSION_WEIGHTS: dict[str, float] = {
    "word_choice":        0.10,
    "sentence_rhythm":    0.10,
    "voice_fingerprints": 0.10,
    "sentence_openers":   0.08,
    "sentence_endings":   0.08,
    "punctuation":        0.08,
    "emphasis_moves":     0.08,
    "hedging":            0.02,
    "argument_structure": 0.02,
    "structure_adherence": 0.10,
    "ai_tells":           0.10,
    "tonal_register":     0.08,
    "overfitting":        0.06,
}


def _compute_overall(by_dimension: dict[str, float]) -> float:
    """
    Deterministic weighted average of dimension scores.
    Missing base dimensions default to 0.5. Custom/dynamic dimensions get 0.05.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for dim, weight in DIMENSION_WEIGHTS.items():
        score = by_dimension.get(dim, 0.5)
        weighted_sum += score * weight
        total_weight += weight
    for dim, score in by_dimension.items():
        if dim not in DIMENSION_WEIGHTS:
            weight = 0.05
            weighted_sum += score * weight
            total_weight += weight
    if total_weight == 0:
        return 0.0
    return round(weighted_sum / total_weight, 4)


class StyleComparator:
    """
    Agent 3: Original article + Generated text + StyleProfile → ComparisonResult.

    Internally runs a 3-stage sub-agent pipeline:
      Stage 1 (parallel): StyleEvaluator (dimension observations) + AISignatureDetector
      Stage 2: StyleScorer (observations → numeric scores + finalized findings)
      Stage 3: StyleVerdict (relative verdict, priorities, convergence, assessment)

    External API is unchanged — same inputs, same ComparisonResult output.
    """

    def __init__(self, client: LLMClient, threshold: float = 0.85) -> None:
        self.client = client
        self.threshold = threshold
        self._evaluator = StyleEvaluator(client)
        self._scorer = StyleScorer(client)
        self._verdict = StyleVerdict(client)

    def compare(
        self,
        article_text: str,
        generated_text: str,
        style_profile: StyleProfile,
        best_generated_text: Optional[str] = None,
        skeleton: Optional[str] = None,
        generation_prompt: Optional[str] = None,
    ) -> ComparisonResult:
        # Stage 1 — parallel: dimension observations + AI signature detection + AI tells
        observations, sig_result, tells_result = self._evaluator.evaluate(
            article_text=article_text,
            generated_text=generated_text,
            style_profile=style_profile,
            skeleton=skeleton,
            generation_prompt=generation_prompt,
        )

        # Stage 2 — score: observations → numeric scores + finalized findings
        scored = self._scorer.score(
            observations=observations,
            sig_result=sig_result,
            tells_result=tells_result,
            style_profile=style_profile,
        )

        # Code — deterministic weighted average (no LLM variance in the convergence metric)
        overall = _compute_overall(scored.by_dimension)

        # Stage 3 — verdict: relative verdict, priorities, holistic assessment, convergence
        result = self._verdict.verdict(
            scored=scored,
            overall_score=overall,
            threshold=self.threshold,
            best_generated_text=best_generated_text,
        )

        return result
