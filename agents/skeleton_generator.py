from __future__ import annotations
from pathlib import Path
from llm.client import LLMClient

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "skeleton_generator.txt"


class SkeletonGenerator:
    """
    Stage 1, Agent A: context + structure + original_writing + topic → markdown skeleton (str).

    Never receives article_text. The original_writing inputs are used only for
    argument-pacing patterns, not voice extraction.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def generate(
        self,
        topic: str,
        context: str,
        structure: str,
        original_writing: list[str],
    ) -> str:
        writing_block = self._build_writing_block(original_writing)

        user_prompt = (
            f"TOPIC: {topic}\n\n"
            f"DOMAIN CONTEXT:\n---\n{context}\n---\n\n"
            f"ARTICLE STRUCTURE:\n---\n{structure}\n---\n\n"
            f"{writing_block}"
            f"Now produce the content skeleton."
        )
        return self.client.complete(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
        )

    def _build_writing_block(self, original_writing: list[str]) -> str:
        if not original_writing:
            return ""
        samples = "\n\n---SAMPLE BREAK---\n\n".join(
            f"[Sample {i+1}]\n{text[:3000]}"
            for i, text in enumerate(original_writing[:3])
        )
        return (
            f"WRITING SAMPLES — use ONLY to understand argument-building patterns "
            f"(claim ordering, pacing, when examples appear, how sections open/close). "
            f"NOT for voice or vocabulary:\n"
            f"---\n{samples}\n---\n\n"
        )
