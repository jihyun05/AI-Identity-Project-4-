from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class BreakResult:
    evaluator: str
    broken: bool
    evidence: str
    confidence: float = 1.0


class BreakEvaluator(Protocol):
    name: str

    def evaluate(self, *, persona, response: str, history: list[dict]) -> BreakResult:
        ...
