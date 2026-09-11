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
| ARCH001–ARCH009 유효 | ID 존재뿐 아니라 규칙 의미와 각 상세 owner의 일치를 확인 |
| Dataset roles / final holdout explicit | [Dataset Policy](../ai/datasets/dataset-policy.md)의 matrix, Golden training 금지, selection tuning 분리, writer/duplicate 규칙 확인 |
| P0 metrics reproducible | [Metrics](../ai/evaluation/metrics.md)의 단위·입력·계산·집계·edge cases를 독립적으로 구현할 수 있고 정렬 동점/빈 GT/실패/annotation 미판정 처리까지 확인 |
| Normalization does not undermine Verbatim | 평가용 복사본 한정, semantic normalization 금지, versioned transform을 확인 |
| Provenance / human review 명확 | source/derived/sample/run/raw/parsed/evaluation linkage 및 transcription correction/decision override 분리 확인 |
| Canonical owners unique | [Index](../index.md)의 responsibility-to-file mapping과 각 문서 Owner가 일치하며 competing detailed source가 없음 |
| Canonical links valid and discoverable | README → index → 모든 필수 owner 링크가 실제 파일로 해석되며 stale path/중복 계약 파일이 없음 |
| No material contradictions | 모든 Canonical 문서를 다시 읽고 용어·허용/금지·handoff·평가 규칙의 상충 여부 기록 |
| Shareable state explicit | git diff/status를 확인하고 평가한 working tree 또는 commit revision을 명시. 미커밋이면 Ready to commit과 공유 한계를 보고 |
| No premature implementation | Gate 0에서 제외한 제품 코드·도구 플랫폼이 추가되지 않았음을 파일 목록으로 확인 |

## Safe Failure exit criteria

다음은 검증 항목이며 체크 표시 자체는 충족 증거가 아니다.

- [ ] Unreadable ≠ Guess 원칙이 [Vision](../product/vision.md)과 [Verbatim Contract](../ai/perception/verbatim-contract.md)에 명시되어 있다.
- [ ] Capture Quality와 Recognition Difficulty가 [Architecture](../architecture/boundaries.md)에서 구분된다.
- [ ] Uncertainty / unreadable을 first-class perception outcome으로 표현하는 계약이 있다 (ARCH008).
- [ ] 불확실·충돌·판독 불가 결과를 confirmed evidence로 자동 전달하는 것이 금지된다 (ARCH009).
- [ ] Safe Failure가 [Evaluation](../ai/evaluation/metrics.md)의 품질 목표이며, 지표 개념과 후속 계산 유보 범위가 명확하다.
- [ ] Evaluation policy가 difficult handwriting slice를 전체 평균과 별도 평가 대상으로 정의한다.

## Verification procedure

1. README와 index에서 시작해 모든 Canonical 문서를 읽고 기준별 PASS/PARTIAL/MISSING/CONFLICT와 근거를 기록한다.
2. 로컬 Markdown 링크를 파일 기준으로 해석하여 유효성을 확인하고 옛 Canonical 경로 및 중복 파일을 검색한다.
3. 교차 문서 검토로 product/domain/provider/dataset/metric 용어와 금지 규칙을 대조한다.
4. P0 계산 계약을 작은 예시로 확인한다: exact match, 학생 오류의 자동교정, whitespace/Unicode 차이, empty GT, terminal failure, annotation 미판정, percentile n=1.
5. 선명하지만 판독 불가인 글씨, uncertain 후보의 Evidence 인계, schema-valid unreadable 반환, text-GT 미확정 사례를 대조한다. 추측/확정 승격 금지와 safety 평가 유지가 동시에 성립해야 한다.
6. git diff --check, diff/status와 최종 파일 목록을 검토한다. 기능 구현이나 benchmark 실행 성공을 Gate 0 증거로 요구하지 않는다.
7. 아래 comprehension 질문과 점수를 audit 보고서에 기록한다. 실패 항목이 남으면 자기 체크로 덮지 않는다.

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
| 사진이 선명하면 전사를 확정해도 되는가? | Architecture의 Capture quality / recognition difficulty 분리 |
| 못 읽은 내용을 문맥으로 채우거나 Evidence가 확정해도 되는가? | Verbatim Safe Failure + ARCH008/009 |
| CER가 좋으면 unreadable detection과 hard slice는 생략 가능한가? | Metrics Safe Failure / Difficulty slice evaluation |
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

## Gate 1 exit criteria — Seed Harness

Gate 0 기준과 계약은 유지한다. Gate 1은 아래 Harness 기준으로 별도 검증한다.

| Criterion | Evidence / verification |
|---|---|
| 단일 Agent 시작점 | AGENTS.md → docs/index.md → task-specific docs 경로가 명확 |
| Router와 canonical ownership | AGENTS.md가 상세 계약을 복제하지 않고 Perception의 boundaries/verbatim/metrics 3개 문서를 연결 |
| Context router | Index에서 dataset, AI behavior, architecture, complex planning 경로 발견 가능 |
| 시스템 지도 | ARCHITECTURE.md의 4개 Domain과 Gateway 경계가 Architecture owner와 일치 |
| Claude 일관성 | CLAUDE.md가 AGENTS.md를 먼저 읽도록 하고 독립 행동 계약을 만들지 않음 |
| 계획 체계 | ExecPlan README/template, active/completed 구조 및 검증 가능한 acceptance criteria 존재 |
| 최소 운영 정책 | stack-agnostic conventions와 .agent 정책 존재; Gate 1 skills/workflows는 비어 있음 |
| 실행 interface | dev/test/lint/typecheck/verify/agent/doctor 모두 파일이며 실행 가능 |
| 구조 검증 | doctor가 Gate 0/1 필수 문서와 6개 script를 검사하고 누락/권한 오류 시 nonzero 반환 |
| 통합 검증 | verify가 doctor → lint → typecheck → test 순서로 실행하며 실패를 전파 |
| 범위 준수 | 제품/Provider/Gateway/dataset/benchmark/CI/MCP 구현 없음 |
| 공유 상태 | diff/link/shell 검증 결과와 working tree 또는 commit 상태를 완료 계획에 기록 |

STUB 명령의 성공은 interface 검증이며 제품 lint/typecheck/test 성공이 아니다.
완료 검토에서는 Perception 문서 3개 발견, Verbatim 10개 규칙 비복제, Claude 순서 일치,
ARCH 규칙 전체 비복제, 계획 위치 active/, 테스트 명령 ./scripts/test, doctor 전체 필수 파일 검증을 확인한다.
Gate 1 PASS 후 Gate 2 — Evaluation Foundation에서 dataset schema, smoke manifest,
CanonicalPerceptionResult, metrics engine, benchmark interface를 다룬다. Gate 1에서는 구현하지 않는다.

## Gate 2 Execution 1 exit criteria — Contract Foundation

- [Canonical contracts](../contracts/canonical-contracts.md)의 다섯 public schema가 구현되고
  strict type, required fields, unknown/optional metadata 및 Unicode round-trip을 검증한다.
- Perception의 source locations, uncertainty/unreadable, reading order, provenance를 표현하고
  모순된 상태/참조를 거부하는 deterministic tests가 있다.
- Manifest pins 및 materialized samples, benchmark/result context 연결을 검증한다.
- Stack 선택과 실제 검증 도구를 conventions에 명시한다. `./scripts/verify`에서
  lint/typecheck/test가 실제 실행되며 남은 STUB을 성공 증거로 사용하지 않는다.
- VLM/Provider 연결, dataset 다운로드, 실제 smoke freeze, metric engine은 범위 밖이다.
- ExecPlan acceptance criteria, diff/working tree, 한계를 검토한다. Execution 1 PASS는
  Gate 2 전체 PASS 또는 실제 dataset/HF integration 검증 완료를 뜻하지 않는다.

## Gate 2 Execution 2 exit criteria — Hugging Face Dataset Adapter

- HF adapter manifest가 explicit pinned commit, split 및 image/transcription/sample-ID/writer column mapping을 strict하게 검증한다.
- HF SDK는 provider adapter에 국한되고 output은 canonical sample이다. Benchmark/Evaluation 계층에 HF SDK/row schema 의존이 없다.
- `HF_TOKEN`만 private/gated access에 사용하고 config, example, output, error에 secret을 기록하지 않는다.
- revision resolution, mapping columns, image readability, verbatim text compatibility, stable/duplicate ID와 selection 검증이 fixture-only deterministic tests에 있다.
- `./scripts/dataset inspect|fetch|validate` interface와 cache/Git-ignore 정책이 문서화된다. 실제 remote smoke dataset은 test fixture가 아닌 별도 manual operation이다.

## Gate 2 Execution 3 exit criteria — smoke-v1 freeze

- `inspect`가 pinned 40-char SHA, split별 row 수, 실제 column/feature를 image payload 전송 없이 보고한다.
- ID column이 없는 source는 `content-digest` identity를 쓰고 canonical sample이 이를 그대로 기록한다.
  Row 위치는 검증되는 fetch hint일 뿐이며 재계산한 ID가 다르면 실패한다.
- `smoke-v1`이 canonical `DatasetManifest`(tier `G0`, role `benchmark`, `golden: false`)로 동결되고
  `./scripts/dataset validate smoke-v1`이 전체 split 다운로드 없이 pin과 일치함을 확인한다.
- 선택은 seed 없이 결정론적이며 length band floor와 label 비례 배분을 문서화한 규칙대로 적용한다.
- GT 검증이 empty/duplicate/encoding/Unicode 이상/mixed-script를 보고하고 GT를 수정하지 않는다.
- Writer identity, handwriting difficulty, near-duplicate 검수, permission review의 부재를 명시한다.
  제공되지 않는 다양성 축을 주장하지 않는다.
- fixture-only deterministic tests가 배분/선택/GT 검증/identity/pin 검증을 다루고 `./scripts/verify`가 통과한다.
- VLM 추론, OpenRouter, metric 계산, verifier, fine-tuning, Golden 선언은 범위 밖이다.
