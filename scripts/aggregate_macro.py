"""논문 Table(모델 x 조건) 형식으로, 페르소나별 붕괴율/시각적 일치율을 먼저 계산한 뒤
세 페르소나에 대한 매크로 평균을 낸다.

사용법:
    python scripts/aggregate_macro.py config/manifest_robustness.yaml
    python scripts/aggregate_macro.py config/manifest_visual.yaml --detail
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import load_yaml  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def _rate_by_model(paths: list[str], evaluator: str) -> dict[str, tuple[int, int]]:
    """주어진 jsonl 파일들을 모두 읽어서, 모델별 (broken 개수, 전체 개수)를 반환."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # model -> [broken, total]
    for path in paths:
        p = Path(path)
        if not p.exists():
            print(f"  [경고] 결과 파일 없음: {path}", file=sys.stderr)
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                model = record.get("model", "unknown")
                for ev in record.get("evaluations", []):
                    if ev.get("evaluator") != evaluator:
                        continue
                    counts[model][1] += 1
                    if ev.get("broken"):
                        counts[model][0] += 1
    return {model: (b, t) for model, (b, t) in counts.items()}


def aggregate(manifest_path: str, detail: bool = False) -> None:
    manifest = load_yaml(manifest_path)
    evaluator = manifest["evaluator"]
    metric_label = manifest.get("metric_label", "비율(%)")
    invert = manifest.get("invert", False)  # True면 (100 - broken_rate)를 보고 (예: 일치율)
    conditions = manifest["conditions"]
    condition_labels = manifest.get("condition_labels", {c: c for c in conditions})
    personas = manifest["personas"]

    # per_persona_rate[persona][condition][model] = rate(0~100)
    per_persona_rate: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    models_seen: set[str] = set()

    for persona, cond_map in personas.items():
        for condition in conditions:
            paths = cond_map.get(condition, [])
            by_model = _rate_by_model(paths, evaluator)
            rates: dict[str, float] = {}
            for model, (broken, total) in by_model.items():
                rate = (broken / total * 100) if total else float("nan")
                rates[model] = (100 - rate) if invert else rate
                models_seen.add(model)
            per_persona_rate[persona][condition] = rates
            if detail:
                for model, r in rates.items():
                    b, t = by_model[model]
                    print(f"  [{persona}] {condition} / {model}: {b}/{t} ({r:.2f}%)")

    models = sorted(models_seen)

    # macro_rate[model][condition] = mean over personas
    macro_rate: dict[str, dict[str, float]] = {m: {} for m in models}
    for model in models:
        for condition in conditions:
            vals = [
                per_persona_rate[p][condition][model]
                for p in personas
                if model in per_persona_rate[p].get(condition, {})
            ]
            macro_rate[model][condition] = sum(vals) / len(vals) if vals else float("nan")

    print(f"\n=== {metric_label} — 페르소나 매크로 평균 (n={len(personas)}개 페르소나) ===")
    header = "모델".ljust(22) + "".join(condition_labels[c].rjust(16) for c in conditions)
    print(header)
    for model in models:
        row = model.ljust(22) + "".join(
            f"{macro_rate[model][c]:15.2f} " for c in conditions
        )
        print(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", help="config/manifest_robustness.yaml 또는 config/manifest_visual.yaml")
    parser.add_argument("--detail", action="store_true", help="페르소나별 세부 수치도 출력")
    args = parser.parse_args()
    aggregate(args.manifest, detail=args.detail)


if __name__ == "__main__":
    main()
