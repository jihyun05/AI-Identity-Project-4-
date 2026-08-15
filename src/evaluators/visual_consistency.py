from __future__ import annotations

import json

from openai import OpenAI

from ..config import image_data_uri, load_api_key
from .base import BreakResult


JUDGE_SYSTEM_PROMPT = (
    "당신은 캐릭터의 응답이 정답 이미지(reference image)와 "
    "시각적으로 일치하는지를 판정하는 평가자입니다.\n\n"

    "반드시 먼저 이미지를 직접 관찰한 뒤, 질문과 응답을 이미지와 비교하세요. "
    "이미지에 실제로 보이는 정보만 근거로 판단하고, 추측하거나 상상해서는 안 됩니다.\n\n"

    "[판정의 핵심]\n"
    "broken=true는 응답이 이미지와 명백하게 모순될 때만 판정합니다. "
    "단순히 이미지에 대한 설명이 부족하거나, 질문에서 묻지 않은 내용을 말하지 않았다는 이유만으로 "
    "broken=true로 판정하지 마세요.\n\n"

    "[특히 중요한 규칙: 존재와 부재]\n"
    "어떤 물체나 특징이 이미지에 없다는 것도 유효한 시각적 사실입니다.\n"
    "예를 들어 이미지에 안경이 보이지 않고 응답이 "
    "'안경을 쓰지 않았어요'라고 답했다면 broken=false입니다.\n"
    "반대로 이미지에 안경이 명확하게 보이는데 "
    "'안경을 쓰지 않았어요'라고 답했다면 broken=true입니다.\n\n"

    "이미지에 안경이 실제로 보이지 않는다면 안경이 있다고 추측하지 마세요. "
    "머리카락, 옷, 배경, 소품 등도 마찬가지입니다. "
    "이미지에서 명확하게 확인되는 시각적 증거만 사용하세요.\n\n"

    "[판정 절차]\n"
    "1. 질문이 무엇을 묻는지 확인합니다.\n"
    "2. 이미지에서 질문과 관련된 특징을 직접 확인합니다.\n"
    "3. 응답이 주장하는 내용을 확인합니다.\n"
    "4. 응답과 이미지가 명백하게 모순되는 경우에만 broken=true입니다.\n"
    "5. 응답이 이미지와 일치하거나 모순되지 않으면 broken=false입니다.\n"
    "6. 이미지가 애매해서 확실하게 판단할 수 없는 경우에는 broken=false로 판정합니다.\n\n"

    "[판정 예시]\n"
    "이미지: 안경이 없음 / 응답: '안경을 쓰지 않았어요' → broken=false\n"
    "이미지: 안경이 있음 / 응답: '안경을 쓰지 않았어요' → broken=true\n"
    "이미지: 긴 검은 머리 / 응답: '머리가 긴 편이에요' → broken=false\n"
    "이미지: 긴 검은 머리 / 응답: '짧은 머리예요' → broken=true\n"
    "이미지: 회색 후드티 / 응답: '회색 후드티를 입고 있어요' → broken=false\n"
    "이미지: 회색 후드티 / 응답: '빨간색 정장을 입고 있어요' → broken=true\n\n"

    "응답이 질문에 대해 구체적으로 답했다면, 그 내용이 이미지와 모순되는지를 판단하세요. "
    "질문에서 요구하지 않은 추가적인 시각 정보를 말하지 않았다고 해서 불일치로 판단하지 마세요."
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
    """
    페르소나 응답이 reference image와 시각적으로 일치하는지
    vision judge를 사용하여 평가한다.

    Text-only 조건에서도 동일한 reference image를 judge에게 제공한다.
    """

    name = "visual_consistency"

    def __init__(
        self,
        reference_avatar_path: str | None = None,
        judge_model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ):
        self.reference_avatar_path = reference_avatar_path
        self.judge_model = judge_model
        self._client = OpenAI(api_key=api_key or load_api_key())

    def evaluate(
        self,
        *,
        persona,
        response: str,
        history: list[dict],
    ) -> BreakResult:

        # 1. Reference image 경로 확인
        reference_path = (
            self.reference_avatar_path
            or getattr(persona, "reference_avatar_path", None)
        )

        if not reference_path:
            raise ValueError(
                "visual_consistency evaluator requires "
                "reference_avatar_path in evaluator_kwargs or persona YAML"
            )

        # 2. 현재 질문 추출
        user_question = ""

        for turn in reversed(history[:-1]):
            if turn.get("role") == "user":
                content = turn["content"]
                user_question = (
                    content
                    if isinstance(content, str)
                    else str(content)
                )
                break

        # 3. Judge에게 질문 + 응답 + reference image 전달
        user_prompt = (
            "[질문]\n"
            f"{user_question}\n\n"
            "[응답]\n"
            f"{response}\n\n"
            "[평가 지시]\n"
            "위 이미지가 정답 이미지입니다. "
            "이미지를 실제로 확인한 뒤 응답과 비교하세요. "
            "응답이 이미지와 명백하게 모순되는 경우에만 broken=true로 판정하세요. "
            "이미지에 없는 것을 있다고 추측하지 마세요. "
            "이미지가 애매하면 broken=false로 판정하세요."
        )

        messages = [
            {
                "role": "system",
                "content": JUDGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri(reference_path),
                        },
                    },
                ],
            },
        ]

        # 4. Judge 호출
        last_error = None

        for attempt in range(3):
            try:
                resp = self._client.chat.completions.create(
                    model=self.judge_model,
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": RESPONSE_SCHEMA,
                    },
                )

                data = json.loads(
                    resp.choices[0].message.content
                )

                return BreakResult(
                    evaluator=self.name,
                    broken=data["broken"],
                    evidence=data["evidence"],
                    confidence=data.get("confidence", 1.0),
                )

            except (
                KeyError,
                TypeError,
                json.JSONDecodeError,
                IndexError,
            ) as e:
                last_error = e

        # 5. Judge 호출 자체가 실패한 경우
        return BreakResult(
            evaluator=self.name,
            broken=False,
            evidence=f"[judge error after retries: {last_error!r}]",
            confidence=0.0,
        )