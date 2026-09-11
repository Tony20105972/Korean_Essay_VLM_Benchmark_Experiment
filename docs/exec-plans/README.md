# ExecPlans

> Owner: docs/exec-plans/README.md

## Rules
- PLAN001: 복잡 작업(2개 이상 도메인 또는 3단계 이상)은 구현 전 ExecPlan을 작성한다. Architecture/AI 동작 변경이나 검증이 어려운 작업도 포함한다.
- PLAN002: Acceptance Criteria는 검증 가능해야 한다.
- PLAN003: 완료한 계획은 active/에서 completed/로 이동한다.
- PLAN004: 구현 중 발견한 변경사항을 계획에 기록한다.
- PLAN005: Gate 0 문서와 충돌하면 계획을 수정한다. Gate 0 문서가 우선한다.

진행 중 계획은 [active/](active/), 완료 기록은 [completed/](completed/)에 둔다.
빈 디렉터리는 ./scripts/agent/doctor가 복원한다. BLOCKED/ABANDONED 상태는 이유를 기록하며 완료로 표시하지 않는다.

## Template
```markdown
# [Plan Title]

> Status: PLANNING | IN_PROGRESS | BLOCKED | COMPLETED | ABANDONED
> Created: YYYY-MM-DD
> Gate: N

## Goal
한 문장.

## Why
이 작업이 필요한 이유.

## Relevant Context
읽어야 할 문서 목록.

## Current State
시작 시점의 상태.

## Acceptance Criteria
- [ ] 검증 가능한 조건.

## Non-Goals
이 Plan에서 하지 않는 것.

## Implementation Steps
1. 작업 단계.

## Verification
검증 방법과 scripts.

## Risks
예상 위험과 대응.

## Progress
작업 중 기록.

## Unexpected Findings
예상치 못한 발견과 충돌 및 해소 내용.

## Completion Notes
완료 후 결과, 검증 증거, 한계와 공유 상태.
```
