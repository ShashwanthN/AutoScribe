import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiUrl } from "../api/client";
import { readSseStream } from "../lib/sse";
import type { ActivityEvent, Phase } from "../types";

type StreamStatus = "idle" | "waiting" | "streaming";

type StreamState = {
  isStreaming: boolean;
  status: StreamStatus;
  model: string | null;
  output: string;
  error: string | null;
};

function useStreamState() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    status: "idle",
    model: null,
    output: "",
    error: null
  });

  const startState = () => setState({ isStreaming: true, status: "waiting", model: null, output: "", error: null });
  const setModel = (model: string) => setState((current) => ({ ...current, model }));
  const appendOutput = (text: string) =>
    setState((current) => ({ ...current, status: "streaming", output: current.output + text }));
  const setError = (message: string) =>
    setState((current) => ({ ...current, error: message }));
  const stopState = () =>
    setState((current) => ({ ...current, isStreaming: false, status: "idle" }));

  return { state, startState, setModel, appendOutput, setError, stopState };
}

export function useChatStream(projectId: string, phase: "ideation" | "structure") {
  const queryClient = useQueryClient();
  const stream = useStreamState();
  // React state updates from startState() are batched/async, so a second call
  // fired before re-render would still see isStreaming === false. This ref is
  // checked and set synchronously, so a rapid double-trigger (e.g. an Enter
  // keydown landing right before a Send click) can never launch two parallel
  // LLM exchanges against the same shared stream state.
  const inFlight = useRef(false);

  const start = async (message: string) => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    stream.startState();
    try {
      const response = await fetch(apiUrl(`/projects/${projectId}/phases/${phase}/chat`), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      let transcriptRefreshed = false;
      await readSseStream(response.body, (frame) => {
        const event = frame.data as ActivityEvent;
        if (frame.event === "llm_call" && event.payload.label === `${phase}.reply`) {
          if (typeof event.payload.model === "string") {
            stream.setModel(event.payload.model);
          }
          if (!transcriptRefreshed) {
            // The user's message is persisted server-side before this call is
            // made, so it's already safe to pull the transcript now instead
            // of waiting for the whole (reply + state-regen) exchange to finish.
            transcriptRefreshed = true;
            queryClient.invalidateQueries({ queryKey: ["transcript", projectId, phase] });
          }
        }
        if (frame.event === "token" && event.payload.label === `${phase}.reply` && event.payload.kind === "content") {
          stream.appendOutput(String(event.payload.text ?? ""));
        }
        if (frame.event === "error") {
          stream.setError(String(event.payload.message ?? "Stream failed"));
        }
        if (frame.event === "file_changed") {
          queryClient.invalidateQueries({ queryKey: ["file", projectId, event.payload.name] });
          queryClient.invalidateQueries({ queryKey: ["project", projectId] });
          queryClient.invalidateQueries({ queryKey: ["projects"] });
        }
      });

      queryClient.invalidateQueries({ queryKey: ["transcript", projectId, phase] });
    } catch (error) {
      stream.setError(error instanceof Error ? error.message : "Stream failed");
    } finally {
      stream.stopState();
      inFlight.current = false;
    }
  };

  return { ...stream.state, start };
}

export function useStartPhase(projectId: string, phase: "ideation" | "structure") {
  const queryClient = useQueryClient();
  const stream = useStreamState();
  const inFlight = useRef(false);

  const start = async () => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    stream.startState();
    try {
      const response = await fetch(apiUrl(`/projects/${projectId}/phases/${phase}/start`), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}"
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      await readSseStream(response.body, (frame) => {
        const event = frame.data as ActivityEvent;
        if (frame.event === "llm_call" && event.payload.label === `${phase}.intro` && typeof event.payload.model === "string") {
          stream.setModel(event.payload.model);
        }
        if (frame.event === "token" && event.payload.label === `${phase}.intro` && event.payload.kind === "content") {
          stream.appendOutput(String(event.payload.text ?? ""));
        }
        if (frame.event === "error") {
          stream.setError(String(event.payload.message ?? "Failed to start phase"));
        }
      });

      queryClient.invalidateQueries({ queryKey: ["transcript", projectId, phase] });
    } catch (error) {
      stream.setError(error instanceof Error ? error.message : "Failed to start phase");
    } finally {
      stream.stopState();
      inFlight.current = false;
    }
  };

  return { ...stream.state, start };
}

export function useGenerateStream(projectId: string, phase: Extract<Phase, "drafting" | "final">) {
  const queryClient = useQueryClient();
  const stream = useStreamState();
  const inFlight = useRef(false);

  const start = async (payload: { instructions?: string; voice_id?: string | null }) => {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    stream.startState();
    try {
      const response = await fetch(apiUrl(`/projects/${projectId}/phases/${phase}/generate`), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      const expectedLabel = phase === "drafting" ? "drafting.generate" : "final.generate";
      await readSseStream(response.body, (frame) => {
        const event = frame.data as ActivityEvent;
        if (frame.event === "llm_call" && event.payload.label === expectedLabel && typeof event.payload.model === "string") {
          stream.setModel(event.payload.model);
        }
        if (frame.event === "token" && event.payload.label === expectedLabel && event.payload.kind === "content") {
          stream.appendOutput(String(event.payload.text ?? ""));
        }
        if (frame.event === "error") {
          stream.setError(String(event.payload.message ?? "Generation failed"));
        }
        if (frame.event === "file_changed") {
          queryClient.invalidateQueries({ queryKey: ["file", projectId, event.payload.name] });
          queryClient.invalidateQueries({ queryKey: ["project", projectId] });
          queryClient.invalidateQueries({ queryKey: ["projects"] });
        }
      });
    } catch (error) {
      stream.setError(error instanceof Error ? error.message : "Generation failed");
    } finally {
      stream.stopState();
      inFlight.current = false;
    }
  };

  return { ...stream.state, start };
}
