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
바꿔 변환한다. `sample_id`는 빈 값이 아닌 upstream string ID여야 한다. Row number,
iteration position, 자동 증가 counter는 mapping으로 쓸 수 없다. `writer_id`는 optional이며
없을 때 provenance에 `writer-disjoint guarantee unavailable`을 남긴다.

`selected_original_sample_ids`는 optional upstream ID subset이다. 존재하면 adapter는 이
ID들만 materialize하고 하나라도 없거나 중복이면 실패한다. 선택하지 않으면 split 전체를
읽을 수 있으므로 real smoke manifest에는 명시 selection을 권장한다. 이 config는 frozen
canonical `DatasetManifest`가 아니다. 실제 smoke subset은 다음 Execution에서 canonical
manifest의 sample/image digest/GT revision과 함께 동결한다.

## Conversion and validation

Adapter는 HF Image column을 decode=false로 읽어 original bytes의 SHA-256을 계산한다.
image value는 nonempty bytes 또는 bytes/path를 가진 mapping이어야 하고 Pillow가 실제 image로
열 수 있어야 한다. Path는 local에서 읽을 수 있어야 한다. Decoded PIL image와 re-encoded
bytes를 source identity로 사용하지 않는다. Transcription은 string이어야 하며 trim, Unicode normalization, spelling correction,
CRLF conversion을 하지 않는다. CR을 포함한 text는 source/변환 이력이 없는 상태로
canonical GT에 넣을 수 없으므로 실패한다.

Canonical `sample_id`는 `hf:{dataset}@{resolved_commit}:{upstream_id}`이다. URI는
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

## Commands

```bash
./scripts/dataset inspect owner/dataset-name --revision 0123456789abcdef0123456789abcdef01234567 --split train
./scripts/dataset validate examples/huggingface-adapter.json
./scripts/dataset fetch examples/huggingface-adapter.json --output .cache/samples.ndjson
```

`inspect`는 pinned revision을 해석하여 dataset, resolved revision, available splits, columns,
feature types와 first-row의 field type preview를 JSON으로 출력한다. Real HF inspect output에는
일반적인 image/transcription/sample-ID/writer-ID column name과 feature를 기반으로 한
`likely_*_fields` 후보도 포함한다. 후보는 mapping을 대신하는 추측이 아니며 사용자가
명시적으로 mapping을 결정한다. `fetch`는 canonical samples를 NDJSON으로 stdout 또는 `--output` file에 쓴다.
`validate`는 inspect의 column check와 selected rows의 conversion/ID/image/text validation을
실행한다. 세 명령 모두 오류를 stderr에만 보고하고 token은 출력하지 않는다.

Network을 쓰는 inspect/fetch/validate는 real dataset 선택 이후의 manual operation이다.
Unit tests는 injected fake Hub client와 small bytes fixtures만 쓰며 network/cache에 의존하지 않는다.
