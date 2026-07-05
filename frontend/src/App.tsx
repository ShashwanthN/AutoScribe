import { useState, useEffect } from "react";
import { FileText, ChevronRight } from "lucide-react";
import { useProjects } from "./hooks/useApi";
import { ProjectSidebar } from "./components/ProjectSidebar";
import { ProjectWorkspace } from "./components/ProjectWorkspace";
import { ActivityLogPane } from "./components/ActivityLogPane";
import { VoiceManager } from "./components/VoiceManager";
import { NavRail } from "./components/ui/NavRail";

type View = "projects" | "voices";

export default function App() {
  const [view, setView] = useState<View>("projects");
  const projects = useProjects();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const activeProjectId = selectedProjectId ?? projects.data?.[0]?.id ?? null;

  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem("isSidebarCollapsed") === "true";
  });

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleSidebar = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("isSidebarCollapsed", next.toString());
      return next;
    });
  };

  // Build gridTemplateColumns dynamically for desktop (2 columns: Sidebar & Workspace)
  const getGridStyle = () => {
    if (windowWidth <= 760) return {};
    const sidebarWidth = isSidebarCollapsed ? "0px" : "280px";
    return {
      gridTemplateColumns: `${sidebarWidth} minmax(0, 1fr)`,
    };
  };

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <NavRail view={view} onChange={setView} />

      {view === "voices" ? (
        <div className="min-w-0 flex-1">
          <VoiceManager />
        </div>
      ) : (
        <main className="app-shell flex-1" style={{ ...getGridStyle(), minWidth: 0 }}>
          <aside className={`sidebar-column ${isSidebarCollapsed ? "collapsed" : ""}`}>
            <ProjectSidebar
              projects={projects.data ?? []}
              selectedProjectId={activeProjectId}
              onSelectProject={setSelectedProjectId}
              onToggleSidebar={toggleSidebar}
            />
            <div className="sidebar-activity-wrapper">
              {activeProjectId ? (
                <ActivityLogPane key={activeProjectId} projectId={activeProjectId} />
              ) : (
                <div className="panel-placeholder">Activity appears here.</div>
              )}
            </div>
          </aside>

          {isSidebarCollapsed && windowWidth > 760 && (
            <button
              className="sidebar-expand-btn"
              onClick={toggleSidebar}
              title="Expand Sidebar"
            >
              <ChevronRight size={16} />
            </button>
          )}

          <section className="workspace">
            {activeProjectId ? (
              <ProjectWorkspace
                key={activeProjectId}
                projectId={activeProjectId}
              />
            ) : (
              <div className="empty-state">
                <FileText size={28} />
                <p>Create a project to start the content pipeline.</p>
              </div>
            )}
          </section>
        </main>
      )}
    </div>
  );
}