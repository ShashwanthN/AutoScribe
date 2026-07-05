import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

type Tone = "neutral" | "accent" | "success" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-bg text-text-muted border-border",
  accent: "bg-accent-soft text-accent border-accent/30",
  success: "bg-success-soft text-success border-success/25",
  danger: "bg-danger-soft text-danger border-danger/30"
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children?: ReactNode }) {
  return (
    <span
      className={cn(
        "tw-scope inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        toneClasses[tone]
      )}
    >
      {children}
    </span>
  );
}
