import { useState } from "react";
import { Mic, Plus, Trash2 } from "lucide-react";
import { useCreatePerson, useDeletePerson } from "../hooks/useApi";
import type { PersonSummary } from "../types";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { IconButton } from "./ui/IconButton";
import { cn } from "../lib/cn";

export function PersonList({
  people,
  selectedPersonId,
  onSelectPerson
}: {
  people: PersonSummary[];
  selectedPersonId: string | null;
  onSelectPerson: (personId: string) => void;
}) {
  const createPerson = useCreatePerson();
  const deletePerson = useDeletePerson();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setError(null);
    const created = await createPerson.mutateAsync(name.trim());
    setName("");
    onSelectPerson(created.id);
  };

  return (
    <aside className="tw-scope flex h-screen w-72 flex-shrink-0 flex-col border-r border-border bg-surface">
      <div className="px-5 pt-5">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-control bg-accent-soft text-accent">
            <Mic size={16} />
          </div>
          <div>
            <h1 className="m-0 text-[17px] font-bold text-text-strong">Voices</h1>
          </div>
        </div>
        <p className="mt-1.5 mb-0 text-xs text-text-muted">Manage voice profiles by person</p>
      </div>

      <div className="mx-5 mt-5 grid gap-2.5 border-b border-border-soft pb-5">
        <label className="grid gap-1.5 text-[11px] font-semibold text-text-muted">
          Name
          <input
            className="w-full rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Jane Doe"
            onKeyDown={(event) => {
              if (event.key === "Enter") handleCreate();
            }}
          />
        </label>
        {error ? <div className="rounded-control border border-danger/30 bg-danger-soft px-2.5 py-2 text-[12px] text-danger">{error}</div> : null}
        <Button fullWidth onClick={handleCreate} loading={createPerson.isPending}>
          <Plus size={16} />
          New person
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-5 py-4">
        <div className="grid gap-2">
          {people.map((person) => {
            const active = person.id === selectedPersonId;
            return (
              <div
                key={person.id}
                className={cn(
                  "group flex items-center gap-2 rounded-card border p-1 transition-colors",
                  active ? "border-accent bg-accent-soft" : "border-border-soft hover:border-border"
                )}
              >
                <button
                  className="grid min-w-0 flex-1 justify-items-start gap-1 rounded-control px-2.5 py-2 text-left"
                  onClick={() => onSelectPerson(person.id)}
                >
                  <span className="w-full truncate text-[13px] font-semibold text-text-strong">
                    {person.name}
                  </span>
                  <span className="flex flex-wrap items-center gap-1.5 text-[11px] text-text-muted">
                    {person.article_count} corpus · {person.run_count} generations
                    {person.voice_id ? <Badge tone="success">deployed</Badge> : null}
                  </span>
                </button>
                <IconButton
                  tone="danger"
                  title="Delete person"
                  onClick={(event) => {
                    event.stopPropagation();
                    if (confirm(`Delete "${person.name}"? This removes all their articles and voice runs.`)) {
                      deletePerson.mutate(person.id);
                      if (person.id === selectedPersonId) {
                        onSelectPerson("");
                      }
                    }
                  }}
                >
                  <Trash2 size={14} />
                </IconButton>
              </div>
            );
          })}
          {people.length === 0 ? (
            <div className="grid place-items-center rounded-card border border-dashed border-border px-4 py-8 text-center text-[13px] text-text-muted">
              No people yet.
            </div>
          ) : null}
        </div>
      </nav>
    </aside>
  );
}
