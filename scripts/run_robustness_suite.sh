#!/bin/bash
# 페르소나 강건성(붕괴율) 실험 9개를 순서대로 실행한다.
# 3페르소나(student_yoo/teacher_park/worker_lee) x 3조건(textonly/portrait/portrait_vpa),
# 파일마다 gpt-4o-mini + qwen3-vl-4b 두 모델을 함께 실행한다 (config/models.yaml 참고).
#
# 사전 준비:
#   - ad005에 Qwen3-VL-4B-Instruct가 vLLM으로 떠 있어야 함 (config/models.yaml의 base_url/api_key 확인)
#   - apikey.txt(또는 OPENAI_API_KEY 환경변수)에 OpenAI 키가 있어야 함
#   - 먼저 --dry-run으로 배선만 확인해보는 걸 권장:
#       python run.py --run-config config/robustness/student_yoo_textonly.yaml --dry-run
#
# 규모: 9개 파일 x 2모델 x 20문항 x 5회 = 1,800턴 (모델별 900턴씩).
#       judge 호출(self_negation, 항상 gpt-4o-mini)까지 포함하면 OpenAI 호출은 이보다 많음.
#       시간이 꽤 걸리니 tmux/nohup 등으로 백그라운드 실행 권장.
#
# 사용법: bash scripts/run_robustness_suite.sh

set -euo pipefail

CONFIG_DIR="config/robustness"

for cfg in "$CONFIG_DIR"/*.yaml; do
  echo "=== 실행: $cfg ==="
  python run.py --run-config "$cfg" --summary
  echo
done

echo "모든 실행 완료. 페르소나 매크로 평균으로 집계하려면:"
echo "  python scripts/aggregate_macro.py config/manifest_robustness.yaml"
echo "시각적 일치율(이미 존재하는 데이터)과 나란히 보려면:"
echo "  python scripts/aggregate_macro.py config/manifest_visual.yaml"
