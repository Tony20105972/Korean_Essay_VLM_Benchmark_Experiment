"""Hugging Face-only adapter from mapped rows to canonical dataset samples."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from os import environ
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, cast

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from nonsulfit.contracts import CanonicalDatasetSample
from nonsulfit.providers import parquet

NonEmpty = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
CommitPrefix = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{7,64}$")]
RowIndex = Annotated[int, Field(ge=0)]

CONTENT_IDENTITY_NOTE = "sample identity derived from image and GT content digest"
CONTENT_ID_PREFIX = "sha256-"
CONTENT_ID_DOMAIN = b"nonsulfit/hf-content-id/v1"


class AdapterError(ValueError):
    """A source row or remote dataset cannot satisfy the canonical boundary."""


class RowLocation(BaseModel):
    """A verified fetch hint: where a known sample sat, not what makes it that sample."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    sample_id: NonEmpty
    file: NonEmpty
    row: RowIndex


class AdapterConfig(BaseModel):
    """Strict, portable adapter manifest; selected IDs are stable IDs, never row offsets."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    schema_version: Literal["huggingface-adapter/v1"]
    dataset: NonEmpty
    revision: CommitPrefix
    split: NonEmpty
    image: NonEmpty
    transcription: NonEmpty
    sample_id: NonEmpty | None = None
    writer_id: NonEmpty | None = None
    selected_original_sample_ids: tuple[NonEmpty, ...] | None = None
    selected_rows: tuple[RowLocation, ...] | None = None

    @property
    def identity_method(self) -> Literal["upstream-id", "content-digest"]:
        """Datasets without an ID column are identified by content, never by row order."""
        return "upstream-id" if self.sample_id else "content-digest"

    @model_validator(mode="after")
    def unique_selection(self) -> AdapterConfig:
        if self.selected_original_sample_ids and (
            len(self.selected_original_sample_ids) != len(set(self.selected_original_sample_ids))
        ):
            raise ValueError("selected_original_sample_ids contains duplicates")
        if self.selected_original_sample_ids and self.selected_rows:
            raise ValueError("selected_rows already carries its sample IDs; use one selection form")
        if self.selected_rows is not None:
            if not self.selected_rows:
                raise ValueError("selected_rows must not be empty")
            ids = [location.sample_id for location in self.selected_rows]
            positions = [(location.file, location.row) for location in self.selected_rows]
            if len(set(ids)) != len(ids):
                raise ValueError("selected_rows contains duplicate sample IDs")
            if len(set(positions)) != len(positions):
                raise ValueError("selected_rows contains duplicate row positions")
        return self


class DatasetDescription(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    dataset: NonEmpty
    requested_revision: CommitPrefix
    resolved_revision: NonEmpty
    splits: tuple[NonEmpty, ...]
    columns: tuple[NonEmpty, ...]
    feature_types: dict[NonEmpty, NonEmpty]
    preview: dict[str, str]
    preview_source: Literal["parquet-row-group", "unavailable"] = "unavailable"
    split_num_examples: dict[NonEmpty, RowIndex] = {}
    data_file_count: RowIndex = 0
    likely_image_fields: tuple[NonEmpty, ...] = ()
    likely_transcription_fields: tuple[NonEmpty, ...] = ()
    likely_sample_id_fields: tuple[NonEmpty, ...] = ()
    likely_writer_id_fields: tuple[NonEmpty, ...] = ()


class HubClient(Protocol):
    """Small injectable seam keeps network tests outside the deterministic test suite."""

    def resolve_revision(self, dataset: str, revision: str, token: str | None) -> str: ...

    def inspect(
        self, dataset: str, revision: str, split: str | None, token: str | None
    ) -> DatasetDescription: ...

    def rows(
        self, dataset: str, revision: str, split: str, token: str | None
    ) -> Iterable[Mapping[str, object]]: ...

    def rows_at(
        self,
        dataset: str,
        revision: str,
        locations: Sequence[tuple[str, int]],
        token: str | None,
    ) -> Iterable[Mapping[str, object]]: ...


@dataclass(frozen=True)
class MaterializedDataset:
    samples: tuple[CanonicalDatasetSample, ...]
    resolved_revision: str


def hf_token() -> str | None:
    """Read authentication only from the process environment; never serialize it."""
    return environ.get("HF_TOKEN") or None


def _commit_matches(requested: str, resolved: str) -> bool:
    return (
        len(resolved) == 40
        and all(char in "0123456789abcdef" for char in resolved.lower())
        and resolved.lower().startswith(requested.lower())
    )


def verify_resolved_revision(requested: str, resolved: str) -> None:
    if not _commit_matches(requested, resolved):
        raise AdapterError("HF revision did not resolve to the requested immutable commit")


def content_sample_id(image: bytes, transcription: str) -> str:
    """Identify a row by what it contains, so upstream reordering cannot rename samples."""
    digest = sha256(
        CONTENT_ID_DOMAIN + b"\x00" + sha256(image).digest() + b"\x00" + transcription.encode()
    ).hexdigest()
    return f"{CONTENT_ID_PREFIX}{digest[:32]}"


def _required_columns(config: AdapterConfig) -> set[str]:
    mapped = {config.image, config.transcription}
    if config.sample_id:
        mapped.add(config.sample_id)
    if config.writer_id:
        mapped.add(config.writer_id)
    return mapped


def _image_bytes(value: object) -> tuple[bytes, str]:
    if isinstance(value, bytes) and value:
        _validate_image(value)
        return value, "inline-bytes"
    if isinstance(value, Mapping):
        raw = value.get("bytes")
        if isinstance(raw, bytes) and raw:
            _validate_image(raw)
            return raw, "inline-bytes"
        path = value.get("path")
        if isinstance(path, str) and path:
            try:
                image = Path(path).read_bytes()
                _validate_image(image)
                return image, f"file://{Path(path).resolve()}"
            except OSError as error:
                raise AdapterError(f"image path is unreadable: {path}") from error
    raise AdapterError("image must be nonempty bytes or a mapping with readable bytes/path")


def _validate_image(raw: bytes) -> None:
    try:
        with Image.open(BytesIO(raw)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise AdapterError("image bytes are not readable as an image") from error


def _text(value: object, column: str) -> str:
    if not isinstance(value, str):
        raise AdapterError(f"{column} must be a text string")
    if "\r" in value:
        raise AdapterError(
            f"{column} contains CR; preserve source and create a versioned LF conversion"
        )
    return value


def _identifier(value: object, column: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"{column} must be a nonempty stable string ID")
    return value


class HuggingFaceDatasetAdapter:
    """The sole HF-aware transformation layer; it returns only canonical contracts."""

    def __init__(self, config: AdapterConfig, client: HubClient, token: str | None = None) -> None:
        self.config = config
        self.client = client
        self.token = hf_token() if token is None else token

    def inspect(self) -> DatasetDescription:
        description = self.client.inspect(
            self.config.dataset, self.config.revision, self.config.split, self.token
        )
        self._verify_revision(description.resolved_revision)
        missing = _required_columns(self.config) - set(description.columns)
        if missing:
            raise AdapterError(f"mapped columns missing from dataset: {', '.join(sorted(missing))}")
        return description

    def materialize(self) -> MaterializedDataset:
        resolved = self.client.resolve_revision(
            self.config.dataset, self.config.revision, self.token
        )
        self._verify_revision(resolved)
        locations = self.config.selected_rows
        samples = (
            self._from_locations(locations, resolved) if locations else self._from_split(resolved)
        )
        return MaterializedDataset(samples, resolved)

    def _from_locations(
        self, locations: Sequence[RowLocation], resolved: str
    ) -> tuple[CanonicalDatasetSample, ...]:
        """Read only the pinned rows, then prove each still holds the sample it promised."""
        positions = tuple((location.file, location.row) for location in locations)
        rows = self.client.rows_at(self.config.dataset, resolved, positions, self.token)
        samples: list[CanonicalDatasetSample] = []
        for location, row in zip(locations, rows, strict=True):
            self._check_columns(row)
            sample = self.convert_row(row, resolved)
            if sample.source.original_sample_id != location.sample_id:
                raise AdapterError(
                    f"{location.file} row {location.row} no longer holds {location.sample_id}; "
                    "upstream rows moved or their content changed"
                )
            samples.append(sample)
        return tuple(samples)

    def _from_split(self, resolved: str) -> tuple[CanonicalDatasetSample, ...]:
        selected = set(self.config.selected_original_sample_ids or ())
        samples: list[CanonicalDatasetSample] = []
        found_ids: set[str] = set()
        for row in self.client.rows(self.config.dataset, resolved, self.config.split, self.token):
            self._check_columns(row)
            mapped_id = self._mapped_identifier(row)
            if selected and mapped_id is not None and mapped_id not in selected:
                continue
            sample = self.convert_row(row, resolved)
            original_id = str(sample.source.original_sample_id)
            if selected and original_id not in selected:
                continue
            if original_id in found_ids:
                raise AdapterError(f"duplicate upstream sample ID: {original_id}")
            found_ids.add(original_id)
            samples.append(sample)
        missing_selected = selected - found_ids
        if missing_selected:
            raise AdapterError(
                f"selected sample IDs not found: {', '.join(sorted(missing_selected))}"
            )
        return tuple(samples)

    def _check_columns(self, row: Mapping[str, object]) -> None:
        missing = _required_columns(self.config) - set(row)
        if missing:
            raise AdapterError(f"mapped columns missing from row: {', '.join(sorted(missing))}")

    def _mapped_identifier(self, row: Mapping[str, object]) -> str | None:
        """Content identity needs the converted payload, so only mapped IDs are known early."""
        if self.config.sample_id is None:
            return None
        return _identifier(row[self.config.sample_id], self.config.sample_id)

    def _verify_revision(self, resolved: str) -> None:
        verify_resolved_revision(self.config.revision, resolved)

    def convert_row(
        self, row: Mapping[str, object], resolved_revision: str
    ) -> CanonicalDatasetSample:
        """Convert one mapped row into a canonical sample; also used by smoke selection."""
        image, image_kind = _image_bytes(row[self.config.image])
        text = _text(row[self.config.transcription], self.config.transcription)
        mapped_id = self._mapped_identifier(row)
        original_id = mapped_id if mapped_id is not None else content_sample_id(image, text)
        writer = None
        if self.config.writer_id is not None:
            writer = _identifier(row[self.config.writer_id], self.config.writer_id)
        digest = sha256(image).hexdigest()
        canonical_id = f"hf:{self.config.dataset}@{resolved_revision}:{original_id}"
        notes: list[str] = []
        if not writer:
            notes.append("writer-disjoint guarantee unavailable")
        if mapped_id is None:
            notes.append(CONTENT_IDENTITY_NOTE)
        payload: dict[str, Any] = {
            "schema_version": "dataset-sample/v1",
            "sample_id": canonical_id,
            "source": {
                "provider": "huggingface",
                "source_type": "external",
                "dataset_identifier": self.config.dataset,
                "revision": resolved_revision,
                "split": self.config.split,
                "original_sample_id": original_id,
                "identity_method": self.config.identity_method,
            },
            "input": {
                "artifact_id": f"sha256:{digest}",
                "uri": f"hf://datasets/{self.config.dataset}@{resolved_revision}/{self.config.split}/{original_id}/{self.config.image}",
                "sha256": digest,
                "page_id": original_id,
            },
            "ground_truth": {
                "transcription": text,
                "revision": f"hf:{resolved_revision}:{self.config.transcription}",
                "eligibility": {"text_eligible": True, "reason": None},
            },
            "metadata": {"writer_id": writer},
            "provenance": {
                "producer": "huggingface-adapter",
                "producer_version": "v1",
                "upstream": [
                    {"artifact_id": f"hf:{self.config.dataset}", "version": resolved_revision},
                    {"artifact_id": f"hf-image:{digest}", "version": image_kind},
                ],
                "notes": notes,
            },
        }
        # The canonical contract defines JSON as its interchange boundary.  Keeping this
        # conversion explicit avoids loosening its strict Python-object semantics.
        return CanonicalDatasetSample.model_validate_json(json.dumps(payload, ensure_ascii=False))


class RealHubClient:
    """Lazy imports keep deterministic tests and canonical consumers independent of HF SDKs."""

    def resolve_revision(self, dataset: str, revision: str, token: str | None) -> str:
        from huggingface_hub import HfApi

        try:
            return str(HfApi().dataset_info(dataset, revision=revision, token=token).sha)
        except Exception as error:
            raise AdapterError(
                f"unable to resolve pinned HF revision for {dataset}: {type(error).__name__}"
            ) from error

    def inspect(
        self, dataset: str, revision: str, split: str | None, token: str | None
    ) -> DatasetDescription:
        from datasets import load_dataset_builder  # type: ignore[import-untyped]

        resolved = self.resolve_revision(dataset, revision, token)
        try:
            builder = load_dataset_builder(dataset, revision=resolved, token=token)
        except Exception as error:
            raise AdapterError(
                f"unable to inspect pinned HF dataset {dataset}: {type(error).__name__}"
            ) from error
        features = builder.info.features
        columns = tuple(features.keys()) if features else ()
        split_sizes = {
            name: int(info.num_examples) for name, info in (builder.info.splits or {}).items()
        }
        splits = tuple(split_sizes)
        chosen_split = split or (splits[0] if splits else None)
        preview, preview_source, file_count = self._preview(dataset, resolved, chosen_split, token)
        return DatasetDescription(
            dataset=dataset,
            requested_revision=revision,
            resolved_revision=resolved,
            splits=splits,
            columns=columns,
            feature_types={key: str(value) for key, value in (features or {}).items()},
            preview=preview,
            preview_source=preview_source,
            split_num_examples=split_sizes,
            data_file_count=file_count,
            likely_image_fields=tuple(
                key
                for key, value in (features or {}).items()
                if "image" in str(value).lower() or key.lower() in {"image", "img", "picture"}
            ),
            likely_transcription_fields=tuple(
                key
                for key in columns
                if key.lower() in {"text", "label", "transcription", "transcript", "output"}
            ),
            likely_sample_id_fields=tuple(
                key for key in columns if key.lower() in {"id", "sample_id", "sampleid", "uuid"}
            ),
            likely_writer_id_fields=tuple(
                key
                for key in columns
                if key.lower() in {"writer", "writer_id", "author", "author_id"}
            ),
        )

    def _preview(
        self, dataset: str, resolved: str, split: str | None, token: str | None
    ) -> tuple[dict[str, str], Literal["parquet-row-group", "unavailable"], int]:
        """Preview from footer metadata and one text row group; image payloads stay remote."""
        if split is None:
            return {}, "unavailable", 0
        try:
            files = parquet.list_data_files(dataset, resolved, split, token)
            return (
                parquet.preview(dataset, resolved, files[0], token),
                "parquet-row-group",
                len(files),
            )
        except parquet.ParquetAccessError:
            return {}, "unavailable", 0

    def rows(
        self, dataset: str, revision: str, split: str, token: str | None
    ) -> Iterable[Mapping[str, object]]:
        from datasets import Image, load_dataset

        try:
            dataset_view = load_dataset(dataset, revision=revision, split=split, token=token)
        except Exception as error:
            raise AdapterError(
                f"unable to fetch pinned HF dataset {dataset}: {type(error).__name__}"
            ) from error
        image_columns = [
            name for name, feature in dataset_view.features.items() if isinstance(feature, Image)
        ]
        for column in image_columns:
            dataset_view = dataset_view.cast_column(column, Image(decode=False))
        return cast(Sequence[Mapping[str, object]], dataset_view)

    def rows_at(
        self,
        dataset: str,
        revision: str,
        locations: Sequence[tuple[str, int]],
        token: str | None,
    ) -> Iterable[Mapping[str, object]]:
        """Fetch pinned rows by row group so a smoke subset never downloads a whole split."""
        try:
            for _file, _row, values in parquet.read_locations(dataset, revision, locations, token):
                yield values
        except parquet.ParquetAccessError as error:
            raise AdapterError(str(error)) from error
