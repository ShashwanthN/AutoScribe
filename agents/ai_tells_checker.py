from __future__ import annotations
from pathlib import Path

from llm.client import LLMClient
from models.ai_tells_result import AITellsResult

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "ai_tells_checker.txt"

_SAMPLE_CHARS = 4000


def _sample(text: str, max_chars: int = _SAMPLE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... middle omitted ...]\n\n" + text[-half:]


class AITellsChecker:
    """
    Universal AI-tell scanner. Runs on every piece of generated content.
    Flags LLM writing patterns that must never appear regardless of voice.
    Does not receive article_text — this is a content-quality check, not a voice check.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def check(self, generated_text: str) -> AITellsResult:
        sample = _sample(generated_text)
        user_prompt = (
            f"Scan this generated text for AI writing tells. "
            f"Be thorough — flag every pattern you find.\n\n"
            f"---\n{sample}\n---"
        )
        return self.client.complete_structured(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=AITellsResult,
            temperature=0.1,
        )
