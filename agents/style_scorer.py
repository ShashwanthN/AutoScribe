from __future__ import annotations
from pathlib import Path

from llm.client import LLMClient
from models.evaluation_observations import EvaluationObservations, AISignatureResult, ScoredResult
from models.ai_tells_result import AITellsResult
from models.style_profile import StyleProfile

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "style_scorer.txt"


class StyleScorer:
    """
    Stage 2 of the comparator pipeline.

    Takes qualitative EvaluationObservations + AISignatureResult and converts
    them into numeric dimension scores and finalized structured findings.
    Does not re-read the original article or generated text.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def score(
        self,
        observations: EvaluationObservations,
        sig_result: AISignatureResult,
        tells_result: AITellsResult,
        style_profile: StyleProfile,
    ) -> ScoredResult:
        obs_json = observations.model_dump_json(indent=2)
        sig_json = sig_result.model_dump_json(indent=2)
        tells_json = tells_result.model_dump_json(indent=2)
        profile_text = style_profile.to_prompt_text()

        user_prompt = (
            f"TARGET VOICE PROFILE:\n{profile_text}\n\n"
            f"EVALUATION OBSERVATIONS:\n{obs_json}\n\n"
            f"AI SIGNATURE RESULT:\n{sig_json}\n\n"
            f"AI TELLS RESULT:\n{tells_json}\n\n"
            f"Produce ScoredResult JSON. Convert observations to numeric scores and finalize findings."
        )
        return self.client.complete_structured(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=ScoredResult,
            temperature=0.1,
        )
