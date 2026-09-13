# VPA 구성요소 분석 결과 (sec:vpa_ablation, Table: VPA 구성요소 조합에 따른 성능 비교)

`_grounded_avatar_v2.yaml`의 `[Visual Persona Anchoring]` 블록을 세 문장 단위로 분리해
B(이미지-페르소나 결속) / R(정체성 재확인) / S(시각 정보 범위 지정)로 정의하고, 2^3=8개
조합을 3페르소나 × 2모델로 실행했다 (2026-09-14, `scripts/run_vpa_ablation.py`).

## 실험 설계

- **role/avatar/few_shot은 Portrait 조건과 완전히 동일**, B/R/S 텍스트만 on/off. 8개 조합
  중 "없음"은 곧 Portrait 조건 그 자체다.
- 기존 `portrait_vpa`(Table 1)에 있던 "이 사진 본인 맞죠?" few-shot 확인 대화는 **일부러
  넣지 않았다** — B/R/S 텍스트 효과와 few-shot 데모 효과가 섞이면 어느 쪽 때문인지
  구분할 수 없기 때문. 그래서 이 표의 "B+R+S" 행은 Table 1의 Portrait+VPA와 근사하지만
  완전히 같은 조건은 아니다 (few-shot 차이).
- 붕괴율: `breaking.yaml` 12문항×5회=60턴/조합/모델, `self_negation` judge.
- 시각적 일치율: `visual_consistency.yaml` 5문항×5회=25턴/조합/모델, `visual_consistency`
  vision judge (100−불일치율).
- `config/personas/{persona}_vpa_components.yaml`(신규 3개) + `src/persona.py`의
  `PersonaComponents` 확장(`avatar_path`/`few_shot_always_on` 지원)으로 구현.

## 결과 — 페르소나 매크로 평균 ± 표본표준편차 (n=3)

| 조합 | gpt-4o-mini 붕괴율(↓) | gpt-4o-mini 일치율(↑) | qwen3-vl-4b 붕괴율(↓) | qwen3-vl-4b 일치율(↑) |
|---|---|---|---|---|
| 없음 (=Portrait) | 96.11 ± 5.36 | 90.67 ± 12.86 | 66.11 ± 10.05 | 72.00 ± 21.17 |
| B | 87.78 ± 5.09 | 89.33 ± 12.22 | 60.00 ± 7.64 | 73.33 ± 22.03 |
| R | **75.56 ± 2.55** | 90.67 ± 8.33 | 70.00 ± 7.64 | 72.00 ± 18.33 |
| S | 95.00 ± 3.33 | 86.67 ± 12.22 | 65.56 ± 3.47 | 72.00 ± 17.44 |
| B+R | 81.11 ± 1.92 | 92.00 ± 6.93 | **60.00 ± 5.77** | 69.33 ± 10.07 |
| B+S | 88.89 ± 3.47 | 89.33 ± 12.22 | 66.11 ± 4.19 | 74.67 ± 12.86 |
| R+S | 81.67 ± 3.33 | 85.33 ± 10.07 | 73.89 ± 3.47 | 72.00 ± 12.00 |
| B+R+S | 81.11 ± 0.96 | 89.33 ± 18.48 | 67.78 ± 4.19 | 70.67 ± 11.55 |

(n=3이라 std는 참고용 산포 지표. 페르소나별 세부치는 `python scripts/aggregate_vpa_ablation.py` 출력 참고.)

## 논문 초안(가설) 대비 실측 결과 — 상당 부분 반박됨

초안은 "B/R/S가 상호보완적이며 B+R+S가 두 모델에서 가장 낮은 붕괴율과 높은 일치율을
함께 낸다"고 예측했지만, 실측 결과는 다음을 보여준다:

1. **"결합할수록 좋다"는 성립하지 않는다.** gpt-4o-mini는 **R 단독(75.56%)이 8개 조합
   중 붕괴율이 가장 낮다** — B나 S를 더하면(B+R 81.11, R+S 81.67, B+R+S 81.11) 오히려
   R 단독보다 나빠진다.
2. **모델마다 최적 컴포넌트가 다르다.** qwen3-vl-4b는 R이 오히려 해롭다(없음 66.11 →
   R 단독 70.00로 악화). 대신 B가 일관되게 도움이 된다(B 60.00, B+R 60.00 — 공동 최저).
3. **S가 일치율을 특별히 올린다는 근거가 약하다.** S를 넣은 조건의 일치율(gpt 86.67,
   qwen 72.00)이 baseline(90.67, 72.00)보다 높지 않고, std 범위 안에서 사실상
   구분되지 않는다.
4. **8개 조합 전부 Table 1의 Text-only(gpt 72.22%, qwen 70.00%)보다 붕괴율이 나쁘다.**
   B/R/S를 어떻게 조합해도 아바타 이미지 자체가 만드는 붕괴율 증가분을 상쇄하지 못한다.

**결론**: "구성요소 결합 = 상호보완 효과"라는 원래 서술은 데이터로 뒷받침되지 않는다.
대신 "모델마다 서로 다른 단일 컴포넌트가 최선이고, 컴포넌트를 더 쌓는다고 항상 좋아지지
않는다"는 정반대에 가까운 그림이 나왔다 — 논문 본문(3.x절 VPA 구성요소 분석)의 가설
서술은 이 결과에 맞춰 다시 써야 한다.

## 재현 방법

```bash
python scripts/run_vpa_ablation.py           # 3페르소나 x 8조합 x 2모델, gpt/qwen 병렬 실행
python scripts/aggregate_vpa_ablation.py     # 매크로 평균 ± std 집계, 페르소나별 세부치 포함
```

결과 파일: `results/vpa_ablation/<persona>/<combo>/<model>/{breaking,visual}.jsonl`
(combo: `none`/`b`/`r`/`s`/`br`/`bs`/`rs`/`brs`).
