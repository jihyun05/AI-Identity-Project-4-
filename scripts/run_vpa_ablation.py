"""VPA(Visual Persona Anchoring) 구성요소 ablation — 이미지-페르소나 결속(B),
정체성 재확인(R), 시각 정보 범위 지정(S) 세 문장 블록의 2^3=8개 조합을 순회하며
붕괴율(self_negation x breaking.yaml)과 시각적 일치율(visual_consistency x
visual_consistency.yaml)을 함께 측정한다.

b/r/s가 전부 꺼진 조합은 Portrait 조건과 동일하다 (같은 role/avatar/few_shot).
few_shot은 Portrait과 동일하게 고정 — 8개 조합 간 유일한 차이는 B/R/S 텍스트뿐이다.

gpt-4o-mini(OpenAI)와 qwen3-vl-4b(ad002 로컬 서버)는 완전히 별개의 백엔드라 서로를
기다릴 이유가 없다. judge는 두 evaluator 모두 항상 gpt-4o-mini(OpenAI)를 쓰지만,
OpenAI 클라이언트는 스레드 세이프해서 두 레인이 동시에 호출해도 문제없다 — 그래서
모델별로 스레드를 하나씩 띄워 병렬 실행한다 (순차 실행 대비 총 소요 시간이 대략 절반).

사용법:
    python scripts/run_vpa_ablation.py                     # 전체 3페르소나 x 8조합 x 2모델
    python scripts/run_vpa_ablation.py --persona student_yoo --combo b r
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_yaml
from src.evaluators.registry import build_evaluators
from src.model_client import ModelClient, ModelSpec
from src.persona import PersonaComponents
from src.runner import run_scenario
from src.scenario import Scenario

COMPONENT_ORDER = ["b", "r", "s"]
# 논문 표 순서: 없음, B, R, S, B+R, B+S, R+S, B+R+S
COMBO_ORDER = [
    frozenset(),
    frozenset({"b"}),
    frozenset({"r"}),
    frozenset({"s"}),
    frozenset({"b", "r"}),
    frozenset({"b", "s"}),
    frozenset({"r", "s"}),
    frozenset({"b", "r", "s"}),
]
PERSONAS = ["student_yoo", "teacher_park", "worker_lee"]

_print_lock = threading.Lock()


def combo_label(active: frozenset[str]) -> str:
    return "".join(c for c in COMPONENT_ORDER if c in active) or "none"


def run_one(client, persona, scenarios, evaluators, out_path: Path, repeats: int):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out_f:
        for scenario in scenarios:
            for repeat in range(repeats):
                run_scenario(client, persona, scenario, evaluators, out_f, repeat=repeat)


def run_for_model(
    model_id: str,
    model_spec: ModelSpec,
    persona_names: list[str],
    combos: list[frozenset[str]],
    breaking_scenarios,
    visual_scenarios,
    repeats: int,
    out_root: Path,
    started: float,
):
    # 모델/evaluator 클라이언트는 레인(스레드)마다 독립적으로 만든다 —
    # openai.OpenAI 자체는 스레드 세이프하지만, 굳이 공유해서 의심의 여지를 만들지 않는다.
    client = ModelClient(model_spec)
    self_negation_eval = build_evaluators(["self_negation"])
    visual_eval = build_evaluators(["visual_consistency"])

    total = len(persona_names) * len(combos)
    done = 0
    for persona_name in persona_names:
        components = PersonaComponents.from_yaml(
            f"config/personas/{persona_name}_vpa_components.yaml"
        )
        for active in combos:
            label = combo_label(active)
            persona = components.build(active)

            breaking_out = out_root / persona_name / label / model_id / "breaking.jsonl"
            run_one(client, persona, breaking_scenarios, self_negation_eval, breaking_out, repeats)

            visual_out = out_root / persona_name / label / model_id / "visual.jsonl"
            run_one(client, persona, visual_scenarios, visual_eval, visual_out, repeats)

            done += 1
            elapsed = time.time() - started
            with _print_lock:
                print(
                    f"[{model_id}] [{done}/{total}] {persona_name} / {label} 완료 "
                    f"(경과 {elapsed:.0f}s)"
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", nargs="*", default=PERSONAS)
    parser.add_argument(
        "--combo", nargs="*", default=None,
        help="특정 조합만 돌리고 싶을 때 (예: --combo b r 는 B+R 조합 하나만). 생략하면 8개 전부.",
    )
    parser.add_argument("--models-config", default="config/models.yaml")
    parser.add_argument("--breaking-scenarios", default="config/scenarios/breaking.yaml")
    parser.add_argument("--visual-scenarios", default="config/scenarios/visual_consistency.yaml")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output-dir", default="results/vpa_ablation")
    args = parser.parse_args()

    models_cfg = load_yaml(args.models_config)["models"]
    model_specs = {m["id"]: ModelSpec(**m) for m in models_cfg}
    target_models = list(model_specs.keys())

    breaking_scenarios = Scenario.load_all(args.breaking_scenarios)
    visual_scenarios = Scenario.load_all(args.visual_scenarios)

    combos = COMBO_ORDER if args.combo is None else [frozenset(args.combo)]
    out_root = Path(args.output_dir)
    started = time.time()

    print(
        f"{len(target_models)}개 모델을 병렬 레인으로 실행: {target_models} "
        f"({len(args.persona)}페르소나 x {len(combos)}조합)"
    )

    with ThreadPoolExecutor(max_workers=len(target_models)) as pool:
        futures = [
            pool.submit(
                run_for_model,
                model_id,
                model_specs[model_id],
                args.persona,
                combos,
                breaking_scenarios,
                visual_scenarios,
                args.repeats,
                out_root,
                started,
            )
            for model_id in target_models
        ]
        for f in futures:
            f.result()  # 예외가 있었다면 여기서 다시 raise됨

    print(f"\n전체 완료 (총 {time.time() - started:.0f}s). 결과: {out_root}/<persona>/<combo>/<model>/{{breaking,visual}}.jsonl")


if __name__ == "__main__":
    main()
