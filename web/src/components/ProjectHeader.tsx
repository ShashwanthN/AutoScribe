import { useState } from "react";
import { usePatchProject, useVoices } from "../hooks/useApi";
import { CONTENT_TYPES } from "../constants";
import type { ContentType, Project } from "../types";

export function ProjectHeader({ project }: { project: Project }) {
  const patchProject = usePatchProject(project.id);
  const voices = useVoices();
  const [title, setTitle] = useState(project.title);

  const saveTitle = () => {
    if (title.trim() && title.trim() !== project.title) {
      patchProject.mutate({ title: title.trim() });
    }
  };

  return (
    <header className="project-header">
      <div className="title-group">
        <input
          className="title-input"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          onBlur={saveTitle}
        />
        <span>{project.id}</span>
      </div>
      <div className="header-controls">
        <label>
          Type
          <select
            value={project.content_type}
            onChange={(event) => patchProject.mutate({ content_type: event.target.value as ContentType })}
          >
            {CONTENT_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Voice
          <select
            value={project.voice_id ?? ""}
            onChange={(event) => patchProject.mutate({ voice_id: event.target.value || null })}
          >
            <option value="">No voice selected</option>
            {(voices.data ?? []).map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
