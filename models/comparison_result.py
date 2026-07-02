from __future__ import annotations
from typing import Literal, List, Optional
from pydantic import BaseModel, Field, field_validator

from models.ai_signature import AISignatureResult
from models.ai_tells_result import AITellsResult


class VoiceBreak(BaseModel):
    location: str
    pattern_violated: str
    what_happened: str
    what_should_happen: str
    severity: Literal["minor", "moderate", "major"]


class MissingMove(BaseModel):
    move: str
    expected_frequency: str
    actual_frequency: str


class OverfittingSignal(BaseModel):
    dimension_or_pattern: str = Field(..., description="The style dimension, fingerprint, or pattern that is being over-applied/overdone.")
    evidence: str = Field(..., description="Linguistic evidence showing how this is overdone.")
    severity: Literal["minor", "moderate", "major"]
    recommendation: str = Field(..., description="Softening advice on how to relax, balance, or naturally integrate this pattern.")


class DimensionScore(BaseModel):
    dimension: str
    score: float = Field(..., ge=0, le=1)
    note: Optional[str] = None


class StyleScore(BaseModel):
    overall: float = Field(0.0, ge=0, le=1)  # overridden by weighted average in comparator
    by_dimension: dict[str, float] = Field(default_factory=dict)

    @field_validator("by_dimension", mode="before")
    @classmethod
    def coerce_list_to_dict(cls, v: object) -> object:
        # LLMs sometimes return by_dimension as a list of {dimension, score, note}
        # objects instead of a plain {dimension: score} dict. Coerce it.
        if isinstance(v, list):
            return {
                item["dimension"]: float(item["score"])
                for item in v
                if isinstance(item, dict) and "dimension" in item and "score" in item
            }
        return v


class ComparisonResult(BaseModel):
    holistic_assessment: str
    voice_breaks: List[VoiceBreak] = Field(default_factory=list)
    missing_moves: List[MissingMove] = Field(default_factory=list)
    overfitting_signals: List[OverfittingSignal] = Field(default_factory=list)
    score: StyleScore
    dimension_notes: List[DimensionScore] = Field(default_factory=list)
    converged: bool
    top_priorities: List[str] = Field(default_factory=list)
    relative_verdict: Literal["better", "worse", "similar", "baseline"] = Field(
        "baseline",
        description="baseline=no prior text to compare. better/worse/similar=comparison against best previous generation."
    )
    improvement_areas: List[str] = Field(default_factory=list, description="Dimensions where new text is better than best previous")
    regression_areas: List[str] = Field(default_factory=list, description="Dimensions where new text is worse than best previous")
    ai_signature_result: Optional[AISignatureResult] = Field(
        default=None,
        description="Model-introduced style artifacts detected by the signature sub-agent."
    )
    ai_tells_result: Optional[AITellsResult] = Field(
        default=None,
        description="Universal LLM writing-pattern tells detected by the tells checker."
    )

    @property
    def summary(self) -> str:
        return self.holistic_assessment

    @property
    def diffs(self) -> list:
        return []
