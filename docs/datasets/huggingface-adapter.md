# Hugging Face Dataset Adapter

> Owner: docs/datasets/huggingface-adapter.md — HF source configuration, adapter behavior and CLI

HF는 첫 external dataset provider다. Adapter만 `datasets` 및 `huggingface_hub`를 안다.
adapter의 output은 [CanonicalDatasetSample](../contracts/canonical-contracts.md)이고,
Evaluation/Benchmark 계층은 HF row/feature/API를 알지 않는다. Dataset 사용 권한과
Golden/holdout 정책은 [Dataset Policy](../ai/datasets/dataset-policy.md)가 소유한다.

## Adapter manifest

JSON UTF-8 adapter manifest는 `huggingface-adapter/v1`이다. 예시는
[huggingface-adapter.json](../../examples/huggingface-adapter.json)이다.

```json
{
  "schema_version": "huggingface-adapter/v1",
  "dataset": "owner/dataset-name",
  "revision": "0123456789abcdef0123456789abcdef01234567",
  "split": "train",
  "image": "image",
  "transcription": "text",
  "sample_id": "id",
  "writer_id": "writer_id",
  "selected_original_sample_ids": ["stable-upstream-id-001"]
}
```

`revision`은 7–64 자리 hexadecimal Git commit prefix여야 한다. branch/tag/`main`/`latest`는
허용하지 않는다. Hub가 이를 full 40-character commit SHA로 해석하고, 요청 prefix와
일치하지 않으면 adapter가 실패한다. 변환된 source revision에는 full SHA만 기록한다.

`image`, `transcription`, `sample_id`, `writer_id`는 dataset column mapping이다.
따라서 `image/text`, `img/label`, `picture/transcript`처럼 서로 다른 schema를 adapter 설정만
바꿔 변환한다. `writer_id`는 optional이며 없을 때 provenance에
`writer-disjoint guarantee unavailable`을 남긴다.

## Sample identity

`sample_id` mapping이 있으면 identity method는 `upstream-id`다. 값은 빈 값이 아닌 upstream
string ID여야 하고 row number, iteration position, 자동 증가 counter는 쓸 수 없다.

`sample_id`가 null이면 identity method는 `content-digest`다. ID column이 없는 dataset을 위한
것이며 adapter가 `sha256(domain || sha256(image bytes) || 0x00 || utf8(transcription))`의 앞
32 hex로 `sha256-…` ID를 만든다. Content로만 결정되므로 upstream이 row를 재정렬해도 같은
sample은 같은 ID를 유지하고, image나 GT가 바뀌면 다른 sample이 된다. 이때 canonical sample의
`identity_method`는 `content-digest`이고 provenance에
`sample identity derived from image and GT content digest`를 남긴다. 이 ID는 upstream이 부여한
식별자가 아니며 그렇게 주장하지 않는다.

## Selection

`selected_original_sample_ids`는 optional upstream ID subset이다. 존재하면 adapter는 이
ID들만 materialize하고 하나라도 없거나 중복이면 실패한다.

`selected_rows`는 frozen subset을 위한 형태이며 `{sample_id, file, row}` 목록이다. `file`은
repo 상대 parquet 경로, `row`는 그 file 안의 절대 row index다. 이것은 **검증되는 fetch
hint**이지 identity가 아니다. Adapter는 해당 row group만 읽고, 각 row에서 다시 계산한 ID가
pin된 `sample_id`와 다르면 실패한다. 즉 row 위치는 다운로드 범위를 줄이는 데만 쓰이고 무엇이
그 sample인지는 항상 content가 결정한다. 두 selection 형식은 동시에 쓸 수 없다.

이 config는 frozen canonical `DatasetManifest`가 아니다. 실제 subset은
[smoke-v1](smoke-v1.md)처럼 canonical manifest의 sample/image digest/GT revision과 함께 동결한다.

## Conversion and validation

Adapter는 HF Image column을 decode=false로 읽어 original bytes의 SHA-256을 계산한다.
image value는 nonempty bytes 또는 bytes/path를 가진 mapping이어야 하고 Pillow가 실제 image로
열 수 있어야 한다. Path는 local에서 읽을 수 있어야 한다. Decoded PIL image와 re-encoded
bytes를 source identity로 사용하지 않는다. Transcription은 string이어야 하며 trim, Unicode normalization, spelling correction,
CRLF conversion을 하지 않는다. CR을 포함한 text는 source/변환 이력이 없는 상태로
canonical GT에 넣을 수 없으므로 실패한다.

Canonical `sample_id`는 `hf:{dataset}@{resolved_commit}:{stable_id}`이다. URI는
`hf://datasets/...` provenance location이며 adapter가 canonical output에서 Hub object를
노출하지 않는다. Image digest, GT revision, upstream source reference와 writer metadata는
sample에 보존된다. Adapter는 schema/column/ID/image/text checks만 수행한다. license,
permission, source content 진실성, writer/near-duplicate 검수와 Golden 선언은 별도 review다.

## Authentication and cache

Public dataset은 token 없이 요청한다. Private/gated dataset은 `HF_TOKEN` environment variable를
자동으로 읽는다. Token은 config/output/log에 저장되지 않는다. Basic usage:

```bash
export HF_TOKEN='...'
./scripts/dataset validate path/to/huggingface-adapter.json
```

HF default cache를 사용한다. 대용량 source image와 cache result를 Git에 추가하지 않는다.

## Bounded reads

Hub는 대용량 dataset을 auto-converted parquet shard로 제공한다. Adapter는 split 전체를
materialize하지 않는다. Scan은 column pruning으로 image payload를 건너뛰고, `selected_rows`
fetch는 필요한 row group만 읽는다. 200개 sample을 얻기 위해 42 GB split을 내려받는 것은
허용하지 않는다. 이 parquet 접근은 `nonsulfit.providers.parquet`에만 있다.

## Commands

```bash
./scripts/dataset inspect owner/dataset-name --revision 0123456789abcdef0123456789abcdef01234567 --split train
./scripts/dataset scan owner/dataset-name --revision <sha> --split train \
  --transcription output --label label --files 6 --output .cache/scan.json
./scripts/dataset select smoke-v1 --scan .cache/scan.json --size 150 \
  --image image --transcription output --label label \
  --pool-row-groups 2 --review-dir .cache/smoke-v1
./scripts/dataset validate smoke-v1
./scripts/dataset fetch smoke-v1 --output .cache/smoke-v1/samples.ndjson
./scripts/dataset validate examples/huggingface-adapter.json
```

`inspect`는 pinned revision을 해석하여 dataset, resolved revision, available splits, split별 row
수, parquet file 수, columns, feature types와 first-row의 field type preview를 JSON으로 출력한다.
Preview는 parquet footer와 하나의 text row group에서만 만들며 image payload를 전송하지 않는다.
얻을 수 없으면 `preview_source`가 `unavailable`이다. Real HF inspect output에는 일반적인
image/transcription/sample-ID/writer-ID column name과 feature를 기반으로 한 `likely_*_fields`
후보도 포함한다. 후보는 mapping을 대신하는 추측이 아니며 사용자가 명시적으로 mapping을 결정한다.

`scan`은 image를 제외한 light-weight column만 읽어 selection용 scan index를 만든다. `--files`는
split의 parquet shard를 균등 간격으로 N개만 읽고, `--row-groups`는 shard당 앞 N개 row group으로
제한한다. `select`는 scan index에서 결정론적으로 subset을 고르고 선택된 row가 속한 row group만
읽어 canonical `DatasetManifest`, `selected_rows` adapter config, selection report, manual review
artifact를 쓴다. 선택 규칙은 [smoke-v1](smoke-v1.md)이 설명한다.

`fetch`와 `validate`의 인자는 adapter manifest 경로이거나 frozen subset 이름이다. 이름을 주면
`datasets/manifests/{name}.adapter.json`으로 해석하고, 같은 이름의 canonical manifest가 있으면
materialize 결과를 그 pin과 대조한다(`frozen_manifest_checked`). `fetch`는 canonical samples를
NDJSON으로 stdout 또는 `--output` file에 쓴다. 모든 명령은 오류를 stderr에만 보고하고 token을
출력하지 않는다.

Network을 쓰는 inspect/fetch/validate는 real dataset 선택 이후의 manual operation이다.
Unit tests는 injected fake Hub client와 small bytes fixtures만 쓰며 network/cache에 의존하지 않는다.
