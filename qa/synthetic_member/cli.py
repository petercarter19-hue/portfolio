"""Local plan and sanitized evidence recorder for synthetic-member QA."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

from .contracts import (
    JOURNEYS,
    ContractError,
    create_manifest,
    record_cleanup,
    record_journey,
    validate_manifest,
)


class _SafeArgumentParser(argparse.ArgumentParser):
    """Refuse malformed input without reflecting supplied values."""

    def error(self, message: str) -> None:
        del message
        self.exit(2, "refused: invalid command syntax\n")


def _require_external_manifest_path(path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        raise ContractError("manifest path could not be resolved") from exc
    if resolved.is_relative_to(repository_root):
        raise ContractError("manifest must be stored outside the repository")


def _read_manifest(path: Path) -> dict[str, Any]:
    _require_external_manifest_path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("manifest could not be read as JSON") from exc
    validate_manifest(value)
    return value


def _manifest_json(manifest: dict[str, Any]) -> str:
    validate_manifest(manifest)
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _create_manifest_file(path: Path, manifest: dict[str, Any]) -> None:
    _require_external_manifest_path(path)
    payload = _manifest_json(manifest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    except FileExistsError as exc:
        raise ContractError("manifest destination already exists") from exc
    except OSError as exc:
        raise ContractError("manifest could not be created") from exc


def _replace_manifest(path: Path, manifest: dict[str, Any]) -> None:
    _require_external_manifest_path(path)
    payload = _manifest_json(manifest)
    temporary_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_name = stream.name
            stream.write(payload)
        os.replace(temporary_name, path)
        temporary_name = None
    except OSError as exc:
        raise ContractError("manifest could not be updated") from exc
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def _build_parser() -> argparse.ArgumentParser:
    parser = _SafeArgumentParser(
        description=(
            "Generate and validate sanitized two-member QA evidence. "
            "This tool never opens a browser or handles identity/session material."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="print the canonical journey matrix")
    plan.add_argument("--json", action="store_true", help="emit JSON")

    initialize = subparsers.add_parser("init", help="create a pending manifest")
    initialize.add_argument("--output", required=True, type=Path)
    initialize.add_argument("--run-id", required=True)
    initialize.add_argument("--source-commit", required=True)
    initialize.add_argument("--mode", required=True)
    initialize.add_argument("--browser", required=True)
    initialize.add_argument("--browser-version", required=True)
    initialize.add_argument("--surface-code", default="foundation")
    initialize.add_argument("--release-id", default="not_recorded")

    journey = subparsers.add_parser("record-journey", help="record one outcome")
    journey.add_argument("--manifest", required=True, type=Path)
    journey.add_argument("--journey", required=True)
    journey.add_argument("--status", required=True)
    journey.add_argument("--note-code", default="none")

    cleanup = subparsers.add_parser("record-cleanup", help="record count-only cleanup")
    cleanup.add_argument("--manifest", required=True, type=Path)
    cleanup.add_argument("--pre-run-baseline", required=True)
    cleanup.add_argument("--created-member-a", type=int, required=True)
    cleanup.add_argument("--created-member-b", type=int, required=True)
    cleanup.add_argument("--residue-member-a", type=int, required=True)
    cleanup.add_argument("--residue-member-b", type=int, required=True)
    cleanup.add_argument("--retention-disclosure", required=True)
    for name in (
        "client-a-destroyed",
        "client-b-destroyed",
        "signed-out-control-destroyed",
        "switch-client-destroyed",
    ):
        cleanup.add_argument(f"--{name}", required=True)

    validate = subparsers.add_parser("validate", help="validate retained evidence")
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--final", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            records = [journey.record() for journey in JOURNEYS]
            if args.json:
                print(json.dumps(records, indent=2, sort_keys=True))
            else:
                for record in records:
                    print(
                        f"{record['journey_id']}: {record['expected_outcome']} "
                        f"[{record['client']}]"
                    )
            return 0

        if args.command == "init":
            manifest = create_manifest(
                run_id=args.run_id,
                source_commit=args.source_commit,
                mode=args.mode,
                browser=args.browser,
                browser_version=args.browser_version,
                surface_code=args.surface_code,
                release_id=args.release_id,
            )
            _create_manifest_file(args.output, manifest)
            print(json.dumps({"result": "created"}))
            return 0

        manifest = _read_manifest(args.manifest)
        if args.command == "record-journey":
            updated = record_journey(
                manifest,
                journey_id=args.journey,
                status=args.status,
                note_code=args.note_code,
            )
            _replace_manifest(args.manifest, updated)
            print(json.dumps({"result": updated["result"], "journey": args.journey}))
            return 0

        if args.command == "record-cleanup":
            updated = record_cleanup(
                manifest,
                pre_run_baseline=args.pre_run_baseline,
                created_member_a=args.created_member_a,
                created_member_b=args.created_member_b,
                residue_member_a=args.residue_member_a,
                residue_member_b=args.residue_member_b,
                retention_disclosure=args.retention_disclosure,
                client_a_destroyed=args.client_a_destroyed,
                client_b_destroyed=args.client_b_destroyed,
                signed_out_control_destroyed=args.signed_out_control_destroyed,
                switch_client_destroyed=args.switch_client_destroyed,
            )
            _replace_manifest(args.manifest, updated)
            print(
                json.dumps(
                    {
                        "cleanup": updated["cleanup"]["status"],
                        "result": updated["result"],
                    }
                )
            )
            return 0

        validate_manifest(manifest, final=args.final)
        print(json.dumps({"result": manifest["result"], "validation": "pass"}))
        return 0
    except ContractError as exc:
        parser.exit(2, f"refused: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
