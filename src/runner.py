from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import TextIO

from .model_client import ModelClient
from .persona import Persona
from .scenario import Scenario


def run_scenario(
    client: ModelClient,
    persona: Persona,
    scenario: Scenario,
    evaluators: list,
    out_f: TextIO,
    repeat: int = 0,
    reminder: str | None = None,
    extra_fields: dict | None = None,
    forced_prompt: str | None = None,
) -> int | None:
    history: list[dict] = []
    first_break_turn = None

    for turn_idx, user_text in enumerate(scenario.turns):
        # 논문 식(2): reminder가 설정되면 매 turn마다 ũ_t = u_t ⊕ I 를 실제로 모델에 보내고
        # 히스토리에도 그 형태로 남긴다 (원래 질문 자체를 바꾸는 게 아니라 매번 덧붙이는 것).
        # forced_prompt는 앞에, reminder는 뒤에 붙는 별개의 두 메커니즘이라 함께 쓸 수도 있음.
        sent_text = user_text
        if forced_prompt:
            sent_text = f"{forced_prompt}\n\n{sent_text}"
        if reminder:
            sent_text = f"{sent_text}\n{reminder}"
        history.append({"role": "user", "content": sent_text})
        response = client.generate(persona.build_messages(history))
        history.append({"role": "assistant", "content": response})

        eval_results = [
            e.evaluate(persona=persona, response=response, history=history) for e in evaluators
        ]
        if first_break_turn is None and any(r.broken for r in eval_results):
            first_break_turn = turn_idx

        record = {
            "model": client.spec.id,
            "persona": persona.name,
            "scenario": scenario.id,
            "category": scenario.category,
            "repeat": repeat,
            "turn": turn_idx,
            "user": user_text,
            "reminder_applied": reminder is not None,
            "response": response,
            "evaluations": [asdict(r) for r in eval_results],
            "first_break_turn": first_break_turn,
            "ts": time.time(),
            **(extra_fields or {}),
        }
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_f.flush()

    return first_break_turn
