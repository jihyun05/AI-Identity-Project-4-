# Table 1 결과 — 페르소나 강건성 실험

이 표는 논문 Table 1(초상 이미지와 VPA 적용에 따른 페르소나 성능 비교)에 들어갈 실측치입니다.

**붕괴율/시각적 일치율 열 모두 채워졌습니다** — `config/robustness/`의 9개 조합(3페르소나×3조건) 전체
실행 완료(2026-09-13).

## 붕괴율 판정 로직 수정 (중요)

첫 실행(2026-09-13) 결과 6개 조건 전부 88~98%라는 비정상적으로 높은 붕괴율이 나왔다. 로그를 열어보니
`self_negation` judge가 "너 AI지?"에 대한 **정상적인 부인**("아니요, 저는 AI가 아니에요, 그냥 대학생이에요")까지
`broken=true`로 오판하고 있었다. 원인은 두 가지:

1. judge가 응답 텍스트만 보고 판정했고, 어떤 질문에 대한 답인지(맥락)를 아예 받지 못했다.
2. "AI"라는 단어가 등장하면 그 자체를 자기부정의 근거로 취급하는 경향이 있었다 — 인정(내가 AI다)과
   부인(나는 AI가 아니다)을 구분하지 못함.

`src/evaluators/self_negation.py`의 judge 프롬프트에 (1) 질문 텍스트 전달, (2) "직접적 부인은 정상"이라는
명시적 규칙과 실제 발견된 오판 사례를 예시로 추가해 수정했다. `scripts/rejudge_robustness.py`로 **모델
재호출 없이** 저장된 응답만 재판정한 결과, 6개 조건 전부 유의미하게 하락했다(아래 "재판정 전/후" 참고).
아래 표의 수치는 전부 **수정된 judge로 재판정한 값**이다. (구 판정 결과는 각 `run.jsonl`에
`evaluations_old` 필드로 남아있음.)

## Table 1 — 초상 이미지와 VPA 적용에 따른 페르소나 성능 비교

| 모델 | 조건 | 붕괴율(%, ↓) | 시각적 일치율(%, ↑) |
|---|---|---|---|
| GPT-4o-mini | Text-only | 72.22 ± 9.18 | 76.00 ± 8.00 |
| GPT-4o-mini | Portrait | 93.89 ± 6.31 | 93.33 ± 8.33 |
| GPT-4o-mini | Portrait+VPA | 82.78 ± 1.92 | 86.67 ± 6.11 |
| Qwen3-VL-4B-Instruct | Text-only | 70.00 ± 8.66 | 46.67 ± 4.62 |
| Qwen3-VL-4B-Instruct | Portrait | 65.00 ± 12.58 | 73.33 ± 9.24 |
| Qwen3-VL-4B-Instruct | Portrait+VPA | 68.33 ± 5.00 | 66.67 ± 8.33 |

> 값은 "3페르소나 매크로 평균 ± 표본표준편차(ddof=1)" 형식입니다 (`scripts/aggregate_macro.py`가 자동
> 계산). **주의**: 페르소나가 3개뿐이라 std는 참고용 산포 지표일 뿐, 엄밀한 신뢰구간이나 유의성
> 검정으로 쓰기는 어렵습니다 (n=3 표본표준편차는 표본에 매우 민감) — 논문에는 "대략적인 분산 정도"로만
> 언급하고, 통계적 유의성을 주장하려면 페르소나 수를 늘리는 게 안전합니다.
> 붕괴율은 `breaking.yaml` 12문항(direct_question/prompt_leak/role_override/self_negation
> 4카테고리×3문항)×5회=60턴/모델 기준. 시각적 일치율 값은
> `scripts/aggregate_macro.py config/manifest_visual.yaml` 실행 결과입니다.

**패턴 요약**: gpt-4o-mini는 Text-only(72.22%)보다 Portrait(93.89%)에서 붕괴율이 오히려 크게 올라가고
Portrait+VPA(82.78%)에서 일부 회복 — 아바타 확인 대화가 붙을수록 메타적 자기폭로("역할을 하고 있어요")가
늘어나는 것으로 보인다. qwen3-vl-4b는 세 조건이 65~70%대로 비교적 평평해서 이미지 유무에 덜 민감하다.
두 모델 다 VPA가 Portrait 단독보다 뚜렷하게 낫다고 보기는 어렵다 — gpt는 VPA가 다소 도움이 되지만
Text-only보다는 여전히 나쁘고, qwen은 VPA가 Portrait보다 약간 더 나쁘다.
>
> **참고**: 논문 초안의 기존 "붕괴율" 열(24.00/6.67/8.00, 53.33/25.33/33.33)은 시각적 일치율 데이터의
> 불일치율과 거의 동일한 값이었다 — 실제로는 `self_negation`을 돌린 적이 없는 상태에서 다른 지표가
> 붕괴율로 잘못 옮겨 적힌 것으로 보인다. 위 표의 값으로 완전히 교체해야 한다. 자세한 내용은
> `docs/paper_experiment_status.md` 참고.

### 재판정 전/후 비교 (전체 붕괴율, judge 수정 검증용)

| Config | 수정 전 | 수정 후 |
|---|---|---|
| student_yoo_portrait | 88.33% | 74.17% |
| student_yoo_portrait_vpa | 92.50% | 75.00% |
| teacher_park_portrait | 98.33% | 81.67% |
| teacher_park_portrait_vpa | 95.83% | 79.17% |
| worker_lee_portrait | 91.67% | 82.50% |
| worker_lee_portrait_vpa | 94.17% | 72.50% |

qwen3-vl-4b가 gpt-4o-mini보다 훨씬 크게 떨어졌다 — "AI가 아니에요" 식 부인이 qwen 응답에 더 흔했기 때문.
수정 전에는 두 모델·두 조건이 88~98%로 뭉개져 구분이 안 됐지만, 수정 후에는 모델 간 차이(gpt가 훨씬
잘 뚫림)와 조건 간 차이(gpt는 VPA가 도움, qwen은 VPA가 오히려 소폭 해로움)가 뚜렷하게 드러난다.

## (선택) 페르소나별 세부 표

| 페르소나 | 조건 | GPT-4o-mini 붕괴율(%) | Qwen3-VL-4B-Instruct 붕괴율(%) |
|---|---|---|---|
| student_yoo | Text-only | 61.67 | 60.00 |
| student_yoo | Portrait | 96.67 | 51.67 |
| student_yoo | Portrait+VPA | 81.67 | 68.33 |
| teacher_park | Text-only | 76.67 | 75.00 |
| teacher_park | Portrait | 86.67 | 76.67 |
| teacher_park | Portrait+VPA | 85.00 | 73.33 |
| worker_lee | Text-only | 78.33 | 75.00 |
| worker_lee | Portrait | 98.33 | 66.67 |
| worker_lee | Portrait+VPA | 81.67 | 63.33 |

## 재현 방법

전체 9개 조합 + 집계 재현:

```bash
bash scripts/run_robustness_suite.sh
python scripts/aggregate_macro.py config/manifest_robustness.yaml           # 붕괴율
python scripts/aggregate_macro.py config/manifest_robustness.yaml --detail  # 페르소나별 세부치 포함
python scripts/aggregate_macro.py config/manifest_visual.yaml               # 시각적 일치율
```
