import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/cn";

type Tone = "neutral" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral: "text-text-muted hover:bg-bg hover:text-text",
  danger: "text-danger hover:bg-danger-soft"
};

export function IconButton({
  tone = "neutral",
  className,
  children,
  ...rest
}: { tone?: Tone; children?: ReactNode } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "tw-scope inline-flex h-7 w-7 items-center justify-center rounded-control border border-transparent transition-colors disabled:cursor-not-allowed disabled:opacity-55",
        toneClasses[tone],
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
