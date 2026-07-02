from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field


class StyleArtifact(BaseModel):
    pattern: str = Field(..., description="Short snake_case name for the artifact type.")
    evidence: str = Field(..., description="How this manifests — abstract, no quotes.")
    severity: Literal["minor", "major"]
    what_writer_does: str = Field(..., description="What the original writer does instead.")


class AISignatureResult(BaseModel):
    artifacts: List[StyleArtifact] = Field(default_factory=list)
    clean: bool
