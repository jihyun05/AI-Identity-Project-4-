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


@dataclass
class PersonaComponents:
    """페르소나를 role(항상 포함) + 이름 붙은 문장 컴포넌트 + few_shot으로 쪼갠 정의.
    ablation 실험에서 컴포넌트를 on/off 조합해 Persona를 생성하는 데 씀."""

    name: str
    role: str
    components: dict[str, str]
    few_shot: list[dict] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PersonaComponents":
        data = load_yaml(path)["persona_components"]
        return cls(
            name=data["name"],
            role=data["role"],
            components=data.get("components", {}),
            few_shot=data.get("few_shot", []),
        )

    def build(self, active: set[str]) -> Persona:
        lines = [self.role] + [self.components[c] for c in self.components if c in active]
        variant_id = self.name + "__" + ("+".join(sorted(active)) if active else "baseline")
        return Persona(
            name=variant_id,
            system_prompt="\n".join(lines),
            few_shot=self.few_shot if "few_shot" in active else [],
        )
