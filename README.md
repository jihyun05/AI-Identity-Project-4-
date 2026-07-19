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

## 실행 방법

```bash
python run.py --run-config config/run.yaml
```

- 어떤 persona/scenario/model 조합을 돌릴지는 `config/run.yaml`에서 설정합니다.
- 결과는 턴 단위 JSONL로 `results/run.jsonl`에 저장됩니다.

## 디렉토리 구조

```
config/
  models.yaml         # 대상 모델 + judge 모델 설정 (OpenAI / 로컬 vLLM)
  personas/           # 페르소나 정의 (system prompt + few-shot)
  scenarios/           # 대화 시나리오 (normal / breaking)
  run.yaml            # 실행 설정 (어떤 persona/scenario/model/evaluator를 쓸지)
src/
  model_client.py     # 모델 백엔드 추상화 (OpenAI / 로컬 서빙)
  persona.py, scenario.py
  evaluators/          # 페르소나 붕괴 판정기 (plugin 구조, self_negation부터 시작)
  runner.py
run.py                 # 실행 진입점
scripts/
  serve_qwen3.sh       # ad005에서 Qwen3를 vLLM으로 서빙하는 스크립트
```
