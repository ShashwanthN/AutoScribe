import { useState } from "react";
import { Sparkles, X } from "lucide-react";
import { useVoiceTemplates } from "../hooks/useApi";
import type { DraftSource, VoiceGenerateRequest } from "../types";
import { Card, CardHeading } from "./ui/Card";
import { Button } from "./ui/Button";
import { IconButton } from "./ui/IconButton";
import { Tabs } from "./ui/Tabs";

/**
 * Configure-and-start modal only. Generation itself runs in the background
 * once started — this dialog can always be dismissed, and progress is shown
 * inline on the Voice Lab dashboard (see VoiceProfileFolder), since a
 * generation run can take a long time and shouldn't trap the user in a modal.
 */
export function GenerateVoiceDialog({
  onStart,
  onClose
}: {
  onStart: (payload: VoiceGenerateRequest) => void;
  onClose: () => void;
}) {
  const templates = useVoiceTemplates();
  const [draftSource, setDraftSource] = useState<DraftSource>("template");
  const [templateId, setTemplateId] = useState("product-market-fit");
  const [customDraft, setCustomDraft] = useState("");
  const [maxIterations, setMaxIterations] = useState(4);

  const canStart = draftSource === "template" ? Boolean(templateId) : customDraft.trim().length > 0;

  const start = () => {
    onStart({
      draft_source: draftSource,
      template_id: draftSource === "template" ? templateId : undefined,
      custom_draft: draftSource === "custom" ? customDraft : undefined,
      max_iterations: maxIterations
    });
    onClose();
  };

  return (
    <div
      className="tw-scope fixed inset-0 z-[200] grid place-items-center bg-black/40 p-4"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <Card className="max-h-[88vh] w-[min(640px,92vw)] overflow-y-auto">
        <CardHeading
          title="Generate voice"
          description="Runs the voice-aware refinement loop against this person's articles. This can take a while — you can dismiss this dialog and keep working; progress shows on the dashboard."
          action={
            <IconButton title="Close" onClick={onClose}>
              <X size={16} />
            </IconButton>
          }
        />

        <div className="grid gap-3 p-4">
          <Tabs
            value={draftSource}
            onChange={setDraftSource}
            options={[
              { value: "template", label: "Use template" },
              { value: "custom", label: "Use own draft" }
            ]}
          />

          {draftSource === "template" ? (
            <label className="grid gap-1.5 text-[11px] font-semibold text-text-muted">
              Template
              <select
                className="w-full rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
                value={templateId}
                onChange={(event) => setTemplateId(event.target.value)}
              >
                {(templates.data ?? []).map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.label}
                  </option>
                ))}
              </select>
              <span className="font-normal text-text-muted">
                {templates.data?.find((t) => t.id === templateId)?.description}
              </span>
            </label>
          ) : (
            <label className="grid gap-1.5 text-[11px] font-semibold text-text-muted">
              Draft
              <textarea
                className="min-h-[160px] w-full resize-y rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
                placeholder="Paste your own WHAT-only draft to generate the voice on"
                value={customDraft}
                onChange={(event) => setCustomDraft(event.target.value)}
              />
            </label>
          )}

          <label className="grid gap-1.5 text-[11px] font-semibold text-text-muted">
            Max iterations
            <input
              className="w-full rounded-control border border-border bg-surface px-2.5 py-2 text-[13px] text-text-strong outline-none"
              type="number"
              min={1}
              max={10}
              value={maxIterations}
              onChange={(event) => setMaxIterations(Number(event.target.value) || 1)}
            />
          </label>

          <Button fullWidth onClick={start} disabled={!canStart}>
            <Sparkles size={16} />
            Generate
          </Button>
        </div>
      </Card>
    </div>
  );
}
