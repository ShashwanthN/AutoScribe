import type { ContentType, Phase, PhaseFile } from "./types";

export const CONTENT_TYPES: Array<{ value: ContentType; label: string }> = [
  { value: "linkedin_post", label: "LinkedIn post" },
  { value: "blog_post", label: "Blog post" },
  { value: "case_study", label: "Case study" },
  { value: "use_case", label: "Use case" },
  { value: "article", label: "Article" }
];

export const PHASES: Array<{ value: Phase; label: string }> = [
  { value: "ideation", label: "Ideation" },
  { value: "structure", label: "Structure" },
  { value: "drafting", label: "Drafting" },
  { value: "final", label: "Final" }
];

export const FILE_TABS: Array<{ value: PhaseFile; label: string }> = [
  { value: "ideation", label: "Ideation" },
  { value: "structure", label: "Structure" },
  { value: "draft", label: "Draft" },
  { value: "final_content", label: "Final" }
];
