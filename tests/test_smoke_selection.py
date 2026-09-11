"""Fixture-only tests for deterministic smoke selection and ground-truth inspection."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nonsulfit.contracts import (
    ArtifactReference as Reference,
)
from nonsulfit.contracts import (
    CanonicalDatasetSample as Sample,
)
from nonsulfit.contracts import (
    Eligibility,
    GroundTruth,
    ImageReference,
    Provenance,
    Source,
)
from nonsulfit.smoke import (
    BAND_FLOOR,
    allocate,
    build_manifest,
    choose,
    distribution,
    findings_summary,
    inspect_text,
    label_bucket,
    length_band,
)
from nonsulfit.smoke import ScanRow as Row

REVISION = "c" * 40


def row(index: int, *, label: str = "P.Paper", length: int = 100, group: int = 0) -> Row:
    return Row(
        file=f"data/train-{index // 100:05d}.parquet",
        row=index,
        row_group=group,
        transcription="가" * length,
        label=label,
    )


def pool() -> list[Row]:
    rows = [row(i, label="P.Paper", length=100) for i in range(400)]
    rows += [row(400 + i, label="T.Tablet", length=300) for i in range(100)]
    rows += [row(500 + i, label="P.Paper", length=20) for i in range(3)]
    rows += [row(600 + i, label="", length=100, group=1) for i in range(5)]
    return rows


def test_allocation_respects_floors_availability_and_total() -> None:
    result = allocate({"medium": 1684, "long": 711, "short": 5}, 150, BAND_FLOOR)
    assert sum(result.values()) == 150
    assert result["short"] == 5  # floor is capped by what the source actually offers
    assert result["medium"] > result["long"] > result["short"]


def test_allocation_never_exceeds_capacity_or_invents_empty_buckets() -> None:
    result = allocate({"a": 2, "b": 0}, 10, floor=5)
    assert result == {"a": 2, "b": 0}
    assert allocate({}, 10) == {}
    assert allocate({"a": 5}, 0) == {"a": 0}


def test_allocation_is_deterministic_under_ties() -> None:
    sizes = {"a": 10, "b": 10, "c": 10}
    assert allocate(sizes, 7) == allocate(dict(reversed(list(sizes.items()))), 7)


def test_selection_is_deterministic_and_covers_every_length_band() -> None:
    first = choose(pool(), 60, frozenset({0}))
    second = choose(list(reversed(pool())), 60, frozenset({0}))
    assert first == second
    assert len(first) == 60
    bands = distribution(first)["length_band"]
    assert bands["short"] == 3  # all that the pool holds
    assert bands["medium"] > 0 and bands["long"] > 0
    assert distribution(first)["label"]["P.Paper"] > distribution(first)["label"]["T.Tablet"]


def test_selection_honours_the_row_group_pool_and_reports_absent_labels() -> None:
    restricted = choose(pool(), 60, frozenset({0}))
    assert all(row.row_group == 0 for row in restricted)
    widened = choose(pool(), 60, frozenset({0, 1}))
    assert "unlabeled" in distribution(widened)["label"]
    assert label_bucket("  ") == "unlabeled"


def test_selection_spreads_within_a_bucket_instead_of_taking_a_prefix() -> None:
    rows = [row(i, length=100) for i in range(100)]
    picked = [item.row for item in choose(rows, 10, None)]
    assert picked[0] == 0
    assert max(picked) > 50


def test_selection_caps_at_pool_size() -> None:
    assert len(choose(pool()[:20], 500, frozenset({0}))) == 20


@pytest.mark.parametrize(
    ("text", "expected"),
    [("가" * 49, "short"), ("가" * 50, "medium"), ("가" * 199, "medium"), ("가" * 200, "long")],
)
def test_length_bands_follow_documented_thresholds(text: str, expected: str) -> None:
    assert length_band(text) == expected


def test_text_inspection_reports_source_properties_without_changing_them() -> None:
    assert inspect_text("   ").empty
    assert inspect_text("가\x07나").control_characters
    assert not inspect_text("줄\n바꿈\t탭").control_characters
    assert inspect_text("\uac00\u11a8").conjoining_jamo  # syllable + stray conjoining jamo
    assert inspect_text("\u3147\u3142").compatibility_jamo  # ordinary standalone ㅇㅂ
    assert not inspect_text("\u3147\u3142").conjoining_jamo
    assert not inspect_text("\u3147\u3142").anomalous  # standalone letters are not corruption
    assert inspect_text("\u1100\u1161").nfc_mismatch  # NFD form of 가
    assert not inspect_text("\uac00").nfc_mismatch  # composed 가
    assert inspect_text("漢字").hanja
    assert inspect_text("OECD 보고서").latin
    assert inspect_text("좋아요 😀").emoji
    assert inspect_text("2026년").digits
    clean = inspect_text("세계화의 문재점은")
    assert not clean.anomalous
    assert not any(getattr(clean, name) for name in ("hanja", "latin", "emoji", "digits"))


def test_findings_summary_counts_duplicates_across_the_selection() -> None:
    summary = findings_summary(["가나", "가나", "다라", ""])
    assert summary["duplicate_transcriptions"] == 1
    assert summary["empty"] == 1


def sample(index: int) -> Sample:
    digest = f"{index:064x}"
    return Sample(
        schema_version="dataset-sample/v1",
        sample_id=f"hf:owner/set@{REVISION}:sha256-{index:032x}",
        source=Source(
            provider="huggingface",
            source_type="external",
            dataset_identifier="owner/set",
            revision=REVISION,
            split="train",
            original_sample_id=f"sha256-{index:032x}",
            identity_method="content-digest",
        ),
        input=ImageReference(
            artifact_id=f"sha256:{digest}",
            uri=f"hf://datasets/owner/set@{REVISION}/train/{index}/image",
            sha256=digest,
            page_id=f"sha256-{index:032x}",
        ),
        ground_truth=GroundTruth(
            transcription="문재점",
            revision=f"hf:{REVISION}:output",
            eligibility=Eligibility(text_eligible=True, reason=None),
        ),
        provenance=Provenance(
            producer="huggingface-adapter",
            producer_version="v1",
            upstream=(Reference(artifact_id="hf:owner/set", version=REVISION),),
            notes=("writer-disjoint guarantee unavailable",),
        ),
    )


def test_frozen_manifest_is_smoke_tier_and_claims_no_writer_guarantee() -> None:
    samples = [sample(index) for index in range(3)]
    manifest = build_manifest(
        samples,
        manifest_id="smoke-v1",
        manifest_version="1",
        dataset="owner/set",
        revision=REVISION,
        split="train",
        method="deterministic stratification",
        rationale="smoke coverage",
        change_reason="initial smoke freeze",
        selected_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    assert (manifest.tier, manifest.role, manifest.golden) == ("G0", "benchmark", False)
    assert manifest.selection_metadata.writer_disjoint == "unavailable"
    assert manifest.selection_metadata.seed is None
    assert all(pinned.writer_id is None for pinned in manifest.selected_samples)
    manifest.validate_samples(tuple(samples))


def test_frozen_manifest_rejects_a_substituted_subset() -> None:
    samples = [sample(index) for index in range(3)]
    manifest = build_manifest(
        samples,
        manifest_id="smoke-v1",
        manifest_version="1",
        dataset="owner/set",
        revision=REVISION,
        split="train",
        method="deterministic stratification",
        rationale="smoke coverage",
        change_reason="initial smoke freeze",
        selected_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="differs from manifest"):
        manifest.validate_samples((samples[0], samples[1], sample(9)))
