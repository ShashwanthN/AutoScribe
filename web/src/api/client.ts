import type {
  ActivityEvent,
  ContentType,
  FilePayload,
  Phase,
  PhaseFile,
  Project,
  ProjectMetadata,
  TranscriptMessage,
  VoiceProfile
} from "../types";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  getProject: (projectId: string) => request<Project>(`/projects/${projectId}`),
  createProject: (payload: { title: string; content_type: ContentType; voice_id?: string | null }) =>
    request<ProjectMetadata>("/projects", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  patchProject: (projectId: string, payload: Partial<{ title: string; content_type: ContentType; voice_id: string | null }>) =>
    request<ProjectMetadata>(`/projects/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  advanceProject: (projectId: string) =>
    request<ProjectMetadata>(`/projects/${projectId}/advance`, { method: "POST" }),
  deleteProject: (projectId: string) =>
    request<void>(`/projects/${projectId}`, { method: "DELETE" }),
  listVoices: () => request<VoiceProfile[]>("/voices"),
  getFile: (projectId: string, name: PhaseFile) =>
    request<FilePayload>(`/projects/${projectId}/files/${name}`),
  saveFile: (projectId: string, name: PhaseFile, content: string) =>
    request<FilePayload>(`/projects/${projectId}/files/${name}`, {
      method: "PUT",
      body: JSON.stringify({ content })
    }),
  getTranscript: (projectId: string, phase: Phase) =>
    request<TranscriptMessage[]>(`/projects/${projectId}/transcript/${phase}`),
  getActivity: (projectId: string) =>
    request<ActivityEvent[]>(`/projects/${projectId}/activity`)
};

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
