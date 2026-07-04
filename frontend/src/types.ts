export type Phase = "ideation" | "structure" | "drafting" | "final";
export type PhaseFile = "ideation" | "structure" | "draft" | "final_content";
export type ContentType = "linkedin_post" | "blog_post" | "case_study" | "use_case" | "article";

export interface Project {
  id: string;
  title: string;
  slug: string;
  content_type: ContentType;
  phase: Phase;
  voice_id: string | null;
  created_at: string;
  updated_at: string;
  files: Record<PhaseFile, boolean>;
}

export interface ProjectMetadata extends Omit<Project, "files"> {}

export interface VoiceProfile {
  id: string;
  run_id: string;
  label: string;
  path: string;
  source: string;
  iteration: number | null;
  mtime: number;
  preview: string;
}

export interface FilePayload {
  name: PhaseFile;
  content: string;
  updated_at: string | null;
}

export interface TranscriptMessage {
  role: "user" | "assistant" | "system";
  content: string;
  ts?: string;
  model_name?: string;
}

export interface ActivityEvent {
  id: string;
  ts: string;
  project_id: string;
  type: string;
  phase: Phase | string | null;
  payload: Record<string, unknown>;
}

export interface SseFrame {
  id?: string;
  event: string;
  data: ActivityEvent;
}
