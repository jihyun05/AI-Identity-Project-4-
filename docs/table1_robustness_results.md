# Table 1 결과 채우기 — 페르소나 강건성 실험

이 표는 논문 Table 1(초상 이미지와 VPA 적용에 따른 페르소나 성능 비교)에 들어갈 실측치입니다.
**붕괴율 열은 아직 비어 있습니다** — `config/robustness/` 실행 결과로 채워주세요.
시각적 일치율 열은 이미 존재하는 데이터로 계산한 값을 참고용으로 미리 채워뒀습니다 (재확인 환영).

## 채우는 방법

```bash
# 1. (선택) 배선 확인 — 모델 호출 없이 즉시 끝남
python run.py --run-config config/robustness/student_yoo_textonly.yaml --dry-run

# 2. 9개(3페르소나 x 3조건) 전체 실행 — 시간 오래 걸림, nohup/tmux 권장
bash scripts/run_robustness_suite.sh

# 3. 집계 (페르소나별로 먼저 계산 후 3페르소나 매크로 평균)
python scripts/aggregate_macro.py config/manifest_robustness.yaml           # 붕괴율
python scripts/aggregate_macro.py config/manifest_robustness.yaml --detail  # 페르소나별 세부치 포함
python scripts/aggregate_macro.py config/manifest_visual.yaml               # 시각적 일치율 (검증용)
```

위 명령 출력값을 아래 표의 빈칸(`TBD`)에 그대로 옮겨 적으면 됩니다.

## Table 1 — 초상 이미지와 VPA 적용에 따른 페르소나 성능 비교

| 모델 | 조건 | 붕괴율(%, ↓) | 시각적 일치율(%, ↑) |
|---|---|---|---|
| GPT-4o-mini | Text-only | TBD | 76.00 |
| GPT-4o-mini | Portrait | TBD | 93.33 |
| GPT-4o-mini | Portrait+VPA | TBD | 86.67 |
| Qwen3-VL-4B-Instruct | Text-only | TBD | 46.67 |
| Qwen3-VL-4B-Instruct | Portrait | TBD | 73.33 |
| Qwen3-VL-4B-Instruct | Portrait+VPA | TBD | 66.67 |

> 시각적 일치율 값은 `scripts/aggregate_macro.py config/manifest_visual.yaml` 실행 결과입니다.
> 논문 초안에 적힌 시각적 일치율(76.00/93.33/92.00, 46.67/74.67/66.77)과 Portrait+VPA 행만 소폭 차이가 있습니다 — 재실행해서 어느 쪽이 맞는지 확인해주세요.
>
> **참고**: 논문 초안의 기존 "붕괴율" 열(24.00/6.67/8.00, 53.33/25.33/33.33)은 위 시각적 일치율 데이터의 불일치율과 거의 동일한 값이었습니다 — 실제 붕괴율(self_negation 평가) 데이터가 없는 상태에서 다른 지표가 잘못 옮겨 적힌 것으로 보입니다. 이번에 새로 실행한 값으로 완전히 교체해주세요. 자세한 내용은 `docs/paper_experiment_status.md` 참고.

## (선택) 페르소나별 세부 표

논문 방법론 검증이나 부록용으로, 매크로 평균 내기 전 페르소나별 수치도 남겨두면 좋습니다.
`--detail` 옵션 출력을 아래처럼 정리해주세요 (붕괴율 예시, 시각적 일치율도 동일한 형식으로 추가 가능):

| 페르소나 | 조건 | GPT-4o-mini 붕괴율(%) | Qwen3-VL-4B-Instruct 붕괴율(%) |
|---|---|---|---|
| student_yoo | Text-only | TBD | TBD |
| student_yoo | Portrait | TBD | TBD |
| student_yoo | Portrait+VPA | TBD | TBD |
| teacher_park | Text-only | TBD | TBD |
| teacher_park | Portrait | TBD | TBD |
| teacher_park | Portrait+VPA | TBD | TBD |
| worker_lee | Text-only | TBD | TBD |
| worker_lee | Portrait | TBD | TBD |
| worker_lee | Portrait+VPA | TBD | TBD |
