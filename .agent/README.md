# Agent Skills & Workflows

반복 실패 패턴에서 승격된 Agent Skill과 Workflow를 저장한다.
Agent 시작점은 [AGENTS.md](../AGENTS.md)다.

## Policy
- SKILL001: 동일한 실패가 3회 이상 반복된 후에만 Skill을 생성한다.
- SKILL002: Skill은 단일 책임을 갖는다.
- SKILL003: Workflow는 2개 이상의 Skill을 조합할 때만 생성한다.
- SKILL004: Gate 1에서는 Skill과 Workflow를 대량 생성하지 않는다.

## Current
- skills/: empty
- workflows/: empty

Git은 빈 디렉터리를 저장하지 않는다. placeholder를 추가하지 않으며 새 checkout에서
./scripts/agent/doctor가 누락된 skills/, workflows/ 및 ExecPlan 디렉터리를 생성한다.
