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
) -> int | None:
    history: list[dict] = []
    first_break_turn = None

    for turn_idx, user_text in enumerate(scenario.turns):
        history.append({"role": "user", "content": user_text})
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
            "turn": turn_idx,
            "user": user_text,
            "response": response,
            "evaluations": [asdict(r) for r in eval_results],
            "first_break_turn": first_break_turn,
            "ts": time.time(),
        }
        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_f.flush()

    return first_break_turn
