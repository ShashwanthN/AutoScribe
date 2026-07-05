import { cn } from "../../lib/cn";

export function Tabs<T extends string>({
  value,
  onChange,
  options
}: {
  value: T;
  onChange: (value: T) => void;
  options: Array<{ value: T; label: string }>;
}) {
  return (
    <div className="tw-scope inline-flex gap-1 rounded-control bg-bg p-1">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-[6px] px-3 py-1.5 text-[13px] font-semibold transition-colors",
            value === option.value
              ? "bg-accent text-white shadow-card"
              : "text-text-muted hover:text-text"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
