# NonsulFit — Definition of Done

> Canonical Source: Gate completion criteria and verification procedure
> Owner: docs/quality/definition-of-done.md

## Principle

Gate 0은 실행 코드가 아니라 Context 품질로 완료를 판단한다. 파일 존재나 이 문서의 자체 체크 표시만으로 PASS하지 않는다.
검증자는 현재 파일을 직접 읽고 아래 기준별 evidence와 결함을 기록한다. 기준 문서와 특정 시점의 audit 결과는 구분한다.

## Gate 0 exit criteria

| Criterion | Canonical evidence / verification |
|---|---|
| Product purpose / users / initial non-goals 명확 | [Vision](../product/vision.md)을 읽고 대상 사용자, 목적, 현재 Domain을 설명할 수 있음 |
| Domain handoff 명확 | [Architecture](../architecture/boundaries.md)의 4개 Domain 모두 Question/Owns/Receives/Produces/Must Preserve/Must Not Do/Allowed Dependencies/Forbidden Dependencies 존재 및 의미 검증 |
| Perception boundary / no auto-correction 명확 | [Verbatim](../ai/perception/verbatim-contract.md)의 예시·reading order·uncertainty와 Architecture의 책임 제한이 일치 |
| Provider boundary 명확 | SDK import 위치, neutral Gateway 계약, Domain 금지 의존을 Architecture에서 확인 |
| ARCH001–ARCH007 유효 | ID 존재뿐 아니라 규칙 의미와 각 상세 owner의 일치를 확인 |
| Dataset roles / final holdout explicit | [Dataset Policy](../ai/datasets/dataset-policy.md)의 matrix, Golden training 금지, selection tuning 분리, writer/duplicate 규칙 확인 |
| P0 metrics reproducible | [Metrics](../ai/evaluation/metrics.md)의 단위·입력·계산·집계·edge cases를 독립적으로 구현할 수 있고 정렬 동점/빈 GT/실패/annotation 미판정 처리까지 확인 |
| Normalization does not undermine Verbatim | 평가용 복사본 한정, semantic normalization 금지, versioned transform을 확인 |
| Provenance / human review 명확 | source/derived/sample/run/raw/parsed/evaluation linkage 및 transcription correction/decision override 분리 확인 |
| Canonical owners unique | [Index](../index.md)의 responsibility-to-file mapping과 각 문서 Owner가 일치하며 competing detailed source가 없음 |
| Canonical links valid and discoverable | README → index → 모든 필수 owner 링크가 실제 파일로 해석되며 stale path/중복 계약 파일이 없음 |
| No material contradictions | 모든 Canonical 문서를 다시 읽고 용어·허용/금지·handoff·평가 규칙의 상충 여부 기록 |
| Shareable state explicit | git diff/status를 확인하고 평가한 working tree 또는 commit revision을 명시. 미커밋이면 Ready to commit과 공유 한계를 보고 |
| No premature implementation | Gate 0에서 제외한 제품 코드·도구 플랫폼이 추가되지 않았음을 파일 목록으로 확인 |

## Verification procedure

1. README와 index에서 시작해 모든 Canonical 문서를 읽고 기준별 PASS/PARTIAL/MISSING/CONFLICT와 근거를 기록한다.
2. 로컬 Markdown 링크를 파일 기준으로 해석하여 유효성을 확인하고 옛 Canonical 경로 및 중복 파일을 검색한다.
3. 교차 문서 검토로 product/domain/provider/dataset/metric 용어와 금지 규칙을 대조한다.
4. P0 계산 계약을 작은 예시로 확인한다: exact match, 학생 오류의 자동교정, whitespace/Unicode 차이, empty GT, terminal failure, annotation 미판정, percentile n=1.
5. git diff --check, diff/status와 최종 파일 목록을 검토한다. 기능 구현이나 benchmark 실행 성공을 Gate 0 증거로 요구하지 않는다.
6. 아래 comprehension 질문과 점수를 audit 보고서에 기록한다. 실패 항목이 남으면 자기 체크로 덮지 않는다.

## Agent comprehension questions

| Question | Expected answer source |
|---|---|
| NonsulFit은 누구를 위해 무엇을 만드는가? | Vision의 Users/Core Purpose |
| 현재 핵심 기술 Domain은 무엇인가? | Vision의 Current focus |
| Perception은 무엇을 인계하고 무엇을 금지하는가? | Architecture handoff + Verbatim |
| 학생의 `문재점`을 `문제점`으로 바꿔도 되는가? | Verbatim Example |
| Provider SDK와 response type은 어디까지 허용되는가? | Architecture Gateway + ARCH002/003 |
| 성능 향상은 어떻게 입증하는가? | Metrics baseline comparison과 P0 calculations |
| Golden weights 학습과 Golden development selection의 차이는? | Dataset Terms/Usage matrix |
| Final holdout을 보고 prompt를 반복 수정해도 되는가? | Dataset DATA006 |
| CER 개선과 Auto-Correction 악화가 함께 오면? | Metrics acceptance policy |
| 전처리 결과로 원본을 교체하거나 Decision override를 전사 GT로 써도 되는가? | Architecture ARCH006/Human review |
| 다음 Gate는 무엇인가? | 아래 Gate 1 scope |

## Scoring and blockers

| Area | Maximum |
|---|---:|
| Product Purpose / Vision | 15 |
| Domain Boundary | 20 |
| Perception / Verbatim Contract | 15 |
| Architecture Invariants | 15 |
| Dataset / Golden Policy | 10 |
| AI Evaluation Policy | 10 |
| Definition of Done | 5 |
| Source of Truth / Docs Routing | 5 |
| Consistency / No Contradiction | 5 |

90+만 PASS 후보이며 모든 exit criterion을 충족해야 한다. 80–89 CONDITIONAL, 60–79 PARTIAL, 0–59 FAIL이다.
점수와 무관하게 Perception Boundary, Verbatim/No Auto-Correction, Golden Final Holdout Separation,
Provider Boundary, Architecture Invariants, Domain Handoff Contract, Reproducible P0 Metric Definitions 중 하나라도 빠지면 PASS 금지다.
Material contradiction과 미해결 P0도 종료를 차단한다. 숫자 threshold 미확정은 Metrics의 명시적 후속 정책에 따르며 임의 채택을 허용하지 않는다.
Working tree 기준 PASS는 가능하지만 commit되지 않았다면 committed revision도 PASS라고 주장하지 않는다.

## Gate 0 Exit → Gate 1

Gate 0 통과 후 Gate 1 — Seed Harness에서 다음을 구축한다:

- AGENTS.md / CLAUDE.md / ARCHITECTURE.md: 이 Canonical owner들로 routing하며 상세 정책을 복제하지 않음
- Deterministic scripts
- ExecPlan structure
- Basic repository routing

후속 schema/parser 구현은 여기서 고정한 책임과 계산 계약을 따라야 한다.
Product UI/API, Gateway/Provider 구현, dataset loader/benchmark runner, CI/linter, MCP/skills/multi-agent,
fine-tuning/verifier/risk engine/writer adaptation은 이번 Gate 0 remediation의 산출물이 아니다.
