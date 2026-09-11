"""Deterministic command interface for Hugging Face dataset adapter operations."""

from __future__ import annotations

import argparse
import json
import sys
from base64 import b64encode
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from nonsulfit import smoke
from nonsulfit.contracts import CanonicalDatasetSample, DatasetManifest
from nonsulfit.providers import parquet
from nonsulfit.providers.huggingface import (
    AdapterConfig,
    AdapterError,
    HuggingFaceDatasetAdapter,
    RealHubClient,
    RowLocation,
    hf_token,
    verify_resolved_revision,
)

MANIFEST_DIR = Path("datasets/manifests")
THUMBNAIL = (360, 360)


def _config(path: Path) -> AdapterConfig:
    return AdapterConfig.model_validate_json(path.read_text(encoding="utf-8"))


def _adapter_path(target: str, manifest_dir: Path) -> Path:
    """A bare name refers to a frozen manifest; anything path-like is used verbatim."""
    if target.endswith(".json") or "/" in target:
        return Path(target)
    return manifest_dir / f"{target}.adapter.json"


def _manifest_path(target: str, manifest_dir: Path) -> Path | None:
    if target.endswith(".json") or "/" in target:
        return None
    return manifest_dir / f"{target}.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _evenly(items: Sequence[str], count: int | None) -> tuple[str, ...]:
    """Pick a deterministic spread of shards so a scan is not limited to one region."""
    if count is None or count >= len(items):
        return tuple(items)
    step = len(items) / count
    return tuple(items[int(index * step)] for index in range(count))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataset")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser(
        "inspect", help="inspect a pinned HF dataset without exposing credentials"
    )
    inspect.add_argument("dataset")
    inspect.add_argument("--revision", required=True)
    inspect.add_argument("--split")

    scan = commands.add_parser("scan", help="scan light-weight columns without image payloads")
    scan.add_argument("dataset")
    scan.add_argument("--revision", required=True)
    scan.add_argument("--split", required=True)
    scan.add_argument("--transcription", required=True)
    scan.add_argument("--label", required=True)
    scan.add_argument("--files", type=int, help="scan this many shards, evenly spread")
    scan.add_argument("--row-groups", type=int, help="scan only the first N row groups per shard")
    scan.add_argument("--output", type=Path, required=True)

    select = commands.add_parser("select", help="freeze a deterministic smoke subset")
    select.add_argument("name")
    select.add_argument("--scan", type=Path, required=True)
    select.add_argument("--size", type=int, required=True)
    select.add_argument("--image", required=True)
    select.add_argument("--transcription", required=True)
    select.add_argument("--label", required=True)
    select.add_argument(
        "--pool-row-groups", type=int, help="restrict the selection pool to the first N row groups"
    )
    select.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    select.add_argument("--review-dir", type=Path, required=True)
    select.add_argument("--manifest-version", default="1")
    select.add_argument("--change-reason", default="initial smoke freeze")

    for name in ("fetch", "validate"):
        command = commands.add_parser(name, help=f"{name} an adapter manifest or frozen name")
        command.add_argument("manifest")
        command.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
        if name == "fetch":
            command.add_argument("--output", type=Path)
    return parser


def _inspect_config(args: argparse.Namespace) -> AdapterConfig:
    return AdapterConfig(
        schema_version="huggingface-adapter/v1",
        dataset=args.dataset,
        revision=args.revision,
        split=args.split or "__inspect__",
        image="__unmapped__",
        transcription="__unmapped__",
    )


def run_inspect(args: argparse.Namespace) -> int:
    config = _inspect_config(args)
    description = RealHubClient().inspect(config.dataset, config.revision, args.split, None)
    verify_resolved_revision(config.revision, description.resolved_revision)
    print(description.model_dump_json(indent=2))
    return 0


def run_scan(args: argparse.Namespace) -> int:
    token = hf_token()
    resolved = RealHubClient().resolve_revision(args.dataset, args.revision, token)
    verify_resolved_revision(args.revision, resolved)
    files = _evenly(parquet.list_data_files(args.dataset, resolved, args.split, token), args.files)
    rows = tuple(
        smoke.ScanRow(
            file=scanned.file,
            row=scanned.row,
            row_group=scanned.row_group,
            transcription=str(scanned.values[args.transcription]),
            label=str(scanned.values[args.label]),
        )
        for scanned in parquet.scan(
            args.dataset,
            resolved,
            files,
            (args.transcription, args.label),
            token,
            row_groups=args.row_groups,
        )
    )
    index = smoke.ScanIndex(
        schema_version="smoke-scan/v1",
        dataset=args.dataset,
        revision=resolved,
        split=args.split,
        files=files,
        scanned_row_groups=args.row_groups,
        rows=rows,
    )
    _write(args.output, index.model_dump_json())
    print(
        json.dumps(
            {
                "status": "scanned",
                "files": len(files),
                "rows": len(rows),
                "distribution": smoke.distribution(rows),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _select_config(args: argparse.Namespace, index: smoke.ScanIndex) -> AdapterConfig:
    return AdapterConfig(
        schema_version="huggingface-adapter/v1",
        dataset=index.dataset,
        revision=index.revision,
        split=index.split,
        image=args.image,
        transcription=args.transcription,
    )


def _materialize_chosen(
    adapter: HuggingFaceDatasetAdapter,
    index: smoke.ScanIndex,
    chosen: Sequence[smoke.ScanRow],
) -> tuple[list[tuple[smoke.ScanRow, CanonicalDatasetSample, Mapping[str, object]]], list[str]]:
    """Read only the chosen rows and keep the first sample per image digest."""
    positions = [(row.file, row.row) for row in chosen]
    kept: list[tuple[smoke.ScanRow, CanonicalDatasetSample, Mapping[str, object]]] = []
    digests: set[str] = set()
    dropped: list[str] = []
    raw = parquet.read_locations(index.dataset, index.revision, positions, hf_token())
    for scanned, (_file, _row, values) in zip(chosen, raw, strict=True):
        sample = adapter.convert_row(values, index.revision)
        if sample.ground_truth.transcription != scanned.transcription:
            raise AdapterError(
                f"{scanned.file} row {scanned.row} transcription differs from the scan index; "
                "rescan before freezing"
            )
        if sample.input.sha256 in digests:
            dropped.append(f"{scanned.file}:{scanned.row} duplicate image digest")
            continue
        digests.add(sample.input.sha256)
        kept.append((scanned, sample, values))
    return kept, dropped


def _thumbnail(value: object) -> str:
    raw = value.get("bytes") if isinstance(value, Mapping) else value
    if not isinstance(raw, bytes):
        return ""
    with Image.open(BytesIO(raw)) as image:
        preview = image.convert("RGB")
        preview.thumbnail(THUMBNAIL)
        buffer = BytesIO()
        preview.save(buffer, format="JPEG", quality=60)
    return b64encode(buffer.getvalue()).decode("ascii")


def run_select(args: argparse.Namespace) -> int:
    index = smoke.ScanIndex.model_validate_json(args.scan.read_text(encoding="utf-8"))
    pool_groups = None if args.pool_row_groups is None else frozenset(range(args.pool_row_groups))
    chosen = smoke.choose(index.rows, args.size, pool_groups)
    if not chosen:
        raise AdapterError("selection is empty; widen the scan or the pool")
    adapter = HuggingFaceDatasetAdapter(_select_config(args, index), RealHubClient())
    kept, dropped = _materialize_chosen(adapter, index, chosen)
    samples = [sample for _row, sample, _values in kept]
    manifest = smoke.build_manifest(
        samples,
        manifest_id=args.name,
        manifest_version=args.manifest_version,
        dataset=index.dataset,
        revision=index.revision,
        split=index.split,
        method=(
            "deterministic stratification over transcription length band "
            f"(floor {smoke.BAND_FLOOR}) then label share, evenly spread within each bucket; "
            f"pool = first {args.pool_row_groups} row group(s) of {len(index.files)} scanned shards"
        ),
        rationale=(
            "G0 smoke coverage of media label and transcription length; writer identity and "
            "handwriting difficulty are unavailable upstream and are not claimed"
        ),
        change_reason=args.change_reason,
        selected_at=datetime.now(UTC),
    )
    config = AdapterConfig(
        schema_version="huggingface-adapter/v1",
        dataset=index.dataset,
        revision=index.revision,
        split=index.split,
        image=args.image,
        transcription=args.transcription,
        selected_rows=tuple(
            RowLocation(sample_id=str(sample.source.original_sample_id), file=row.file, row=row.row)
            for row, sample, _values in kept
        ),
    )
    _write(args.manifest_dir / f"{args.name}.json", manifest.model_dump_json(indent=2) + "\n")
    _write(args.manifest_dir / f"{args.name}.adapter.json", config.model_dump_json(indent=2) + "\n")
    report = _report(args.name, index, kept, dropped, args)
    _write(args.manifest_dir / f"{args.name}.report.md", report)
    _write(args.review_dir / "review.md", _review_markdown(args.name, kept))
    _write(args.review_dir / "review.html", _review_html(args, kept))
    print(
        json.dumps(
            {
                "status": "frozen",
                "manifest": str(args.manifest_dir / f"{args.name}.json"),
                "adapter": str(args.manifest_dir / f"{args.name}.adapter.json"),
                "report": str(args.manifest_dir / f"{args.name}.report.md"),
                "review": str(args.review_dir / "review.html"),
                "selected": len(kept),
                "dropped": dropped,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _report(
    name: str,
    index: smoke.ScanIndex,
    kept: Sequence[tuple[smoke.ScanRow, CanonicalDatasetSample, Mapping[str, object]]],
    dropped: Sequence[str],
    args: argparse.Namespace,
) -> str:
    rows = [row for row, _sample, _values in kept]
    texts = [row.transcription for row in rows]
    scanned = smoke.distribution(index.rows)
    selected = smoke.distribution(rows)
    findings = smoke.findings_summary(texts)
    lengths = sorted(len(text) for text in texts)
    lines = [
        f"# {name} — selection report",
        "",
        "> Generated by `./scripts/dataset select`. Ground-truth text is not reproduced here;",
        "> the reviewable copy with transcriptions is written to the review directory.",
        "",
        "## Source",
        "",
        f"- dataset: `{index.dataset}`",
        f"- revision: `{index.revision}`",
        f"- split: `{index.split}`",
        f"- scanned shards: {len(index.files)} of the split",
        f"- scanned rows: {len(index.rows)}",
        f"- selection pool: first {args.pool_row_groups} row group(s) per scanned shard",
        f"- selected: {len(kept)}",
        "",
        "## Distribution",
        "",
        "| Axis | Scanned | Selected |",
        "|---|---|---|",
    ]
    for axis in ("label", "length_band"):
        for key in sorted(set(scanned[axis]) | set(selected[axis])):
            lines.append(
                f"| {axis} `{key}` | {scanned[axis].get(key, 0)} | {selected[axis].get(key, 0)} |"
            )
    lines += [
        "",
        (
            f"- transcription length: min {lengths[0]}, "
            f"median {lengths[len(lengths) // 2]}, max {lengths[-1]}"
        ),
        "",
        "## Ground-truth findings",
        "",
        "Findings describe the source. No transcription was normalized, trimmed or corrected.",
        "",
        "| Finding | Selected samples |",
        "|---|---|",
    ]
    lines += [f"| {key} | {value} |" for key, value in sorted(findings.items())]
    lines += [
        "",
        "## Known limitations",
        "",
        "- Writer identity is unavailable upstream; no writer-disjoint or writer-generalization claim.",
        "- Handwriting difficulty and capture quality are unavailable upstream and are not invented.",
        "- The pool is a documented shard/row-group subset, not a random sample of the full split.",
        "",
    ]
    if dropped:
        lines += ["## Dropped during freeze", ""] + [f"- {item}" for item in dropped] + [""]
    return "\n".join(lines)


def _review_markdown(
    name: str,
    kept: Sequence[tuple[smoke.ScanRow, CanonicalDatasetSample, Mapping[str, object]]],
) -> str:
    lines = [
        f"# {name} — manual review index",
        "",
        "> Contains verbatim ground truth. Per DATA005 this text must not be placed in any",
        "> inference prompt; evaluation reads GT only after inference completes.",
        "",
        "| Sample ID | Location | Label | Length | Ground truth |",
        "|---|---|---|---|---|",
    ]
    for row, sample, _values in kept:
        text = row.transcription.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{sample.source.original_sample_id}` | `{row.file}:{row.row}` | "
            f"{smoke.label_bucket(row.label)} | {len(row.transcription)} | {text} |"
        )
    return "\n".join(lines) + "\n"


def _review_html(
    args: argparse.Namespace,
    kept: Sequence[tuple[smoke.ScanRow, CanonicalDatasetSample, Mapping[str, object]]],
) -> str:
    cards = []
    for row, sample, values in kept:
        thumb = _thumbnail(values[args.image])
        image = f'<img src="data:image/jpeg;base64,{thumb}" alt="">' if thumb else "<p>no image</p>"
        text = row.transcription.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cards.append(
            f"<article><h2>{sample.source.original_sample_id}</h2>"
            f"<p>{row.file}:{row.row} &middot; {smoke.label_bucket(row.label)} &middot; "
            f"{len(row.transcription)} chars</p>{image}<pre>{text}</pre></article>"
        )
    style = (
        "body{font-family:system-ui;margin:2rem;max-width:60rem}"
        "article{border-top:1px solid #ccc;padding:1rem 0}"
        "img{max-width:100%}pre{white-space:pre-wrap;background:#f6f6f6;padding:.5rem}"
    )
    return (
        f"<!doctype html><meta charset=utf-8><title>{args.name} review</title>"
        f"<style>{style}</style><h1>{args.name} manual review</h1>"
        "<p>Verbatim ground truth; do not place in inference prompts (DATA005).</p>"
        + "".join(cards)
    )


def run_validate(args: argparse.Namespace) -> int:
    adapter = HuggingFaceDatasetAdapter(
        _config(_adapter_path(args.manifest, args.manifest_dir)), RealHubClient()
    )
    adapter.inspect()
    materialized = adapter.materialize()
    frozen = _manifest_path(args.manifest, args.manifest_dir)
    checked = False
    if frozen is not None and frozen.exists():
        manifest = DatasetManifest.model_validate_json(frozen.read_text(encoding="utf-8"))
        manifest.validate_samples(materialized.samples)
        checked = True
    print(
        json.dumps(
            {
                "status": "valid",
                "samples": len(materialized.samples),
                "resolved_revision": materialized.resolved_revision,
                "frozen_manifest_checked": checked,
            }
        )
    )
    return 0


def run_fetch(args: argparse.Namespace) -> int:
    adapter = HuggingFaceDatasetAdapter(
        _config(_adapter_path(args.manifest, args.manifest_dir)), RealHubClient()
    )
    materialized = adapter.materialize()
    output = "\n".join(sample.model_dump_json() for sample in materialized.samples)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{output}\n" if output else "", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "fetched",
                    "samples": len(materialized.samples),
                    "output": str(args.output),
                }
            )
        )
    else:
        print(output)
    return 0


COMMANDS = {
    "inspect": run_inspect,
    "scan": run_scan,
    "select": run_select,
    "validate": run_validate,
    "fetch": run_fetch,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except (
        AdapterError,
        parquet.ParquetAccessError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        print(f"dataset error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
