# Gate 2 Execution 1 — Contract Foundation

> Status: COMPLETED
> Created: 2026-09-11
> Gate: 2

## Goal
Dataset 수집과 Perception 평가에 필요한 다섯 provider-neutral 계약을 구현한다.

## Why
HF adapter와 evaluation engine이 공유할 엄격한 데이터 경계를 먼저 고정한다.

## Relevant Context
AGENTS.md → docs/index.md; ARCHITECTURE.md; boundaries, verbatim-contract,
metrics, dataset-policy, definition-of-done, conventions 및 ExecPlan 규칙을 읽었다.

## Current State
Gate 1 완료 계획은 working tree PASS를 기록한다. 기존 Gate 1 변경은 미커밋이며 보존한다.
Stack은 미정이고 test/lint/typecheck는 STUB이다. doctor 구조 검증 통과.

## Acceptance Criteria
- [x] 다섯 계약 및 공통 참조가 strict validation과 version을 가진다.
- [x] 선택 metadata 없이 수용하며 unknown/null과 verbatim Unicode를 보존한다.
- [x] uncertainty/unreadable/reading order 및 provenance 연결을 검증한다.
- [x] manifest가 upstream revision, ID, image digest, GT/annotation revision을 고정한다.
- [x] benchmark 실행/샘플 결과가 policy versions, 실패 및 미측정 값을 표현한다.
- [x] deterministic 정상/실패 테스트와 실제 lint/typecheck/test가 verify에서 통과한다.
- [x] stack 결정, 계약 의미와 한계를 문서화하고 diff/완료 기준을 검토한다.

## Non-Goals
VLM/Provider/Gateway/HF adapter 구현, 데이터 다운로드, frozen smoke 실데이터,
평가 계산 엔진, Golden 구축, Verifier, fine-tuning, Human Review.

## Implementation Steps
1. Python/Pydantic stack과 schema version/참조/unknown 규칙 문서화.
2. 공통 및 다섯 계약과 semantic validators 구현.
3. deterministic tests와 검증 스크립트 연결.
4. verify 및 diff 검토 후 계획 completed 이동.

## Verification
./scripts/verify; git diff --check; schema JSON round-trip 및 부정 입력 테스트.

## Risks
Schema만으로 이미지 진실성, upstream 가용성, 누출 검사를 입증할 수 없다.
Unknown revision은 sample에 보존하되 frozen manifest는 실제 pin을 요구한다.

## Progress
- 필수 문서, Gate 1 완료 기록, scripts 및 working tree 확인.
- 계약/테스트/문서 구현 및 검증 완료. 확인된 읽기 순서와 문자열의 모순도 거부한다.

## Unexpected Findings
- 기존 stack 없음. Python 3.12+ / Pydantic 2 / uv를 명시적으로 선택한다.
- Canonical owner가 요구하는 page/source/GT/policy linkage를 최소 사용자 필드에 추가한다.

## Completion Notes
Execution 1 PASS — 2026-09-11 working tree 기준. Gate 2 전체 완료는 아니다.

- 다섯 계약과 공통 reference/region/span/eligibility/provenance/metric observation 구현.
- Python 3.12+ / Pydantic 2 / uv 선택을 conventions에 문서화했고 uv.lock을 생성했다.
  검증 실행 환경은 Python 3.14.4다. 다른 지원 Python 버전 matrix는 실행하지 않았다.
- Canonical schema 문서를 추가하고 index, README, 완료 기준 owner에서 연결했다.
- ./scripts/verify 통과: doctor 구조 검사, Ruff lint/format, mypy strict(2 source files),
  pytest 52개 통과. test/lint/typecheck의 STUB을 실제 도구로 교체했다. dev만 STUB 유지.
- 유효/필수 누락/extra/coercion/Unicode/미확정 GT/uncertainty/conflict/unreadable,
  coordinates/reading order/provenance, manifest pins/holdout 및 benchmark linkage 검증.
- 첫 검증의 Ruff timezone 변환 경고와 mypy BaseModel.schema 이름 충돌을 수정했다.
  PolicyVersions 필드는 result_schema_version으로 명시했다.
- 계약/diff/acceptance review 완료. Gate 0 behavior/metric/dataset owner 규칙 변경 없음.
  Source/GT/annotation refs와 unknown metadata를 보존하고 성공 unreadable과 구조 실패를 구분한다.
- 기존 Gate 1 미커밋 변경을 보존했다. 신규 파일도 미커밋이며 commit/push하지 않았다.
- Ready for HF adapter: YES (계약 경계). 실제 dataset/revision/ID 안정성, bytes digest,
  license, writer/duplicate 검수와 외부 provenance artifact 해석은 후속 작업이다.
  Schema validation은 시각적 진실성이나 dataset 무결성 검수 완료를 보증하지 않는다.
- 실제 데이터 다운로드, frozen smoke, inference/provider, metric engine 구현 없음.
  미해결 canonical contradiction 없음.
