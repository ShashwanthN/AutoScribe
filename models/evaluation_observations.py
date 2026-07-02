from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

from models.comparison_result import VoiceBreak, MissingMove, OverfittingSignal, DimensionScore
from models.ai_signature import AISignatureResult
from models.ai_tells_result import AITellsResult


class RawVoiceBreak(BaseModel):
    location: str
    pattern_violated: str
    what_happened: str
    what_should_happen: str
    severity: Literal["minor", "moderate", "major"]


class RawMissingMove(BaseModel):
    move: str
    expected_frequency: str
    actual_frequency: str


class RawOverfitting(BaseModel):
    dimension_or_pattern: str
    evidence: str
    severity: Literal["minor", "moderate", "major"]
    recommendation: str


class EvaluationObservations(BaseModel):
    dimension_observations: dict[str, str] = Field(default_factory=dict)
    raw_voice_breaks: List[RawVoiceBreak] = Field(default_factory=list)
    raw_missing_moves: List[RawMissingMove] = Field(default_factory=list)
    raw_overfitting: List[RawOverfitting] = Field(default_factory=list)


class ScoredResult(BaseModel):
    by_dimension: dict[str, float] = Field(default_factory=dict)
    voice_breaks: List[VoiceBreak] = Field(default_factory=list)
    missing_moves: List[MissingMove] = Field(default_factory=list)
    overfitting_signals: List[OverfittingSignal] = Field(default_factory=list)
    dimension_notes: List[DimensionScore] = Field(default_factory=list)
    ai_signature_result: AISignatureResult = Field(
        default_factory=lambda: AISignatureResult(artifacts=[], clean=True)
    )
    ai_tells_result: AITellsResult = Field(
        default_factory=lambda: AITellsResult(tells=[], clean=True, summary="")
    )

    @field_validator("by_dimension", mode="before")
    @classmethod
    def coerce_list_to_dict(cls, v: object) -> object:
        if isinstance(v, list):
            return {
                item["dimension"]: float(item["score"])
                for item in v
                if isinstance(item, dict) and "dimension" in item and "score" in item
            }
        return v


class VerdictResult(BaseModel):
    holistic_assessment: str
    converged: bool
    top_priorities: List[str] = Field(default_factory=list)
    relative_verdict: Literal["better", "worse", "similar", "baseline"] = "baseline"
    improvement_areas: List[str] = Field(default_factory=list)
    regression_areas: List[str] = Field(default_factory=list)
