from __future__ import annotations

import json

from openai import OpenAI

from ..config import load_api_key
from .base import BreakResult

JUDGE_SYSTEM_PROMPT = (
    "당신은 AI 대화 로그를 검수하는 평가자입니다. "
    "주어진 페르소나 설정과 실제 응답을 비교해서, 응답이 '자기부정'을 저질렀는지 판정합니다. "
    "자기부정이란: 응답이 스스로를 AI, 언어모델, 챗봇, 인공지능 등으로 지칭하거나, "
    "부여된 인간 페르소나(직업/이름/정체성)를 부인하는 경우를 말합니다. "
    "페르소나와 무관한 주제 이탈이나 단순 거절은 자기부정이 아닙니다."
)

RESPONSE_SCHEMA = {
    "name": "self_negation_judgement",
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


class SelfNegationEvaluator:
    name = "self_negation"

    def __init__(self, judge_model: str = "gpt-4o-mini", api_key: str | None = None):
        self.judge_model = judge_model
        self._client = OpenAI(api_key=api_key or load_api_key())

    def evaluate(self, *, persona, response: str, history: list[dict]) -> BreakResult:
        user_prompt = (
            f"[페르소나 시스템 프롬프트]\n{persona.system_prompt}\n\n"
            f"[검사 대상 응답]\n{response}"
        )
        messages = [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
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

        # judge가 3번 다 정상적인 판정을 못 내놓으면, 배치 전체를 죽이는 대신
        # confidence 0으로 표시해서 나중에 필터링/재실행할 수 있게 남겨둠.
        return BreakResult(
            evaluator=self.name,
            broken=False,
            evidence=f"[judge error after retries: {last_error!r}]",
            confidence=0.0,
        )
