# Claude Configuration

Read [AGENTS.md](AGENTS.md) first.

Canonical project knowledge lives in docs/.
Claude-specific configuration lives under .claude/ (필요할 때 생성).

When making changes:
1. AGENTS.md Context Loading Policy의 관련 문서를 읽는다.
2. 복잡 작업은 [ExecPlan](docs/exec-plans/README.md)에 따라 docs/exec-plans/active/에 계획을 작성한다.
3. 완료 판단 전 ./scripts/verify를 실행한다.
4. [Definition of Done](docs/quality/definition-of-done.md)을 확인한다.
