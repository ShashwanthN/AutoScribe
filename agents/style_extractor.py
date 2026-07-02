from __future__ import annotations
from pathlib import Path
from typing import Optional

from llm.client import LLMClient
from models.style_profile import StyleProfile

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "style_extractor.txt"


class StyleExtractor:
    """
    Agent 1: Article → StyleProfile.
    Extracts abstract structural style characteristics.

    NEW: Can also extract anti-patterns by comparing original article
    with a generated baseline (what the model defaults to without training).
    This creates a dynamic negative_space that constrains the model's
    natural voice instead of just listing what the author does.

    The article_text is consumed here and goes no further downstream
    (except to Agent 3 for comparison — never to Agents 4 or 5).
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def extract(self, article_text: str, generated_baseline: Optional[str] = None) -> StyleProfile:
        """
        Extract style profile from article.

        Args:
            article_text: The original article to analyze
            generated_baseline: Optional generated text (model defaults) to extract anti-patterns from.
                               If provided, compares against original to find what the model does by
                               default that the author never does — those patterns go into negative_space.
        """
        if generated_baseline:
            user_prompt = (
                "Analyze the ORIGINAL ARTICLE's style. Then compare it with the AI GENERATED BASELINE"
                " to identify what the model produces by default that the original author never does.\n\n"
                "ORIGINAL ARTICLE:\n---\n"
                f"{article_text}\n"
                "---\n\n"
                "AI GENERATED BASELINE (default LLM output — no style guidance applied):\n---\n"
                f"{generated_baseline}\n"
                "---\n\n"
                "For the negative_space field: include (a) patterns this author avoids in general,"
                " AND (b) any pattern that appears in the BASELINE but is absent from the ORIGINAL —"
                " these are the model's defaults that must be actively suppressed.\n\n"
                "Remember: describe only HOW it is written, never WHAT it says."
            )
        else:
            user_prompt = (
                "Analyze the following article and produce a StyleProfile JSON.\n\n"
                "ARTICLE:\n"
                "---\n"
                f"{article_text}\n"
                "---\n\n"
                "Remember: describe only HOW it is written, never WHAT it says."
            )

        return self.client.complete_structured(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            response_model=StyleProfile,
            temperature=0.2,
        )
