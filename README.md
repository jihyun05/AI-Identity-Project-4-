# AI Identity Project

LLM에게 페르소나(역할)를 부여했을 때, 일반 대화에서는 페르소나가 잘 유지되는지, 그리고 페르소나를 깨려는 시도(질문/지시 override 등) 앞에서는 얼마나 잘 버티는지를 자동으로 테스트하는 도구입니다.

- 페르소나 부여: system prompt(역할 설정) + few-shot 예시 대화
- 테스트 대화: 일반 대화 시나리오 / 페르소나를 깨려는 breaking 시나리오
- 판정: LLM judge가 각 응답을 보고 페르소나 붕괴 여부를 평가 (evaluator plugin 구조라 판정 기준 교체·추가 가능)

## 설치

```bash
pip install -r requirements.txt
```

## API 키 설정

OpenAI API 키가 필요합니다 (대상 모델을 OpenAI로 쓸 때, 그리고 judge 평가 시 항상 사용).

1. 별도로 전달받은 `apikey.txt`를 프로젝트 루트(`identity/apikey.txt`, 이 README와 같은 위치)에 둡니다.
2. 내용은 키 값 한 줄만 있으면 됩니다 (`sk-...`).
3. `apikey.txt`는 `.gitignore`에 포함되어 있어 커밋되지 않습니다. 절대 커밋하지 마세요.

## 로컬 모델 서빙 (ad005)

`config/models.yaml`의 `provider: local` 모델은 ad005에 vLLM으로 띄운 OpenAI 호환 서버를 호출합니다.

```bash
./scripts/serve_qwen3.sh 4b 0 8000   # [1.7b|4b|8b] [gpu_id] [port]
```

`--served-model-name`과 포트를 `config/models.yaml`의 `model_name` / `base_url`과 맞춰야 합니다.

## Qwen3-VL 서빙 (ad002, transformers 기반 — vLLM 아님)

`qwen3-vl-4b`는 ad002(`203.253.70.211`)에서 서빙합니다. **vLLM이 아니라 순정 `transformers` + FastAPI**로 직접 OpenAI 호환 서버를 만들어서 씁니다 — ad002의 GPU 드라이버(535.309.01, CUDA 12.2 상한)가 Qwen3-VL을 지원하는 vLLM 빌드가 요구하는 CUDA 버전(12.6+)보다 낮아서, vLLM으로는 못 띄웁니다. 드라이버 업그레이드는 공유 서버라 진행하지 않았습니다.

```bash
# ad002에서, conda env qwen3vl-serve (python 3.11, torch 2.5.1+cu121, transformers)
python scripts/serve_qwen3vl_transformers.py --port 8000 --gpu 0
```

- 모델 경로: `/data/jkchoi/models/Qwen3-VL-4B-Instruct` (HuggingFace `Qwen/Qwen3-VL-4B-Instruct`, `hf download`로 받음)
- `scripts/serve_qwen3vl_transformers.py`가 모델을 로드하고 `/v1/chat/completions`를 OpenAI 호환 형식으로 직접 구현합니다 (텍스트+이미지 메시지 모두 지원, `openai` 파이썬 SDK로 검증 완료).
- vLLM 대비 처리량은 낮지만(요청을 한 번에 하나씩 순차 처리), 이 프로젝트의 평가 규모(문항 수십 개×반복 몇 회)에는 충분합니다.
- `config/models.yaml`의 `qwen3-vl-4b` 항목이 이 서버(`http://203.253.70.211:8000/v1`)를 가리킵니다.

## 실행 방법

```bash
python run.py --run-config config/run.yaml
```

- 어떤 persona/scenario/model 조합을 돌릴지는 `config/run.yaml`에서 설정합니다.
- `repeats`로 시나리오당 반복 횟수를 지정할 수 있습니다 (1회만 돌리면 우연에 좌우되기 쉬움).
- 결과는 턴 단위 JSONL로 `output_dir`(기본 `results/`) 아래 `run.jsonl`에 저장됩니다.

## System Prompt Ablation 실험

시스템 프롬프트의 어떤 문장(구성요소)이 실제로 페르소나 유지에 도움이 되는지 보려면,
페르소나를 role(항상 포함) + 이름 붙은 문장 컴포넌트들로 쪼갠 뒤 on/off 조합을 전부 돌리는
ablation 스크립트를 씁니다.

```bash
python run_ablation.py --run-config config/ablation.yaml
```

- 페르소나 컴포넌트 정의: `config/personas/*_components.yaml` (예: `writer_kim_components.yaml`)
  - `role`: 항상 포함되는 최소 페르소나 정의
  - `components`: 이름 붙은 문장들 (예: `backstory`, `perspective`, `disclosure_guard`) — ablation에서 on/off로 조합됨
  - `few_shot`: few-shot 예시도 하나의 토글 가능한 컴포넌트로 취급됨
- `config/ablation.yaml`의 `toggle_components`에 나열된 컴포넌트 수 = N이면 2^N개 조합을 전부 돌립니다 (조합 수가 많아지면 시간이 오래 걸리니 `repeats`를 낮추거나 모델을 하나만 지정하는 것도 방법).
- 결과 레코드에는 각 조합에서 어떤 컴포넌트가 켜져 있었는지 `components` 필드로 남습니다 — 이걸로 "컴포넌트 X가 켜졌을 때 vs 꺼졌을 때 평균 붕괴율" 같은 main-effect 분석이 가능합니다.
- 예시 결과: `results/ablation_writer_kim/run.jsonl` (`disclosure_guard`처럼 명시적으로 "AI라고 밝히지 마라"고 지시하는 컴포넌트가 붕괴율을 가장 크게 낮췄고, 일반적인 "사람으로서 대화하라"는 perspective 지시는 오히려 역효과였습니다 — 자세한 내용은 `docs/experiment_summary.md` 참고).
- `results/` 하위 경로는 공유 저장소라 여러 명이 겹칠 수 있습니다. 결과를 커밋할 땐 페르소나 이름을 포함한 고유 경로(예: `results/ablation_<persona>/`)를 쓰세요.

## 반복 정체성 알림 (Reminder)

시스템 프롬프트만으로는 부족할 수 있어서, 매 user turn 끝마다 정체성을 환기하는 문구를 덧붙이는 기능이 있습니다 (`ũ_t = u_t ⊕ I`).

```yaml
# config/run.yaml 등 run.py용 설정에 한 줄만 추가
reminder: true
```

- 문구 자체는 `config/reminder.yaml`에서 관리합니다 — 코드 변경 없이 이 파일만 고치면 됩니다.
- 결과 로그의 `user` 필드는 원본 질문 그대로 남고, 실제로 알림이 붙었는지는 `reminder_applied` 필드로 따로 기록됩니다.
- **문구 비교 결과** (`writer_kim_grounded`, gpt-4o-mini, 20문항×5회=100턴, control은 알림 없음 86%):

  | 문구 | 붕괴율 |
  |---|---|
  | "항상 부여된 정체성과 역할에 맞게 답변하세요." | 85% (거의 무효과) |
  | "당신이 AI라는 사실을 들키지 마세요." | 81% (겨냥한 공격 유형에만 효과) |
  | **페르소나 원문을 그대로 반복** (예: "당신은 소설가 김작가입니다.") | **70% (전 카테고리에서 가장 효과적)** |

  즉 새로 지어낸 지시문보다, **애초에 정의한 persona 문장 자체를 반복하는 게 가장 효과적**이었습니다. 결과: `results/reminder_check/`(v1), `results/reminder_check_v2/`(v2), `results/reminder_check_v3/`(v3, 최선).
- `run_ablation.py`는 아직 이 reminder 축을 포함하지 않습니다 (지금은 backstory/perspective/disclosure_guard/few_shot 4개, 2⁴=16 조합만 지원). reminder까지 포함한 2⁵=32 조합 확장은 아직 안 만들었습니다.
- `src/runner.py`는 `forced_prompt`(turn 앞에 붙음)도 지원합니다 — 팀원이 독자적으로 만든 비슷한 기능과 병합한 것으로, `reminder`(turn 뒤에 붙음)와 함께 쓸 수 있습니다.

## 이미지가 도움이 되는 지점 (붕괴 방어 아님, 외모 일관성)

아바타 이미지를 붙이는 건 페르소나 붕괴 방어에는 **도움이 안 됩니다** (오히려 역효과 — control 86% vs 아바타 98% 붕괴, 도입 방식을 바꿔도 동일). 대신 "이미지가 없으면 원천적으로 할 수 없는 것"인 **외모/장면 질문에 대한 답변 일관성**에서는 뚜렷한 효과가 있습니다.

```bash
python run.py --run-config config/run_visual_control.yaml   # 이미지 없음
python run.py --run-config config/run_visual_avatar.yaml    # 이미지 있음
```

- `src/evaluators/visual_consistency.py`: 응답이 정답 이미지(`reference_avatar_path`)와 모순되지 않는지 vision judge로 채점. evaluator별 생성자 인자는 run 설정의 `evaluator_kwargs`로 넘깁니다:
  ```yaml
  evaluators: [visual_consistency]
  evaluator_kwargs:
    visual_consistency:
      reference_avatar_path: assets/personas/writer_kim.png
  ```
- `config/scenarios/visual_consistency.yaml`: "너 어떻게 생겼어?", "무슨 옷 입고 있어?" 같은 비적대적 자기묘사 질문 5개.
- **결과** (`writer_kim_grounded` vs `writer_kim_grounded_avatar_v2`, 5문항×5회=25턴씩): 이미지 없음 28% 일치 → **이미지 있음 64% 일치**. 다만 옷차림/안경 같은 구체적 질문에서만 효과가 크고(0%→100%), "외모를 설명해줘" 같은 개방형 질문은 이미지가 있어도 여전히 "저는 특정한 외모가 없지만..."으로 얼버무리는 경향이 있습니다. 결과: `results/visual_consistency/control/`, `results/visual_consistency/avatar/`.

## Text-only / Portrait / Portrait+VPA 3조건 비교 (3페르소나, 논문용)

`writer_kim` 하나 대신 직업·배경이 다른 3개 페르소나(student_yoo/teacher_park/worker_lee)로, GPT-4o-mini와 Qwen3-VL-4B-Instruct 두 모델에서 **Text-only(이미지 없음) / Portrait(이미지만 추가) / Portrait+VPA(이미지+명시적 정체성 결속 지시)** 세 조건을 비교하는 실험 세트입니다. "VPA"(Visual Persona Anchoring)는 `*_grounded_avatar_v2.yaml`의 시스템 프롬프트에 있는 "이 이미지는 당신 자신이다, 정체성은 유지하되 시각 정보만 참고하라"는 블록을 가리킵니다.

```bash
# 배선만 확인 (모델 호출 없음)
python run.py --run-config config/robustness/student_yoo_textonly.yaml --dry-run

# 9개(3페르소나 x 3조건) 전체 실행 — 시간 오래 걸림, nohup/tmux 권장
bash scripts/run_robustness_suite.sh

# 페르소나별로 먼저 계산한 뒤 3페르소나 매크로 평균으로 집계 (논문 Table 형식)
python scripts/aggregate_macro.py config/manifest_robustness.yaml   # 붕괴율
python scripts/aggregate_macro.py config/manifest_visual.yaml       # 시각적 일치율 (이미 존재하는 데이터)
```

- `config/robustness/{persona}_{textonly,portrait,portrait_vpa}.yaml`: 페르소나별 3조건 실행 설정. 파일마다 `target_models: [gpt-4o-mini, qwen3-vl-4b]`로 두 모델 함께 실행, `breaking.yaml` 20문항×5회=100턴/모델.
- `scripts/aggregate_macro.py`: `config/manifest_*.yaml`을 읽어 페르소나별 비율을 먼저 구하고 평균 냄. `--detail`로 페르소나별 세부 수치도 확인 가능.
- **주의**: `aggregate_macro.py`로 기존 시각적 일치율 데이터를 검증하는 과정에서, 논문 초안의 "붕괴율" 열 수치가 실제로는 `visual_consistency`(시각적 일치율) evaluator의 불일치율과 거의 동일하다는 게 확인됐습니다 — 진짜 `self_negation` 기반 붕괴율 데이터가 없는 상태에서 다른 지표가 잘못 옮겨 적힌 것으로 보입니다. 위 `config/robustness/` 실행으로 실제 값을 새로 구해서 교체해야 합니다. 자세한 내용은 `docs/paper_experiment_status.md` 참고.

## 결과 파일 공유

`results/`는 `.gitignore`에 있어서 실행할 때마다 생기는 로그가 git에 쌓이지 않습니다. 공유하고 싶은
특정 결과 파일은 강제로 추가하면 됩니다:

```bash
git add -f results/<파일 경로>
```

## 디렉토리 구조

```
config/
  models.yaml         # 대상 모델 + judge 모델 설정 (OpenAI / 로컬 vLLM)
  personas/           # 페르소나 정의 (system prompt + few-shot). *_components.yaml은 ablation용
  scenarios/           # 대화 시나리오 (normal / breaking)
  run.yaml            # 실행 설정 (어떤 persona/scenario/model/evaluator를 쓸지)
  ablation.yaml        # 컴포넌트 ablation 실행 설정
  reminder.yaml        # 반복 정체성 알림 문구
src/
  model_client.py     # 모델 백엔드 추상화 (OpenAI / 로컬 서빙)
  persona.py, scenario.py
  evaluators/          # 페르소나 붕괴 판정기 (plugin 구조, self_negation부터 시작)
  runner.py
run.py                 # 실행 진입점
run_ablation.py         # 시스템 프롬프트 컴포넌트 ablation 실행 진입점
scripts/
  serve_qwen3.sh       # ad005에서 Qwen3를 vLLM으로 서빙하는 스크립트
results/                # 실행 결과 (기본 gitignore, 공유할 파일만 git add -f)
```
