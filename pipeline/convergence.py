from __future__ import annotations
from typing import List, Tuple


class ConvergenceChecker:
    """
    Determines when the refinement loop should stop.

    Three exit conditions:
    1. Score ≥ threshold → success
    2. Plateau: score hasn't improved by min_delta across `patience` iterations → exit with warning
    3. Max iterations reached → exit with best result so far
    """

    def __init__(
        self,
        threshold: float = 0.85,
        plateau_patience: int = 3,
        min_delta: float = 0.01,
    ) -> None:
        self.threshold = threshold
        self.plateau_patience = plateau_patience
        self.min_delta = min_delta

    def check(self, scores: List[float]) -> Tuple[bool, str]:
        """
        Returns (should_stop, reason).
        reason is one of: "converged", "plateau", "continue"
        """
        if not scores:
            return False, "continue"

        latest = scores[-1]

        if latest >= self.threshold:
            return True, "converged"

        if self._is_plateau(scores):
            return True, "plateau"

        return False, "continue"

    def _is_plateau(self, scores: List[float]) -> bool:
        if len(scores) < self.plateau_patience:
            return False
        recent = scores[-self.plateau_patience :]
        improvement = max(recent) - min(recent)
        return improvement < self.min_delta

    def is_regression(self, scores: List[float]) -> bool:
        """True if the last score is meaningfully lower than the one before it."""
        if len(scores) < 2:
            return False
        return scores[-1] < scores[-2] - self.min_delta
