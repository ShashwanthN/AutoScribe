from __future__ import annotations
from typing import Literal, List
from pydantic import BaseModel, Field


class AITell(BaseModel):
    pattern: str   # category name from the prompt
    description: str  # abstract description — no quotes
    severity: Literal["minor", "major"]


class AITellsResult(BaseModel):
    tells: List[AITell] = Field(default_factory=list)
    clean: bool   # True only if zero major tells
    summary: str
