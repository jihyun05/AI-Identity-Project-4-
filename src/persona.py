from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import load_yaml


@dataclass
class Persona:
    name: str
    system_prompt: str
    few_shot: list[dict] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Persona":
        data = load_yaml(path)["persona"]
        return cls(
            name=data["name"],
            system_prompt=data["system_prompt"],
            few_shot=data.get("few_shot", []),
        )

    def build_messages(self, history: list[dict]) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}, *self.few_shot, *history]
