import { usePerson } from "../hooks/useApi";
import { ArticlesFolder } from "./ArticlesFolder";
import { VoiceProfileFolder } from "./VoiceProfileFolder";
import { Card } from "./ui/Card";
import { Badge } from "./ui/Badge";

export function PersonDetail({ personId }: { personId: string }) {
  const person = usePerson(personId);

  if (person.isLoading) {
    return <div className="tw-scope grid min-h-[180px] place-items-center text-text-muted">Loading person...</div>;
  }
  if (!person.data) {
    return <div className="tw-scope grid min-h-[180px] place-items-center text-text-muted">Person not found.</div>;
  }

  return (
    <div className="tw-scope mx-auto grid w-full max-w-6xl gap-4">
      <Card className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <div className="min-w-0">
          <h1 className="m-0 text-[19px] font-bold text-text-strong">{person.data.name}</h1>
          <p className="mt-1 mb-0 flex flex-wrap items-center gap-1.5 text-xs text-text-muted">
            {person.data.article_count} corpus samples · {person.data.run_count} voice generations
            {person.data.voice_id ? (
              <Badge tone="success">voice deployed</Badge>
            ) : (
              <Badge tone="neutral">no voice yet</Badge>
            )}
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-[minmax(0,340px)_minmax(0,1fr)] items-start gap-4">
        <ArticlesFolder personId={personId} />
        <VoiceProfileFolder person={person.data} />
      </div>
    </div>
  );
}
