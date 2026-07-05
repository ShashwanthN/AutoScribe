import { useState } from "react";
import { Users } from "lucide-react";
import { usePersons } from "../hooks/useApi";
import { PersonList } from "./PersonList";
import { PersonDetail } from "./PersonDetail";

export function VoiceManager() {
  const persons = usePersons();
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  const activePersonId = selectedPersonId ?? persons.data?.[0]?.id ?? null;

  return (
    <main className="tw-scope flex h-screen w-full overflow-hidden bg-bg">
      <PersonList
        people={persons.data ?? []}
        selectedPersonId={activePersonId}
        onSelectPerson={setSelectedPersonId}
      />

      <section className="min-w-0 flex-1 overflow-y-auto p-5">
        {activePersonId ? (
          <PersonDetail key={activePersonId} personId={activePersonId} />
        ) : (
          <div className="grid h-full min-h-[240px] place-items-center gap-2 text-center text-text-muted">
            <Users size={28} />
            <p className="m-0">Create a person to start managing their voice.</p>
          </div>
        )}
      </section>
    </main>
  );
}
