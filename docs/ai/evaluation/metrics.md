# NonsulFit — AI Evaluation Metrics

> Canonical Source: AI 품질 측정 지표 정의
> Owner: docs/ai/evaluation/

---

## Evaluation Principle

하나의 평균 CER만으로 모델 또는 Prompt를 선택하지 않는다.

예: CER는 개선되었지만 Auto-Correction Rate가 크게 악화되었다면 candidate를 reject할 수 있다.

모델 선택은 다차원 지표의 종합 판단이다.

---

## P0 Metrics (Initial)

| Metric | Description |
|--------|-------------|
| Strict CER | 원본 대비 문자 단위 오류율 (교정 없이 strict 비교) |
| Normalized CER | 정규화된 문자 오류율 |
| WER | 단어 단위 오류율 |
| Omission Rate | 원본에 있으나 전사에서 누락된 비율 |
| Hallucination Rate | 원본에 없으나 전사에서 생성된 비율 |
| Auto-Correction Rate | Perception이 원본을 임의로 교정한 비율 |
| Structured Output Failure Rate | 요구된 출력 구조를 만족하지 못한 비율 |
| Cost / Page | 페이지당 inference 비용 |
| Latency P50 | 응답 시간 중앙값 |
| Latency P95 | 응답 시간 95th percentile |

---

## P1 Metrics (Future)

| Metric | Description |
|--------|-------------|
| Critical Semantic Error Rate | 의미를 왜곡하는 치명적 오류의 비율 |
| Uncertainty Error Recall | 실제 불확실 영역 중 모델이 탐지한 비율 |
| Human Correction Time | 사람이 AI 결과를 수정하는 데 소요되는 시간 |
| Auto Acceptance Rate | 수정 없이 승인된 AI 결과 비율 |

---

## Decision Rule

모델 또는 Prompt 변경 시 P0 지표 전체를 기준으로 판단한다.

단일 지표 개선이 다른 핵심 지표의 악화를 동반할 경우, 해당 변경은 reject 대상이다.

Dataset 정책과 Golden sample 관리는 `docs/ai/datasets/dataset-policy.md`를 참조한다.