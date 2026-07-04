import { ChatPane } from "./ChatPane";
import { GeneratePane } from "./GeneratePane";
import type { Project } from "../types";

export function PhasePanel({ project }: { project: Project }) {
  if (project.phase === "ideation" || project.phase === "structure" || project.phase === "drafting") {
    return <ChatPane key={project.phase} project={project} phase={project.phase} />;
  }
  return <GeneratePane project={project} phase="final" />;
}
