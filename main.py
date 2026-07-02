#!/usr/bin/env python3
"""
Writter — Two-Stage Voice-Cloning Content Generation Pipeline

Usage:
    python main.py \
        --context context.txt \
        --original-writing sample.md \
        --structure outline.txt \
        --topic "Your Product will Fail! It's not your Fault"
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import config  # noqa: F401 — side effect: load_dotenv()

from rich.console import Console

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Writter — Two-stage voice-cloning content generation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Inputs
    parser.add_argument("--context", metavar="FILE", required=True,
                        help="Path to domain context document (background knowledge for skeleton generation)")
    parser.add_argument("--structure", metavar="FILE", required=True,
                        help="Path to article structure/outline file")
    parser.add_argument("--original-writing", metavar="FILE", action="append",
                        dest="original_writing", required=True,
                        help="Path to a sample article in the target voice (can be specified multiple times)")
    parser.add_argument("--topic",
                        help="Topic for the generated article (optional if structure's first line is the title)")

    # Generation options
    parser.add_argument("--output-dir", default="outputs", metavar="DIR",
                        help="Output directory (default: outputs)")
    parser.add_argument("--max-iterations", type=int, default=6, metavar="N",
                        help="Max voice refinement iterations in Stage 2 (default: 6)")
    parser.add_argument("--threshold", type=float, default=0.85, metavar="F",
                        help="Convergence score threshold (default: 0.85)")
    parser.add_argument("--word-count", type=int, default=None, metavar="N",
                        help="Target word count for the generated article (approximate, ±15%%)")
    parser.add_argument("--run-all", action="store_true",
                        help="Run all iterations regardless of convergence")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--detailed-log", action="store_true",
                        help="Save full LLM input/output for every agent call to detailed_log.txt")

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from models.pipeline_state import PipelineConfig
    from pipeline.two_stage_runner import TwoStageRunner

    # Load context
    context_path = Path(args.context)
    if not context_path.exists():
        console.print(f"[red]Error: context file not found: {context_path}[/red]")
        sys.exit(1)
    context_text = context_path.read_text(encoding="utf-8").strip()
    if not context_text:
        console.print("[red]Error: context file is empty.[/red]")
        sys.exit(1)

    # Load original writing samples
    original_writing: list[str] = []
    for fpath in args.original_writing:
        p = Path(fpath)
        if not p.exists():
            console.print(f"[red]Error: original-writing file not found: {p}[/red]")
            sys.exit(1)
        text = p.read_text(encoding="utf-8").strip()
        if text:
            original_writing.append(text)

    if not original_writing:
        console.print("[red]Error: at least one non-empty --original-writing file required.[/red]")
        sys.exit(1)

    # Load structure
    structure_path = Path(args.structure)
    if not structure_path.exists():
        console.print(f"[red]Error: structure file not found: {structure_path}[/red]")
        sys.exit(1)
    structure = structure_path.read_text(encoding="utf-8").strip()

    # Derive topic
    topic = args.topic or (structure.splitlines()[0].lstrip("#").strip() if structure else "")
    if not topic:
        console.print("[red]Error: provide --topic or a --structure whose first line is the title.[/red]")
        sys.exit(1)

    pipeline_config = PipelineConfig(
        topic=topic,
        article_hash="",
        max_iterations=args.max_iterations,
        threshold=args.threshold,
        output_dir=args.output_dir,
        verbose=args.verbose,
        run_all=args.run_all,
        target_word_count=args.word_count,
        detailed_log=args.detailed_log,
        context=context_text,
    )

    runner = TwoStageRunner(pipeline_config)
    state = runner.run(original_writing, structure=structure)

    run_dir = Path(args.output_dir) / state.run_id
    console.print(f"\n[bold]Run artifacts saved to:[/bold] {run_dir}")
    console.print(f"  final_skeleton.md         — content skeleton from Stage 1")
    console.print(f"  stage1_prompt.txt         — portable skeleton generation prompt")
    console.print(f"  stage2_prompt.txt         — portable one-shot generation prompt")
    console.print(f"  final_style_profile.json  — portable style spec")
    console.print(f"  final_style_prompt.txt    — voice prompt")
    console.print(f"  final_content.txt         — best generated article")
    console.print(f"  run_summary.json          — score progression")


if __name__ == "__main__":
    main()
