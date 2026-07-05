import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/cn";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "sm";

const variantClasses: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-hover border border-transparent",
  secondary: "bg-surface text-text border border-border hover:bg-bg",
  ghost: "bg-transparent text-text-muted border border-transparent hover:bg-bg"
};

const sizeClasses: Record<Size, string> = {
  md: "h-9 px-3.5 text-[13px] gap-2",
  sm: "h-8 px-2.5 text-[12px] gap-1.5"
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  className,
  children,
  disabled,
  ...rest
}: {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  children?: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "tw-scope inline-flex items-center justify-center rounded-control font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55",
        variantClasses[variant],
        sizeClasses[size],
        fullWidth && "w-full",
        className
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <Loader2 size={size === "sm" ? 14 : 16} className="animate-spin" /> : null}
      {children}
    </button>
  );
}
