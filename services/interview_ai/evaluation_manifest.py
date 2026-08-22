"""The strict deployable evaluation-set manifest (consolidated B5).

One shared parser/projector for build and runtime: the builder writes the
manifest through :func:`manifest_bytes` and re-parses it with
:func:`parse_manifest`; release resolution (and therefore process boot)
parses the deployed copy with the SAME function. There is no second
parser to drift.

The manifest is a CLOSED contract for the initial extraction:

- top-level keys are exactly ``schema``, ``responsible_version``,
  ``projection_version``, ``total_source_count``,
  ``evaluation_set_hash``, ``files``;
- every entry carries exactly ``path``, ``sha256``, ``category``;
- paths are unique, normalized, repository-relative, traversal-free,
  ASCII, and canonically sorted;
- exactly 42 sources: 2 golden documents and 40 parity fixtures;
- the recorded aggregate hash must equal the recomputed projection
  digest — it is verified, never trusted.

Any duplicate, absolute, parent-traversal, noncanonical, malformed,
extra, missing, substituted, or reordered entry is a
:class:`EvaluationManifestError`.
"""

import json

from services.interview_ai.constants import CONTRACTS_VERSION
from services.interview_ai.identity import (
    canonical_json_bytes,
    is_full_sha256,
    sha256_hex,
)

SCHEMA = "interview-evaluation-set@2"
PROJECTION_VERSION = "peerslate.interview.evalset.v3"

TOP_LEVEL_KEYS = frozenset({
    "schema", "responsible_version", "projection_version",
    "total_source_count", "evaluation_set_hash", "files",
})
ENTRY_KEYS = frozenset({"path", "sha256", "category"})
CATEGORIES = ("golden_document", "parity_fixture")

# The initial extraction's frozen source population.
EXPECTED_TOTAL_SOURCES = 42
EXPECTED_CATEGORY_COUNTS = {"golden_document": 2, "parity_fixture": 40}


class EvaluationManifestError(ValueError):
    """The evaluation-set manifest violates the closed contract."""


def _validate_path(path):
    if not isinstance(path, str) or not path:
        raise EvaluationManifestError("entry path must be a non-empty string")
    if not path.isascii():
        raise EvaluationManifestError("entry path must be ASCII: %r" % path)
    if "\\" in path:
        raise EvaluationManifestError(
            "entry path must use forward slashes: %r" % path
        )
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        raise EvaluationManifestError(
            "entry path must be repository-relative: %r" % path
        )
    if path != path.strip():
        raise EvaluationManifestError(
            "entry path carries surrounding whitespace: %r" % path
        )
    segments = path.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise EvaluationManifestError(
            "entry path must be normalized and traversal-free: %r" % path
        )


def project_entries(entries):
    """The canonical identity projection over validated entries."""
    return {
        "digest_domain": PROJECTION_VERSION,
        "files": [
            {
                "path": entry["path"],
                "sha256": entry["sha256"],
                "category": entry["category"],
            }
            for entry in entries
        ],
    }


def aggregate_hash(entries):
    """SHA-256 of the canonical projection of the (already sorted) entries."""
    return sha256_hex(canonical_json_bytes(project_entries(entries)))


def parse_manifest(manifest_data):
    """Validate one parsed manifest object; return (entries, aggregate).

    ``manifest_data`` is the result of ``json.loads`` on the manifest
    file. Every closure rule above is enforced; the returned aggregate is
    RECOMPUTED and already proven equal to the recorded field.
    """
    if not isinstance(manifest_data, dict):
        raise EvaluationManifestError("manifest must be a JSON object")
    if set(manifest_data) != TOP_LEVEL_KEYS:
        raise EvaluationManifestError(
            "manifest top-level keys must be exactly %s"
            % sorted(TOP_LEVEL_KEYS)
        )
    if manifest_data["schema"] != SCHEMA:
        raise EvaluationManifestError("unsupported manifest schema")
    if manifest_data["responsible_version"] != CONTRACTS_VERSION:
        raise EvaluationManifestError(
            "manifest responsible_version does not match the running "
            "contracts version"
        )
    if manifest_data["projection_version"] != PROJECTION_VERSION:
        raise EvaluationManifestError(
            "manifest projection_version does not match the canonical "
            "projection"
        )

    entries = manifest_data["files"]
    if not isinstance(entries, list) or not entries:
        raise EvaluationManifestError("manifest files must be a non-empty list")

    seen_paths = set()
    category_counts = {category: 0 for category in CATEGORIES}
    previous_path = None
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise EvaluationManifestError(
                "every entry carries exactly path, sha256, and category"
            )
        _validate_path(entry["path"])
        if entry["path"] in seen_paths:
            raise EvaluationManifestError(
                "duplicate entry path: %r" % entry["path"]
            )
        seen_paths.add(entry["path"])
        if previous_path is not None and entry["path"] <= previous_path:
            raise EvaluationManifestError(
                "entries must be canonically sorted: %r after %r"
                % (entry["path"], previous_path)
            )
        previous_path = entry["path"]
        if not is_full_sha256(entry["sha256"]):
            raise EvaluationManifestError(
                "entry sha256 must be 64 lowercase hex characters: %r"
                % entry["path"]
            )
        if entry["category"] not in CATEGORIES:
            raise EvaluationManifestError(
                "entry category outside the closed enum: %r"
                % entry["category"]
            )
        category_counts[entry["category"]] += 1

    total = manifest_data["total_source_count"]
    if not isinstance(total, int) or isinstance(total, bool):
        raise EvaluationManifestError("total_source_count must be an integer")
    if total != len(entries):
        raise EvaluationManifestError(
            "total_source_count does not match the entry count"
        )
    if total != EXPECTED_TOTAL_SOURCES:
        raise EvaluationManifestError(
            "the initial extraction requires exactly %d sources"
            % EXPECTED_TOTAL_SOURCES
        )
    if category_counts != EXPECTED_CATEGORY_COUNTS:
        raise EvaluationManifestError(
            "the initial extraction requires exactly %d golden documents "
            "and %d parity fixtures" % (
                EXPECTED_CATEGORY_COUNTS["golden_document"],
                EXPECTED_CATEGORY_COUNTS["parity_fixture"],
            )
        )

    recomputed = aggregate_hash(entries)
    recorded = manifest_data["evaluation_set_hash"]
    if not is_full_sha256(recorded) or recorded != recomputed:
        raise EvaluationManifestError(
            "recorded evaluation_set_hash does not match the recomputed "
            "projection digest"
        )
    return entries, recomputed


def parse_manifest_bytes(raw_bytes):
    """Parse and validate the manifest from its exact file bytes."""
    try:
        manifest_data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvaluationManifestError("manifest is not valid JSON") from error
    return parse_manifest(manifest_data)


def manifest_bytes(entries):
    """Serialize the canonical manifest for the validated, sorted entries.

    The builder writes exactly these bytes; they re-parse through
    :func:`parse_manifest_bytes`, so the written manifest can never
    violate the contract it is checked against.
    """
    manifest = {
        "schema": SCHEMA,
        "responsible_version": CONTRACTS_VERSION,
        "projection_version": PROJECTION_VERSION,
        "total_source_count": len(entries),
        "evaluation_set_hash": aggregate_hash(entries),
        "files": project_entries(entries)["files"],
    }
    raw = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8")
    parse_manifest_bytes(raw)
    return raw
