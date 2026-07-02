import { useMemo } from "react";
import { Settings } from "lucide-react";
import { useActivity } from "../hooks/useApi";
import { useActivityStream } from "../hooks/useActivityStream";
import type { ActivityEvent } from "../types";

function dedupeById(events: ActivityEvent[]): ActivityEvent[] {
  const seen = new Set<string>();
  const deduped: ActivityEvent[] = [];
  for (const event of events) {
    if (seen.has(event.id)) {
      continue;
    }
    seen.add(event.id);
    deduped.push(event);
  }
  return deduped;
}

export function ActivityLogPane({ projectId }: { projectId: string }) {
  const history = useActivity(projectId);
  const { events: live, liveStreams } = useActivityStream(projectId);

  // Neither history (server-filtered) nor live (never accumulates raw
  // tokens — see useActivityStream) can grow unbounded, so this list stays
  // small: it's just the finished-call marker events for the whole session.
  const finished = useMemo(
    () => dedupeById([...(history.data ?? []), ...live]).slice(-400).reverse(),
    [history.data, live]
  );
  const streaming = Object.values(liveStreams);

  return (
    <div className="activity-panel">
      <div className="activity-heading">
        <Settings size={16} />
        <h2>Activity</h2>
      </div>
      <div className="activity-list">
        {streaming.map((stream) => (
          <StreamRow key={stream.key} stream={stream} />
        ))}
        {finished.map((event) => (
          <ActivityRow key={event.id} event={event} />
        ))}
        {streaming.length === 0 && finished.length === 0 ? <div className="panel-placeholder">No activity yet.</div> : null}
      </div>
    </div>
  );
}

function StreamRow({ stream }: { stream: { phase: string | null; label: string; kind: string; text: string } }) {
  const preview = stream.text.length > 400 ? `...${stream.text.slice(-400)}` : stream.text;

  return (
    <div className="activity-row token-stream live">
      <div className="activity-meta">
        <span>{stream.kind === "reasoning" ? "thinking" : "streaming"}</span>
        <small>{stream.phase ?? "project"}</small>
      </div>
      <strong>{stream.label}</strong>
      {preview ? <p>{preview}</p> : null}
    </div>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const payload = event.payload;
  const label = typeof payload.label === "string" ? payload.label : event.type;
  const text =
    typeof payload.text === "string"
      ? payload.text
      : typeof payload.message === "string"
        ? payload.message
        : typeof payload.name === "string"
          ? payload.name
          : "";

  return (
    <div className={`activity-row ${event.type}`}>
      <div className="activity-meta">
        <span>{event.type}</span>
        <small>{event.phase ?? "project"}</small>
      </div>
      <strong>{label}</strong>
      {text ? <p>{text.length > 220 ? `${text.slice(0, 220)}...` : text}</p> : null}
    </div>
  );
}
