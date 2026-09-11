# NonsulFit — Documentation Index

이 문서는 Context Router다. 각 책임의 유일한 Canonical owner는 아래 파일이다. 다른 문서는 요약과 링크만 제공하며 규칙 변경은 owner에서 시작한다.

| Area | Canonical document | 이 문서는 어떤 질문에 답하는가? |
|---|---|---|
| Product | [vision.md](product/vision.md) | 누구를 위해 무엇을 만들며, 현재 초점·Human Review 목적·Non-goal은 무엇인가? |
| Architecture | [boundaries.md](architecture/boundaries.md) | Domain/Provider/provenance 경계는 무엇이며, capture quality와 handwriting difficulty는 어떻게 다르고 불확실한 결과는 downstream으로 어떻게 전달되는가? |
| Perception | [verbatim-contract.md](ai/perception/verbatim-contract.md) | 무엇을 그대로 전사하며, 못 읽었을 때 추측하지 않고 uncertainty/unreadable을 어떻게 드러내는가? |
| AI Evaluation | [metrics.md](ai/evaluation/metrics.md) | P0 metric을 어떻게 계산하며 Safe Failure와 difficult handwriting을 어떻게 평가하고 모델/Prompt 변경을 판단하는가? |
| Dataset | [dataset-policy.md](ai/datasets/dataset-policy.md) | Golden·tuning·holdout 사용 권한과 writer/duplicate leakage 방지는 무엇인가? |
| Canonical Schemas | [canonical-contracts.md](contracts/canonical-contracts.md) | Dataset/manifest/perception/benchmark의 구현 필드, version, strict validation과 통합 경계는 무엇인가? |
| Hugging Face Adapter | [huggingface-adapter.md](datasets/huggingface-adapter.md) | HF pinned revision과 서로 다른 row columns를 canonical dataset sample로 어떻게 변환하는가? |
| Smoke Dataset | [smoke-v1.md](datasets/smoke-v1.md) | smoke-v1의 source, sample identity, 선택 규칙과 한계는 무엇인가? |
| Quality | [definition-of-done.md](quality/definition-of-done.md) | Gate별 완료를 어떻게 검증하는가? |

README는 프로젝트 진입점이며 정책 owner가 아니다. Architecture의 invariant 요약은 행동·데이터·metric owner를 대체하지 않는다.
상세 규칙이 서로 다르면 임의로 선택하지 말고 material contradiction으로 기록하여 Gate 종료 전에 해소한다.

## Gate 1 Canonical Ownership

| Responsibility | Owner |
|---|---|
| Agent routing / entrypoint | [AGENTS.md](../AGENTS.md) |
| Claude configuration | [CLAUDE.md](../CLAUDE.md) |
| System map | [ARCHITECTURE.md](../ARCHITECTURE.md) |
| Context routing | 이 문서 |
| Engineering rules | [Conventions](engineering/conventions.md) |
| Execution plans | [ExecPlans](exec-plans/README.md) |
| Agent skills / workflows | [.agent](../.agent/README.md) |
| Deterministic commands | [scripts/](../scripts/) |

## Context Loading by Task
Any Task: [AGENTS.md](../AGENTS.md) → 이 문서 → 작업별 문서 → 관련 코드와 테스트.
아래 순서를 따르고 여러 유형이면 필요한 문서의 합집합을 읽는다.

| Task | Read in order |
|---|---|
| Product | [Vision](product/vision.md) |
| Perception | [Boundaries](architecture/boundaries.md) → [Verbatim](ai/perception/verbatim-contract.md) → [Metrics](ai/evaluation/metrics.md) |
| Datasets | [Dataset policy](ai/datasets/dataset-policy.md) → [Metrics](ai/evaluation/metrics.md) → [Hugging Face adapter](datasets/huggingface-adapter.md) → [smoke-v1](datasets/smoke-v1.md) |
| AI behavior change | [Verbatim](ai/perception/verbatim-contract.md) → [Metrics](ai/evaluation/metrics.md) → [Done](quality/definition-of-done.md) |
| Architecture change | [System map](../ARCHITECTURE.md) → [Boundaries](architecture/boundaries.md) |
| Complex planning | [ExecPlan rules/template](exec-plans/README.md) |
| Harness / engineering | [Conventions](engineering/conventions.md) → [.agent policy](../.agent/README.md) → [ExecPlans](exec-plans/README.md) |
| Contract implementation / HF adapter | [Dataset](ai/datasets/dataset-policy.md) → [Boundaries](architecture/boundaries.md) → [Verbatim](ai/perception/verbatim-contract.md) → [Metrics](ai/evaluation/metrics.md) → [Canonical contracts](contracts/canonical-contracts.md) → [Conventions](engineering/conventions.md) |
| Completion review | [Definition of Done](quality/definition-of-done.md) |
