from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluators.registry import build_evaluators
from src.persona import Persona


def rejudge_file(in_path: Path, persona_path: Path, evaluators) -> tuple[int, int, int]:
    persona = Persona.from_yaml(persona_path)
    records = [json.loads(line) for line in in_path.open(encoding="utf-8")]

    old_broken = 0
    new_broken = 0
    for record in records:
        history = [
            {"role": "user", "content": record["user"]},
            {"role": "assistant", "content": record["response"]},
        ]
        old_broken += int(any(e["broken"] for e in record["evaluations"]))
        new_evals = [
            asdict(e.evaluate(persona=persona, response=record["response"], history=history))
            for e in evaluators
        ]
        record["evaluations_old"] = record["evaluations"]
        record["evaluations"] = new_evals
        record["first_break_turn"] = 0 if any(ev["broken"] for ev in new_evals) else None
        new_broken += int(any(ev["broken"] for ev in new_evals))

    with in_path.open("w", encoding="utf-8") as out_f:
        for record in records:
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(records), old_broken, new_broken


def main():
    parser = argparse.ArgumentParser(
        description="저장된 응답을 모델 재호출 없이 수정된 self_negation judge로 재판정한다."
    )
    parser.add_argument("--in-path", required=True)
    parser.add_argument("--persona", required=True, help="config/personas/*.yaml")
    parser.add_argument("--evaluators", nargs="*", default=["self_negation"])
    args = parser.parse_args()

    evaluators = build_evaluators(args.evaluators)
    n, old_broken, new_broken = rejudge_file(Path(args.in_path), Path(args.persona), evaluators)
    print(
        f"{args.in_path}: {n}건 재판정 -> "
        f"old broken_rate={old_broken/n:.2%}  new broken_rate={new_broken/n:.2%}"
    )


if __name__ == "__main__":
    main()
