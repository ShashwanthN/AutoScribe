// The reply agent emits a trailing "[[REGEN:YES]]" / "[[REGEN:NO]]" control
// line for the separate regen agent (see server/phases/prompt_assembly.py).
// The backend strips it before persisting to the transcript, but the raw
// live token stream can transiently include it (whole or partial, since it
// arrives token-by-token) before the exchange finishes — strip it for display.
export function stripRegenMarker(text: string): string {
  const idx = text.lastIndexOf("[[REGEN");
  if (idx === -1) {
    return text;
  }
  const tail = text.slice(idx);
  if (/^\[\[REGEN:?(YES|NO)?\]?\]?\s*$/.test(tail)) {
    return text.slice(0, idx).replace(/\n+$/, "");
  }
  return text;
}
