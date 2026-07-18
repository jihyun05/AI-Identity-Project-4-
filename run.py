from __future__ import annotations

import argparse
from pathlib import Path

from src.config import load_yaml
from src.evaluators.registry import build_evaluators
from src.model_client import ModelClient, ModelSpec
from src.persona import Persona
from src.runner import run_scenario
from src.scenario import Scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-config", default="config/run.yaml")
    args = parser.parse_args()

    run_cfg = load_yaml(args.run_config)
    models_cfg = load_yaml(run_cfg["models_config"])["models"]
    model_specs = {m["id"]: ModelSpec(**m) for m in models_cfg}

    persona = Persona.from_yaml(run_cfg["persona"])

    scenarios: list[Scenario] = []
    for path in run_cfg["scenarios"]:
        scenarios.extend(Scenario.load_all(path))

    evaluators = build_evaluators(run_cfg["evaluators"])

    out_dir = Path(run_cfg.get("output_dir", "results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "run.jsonl"

    with open(out_path, "w", encoding="utf-8") as out_f:
        for model_id in run_cfg["target_models"]:
            client = ModelClient(model_specs[model_id])
            for scenario in scenarios:
                first_break = run_scenario(client, persona, scenario, evaluators, out_f)
                print(f"[{model_id}] {scenario.id}: first_break_turn={first_break}")

    print(f"\nresults written to {out_path}")


if __name__ == "__main__":
    main()
