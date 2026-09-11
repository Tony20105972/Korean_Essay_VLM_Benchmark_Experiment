# NonsulFit System Map

Agent는 [AGENTS.md](AGENTS.md)에서 시작한다. 이 지도는 논리적 구조이며 구현 상태를 뜻하지 않는다.

```text
Student Answer Image
  ↓
Perception — 학생이 실제로 무엇을 썼는가? (verbatim, no correction)
  ↓ canonical transcription + source/status references
Evidence — 평가 근거가 답안 어디에 있는가? (locate, don't judge)
  ↓ extracted evidence
Decision — 루브릭 기준으로 어떻게 판단하는가? (provider-independent)
  ↓ finalized judgment
Generation — 확정된 판단을 어떻게 설명하는가? (decision read-only)
```

## Dependency overview
공개 계약에 대한 의존이며 upstream 구현 호출 권한이 아니다.

```text
Perception → Canonical Schemas + Source Artifact Contract
Evidence → Perception Public Contract + Rubric Criteria
Decision → Evidence Public Contract + Rubric Domain
Generation → Finalized Decision Public Contract + Evidence References

All domains → Canonical Schemas + Model Gateway Interface
Provider Adapter → Model Gateway Interface (implements) + Provider SDK
Runtime: Product Domain → Model Gateway → injected Provider Adapter
```

전체 허용/금지 의존과 불확실성 handoff 및 ARCH 규칙은
[Domain boundaries](docs/architecture/boundaries.md)가 소유한다.
전사 행동은 [Perception contract](docs/ai/perception/verbatim-contract.md)를 따른다.
