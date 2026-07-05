import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiUrl } from "../api/client";
import { readSseStream } from "../lib/sse";
import type { VoiceGenerateEvent, VoiceGenerateRequest } from "../types";

export interface VoiceGenerateState {
  isRunning: boolean;
  events: VoiceGenerateEvent[];
  error: string | null;
  doneEvent: VoiceGenerateEvent | null;
}

export function useVoiceGenerateStream(personId: string) {
  const queryClient = useQueryClient();
  const inFlight = useRef(false);
  const [state, setState] = useState<VoiceGenerateState>({
    isRunning: false,
    events: [],
    error: null,
    doneEvent: null
  });

  const start = async (payload: VoiceGenerateRequest) => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    setState({ isRunning: true, events: [], error: null, doneEvent: null });

    try {
      const response = await fetch(apiUrl(`/persons/${personId}/generate`), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      await readSseStream(response.body, (frame) => {
        const event = frame.data as unknown as VoiceGenerateEvent;
        setState((current) => ({ ...current, events: [...current.events, event] }));
        if (frame.event === "error") {
          setState((current) => ({ ...current, error: String(event.message ?? "Generation failed") }));
        }
        if (frame.event === "done") {
          setState((current) => ({ ...current, doneEvent: event }));
          queryClient.invalidateQueries({ queryKey: ["runs", personId] });
          queryClient.invalidateQueries({ queryKey: ["person", personId] });
          queryClient.invalidateQueries({ queryKey: ["persons"] });
          queryClient.invalidateQueries({ queryKey: ["voices"] });
        }
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Generation failed"
      }));
    } finally {
      setState((current) => ({ ...current, isRunning: false }));
      inFlight.current = false;
    }
  };

  return { ...state, start };
}
