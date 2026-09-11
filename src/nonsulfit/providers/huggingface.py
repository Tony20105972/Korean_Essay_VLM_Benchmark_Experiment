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
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from nonsulfit.contracts import CanonicalDatasetSample

NonEmpty = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
CommitPrefix = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{7,64}$")]


class AdapterError(ValueError):
    """A source row or remote dataset cannot satisfy the canonical boundary."""


class AdapterConfig(BaseModel):
    """Strict, portable adapter manifest; selected IDs are upstream IDs, never row offsets."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    schema_version: Literal["huggingface-adapter/v1"]
    dataset: NonEmpty
    revision: CommitPrefix
    split: NonEmpty
    image: NonEmpty
    transcription: NonEmpty
    sample_id: NonEmpty
    writer_id: NonEmpty | None = None
    selected_original_sample_ids: tuple[NonEmpty, ...] | None = None

    @model_validator(mode="after")
    def unique_selection(self) -> AdapterConfig:
        if self.selected_original_sample_ids and (
            len(self.selected_original_sample_ids) != len(set(self.selected_original_sample_ids))
        ):
            raise ValueError("selected_original_sample_ids contains duplicates")
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


def _required_columns(config: AdapterConfig) -> set[str]:
    return {config.image, config.transcription, config.sample_id} | (
        {config.writer_id} if config.writer_id else set()
    )


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
        selected = set(self.config.selected_original_sample_ids or ())
        samples: list[CanonicalDatasetSample] = []
        seen_ids: set[str] = set()
        found_ids: set[str] = set()
        for row in self.client.rows(self.config.dataset, resolved, self.config.split, self.token):
            missing = _required_columns(self.config) - set(row)
            if missing:
                raise AdapterError(f"mapped columns missing from row: {', '.join(sorted(missing))}")
            original_id = _identifier(row[self.config.sample_id], self.config.sample_id)
            if selected and original_id not in selected:
                continue
            if original_id in found_ids:
                raise AdapterError(f"duplicate upstream sample ID: {original_id}")
            found_ids.add(original_id)
            samples.append(self._convert(row, original_id, resolved))
            if samples[-1].sample_id in seen_ids:
                raise AdapterError(f"duplicate canonical sample ID: {samples[-1].sample_id}")
            seen_ids.add(samples[-1].sample_id)
        missing_selected = selected - found_ids
        if missing_selected:
            raise AdapterError(
                f"selected sample IDs not found: {', '.join(sorted(missing_selected))}"
            )
        return MaterializedDataset(tuple(samples), resolved)

    def _verify_revision(self, resolved: str) -> None:
        verify_resolved_revision(self.config.revision, resolved)

    def _convert(
        self, row: Mapping[str, object], original_id: str, resolved_revision: str
    ) -> CanonicalDatasetSample:
        image, image_kind = _image_bytes(row[self.config.image])
        text = _text(row[self.config.transcription], self.config.transcription)
        writer = None
        if self.config.writer_id is not None:
            writer = _identifier(row[self.config.writer_id], self.config.writer_id)
        digest = sha256(image).hexdigest()
        canonical_id = f"hf:{self.config.dataset}@{resolved_revision}:{original_id}"
        provenance_notes: tuple[str, ...] = (
            () if writer else ("writer-disjoint guarantee unavailable",)
        )
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
                "identity_method": "upstream-id",
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
                "notes": list(provenance_notes),
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
        splits = tuple(builder.info.splits.keys()) if builder.info.splits else ()
        chosen_split = split or (splits[0] if splits else None)
        preview: dict[str, str] = {}
        if chosen_split is not None:
            dataset_view = builder.as_dataset(split=chosen_split)
            if len(dataset_view):
                preview = {key: type(value).__name__ for key, value in dataset_view[0].items()}
        return DatasetDescription(
            dataset=dataset,
            requested_revision=revision,
            resolved_revision=resolved,
            splits=splits,
            columns=columns,
            feature_types={key: str(value) for key, value in (features or {}).items()},
            preview=preview,
            likely_image_fields=tuple(
                key
                for key, value in (features or {}).items()
                if "image" in str(value).lower() or key.lower() in {"image", "img", "picture"}
            ),
            likely_transcription_fields=tuple(
                key
                for key in columns
                if key.lower() in {"text", "label", "transcription", "transcript"}
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
