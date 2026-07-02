import { ChatPane } from "./ChatPane";
import { GeneratePane } from "./GeneratePane";
import type { Project } from "../types";

export function PhasePanel({ project }: { project: Project }) {
  if (project.phase === "ideation" || project.phase === "structure") {
    return <ChatPane project={project} phase={project.phase} />;
  }
  if (project.phase === "drafting") {
    return <GeneratePane project={project} phase="drafting" />;
  }
  return <GeneratePane project={project} phase="final" />;
}
