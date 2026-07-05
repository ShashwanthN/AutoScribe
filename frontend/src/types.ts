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

export interface Person {
  id: string;
  name: string;
  slug: string;
  current_run_id: string | null;
  voice_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonSummary extends Person {
  article_count: number;
  run_count: number;
}

export interface Article {
  id: string;
  title: string;
  text: string;
  added_at: string;
}

export interface VoiceTemplate {
  id: string;
  label: string;
  description: string;
}

export type DraftSource = "template" | "custom";

export interface VoiceGenerateRequest {
  draft_source: DraftSource;
  template_id?: string | null;
  custom_draft?: string | null;
  max_iterations?: number;
}

export interface VoiceRunSummary {
  run_id: string;
  person_id: string;
  draft_source: string;
  max_iterations: number;
  status: string;
  best_score: number | null;
  best_iteration: number | null;
  exit_reason: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface VoiceRunDetail extends VoiceRunSummary {
  style_prompt: string | null;
  final_content: string | null;
}

export interface VoiceGenerateEvent {
  type: string;
  [key: string]: unknown;
}
