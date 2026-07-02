from __future__ import annotations
from pathlib import Path

from llm.client import LLMClient
from models.comparison_result import ComparisonResult
from models.style_profile import StyleProfile

_NORMAL_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "prompt_refiner.txt"
_RESCUE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "prompt_refiner_best_only.txt"

_GENERATED_SAMPLE_CHARS = 10000
_PREV_SAMPLE_CHARS = 6000
_ARTICLE_SAMPLE_CHARS = 10000


def _sample(text: str, max_chars: int = _GENERATED_SAMPLE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... remainder omitted ...]\n\n" + text[-half:]


def _trunc(s: str, n: int) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n - 3] + "..."


class PromptRefinerBestOnly:
    """
    Agent 4 variant for the best-only pipeline.

    Accepts alternative_mode=True to switch to the rescue-mode prompt.
    In rescue mode the LLM takes a fundamentally different angle on priority
    fields rather than incrementally refining.
    """

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self._normal_prompt = _NORMAL_PROMPT_PATH.read_text()
        self._rescue_prompt = _RESCUE_PROMPT_PATH.read_text()

    def refine(
        self,
        style_profile: StyleProfile,
        comparison_result: ComparisonResult,
        generated_text: str,
        article_text: str = "",
        skeleton: str | None = None,
        generation_prompt: str | None = None,
        iteration_history: list[dict] | None = None,
        consecutive_failures: dict[str, int] | None = None,
        prev_generated_text: str | None = None,
        current_profile_changes: list[dict] | None = None,
        alternative_mode: bool = False,
    ) -> StyleProfile:
        system_prompt = self._rescue_prompt if alternative_mode else self._normal_prompt

        profile_json = style_profile.model_dump_json(indent=2)
        comparison_json = comparison_result.model_dump_json(indent=2)
        sampled = len(generated_text) > _GENERATED_SAMPLE_CHARS

        # ── Causal chain history block ─────────────────────────────────────
        history_block = ""
        if iteration_history and not alternative_mode:
            recent = iteration_history[-2:]
            lines = ["ITERATION HISTORY — last 2 iterations (what changed and what happened):"]
            for rec in recent:
                verdict = rec.get("verdict", "")
                verdict_tag = {
                    "worse":    " ↓ REGRESSION",
                    "better":   " ↑ IMPROVEMENT",
                    "similar":  " → no change",
                    "baseline": " [baseline]",
                }.get(verdict, "")
                priorities = ", ".join(rec["top_priorities"]) if rec["top_priorities"] else "none"
                lines.append(f"\n  [Iter {rec['iteration']}]{verdict_tag}")
                lines.append(f"    Failing dimensions: {priorities}")

                prompt_sample = rec.get("style_prompt_sample")
                if prompt_sample:
                    lines.append(
                        "    Compiled style prompt given to generator "
                        "(this is what drives generation — not the raw JSON profile):"
                    )
                    for ln in prompt_sample.splitlines()[:12]:
                        lines.append(f"      {ln}")

                changes = rec.get("profile_changes")
                if changes is None:
                    lines.append("    Profile field changes: [baseline — no prior refinement]")
                elif len(changes) == 0:
                    lines.append("    Profile field changes: [none]")
                else:
                    lines.append("    Profile field changes from previous iteration:")
                    for ch in changes[:6]:
                        lines.append(f"      [{ch['field']}]")
                        lines.append(f"        was: {_trunc(ch['before'], 130)}")
                        lines.append(f"        now: {_trunc(ch['after'], 130)}")
                    if len(changes) > 6:
                        lines.append(f"      ... (+{len(changes) - 6} more fields changed)")

                sample = rec.get("generated_sample")
                if sample:
                    lines.append("    Generated output (first 2 paragraphs):")
                    lines.append("    ---")
                    for ln in sample.splitlines():
                        lines.append(f"    {ln}")
                    lines.append("    ---")

                if verdict == "worse" and changes:
                    bad_fields = ", ".join(c["field"] for c in changes)
                    lines.append(f"    ↑ These field changes CAUSED THE REGRESSION: {bad_fields}")
                    lines.append(f"      Do NOT move these fields in the same direction again.")

            all_priorities: list[str] = []
            for rec in recent:
                all_priorities.extend(rec["top_priorities"])
            recurring = [p for p in set(all_priorities) if all_priorities.count(p) >= 2]
            if recurring:
                lines.append(
                    f"\n  RECURRING ISSUES (failed across multiple iterations — previous fixes "
                    f"were ineffective): {', '.join(recurring)}"
                )
            history_block = "\n".join(lines) + "\n\n"

        # ── What the previous refinement actually changed ──────────────────
        current_changes_block = ""
        if current_profile_changes is not None and not alternative_mode:
            if len(current_profile_changes) == 0:
                current_changes_block = (
                    "WHAT THE PREVIOUS REFINEMENT CHANGED: [no fields were modified]\n\n"
                )
            else:
                lines = [
                    "WHAT THE PREVIOUS REFINEMENT CHANGED — the style prompt below was given "
                    "to the generator this iteration. These field edits produced it:"
                ]
                for ch in current_profile_changes[:8]:
                    lines.append(f"  [{ch['field']}]")
                    lines.append(f"    was: {_trunc(ch['before'], 160)}")
                    lines.append(f"    now: {_trunc(ch['after'], 160)}")
                lines.append(
                    f"\nResult: verdict={comparison_result.relative_verdict}"
                )
                if comparison_result.relative_verdict == "worse":
                    lines.append(
                        "→ These field changes MADE THINGS WORSE. Strongly consider reverting "
                        "or taking a completely different approach for these fields."
                    )
                elif comparison_result.relative_verdict == "better":
                    lines.append("→ These changes IMPROVED the score. Build on what worked.")
                else:
                    lines.append("→ These changes had no meaningful effect. Try a different field or approach.")
                current_changes_block = "\n".join(lines) + "\n\n"

        # ── Consecutive failure alert ──────────────────────────────────────
        consecutive_block = ""
        if consecutive_failures and not alternative_mode:
            failing = {k: v for k, v in consecutive_failures.items() if v >= 2}
            if failing:
                dims = ", ".join(
                    f"{k} ({v} consecutive)"
                    for k, v in sorted(failing.items(), key=lambda x: -x[1])
                )
                consecutive_block = (
                    f"CONSECUTIVE FAILURE ALERT — these dimensions have failed {2}+ iterations "
                    f"in a row: {dims}\n"
                    f"Per the CONSECUTIVE FAILURE RULE: fully rewrite these fields from scratch.\n\n"
                )

        # ── Regression warning ─────────────────────────────────────────────
        verdict_block = ""
        if comparison_result.relative_verdict == "worse" and not alternative_mode:
            verdict_block = (
                "REGRESSION WARNING: This iteration scored WORSE than the previous best.\n"
                "The previous profile change made things worse. See 'WHAT THE PREVIOUS "
                "REFINEMENT CHANGED' above for exactly what was modified.\n\n"
            )

        # ── Content comparison block ───────────────────────────────────────
        if (
            prev_generated_text
            and prev_generated_text != generated_text
            and comparison_result.relative_verdict == "worse"
            and not alternative_mode
        ):
            prev_sample = _sample(prev_generated_text, _PREV_SAMPLE_CHARS)
            curr_sample = _sample(generated_text, _PREV_SAMPLE_CHARS)
            content_block = (
                f"PREVIOUS BEST CONTENT (scored higher — what the voice should sound like):\n"
                f"---\n{prev_sample}\n---\n\n"
                f"CURRENT CONTENT (this iteration — what regressed):\n"
                f"---\n{curr_sample}\n---\n\n"
            )
        else:
            content_block = (
                f"GENERATED TEXT (pipeline output — diagnostic evidence only"
                f"{', sampled' if sampled else ''}):\n"
                f"---\n{_sample(generated_text)}\n---\n\n"
            )

        # ── Original article block ─────────────────────────────────────────
        if article_text:
            article_sample = _sample(article_text, _ARTICLE_SAMPLE_CHARS)
            article_sampled = len(article_text) > _ARTICLE_SAMPLE_CHARS
            article_block = (
                f"ORIGINAL ARTICLE — reference voice"
                f"{' (sampled)' if article_sampled else ''}"
                f" (do not quote in output):\n"
                f"---\n{article_sample}\n---\n\n"
            )
        else:
            article_block = ""

        # ── Skeleton / generation prompt block ────────────────────────────
        skeleton_block = ""
        if generation_prompt:
            skeleton_block = (
                f"FULL GENERATION PROMPT (what the generator received — SKELETON IS A WALL):\n"
                f"---\n{generation_prompt}\n---\n"
                f"Content mandated by the skeleton cannot be changed. "
                f"Only adjust VOICE and STYLE dimensions.\n\n"
            )
        elif skeleton:
            skeleton_block = (
                f"CONTENT SKELETON (the structural brief the generator was given — "
                f"use this to understand what it was asked to write):\n"
                f"---\n{skeleton}\n---\n\n"
            )

        # Include AI signature artifacts if detected
        sig_block = ""
        if comparison_result.ai_signature_result and not comparison_result.ai_signature_result.clean:
            sig_json = comparison_result.ai_signature_result.model_dump_json(indent=2)
            sig_block = f"AI SIGNATURE ARTIFACTS (model-introduced style mismatches):\n{sig_json}\n\n"

        user_prompt = (
            f"{verdict_block}"
            f"{consecutive_block}"
            f"{history_block}"
            f"{current_changes_block}"
            f"{skeleton_block}"
            f"CURRENT STYLE PROFILE (the best-known profile — your base):\n{profile_json}\n\n"
            f"{article_block}"
            f"{content_block}"
            f"COMPARISON RESULT (pipeline findings — primary source, trust these):\n{comparison_json}\n\n"
            f"{sig_block}"
            f"Produce the updated StyleProfile JSON. "
            f"Focus adjustments on: {', '.join(comparison_result.top_priorities)}. "
            f"{'Take a completely fresh approach to each priority field — do not refine incrementally.' if alternative_mode else 'If an issue is marked RECURRING, the previous description was not clear enough — rewrite it more concretely, not just tighten it.'} "
            f"Keep dimensions that already score above 0.80 unchanged."
        )
        return self.client.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=StyleProfile,
            temperature=0.5 if alternative_mode else 0.3,
        )
