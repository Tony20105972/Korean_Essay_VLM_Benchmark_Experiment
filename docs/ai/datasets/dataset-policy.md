# NonsulFit — Dataset Policy

> Canonical Source: 평가 Dataset 계층 및 데이터 무결성 규칙
> Owner: docs/ai/datasets/

---

## Dataset Tiers (Long-term Target)

### G0 — Smoke

빠른 pipeline / schema / API regression 탐지.

- 초기 목표: 100–200 samples
- 목적: 변경이 기본 기능을 깨뜨리지 않는지 빠르게 확인

### G1 — General Korean Golden

범용 한국어 손글씨 성능 평가.

- 초기 목표: 1,000–2,000 samples
- 목적: 전반적인 한국어 handwriting recognition 품질 측정

### G2 — Challenge / Anti-Correction

취약점 중심 평가.

- 희귀어, mixed-script, 비정상 표현
- 장문, 환각, 누락
- 자동 교정, 문맥 추측

모델이 "똑똑하게" 고치려 할 때 실패하는 케이스를 집중 평가한다.

### G3 — NonsulFit Domain Golden

실제 학생 논술 답안을 이용한 Production Validity 평가.

- 실 서비스 데이터 기반
- 가능한 경우 writer-level leakage 방지 (DATA007)

---

## Dataset Invariants

| ID | Rule |
|----|------|
| DATA001 | Golden sample은 training / fine-tuning에 사용하지 않는다 |
| DATA002 | Golden manifest 변경 시 기존 version을 덮어쓰지 않는다 |
| DATA003 | Benchmark run은 dataset / source revision을 기록한다 |
| DATA004 | Evaluation run은 sample-level output을 보존한다 |
| DATA005 | Golden Ground Truth를 inference prompt에 노출하지 않는다 |
| DATA006 | 튜닝에 사용한 dataset을 final holdout으로 사용하지 않는다 |
| DATA007 | Domain Golden은 가능한 경우 writer-level leakage를 방지한다 |

---

## Reference

평가 지표 정의는 `docs/ai/evaluation/metrics.md`를 참조한다.

Architecture Rule ARCH005 (Golden Holdout 격리)는 `docs/architecture/boundaries.md`를 참조한다.