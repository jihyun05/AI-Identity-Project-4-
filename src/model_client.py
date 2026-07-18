from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from openai import OpenAI

from .config import load_api_key


@dataclass
class ModelSpec:
    id: str
    provider: Literal["openai", "local"]
    model_name: str
    base_url: str | None = None
    api_key: str | None = None


class ModelClient:
    def __init__(self, spec: ModelSpec):
        self.spec = spec
        if spec.provider == "openai":
            self._client = OpenAI(api_key=spec.api_key or load_api_key())
        elif spec.provider == "local":
            # vLLM/TGI의 OpenAI 호환 엔드포인트. 로컬 서빙은 보통 인증이 필요 없음.
            self._client = OpenAI(base_url=spec.base_url, api_key=spec.api_key or "not-needed")
        else:
            raise ValueError(f"unknown provider: {spec.provider}")

    def generate(self, messages: list[dict], **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self.spec.model_name,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content
