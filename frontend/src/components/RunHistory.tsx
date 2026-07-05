import { useState } from "react";
import { Check, ChevronDown, ChevronRight, Loader2, Trash2 } from "lucide-react";
import { useActivateRun, useDeleteRun, useRun, useRuns } from "../hooks/useApi";
import type { Person } from "../types";
import { Badge } from "./ui/Badge";
import { IconButton } from "./ui/IconButton";
import { cn } from "../lib/cn";

/** Generation history: every voice-generation run for this person, most recent last. */
export function RunHistory({ person }: { person: Person }) {
  const runs = useRuns(person.id);
  const activateRun = useActivateRun(person.id);
  const deleteRun = useDeleteRun(person.id);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  if (runs.isLoading) {
    return <div className="text-sm text-text-muted">Loading generation history...</div>;
  }
  if (!runs.data || runs.data.length === 0) {
    return <div className="text-sm text-text-muted">No runs yet — generate a voice to start the history.</div>;
  }

  return (
    <div className="grid gap-1.5">
      {runs.data.map((run) => {
        const isActive = person.current_run_id === run.run_id;
        const isExpanded = expandedRunId === run.run_id;
        return (
          <div
            key={run.run_id}
            className={cn(
              "rounded-control border",
              isActive ? "border-accent bg-accent-soft" : "border-border-soft bg-surface"
            )}
          >
            <div className="flex items-center gap-2 px-2.5 py-2">
              <IconButton onClick={() => setExpandedRunId(isExpanded ? null : run.run_id)} title="Toggle details">
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </IconButton>
              <span className="w-16 flex-shrink-0 font-mono text-[12px] font-bold text-text-strong">
                {run.best_score?.toFixed(3) ?? "—"}
              </span>
              <span className="min-w-0 flex-1 truncate text-[12px] text-text-muted">
                {run.run_id} · {run.draft_source} · {run.status}
                {run.exit_reason ? ` · ${run.exit_reason}` : ""}
              </span>
              {isActive ? <Badge tone="accent">deployed</Badge> : null}
              <span className="flex flex-shrink-0 gap-1">
                {!isActive ? (
                  <IconButton
                    title="Deploy this run as the active voice"
                    onClick={() => activateRun.mutate(run.run_id)}
                    disabled={activateRun.isPending}
                  >
                    {activateRun.isPending ? <Loader2 className="animate-spin" size={14} /> : <Check size={14} />}
                  </IconButton>
                ) : null}
                <IconButton
                  tone="danger"
                  title="Delete run"
                  onClick={() => {
                    if (confirm(`Delete run ${run.run_id}?`)) {
                      deleteRun.mutate(run.run_id);
                    }
                  }}
                >
                  <Trash2 size={14} />
                </IconButton>
              </span>
            </div>
            {isExpanded ? <RunDetail personId={person.id} runId={run.run_id} /> : null}
          </div>
        );
      })}
    </div>
  );
}

function RunDetail({ personId, runId }: { personId: string; runId: string }) {
  const detail = useRun(personId, runId);
  if (detail.isLoading) {
    return <p className="px-3 pb-3 text-sm text-text-muted">Loading...</p>;
  }
  if (!detail.data) {
    return null;
  }
  return (
    <div className="mx-2.5 mb-2.5 max-h-[240px] overflow-auto rounded-control border border-border-soft bg-bg p-3">
      <pre className="m-0 whitespace-pre-wrap font-sans text-sm text-text">{detail.data.style_prompt ?? "No style prompt saved."}</pre>
    </div>
  );
}
