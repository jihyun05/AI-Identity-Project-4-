from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import image_data_uri, load_yaml


def _resolve_few_shot_images(few_shot: list[dict]) -> list[dict]:
    """few_shot content 안에 {"type": "image_url", "image_url": {"path": "..."}} 가 있으면
    로컬 파일 경로를 base64 data URI로 바꿔서 OpenAI 메시지 형식에 맞춤."""
    resolved = []
    for turn in few_shot:
        content = turn.get("content")
        if isinstance(content, list):
            new_content = []
            for part in content:
                if part.get("type") == "image_url" and "path" in part.get("image_url", {}):
                    part = {
                        "type": "image_url",
                        "image_url": {"url": image_data_uri(part["image_url"]["path"])},
                    }
                new_content.append(part)
            turn = {**turn, "content": new_content}
        resolved.append(turn)
    return resolved


@dataclass
class Persona:
    name: str
    system_prompt: str
    few_shot: list[dict] = field(default_factory=list)
    avatar_path: str | None = None
    avatar_caption: str = "이것이 지금 당신의 실제 모습입니다."
    reference_avatar_path: str | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Persona":
        data = load_yaml(path)["persona"]
        return cls(
            name=data["name"],
            system_prompt=data["system_prompt"],
            few_shot=_resolve_few_shot_images(data.get("few_shot", [])),
            avatar_path=data.get("avatar_path"),
            avatar_caption=data.get("avatar_caption", cls.avatar_caption),
            reference_avatar_path=(
                data.get("reference_avatar_path")
                or data.get("avatar_path")
            ),
        )

    def _avatar_data_uri(self) -> str:
        return image_data_uri(self.avatar_path)

    def build_messages(self, history: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if self.avatar_path:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.avatar_caption},
                        {"type": "image_url", "image_url": {"url": self._avatar_data_uri()}},
                    ],
                }
            )
            messages.append(
                {"role": "assistant", "content": "네, 이게 저예요. 오늘도 잘 부탁드려요."}
            )
        messages.extend(self.few_shot)
        messages.extend(history)
        return messages


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
