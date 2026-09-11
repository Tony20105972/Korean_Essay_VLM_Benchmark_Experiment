# Gate 2 Execution 3 — hyokwan/ocr_dataset 연결 및 smoke-v1 고정

> Status: IN_PROGRESS
> Created: 2026-09-11
> Gate: 2

## Goal
`hyokwan/ocr_dataset`을 pinned revision으로 연결하고 재현 가능한 `smoke-v1` 평가 부분집합을 고정한다.

## Why
Execution 2의 HF adapter는 fixture로만 검증했다. Execution 4의 metric engine은 실제 이미지와
verbatim GT가 고정된 subset을 입력으로 요구한다. upstream dataset 전체는 Golden이 아니며
G0 Smoke tier의 External Smoke Dataset으로만 사용한다.

## Relevant Context
AGENTS.md → docs/index.md → boundaries, verbatim-contract, metrics, dataset-policy,
definition-of-done, datasets/huggingface-adapter.md, contracts/canonical-contracts.md,
conventions, Execution 1/2 완료 기록.

## Current State
- `HuggingFaceDatasetAdapter`는 upstream string ID column mapping을 **필수**로 요구한다.
- `RealHubClient.rows()`는 `load_dataset`으로 split 전체를 materialize한다.
- 실제 dataset에는 ID column이 없고 auto-converted parquet은 86 shard / 42.7 GB다.

## Acceptance Criteria
- [ ] `inspect`가 pinned 40-char SHA, 실제 column/feature, split을 출력하고 사전 조사와 대조된다.
- [ ] Adapter가 ID column 없는 dataset에 대해 `content-digest` identity를 지원하고
      canonical `Source.identity_method`에 이를 정직하게 기록한다.
- [ ] Row location은 fetch hint일 뿐이며 materialize 시 content digest 재계산으로 검증된다.
      upstream row 순서가 바뀌면 실패한다.
- [ ] `smoke-v1`이 100–200 samples로 고정되고 canonical `DatasetManifest`(tier G0,
      role benchmark, golden false)로 직렬화된다.
- [ ] 선택은 결정론적이며 label(P.Paper/T.Tablet)과 output 길이 band를 계층화한다.
      제공되지 않는 writer/difficulty 다양성을 주장하지 않는다.
- [ ] GT 검증이 empty/duplicate/encoding/Unicode 이상/mixed-script를 보고하고 GT를 수정하지 않는다.
- [ ] 수동 검토 아티팩트(Markdown index + thumbnail HTML)를 생성한다.
- [ ] `./scripts/dataset fetch smoke-v1`과 `validate smoke-v1`이 전체 42.7 GB 다운로드 없이
      manifest pins와 일치함을 확인한다.
- [ ] fixture-only deterministic tests와 `./scripts/verify`가 통과한다.

## Non-Goals
VLM 추론, OpenRouter, metric 계산, verifier, fine-tuning, Golden 선언, Object Storage,
annotation UI, GT 정규화/교정, 전체 dataset 다운로드.

## Implementation Steps
1. 실제 `inspect`로 revision/schema/split을 확인하고 사전 조사와 차이를 기록한다.
2. Adapter에 content-digest identity와 검증되는 row-location fetch hint를 추가한다.
3. Provider parquet layer에 column-pruned scan과 row-group 타깃 read를 추가한다.
4. 순수 selection/GT-check 모듈과 manifest builder를 구현한다.
5. CLI에 `scan`/`select`/`review`와 manifest name 해석을 추가한다.
6. 실제 scan → select → fetch → validate를 실행하고 산출물을 고정한다.
7. 문서 갱신, fixture-only tests, `./scripts/verify`.

## Verification
`./scripts/dataset inspect|scan|select|review|fetch|validate`, `./scripts/verify`.

## Risks
- upstream row 재정렬 시 row-location hint 무효화 → content digest 재검증으로 탐지한다.
- row group 단위 read로 선택 pool을 제한하므로 전체 85k의 무작위 표본이 아니다 → 한계를 문서화한다.
- Scan 대상 밖 shard의 분포는 알 수 없다 → 보고서에 scan window를 명시한다.

## Progress
- 사전 조사: public dataset, sha `7257b1a377b98e06e85ac2aba040263083aa9185`,
  86 parquet shards, shard당 995 rows / 5 row groups / row group당 약 100 MB.
- 4-shard text scan에서 `label`에 빈 문자열 값이 존재함을 확인했다(사전 조사의 3 classes와 일치).

## Unexpected Findings

- `RealHubClient.inspect`가 `builder.as_dataset()`를 호출하고 있었다. 이 dataset처럼 로컬에
  준비되지 않은 source에서는 `FileNotFoundError`로 실패한다. Preview를 parquet footer와
  text-only row group에서 만들도록 바꿔 image payload 전송 없이 동작하게 했다.
- 사전 조사의 `output` 길이 하한 11자는 scan window에서 재현되지 않았다(최소 22자).
  Inspect/scan 결과를 신뢰한다.
- `label` column의 세 번째 class는 빈 문자열이다. 값을 지어내지 않고 `unlabeled`로 보고한다.
- "자모 분리"를 단일 지표로 세면 정상 원문을 손상으로 오독한다. Scan window에서 conjoining
  jamo는 0건이고, 검출된 자모는 전부 독립 글자로 쓰인 compatibility jamo(ㅇ/ㅂ/ㅅ)였다.
  두 지표를 분리했다.
- `label`(P.Paper / T.Tablet)은 매체 유형이지만 canonical `Metadata`에는 이를 담을 필드가 없다.
  `capture_quality`(촬영 품질)나 `handwriting_difficulty`와 의미가 다르고 `script_properties` /
  `content_properties`에도 해당하지 않는다. 임의로 욱여넣지 않고 selection report에만 남겼다.
  Execution 4에서 매체별 slice가 필요하면 `Metadata`에 capture-medium 필드를 추가해야 하며,
  이는 [Canonical contracts](../../contracts/canonical-contracts.md)가 소유하는 변경이다.

## Completion Notes
