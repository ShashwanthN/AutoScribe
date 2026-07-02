import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiUrl } from "../api/client";
import type { ActivityEvent } from "../types";
import { useMountEffect } from "./useMountEffect";

const EVENT_TYPES = [
  "project_created",
  "project_updated",
  "phase_advanced",
  "llm_call",
  "token",
  "assistant_done",
  "file_changed",
  "error",
  "done"
];

export type LiveStream = {
  key: string;
  phase: string | null;
  label: string;
  kind: "content" | "reasoning";
  text: string;
};

// Raw token events are never appended to the persisted `events` list — a
// single verbose reasoning call can emit thousands of them, which used to
// blow past every downstream cap and push finished calls' marker events
// (llm_call/assistant_done/file_changed/done) out of the window entirely.
// Instead, tokens accumulate into a small, bounded `liveStreams` map (at most
// one entry per open content/reasoning stream) that gets cleared the moment
// its call finishes or errors.
export function useActivityStream(projectId: string) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [liveStreams, setLiveStreams] = useState<Record<string, LiveStream>>({});
  const queryClient = useQueryClient();

  useMountEffect(() => {
    const source = new EventSource(apiUrl(`/projects/${projectId}/activity/stream`));

    const closeStreamsFor = (phase: string | null, label: string) => {
      setLiveStreams((current) => {
        const contentKey = `${phase ?? ""}:${label}:content`;
        const reasoningKey = `${phase ?? ""}:${label}:reasoning`;
        if (!(contentKey in current) && !(reasoningKey in current)) {
          return current;
        }
        const next = { ...current };
        delete next[contentKey];
        delete next[reasoningKey];
        return next;
      });
    };

    const handle = (message: MessageEvent) => {
      // The browser's native EventSource connection-error Event shares the "error"
      // listener with our server-sent "error" data event, but has no `.data` — skip it.
      if (typeof message.data !== "string") {
        return;
      }
      const event = JSON.parse(message.data) as ActivityEvent;
      const label = typeof event.payload.label === "string" ? event.payload.label : undefined;

      if (event.type === "token" && label) {
        const kind = event.payload.kind === "reasoning" ? "reasoning" : "content";
        const key = `${event.phase ?? ""}:${label}:${kind}`;
        setLiveStreams((current) => {
          const existing = current[key];
          const text = (existing?.text ?? "") + String(event.payload.text ?? "");
          return { ...current, [key]: { key, phase: event.phase, label, kind, text } };
        });
        return;
      }

      if (label && (event.type === "assistant_done" || event.type === "error")) {
        closeStreamsFor(event.phase, label);
      }

      setEvents((current) => [...current.slice(-500), event]);

      if (event.type === "file_changed") {
        queryClient.invalidateQueries({ queryKey: ["file", projectId, event.payload.name] });
        queryClient.invalidateQueries({ queryKey: ["project", projectId] });
        queryClient.invalidateQueries({ queryKey: ["projects"] });
      }
    };

    for (const type of EVENT_TYPES) {
      source.addEventListener(type, handle);
    }

    return () => {
      for (const type of EVENT_TYPES) {
        source.removeEventListener(type, handle);
      }
      source.close();
    };
  });

  return { events, liveStreams };
}
