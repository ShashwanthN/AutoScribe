from __future__ import annotations
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


# Only enums that are unambiguous scales remain
PersonEnum = Literal["first", "second", "third", "mixed"]
ScopeEnum = Literal["universal", "context_sensitive"]


class VoiceFingerprint(BaseModel):
    pattern: str = Field(
        ...,
        description="The structural template of the move — specific enough that a generator can replicate the syntactic shape mechanically. No content references."
    )
    scope: ScopeEnum = Field(
        ...,
        description="'universal' if this pattern appears regardless of content type (a true personal habit). 'context_sensitive' if it only appears because of the current article's genre, format, or subject matter."
    )


class StyleProfile(BaseModel):
    """
    Voice-focused style profile.
    Numeric fields for scales that have unambiguous anchors.
    Free-text fields for everything behavioral — so the generator gets
    a description of what THIS writer does, not a label that each model
    interprets differently.
    """

    # ── Scales (unambiguous anchors, used numerically by the comparator) ──────
    active_voice_ratio: float = Field(
        ..., ge=0, le=1,
        description="0=passive voice dominant, 1=active voice dominant"
    )
    person: PersonEnum = Field(..., description="Grammatical person the writer defaults to")
    formality_register: float = Field(
        ..., ge=0, le=1,
        description="0=casual/conversational, 1=formal/academic"
    )
    emotional_temperature: float = Field(
        ..., ge=0, le=1,
        description="0=detached/analytical, 1=passionate/emotive"
    )
    reader_directness: float = Field(
        ..., ge=0, le=1,
        description="0=reader never addressed, 1=writer constantly speaks to/challenges reader"
    )
    reader_relationship: str = Field(
        ...,
        description="The qualitative nature of the author-reader relationship — how the writer positions themselves relative to the reader. E.g., 'practitioner sharing a hard-won tip with a peer', 'authority issuing challenges to students'. No content references."
    )

    # ── Behavioral descriptions — all free-text ───────────────────────────────

    word_choice_style: str = Field(
        ...,
        description="Vocabulary and word choice habits — register, contractions, plain vs elevated phrasing, colloquialisms. No content references."
    )

    sentence_construction: str = Field(
        ...,
        description="How sentences are built — clause structure, how clauses connect, comma use, typical syntactic shape. No content references."
    )

    punctuation_details: str = Field(
        ...,
        description="Where this writer deviates from standard punctuation conventions. Note absences and additions for each mark. No content references."
    )

    rhythm_description: str = Field(
        ...,
        description="Sentence length rhythm — the actual pattern, concrete enough to replicate. No content references."
    )

    sentence_opener_patterns: str = Field(
        ...,
        description="What this writer uses to start sentences — recurring starters, conjunction openers, adverbs, conditionals. No content references."
    )

    sentence_ending_patterns: str = Field(
        ...,
        description="How sentences typically close — payload placement, trailing qualifiers, paragraph-final patterns. No content references."
    )

    hedging_style: str = Field(
        ...,
        description="How this writer handles uncertainty and qualification — what form it takes and how often. No content references."
    )

    emphasis_style: str = Field(
        ...,
        description="The actual mechanism this writer uses to create emphasis and punch. No content references."
    )

    analogy_style: str = Field(
        ...,
        description="How this writer uses analogies and metaphors — type, placement, length. No content references."
    )

    humor_style: str = Field(
        ...,
        description="How humor appears in this writing, or confirm it is absent. No content references."
    )

    argument_style: str = Field(
        ...,
        description="How this writer structures a point at the paragraph level — the actual move made. No content references."
    )

    jargon_style: str = Field(
        ...,
        description="How this writer handles domain-specific terminology — introduce-then-explain, use without explanation, avoid entirely, etc. No content references."
    )

    parenthetical_style: str = Field(
        ...,
        description="How this writer uses parenthetical asides, or confirm absence. No content references."
    )

    structural_conventions: str = Field(
        ...,
        description="Macro-level formatting habits — headers, paragraph density, word count, lists, special formatting. No content references."
    )

    # ── Open-ended fingerprint fields ─────────────────────────────────────────

    voice_fingerprints: List[VoiceFingerprint] = Field(
        ...,
        description="3 to 7 concrete signature moves that would immediately identify this writer. Each must be an observable behavior a generator can replicate. No content references."
    )

    negative_space: List[str] = Field(
        ...,
        description="3 to 5 things this writer never does — stated as concrete prohibitions. No content references."
    )

    open_observations: Optional[str] = Field(
        None,
        description="Anything distinctive about this voice not captured above. No quoted text, no named entities, no content references."
    )

    @staticmethod
    def _scale_label(val: float, low: str, high: str) -> str:
        if val >= 0.85:
            return high
        elif val >= 0.65:
            return f"leaning {high}"
        elif val >= 0.35:
            return f"mix of {low} and {high}"
        elif val >= 0.15:
            return f"leaning {low}"
        else:
            return low

    def to_prompt_text(self) -> str:
        sl = self._scale_label
        parts: list[str] = []

        parts.append("## Writing Voice Profile")
        parts.append("")

        # ── Signature moves FIRST — split by scope ────────────────────────────
        universal = [fp for fp in self.voice_fingerprints if fp.scope == "universal"]
        context_sensitive = [fp for fp in self.voice_fingerprints if fp.scope == "context_sensitive"]

        if universal:
            parts.append("SIGNATURE MOVES — apply these throughout regardless of content type:")
            for i, fp in enumerate(universal, 1):
                parts.append(f"  {i}. {fp.pattern}")
            parts.append("")

        if context_sensitive:
            parts.append("SIGNATURE MOVES — apply these only when the content naturally calls for it:")
            for i, fp in enumerate(context_sensitive, 1):
                parts.append(f"  {i}. {fp.pattern}")
            parts.append("")

        # ── Prohibitions — any violation breaks the voice immediately ──────────
        parts.append("NEVER do any of the following — each one breaks the voice completely:")
        for i, ns in enumerate(self.negative_space, 1):
            parts.append(f"  {i}. {ns}")
        parts.append("")

        # ── Register calibration ───────────────────────────────────────────────
        parts.append(
            f"Register: {self.person} person · "
            f"active voice {self.active_voice_ratio:.2f} ({sl(self.active_voice_ratio, 'passive dominant', 'active dominant')}) · "
            f"formality {self.formality_register:.2f} ({sl(self.formality_register, 'casual/conversational', 'formal/academic')}) · "
            f"emotional temperature {self.emotional_temperature:.2f} ({sl(self.emotional_temperature, 'detached/analytical', 'passionate/emotive')}) · "
            f"reader directness {self.reader_directness:.2f} ({sl(self.reader_directness, 'never addresses reader', 'constantly addresses reader')})"
        )
        parts.append(f"Reader relationship: {self.reader_relationship}")
        parts.append("")

        # ── Voice behaviors ────────────────────────────────────────────────────
        parts.append(self.word_choice_style)
        parts.append("")
        parts.append(self.sentence_construction)
        parts.append(self.rhythm_description)
        parts.append(self.sentence_opener_patterns)
        parts.append(self.sentence_ending_patterns)
        parts.append("")
        parts.append(self.punctuation_details)
        parts.append("")
        parts.append(self.hedging_style)
        parts.append(self.emphasis_style)
        parts.append("")
        parts.append(self.analogy_style)
        if self.humor_style:
            parts.append(self.humor_style)
        parts.append(self.argument_style)
        parts.append(self.jargon_style)
        if self.parenthetical_style:
            parts.append(self.parenthetical_style)
        parts.append("")

        # ── Structure last — defines what, not who ─────────────────────────────
        parts.append("STRUCTURE (follow these formatting conventions):")
        parts.append(self.structural_conventions)

        if self.open_observations:
            parts.append("")
            parts.append(self.open_observations)

        return "\n".join(parts)
