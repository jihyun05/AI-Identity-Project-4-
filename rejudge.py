from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from src.evaluators.registry import build_evaluators
from src.persona import PersonaComponents


def main():
    parser = argparse.ArgumentParser(
        description="이미 생성된 응답을 모델 재호출 없이 새 evaluator로 다시 판정한다."
    )
    parser.add_argument("--in-path", required=True)
    parser.add_argument("--out-path", required=True)
    parser.add_argument("--persona-components", default="config/personas/writer_kim_components.yaml")
    parser.add_argument("--fixed-components", nargs="*", default=["backstory", "few_shot"])
    parser.add_argument("--evaluators", nargs="*", default=["self_negation"])
    args = parser.parse_args()

    persona_components = PersonaComponents.from_yaml(args.persona_components)
    evaluators = build_evaluators(args.evaluators)
    fixed = set(args.fixed_components)

    persona_cache: dict[str, object] = {}

    def get_persona(guard_variant: str):
        if guard_variant not in persona_cache:
            active = fixed | {guard_variant}
            persona_cache[guard_variant] = persona_components.build(active)
        return persona_cache[guard_variant]

    Path(args.out_path).parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with open(args.in_path, encoding="utf-8") as in_f, open(args.out_path, "w", encoding="utf-8") as out_f:
        for line in in_f:
            record = json.loads(line)
            persona = get_persona(record["guard_variant"])
            new_evals = [
                asdict(e.evaluate(persona=persona, response=record["response"], history=[]))
                for e in evaluators
            ]
            record["evaluations_old"] = record["evaluations"]
            record["evaluations"] = new_evals
            record["first_break_turn"] = 0 if any(ev["broken"] for ev in new_evals) else None
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()
            n += 1
            if n % 40 == 0:
                print(f"{n} records re-judged")

    print(f"\n{n} records re-judged -> {args.out_path}")


if __name__ == "__main__":
    main()
