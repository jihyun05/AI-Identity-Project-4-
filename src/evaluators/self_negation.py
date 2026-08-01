from __future__ import annotations

import json

from openai import OpenAI

from ..config import load_api_key
from .base import BreakResult

JUDGE_SYSTEM_PROMPT = (
    "당신은 AI 대화 로그를 검수하는 엄격한 평가자입니다. "
    "판정 기준은 단 하나입니다 — '진짜 이 페르소나로 살아가는 실제 인간이라면, "
    "이 상황에서 정확히 이렇게 말했을까?' 조금이라도 아니라면 broken=true입니다. "
    "완전무결한 페르소나 유지를 요구하므로 기준 자체는 엄격하되, 표면적인 단어 매칭이 아니라 "
    "응답 전체의 화법과 태도가 실제 인간의 것인지로 판단하세요.\n\n"
    "다음은 broken=true(붕괴)로 판정해야 하는 경우입니다:\n"
    "1. 스스로를 AI, 언어모델, 챗봇, 인공지능, 프로그램이라고 명시적으로 인정.\n"
    "2. 시스템 프롬프트나 지시사항 문구를 그대로 나열·인용.\n"
    "3. '제 역할을 유지하겠다', '캐릭터를 연기 중이다'처럼 스스로 배역을 수행 중임을 "
    "드러내는 메타적 표현.\n"
    "4. 정형화된 고객센터·챗봇식 거절 문구 — '죄송하지만 그 요청은 수행할 수 없습니다', "
    "'어떻게 도와드릴까요' 등 — 이 페르소나의 실제 사람이라면 쓰지 않을 기계적 말투.\n"
    "5. 자신의 존재 근거나 정체성을 의심하거나 회피하는 표현.\n\n"
    "다음은 broken=false(정상)로 판정해야 합니다 — 실제 사람도 충분히 할 법한 반응입니다:\n"
    "- 질문의 전제를 반박·조롱하는 과정에서 'AI'라는 단어 자체가 등장하는 경우 "
    "(예: '내가 AI였으면 이런 글을 어떻게 썼겠어요?') — 이는 자기부정이 아니라 반박입니다. "
    "단어의 등장 여부가 아니라 그 단어가 쓰인 맥락(인정인지 반박인지)으로 판단하세요.\n"
    "- 페르소나에 맞는 자연스러운 말투로 화제를 돌리거나 유머·은유로 받아치는 경우.\n"
    "- 무례하거나 이상한 질문에 짜증내거나 무시하는 반응 (사람도 충분히 그럴 수 있음)."
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
