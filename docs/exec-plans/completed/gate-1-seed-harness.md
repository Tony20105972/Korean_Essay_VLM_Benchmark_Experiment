# Gate 1 Seed Harness

> Status: COMPLETED
> Created: 2026-09-11
> Gate: 1

## Goal
Gate 0 지식을 Agent가 발견하고 실행할 수 있는 최소 Harness로 연결한다.

## Why
새 Agent가 대화 이력 없이 canonical context와 검증 명령을 찾도록 한다.

## Relevant Context
- [Index](../../index.md)
- [Vision](../../product/vision.md)
- [Boundaries](../../architecture/boundaries.md)
- [Verbatim](../../ai/perception/verbatim-contract.md)
- [Metrics](../../ai/evaluation/metrics.md)
- [Dataset](../../ai/datasets/dataset-policy.md)
- [Done](../../quality/definition-of-done.md)

## Current State
Gate 0 PASS는 실행 요청의 전제다. 시작 working tree는 clean이며 문서만 존재한다.
AGENTS.md/CLAUDE.md에 행동 요약이 중복되고 ARCHITECTURE.md 및 scripts는 없다.
소스 코드, 테스트, stack 설정은 없다.

## Acceptance Criteria
- [x] Agent 진입점과 task routing, 시스템 지도, Claude 참조가 연결된다.
- [x] ExecPlan과 conventions, 빈 skill/workflow 디렉터리 정책이 존재한다.
- [x] 6개 script가 실행 가능하고 doctor가 Gate 0/1 필수 파일을 검증한다.
- [x] verify, shell syntax, 로컬 링크, doctor 실패 경로를 검증한다.
- [x] Completion Review Q1–Q7을 통과하며 제품 구현과 Gate 0 계약 변경이 없다.

## Non-Goals
제품 기능, Provider/Gateway, Dataset, benchmark, MCP, CI/CD, Skill/Workflow 구현.

## Implementation Steps
1. Router와 canonical ownership 연결을 정리한다.
2. ExecPlan/engineering/agent 정책 및 shell interface를 작성한다.
3. 성공·실패 경로와 링크/차이를 검토하고 계획을 completed로 이동한다.

## Verification
scripts/verify, scripts/dev, scripts/agent/doctor; bash -n; git diff --check.
임시 복사본에서 누락 파일/실행 권한 오류와 verify fail-fast를 확인한다.

## Risks
STUB 성공을 제품 검증으로 오인할 수 있으므로 출력과 보고서에 한계를 명시한다.

## Progress
- Gate 0 문서와 기존 Agent 파일, 파일 목록을 확인했다.

## Unexpected Findings
- 요청의 lowercase-only 파일명 규약과 필수 AGENTS.md/CLAUDE.md/ARCHITECTURE.md/README.md가 충돌한다. 명시된 필수 파일명은 예외로 보존한다.
- 요청 지도 예시의 Perception canonical schemas only는 Gate 0의 source contract/Gateway 허용을 생략한다. Gate 0을 우선하여 지도에 계약 및 Gateway 경계를 표시한다.
- 빈 디렉터리는 Git 추적이 불가능하다. placeholder 대신 doctor가 필요한 빈 디렉터리를 생성하여 fresh checkout에서도 복원한다.
- Gate 0의 schema/구조 확정 시점은 Gate 1/2로 열려 있다. 이번 명령의 범위에 따라 Gate 2로 유보한다.

## Completion Notes
Gate 1 PASS — 2026-09-11 working tree 기준. 미커밋이며 Ready to commit 상태다.

- scripts/verify와 scripts/dev exit 0. dev/test/lint/typecheck는 STUB이며 제품 검증을 수행하지 않는다.
- bash -n으로 6개 script 문법 검증, 로컬 Markdown 링크 104개 검증, git diff --check 통과.
- 임시 복사본에서 외부 cwd/공백 포함 경로 실행, 빈 디렉터리 복원 통과.
- Gate 0 및 Gate 1 문서 누락과 script 실행 권한 제거 시 doctor exit 1 확인.
- lint exit 7 주입 시 verify exit 7 및 후속 test/완료 출력 미실행 확인.
- skills/workflows는 비어 있다. 제품 구현과 Gate 0 행동/Architecture/metric/dataset 계약 변경은 없다.
- 완료 기준 owner에는 Gate 1 검증 기준을 추가했다. README의 진입점과 Gate 상태도 갱신했다.

### Completion Review
| Question | Result / evidence |
|---|---|
| Q1 Perception 문서 3개 이내 발견? | Yes — AGENTS.md task table의 boundaries, verbatim-contract, metrics |
| Q2 Verbatim 10개 규칙 복사? | No — 요약 및 owner 링크만 존재 |
| Q3 Claude의 독립 Context Loading 순서? | No — AGENTS.md first 및 해당 정책 참조 |
| Q4 ARCH001–ARCH007 전체 복사? | No — 시스템 지도와 경계 링크만 존재 |
| Q5 복잡 작업 계획 위치? | docs/exec-plans/active/ |
| Q6 테스트 명령? | ./scripts/test |
| Q7 Gate 0 + Gate 1 필수 파일 검증? | Yes — doctor 정상/누락/권한 실패 경로 검증 |

미해결 충돌 없음. Unexpected Findings에 기록한 차이는 명시적 필수 파일명과 Gate 0 우선 규칙으로 해소했다.
Gate 2 착수 준비가 되었으며 이번 작업에서 Gate 2 구현은 시작하지 않았다.
