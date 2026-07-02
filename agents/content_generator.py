from __future__ import annotations
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from llm.client import LLMClient
from models.style_profile import StyleProfile

if TYPE_CHECKING:
    from models.ai_tells_result import AITellsResult
    from models.comparison_result import ComparisonResult


_SEV_ORDER = {"major": 0, "moderate": 1, "minor": 2}

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "content_generator.txt"


def _build_comparison_block(prev_comparison: "ComparisonResult | None") -> str:
    if not prev_comparison:
        return ""
    lines = ["WHAT WENT WRONG IN THE PREVIOUS DRAFT — fix each of these specifically:\n"]
    any_content = False

    if prev_comparison.voice_breaks:
        sorted_breaks = sorted(prev_comparison.voice_breaks, key=lambda vb: _SEV_ORDER.get(vb.severity, 3))[:5]
        lines.append("VOICE BREAKS (you violated these profile rules):")
        for vb in sorted_breaks:
            lines.append(f"  [{vb.severity.upper()}] {vb.pattern_violated}")
            lines.append(f"    You did:    {vb.what_happened}")
            lines.append(f"    Should be:  {vb.what_should_happen}")
        any_content = True

    if prev_comparison.missing_moves:
        lines.append("\nMISSING MOVES (these signature patterns were absent — add them):")
        for mm in prev_comparison.missing_moves[:4]:
            lines.append(f"  {mm.move}")
            lines.append(f"    Expected: {mm.expected_frequency}  |  You had: {mm.actual_frequency}")
        any_content = True

    if hasattr(prev_comparison, "overfitting_signals") and prev_comparison.overfitting_signals:
        lines.append("\nOVERDONE PATTERNS / OVERFITTING (you over-applied these rules; soften and modulate them):")
        for osig in prev_comparison.overfitting_signals[:4]:
            lines.append(f"  [{osig.severity.upper()}] {osig.dimension_or_pattern}")
            lines.append(f"    Evidence:       {osig.evidence}")
            lines.append(f"    Recommendation: {osig.recommendation}")
        any_content = True

    if not any_content:
        return ""
    return "\n".join(lines) + "\n\n"


class ContentGenerator:
    """
    Agent 2: Structure + StyleProfile → article text.
    The structure is an outline/skeleton provided by the user.
    The voice profile tells it HOW to write — not what to write about.
    Never receives article_text.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._system_prompt = _PROMPT_PATH.read_text()

    def generate(
        self,
        topic: str,
        style_profile: StyleProfile,
        structure: Optional[str] = None,
        skeleton: Optional[str] = None,
        prev_tells: Optional["AITellsResult"] = None,
        prev_comparison: Optional["ComparisonResult"] = None,
        iteration_history: Optional[list[dict]] = None,
        target_word_count: Optional[int] = None,
    ) -> str:
        voice_description = style_profile.to_prompt_text()

        word_count_line = (
            f"TARGET LENGTH: approximately {target_word_count} words "
            f"(ballpark — stay within ~15% of this).\n\n"
            if target_word_count else ""
        )

        if skeleton:
            structure_block = (
                f"SKELETON:\n"
                f"---\n{skeleton}\n---\n\n"
                f"Follow this skeleton section by section. The skeleton tells you WHAT to write. "
                f"The voice profile tells you HOW.\n\n"
                f"TOPIC: {topic}\n\n"
            )
        elif structure:
            structure_block = (
                f"STRUCTURE:\n"
                f"---\n{structure}\n---\n\n"
            )
        else:
            structure_block = (
                f"TOPIC: {topic}\n\n"
                f"Write a complete article on this topic. "
                f"You decide the structure — focus entirely on voice.\n\n"
            )

        # Score history — tells the generator how previous drafts performed
        # and what kept being flagged, so it can try something different.
        history_block = ""
        if iteration_history and len(iteration_history) >= 1:
            lines = ["PREVIOUS ATTEMPT SCORES:"]
            for rec in iteration_history:
                priorities = ", ".join(rec["top_priorities"]) if rec["top_priorities"] else "none"
                lines.append(
                    f"  Iteration {rec['iteration']}: score={rec['score']:.3f}  "
                    f"still failing: [{priorities}]"
                )
            # Surface patterns that keep failing so the generator actively avoids them
            all_priorities: list[str] = []
            for rec in iteration_history:
                all_priorities.extend(rec["top_priorities"])
            persistent = [p for p in set(all_priorities) if all_priorities.count(p) >= 2]
            if persistent:
                lines.append(
                    f"\n  PERSISTENT FAILURES — previous drafts kept getting these wrong: "
                    f"{', '.join(persistent)}. "
                    f"Your approach to these has not worked. Try differently."
                )
            history_block = "\n".join(lines) + "\n\n"

        # AI-tell corrections — accumulated across all iterations so persistent
        # patterns are flagged with increasing urgency.
        tells_block = ""
        if prev_tells and prev_tells.tells:
            major = [t for t in prev_tells.tells if t.severity == "major"]
            minor = [t for t in prev_tells.tells if t.severity == "minor"]
            lines = [
                "AI WRITING PATTERNS TO AVOID — your previous drafts contained these. "
                "Fix all of them:\n"
            ]
            if major:
                lines.append("MAJOR (immediately signals AI authorship — must not appear):")
                for t in major:
                    lines.append(f"  [{t.pattern}] {t.description}")
            if minor:
                lines.append("MINOR (fix if possible):")
                for t in minor:
                    lines.append(f"  [{t.pattern}] {t.description}")
            tells_block = "\n".join(lines) + "\n\n"

        comparison_block = _build_comparison_block(prev_comparison)

        user_prompt = (
            f"{word_count_line}"
            f"{structure_block}"
            f"{history_block}"
            f"{comparison_block}"
            f"{tells_block}"
            f"{voice_description}"
        )

        return self.client.complete(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,
        )
