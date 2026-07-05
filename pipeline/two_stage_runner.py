from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box

from agents import (
    ContentGenerator,
    SkeletonGenerator,
    StyleComparator,
    StyleExtractor,
)
from agents.prompt_refiner_best_only import PromptRefinerBestOnly
from llm.client import LLMClient, close_detailed_log, enable_detailed_log
from models.ai_tells_result import AITellsResult
from models.comparison_result import ComparisonResult
from models.pipeline_state import IterationRecord, PipelineConfig, PipelineState
from models.style_profile import StyleProfile
from pipeline.convergence import ConvergenceChecker
from pipeline.draft_utils import strip_draft_scaffolding

console = Console()


# ── Utility helpers ────────────────────────────────────────────────────────────

def _client(env_key: str) -> LLMClient:
    model = os.environ.get(env_key, "").strip() or None
    return LLMClient(model_override=model)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _step(label: str) -> None:
    console.print(f"\n[bold cyan]▶ {label}[/bold cyan]")


def _done(label: str) -> None:
    console.print(f"[bold green]✓ {label}[/bold green]")


def _first_two_paragraphs(text: str) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n\n".join(paras[:2])


def _diff_profiles(prev: dict, curr: dict) -> list[dict]:
    """Return list of {field, before, after} for meaningfully changed fields."""
    _FLOAT_FIELDS = {"active_voice_ratio", "formality_register", "emotional_temperature", "reader_directness"}
    changes = []
    for key in curr:
        if key not in prev:
            continue
        pv, cv = prev[key], curr[key]
        if key in _FLOAT_FIELDS:
            try:
                if abs(float(cv) - float(pv)) > 0.05:
                    changes.append({"field": key, "before": pv, "after": cv})
            except (TypeError, ValueError):
                pass
        elif isinstance(cv, list):
            if json.dumps(sorted(str(x) for x in (cv or []))) != json.dumps(sorted(str(x) for x in (pv or []))):
                changes.append({"field": key, "before": pv, "after": cv})
        elif cv != pv:
            changes.append({"field": key, "before": str(pv), "after": str(cv)})
    return changes


def _build_rich_history(records: list) -> list[dict]:
    """Build per-iteration history with profile diffs and generated text samples."""
    rich: list[dict] = []
    prev_profile: dict | None = None
    for rec in records:
        entry: dict = {
            "iteration": rec.iteration,
            "score": rec.score,
            "verdict": rec.relative_verdict,
            "top_priorities": rec.top_priorities,
            "generated_sample": None,
            "style_prompt_sample": None,
            "profile_changes": None,
        }
        try:
            text = Path(rec.generated_content_path).read_text()
            entry["generated_sample"] = _first_two_paragraphs(text)
        except Exception:
            pass
        try:
            prompt_text = Path(rec.style_prompt_path).read_text()
            entry["style_prompt_sample"] = prompt_text[:600]
        except Exception:
            pass
        try:
            curr_profile = json.loads(Path(rec.style_profile_path).read_text())
            if prev_profile is not None:
                entry["profile_changes"] = _diff_profiles(prev_profile, curr_profile)
            prev_profile = curr_profile
        except Exception:
            pass
        rich.append(entry)
    return rich


def _log_profile(profile: StyleProfile) -> None:
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta", expand=False)
    table.add_column("Scale", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("person",                profile.person)
    table.add_row("active_voice_ratio",    f"{profile.active_voice_ratio:.2f}")
    table.add_row("formality_register",    f"{profile.formality_register:.2f}")
    table.add_row("emotional_temperature", f"{profile.emotional_temperature:.2f}")
    table.add_row("reader_directness",     f"{profile.reader_directness:.2f}")
    console.print(table)
    for label, value in [
        ("word_choice_style",        profile.word_choice_style),
        ("sentence_construction",    profile.sentence_construction),
        ("rhythm_description",       profile.rhythm_description),
    ]:
        console.print(f"[bold cyan]{label}:[/bold cyan] {value}")
    if profile.voice_fingerprints:
        console.print("\n[bold]voice_fingerprints:[/bold]")
        for i, fp in enumerate(profile.voice_fingerprints, 1):
            console.print(f"  {i}. {fp.pattern}")
    if profile.negative_space:
        console.print("[bold]negative_space:[/bold]")
        for i, ns in enumerate(profile.negative_space, 1):
            console.print(f"  {i}. {ns}")


def _log_comparison(comparison: ComparisonResult, threshold: float) -> None:
    overall_color = "green" if comparison.score.overall >= threshold else "yellow" if comparison.score.overall >= 0.65 else "red"
    verdict_color = {"better": "green", "worse": "red", "similar": "yellow", "baseline": "dim"}.get(comparison.relative_verdict, "dim")
    console.print(
        f"\n  [bold]Overall score:[/bold] [{overall_color}]{comparison.score.overall:.3f}[/{overall_color}]  "
        f"(threshold: {threshold})  "
        f"converged: {'[green]yes[/green]' if comparison.converged else '[red]no[/red]'}  "
        f"verdict: [{verdict_color}]{comparison.relative_verdict}[/{verdict_color}]"
    )
    if comparison.improvement_areas:
        console.print(f"  [bold green]Improved:[/bold green] {', '.join(comparison.improvement_areas)}")
    if comparison.regression_areas:
        console.print(f"  [bold red]Regressed:[/bold red] {', '.join(comparison.regression_areas)}")
    console.print(f"\n  [bold magenta]Holistic assessment:[/bold magenta]")
    console.print(f"  {comparison.holistic_assessment}")
    if comparison.top_priorities:
        console.print(f"  [bold]Top priorities:[/bold] {', '.join(comparison.top_priorities)}")
    if comparison.score.by_dimension:
        from agents.style_comparator import DIMENSION_WEIGHTS
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold", expand=False)
        table.add_column("Dimension", style="cyan", no_wrap=True)
        table.add_column("Wt", justify="right", style="dim")
        table.add_column("Score", justify="right")
        table.add_column("", width=12)
        for dim, sc in sorted(comparison.score.by_dimension.items(), key=lambda x: x[1]):
            color = "green" if sc >= 0.8 else "yellow" if sc >= 0.6 else "red"
            bar = "█" * int(sc * 10) + "░" * (10 - int(sc * 10))
            wt = DIMENSION_WEIGHTS.get(dim, 0.05)
            table.add_row(dim, f"{wt:.0%}", f"{sc:.2f}", f"[{color}]{bar}[/{color}]")
        console.print(table)


def _log_ai_tells(result: AITellsResult) -> None:
    clean_label = "[green]CLEAN[/green]" if result.clean else "[red]TELLS FOUND[/red]"
    console.print(f"\n  [bold]AI-tell scan:[/bold] {clean_label}  — {result.summary}")
    if result.tells:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold", expand=False)
        table.add_column("Severity", no_wrap=True)
        table.add_column("Pattern", style="cyan", no_wrap=True)
        table.add_column("Description")
        for tell in sorted(result.tells, key=lambda t: (t.severity == "minor", t.pattern)):
            sev_color = "red" if tell.severity == "major" else "yellow"
            table.add_row(
                f"[{sev_color}]{tell.severity.upper()}[/{sev_color}]",
                tell.pattern,
                tell.description,
            )
        console.print(table)


def _log_content_preview(text: str, lines: int = 8) -> None:
    preview = "\n".join(text.splitlines()[:lines])
    if len(text.splitlines()) > lines:
        preview += f"\n[dim]... ({len(text.splitlines())} lines total)[/dim]"
    console.print(Panel(preview, title="Generated content preview", border_style="dim"))


# ── Runner ─────────────────────────────────────────────────────────────────────

class TwoStageRunner:
    """
    Two-stage article generation pipeline.

    Stage 1: Single-pass content skeleton generation
      - SkeletonGenerator produces a markdown skeleton from context + structure
        using original_writing samples only for structural/pacing patterns.

    Stage 2: Voice-aware article generation (skeleton-aware best-only loop)
      - Agent 0: Generate neutral baseline for adversarial stylometry.
      - Agent 1 (StyleExtractor): Extract voice profile from writing samples,
        using baseline to populate negative_space with model-default anti-patterns.
      - Agents 2–4 run the best-only refinement loop:
          - Agent 2 (ContentGenerator): Generate article following skeleton + voice.
          - Agent 3 (StyleComparator): Score against reference voice.
          - Agent 4 (PromptRefinerBestOnly): Refine from best-known profile.
        Regressions trigger a rescue attempt before advancing to the next iteration.

    Key invariants:
    - original_writing texts never written to disk; never passed to ContentGenerator.
    - Stage 2 always refines from best_profile, not a regressed profile.
    - best_profile / best_content track the highest-scoring iteration.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.skeleton_gen = SkeletonGenerator(_client("PRIMARY_SKELETON_GENERATOR"))
        self.extractor    = StyleExtractor(   _client("PRIMARY_STYLE_EXTRACTOR"))
        self.generator    = ContentGenerator( _client("PRIMARY_CONTENT_GENERATOR"))
        self.comparator   = StyleComparator(  _client("PRIMARY_STYLE_COMPARATOR"), threshold=config.threshold)
        self.refiner      = PromptRefinerBestOnly(_client("PRIMARY_PROMPT_REFINER"))
        self.checker      = ConvergenceChecker(
            threshold=config.threshold,
            plateau_patience=config.plateau_patience,
        )

    def run(
        self,
        original_writing: list[str],
        structure: str,
        draft: Optional[str] = None,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ) -> PipelineState:
        run_id = f"run_two_stage_{_timestamp()}"
        run_dir = Path(self.config.output_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        if self.config.detailed_log:
            enable_detailed_log(run_dir / "detailed_log.txt")

        try:
            return self._run(original_writing, structure, run_id, run_dir, draft, progress_cb)
        finally:
            if self.config.detailed_log:
                close_detailed_log()

    def _run(
        self,
        original_writing: list[str],
        structure: str,
        run_id: str,
        run_dir: Path,
        draft: Optional[str] = None,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ) -> PipelineState:
        using_draft = draft is not None
        console.print(Panel(
            f"[bold cyan]Writer Pipeline — Two-Stage Mode[/bold cyan]\n"
            f"Run ID:    {run_id}\n"
            f"Topic:     {self.config.topic}\n"
            + (
                f"Stage 1:   Skipped — using supplied draft as content skeleton\n"
                if using_draft else
                f"Stage 1:   Skeleton generation (single pass)\n"
            )
            + f"Stage 2:   Voice generation ({self.config.max_iterations} max iters, "
            f"threshold {self.config.threshold})\n"
            f"[dim]Stage 1 produces a content skeleton. Stage 2 generates article in the author's voice.[/dim]",
            border_style="cyan",
        ))

        if using_draft:
            skeleton = strip_draft_scaffolding(draft)
            (run_dir / "skeleton.md").write_text(skeleton)
        else:
            skeleton = self._run_stage1(structure, run_dir, original_writing)
        state = self._run_stage2(original_writing, structure, skeleton, run_dir, run_id, progress_cb)
        self._write_portable_artifacts(run_dir, skeleton, structure, state)
        return state

    # ── Stage 1 ────────────────────────────────────────────────────────────────

    def _run_stage1(self, structure: str, run_dir: Path, original_writing: list[str]) -> str:
        context = self.config.context or ""

        console.print(Panel(
            "[bold yellow]Stage 1: Content Skeleton Generation[/bold yellow]",
            border_style="yellow",
        ))

        _step("SkeletonGenerator — creating content skeleton...")
        skeleton = self.skeleton_gen.generate(
            topic=self.config.topic,
            context=context,
            structure=structure,
            original_writing=original_writing,
        )
        _done(f"SkeletonGenerator complete — {len(skeleton)} chars")

        (run_dir / "skeleton.md").write_text(skeleton)
        return skeleton

    # ── Stage 2 ────────────────────────────────────────────────────────────────

    def _run_stage2(
        self,
        original_writing: list[str],
        structure: str,
        skeleton: str,
        run_dir: Path,
        run_id: str,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ) -> PipelineState:
        def _notify(event: dict) -> None:
            if progress_cb is not None:
                progress_cb(event)

        reference_text = "\n\n---ARTICLE BREAK---\n\n".join(original_writing)

        state = PipelineState(
            config=PipelineConfig(
                **{**self.config.model_dump(), "article_hash": _sha256(reference_text)}
            ),
            run_id=run_id,
        )

        console.print(Panel(
            "[bold yellow]Stage 2: Voice-Aware Article Generation[/bold yellow]",
            border_style="yellow",
        ))
        _notify({"type": "stage2_start", "max_iterations": self.config.max_iterations})

        # Agent 0 — neutral baseline for adversarial stylometry
        _step("Agent 0 — Generating neutral baseline for adversarial stylometry...")
        baseline_text = self.extractor.client.complete(
            system_prompt="Write a clear, informative article. Use a natural, confident style.",
            user_prompt=(
                f"Topic: {self.config.topic}\n\n"
                f"Follow this structure:\n{skeleton}"
            ),
            temperature=0.0,
        )
        _done(f"Agent 0 complete — baseline {len(baseline_text)} chars")
        (run_dir / "baseline.txt").write_text(baseline_text)
        _notify({"type": "baseline_done"})

        # Agent 1 — extract voice profile
        _step("Agent 1 — Extracting voice profile from writing samples...")
        style_profile = self.extractor.extract(reference_text, generated_baseline=baseline_text)
        _done("Agent 1 complete — voice profile extracted")
        _log_profile(style_profile)
        _notify({"type": "profile_extracted"})

        best_profile = style_profile
        best_content = ""
        best_generated_text = ""
        prev_comparison: Optional[ComparisonResult] = None
        consecutive_failures: dict[str, int] = {}

        for iteration in range(1, self.config.max_iterations + 1):
            console.print(Rule(
                f"[bold]Iteration {iteration} / {self.config.max_iterations}[/bold]"
                + ("  [dim][best-only mode][/dim]" if iteration > 1 else "")
            ))

            iteration_history = (
                [
                    {
                        "iteration": r.iteration,
                        "score": r.score,
                        "top_priorities": r.top_priorities,
                    }
                    for r in state.iterations
                ]
                or None
            )

            # Agent 2 — generate
            generation_prompt = self._build_stage2_prompt(skeleton, style_profile)
            generated_text = self._generate(
                style_profile, structure, skeleton,
                prev_comparison, iteration_history, iteration,
            )
            content_path = run_dir / f"iter_{iteration:02d}_content.txt"
            content_path.write_text(generated_text)

            # Agent 3 — compare
            _step("Agent 3 — Comparing voice against writing samples...")
            comparison = self.comparator.compare(
                reference_text,
                generated_text,
                style_profile,
                best_generated_text=best_generated_text if best_generated_text else None,
                skeleton=skeleton,
                generation_prompt=generation_prompt,
            )
            _done("Agent 3 complete — comparison result:")
            _log_comparison(comparison, self.config.threshold)
            if comparison.ai_tells_result and not comparison.ai_tells_result.clean:
                _log_ai_tells(comparison.ai_tells_result)

            score = comparison.score.overall

            # Rescue attempt when regression occurs
            accepted_text = generated_text
            accepted_comparison = comparison
            accepted_score = score
            accepted_profile = style_profile

            if score <= state.best_score and best_content != "":
                console.print(
                    f"\n  [bold yellow]⚠ Score {score:.3f} ≤ best {state.best_score:.3f} "
                    f"— launching rescue attempt from best profile...[/bold yellow]"
                )

                # Agent 4 (alternative mode) — rescue from best profile
                _step("Rescue — Agent 4 (alternative mode) refining from best-known profile...")
                rescue_profile = self.refiner.refine(
                    best_profile, comparison, generated_text,
                    article_text=reference_text,
                    skeleton=skeleton,
                    generation_prompt=generation_prompt,
                    alternative_mode=True,
                )
                _done("Rescue — Agent 4 complete")
                _log_profile(rescue_profile)

                _step("Rescue — Agent 2 generating with rescue profile...")
                rescue_generation_prompt = self._build_stage2_prompt(skeleton, rescue_profile)
                rescue_text = self._generate(
                    rescue_profile, structure, skeleton,
                    prev_comparison, iteration_history, iteration,
                )
                (run_dir / f"iter_{iteration:02d}_rescue_content.txt").write_text(rescue_text)

                _step("Rescue — Agent 3 scoring rescue content...")
                rescue_comparison = self.comparator.compare(
                    reference_text, rescue_text, rescue_profile,
                    best_generated_text=best_generated_text if best_generated_text else None,
                    skeleton=skeleton,
                    generation_prompt=rescue_generation_prompt,
                )
                rescue_score = rescue_comparison.score.overall
                _done(f"Rescue — Agent 3 complete  (rescue score: {rescue_score:.3f})")
                _log_comparison(rescue_comparison, self.config.threshold)
                if rescue_comparison.ai_tells_result and not rescue_comparison.ai_tells_result.clean:
                    _log_ai_tells(rescue_comparison.ai_tells_result)

                if rescue_score > state.best_score:
                    accepted_text = rescue_text
                    accepted_comparison = rescue_comparison
                    accepted_score = rescue_score
                    accepted_profile = rescue_profile
                    console.print(
                        f"  [bold green]✓ Rescue succeeded: {rescue_score:.3f} > best {state.best_score:.3f}[/bold green]"
                    )
                else:
                    console.print(
                        f"  [bold red]✗ Rescue failed: {rescue_score:.3f} ≤ best {state.best_score:.3f} "
                        f"— falling back to best profile for next iteration[/bold red]"
                    )
                _notify({
                    "type": "rescue",
                    "iteration": iteration,
                    "rescue_score": rescue_score,
                    "accepted": accepted_score == rescue_score,
                })

            prev_comparison = accepted_comparison

            # Update best
            if accepted_score > state.best_score or best_content == "":
                best_content = accepted_text
                best_generated_text = accepted_text
                best_profile = accepted_profile

            # Track consecutive failures / improvements
            for priority in accepted_comparison.top_priorities:
                consecutive_failures[priority] = consecutive_failures.get(priority, 0) + 1
            for dim in accepted_comparison.improvement_areas:
                consecutive_failures[dim] = 0

            # Save iteration artifacts
            profile_path = run_dir / f"iter_{iteration:02d}_profile.json"
            profile_path.write_text(accepted_profile.model_dump_json(indent=2))
            prompt_path = run_dir / f"iter_{iteration:02d}_style_prompt.txt"
            prompt_path.write_text(self._build_stage2_prompt(skeleton, accepted_profile))
            voice_prompt_path = run_dir / f"iter_{iteration:02d}_voice_prompt.txt"
            voice_prompt_path.write_text(accepted_profile.to_prompt_text())

            record = IterationRecord(
                iteration=iteration,
                score=accepted_score,
                converged=accepted_comparison.converged,
                top_priorities=accepted_comparison.top_priorities,
                generated_content_path=str(content_path),
                style_profile_path=str(profile_path),
                style_prompt_path=str(prompt_path),
                relative_verdict=accepted_comparison.relative_verdict,
            )
            state.record_iteration(record)
            _notify({
                "type": "iteration",
                "iteration": iteration,
                "score": accepted_score,
                "best_score": state.best_score,
                "verdict": accepted_comparison.relative_verdict,
                "converged": accepted_comparison.converged,
                "top_priorities": accepted_comparison.top_priorities,
            })

            # Convergence check
            if not self.config.run_all:
                should_stop, reason = self.checker.check(state.scores())
                if should_stop:
                    state.exit_reason = reason
                    console.print(f"\n[bold green]✓ Stopping: {reason}[/bold green]")
                    break

            # Agent 4 — refine best profile for next iteration
            if iteration < self.config.max_iterations:
                rich_history = _build_rich_history(state.iterations[:-1])

                current_profile_changes: list[dict] | None = None
                if len(state.iterations) >= 2:
                    try:
                        prev_iter = state.iterations[-2]
                        prev_profile_dict = json.loads(
                            Path(prev_iter.style_profile_path).read_text()
                        )
                        current_profile_changes = _diff_profiles(
                            prev_profile_dict, best_profile.model_dump()
                        )
                    except Exception:
                        pass

                _step("Agent 4 — Refining best profile for next iteration...")
                refined_profile = self.refiner.refine(
                    best_profile,
                    accepted_comparison,
                    accepted_text,
                    article_text=reference_text,
                    skeleton=skeleton,
                    generation_prompt=generation_prompt,
                    iteration_history=rich_history,
                    consecutive_failures=(consecutive_failures if consecutive_failures else None),
                    prev_generated_text=(
                        best_generated_text
                        if best_generated_text and best_generated_text != accepted_text
                        else None
                    ),
                    current_profile_changes=current_profile_changes,
                    alternative_mode=False,
                )
                _done("Agent 4 complete — updated profile:")
                _log_profile(refined_profile)
                style_profile = refined_profile

        else:
            state.exit_reason = "max_iterations"

        state.completed_at = datetime.utcnow().isoformat()
        self._write_stage2_outputs(run_dir, state, best_profile, best_content, skeleton)

        console.print(Panel(
            f"[bold green]Done![/bold green]\n"
            f"Best score:  {state.best_score:.3f}  (iteration {state.best_iteration})\n"
            f"Exit reason: {state.exit_reason}\n"
            f"Outputs:     {run_dir}",
            border_style="green",
        ))
        _notify({
            "type": "pipeline_done",
            "best_score": state.best_score,
            "best_iteration": state.best_iteration,
            "exit_reason": state.exit_reason,
        })
        return state

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _generate(
        self,
        profile: StyleProfile,
        structure: str,
        skeleton: str,
        prev_comparison: Optional[ComparisonResult],
        iteration_history: Optional[list[dict]],
        iteration: int,
    ) -> str:
        _step(f"Agent 2 — Generating content on: {self.config.topic[:70]}")
        generated_text = self.generator.generate(
            self.config.topic,
            profile,
            structure=structure,
            skeleton=skeleton,
            prev_tells=prev_comparison.ai_tells_result if prev_comparison else None,
            prev_comparison=prev_comparison,
            iteration_history=iteration_history,
            target_word_count=self.config.target_word_count,
        )
        _done(f"Agent 2 complete — {len(generated_text)} chars generated")
        _log_content_preview(generated_text)
        return generated_text

    def _build_stage1_prompt(self, structure: str) -> str:
        return (
            f"## Stage 1 — Content Skeleton Generator Prompt\n\n"
            f"Copy and paste the following into any AI chat to regenerate a content skeleton.\n\n"
            f"---\n\n"
            f"TOPIC: {self.config.topic}\n\n"
            f"DOMAIN CONTEXT:\n---\n{self.config.context}\n---\n\n"
            f"ARTICLE STRUCTURE:\n---\n{structure}\n---\n\n"
            f"Instructions:\n"
            f"For each section in the ARTICLE STRUCTURE, produce one flat section block.\n"
            f"Record exactly what the outline says about that section — no editorial additions.\n"
            f"Load relevant DOMAIN CONTEXT into sections scoped to the domain example.\n"
            f"Include any placeholder markers verbatim where the outline specifies them.\n"
            f"Do NOT add suggestions, argument angles, or rhetorical devices not stated in the outline.\n"
        )

    def _build_stage2_prompt(self, skeleton: str, profile: StyleProfile) -> str:
        voice_prompt = profile.to_prompt_text()
        return (
            f"## Stage 2 — Article Generator Prompt\n\n"
            f"Paste this into any AI chat to generate the full article in one shot.\n\n"
            f"---\n\n"
            f"You are writing an article. The skeleton below tells you WHAT to write. "
            f"The voice profile tells you HOW to write it.\n\n"
            f"CONTENT SKELETON:\n---\n{skeleton}\n---\n\n"
            f"{voice_prompt}\n\n"
            f"Write the full article now. Follow the skeleton's content and structure exactly. "
            f"Every sentence must sound like it came from the voice profile above."
        )

    def _write_stage2_outputs(
        self,
        run_dir: Path,
        state: PipelineState,
        best_profile: StyleProfile,
        best_content: str,
        skeleton: str,
    ) -> None:
        (run_dir / "final_style_profile.json").write_text(
            best_profile.model_dump_json(indent=2)
        )
        (run_dir / "final_content.txt").write_text(best_content)
        (run_dir / "run_summary.json").write_text(
            json.dumps(
                {
                    "run_id": state.run_id,
                    "exit_reason": state.exit_reason,
                    "best_score": state.best_score,
                    "best_iteration": state.best_iteration,
                    "threshold": state.config.threshold,
                    "scores": state.scores(),
                    "iterations": [r.model_dump() for r in state.iterations],
                    "started_at": state.started_at,
                    "completed_at": state.completed_at,
                },
                indent=2,
            )
        )
        _step("Writing full generation prompt...")
        (run_dir / "final_style_prompt.txt").write_text(
            self._build_stage2_prompt(skeleton, best_profile)
        )
        (run_dir / "final_voice_prompt.txt").write_text(best_profile.to_prompt_text())
        _done(f"Full prompt written → {run_dir / 'final_style_prompt.txt'}")

    def _write_portable_artifacts(
        self,
        run_dir: Path,
        skeleton: str,
        structure: str,
        state: PipelineState,
    ) -> None:
        best_profile = StyleProfile.model_validate_json(
            (run_dir / "final_style_profile.json").read_text()
        )
        (run_dir / "final_skeleton.md").write_text(skeleton)
        (run_dir / "stage1_prompt.txt").write_text(self._build_stage1_prompt(structure))
        (run_dir / "stage2_prompt.txt").write_text(
            self._build_stage2_prompt(skeleton, best_profile)
        )
        _done("Portable prompts written")
