import { useState } from "react";
import { Plus, Trash2, ChevronLeft } from "lucide-react";
import { useCreateProject, useDeleteProject, useVoices } from "../hooks/useApi";
import { CONTENT_TYPES, FILE_TABS } from "../constants";
import type { ContentType, Project } from "../types";

export function ProjectSidebar({
  projects,
  selectedProjectId,
  onSelectProject,
  onToggleSidebar
}: {
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (projectId: string) => void;
  onToggleSidebar: () => void;
}) {
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const voices = useVoices();
  const [title, setTitle] = useState("");
  const [contentType, setContentType] = useState<ContentType>("linkedin_post");
  const [voiceId, setVoiceId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!title.trim()) {
      setError("Title is required");
      return;
    }
    setError(null);
    const created = await createProject.mutateAsync({
      title: title.trim(),
      content_type: contentType,
      voice_id: voiceId || null
    });
    setTitle("");
    onSelectProject(created.id);
  };

  return (
    <aside className="sidebar">
      <div className="brand-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>AutoScribe</h1>
          <p>End-To-End Content Generator</p>
        </div>
        <button
          className="icon-button ghost sidebar-collapse-btn"
          onClick={onToggleSidebar}
          title="Collapse Sidebar"
        >
          <ChevronLeft size={16} />
        </button>
      </div>

      <div className="new-project">
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="New content project" />
        </label>
        <label>
          Type
          <select value={contentType} onChange={(event) => setContentType(event.target.value as ContentType)}>
            {CONTENT_TYPES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Voice
          <select value={voiceId} onChange={(event) => setVoiceId(event.target.value)}>
            <option value="">Select later</option>
            {(voices.data ?? []).map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.label}
              </option>
            ))}
          </select>
        </label>
        {error ? <div className="inline-error">{error}</div> : null}
        <button className="primary full" onClick={handleCreate} disabled={createProject.isPending}>
          <Plus size={16} />
          New project
        </button>
      </div>

      <nav className="project-list">
        {projects.map((project) => {
          const completedCount = FILE_TABS.filter((tab) => project.files[tab.value]).length;
          return (
            <div
              key={project.id}
              className={project.id === selectedProjectId ? "project-item active" : "project-item"}
            >
              <button className="project-item-main" onClick={() => onSelectProject(project.id)}>
                <span>{project.title}</span>
                <small>
                  {project.content_type.replaceAll("_", " ")} · {project.phase} · {completedCount}/{FILE_TABS.length} files
                </small>
              </button>
              <button
                className="icon-button ghost"
                title="Delete project"
                onClick={(event) => {
                  event.stopPropagation();
                  if (confirm(`Delete "${project.title}"? This cannot be undone.`)) {
                    deleteProject.mutate(project.id);
                  }
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}