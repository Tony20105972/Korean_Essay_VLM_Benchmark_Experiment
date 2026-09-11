"""Synthetic fixtures only: no real dataset, network, clock, or inference."""

import json
from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from nonsulfit.contracts import (
    BenchmarkRun,
    BenchmarkSampleResult,
    CanonicalDatasetSample,
    CanonicalPerceptionResult,
    DatasetManifest,
    MetricObservation,
)

REF = {"artifact_id": "fixture", "version": "v1"}
PROVENANCE = {
    "producer": "synthetic-test",
    "producer_version": "v1",
    "upstream": [REF],
    "notes": ["writer-disjoint guarantee unavailable"],
}
IMAGE = {
    "artifact_id": "image-1",
    "uri": "fixtures/page.png",
    "sha256": "a" * 64,
    "page_id": "page-1",
}
ELIGIBILITY = {"text_eligible": True, "reason": None}
POLICIES = {
    "metric": "evaluation/metrics-v1",
    "normalization": "evaluation/normalization-policy-v1",
    "annotation": "fixture/v1",
    "result_schema_version": "perception-result/v1",
    "parser": "fixture-parser/v1",
}
REGION = {
    "region_id": "r1",
    "image_artifact_id": "image-1",
    "x": 0.0,
    "y": 0.0,
    "width": 1.0,
    "height": 1.0,
    "coordinate_system": "normalized-top-left",
}


def sample_data() -> dict[str, Any]:
    return deepcopy(
        {
            "schema_version": "dataset-sample/v1",
            "sample_id": "sample-1",
            "source": {
                "provider": "fixture",
                "source_type": "external",
                "dataset_identifier": "fixture/korean",
                "revision": "commit-123",
                "split": "test",
                "original_sample_id": "original-1",
                "identity_method": "upstream-id",
            },
            "input": IMAGE,
            "ground_truth": {
                "transcription": "세계화의 문재점은\n가🙂 ",
                "revision": "gt-1",
                "eligibility": ELIGIBILITY,
            },
            "provenance": PROVENANCE,
        }
    )


def prediction_data(text: str = "문재점") -> dict[str, Any]:
    return deepcopy(
        {
            "schema_version": "perception-result/v1",
            "result_id": "result-1",
            "result_version": "v1",
            "sample_id": "sample-1",
            "transcription": text,
            "text_regions": [{"region": REGION, "span": {"start": 0, "end": len(text)}}]
            if text
            else [],
            "reading_order": [],
            "uncertain_spans": [],
            "unreadable_regions": [],
            "perception_status": "confirmed",
            "source_reference": {
                "original": IMAGE,
                "input_artifact_id": "image-1",
                "derived_reference": None,
                "coordinate_mapping_reference": None,
            },
            "provenance": {
                **PROVENANCE,
                "run_id": "page-run-1",
                "parser_version": "fixture-parser/v1",
                "attempt_records_reference": REF,
                "raw_response_ref": None,
                "raw_response_absence_reason": "synthetic fixture",
            },
        }
    )


def manifest_data() -> dict[str, Any]:
    return deepcopy(
        {
            "schema_version": "dataset-manifest/v1",
            "manifest_id": "smoke-fixture",
            "manifest_version": "v1",
            "dataset_identifier": "fixture/korean",
            "dataset_revision": "commit-123",
            "split": "test",
            "source_origin": "external",
            "tier": "G0",
            "role": "benchmark",
            "golden": False,
            "selected_samples": [
                {
                    "sample_id": "sample-1",
                    "image": IMAGE,
                    "gt_revision": "gt-1",
                    "annotation_revision": None,
                    "writer_id": None,
                    "eligibility": ELIGIBILITY,
                    "sample_reference": REF,
                }
            ],
            "selection_metadata": {
                "method": "explicit-stable-ids",
                "seed": None,
                "rationale": "contract fixture",
                "selected_at": "2026-09-11T00:00:00Z",
                "change_reason": "initial",
                "lineage": [REF],
                "exposure_history": None,
                "permission_reference": None,
                "integrity_review_reference": None,
                "writer_disjoint": "unavailable",
            },
            "provenance": PROVENANCE,
        }
    )


def result_data() -> dict[str, Any]:
    return deepcopy(
        {
            "schema_version": "benchmark-sample-result/v1",
            "evaluation_id": "eval-1",
            "benchmark_execution_id": "bench-1",
            "sample_id": "sample-1",
            "run_id": "page-run-1",
            "manifest_reference": {"artifact_id": "smoke-fixture", "version": "v1"},
            "source": sample_data()["source"],
            "image": IMAGE,
            "gt_revision": "gt-1",
            "annotation_revision": None,
            "policies": POLICIES,
            "eligibility": ELIGIBILITY,
            "terminal_status": "success",
            "prediction": prediction_data(),
            "failure_reason": None,
            "metrics": {},
            "annotation_labels_reference": None,
            "provenance": PROVENANCE,
        }
    )


def run_data() -> dict[str, Any]:
    return deepcopy(
        {
            "schema_version": "benchmark-run/v1",
            "benchmark_execution_id": "bench-1",
            "manifest_reference": {"artifact_id": "smoke-fixture", "version": "v1"},
            "candidate_reference": REF,
            "execution_configuration_reference": REF,
            "policies": POLICIES,
            "sample_ids": ["sample-1"],
            "provenance": PROVENANCE,
        }
    )


def parse(model: Any, data: dict[str, Any]) -> Any:
    # JSON is the adapter interchange boundary; strict Python tuples are intentional.
    return model.model_validate_json(json.dumps(data, ensure_ascii=False))


def test_optional_metadata_and_exact_unicode_round_trip() -> None:
    data = sample_data()
    sample = parse(CanonicalDatasetSample, data)
    assert sample.metadata is None
    assert sample.annotations is None
    assert sample.ground_truth.transcription == data["ground_truth"]["transcription"]
    assert CanonicalDatasetSample.model_validate_json(sample.model_dump_json()) == sample
    data["metadata"] = {"capture_quality": "good", "handwriting_difficulty": "extreme"}
    assert parse(CanonicalDatasetSample, data).metadata.writer_id is None


@pytest.mark.parametrize(
    "field", ["schema_version", "sample_id", "source", "input", "ground_truth", "provenance"]
)
def test_required_sample_fields(field: str) -> None:
    data = sample_data()
    del data[field]
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)


@pytest.mark.parametrize(
    "path,value",
    [
        (("sample_id",), 123),
        (("sample_id",), " "),
        (("schema_version",), "v99"),
        (("input", "sha256"), "invalid"),
        (("input", "uri"), ""),
        (("ground_truth", "eligibility", "text_eligible"), "true"),
        (("ground_truth", "transcription"), "가\r\n나"),
        (("source", "original_sample_id"), None),
        (("provenance", "upstream"), []),
        (("provenance", "notes"), []),
        (("provenance", "producer_version"), ""),
    ],
)
def test_invalid_sample(path: tuple[str, ...], value: Any) -> None:
    data = sample_data()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)


def test_extra_fields_rejected_recursively() -> None:
    data = sample_data()
    data["source"]["guessed_writer"] = "writer-1"
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)


def test_unknown_source_and_unresolved_gt() -> None:
    data = sample_data()
    data["source"].update(
        revision=None, split=None, original_sample_id=None, identity_method="content-digest"
    )
    data["ground_truth"].update(
        transcription=None, eligibility={"text_eligible": False, "reason": "unresolved GT"}
    )
    assert parse(CanonicalDatasetSample, data).ground_truth.transcription is None
    data["ground_truth"]["eligibility"] = ELIGIBILITY
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)
    data["ground_truth"]["transcription"] = ""
    assert parse(CanonicalDatasetSample, data).ground_truth.transcription == ""


def test_unicode_spans_no_normalization_or_trim() -> None:
    text = " 가🙂\r\n문재점 "
    prediction = parse(CanonicalPerceptionResult, prediction_data(text))
    assert prediction.transcription == text
    assert prediction.text_regions[0].span.end == len(text)
    data = prediction_data(text)
    data["text_regions"][0]["span"]["end"] = len(text.encode("utf-8"))
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)


def uncertainty() -> dict[str, Any]:
    return deepcopy(
        {
            "span": {"start": 0, "end": 1},
            "region": REGION,
            "kind": "character",
            "status": "uncertain",
            "candidates": None,
            "visual_evidence": None,
        }
    )


def test_uncertain_and_conflicting_candidates() -> None:
    data = prediction_data()
    data.update(uncertain_spans=[uncertainty()], perception_status="uncertain")
    assert parse(CanonicalPerceptionResult, data).uncertain_spans[0].candidates is None
    data["perception_status"] = "confirmed"
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)
    data["perception_status"] = "uncertain"
    data["uncertain_spans"][0].update(status="conflicting", candidates=["문", "몬"])
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)
    data["uncertain_spans"][0]["visual_evidence"] = "ambiguous vowel stroke in r1"
    assert parse(CanonicalPerceptionResult, data).perception_status == "uncertain"


def test_unreadable_without_text_and_partial_text() -> None:
    data = prediction_data("")
    data.update(
        unreadable_regions=[{"region": REGION, "reason": "no legible strokes"}],
        perception_status="unreadable",
    )
    assert parse(CanonicalPerceptionResult, data).transcription == ""
    partial = prediction_data("문")
    partial.update(unreadable_regions=data["unreadable_regions"], perception_status="uncertain")
    assert parse(CanonicalPerceptionResult, partial).transcription == "문"


@pytest.mark.parametrize(
    "mutation",
    [
        "no-reason",
        "no-attempt-ref",
        "wrong-image",
        "no-coverage",
        "invalid-span",
        "region-bounds",
        "order-cycle",
        "unknown-order",
    ],
)
def test_invalid_prediction(mutation: str) -> None:
    data = prediction_data()
    if mutation == "no-reason":
        data["provenance"]["raw_response_absence_reason"] = None
    elif mutation == "no-attempt-ref":
        del data["provenance"]["attempt_records_reference"]
    elif mutation == "wrong-image":
        data["text_regions"][0]["region"]["image_artifact_id"] = "wrong"
    elif mutation == "no-coverage":
        data["text_regions"] = []
    elif mutation == "invalid-span":
        data["text_regions"][0]["span"]["end"] = 0
    elif mutation == "region-bounds":
        data["text_regions"][0]["region"]["x"] = 0.5
    else:
        data["reading_order"] = [
            {"before": "r1", "after": "r1" if mutation == "order-cycle" else "unknown"}
        ]
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)


def test_derived_coordinates_require_mapping() -> None:
    data = prediction_data()
    data["source_reference"].update(
        input_artifact_id="derived-1",
        derived_reference={"artifact_id": "derived-1", "version": "v1"},
    )
    data["text_regions"][0]["region"]["image_artifact_id"] = "derived-1"
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)
    data["source_reference"]["coordinate_mapping_reference"] = REF
    assert parse(CanonicalPerceptionResult, data).source_reference.original.artifact_id == "image-1"


def test_nonstandard_annotation_preserves_gt_and_rejects_overlap() -> None:
    data = sample_data()
    data["ground_truth"]["transcription"] = "문재점"
    opportunity = {
        "opportunity_id": "o1",
        "span": {"start": 0, "end": 3},
        "region": REGION,
        "observed_text": "문재점",
        "error_type": "spelling",
        "standardized_candidates": ["문제점"],
        "correction_reason": "student spelling",
    }
    data["annotations"] = {"revision": "ann-1", "intentionally_non_standard_text": [opportunity]}
    assert parse(CanonicalDatasetSample, data).ground_truth.transcription == "문재점"
    opportunity["observed_text"] = "문제점"
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)
    opportunity["observed_text"] = "문재점"
    data["annotations"]["intentionally_non_standard_text"].append(
        {**opportunity, "opportunity_id": "o2"}
    )
    with pytest.raises(ValidationError):
        parse(CanonicalDatasetSample, data)


def test_manifest_materialized_pins() -> None:
    manifest = parse(DatasetManifest, manifest_data())
    manifest.validate_samples((parse(CanonicalDatasetSample, sample_data()),))
    for field in ("revision", "split", "dataset_identifier"):
        data = sample_data()
        data["source"][field] = "changed"
        with pytest.raises(ValueError):
            manifest.validate_samples((parse(CanonicalDatasetSample, data),))
    with pytest.raises(ValueError):
        manifest.validate_samples(())


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "digest",
        "mutable-revision",
        "missing-split",
        "bad-time",
        "naive-time",
        "golden-training",
        "holdout",
        "writer-claim",
    ],
)
def test_invalid_manifest(mutation: str) -> None:
    data = manifest_data()
    if mutation in {"duplicate", "digest"}:
        other = deepcopy(data["selected_samples"][0])
        if mutation == "digest":
            other["sample_id"] = "sample-2"
            other["image"]["artifact_id"] = "image-2"
        data["selected_samples"].append(other)
    elif mutation == "mutable-revision":
        data["dataset_revision"] = "main"
    elif mutation == "missing-split":
        del data["split"]
    elif mutation in {"bad-time", "naive-time"}:
        data["selection_metadata"]["selected_at"] = (
            "yesterday" if mutation == "bad-time" else "2026-09-11T00:00:00"
        )
    elif mutation == "golden-training":
        data.update(golden=True, role="training")
    elif mutation == "holdout":
        data["role"] = "final-holdout"
    else:
        data["selection_metadata"]["writer_disjoint"] = "verified"
    with pytest.raises(ValidationError):
        parse(DatasetManifest, data)


def test_benchmark_success_failure_and_linkage() -> None:
    result = parse(BenchmarkSampleResult, result_data())
    result.validate_context(
        parse(BenchmarkRun, run_data()), parse(DatasetManifest, manifest_data())
    )
    assert result.metric_prediction == "문재점"
    data = result_data()
    data.update(
        terminal_status="failure", prediction=None, failure_reason="schema validation failure"
    )
    assert parse(BenchmarkSampleResult, data).metric_prediction == ""
    data["terminal_status"] = "success"
    with pytest.raises(ValidationError):
        parse(BenchmarkSampleResult, data)
    data = result_data()
    data["run_id"] = "different"
    with pytest.raises(ValidationError):
        parse(BenchmarkSampleResult, data)
    data = run_data()
    data["policies"]["metric"] = "other-version"
    with pytest.raises(ValueError):
        result.validate_context(parse(BenchmarkRun, data), parse(DatasetManifest, manifest_data()))


def test_metric_unknown_is_not_zero_and_rates_can_exceed_one() -> None:
    metric = {
        "numerator": 3.0,
        "denominator": 1.0,
        "value": 3.0,
        "status": "measured",
        "reason": None,
    }
    assert parse(MetricObservation, metric).value == 3.0
    metric.update(value=None, status="not-measured", reason="engine not implemented")
    assert parse(MetricObservation, metric).value is None
    metric["value"] = 0.0
    with pytest.raises(ValidationError):
        parse(MetricObservation, metric)


@pytest.mark.parametrize(
    "model,factory",
    [
        (CanonicalDatasetSample, sample_data),
        (DatasetManifest, manifest_data),
        (CanonicalPerceptionResult, prediction_data),
        (BenchmarkRun, run_data),
        (BenchmarkSampleResult, result_data),
    ],
)
def test_five_contracts_json_schema_and_round_trip(model: Any, factory: Any) -> None:
    value = parse(model, factory())
    assert model.model_validate_json(value.model_dump_json()) == value
    schema = model.model_json_schema()
    assert schema["additionalProperties"] is False
    assert "schema_version" in schema["required"]


def test_partial_reading_order_requires_explicit_uncertainty() -> None:
    data = prediction_data("가나")
    data["text_regions"] = [
        {"region": REGION, "span": {"start": 0, "end": 1}},
        {"region": {**REGION, "region_id": "r2"}, "span": {"start": 1, "end": 2}},
    ]
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)
    data["uncertain_spans"] = [{**uncertainty(), "kind": "order", "span": None}]
    data["perception_status"] = "uncertain"
    assert parse(CanonicalPerceptionResult, data).reading_order == ()
    data["uncertain_spans"] = []
    data["perception_status"] = "confirmed"
    data["reading_order"] = [{"before": "r1", "after": "r2"}]
    assert parse(CanonicalPerceptionResult, data).transcription == "가나"
    data["reading_order"] = [{"before": "r2", "after": "r1"}]
    with pytest.raises(ValidationError):
        parse(CanonicalPerceptionResult, data)


def test_domain_holdout_requires_writer_evidence_and_no_exposure() -> None:
    data = manifest_data()
    data.update(source_origin="domain", role="final-holdout", golden=True)
    selection = data["selection_metadata"]
    selection.update(
        exposure_history=[],
        permission_reference="permission/v1",
        integrity_review_reference="leakage-review/v1",
        writer_disjoint="verified",
    )
    with pytest.raises(ValidationError):
        parse(DatasetManifest, data)
    data["selected_samples"][0]["writer_id"] = "writer-1"
    assert parse(DatasetManifest, data).role == "final-holdout"
    selection["exposure_history"] = ["prompt selection"]
    with pytest.raises(ValidationError):
        parse(DatasetManifest, data)
