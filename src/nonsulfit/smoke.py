"""Deterministic smoke-subset selection and ground-truth inspection.

This module is pure: it takes already-scanned rows and materialized canonical samples
and returns a selection, findings and manifest.  It performs no I/O and knows nothing
about Hugging Face, so the freeze is reproducible and testable without the network.
Findings describe the source; they never rewrite it.  Verbatim GT is preserved as-is
per docs/ai/perception/verbatim-contract.md.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from nonsulfit.contracts import (
    ArtifactReference,
    CanonicalDatasetSample,
    DatasetManifest,
    ManifestSample,
    Provenance,
    SelectionMetadata,
)

NonEmpty = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Count = Annotated[int, Field(ge=0)]

SCAN_SCHEMA = "smoke-scan/v1"
LengthBand = Literal["short", "medium", "long"]
LENGTH_BANDS: tuple[LengthBand, ...] = ("short", "medium", "long")
SHORT_MAX = 50
MEDIUM_MAX = 200
UNLABELED = "unlabeled"
# Every length band must appear even where the source distribution is lopsided; a smoke
# set that silently drops a band stops exercising the shape it was meant to cover.
BAND_FLOOR = 10

_HANJA_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))
# Conjoining jamo signal a decomposed or broken syllable; compatibility jamo are ordinary
# standalone letters that handwriting legitimately contains.  Reporting them as one
# "unicode anomaly" would misread normal source text as corruption.
_CONJOINING_JAMO_RANGES = ((0x1100, 0x11FF), (0xA960, 0xA97F), (0xD7B0, 0xD7FF))
_COMPATIBILITY_JAMO_RANGES = ((0x3130, 0x318F),)
_EMOJI_RANGES = ((0x2600, 0x27BF), (0x1F300, 0x1FAFF), (0xFE0F, 0xFE0F))


class ScanRow(BaseModel):
    """One scanned row: light-weight columns plus the physical position that found it."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    file: NonEmpty
    row: Count
    row_group: Count
    transcription: str
    label: str


class ScanIndex(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    schema_version: Literal["smoke-scan/v1"]
    dataset: NonEmpty
    revision: NonEmpty
    split: NonEmpty
    files: tuple[NonEmpty, ...]
    scanned_row_groups: Count | None
    rows: tuple[ScanRow, ...]


class TextFindings(BaseModel):
    """What the source transcription contains; no value here authorizes changing it."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    empty: bool
    not_utf8_encodable: bool
    control_characters: bool
    nfc_mismatch: bool
    conjoining_jamo: bool
    compatibility_jamo: bool
    hanja: bool
    latin: bool
    emoji: bool
    digits: bool

    @property
    def anomalous(self) -> bool:
        """Only these make a sample unusable; the rest are properties worth recording."""
        return (
            self.empty
            or self.not_utf8_encodable
            or self.control_characters
            or self.nfc_mismatch
            or self.conjoining_jamo
        )


def _in_ranges(code: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(low <= code <= high for low, high in ranges)


def inspect_text(text: str) -> TextFindings:
    """Report source properties verbatim; normalization is never applied to the source."""
    try:
        text.encode("utf-8")
        encodable = True
    except UnicodeEncodeError:
        encodable = False
    codes = [ord(character) for character in text]
    return TextFindings(
        empty=not text.strip(),
        not_utf8_encodable=not encodable,
        control_characters=any(
            unicodedata.category(character) == "Cc" and character not in "\n\t"
            for character in text
        ),
        nfc_mismatch=unicodedata.normalize("NFC", text) != text,
        conjoining_jamo=any(_in_ranges(code, _CONJOINING_JAMO_RANGES) for code in codes),
        compatibility_jamo=any(_in_ranges(code, _COMPATIBILITY_JAMO_RANGES) for code in codes),
        hanja=any(_in_ranges(code, _HANJA_RANGES) for code in codes),
        latin=any(character.isascii() and character.isalpha() for character in text),
        emoji=any(
            _in_ranges(code, _EMOJI_RANGES) or unicodedata.category(chr(code)) == "So"
            for code in codes
        ),
        digits=any(character.isdigit() for character in text),
    )


def length_band(text: str) -> LengthBand:
    if len(text) < SHORT_MAX:
        return "short"
    return "medium" if len(text) < MEDIUM_MAX else "long"


def label_bucket(label: str) -> str:
    """An absent label is reported as such rather than invented or silently merged."""
    return label.strip() or UNLABELED


def allocate[Key](sizes: Mapping[Key, int], total: int, floor: int = 0) -> dict[Key, int]:
    """Largest-remainder allocation with a per-bucket floor, capped by availability."""
    result: dict[Key, int] = dict.fromkeys(sizes, 0)
    available = [key for key in sizes if sizes[key] > 0]
    total = min(total, sum(sizes[key] for key in available))
    if not available or total <= 0:
        return result
    order = sorted(available, key=lambda key: (-sizes[key], str(key)))
    for key in order:
        taken = sum(result.values())
        if taken >= total:
            break
        result[key] = min(floor, sizes[key], total - taken)
    remaining = total - sum(result.values())
    headroom = {key: sizes[key] - result[key] for key in available}
    free = sum(headroom.values())
    if remaining <= 0 or free <= 0:
        return result
    exact = {key: remaining * headroom[key] / free for key in available}
    extra = {key: min(int(exact[key]), headroom[key]) for key in available}
    leftover = remaining - sum(extra.values())
    ranked = sorted(available, key=lambda key: (-(exact[key] % 1), -sizes[key], str(key)))
    while leftover > 0:
        progressed = False
        for key in ranked:
            if leftover <= 0:
                break
            if extra[key] < headroom[key]:
                extra[key] += 1
                leftover -= 1
                progressed = True
        if not progressed:
            break
    for key in available:
        result[key] += extra[key]
    return result


def spread(items: Sequence[ScanRow], count: int) -> list[ScanRow]:
    """Take evenly spaced members so a bucket is not sampled from one contiguous block."""
    if count <= 0:
        return []
    if count >= len(items):
        return list(items)
    step = len(items) / count
    return [items[int(index * step)] for index in range(count)]


def choose(
    rows: Sequence[ScanRow], total: int, row_groups: frozenset[int] | None = None
) -> tuple[ScanRow, ...]:
    """Stratify by transcription length, then by label within each band, deterministically.

    Length bands carry a floor because the source is dominated by one band; labels are
    proportional because the P.Paper / T.Tablet ratio is a property worth reproducing.
    """
    pool = sorted(
        (row for row in rows if row_groups is None or row.row_group in row_groups),
        key=lambda row: (row.file, row.row),
    )
    banded: dict[LengthBand, list[ScanRow]] = {band: [] for band in LENGTH_BANDS}
    for row in pool:
        banded[length_band(row.transcription)].append(row)
    band_quota = allocate({band: len(banded[band]) for band in LENGTH_BANDS}, total, BAND_FLOOR)
    selected: list[ScanRow] = []
    for band in LENGTH_BANDS:
        by_label: dict[str, list[ScanRow]] = {}
        for row in banded[band]:
            by_label.setdefault(label_bucket(row.label), []).append(row)
        label_quota = allocate(
            {label: len(members) for label, members in sorted(by_label.items())},
            band_quota[band],
            floor=1,
        )
        for label in sorted(label_quota):
            selected.extend(spread(by_label[label], label_quota[label]))
    return tuple(sorted(selected, key=lambda row: (row.file, row.row)))


def distribution(rows: Sequence[ScanRow]) -> dict[str, dict[str, int]]:
    return {
        "label": dict(sorted(Counter(label_bucket(row.label) for row in rows).items())),
        "length_band": {
            band: sum(1 for row in rows if length_band(row.transcription) == band)
            for band in LENGTH_BANDS
        },
    }


def findings_summary(texts: Sequence[str]) -> dict[str, int]:
    findings = [inspect_text(text) for text in texts]
    counts = {
        name: sum(1 for finding in findings if getattr(finding, name))
        for name in TextFindings.model_fields
    }
    counts["duplicate_transcriptions"] = len(texts) - len(set(texts))
    return counts


def build_manifest(
    samples: Sequence[CanonicalDatasetSample],
    *,
    manifest_id: str,
    manifest_version: str,
    dataset: str,
    revision: str,
    split: str,
    method: str,
    rationale: str,
    change_reason: str,
    selected_at: datetime,
) -> DatasetManifest:
    """Freeze the subset as G0 smoke: a benchmark set, explicitly not Golden."""
    return DatasetManifest(
        schema_version="dataset-manifest/v1",
        manifest_id=manifest_id,
        manifest_version=manifest_version,
        dataset_identifier=dataset,
        dataset_revision=revision,
        split=split,
        source_origin="external",
        tier="G0",
        role="benchmark",
        golden=False,
        selected_samples=tuple(
            ManifestSample(
                sample_id=sample.sample_id,
                image=sample.input,
                gt_revision=sample.ground_truth.revision,
                annotation_revision=None,
                writer_id=sample.metadata.writer_id if sample.metadata else None,
                eligibility=sample.ground_truth.eligibility,
                sample_reference=ArtifactReference(
                    artifact_id=sample.sample_id, version=sample.ground_truth.revision
                ),
            )
            for sample in samples
        ),
        selection_metadata=SelectionMetadata(
            method=method,
            seed=None,
            rationale=rationale,
            selected_at=selected_at.isoformat(),
            change_reason=change_reason,
            lineage=(ArtifactReference(artifact_id=f"hf:{dataset}", version=revision),),
            exposure_history=None,
            permission_reference=None,
            integrity_review_reference=None,
            writer_disjoint="unavailable",
        ),
        provenance=Provenance(
            producer="nonsulfit-smoke-selection",
            producer_version="v1",
            upstream=(ArtifactReference(artifact_id=f"hf:{dataset}", version=revision),),
            notes=(
                "external smoke dataset; not Golden and not a holdout",
                "writer identity unavailable upstream; no writer-generalization claim",
                "handwriting difficulty unavailable upstream",
            ),
        ),
    )
