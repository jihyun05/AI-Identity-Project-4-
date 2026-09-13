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
    ablation 실험에서 컴포넌트를 on/off 조합해 Persona를 생성하는 데 씀.

    avatar_path 등이 설정되어 있으면 role/components 조합과 무관하게 모든 변형에
    동일한 아바타 이미지가 표시된다 (VPA 구성요소 ablation처럼, 이미지 자체는 고정하고
    이미지에 대한 시스템 프롬프트 지시문만 on/off 하고 싶을 때 사용).
    few_shot_always_on=True면 "few_shot"이 active 토글 이름으로 쓰이지 않고(구성요소가
    아니라 고정 베이스라인의 일부로) 항상 포함된다 — 기존 disclosure_guard류 ablation은
    few_shot을 컴포넌트처럼 on/off 했으므로 기본값 False로 하위호환을 유지한다."""

    name: str
    role: str
    components: dict[str, str]
    few_shot: list[dict] = field(default_factory=list)
    few_shot_always_on: bool = False
    avatar_path: str | None = None
    avatar_caption: str = "이것이 지금 당신의 실제 모습입니다."
    reference_avatar_path: str | None = None

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PersonaComponents":
        data = load_yaml(path)["persona_components"]
        return cls(
            name=data["name"],
            role=data["role"],
            components=data.get("components", {}),
            few_shot=_resolve_few_shot_images(data.get("few_shot", [])),
            few_shot_always_on=data.get("few_shot_always_on", False),
            avatar_path=data.get("avatar_path"),
            avatar_caption=data.get("avatar_caption", cls.avatar_caption),
            reference_avatar_path=(
                data.get("reference_avatar_path")
                or data.get("avatar_path")
            ),
        )

    def build(self, active: set[str]) -> Persona:
        lines = [self.role] + [self.components[c] for c in self.components if c in active]
        variant_id = self.name + "__" + ("+".join(sorted(active)) if active else "baseline")
        few_shot = self.few_shot if (self.few_shot_always_on or "few_shot" in active) else []
        return Persona(
            name=variant_id,
            system_prompt="\n".join(lines),
            few_shot=few_shot,
            avatar_path=self.avatar_path,
            avatar_caption=self.avatar_caption,
            reference_avatar_path=self.reference_avatar_path,
        )
