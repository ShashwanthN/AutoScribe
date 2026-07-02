import { useProject } from "../hooks/useApi";
import { ProjectHeader } from "./ProjectHeader";
import { PhaseStepper } from "./PhaseStepper";
import { PhasePanel } from "./PhasePanel";
import { StateFileViewer } from "./StateFileViewer";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const projectQuery = useProject(projectId);
  const project = projectQuery.data;

  if (projectQuery.isLoading || !project) {
    return <div className="empty-state">Loading project...</div>;
  }

  return (
    <div className="workspace-grid">
      <ProjectHeader key={project.id} project={project} />
      <PhaseStepper project={project} />
      <PhasePanel project={project} />
      <StateFileViewer projectId={project.id} />
    </div>
  );
}
