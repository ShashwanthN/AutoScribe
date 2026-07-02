import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Save } from "lucide-react";
import { useSaveFile } from "../hooks/useApi";
import type { PhaseFile } from "../types";

export function FileEditor({ projectId, name, content }: { projectId: string; name: PhaseFile; content: string }) {
  const saveFile = useSaveFile(projectId, name);
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [draft, setDraft] = useState(content);
  const isDirty = draft !== content;

  const save = async () => {
    await saveFile.mutateAsync(draft);
    setMode("view");
  };

  return (
    <div className="file-editor">
      <div className="file-toolbar">
        <div>
          <strong>{name}.md</strong>
          {isDirty ? <span className="dirty">unsaved</span> : null}
        </div>
        <div className="segmented">
          <button className={mode === "view" ? "active" : ""} onClick={() => setMode("view")}>
            View
          </button>
          <button className={mode === "edit" ? "active" : ""} onClick={() => setMode("edit")}>
            Edit
          </button>
          <button className="icon-button secondary" onClick={save} disabled={!isDirty || saveFile.isPending} title="Save">
            <Save size={16} />
          </button>
        </div>
      </div>
      {mode === "edit" ? (
        <textarea className="file-textarea" value={draft} onChange={(event) => setDraft(event.target.value)} />
      ) : (
        <div className="markdown-view">
          {draft.trim() ? <ReactMarkdown>{draft}</ReactMarkdown> : <span>No content yet.</span>}
        </div>
      )}
    </div>
  );
}
