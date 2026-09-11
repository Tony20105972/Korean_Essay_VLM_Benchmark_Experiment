# Canonical Contracts v1

> Owner: docs/contracts/canonical-contracts.md — serialized shape, validation and integration
> Executable definitions: [contracts.py](../../src/nonsulfit/contracts.py)

Behavior와 권한은 기존 [Perception](../ai/perception/verbatim-contract.md),
[Architecture](../architecture/boundaries.md), [Dataset](../ai/datasets/dataset-policy.md),
[Metrics](../ai/evaluation/metrics.md) owner를 따른다. 이 문서는 구현 표현만 소유한다.
Execution 1은 계약 기초이며 adapter, inference, metric calculation을 실행하지 않는다.
Stack과 설치는 [Conventions](../engineering/conventions.md#gate-2-python-stack)을 따른다.

## Public entry points

`from nonsulfit.contracts import ...`로 아래 모델을 사용한다.

| Contract | Version | Identity and scope |
|---|---|---|
| CanonicalDatasetSample | dataset-sample/v1 | sample_id; source page 한 장, source/input/GT 및 provenance |
| DatasetManifest | dataset-manifest/v1 | manifest_id + manifest_version; upstream과 별도로 고정한 평가 부분집합 |
| CanonicalPerceptionResult | perception-result/v1 | result_id + result_version; sample_id 및 page run_id에 연결된 결과 |
| BenchmarkRun | benchmark-run/v1 | benchmark_execution_id; manifest/candidate/configuration/policies와 선택 sample IDs |
| BenchmarkSampleResult | benchmark-sample-result/v1 | evaluation_id; sample_id + page run_id + benchmark_execution_id에 귀속되는 평가 결과 |

모든 schema_version은 필수 literal이다. ID/version은 빈 값이나 whitespace-only를 거부한다.
Pydantic strict type과 extra=forbid를 모든 중첩 객체에 적용한다. 숫자→문자열,
문자열→bool 등 암묵적 변환을 하지 않는다. 모델 변경은 새 artifact/version으로 저장한다.
`frozen=True`는 field 재할당 방지이며 영구 저장소 불변성 보증은 아니다.

교환 형식은 UTF-8 JSON이다. `Model.model_validate_json(payload)`가 공식 입력 경계다.
Python 객체를 직접 넣을 때 collection은 strict tuple이어야 한다(JSON에서는 array).
`model_construct`, 검증 없는 `model_copy(update=...)`는 입력 검증 경로로 쓰지 않는다.
`model_dump_json()`은 Unicode와 공백을 그대로 round-trip한다.
`Model.model_json_schema()`로 기계 판독 shape를 얻을 수 있다. JSON Schema만으로는
cross-field validators를 실행할 수 없으므로 최종 수용에는 Pydantic validation이 필요하다.

## Dataset sample and annotations

`source`는 provider, source_type(external/domain/synthetic), dataset_identifier,
revision, split, original_sample_id, identity_method를 갖는다. 알 수 없는 upstream 값은
필드 자체를 생략하지 않고 null이다. Metadata/annotations 전체는 생략 또는 null 가능하다.
Metadata의 writer_id, script_properties, content_properties는 null; capture_quality와
handwriting_difficulty는 unknown이 기본이다. 두 품질 축은 독립적이다.

`input`은 image artifact ID, URI, 원본 bytes의 SHA-256(lowercase hex), page_id다.
URI는 local/object/http 등 위치 참조일 뿐 schema가 읽거나 다운로드하지 않는다.
`sample_id`는 provider-neutral이고 adapter가 namespace를 포함해 충돌 없이 결정한다.
Upstream stable ID가 없으면 immutable source revision + source digest + page identity에
기반한 content-digest 전략을 사용한다. Row index만을 안정성 근거로 사용하지 않는다.
Upstream ID의 실제 안정성과 digest의 bytes 일치는 adapter 검증 책임이다.

`ground_truth`는 transcription, revision, eligibility(text_eligible + reason)를 갖는다.
null transcription은 미확정 GT이고 빈 문자열은 확인된 빈 전사다. Text-eligible이면
null을 거부한다. Ineligible이면 이유를 요구한다. 부분 GT는 문자열로 보존하면서
ineligible로 표시할 수 있다. GT의 CR은 수정하지 않고 거부하며 LF 변환은 adapter가
source 원문과 변환 이력 및 GT revision을 보존한 뒤 수행한다. NFC/trim/교정은 하지 않는다.

Annotations는 자체 revision과 uncertain_regions, unreadable_regions,
intentionally_non_standard_text를 갖는다. Span은 저장 문자열의 Unicode code-point
반개방 구간 [start,end)다. Region은 원본 artifact ID와 normalized-top-left 좌표
(x,y,width,height, 모두 0–1 범위)를 갖는다. 위치가 없으면 임의 bbox를 만들지 않고
annotation을 생략한다. 전체 페이지가 실제 관찰 범위라면 (0,0,1,1)을 쓸 수 있다.
Nonstandard opportunity의 ID, span, observed_text, error_type, 표준화 후보 및 reason을
표현하며 GT와 정확한 문자열 일치, 비중첩, text eligibility를 검증한다.
Sample/GT revision은 부모 객체에서 상속한다. 후보 문자열을 GT에 반영하지 않는다.

## Frozen manifest representation

`selected_samples`의 순서 있는 항목들이 selected sample IDs의 단일 소유자다.
별도 ID 목록을 중복 저장하지 않는다. 각 항목은 sample_id, image reference/digest/page,
GT/annotation revision, writer_id 또는 null, eligibility, versioned sample_reference를 고정한다.
Dataset identifier/revision/split, manifest version과 selection metadata는 필수다.
Sample 단계의 unknown upstream revision은 허용하지만 manifest에서는 null,
unknown/main/master/latest를 거부한다. 다른 revision의 실제 불변성도 adapter에서 확인한다.

SelectionMetadata는 method, seed 또는 null, rationale, timezone 포함 ISO timestamp,
change_reason, lineage, exposure_history, permission reference, integrity review reference,
writer-disjoint 상태를 가진다. Unknown exposure는 null이고 검증된 미노출은 빈 array다.
필수값을 채우려고 임의 날짜/seed/권한/검수 결과를 생성하지 않는다.

중복 sample ID/image ID/exact digest, Golden training, 노출 또는 이력 미확인 holdout,
검수 근거 없는 writer-disjoint 주장을 거부한다. Domain holdout에는 writer ID와 검수
근거를 요구한다. 빈 부분집합은 empty-run 계산 계약을 위해 유효하지만 smoke 확보로
간주하지 않는다. 외부 writer 미상 sample은 provenance notes에
`writer-disjoint guarantee unavailable`을 명시한다.

Materialization 후 `manifest.validate_samples(tuple(samples))`를 호출하면 선택 집합,
source origin/revision/split, image, GT/annotation revision, eligibility, writer pins를 대조한다.
Artifact reference가 가리키는 파일의 존재, 권한, digest, near-duplicate 검수의 진실성,
이전 manifest 변경 이력은 schema만으로 증명할 수 없다. 실제 freeze 전에 후속 adapter와
검수 작업이 수행해야 한다. 기존 버전을 덮어쓰지 않는다.

## Perception representation

Transcription과 text_regions, reading_order, uncertain_spans, unreadable_regions,
perception_status, source_reference, provenance를 함께 요구한다. 모든 transcription
code point는 source text region으로 추적된다. Text 없는 unreadable region도 유효하다.

- confirmed: uncertain/unreadable 항목 없음. 빈 이미지의 확인된 빈 전사도 가능하다.
- uncertain: 불확실 span 또는 부분 unreadable 존재. 읽힌 텍스트는 보존한다.
- unreadable: 전사 문자열이 비어 있고 unreadable region이 있으며 uncertain 후보가 없음.

Uncertainty는 character/layout/order, uncertain/conflicting, span 또는 null, region을 갖는다.
후보 미상은 null이다. 후보가 있으면 visual_evidence를 요구하고 conflicting은 서로 다른
후보 두 개 이상을 요구한다. Schema는 실제 시각 근거의 타당성까지 판단하지 않는다.

Reading order는 before/after region ID의 비순환 관계다. 순서가 유일하지 않으면 order
uncertainty를 요구한다. Partial order에서 문자열/배열 순서는 직렬화 순서일 뿐 확인된
읽기 순서가 아니다. 전사 문자열의 CRLF·분해 자모·학생 오류는 수정하지 않는다.
Region ID 재사용 시 좌표가 같아야 하며 존재하지 않는 order reference를 거부한다.

SourceReference는 original image와 실제 input_artifact_id를 분리한다. 파생 이미지면
versioned derived reference와 원본 좌표로의 mapping reference를 요구한다.
Provenance에는 producer/version/upstream, page run_id, parser_version,
attempt_records_reference, raw_response_ref가 있다. Raw response 미존재는 null + 이유다.
Attempt record는 Architecture owner의 ARCH004 및 linkage 필드(provider/model resolution,
prompt/preprocessing/pipeline versions, timestamps/status/usage/cost)를 담는 외부 artifact
참조다. Execution 1에서는 attempt 실행이나 저장 형식을 구현하지 않는다.

## Benchmark representation and missing measurements

BenchmarkRun은 page inference run과 구별되는 benchmark_execution_id를 사용한다.
Candidate/configuration은 versioned opaque references이며 실제 provider-specific object를
포함하지 않는다. 후속 runner는 참조 대상에 model resolution, prompt/preprocessing/pipeline,
retry/timeout/concurrency/cost basis를 고정해야 한다. Policies는 metric, normalization,
annotation, result_schema_version, parser를 명시한다.

BenchmarkSampleResult는 source/image/GT/annotation 및 manifest/policy revisions,
eligibility, terminal status, prediction, metrics, annotation_labels_reference를 보존한다.
Success는 canonical prediction을 요구하고 failure는 null prediction + 이유를 요구한다.
유효한 unreadable도 success다. `metric_prediction`은 success의 원문 또는 실패의 빈 문자열을
반환한다. Prediction sample/run/source/parser linkage를 검증한다.
`result.validate_context(run, manifest)`는 benchmark/manifest/policy/sample pins를 대조한다.
후속 runner는 모든 selected page가 정확히 하나의 terminal result를 갖는지 검사해야 한다.

Metrics는 metric 이름 → numerator/denominator/value/status/reason 객체다.
Counts가 적용되지 않는 latency 등의 numerator/denominator는 null 가능하다.
Measured는 value가 필수이고 undefined/not-measured/provisional은 official value=null과
이유를 요구한다. CER 등은 1 초과 가능하며 음수/NaN/Infinity는 거부한다.
미측정은 빈 metrics 또는 명시적 not-measured로 표현하며 0으로 채우지 않는다.
수치 계산의 정확성, official metric completeness, annotation adjudication, aggregate coverage는
후속 evaluation engine 책임이다. 이 계약의 통과로 benchmark 품질/안전성을 주장하지 않는다.

## HF adapter handoff

계약 경계는 준비됐다. 다음 Execution에서 실제 dataset의 revision pin, stable ID 전략,
원본 image bytes/digest, GT 변환 이력, license와 writer availability를 확인하고
CanonicalDatasetSample을 만든 뒤 DatasetManifest와 validate_samples로 대조한다.
실제 HF 데이터, frozen smoke manifest, inference adapter와 평가 엔진은 아직 없다.
Synthetic 예시는 [계약 테스트](../../tests/test_contracts.py)의 fixture factories에 있다.
