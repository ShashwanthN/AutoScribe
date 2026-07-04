import { useState, useEffect } from "react";
import { useProject } from "../hooks/useApi";
import { ProjectHeader } from "./ProjectHeader";
import { PhaseStepper } from "./PhaseStepper";
import { PhasePanel } from "./PhasePanel";
import { StateFileViewer } from "./StateFileViewer";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const projectQuery = useProject(projectId);
  const project = projectQuery.data;

  const [windowWidth, setWindowWidth] = useState(window.innerWidth);
  const [rightPanelWidth, setRightPanelWidth] = useState(() => {
    const saved = localStorage.getItem("rightPanelWidth");
    return saved ? parseInt(saved, 10) : 450;
  });

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isWide = windowWidth > 1180;

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightPanelWidth;

    const doDrag = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - startX;
      // Constraint right panel between 250px and screen width minus 600px
      const newWidth = Math.max(250, Math.min(window.innerWidth - 600, startWidth - deltaX));
      setRightPanelWidth(newWidth);
      localStorage.setItem("rightPanelWidth", newWidth.toString());
    };

    const stopDrag = () => {
      document.removeEventListener("mousemove", doDrag);
      document.removeEventListener("mouseup", stopDrag);
    };

    document.addEventListener("mousemove", doDrag);
    document.addEventListener("mouseup", stopDrag);
  };

  if (projectQuery.isLoading || !project) {
    return <div className="empty-state">Loading project...</div>;
  }

  return (
    <div className={`workspace-grid ${isWide ? "wide" : ""}`}>
      <ProjectHeader key={project.id} project={project} />
      <PhaseStepper project={project} />

      <div className="workspace-content">
        <PhasePanel project={project} />
        {isWide && (
          <>
            <div className="resizer-col" onMouseDown={startResize}>
              <div className="resizer-col-line" />
            </div>
            <div className="workspace-preview" style={{ width: rightPanelWidth }}>
              <StateFileViewer projectId={project.id} />
            </div>
          </>
        )}
      </div>

      {!isWide && <StateFileViewer projectId={project.id} />}
    </div>
  );
}