import type { VoiceGenerateEvent } from "../types";
import { cn } from "../lib/cn";
import { ScoreChart, type ScorePoint } from "./ui/ScoreChart";

function describeEvent(event: VoiceGenerateEvent): string {
  switch (event.type) {
    case "queued":
      return `Queued — up to ${event.max_iterations} iterations`;
    case "stage2_start":
      return "Starting voice-aware generation...";
    case "baseline_done":
      return "Generated neutral baseline for comparison";
    case "profile_extracted":
      return "Extracted initial voice profile from articles";
    case "iteration": {
      const score = typeof event.score === "number" ? event.score.toFixed(3) : event.score;
      const best = typeof event.best_score === "number" ? event.best_score.toFixed(3) : event.best_score;
      return `Iteration ${event.iteration}: score ${score} (best ${best}) — ${event.verdict}`;
    }
    case "rescue":
      return `Iteration ${event.iteration}: rescue attempt ${event.accepted ? "succeeded" : "did not beat best"}`;
    case "pipeline_done":
      return `Refinement loop finished — best score ${typeof event.best_score === "number" ? event.best_score.toFixed(3) : event.best_score}`;
    case "done":
      return `Done — best score ${typeof event.best_score === "number" ? event.best_score.toFixed(3) : event.best_score} (iteration ${event.best_iteration})`;
    case "error":
      return `Error: ${event.message ?? event.error}`;
    default:
      return event.type;
  }
}

export function VoiceRunProgress({ events, error }: { events: VoiceGenerateEvent[]; error: string | null }) {
  const points: ScorePoint[] = events
    .filter((event) => event.type === "iteration" && typeof event.score === "number")
    .map((event) => ({
      key: String(event.iteration),
      label: `iter ${event.iteration}`,
      score: event.score as number
    }));

  return (
    <div className="tw-scope grid gap-3">
      {points.length > 0 ? (
        <div className="rounded-control border border-border-soft bg-bg p-3">
          <ScoreChart points={points} />
        </div>
      ) : null}

      <div className="grid max-h-[220px] gap-2 overflow-y-auto">
        {events.map((event, index) => (
          <div
            key={index}
            className={cn(
              "rounded-control border px-3 py-2 text-[13px]",
              event.type === "error" ? "border-danger/30 bg-danger-soft text-danger" : "border-border-soft bg-surface text-text"
            )}
          >
            {describeEvent(event)}
          </div>
        ))}
        {error ? (
          <div className="rounded-control border border-danger/30 bg-danger-soft px-2.5 py-2 text-[12px] text-danger">{error}</div>
        ) : null}
        {events.length === 0 ? <div className="text-sm text-text-muted">Progress will appear here.</div> : null}
      </div>
    </div>
  );
}
