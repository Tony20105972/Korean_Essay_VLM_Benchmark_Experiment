# Gate 2 Execution 2 — Hugging Face Dataset Adapter

> Status: COMPLETED
> Created: 2026-09-11
> Gate: 2

## Goal
Hugging Face dataset rows를 provider-neutral `CanonicalDatasetSample`로 변환한다.

## Relevant Context
AGENTS.md → docs/index.md → dataset-policy, boundaries, verbatim-contract, metrics,
canonical-contracts, conventions, definition-of-done 및 Execution 1 완료 기록을 읽었다.

## Acceptance Criteria
- [x] Pinned HF revision과 column mapping을 strict config로 표현한다.
- [x] HF SDK는 adapter/provider 내부에만 있고 canonical/evaluation contracts는 import하지 않는다.
- [x] Public/gated authentication, revision resolution, image/text/ID/duplicate 검증을 지원한다.
- [x] inspect/fetch/validate CLI와 fixture-only deterministic tests가 있다.
- [x] 실제 lint/typecheck/test 및 repository verify가 통과한다.

## Non-Goals
실제 smoke dataset 선정·동결, Golden 선언, VLM/metrics/benchmark runner, Object Storage.

## Implementation Steps
1. HF config, client boundary, materializer 및 CLI를 구현한다.
2. mock client와 rows로 deterministic tests를 작성한다.
3. 문서, example config, ignore rules, 검증 명령을 정리한다.
4. verify 및 completion review 후 completed로 이동한다.

## Risks
Schema validation은 Hub 권한, stable-ID 정책의 실제 적합성, image bytes provenance,
near-duplicate 검수를 대신하지 않는다. 실제 dataset은 후속 smoke selection에서 검수한다.

## Progress
- Gate 2 Execution 1 contracts와 Python stack을 확인했다.
- Adapter, CLI, fixture-only tests, example config 및 HF integration 문서를 구현했다.
- 실제 image decoder, pinned revision resolution, mapped-column/schema/selection checks를 검증했다.

## Completion Notes
Execution 2 PASS — 2026-09-11 working tree 기준. Gate 2 전체 완료는 아니다.

- `HuggingFaceDatasetAdapter`는 strict `huggingface-adapter/v1` JSON config와 injected
  Hub client boundary를 사용한다. `datasets`/`huggingface_hub` imports는 provider module에만 있다.
- Commit-like 7–64 hex prefix만 받아 Hub의 40-char resolved SHA와 대조한다. branch/tag
  revision은 reject한다. Canonical sample source에는 resolved SHA만 기록한다.
- Mapping은 image/transcription/sample_id/writer_id column명을 config로 받으며, canonical ID는
  dataset + resolved commit + upstream stable ID로 생성한다. row offset은 identity로 사용하지 않는다.
- `HF_TOKEN`은 process environment에서만 읽는다. Public dataset은 token 없이 작동한다.
  token은 config, example, CLI output 및 error에 기록하지 않는다.
- `./scripts/dataset inspect|fetch|validate`를 추가했다. fetch output은 NDJSON stdout 또는
  명시된 output path이고 default HF cache를 사용한다. local `.cache/`, `hf-cache/`와 token-like
  files는 Git-ignore한다.
- `./scripts/verify` 통과: doctor, Ruff, mypy strict(5 source files), pytest 73개 통과.
  `scripts/dataset --help`, example manifest strict parse, shell syntax, `git diff --check`도 통과했다.
- Tests는 injected fake Hub와 valid tiny PNG fixture만 사용한다. network/download는 실행하지 않았다.
- 실제 HF smoke dataset identifier, licensed access, immutable commit, mapping, subset, stable-ID
  semantics, writer/duplicate review와 canonical frozen DatasetManifest 작성은 후속 작업이다.
  변경은 미커밋이며 기존 작업 tree 변경을 보존했다.
