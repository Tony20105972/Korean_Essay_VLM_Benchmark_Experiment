# NonsulFit Agent Guide

## Mission
NonsulFit은 학생의 서면 논술 답안을 처리하는 AI 시스템이다. 목적과 범위는 [Vision](docs/product/vision.md)이 소유한다.

## Start Here
모든 Coding Agent의 유일한 시작점은 이 파일이다. 다음으로 [docs/index.md](docs/index.md)를 읽는다.
Canonical project knowledge는 docs/에 있으며 대화 이력을 대신한다.

## Critical Invariants
아래는 탐색용 요약이며 상세 규칙은 링크의 owner를 따른다.

| Responsibility | Canonical source |
|---|---|
| 원문 보존, 교정 금지, Unreadable ≠ Guess | [Perception behavior](docs/ai/perception/verbatim-contract.md) |
| Domain/Provider 경계, 불확실성 인계, 원본 보존 | [Architecture rules](docs/architecture/boundaries.md) |
| AI 변경의 평가와 채택 | [AI evaluation](docs/ai/evaluation/metrics.md) |
| Golden/holdout 격리와 무결성 | [Dataset integrity](docs/ai/datasets/dataset-policy.md) |

## Context Loading Policy
Any Task: 이 파일 → [Index](docs/index.md) → 아래 작업별 문서(왼쪽부터) → 관련 코드 → 관련 테스트.
여러 유형이면 필요한 경로를 합치고 이미 읽은 문서는 반복하지 않는다. 이유 없이 전체 저장소를 탐색하지 않는다.

| Task | Read in order |
|---|---|
| Perception | [Boundaries](docs/architecture/boundaries.md) → [Verbatim](docs/ai/perception/verbatim-contract.md) → [Metrics](docs/ai/evaluation/metrics.md) |
| Dataset | [Dataset policy](docs/ai/datasets/dataset-policy.md) → [Metrics](docs/ai/evaluation/metrics.md) |
| AI 동작 변경 | [Verbatim](docs/ai/perception/verbatim-contract.md) → [Metrics](docs/ai/evaluation/metrics.md) → [Done](docs/quality/definition-of-done.md) |
| Architecture 변경 | [System map](ARCHITECTURE.md) → [Boundaries](docs/architecture/boundaries.md) |

기타 작업 경로는 [Index](docs/index.md)의 Context Loading by Task에서 찾는다.

## Task Lifecycle
Read → Plan → Implement → Verify → Done.
구현 전 관련 문서·코드·테스트를 확인하고, 검증 후 acceptance criteria와 diff를 검토한다.
충돌은 기록하고 canonical owner에 맞춰 계획을 수정한다. 미해결 충돌을 임의로 덮지 않는다.

## Planning Rules
복잡 작업은 [ExecPlan 규칙과 template](docs/exec-plans/README.md)을 따라
[active/](docs/exec-plans/active/)에 계획을 작성한 후 시작한다.

## Commands
```bash
./scripts/dev
./scripts/test
./scripts/lint
./scripts/typecheck
./scripts/verify
./scripts/agent/doctor
```
새 checkout에서는 doctor를 먼저 실행한다. 각 명령의 STUB 표시는 미구현 검증을 뜻한다.

## Definition of Done
완료 전 ./scripts/verify를 실행하고 [완료 기준](docs/quality/definition-of-done.md)과 작업 계획의 acceptance criteria를 확인한다.
Engineering 규약은 [Conventions](docs/engineering/conventions.md), Skill/Workflow 승격은 [.agent 정책](.agent/README.md)을 따른다.
