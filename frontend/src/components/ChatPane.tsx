import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2, Send } from "lucide-react";
import { useTranscript } from "../hooks/useApi";
import { useChatStream, useStartPhase } from "../hooks/useStreams";
import { stripRegenMarker } from "../lib/regenMarker";
import type { Project } from "../types";

export function ChatPane({ project, phase }: { project: Project; phase: "ideation" | "structure" | "drafting" }) {
  const transcript = useTranscript(project.id, phase);
  const chatStream = useChatStream(project.id, phase);
  const startPhase = useStartPhase(project.id, phase);
  const [message, setMessage] = useState("");
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const autoStarted = useRef(false);

  // The agent opens the conversation, not the user: if this phase has no
  // transcript yet, kick off the intro exchange automatically. The ref guard
  // (rather than relying on effect deps) keeps this to a single fire even
  // under React StrictMode's dev-only double-invoke.
  useEffect(() => {
    if (autoStarted.current || !transcript.isSuccess) {
      return;
    }
    if ((transcript.data ?? []).length > 0) {
      return;
    }
    autoStarted.current = true;
    void startPhase.start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transcript.isSuccess, transcript.data]);

  const isBusy = chatStream.isStreaming || startPhase.isStreaming;

  const send = async () => {
    const outgoing = message.trim();
    if (!outgoing || isBusy) {
      return;
    }
    setMessage("");
    setPendingMessage(outgoing);
    await chatStream.start(outgoing);
    setPendingMessage(null);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  };

  const history = transcript.data ?? [];
  const lastMessage = history[history.length - 1];
  const showPending = pendingMessage && !(lastMessage?.role === "user" && lastMessage.content === pendingMessage);

  return (
    <section className="work-panel">
      <div className="panel-heading">
        <div>
          <h2>
            {phase === "ideation"
              ? "Ideation"
              : phase === "structure"
              ? "Structure"
              : "Drafting"}
          </h2>
          <p>
            {phase === "ideation"
              ? "Capture raw material and pressure-test the idea."
              : phase === "structure"
              ? "Resolve the content shape one question at a time."
              : "Iterate and co-create the draft skeleton."}
          </p>
        </div>
      </div>

      <div className="transcript">
        {history.map((item, index) => (
          <div key={`${item.role}-${index}`} className={`message ${item.role}`}>
            <strong>{item.role}{item.model_name ? ` · ${item.model_name}` : ""}</strong>
            <ReactMarkdown>{item.content}</ReactMarkdown>
          </div>
        ))}
        {showPending ? (
          <div className="message user pending-echo">
            <strong>user</strong>
            <ReactMarkdown>{pendingMessage}</ReactMarkdown>
          </div>
        ) : null}
        {startPhase.status === "waiting" ? (
          <div className="message assistant pending">
            <strong>assistant{startPhase.model ? ` · ${startPhase.model}` : ""}</strong>
            <span className="typing-dots">
              <span />
              <span />
              <span />
            </span>
          </div>
        ) : null}
        {startPhase.status === "streaming" ? (
          <div className="message assistant streaming">
            <strong>assistant{startPhase.model ? ` · ${startPhase.model}` : ""}</strong>
            <ReactMarkdown>{stripRegenMarker(startPhase.output)}</ReactMarkdown>
          </div>
        ) : null}
        {chatStream.status === "waiting" ? (
          <div className="message assistant pending">
            <strong>assistant{chatStream.model ? ` · ${chatStream.model}` : ""}</strong>
            <span className="typing-dots">
              <span />
              <span />
              <span />
            </span>
          </div>
        ) : null}
        {chatStream.status === "streaming" ? (
          <div className="message assistant streaming">
            <strong>assistant{chatStream.model ? ` · ${chatStream.model}` : ""}</strong>
            <ReactMarkdown>{stripRegenMarker(chatStream.output)}</ReactMarkdown>
          </div>
        ) : null}
      </div>

      {startPhase.error ? <div className="inline-error">{startPhase.error}</div> : null}
      {chatStream.error ? <div className="inline-error">{chatStream.error}</div> : null}
      <div className="composer">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Add context, answer the question, or push back... (Enter to send, Shift+Enter for a new line)"
          disabled={isBusy}
        />
        <button className="primary icon-button" onClick={send} disabled={isBusy || !message.trim()} title="Send">
          {isBusy ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
        </button>
      </div>
    </section>
  );
}
