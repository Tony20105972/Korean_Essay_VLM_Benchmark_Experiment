# NonsulFit — Definition of Done

> Canonical Source: Gate별 완료 조건
> Owner: docs/quality/

---

## Principle

Gate 0의 완료는 코드 실행 여부가 아니라 **Context 품질**로 판단한다.

---

## Gate 0 Checklist

- [ ] NonsulFit의 Product Vision이 명시되어 있다 → `docs/product/vision.md`
- [ ] Perception / Evidence / Decision / Generation 책임이 분리되어 있다 → `docs/architecture/boundaries.md`
- [ ] Perception의 금지 책임이 명시되어 있다 → `docs/architecture/boundaries.md`
- [ ] Provider와 Product Domain의 경계가 정의되어 있다 → `docs/architecture/boundaries.md`
- [ ] ARCH001–ARCH007이 존재한다 → `docs/architecture/boundaries.md`
- [ ] Verbatim Contract가 존재한다 → `docs/ai/perception/verbatim-contract.md`
- [ ] Golden Dataset의 목적과 분리가 정의되어 있다 → `docs/ai/datasets/dataset-policy.md`
- [ ] 핵심 AI Evaluation Metrics가 정의되어 있다 → `docs/ai/evaluation/metrics.md`
- [ ] Initial Non-goals가 명확하다 → `docs/product/vision.md`
- [ ] Agent가 위 내용을 찾을 수 있도록 docs/index.md가 연결한다 → `docs/index.md`
- [ ] 서로 충돌하는 Canonical Source가 없다

---

## Gate 0 Verification Questions

| # | Question | Expected |
|---|----------|----------|
| Q1 | Perception이 맞춤법을 고쳐도 되는가? | **No** |
| Q2 | Decision layer가 OpenRouter response object를 직접 사용해도 되는가? | **No** (ARCH002) |
| Q3 | 학생 이미지 원본을 preprocessing 결과로 덮어써도 되는가? | **No** (ARCH006) |
| Q4 | Golden sample을 모델 튜닝에 사용할 수 있는가? | **No** (ARCH005, DATA001) |
| Q5 | CER가 개선되면 무조건 새로운 모델을 채택하는가? | **No** |
| Q6 | NonsulFit Perception의 목표가 자연스러운 한국어 생성인가? | **No** — 목표는 Visual / Verbatim Fidelity |

모든 질문에 명확히 답할 수 있어야 Gate 0을 통과한다.

---

## Gate 0 Exit → Gate 1

Gate 0 통과 후 Gate 1 (Seed Harness)에서 다음을 구축한다:

- AGENTS.md / CLAUDE.md / ARCHITECTURE.md
- Deterministic scripts
- ExecPlan structure
- Basic repository routing