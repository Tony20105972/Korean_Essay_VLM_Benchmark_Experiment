"""Deterministic command interface for Hugging Face dataset adapter operations."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from nonsulfit.providers.huggingface import (
    AdapterConfig,
    AdapterError,
    HuggingFaceDatasetAdapter,
    RealHubClient,
    verify_resolved_revision,
)


def _config(path: str) -> AdapterConfig:
    return AdapterConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dataset")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser(
        "inspect", help="inspect a pinned HF dataset without exposing credentials"
    )
    inspect.add_argument("dataset")
    inspect.add_argument("--revision", required=True)
    inspect.add_argument("--split")
    for name in ("fetch", "validate"):
        command = commands.add_parser(name, help=f"{name} a Hugging Face adapter manifest")
        command.add_argument("manifest")
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
        sample_id="__unmapped__",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            config = _inspect_config(args)
            description = RealHubClient().inspect(config.dataset, config.revision, args.split, None)
            verify_resolved_revision(config.revision, description.resolved_revision)
            print(description.model_dump_json(indent=2))
            return 0
        adapter = HuggingFaceDatasetAdapter(_config(args.manifest), RealHubClient())
        if args.command == "validate":
            adapter.inspect()
            materialized = adapter.materialize()
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "samples": len(materialized.samples),
                        "resolved_revision": materialized.resolved_revision,
                    }
                )
            )
            return 0
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
    except (AdapterError, ValidationError, OSError, ValueError) as error:
        print(f"dataset error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
