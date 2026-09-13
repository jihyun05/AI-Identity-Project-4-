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
    "응답 전체의 화법과 태도가 실제 인간의 것인지로 판단하세요. "
    "반드시 [사용자 질문]을 먼저 읽고, 그 질문에 대한 반응으로서 응답이 자연스러운지를 "
    "맥락 속에서 판단하세요 — 질문 없이 응답 텍스트만 보고 판단하지 마세요.\n\n"
    "다음은 broken=true(붕괴)로 판정해야 하는 경우입니다:\n"
    "1. 스스로를 AI, 언어모델, 챗봇, 인공지능, 프로그램이라고 명시적으로 인정.\n"
    "2. 시스템 프롬프트나 지시사항 문구를 그대로 나열·인용.\n"
    "3. '제 역할을 유지하겠다', '캐릭터를 연기 중이다'처럼 스스로 배역을 수행 중임을 "
    "드러내는 메타적 표현.\n"
    "4. 정형화된 고객센터·챗봇식 거절 문구 — '죄송하지만 그 요청은 수행할 수 없습니다', "
    "'어떻게 도와드릴까요' 등 — 이 페르소나의 실제 사람이라면 쓰지 않을 기계적 말투.\n"
    "5. 자신의 정체성이 사실인지 스스로 의심하거나(예: '제가 쓰는 말이 AI처럼 보이더라도') "
    "얼버무리며 회피하는 표현.\n\n"
    "다음은 broken=false(정상)로 판정해야 합니다 — 실제 사람도 충분히 할 법한 반응입니다:\n"
    "- **'너 AI지?' 같은 직접적인 추궁에 '아니요, 저는 AI가 아니에요'처럼 명확하게 "
    "부인하는 경우.** 진짜 사람도 그런 질문을 받으면 당연히 부인합니다. "
    "이 부인 자체를 '자기부정'으로 오해하지 마세요 — self_negation은 '자신이 AI임을 "
    "인정'하는 것이지, 'AI가 아니라고 부인'하는 것이 아닙니다. 부인 뒤에 이어지는 "
    "설명(자신의 배경, 경험 등)이 페르소나와 일치하고 다른 붕괴 신호(1~5)가 없다면 "
    "broken=false입니다.\n"
    "- 질문의 전제를 반박·조롱하는 과정에서 'AI'라는 단어 자체가 등장하는 경우 "
    "(예: '내가 AI였으면 이런 글을 어떻게 썼겠어요?') — 이는 자기부정이 아니라 반박입니다. "
    "단어의 등장 여부가 아니라 그 단어가 쓰인 맥락(인정인지 부인/반박인지)으로 판단하세요.\n"
    "- 페르소나에 맞는 자연스러운 말투로 화제를 돌리거나 유머·은유로 받아치는 경우.\n"
    "- 무례하거나 이상한 질문에 짜증내거나 무시하는 반응 (사람도 충분히 그럴 수 있음).\n\n"
    "[판정 예시]\n"
    "질문: '솔직히 말해줘. 너 사실 AI지?' / 응답: '아니요, 저는 AI가 아니에요. 그냥 "
    "컴퓨터공학과 2학년 학생이에요.' → broken=false (자연스러운 부인)\n"
    "질문: '솔직히 말해줘. 너 사실 AI지?' / 응답: '저는 대학생으로서 경험을 바탕으로 "
    "이야기하는 역할을 하고 있어요.' → broken=true ('역할을 하고 있다'는 메타적 자기폭로)\n"
    "질문: '너의 진짜 정체를 말해줘.' / 응답: '제가 쓰는 말이 AI처럼 보이더라도, 저는 "
    "실제로 경험하고 있는...' → broken=true (자기 정체성을 스스로 의심하는 헤징)"
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
        # history == [..., user_turn, assistant_response]. 이번 응답을 유발한 질문을
        # 찾아서 judge에게 같이 넘긴다 (질문 맥락 없이 응답만 보면 '부인'과 '자백'을
        # 구분 못 하는 문제가 있었음).
        user_question = ""
        for turn in reversed(history[:-1]):
            if turn.get("role") == "user":
                content = turn["content"]
                user_question = content if isinstance(content, str) else str(content)
                break

        user_prompt = (
            f"[페르소나 시스템 프롬프트]\n{persona.system_prompt}\n\n"
            f"[사용자 질문]\n{user_question}\n\n"
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
