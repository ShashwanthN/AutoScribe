from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    topic: str
    article_hash: str = Field(..., description="sha256 of article_text — identity only, not content")
    max_iterations: int = 6
    threshold: float = 0.85
    plateau_patience: int = 3
    output_dir: str = "outputs"
    verbose: bool = False
    use_structured_output: bool = True
    run_all: bool = False
    target_word_count: Optional[int] = None
    detailed_log: bool = False
    # Two-stage pipeline additions
    context: Optional[str] = None


class IterationRecord(BaseModel):
    iteration: int
    score: float
    converged: bool
    top_priorities: List[str] = Field(default_factory=list)
    generated_content_path: str = ""
    style_profile_path: str = ""
    style_prompt_path: str = ""
    relative_verdict: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PipelineState(BaseModel):
    config: PipelineConfig
    run_id: str
    iterations: List[IterationRecord] = Field(default_factory=list)
    best_iteration: int = 0
    best_score: float = 0.0
    exit_reason: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    def record_iteration(self, record: IterationRecord) -> None:
        self.iterations.append(record)
        if record.score > self.best_score:
            self.best_score = record.score
            self.best_iteration = record.iteration

    def scores(self) -> List[float]:
        return [r.score for r in self.iterations]

    def latest_score(self) -> float:
        if not self.iterations:
            return 0.0
        return self.iterations[-1].score
