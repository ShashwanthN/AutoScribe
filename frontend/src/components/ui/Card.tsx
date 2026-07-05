import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/cn";

export function Card({
  className,
  children,
  ...rest
}: { children?: ReactNode } & HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "tw-scope bg-surface border border-border rounded-card shadow-card",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeading({
  title,
  description,
  action
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3.5 border-b border-border-soft">
      <div className="min-w-0">
        <h2 className="m-0 text-[15px] font-semibold text-text-strong">{title}</h2>
        {description ? <p className="mt-1 mb-0 text-xs text-text-muted">{description}</p> : null}
      </div>
      {action ? <div className="flex-shrink-0">{action}</div> : null}
    </div>
  );
}
