"""Fixture-only tests: the Hugging Face SDK and network are never used here."""

from __future__ import annotations

import json
from base64 import b64decode
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

import pytest
from pydantic import ValidationError

from nonsulfit import dataset_cli
from nonsulfit.providers.huggingface import (
    CONTENT_IDENTITY_NOTE,
    AdapterConfig,
    AdapterError,
    DatasetDescription,
    HuggingFaceDatasetAdapter,
    content_sample_id,
    hf_token,
)

REQUESTED = "a" * 40
RESOLVED = "a" * 40
IMAGE_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FakeHub:
    def __init__(self, rows: list[Mapping[str, object]], resolved: str = RESOLVED) -> None:
        self._rows = rows
        self.resolved = resolved
        self.tokens: list[str | None] = []

    def resolve_revision(self, dataset: str, revision: str, token: str | None) -> str:
        self.tokens.append(token)
        assert dataset == "owner/korean"
        assert revision == REQUESTED
        return self.resolved

    def inspect(
        self, dataset: str, revision: str, split: str | None, token: str | None
    ) -> DatasetDescription:
        self.tokens.append(token)
        return DatasetDescription(
            dataset=dataset,
            requested_revision=revision,
            resolved_revision=self.resolved,
            splits=("train", "test"),
            columns=("picture", "transcript", "stable_id", "writer"),
            feature_types={
                "picture": "Image(decode=False)",
                "transcript": "Value('string')",
                "stable_id": "Value('string')",
                "writer": "Value('string')",
            },
            preview={"picture": "dict", "transcript": "str", "stable_id": "str"},
        )

    def rows(
        self, dataset: str, revision: str, split: str, token: str | None
    ) -> Iterable[Mapping[str, object]]:
        self.tokens.append(token)
        assert (dataset, revision, split) == ("owner/korean", RESOLVED, "train")
        return self._rows

    def rows_at(
        self,
        dataset: str,
        revision: str,
        locations: Sequence[tuple[str, int]],
        token: str | None,
    ) -> Iterable[Mapping[str, object]]:
        self.tokens.append(token)
        self.requested_locations = list(locations)
        return [self._rows[row] for _file, row in locations]


def config_data() -> dict[str, object]:
    return {
        "schema_version": "huggingface-adapter/v1",
        "dataset": "owner/korean",
        "revision": REQUESTED,
        "split": "train",
        "image": "picture",
        "transcription": "transcript",
        "sample_id": "stable_id",
        "writer_id": "writer",
    }


def rows() -> list[Mapping[str, object]]:
    return [
        {
            "picture": {"bytes": IMAGE_BYTES},
            "transcript": "학생의 문재점\n그대로",
            "stable_id": "page-001",
            "writer": "writer-7",
        },
        {
            "picture": IMAGE_BYTES,
            "transcript": "둘째 답안",
            "stable_id": "page-002",
            "writer": "writer-8",
        },
    ]


def adapter(
    config: dict[str, object] | None = None, source_rows: list[Mapping[str, object]] | None = None
) -> HuggingFaceDatasetAdapter:
    return HuggingFaceDatasetAdapter(
        AdapterConfig.model_validate_json(json.dumps(config or config_data())),
        FakeHub(source_rows or rows()),
        token=None,
    )


def test_mapping_converts_rows_to_provider_neutral_canonical_samples() -> None:
    materialized = adapter().materialize()
    first = materialized.samples[0]
    assert materialized.resolved_revision == RESOLVED
    assert first.sample_id == f"hf:owner/korean@{RESOLVED}:page-001"
    assert first.source.provider == "huggingface"
    assert first.ground_truth.transcription == "학생의 문재점\n그대로"
    assert first.metadata is not None and first.metadata.writer_id == "writer-7"
    assert first.input.sha256 == "431ced6916a2a21a156e38701afe55bbd7f88969fbbfc56d7fe099d47f265460"
    assert "Image(" not in first.model_dump_json()


def test_mapping_supports_other_column_names_and_preserves_missing_writer_provenance() -> None:
    config = config_data()
    config.update(image="img", transcription="label", sample_id="id", writer_id=None)
    source = [{"img": IMAGE_BYTES, "label": "문재점", "id": "x-1"}]
    sample = adapter(config, source).materialize().samples[0]
    assert sample.ground_truth.transcription == "문재점"
    assert sample.metadata is not None and sample.metadata.writer_id is None
    assert sample.provenance.notes == ("writer-disjoint guarantee unavailable",)


def test_inspect_reports_schema_and_rejects_missing_mapped_columns() -> None:
    inspected = adapter().inspect()
    assert inspected.splits == ("train", "test")
    assert inspected.feature_types["picture"] == "Image(decode=False)"
    assert inspected.likely_image_fields == ()
    config = config_data()
    config["image"] = "missing"
    with pytest.raises(AdapterError, match="mapped columns missing"):
        adapter(config).inspect()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("revision", "main"),
        ("revision", "abc123"),
        ("sample_id", ""),
        ("writer_id", 1),
        ("unknown", "field"),
    ],
)
def test_config_rejects_unpinned_or_invalid_mapping(key: str, value: object) -> None:
    config = config_data()
    config[key] = value
    with pytest.raises(ValidationError):
        AdapterConfig.model_validate_json(json.dumps(config))


def test_revision_must_resolve_to_requested_full_commit() -> None:
    with pytest.raises(AdapterError, match="immutable commit"):
        HuggingFaceDatasetAdapter(
            AdapterConfig.model_validate_json(json.dumps(config_data())),
            FakeHub(rows(), "b" * 40),
            token=None,
        ).materialize()


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("picture", b"", "image"),
        ("picture", b"not an image", "not readable"),
        ("picture", {"path": "/not/a/real/image"}, "image path"),
        ("transcript", 3, "text string"),
        ("transcript", "line\r\nbreak", "contains CR"),
        ("stable_id", "", "stable string ID"),
    ],
)
def test_invalid_row_values_fail(field: str, value: object, error: str) -> None:
    source = rows()[:1]
    changed = dict(source[0])
    changed[field] = value
    with pytest.raises(AdapterError, match=error):
        adapter(source_rows=[changed]).materialize()


def test_duplicate_and_missing_selected_ids_fail_without_row_offsets() -> None:
    duplicate = [rows()[0], dict(rows()[0])]
    with pytest.raises(AdapterError, match="duplicate upstream"):
        adapter(source_rows=duplicate).materialize()
    config = config_data()
    config["selected_original_sample_ids"] = ["page-001", "not-present"]
    with pytest.raises(AdapterError, match="not found"):
        adapter(config).materialize()
    config["selected_original_sample_ids"] = ["page-001", "page-001"]
    with pytest.raises(ValidationError, match="duplicates"):
        AdapterConfig.model_validate_json(json.dumps(config))


def test_selection_materializes_only_requested_stable_ids() -> None:
    config = config_data()
    config["selected_original_sample_ids"] = ["page-002"]
    materialized = adapter(config).materialize()
    assert [sample.source.original_sample_id for sample in materialized.samples] == ["page-002"]


def test_hf_token_is_environment_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert hf_token() is None
    monkeypatch.setenv("HF_TOKEN", "secret-value")
    fake = FakeHub(rows())
    HuggingFaceDatasetAdapter(
        AdapterConfig.model_validate_json(json.dumps(config_data())), fake
    ).materialize()
    assert fake.tokens == ["secret-value", "secret-value"]


def test_cli_validate_and_fetch_use_manifest_and_do_not_print_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "adapter.json"
    manifest.write_text(json.dumps(config_data()), encoding="utf-8")
    output = tmp_path / "samples.ndjson"
    monkeypatch.setenv("HF_TOKEN", "super-secret")
    monkeypatch.setattr(dataset_cli, "RealHubClient", lambda: FakeHub(rows()))
    assert dataset_cli.main(["validate", str(manifest)]) == 0
    assert '"status": "valid"' in capsys.readouterr().out
    assert dataset_cli.main(["fetch", str(manifest), "--output", str(output)]) == 0
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
    captured = capsys.readouterr()
    assert "super-secret" not in captured.out + captured.err


def test_cli_inspect_prints_dataset_shape_without_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HF_TOKEN", "super-secret")
    monkeypatch.setattr(dataset_cli, "RealHubClient", lambda: FakeHub(rows()))
    assert dataset_cli.main(["inspect", "owner/korean", "--revision", REQUESTED]) == 0
    captured = capsys.readouterr()
    assert '"columns"' in captured.out
    assert '"stable_id"' in captured.out
    assert "super-secret" not in captured.out + captured.err


def test_cli_reports_config_errors_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "bad.json"
    manifest.write_text("{}", encoding="utf-8")
    assert dataset_cli.main(["validate", str(manifest)]) == 2
    assert "dataset error:" in capsys.readouterr().err


def content_config() -> dict[str, object]:
    """A source without an ID column: identity has to come from the content itself."""
    config = config_data()
    config.update(sample_id=None, writer_id=None)
    return config


def test_missing_id_column_yields_stable_content_identity() -> None:
    materialized = adapter(content_config()).materialize()
    first, second = materialized.samples
    expected = content_sample_id(IMAGE_BYTES, "학생의 문재점\n그대로")
    assert first.source.identity_method == "content-digest"
    assert first.source.original_sample_id == expected
    assert first.sample_id == f"hf:owner/korean@{RESOLVED}:{expected}"
    assert CONTENT_IDENTITY_NOTE in first.provenance.notes
    assert second.source.original_sample_id != expected


def test_content_identity_ignores_row_order_but_tracks_content() -> None:
    reversed_rows = list(reversed(rows()))
    forward = adapter(content_config()).materialize().samples
    backward = adapter(content_config(), reversed_rows).materialize().samples
    assert {sample.sample_id for sample in forward} == {sample.sample_id for sample in backward}
    edited = dict(rows()[0])
    edited["transcript"] = "학생의 문제점"
    changed = adapter(content_config(), [edited]).materialize().samples[0]
    assert changed.sample_id != forward[0].sample_id


def test_selected_rows_fetch_only_pinned_positions() -> None:
    expected = content_sample_id(IMAGE_BYTES, "둘째 답안")
    config = content_config()
    config["selected_rows"] = [{"sample_id": expected, "file": "data/train-0.parquet", "row": 1}]
    hub = FakeHub(rows())
    materialized = HuggingFaceDatasetAdapter(
        AdapterConfig.model_validate_json(json.dumps(config)), hub, token=None
    ).materialize()
    assert hub.requested_locations == [("data/train-0.parquet", 1)]
    assert [sample.source.original_sample_id for sample in materialized.samples] == [expected]


def test_moved_or_edited_row_fails_instead_of_silently_substituting() -> None:
    config = content_config()
    config["selected_rows"] = [
        {
            "sample_id": content_sample_id(IMAGE_BYTES, "둘째 답안"),
            "file": "data/train-0.parquet",
            "row": 0,
        }
    ]
    with pytest.raises(AdapterError, match="no longer holds"):
        HuggingFaceDatasetAdapter(
            AdapterConfig.model_validate_json(json.dumps(config)), FakeHub(rows()), token=None
        ).materialize()


@pytest.mark.parametrize(
    ("selected_rows", "error"),
    [
        ([], "must not be empty"),
        (
            [
                {"sample_id": "a", "file": "f.parquet", "row": 0},
                {"sample_id": "a", "file": "f.parquet", "row": 1},
            ],
            "duplicate sample IDs",
        ),
        (
            [
                {"sample_id": "a", "file": "f.parquet", "row": 0},
                {"sample_id": "b", "file": "f.parquet", "row": 0},
            ],
            "duplicate row positions",
        ),
        ([{"sample_id": "a", "file": "f.parquet", "row": -1}], "greater than or equal to 0"),
    ],
)
def test_selected_rows_reject_ambiguous_pins(selected_rows: object, error: str) -> None:
    config = content_config()
    config["selected_rows"] = selected_rows
    with pytest.raises(ValidationError, match=error):
        AdapterConfig.model_validate_json(json.dumps(config))


def test_selection_forms_are_mutually_exclusive() -> None:
    config = config_data()
    config["selected_original_sample_ids"] = ["page-001"]
    config["selected_rows"] = [{"sample_id": "page-001", "file": "f.parquet", "row": 0}]
    with pytest.raises(ValidationError, match="one selection form"):
        AdapterConfig.model_validate_json(json.dumps(config))


def test_cli_resolves_a_bare_name_to_a_frozen_manifest_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = content_config()
    config["selected_rows"] = [
        {
            "sample_id": content_sample_id(IMAGE_BYTES, "둘째 답안"),
            "file": "data/train-0.parquet",
            "row": 1,
        }
    ]
    (tmp_path / "smoke-test.adapter.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(dataset_cli, "RealHubClient", lambda: FakeHub(rows()))
    assert dataset_cli.main(["validate", "smoke-test", "--manifest-dir", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["samples"] == 1
    # No frozen canonical manifest beside it means the pin check is reported as not run.
    assert result["frozen_manifest_checked"] is False


@pytest.mark.parametrize(
    "example",
    ["examples/huggingface-adapter.json", "examples/huggingface-adapter-content-id.json"],
)
def test_documented_examples_parse_strictly_and_carry_no_token(example: str) -> None:
    text = Path(example).read_text(encoding="utf-8")
    config = AdapterConfig.model_validate_json(text)
    assert len(config.revision) == 40
    assert "token" not in text.lower()
