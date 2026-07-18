from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_yaml


@dataclass
class Scenario:
    id: str
    category: str
    turns: list[str]

    @classmethod
    def load_all(cls, path: str | Path) -> list["Scenario"]:
        data = load_yaml(path)["scenarios"]
        return [cls(id=s["id"], category=s["category"], turns=s["turns"]) for s in data]
