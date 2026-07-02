import { useState } from "react";
import { useFile } from "../hooks/useApi";
import { FILE_TABS } from "../constants";
import { FileEditor } from "./FileEditor";
import type { PhaseFile } from "../types";

export function StateFileViewer({ projectId }: { projectId: string }) {
  const [activeFile, setActiveFile] = useState<PhaseFile>("ideation");
  const file = useFile(projectId, activeFile);

  return (
    <section className="state-panel">
      <div className="tabs">
        {FILE_TABS.map((tab) => (
          <button
            key={tab.value}
            className={activeFile === tab.value ? "tab active" : "tab"}
            onClick={() => setActiveFile(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {file.isLoading ? (
        <div className="panel-placeholder">Loading file...</div>
      ) : (
        <FileEditor
          key={`${projectId}-${activeFile}-${file.data?.updated_at ?? "empty"}`}
          projectId={projectId}
          name={activeFile}
          content={file.data?.content ?? ""}
        />
      )}
    </section>
  );
}
