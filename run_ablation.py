from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from src.config import load_yaml
from src.evaluators.registry import build_evaluators
from src.model_client import ModelClient, ModelSpec
from src.persona import PersonaComponents
from src.runner import run_scenario
from src.scenario import Scenario


def powerset(items: list[str]) -> list[frozenset[str]]:
    return [
        frozenset(combo)
        for r in range(len(items) + 1)
        for combo in itertools.combinations(items, r)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-config", default="config/ablation.yaml")
    args = parser.parse_args()

    run_cfg = load_yaml(args.run_config)
    models_cfg = load_yaml(run_cfg["models_config"])["models"]
    model_specs = {m["id"]: ModelSpec(**m) for m in models_cfg}

    persona_components = PersonaComponents.from_yaml(run_cfg["persona_components"])
    toggle_names = run_cfg["toggle_components"]
    combos = powerset(toggle_names)

    scenarios: list[Scenario] = []
    for path in run_cfg["scenarios"]:
        scenarios.extend(Scenario.load_all(path))

    evaluators = build_evaluators(run_cfg["evaluators"])
    repeats = run_cfg.get("repeats", 1)

    out_dir = Path(run_cfg.get("output_dir", "results/ablation"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "run.jsonl"

    print(
        f"{len(combos)} component combos x {len(run_cfg['target_models'])} models x "
        f"{len(scenarios)} scenarios x {repeats} repeats"
    )

    with open(out_path, "w", encoding="utf-8") as out_f:
        for combo in combos:
            persona = persona_components.build(set(combo))
            components_field = {c: (c in combo) for c in toggle_names}

            for model_id in run_cfg["target_models"]:
                client = ModelClient(model_specs[model_id])
                for scenario in scenarios:
                    for repeat in range(repeats):
                        first_break = run_scenario(
                            client,
                            persona,
                            scenario,
                            evaluators,
                            out_f,
                            repeat=repeat,
                            extra_fields={"components": components_field},
                        )
                        print(
                            f"[{persona.name}] [{model_id}] {scenario.id} "
                            f"(repeat {repeat}): first_break_turn={first_break}"
                        )

    print(f"\nresults written to {out_path}")


if __name__ == "__main__":
    main()
