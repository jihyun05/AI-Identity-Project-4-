from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def summarize_results(path: str | Path, detail: bool = False) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")

    totals: dict[str, int] = {}
    evaluator_counts: dict[str, dict[str, int]] = {}
    model_evaluator_counts: dict[str, dict[str, dict[str, int]]] = {}
    category_evaluator_counts: dict[str, dict[str, dict[str, int]]] = {}
    scenario_evaluator_counts: dict[str, dict[str, dict[str, int]]] = {}

    n_records = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n_records += 1
            record = json.loads(line)
            model = record.get("model", "unknown")
            category = record.get("category", "unknown")
            scenario = record.get("scenario", "unknown")
            for eval_obj in record.get("evaluations", []):
                name = eval_obj.get("evaluator", "unknown")
                broken = bool(eval_obj.get("broken", False))

                evaluator_counts.setdefault(name, {"count": 0, "broken": 0})
                evaluator_counts[name]["count"] += 1
                evaluator_counts[name]["broken"] += int(broken)

                model_evaluator_counts.setdefault(model, {})
                model_evaluator_counts[model].setdefault(name, {"count": 0, "broken": 0})
                model_evaluator_counts[model][name]["count"] += 1
                model_evaluator_counts[model][name]["broken"] += int(broken)

                category_evaluator_counts.setdefault(category, {})
                category_evaluator_counts[category].setdefault(name, {"count": 0, "broken": 0})
                category_evaluator_counts[category][name]["count"] += 1
                category_evaluator_counts[category][name]["broken"] += int(broken)

                if detail:
                    scenario_evaluator_counts.setdefault(scenario, {})
                    scenario_evaluator_counts[scenario].setdefault(name, {"count": 0, "broken": 0})
                    scenario_evaluator_counts[scenario][name]["count"] += 1
                    scenario_evaluator_counts[scenario][name]["broken"] += int(broken)

    def build_metrics(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, float | int]]:
        return {
            key: {
                "count": data["count"],
                "broken": data["broken"],
                "consistent": data["count"] - data["broken"],
                "broken_rate": data["broken"] / data["count"] if data["count"] else 0.0,
                "consistent_rate": (data["count"] - data["broken"]) / data["count"] if data["count"] else 0.0,
            }
            for key, data in counts.items()
        }

    summary = {
        "total_records": n_records,
        "total_evaluations": sum(v["count"] for v in evaluator_counts.values()),
        "evaluator_summary": build_metrics(evaluator_counts),
        "model_evaluator_summary": {
            model: build_metrics(counts) for model, counts in model_evaluator_counts.items()
        },
        "category_evaluator_summary": {
            category: build_metrics(counts) for category, counts in category_evaluator_counts.items()
        },
        "scenario_evaluator_summary": {
            scenario: build_metrics(counts) for scenario, counts in scenario_evaluator_counts.items()
        } if detail else {},
    }

    lines = [
        f"Loaded {n_records} records from {path}",
        f"Total evaluator calls: {summary['total_evaluations']}",
    ]
    for evaluator, metrics in summary["evaluator_summary"].items():
        lines.append(
            f"- {evaluator}: count={metrics['count']} broken={metrics['broken']} "
            f"broken_rate={metrics['broken_rate']:.2%} consistent_rate={metrics['consistent_rate']:.2%}"
        )

    for model, counts in summary["model_evaluator_summary"].items():
        for evaluator, metrics in counts.items():
            lines.append(
                f"  [{model}] {evaluator}: broken_rate={metrics['broken_rate']:.2%} "
                f"consistent_rate={metrics['consistent_rate']:.2%}"
            )

    for category, counts in summary["category_evaluator_summary"].items():
        for evaluator, metrics in counts.items():
            lines.append(
                f"  [{category}] {evaluator}: broken_rate={metrics['broken_rate']:.2%} "
                f"consistent_rate={metrics['consistent_rate']:.2%}"
            )

    summary_text = "\n".join(lines)
    summary["summary_text"] = summary_text
    return summary


def main():
    parser = argparse.ArgumentParser(description="Summarize run result JSONL files.")
    parser.add_argument("--in-path", required=True, help="Input run.jsonl file.")
    parser.add_argument("--out-path", default=None, help="Optional JSON file to write the summary.")
    parser.add_argument("--detail", action="store_true", help="Include scenario-level summary details.")
    args = parser.parse_args()

    summary = summarize_results(args.in_path, detail=args.detail)
    print(summary["summary_text"])
    if args.out_path:
        out_path = Path(args.out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Summary written to {out_path}")


if __name__ == "__main__":
    main()
