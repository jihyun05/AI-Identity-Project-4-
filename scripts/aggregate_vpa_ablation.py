"""scripts/run_vpa_ablation.py 결과(results/vpa_ablation/<persona>/<combo>/<model>/
{breaking,visual}.jsonl)를 읽어 논문 Table(VPA 구성요소 조합 x 모델) 형식으로
페르소나 매크로 평균 ± 표본표준편차를 출력한다.

사용법: python scripts/aggregate_vpa_ablation.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PERSONAS = ["student_yoo", "teacher_park", "worker_lee"]
MODELS = ["gpt-4o-mini", "qwen3-vl-4b"]
COMBO_ORDER = ["none", "b", "r", "s", "br", "bs", "rs", "brs"]
COMBO_LABEL = {
    "none": "(baseline=Portrait)",
    "b": "B",
    "r": "R",
    "s": "S",
    "br": "B+R",
    "bs": "B+S",
    "rs": "R+S",
    "brs": "B+R+S",
}
ROOT = Path("results/vpa_ablation")


def broken_rate(path: Path) -> float | None:
    if not path.exists():
        return None
    total = broken = 0
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        record = json.loads(line)
        for ev in record.get("evaluations", []):
            total += 1
            broken += int(bool(ev.get("broken")))
    return (broken / total * 100) if total else None


def mean_std(vals: list[float]) -> tuple[float, float]:
    mean = sum(vals) / len(vals) if vals else float("nan")
    std = statistics.stdev(vals) if len(vals) > 1 else float("nan")
    return mean, std


def main():
    # per_persona[combo][model]["breaking"|"visual"] = rate
    per_persona: dict[str, dict[str, dict[str, dict[str, float]]]] = {
        p: {c: {m: {} for m in MODELS} for c in COMBO_ORDER} for p in PERSONAS
    }

    for persona in PERSONAS:
        for combo in COMBO_ORDER:
            for model in MODELS:
                base = ROOT / persona / combo / model
                b = broken_rate(base / "breaking.jsonl")
                v = broken_rate(base / "visual.jsonl")
                if b is not None:
                    per_persona[persona][combo][model]["breaking"] = b
                if v is not None:
                    per_persona[persona][combo][model]["visual"] = 100 - v  # invert -> 일치율

    print("=== 페르소나별 세부치 ===")
    for persona in PERSONAS:
        for combo in COMBO_ORDER:
            row = [f"[{persona}] {COMBO_LABEL[combo]:>18}"]
            for model in MODELS:
                d = per_persona[persona][combo][model]
                b = d.get("breaking", float("nan"))
                v = d.get("visual", float("nan"))
                row.append(f"{model}: 붕괴율={b:5.2f} 일치율={v:5.2f}")
            print("  ".join(row))

    print(f"\n=== VPA 구성요소 조합 x 모델 — 페르소나 매크로 평균 ± 표본표준편차 (n={len(PERSONAS)}) ===")
    header = f"{'조합':<20}" + "".join(f"{m + ' 붕괴율':>18}{m + ' 일치율':>18}" for m in MODELS)
    print(header)
    for combo in COMBO_ORDER:
        cells = []
        for model in MODELS:
            b_vals = [per_persona[p][combo][model]["breaking"] for p in PERSONAS if "breaking" in per_persona[p][combo][model]]
            v_vals = [per_persona[p][combo][model]["visual"] for p in PERSONAS if "visual" in per_persona[p][combo][model]]
            b_mean, b_std = mean_std(b_vals)
            v_mean, v_std = mean_std(v_vals)
            cells.append(f"{b_mean:6.2f}±{b_std:5.2f}    {v_mean:6.2f}±{v_std:5.2f}  ")
        print(f"{COMBO_LABEL[combo]:<20}" + "".join(cells))


if __name__ == "__main__":
    main()
