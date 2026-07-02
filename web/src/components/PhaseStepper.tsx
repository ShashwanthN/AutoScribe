import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import { useAdvancePhase } from "../hooks/useApi";
import { PHASES } from "../constants";
import type { Project } from "../types";

export function PhaseStepper({ project }: { project: Project }) {
  const advance = useAdvancePhase(project.id);
  const activeIndex = PHASES.findIndex((phase) => phase.value === project.phase);
  const [error, setError] = useState<string | null>(null);

  const handleAdvance = async () => {
    setError(null);
    try {
      await advance.mutateAsync();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not advance");
    }
  };

  return (
    <section className="phase-stepper">
      <div className="phase-track">
        {PHASES.map((phase, index) => (
          <div key={phase.value} className={index === activeIndex ? "phase active" : index < activeIndex ? "phase done" : "phase"}>
            {index < activeIndex ? <Check size={14} /> : <span>{index + 1}</span>}
            {phase.label}
          </div>
        ))}
      </div>
      <button className="secondary" onClick={handleAdvance} disabled={project.phase === "final" || advance.isPending}>
        <ArrowRight size={16} />
        Move to next phase
      </button>
      {error ? <div className="inline-error wide">{error}</div> : null}
    </section>
  );
}
