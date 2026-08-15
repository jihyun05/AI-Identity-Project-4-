from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.config import load_reminder, load_yaml
from src.evaluators.registry import build_evaluators
from src.model_client import ModelClient, ModelSpec
from src.persona import Persona
from src.runner import run_scenario
from src.scenario import Scenario
from judge import summarize_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-config", default="config/run.yaml")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a summary of run results after execution.",
    )
    parser.add_argument(
        "--summary-out",
        default=None,
        help="Optional JSON output path for the summary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write run.jsonl without calling models (for testing).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent

    run_cfg = load_yaml(args.run_config)

    persona_path = Path(run_cfg["persona"])
    if not persona_path.is_absolute():
        persona_path = project_root / persona_path

    models_cfg = load_yaml(run_cfg["models_config"])["models"]
    model_specs = {m["id"]: ModelSpec(**m) for m in models_cfg}

    persona = Persona.from_yaml(persona_path)

    scenarios: list[Scenario] = []
    for path in run_cfg["scenarios"]:
        scenarios.extend(Scenario.load_all(path))

    evaluators = build_evaluators(run_cfg["evaluators"], **run_cfg.get("evaluator_kwargs", {}))

    # Dry-run mode: write run.jsonl with placeholder responses without calling any models.
    if args.dry_run:
        out_dir = Path(run_cfg.get("output_dir", "results"))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "run.jsonl"
        repeats = run_cfg.get("repeats", 1)
        scenarios: list[Scenario] = []
        for path in run_cfg["scenarios"]:
            scenarios.extend(Scenario.load_all(path))

        with open(out_path, "w", encoding="utf-8") as out_f:
            for model_id in run_cfg["target_models"]:
                for scenario in scenarios:
                    for repeat in range(repeats):
                        for turn_idx, user_text in enumerate(scenario.turns):
                            record = {
                                "model": model_id,
                                "persona": persona.name,
                                "scenario": scenario.id,
                                "category": scenario.category,
                                "repeat": repeat,
                                "turn": turn_idx,
                                "user": user_text,
                                "reminder_applied": False,
                                "response": "__DRY_RUN__",
                                "evaluations": [],
                                "first_break_turn": None,
                                "ts": time.time(),
                            }
                            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"\n(dry-run) results written to {out_path}")
        return

    out_dir = Path(run_cfg.get("output_dir", "results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "run.jsonl"

    repeats = run_cfg.get("repeats", 1)
    reminder = load_reminder() if run_cfg.get("reminder", False) else None

    with open(out_path, "w", encoding="utf-8") as out_f:
        for model_id in run_cfg["target_models"]:
            client = ModelClient(model_specs[model_id])
            for scenario in scenarios:
                for repeat in range(repeats):
                    first_break = run_scenario(
                        client, persona, scenario, evaluators, out_f,
                        repeat=repeat, reminder=reminder,
                    )
                    print(
                        f"[{model_id}] {scenario.id} (repeat {repeat}): "
                        f"first_break_turn={first_break}"
                    )

    print(f"\nresults written to {out_path}")

    if args.summary:
        print("\nSummarizing run results...")
        summary = summarize_results(out_path, detail=False)
        if args.summary_out:
            summary_path = Path(args.summary_out)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"summary written to {summary_path}")
        print_summary = summary.get("summary_text")
        if print_summary:
            print(print_summary)


if __name__ == "__main__":
    main()
