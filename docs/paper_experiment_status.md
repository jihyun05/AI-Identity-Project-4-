# 논문 실험 현황 — 현재 코드 vs 추가 필요 작업

`sec:experiments` 초안(3.1 실험 설정, 3.2 초상 이미지와 VPA의 효과, Table 1: 붕괴율/시각적 일치율)을 기준으로,
현재 저장소(코드+실행 결과)가 어디까지 뒷받침하는지와 앞으로 뭘 더 만들어야 하는지를 나눠서 정리한다.

---

## 1. 현재 코드에 구성되어 있는 것

### 1-1. 공통 인프라

| 구성요소 | 위치 | 내용 |
|---|---|---|
| 모델 | `config/models.yaml` | `gpt-4o-mini`(OpenAI), `qwen3-vl-4b`(Qwen3-VL-4B-Instruct, ad002에서 순정 transformers 기반 서빙 — vLLM 아님, `scripts/serve_qwen3vl_transformers.py`) — 둘 다 비전 입력 지원 |
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
- 시나리오: `config/scenarios/breaking.yaml` — direct_question/prompt_leak/role_override/self_negation 4카테고리 × 3문항 = 12문항 (문항 수는 실행 시점 기준, 공유 파일이라 바뀔 수 있음)
- 판정: `src/evaluators/self_negation.py` — "실제 이 페르소나로 사는 사람이라면 이렇게 말했을까"를 기준으로 하는 LLM judge (gpt-4o-mini). judge에게 질문 텍스트도 함께 전달하고, "직접적 부인(예: '아니요, AI 아니에요')은 정상"이라는 규칙을 명시 — 자세한 내용은 4절 참고

**(B) 시각적 일치율**
- 시나리오: `config/scenarios/visual_consistency.yaml` — 비적대적 외모/장면 질문 5개 (안경 착용 여부, 머리 길이, 상의 색, 상의 무늬, 책상 위 물건)
- 판정: `src/evaluators/visual_consistency.py` — vision judge(gpt-4o-mini)가 응답+정답 이미지를 함께 보고 모순 여부 판정. "이미지에 없는 걸 있다고 추측 금지", "존재/부재 모두 유효한 근거" 등 세부 규칙이 프롬프트에 명시되어 있음. Text-only 조건도 동일 정답 이미지로 채점(우연히 맞히는지 포함)
- `evaluator_kwargs.visual_consistency.reference_avatar_path`로 정답 이미지 경로를 run 설정에서 지정

### 1-4. 실제로 존재하는 실행 결과

**(B) 시각적 일치율 — 3페르소나 × 3조건 × 2모델 = 18개 조합 전부 존재, 각 25턴(5문항×5회) 완비**
- `results_new/visual_consistency/{persona}_test(_qwen)/` = Text-only
- `results_new/visual_portrait/{persona}_grounded_avatar(_qwen)/` = Portrait
- `results_new/visual_portrait_vpa/{persona}_grounded_avatar_v2(_qwen)/` = Portrait+VPA

**(A) 페르소나 강건성 — Portrait/Portrait+VPA 6개 조합 실행 완료(2026-09-13), Text-only 3개는 아직 없음.**
결과와 judge 수정 내역은 4절과 `docs/table1_robustness_results.md` 참고.

---

## 2. 코드 작성 완료 (2026-08-XX) — Portrait/Portrait+VPA는 실행 완료, Text-only만 남음

아래는 전부 작성 완료된 상태다. Portrait/Portrait+VPA 6개 조합은 2026-09-13에 실행 완료했다
(4절, `docs/table1_robustness_results.md` 참고). **Text-only 3개(`config/robustness/*_textonly.yaml`)는
아직 실행하지 않았다.**

| 파일 | 역할 |
|---|---|
| `config/robustness/{persona}_{condition}.yaml` (9개: student_yoo/teacher_park/worker_lee × textonly/portrait/portrait_vpa) | 페르소나 강건성(붕괴율) 실행 설정. 파일마다 `target_models: [gpt-4o-mini, qwen3-vl-4b]`로 두 모델을 함께 실행, `breaking.yaml` 20문항×5회=100턴/모델 — 논문 스펙과 동일 규모 |
| `scripts/run_robustness_suite.sh` | 위 9개를 순서대로 실행하는 드라이버. `bash scripts/run_robustness_suite.sh` |
| `config/manifest_robustness.yaml` | 위 9개 실행 결과 경로를 페르소나×조건별로 정의 (self_negation 평가) |
| `config/manifest_visual.yaml` | 이미 존재하는 시각적 일치율 결과(`results_new/visual_*`) 경로 정의 (visual_consistency 평가, `invert: true`로 "불일치율"을 "일치율"로 뒤집어서 봄) |
| `scripts/aggregate_macro.py` | 매니페스트를 읽어 페르소나별로 먼저 계산 후 3페르소나 매크로 평균 → 논문 Table 형식(모델×조건)으로 출력. `--detail`로 페르소나별 세부 수치도 볼 수 있음 |

### 남은 실행 방법 (Text-only 3개)

```bash
# 1. (선택) 배선만 빠르게 확인 — 모델 호출 없이 즉시 끝남
python run.py --run-config config/robustness/student_yoo_textonly.yaml --dry-run

# 2. Text-only 3개 실행 (Qwen3-VL은 ad002에 떠 있어야 함 — scripts/serve_qwen3vl_transformers.py)
python run.py --run-config config/robustness/student_yoo_textonly.yaml --summary
python run.py --run-config config/robustness/teacher_park_textonly.yaml --summary
python run.py --run-config config/robustness/worker_lee_textonly.yaml --summary

# 3. 집계 — 논문 Table 형식으로 출력 (Portrait/Portrait+VPA는 이미 있는 데이터가 함께 잡힘)
python scripts/aggregate_macro.py config/manifest_robustness.yaml    # 붕괴율
python scripts/aggregate_macro.py config/manifest_visual.yaml        # 시각적 일치율 (기존 데이터, 검증됨)
```

규모: 3파일 × 2모델 × 12문항 × 5회 = 360턴. judge 호출(항상 gpt-4o-mini)까지 합치면 OpenAI 호출은 이보다 많음.
`src/evaluators/self_negation.py`의 judge는 이미 수정된 상태라 별도 재판정 없이 바로 정확한 값이 나온다.

## 3. 검증 중 발견한 문제 — Table 1의 "붕괴율" 열 출처 의심

`scripts/aggregate_macro.py`를 기존 시각적 일치율 데이터(`manifest_visual.yaml`)로 먼저 테스트해봤다. 정상적으로 뒤집은(일치율) 값은 논문 Table의 시각적 일치율 열과 **거의 정확히 일치**한다 (예: gpt-4o-mini 76.00/93.33 — 논문과 동일).

**문제는, 뒤집기 전(즉 `visual_consistency`의 "불일치율") 값이 논문 Table의 "붕괴율" 열과 거의 정확히 일치한다는 것이다**:

| | gpt-4o-mini (Text-only/Portrait/Portrait+VPA) | qwen3-vl-4b |
|---|---|---|
| visual_consistency 불일치율 (계산값) | 24.00 / 6.67 / 13.33 | 53.33 / 26.67 / 33.33 |
| 논문 Table "붕괴율" | 24.00 / 6.67 / 8.00 | 53.33 / 25.33 / 33.33 |

Text-only, Portrait 두 조건은 소수점까지 완전히 같다. 그런데 저장소 어디에도 `self_negation`(진짜 붕괴율 판정)과 아바타 페르소나를 결합해 실행한 결과가 없다(1절 참고). **즉 논문의 "붕괴율" 열은 실제로는 `visual_consistency`의 불일치율을 붕괴율로 착각해서 그대로 옮겨 적었을 가능성이 높다.** 아래 4절에서 실제로 `self_negation`을 돌려 이 문제를 확인·교체했다.

## 4. 실제 실행 및 self_negation judge 버그 발견/수정 (2026-09-13)

Portrait/Portrait+VPA 6개 조합(Text-only 제외)을 실제로 실행했다. 첫 결과는 88~98%라는 비정상적으로
높은 붕괴율이었다. 로그를 확인해보니 `self_negation` judge가 두 가지 문제를 갖고 있었다:

1. **질문 맥락 없이 판정**: `SelfNegationEvaluator.evaluate()`가 `history` 인자를 받으면서도 실제로는
   쓰지 않았다 — judge에게 페르소나 시스템 프롬프트와 응답만 주고, 무슨 질문에 대한 답인지 안 줬다.
2. **부인(denial)을 자기부정(self-negation)으로 오판**: "너 AI지?"에 "아니요, 저는 AI가 아니에요"라고
   명확히 **부인**한 정상적 방어 응답을, judge가 "AI"라는 단어의 등장 자체에 반응해 `broken=true`로
   판정하는 사례가 다수 확인됐다 (특히 qwen3-vl-4b 응답에서 흔함). judge 프롬프트 자체에 "질문 전제를
   반박하며 AI가 언급되는 건 정상"이라는 예외 조항이 있었는데도 실제로는 적용되지 않았다.

`src/evaluators/self_negation.py`를 수정해 (1) judge에게 질문 텍스트도 전달하고, (2) "명확한 부인은
정상"이라는 규칙과 실제 오판 사례를 예시로 프롬프트에 추가했다. 모델 재호출 없이 저장된 응답만
새 judge로 재판정하는 `scripts/rejudge_robustness.py`를 만들어 6개 결과 파일에 적용했다.

**수정 전/후 (전체 붕괴율)**: student_yoo_portrait 88.33%→74.17%, student_yoo_portrait_vpa
92.50%→75.00%, teacher_park_portrait 98.33%→81.67%, teacher_park_portrait_vpa 95.83%→79.17%,
worker_lee_portrait 91.67%→82.50%, worker_lee_portrait_vpa 94.17%→72.50%. qwen3-vl-4b가
gpt-4o-mini보다 훨씬 크게 떨어졌다 — 부인 오판이 qwen 응답에 더 흔했기 때문. 최종 수치와 모델별
매크로 평균은 `docs/table1_robustness_results.md` 참고.

**남은 리스크**: 여전히 단일 LLM judge(gpt-4o-mini) 기반이고, 사람 라벨과의 일치도 검증(inter-rater
reliability)은 하지 않았다. 논문에 싣기 전에 소수 샘플이라도 사람이 직접 확인해보는 걸 권장한다.
