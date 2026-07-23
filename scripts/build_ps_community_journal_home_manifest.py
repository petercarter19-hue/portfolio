"""Build and validate the combined 98-capture milestone evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = Path(
    os.environ.get(
        "PEERSLATE_MILESTONE_EVIDENCE_ROOT",
        ROOT / "artifacts" / "ps-community-journal-home-milestone-001",
    )
)
SOURCE_DIRECTORIES = {
    "community": ROOT / "artifacts" / "ps-community-tabs-001",
    "journal": ROOT / "artifacts" / "ps-journal-001-j1-frontend",
    "owner_home": ROOT / "artifacts" / "ps-home-frontend-001" / "screenshots",
}
EXPECTED_COUNTS = {"community": 15, "journal": 62, "owner_home": 21}
SOURCE_SHAS = {
    "community": "a8c04964a5a363d47a56829da01c9a5bfefe3653",
    "journal": "099e8e1582c05d3e13fd54dacfeb03700f90ae09",
    "owner_home": "f8c882633f6e442a4f661b67f8d3c799a66a1989",
}


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _comparison(candidate: Image.Image, source: Image.Image, package: str, filename: str):
    candidate_rgb = candidate.convert("RGB")
    source_rgb = source.convert("RGB")
    dimensions_equal = candidate_rgb.size == source_rgb.size
    explanation = {
        "community": (
            "Fresh integrated Chromium PNG compared with the approved source raster. "
            "Dark Feed deltas include the audited normal-text contrast correction; all "
            "other differences remain disclosed with semantic route/state assertions."
        ),
        "journal": (
            "Fresh integrated Chromium PNG compared with the approved J1 source raster. "
            "The 200% proof intentionally changes from CSS body zoom to a true 720-CSS-"
            "pixel reflow equivalent; every other raster delta is recorded without "
            "normalization or concealment."
        ),
        "owner_home": (
            "Fresh Mock-backed owner-home.v1 Chromium PNG compared with the approved "
            "source state. The 200% proof intentionally replaces the invalid widened "
            "page-scale canvas with a real 720-CSS-pixel reflow capture."
        ),
    }[package]
    if not dimensions_equal:
        return {
            "decoded_pixel_identical": False,
            "dimensions_equal": False,
            "changed_rgb_pixel_count": "size_mismatch",
            "changed_rgb_bbox": None,
            "mean_absolute_rgb_channel_error": None,
            "rmse_rgb_channel_error": None,
            "max_channel_delta": None,
            "pixels_above_delta_8": None,
            "pixels_above_delta_16": None,
            "pixels_above_delta_32": None,
            "percent_pixels_above_delta_8": None,
            "percent_pixels_above_delta_16": None,
            "percent_pixels_above_delta_32": None,
            "raster_explanation": explanation + f" Dimension mismatch is explicit for {filename}.",
        }

    difference = ImageChops.difference(candidate_rgb, source_rgb)
    changed = above_8 = above_16 = above_32 = 0
    absolute_total = square_total = max_delta = 0
    for red, green, blue in difference.getdata():
        pixel_max = max(red, green, blue)
        changed += pixel_max > 0
        above_8 += pixel_max > 8
        above_16 += pixel_max > 16
        above_32 += pixel_max > 32
        absolute_total += red + green + blue
        square_total += red * red + green * green + blue * blue
        max_delta = max(max_delta, pixel_max)
    pixel_count = candidate_rgb.width * candidate_rgb.height
    channel_count = pixel_count * 3
    bbox = difference.getbbox()
    return {
        "decoded_pixel_identical": changed == 0,
        "dimensions_equal": True,
        "changed_rgb_pixel_count": changed,
        "changed_rgb_bbox": list(bbox) if bbox else None,
        "mean_absolute_rgb_channel_error": absolute_total / channel_count,
        "rmse_rgb_channel_error": math.sqrt(square_total / channel_count),
        "max_channel_delta": max_delta,
        "pixels_above_delta_8": above_8,
        "pixels_above_delta_16": above_16,
        "pixels_above_delta_32": above_32,
        "percent_pixels_above_delta_8": above_8 * 100 / pixel_count,
        "percent_pixels_above_delta_16": above_16 * 100 / pixel_count,
        "percent_pixels_above_delta_32": above_32 * 100 / pixel_count,
        "raster_explanation": explanation,
    }


def _load_log(package: str):
    path = EVIDENCE_ROOT / package / "capture-log.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    captures = payload["captures"]
    if len(captures) != EXPECTED_COUNTS[package]:
        raise RuntimeError(f"{package} capture log has {len(captures)} entries")
    return {item["file"]: item for item in captures}


def _record(package: str, path: Path, log: dict, rendered_product_commit: str):
    source_path = SOURCE_DIRECTORIES[package] / path.name
    if not source_path.is_file():
        raise RuntimeError(f"missing approved source capture: {source_path}")
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"not a PNG stream: {path}")
    source_payload = source_path.read_bytes()
    with Image.open(path) as candidate_image, Image.open(source_path) as source_image:
        if candidate_image.format != "PNG" or source_image.format != "PNG":
            raise RuntimeError(f"non-PNG decoded format for {path.name}")
        candidate_rgba = candidate_image.convert("RGBA").tobytes()
        source_rgba = source_image.convert("RGBA").tobytes()
        comparison = _comparison(candidate_image, source_image, package, path.name)
        dimensions = f"{candidate_image.width}x{candidate_image.height}"
        source_dimensions = f"{source_image.width}x{source_image.height}"

    route = log.get("route") or log.get("path") or "/app"
    theme_value = log.get("theme")
    if not theme_value:
        theme_value = "dark" if log.get("dark") else "light"
    record = {
        "file": path.name,
        "route": route,
        "state": log["state"],
        "viewport": log["viewport"],
        "theme": theme_value,
        "file_type": "png",
        "dimensions": dimensions,
        "file_sha256": _sha(payload),
        "decoded_rgba_sha256": _sha(candidate_rgba),
        "rendered_product_commit": rendered_product_commit,
        "source_dimensions": source_dimensions,
        "source_file_sha256": _sha(source_payload),
        "source_decoded_rgba_sha256": _sha(source_rgba),
        "source_pixel_comparison": comparison,
    }
    for field in (
        "region",
        "fixture_state",
        "capture_method",
        "browser_zoom_equivalent_percent",
        "physical_viewport_equivalent",
        "semantic_assertions",
        "reflow",
        "java_script_enabled",
        "reduced_motion",
        "forced_colors",
    ):
        if field in log:
            record[field] = log[field]
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rendered-product-commit", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.rendered_product_commit):
        raise SystemExit("rendered product commit must be a lowercase 40-character Git SHA")

    manifest = {
        "package": "PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001",
        "rendered_product_commit": args.rendered_product_commit,
        "frozen_base": "e1272220f539f41810698855341b9399b14ebd73",
        "capture_method": (
            "Fresh local Flask + installed Chrome/Playwright capture from the frozen "
            "product SHA; process-local test fixtures only; no database or SQL."
        ),
        "candidate_note": (
            "The evidence-only commit intentionally does not self-reference. Every "
            "raster is bound to this frozen rendered-product SHA and exact hashes."
        ),
        "comparison_policy": (
            "Every candidate has decoded candidate/source hashes and a per-file source "
            "comparison. Dimension-changing zoom corrections are explicit, never coerced."
        ),
        "packages": {},
        "comparison_artifacts": [],
    }
    owner_reconciliation = {
        "rendered_product_commit": args.rendered_product_commit,
        "source_commit": SOURCE_SHAS["owner_home"],
        "files": [],
    }

    for package, expected_count in EXPECTED_COUNTS.items():
        directory = EVIDENCE_ROOT / package
        logs = _load_log(package)
        paths = sorted(directory.glob("*.png"))
        if len(paths) != expected_count or {path.name for path in paths} != set(logs):
            raise RuntimeError(f"{package} PNG/log closure mismatch")
        captures = [
            _record(package, path, logs[path.name], args.rendered_product_commit)
            for path in paths
        ]
        by_hash = defaultdict(list)
        for capture in captures:
            by_hash[capture["file_sha256"]].append(capture["file"])
        duplicate_groups = sorted(
            sorted(files) for files in by_hash.values() if len(files) > 1
        )
        manifest["packages"][package] = {
            "frozen_source_sha": SOURCE_SHAS[package],
            "capture_count": len(captures),
            "unique_exact_hash_count": len(by_hash),
            "permitted_exact_duplicate_groups": duplicate_groups,
            "captures": captures,
        }
        if package == "owner_home":
            owner_reconciliation["files"] = [
                {
                    "file": capture["file"],
                    "candidate_dimensions": capture["dimensions"],
                    "source_dimensions": capture["source_dimensions"],
                    "candidate_file_sha256": capture["file_sha256"],
                    "source_file_sha256": capture["source_file_sha256"],
                    "candidate_decoded_rgba_sha256": capture["decoded_rgba_sha256"],
                    "source_decoded_rgba_sha256": capture["source_decoded_rgba_sha256"],
                    **capture["source_pixel_comparison"],
                    "fixture_state_explanation": (
                        "State-specific process-local Mock-backed owner-home.v1 fixture; "
                        "no database or SQL execution."
                    ),
                }
                for capture in captures
            ]

    (EVIDENCE_ROOT / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (EVIDENCE_ROOT / "OWNER_HOME_EVIDENCE_RECONCILIATION.json").write_text(
        json.dumps(owner_reconciliation, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
