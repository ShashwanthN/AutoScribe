import { useMemo, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { useRun, useRuns } from "../hooks/useApi";
import { useVoiceGenerateStream } from "../hooks/useVoiceGenerateStream";
import { GenerateVoiceDialog } from "./GenerateVoiceDialog";
import { RunHistory } from "./RunHistory";
import { VoiceRunProgress } from "./VoiceRunProgress";
import type { Person } from "../types";
import { Card, CardHeading } from "./ui/Card";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { ScoreChart, type ScorePoint } from "./ui/ScoreChart";

/** Voice Lab: the deployed voice, the score trend across runs, and the generation log. */
export function VoiceProfileFolder({ person }: { person: Person }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const currentRun = useRun(person.id, person.current_run_id);
  const runs = useRuns(person.id);
  const stream = useVoiceGenerateStream(person.id);

  const points = useMemo<ScorePoint[]>(
    () =>
      [...(runs.data ?? [])]
        .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
        .map((run) => ({
          key: run.run_id,
          label: run.run_id,
          score: run.best_score,
          active: run.run_id === person.current_run_id
        })),
    [runs.data, person.current_run_id]
  );

  // Once the dialog is dismissed, the running generation just lives here on
  // the dashboard for as long as it's in flight — no separate dismiss control.
  const liveVisible = stream.isRunning || stream.events.length > 0;

  return (
    <div className="grid gap-4">
      {liveVisible ? (
        <Card className="border-accent">
          <CardHeading
            title={stream.isRunning ? "Generating voice…" : "Generation finished"}
            description={
              stream.isRunning
                ? "Running in the background — feel free to keep working."
                : "This run has finished."
            }
          />
          <div className="p-4">
            <VoiceRunProgress events={stream.events} error={stream.error} />
          </div>
        </Card>
      ) : null}

      <Card>
        <CardHeading
          title="Deployed voice"
          description={`The active checkpoint used for ${person.name}'s content generation.`}
          action={
            <Button onClick={() => setDialogOpen(true)} disabled={stream.isRunning}>
              {stream.isRunning ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {stream.isRunning ? "Generating…" : person.current_run_id ? "Generate new voice" : "Generate voice"}
            </Button>
          }
        />
        <div className="p-4">
          {person.current_run_id ? (
            currentRun.isLoading ? (
              <span className="text-sm text-text-muted">Loading...</span>
            ) : (
              <>
                <div className="mb-2 flex items-center gap-2">
                  <Badge tone="accent">score {currentRun.data?.best_score?.toFixed(3) ?? "n/a"}</Badge>
                  <span className="font-mono text-xs text-text-muted">{person.current_run_id}</span>
                </div>
                <div className="max-h-[220px] overflow-auto rounded-control border border-border-soft bg-bg p-3">
                  <pre className="m-0 whitespace-pre-wrap font-sans text-sm text-text">
                    {currentRun.data?.style_prompt ?? "No style prompt saved for this run."}
                  </pre>
                </div>
              </>
            )
          ) : (
            <span className="text-sm text-text-muted">No voice deployed yet. Add corpus samples, then generate a voice.</span>
          )}
        </div>
      </Card>

      <Card>
        <CardHeading title="Score trend" description="Best score achieved by each voice generation, in order." />
        <div className="p-4">
          <ScoreChart points={points} />
        </div>
      </Card>

      <Card>
        <CardHeading title="Generation history" description="Every voice generation run for this person." />
        <div className="p-3">
          <RunHistory person={person} />
        </div>
      </Card>

      {dialogOpen ? (
        <GenerateVoiceDialog onStart={(payload) => stream.start(payload)} onClose={() => setDialogOpen(false)} />
      ) : null}
    </div>
  );
}
