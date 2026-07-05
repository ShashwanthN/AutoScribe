from __future__ import annotations

import re

SCAFFOLDING_HEADINGS = {
    "source material reconciliation",
    "required input / final decisions for phase 4",
    "guardrails compliance check",
    "resolved counterarguments (in-text anchors for phase 4)",
}

_CONTRACT_PARAGRAPH_RE = re.compile(
    r"^This document is the Phase 3 WHAT-only draft\..*?(?=\n\n)\n\n",
    re.DOTALL | re.MULTILINE,
)


def strip_draft_scaffolding(draft: str) -> str:
    """Remove Phase-3 process scaffolding from a draft before it reaches a
    content/voice generator: the "WHAT-only draft" contract paragraph and any
    ``##`` sections used to record process decisions rather than content
    (source-material reconciliation, required-input placeholders, guardrails
    checklists). Body sections (Reader, Thesis, Body Sequence, Section N...)
    are left untouched.
    """
    text = _CONTRACT_PARAGRAPH_RE.sub("", draft.lstrip(), count=1)

    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            skipping = heading in SCAFFOLDING_HEADINGS
            if skipping:
                continue
        if not skipping:
            kept.append(line)

    result = "\n".join(kept)
    result = re.sub(r"\n{3,}", "\n\n", result).strip() + "\n"
    return result
