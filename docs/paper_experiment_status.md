# 논문 실험 현황 — 현재 코드 vs 추가 필요 작업

`sec:experiments` 초안(3.1 실험 설정, 3.2 초상 이미지와 VPA의 효과, Table 1: 붕괴율/시각적 일치율)을 기준으로,
현재 저장소(코드+실행 결과)가 어디까지 뒷받침하는지와 앞으로 뭘 더 만들어야 하는지를 나눠서 정리한다.

---

## 1. 현재 코드에 구성되어 있는 것

### 1-1. 공통 인프라

| 구성요소 | 위치 | 내용 |
|---|---|---|
| 모델 | `config/models.yaml` | `gpt-4o-mini`(OpenAI), `qwen3-vl-4b`(Qwen3-VL-4B-Instruct, ad005 vLLM 서빙) — 둘 다 비전 입력 지원 |
| 페르소나 3종 | `config/personas/{student_yoo,teacher_park,worker_lee}_grounded*.yaml` | 대학생/은퇴 교사/마케팅 직장인 — 직업·배경이 서로 다른 3인 |
| 초상 이미지 | `assets/personas/{student_yoo,teacher_park,worker_lee}.png` | GPT Image로 생성, 페르소나별 1장 |
| 실행 결과 집계 유틸 | `judge.py` | jsonl 결과를 모델/카테고리/시나리오 단위로 집계 (붕괴율 계산) |
| 반복 실행 | `run.py --run-config <yaml>` | `--dry-run`(모델 호출 없이 배선 확인), `--summary`(judge.py 연동 요약 출력) 지원 |

### 1-2. 조건 3단계 (Text-only / Portrait / Portrait+VPA)

페르소나별로 3개 YAML이 조건에 대응한다 (예: teacher_park 기준):

| 조건 | 파일 | 구성 |
|---|---|---|
| **Text-only** | `teacher_park_grounded.yaml` | 역할선언+배경정보+자기노출방지지시 + few-shot 1턴. 이미지 없음. `reference_avatar_path`만 채점용으로 지정 |
| **Portrait** | `teacher_park_grounded_avatar.yaml` | Text-only와 텍스트 동일 + `avatar_path` 추가. 시스템 프롬프트 직후 "이것이 지금 당신의 실제 모습입니다" + 이미지를 보여주고 확인 응답이 삽입됨 |
| **Portrait+VPA** | `teacher_park_grounded_avatar_v2.yaml` | 시스템 프롬프트에 **"[Visual Persona Anchoring]"** 블록 추가 — "이 이미지는 당신 자신이다, 다른 사람으로 해석 금지", "이미지는 외모/배경 참고용으로만 쓰고 정체성(이름·직업·경력)은 유지", "이미지에 없는 건 추측 금지" 지시. + few-shot 안에서 제3자가 "이 사진 본인 맞으시죠?"라고 확인 요청하고 캐릭터가 자연스럽게 인정하는 대화 결합 |

worker_lee, student_yoo도 동일한 3단계 구조로 존재.

### 1-3. 평가 축 2가지

**(A) 페르소나 강건성 (붕괴율)**
- 시나리오: `config/scenarios/breaking.yaml` — direct_question/prompt_leak/role_override/self_negation 4카테고리 × 5문항 = 20문항
- 판정: `src/evaluators/self_negation.py` — "실제 이 페르소나로 사는 사람이라면 이렇게 말했을까"를 기준으로 하는 LLM judge (gpt-4o-mini)

**(B) 시각적 일치율**
- 시나리오: `config/scenarios/visual_consistency.yaml` — 비적대적 외모/장면 질문 5개 (안경 착용 여부, 머리 길이, 상의 색, 상의 무늬, 책상 위 물건)
- 판정: `src/evaluators/visual_consistency.py` — vision judge(gpt-4o-mini)가 응답+정답 이미지를 함께 보고 모순 여부 판정. "이미지에 없는 걸 있다고 추측 금지", "존재/부재 모두 유효한 근거" 등 세부 규칙이 프롬프트에 명시되어 있음. Text-only 조건도 동일 정답 이미지로 채점(우연히 맞히는지 포함)
- `evaluator_kwargs.visual_consistency.reference_avatar_path`로 정답 이미지 경로를 run 설정에서 지정

### 1-4. 실제로 존재하는 실행 결과

**(B) 시각적 일치율 — 3페르소나 × 3조건 × 2모델 = 18개 조합 전부 존재, 각 25턴(5문항×5회) 완비**
- `results_new/visual_consistency/{persona}_test(_qwen)/` = Text-only
- `results_new/visual_portrait/{persona}_grounded_avatar(_qwen)/` = Portrait
- `results_new/visual_portrait_vpa/{persona}_grounded_avatar_v2(_qwen)/` = Portrait+VPA

**(A) 페르소나 강건성 — 실행 결과 없음.** 아래 "2. 추가 필요 작업" 참고.

---

## 2. 코드 작성 완료 (2026-08-XX) — 이제 실행만 하면 됨

아래는 전부 작성 완료된 상태다. **아직 실행은 안 했다** — 학생이 직접 돌려보는 것까지가 다음 단계.

| 파일 | 역할 |
|---|---|
| `config/robustness/{persona}_{condition}.yaml` (9개: student_yoo/teacher_park/worker_lee × textonly/portrait/portrait_vpa) | 페르소나 강건성(붕괴율) 실행 설정. 파일마다 `target_models: [gpt-4o-mini, qwen3-vl-4b]`로 두 모델을 함께 실행, `breaking.yaml` 20문항×5회=100턴/모델 — 논문 스펙과 동일 규모 |
| `scripts/run_robustness_suite.sh` | 위 9개를 순서대로 실행하는 드라이버. `bash scripts/run_robustness_suite.sh` |
| `config/manifest_robustness.yaml` | 위 9개 실행 결과 경로를 페르소나×조건별로 정의 (self_negation 평가) |
| `config/manifest_visual.yaml` | 이미 존재하는 시각적 일치율 결과(`results_new/visual_*`) 경로 정의 (visual_consistency 평가, `invert: true`로 "불일치율"을 "일치율"로 뒤집어서 봄) |
| `scripts/aggregate_macro.py` | 매니페스트를 읽어 페르소나별로 먼저 계산 후 3페르소나 매크로 평균 → 논문 Table 형식(모델×조건)으로 출력. `--detail`로 페르소나별 세부 수치도 볼 수 있음 |

### 실행 방법 (학생이 할 일)

```bash
# 1. (선택) 배선만 빠르게 확인 — 모델 호출 없이 즉시 끝남
python run.py --run-config config/robustness/student_yoo_textonly.yaml --dry-run

# 2. 9개 전체 실행 (시간 오래 걸림 — nohup/tmux 권장, Qwen3-VL은 ad005에 떠 있어야 함)
bash scripts/run_robustness_suite.sh

# 3. 집계 — 논문 Table 형식으로 출력
python scripts/aggregate_macro.py config/manifest_robustness.yaml    # 붕괴율 (새로 실행한 데이터)
python scripts/aggregate_macro.py config/manifest_visual.yaml        # 시각적 일치율 (기존 데이터, 검증됨)
```

규모: 9파일 × 2모델 × 20문항 × 5회 = 1,800턴. judge 호출(항상 gpt-4o-mini)까지 합치면 OpenAI 호출은 이보다 많음.

## 3. 검증 중 발견한 문제 — Table 1의 "붕괴율" 열 출처 의심

`scripts/aggregate_macro.py`를 기존 시각적 일치율 데이터(`manifest_visual.yaml`)로 먼저 테스트해봤다. 정상적으로 뒤집은(일치율) 값은 논문 Table의 시각적 일치율 열과 **거의 정확히 일치**한다 (예: gpt-4o-mini 76.00/93.33 — 논문과 동일).

**문제는, 뒤집기 전(즉 `visual_consistency`의 "불일치율") 값이 논문 Table의 "붕괴율" 열과 거의 정확히 일치한다는 것이다**:

| | gpt-4o-mini (Text-only/Portrait/Portrait+VPA) | qwen3-vl-4b |
|---|---|---|
| visual_consistency 불일치율 (계산값) | 24.00 / 6.67 / 13.33 | 53.33 / 26.67 / 33.33 |
| 논문 Table "붕괴율" | 24.00 / 6.67 / 8.00 | 53.33 / 25.33 / 33.33 |

Text-only, Portrait 두 조건은 소수점까지 완전히 같다. 그런데 저장소 어디에도 `self_negation`(진짜 붕괴율 판정)과 아바타 페르소나를 결합해 실행한 결과가 없다(1절 참고). **즉 논문의 "붕괴율" 열은 실제로는 `visual_consistency`의 불일치율을 붕괴율로 착각해서 그대로 옮겨 적었을 가능성이 높다.** 이 부분은 학생에게 명확히 알려줘야 할 것 같다 — 위 2절 실행을 통해 진짜 붕괴율로 교체해야 함.
