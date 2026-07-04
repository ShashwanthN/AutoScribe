import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2, Play } from "lucide-react";
import { useGenerateStream } from "../hooks/useStreams";
import type { Project } from "../types";

export function GeneratePane({ project, phase }: { project: Project; phase: "final" }) {
  const stream = useGenerateStream(project.id, phase);
  const [instructions, setInstructions] = useState("");

  const run = () => {
    stream.start({
      instructions: instructions.trim() || undefined,
      voice_id: project.voice_id
    });
  };

  return (
    <section className="work-panel">
      <div className="panel-heading">
        <div>
          <h2>Final Content</h2>
          <p>Render the saved draft through the selected voice prompt.</p>
        </div>
        <button className="primary" onClick={run} disabled={stream.isStreaming}>
          {stream.isStreaming ? <Loader2 className="spin" size={16} /> : <Play size={16} />}
          Generate
        </button>
      </div>

      <textarea
        className="instructions"
        value={instructions}
        onChange={(event) => setInstructions(event.target.value)}
        placeholder="Optional generation instructions"
        disabled={stream.isStreaming}
      />

      {stream.model ? <div className="model-tag">{stream.model}</div> : null}
      {stream.error ? <div className="inline-error">{stream.error}</div> : null}
      <div className="stream-preview">
        {stream.status === "waiting" ? (
          <span className="typing-dots">
            <span />
            <span />
            <span />
          </span>
        ) : stream.output ? (
          <ReactMarkdown>{stream.output}</ReactMarkdown>
        ) : (
          <span>Streaming output appears here.</span>
        )}
      </div>
    </section>
  );
}
