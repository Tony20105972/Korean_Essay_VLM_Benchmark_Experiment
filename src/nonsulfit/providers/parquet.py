"""Bounded parquet reads for pinned HF datasets; never materializes a whole split.

The Hub serves large datasets as auto-converted parquet shards. Reading a 42 GB split
to select two hundred smoke samples is not acceptable, so this layer uses column
pruning for scans and row-group targeting for materialization. It stays HF-aware and
returns plain Python values; canonical conversion belongs to the adapter.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

BINARY_PREVIEW = "dict"


class ParquetAccessError(RuntimeError):
    """A pinned parquet layout cannot be listed or read as requested."""


@dataclass(frozen=True)
class ScannedRow:
    """One row of the light-weight columns, addressed by its physical position."""

    file: str
    row: int
    row_group: int
    values: Mapping[str, object]


def _filesystem(revision: str, token: str | None) -> Any:
    from huggingface_hub import HfFileSystem

    return HfFileSystem(revision=revision, token=token)


def _root(dataset: str, revision: str) -> str:
    return f"datasets/{dataset}@{revision}"


def _matches_split(relative_path: str, split: str) -> bool:
    parts = relative_path.split("/")
    name = parts[-1]
    return name.startswith(f"{split}-") or name == f"{split}.parquet" or split in parts[:-1]


def list_data_files(dataset: str, revision: str, split: str, token: str | None) -> tuple[str, ...]:
    """Return repo-relative parquet paths of a split, in stable lexicographic order."""
    filesystem = _filesystem(revision, token)
    root = _root(dataset, revision)
    try:
        paths = filesystem.glob(f"{root}/**/*.parquet")
    except Exception as error:  # Hub failures surface as adapter errors without internals
        raise ParquetAccessError(
            f"unable to list parquet files for {dataset}: {type(error).__name__}"
        ) from error
    relative = sorted(str(path)[len(root) + 1 :] for path in paths)
    matched = tuple(path for path in relative if _matches_split(path, split))
    if not matched:
        raise ParquetAccessError(f"no parquet files for split {split!r} in {dataset}")
    return matched


def _open(filesystem: Any, dataset: str, revision: str, file: str) -> Any:
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    try:
        return pq.ParquetFile(filesystem.open(f"{_root(dataset, revision)}/{file}", "rb"))
    except Exception as error:  # Hub failures surface as adapter errors without internals
        raise ParquetAccessError(f"unable to open {file}: {type(error).__name__}") from error


def _is_heavy(field_type: Any) -> bool:
    """Binary payloads (and structs carrying them) are excluded from light-weight reads."""
    import pyarrow as pa

    if pa.types.is_binary(field_type) or pa.types.is_large_binary(field_type):
        return True
    if pa.types.is_struct(field_type):
        return any(_is_heavy(field_type.field(i).type) for i in range(field_type.num_fields))
    return pa.types.is_list(field_type) and _is_heavy(field_type.value_type)


def light_columns(dataset: str, revision: str, file: str, token: str | None) -> tuple[str, ...]:
    """Columns that can be scanned without transferring image payloads."""
    parquet = _open(_filesystem(revision, token), dataset, revision, file)
    return tuple(field.name for field in parquet.schema_arrow if not _is_heavy(field.type))


def scan(
    dataset: str,
    revision: str,
    files: Sequence[str],
    columns: Sequence[str],
    token: str | None,
    row_groups: int | None = None,
) -> Iterator[ScannedRow]:
    """Stream selected light-weight columns, optionally limited to the first row groups."""
    filesystem = _filesystem(revision, token)
    for file in files:
        parquet = _open(filesystem, dataset, revision, file)
        limit = parquet.metadata.num_row_groups if row_groups is None else row_groups
        offset = 0
        for group in range(min(limit, parquet.metadata.num_row_groups)):
            table = parquet.read_row_group(group, columns=list(columns))
            block = table.to_pylist()
            for index, values in enumerate(block):
                yield ScannedRow(file=file, row=offset + index, row_group=group, values=values)
            offset += len(block)


def _row_group_of(parquet: Any, row: int) -> tuple[int, int]:
    """Map an absolute row index to (row group, offset) using footer metadata only."""
    offset = 0
    for group in range(parquet.metadata.num_row_groups):
        size = parquet.metadata.row_group(group).num_rows
        if row < offset + size:
            return group, row - offset
        offset += size
    raise ParquetAccessError(f"row {row} is beyond the end of the file")


def read_locations(
    dataset: str,
    revision: str,
    locations: Sequence[tuple[str, int]],
    token: str | None,
) -> Iterator[tuple[str, int, Mapping[str, object]]]:
    """Read only the row groups that contain the requested rows, in the given order."""
    filesystem = _filesystem(revision, token)
    wanted: dict[str, list[int]] = {}
    for file, row in locations:
        wanted.setdefault(file, []).append(row)
    resolved: dict[tuple[str, int], Mapping[str, object]] = {}
    for file, rows in wanted.items():
        parquet = _open(filesystem, dataset, revision, file)
        groups: dict[int, list[tuple[int, int]]] = {}
        for row in rows:
            group, offset = _row_group_of(parquet, row)
            groups.setdefault(group, []).append((row, offset))
        for group, members in sorted(groups.items()):
            table = parquet.read_row_group(group)
            block = table.to_pylist()
            for row, offset in members:
                resolved[(file, row)] = block[offset]
    for file, row in locations:
        yield file, row, resolved[(file, row)]


def preview(dataset: str, revision: str, file: str, token: str | None) -> dict[str, str]:
    """Type preview of the first row; binary payload types are reported, never transferred."""
    parquet = _open(_filesystem(revision, token), dataset, revision, file)
    fields = list(parquet.schema_arrow)
    light = [field.name for field in fields if not _is_heavy(field.type)]
    values: dict[str, object] = {}
    if light and parquet.metadata.num_row_groups:
        table = parquet.read_row_group(0, columns=light)
        if table.num_rows:
            values = table.slice(0, 1).to_pylist()[0]
    return {
        field.name: type(values[field.name]).__name__ if field.name in values else BINARY_PREVIEW
        for field in fields
    }
