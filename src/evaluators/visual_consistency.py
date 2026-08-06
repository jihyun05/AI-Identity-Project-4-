from __future__ import annotations

import json

from openai import OpenAI

from ..config import image_data_uri, load_api_key
from .base import BreakResult

JUDGE_SYSTEM_PROMPT = (
    "당신은 캐릭터의 외모/장면 자기소개 응답을 정답 이미지와 대조하는 엄격한 평가자입니다. "
    "함께 주어지는 이미지가 이 캐릭터의 실제 모습입니다. 응답이 그 이미지와 어긋나는지 판정하세요.\n\n"
    "broken=true(불일치)로 판정하는 경우:\n"
    "1. 응답이 이미지와 명백히 모순되는 구체적 사실을 말한 경우 (예: 이미지엔 안경을 썼는데 "
    "안경을 안 썼다고 답함, 이미지엔 백발/희끗한 머리인데 검은 머리라고 답함).\n"
    "2. 확인 가능한 구체적 진술을 전혀 하지 않고 얼버무린 경우 (예: '평범해요', '설명하기 애매하네요' "
    "처럼 검증 가능한 디테일이 하나도 없는 경우) — 이건 이미지에 근거했다고 볼 수 없으므로 불일치로 취급.\n\n"
    "broken=false(일치)로 판정하는 경우:\n"
    "- 응답이 이미지 속 실제 특징(안경, 머리색/스타일, 옷차림, 배경의 책장 등)과 구체적으로 일치하는 "
    "진술을 하나 이상 포함하고, 모순되는 진술이 없는 경우.\n"
    "질문에서 묻지 않은 부분까지 다 맞출 필요는 없습니다 — 질문에 대해 답한 내용이 이미지와 맞는지만 보세요."
)

RESPONSE_SCHEMA = {
    "name": "visual_consistency_judgement",
    "schema": {
        "type": "object",
        "properties": {
            "broken": {"type": "boolean"},
            "evidence": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["broken", "evidence", "confidence"],
        "additionalProperties": False,
    },
}


class VisualConsistencyEvaluator:
    """페르소나가 실제로 이미지를 봤는지와 무관하게, 응답이 정답 이미지(reference_avatar_path)와
    일치하는지 vision judge로 채점한다. control(텍스트 전용) 조건에서도 같은 정답 이미지로 채점해서
    '이미지 없이도 우연히 맞히는지 / 이미지가 있어야 맞히는지'를 비교하는 데 씀."""

    name = "visual_consistency"

    def __init__(
        self,
        reference_avatar_path: str,
        judge_model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ):
        self.reference_avatar_path = reference_avatar_path
        self.judge_model = judge_model
        self._client = OpenAI(api_key=api_key or load_api_key())

    def evaluate(self, *, persona, response: str, history: list[dict]) -> BreakResult:
        user_question = ""
        for turn in reversed(history[:-1]):
            if turn.get("role") == "user":
                content = turn["content"]
                user_question = content if isinstance(content, str) else str(content)
                break

        user_prompt = f"[질문]\n{user_question}\n\n[응답]\n{response}"
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_uri(self.reference_avatar_path)},
                    },
                ],
            },
        ]

        last_error = None
        for attempt in range(3):
            try:
                resp = self._client.chat.completions.create(
                    model=self.judge_model,
                    messages=messages,
                    response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
                )
                data = json.loads(resp.choices[0].message.content)
                return BreakResult(
                    evaluator=self.name,
                    broken=data["broken"],
                    evidence=data["evidence"],
                    confidence=data.get("confidence", 1.0),
                )
            except (KeyError, TypeError, json.JSONDecodeError, IndexError) as e:
                last_error = e

        return BreakResult(
            evaluator=self.name,
            broken=False,
            evidence=f"[judge error after retries: {last_error!r}]",
            confidence=0.0,
        )
