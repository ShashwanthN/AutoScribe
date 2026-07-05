import { FileText, Mic } from "lucide-react";
import { cn } from "../../lib/cn";

type View = "projects" | "voices";

export function NavRail({ view, onChange }: { view: View; onChange: (view: View) => void }) {
  const items: Array<{ id: View; label: string; icon: typeof FileText }> = [
    { id: "projects", label: "Projects", icon: FileText },
    { id: "voices", label: "Voices", icon: Mic }
  ];

  return (
    <nav className="tw-scope flex h-screen w-14 flex-shrink-0 flex-col items-center gap-2 border-r border-border bg-surface py-4 shadow-rail">
      {items.map((item) => {
        const Icon = item.icon;
        const active = view === item.id;
        return (
          <button
            key={item.id}
            title={item.label}
            aria-label={item.label}
            onClick={() => onChange(item.id)}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-control border transition-colors",
              active
                ? "border-transparent bg-accent text-white shadow-card"
                : "border-transparent text-text-muted hover:bg-bg hover:text-text"
            )}
          >
            <Icon size={18} />
          </button>
        );
      })}
    </nav>
  );
}
