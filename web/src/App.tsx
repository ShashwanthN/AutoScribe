import { useState } from "react";
import { FileText } from "lucide-react";
import { useProjects } from "./hooks/useApi";
import { ProjectSidebar } from "./components/ProjectSidebar";
import { ProjectWorkspace } from "./components/ProjectWorkspace";
import { ActivityLogPane } from "./components/ActivityLogPane";

export default function App() {
  const projects = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const activeProjectId = selectedProjectId ?? projects.data?.[0]?.id ?? null;

  return (
    <main className="app-shell">
      <ProjectSidebar
        projects={projects.data ?? []}
        selectedProjectId={activeProjectId}
        onSelectProject={setSelectedProjectId}
      />
      <section className="workspace">
        {activeProjectId ? (
          <ProjectWorkspace key={activeProjectId} projectId={activeProjectId} />
        ) : (
          <div className="empty-state">
            <FileText size={28} />
            <p>Create a project to start the content pipeline.</p>
          </div>
        )}
      </section>
      <aside className="activity-column">
        {activeProjectId ? (
          <ActivityLogPane key={activeProjectId} projectId={activeProjectId} />
        ) : (
          <div className="panel-placeholder">Activity appears here.</div>
        )}
      </aside>
    </main>
  );
}
