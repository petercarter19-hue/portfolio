"""Identity computation for Interview AI bundles and release sets.

Implements the §2 digest framing rules as frozen in 01_FROZEN_CONTRACTS.md
§2 (`identity-framing@1`). Every canonical identity is a full 64-hex
SHA-256; short prefixes are display labels only and are never compared.
"""

import hashlib
import json

BUNDLE_DOMAIN = b"peerslate.interview.bundle.v1\x00"
# The evaluation-set projection domain lives with its shared parser in
# services/interview_ai/evaluation_manifest.py (consolidated B5).
RUNTIME_CORE_DOMAIN = "peerslate.interview.runtime-core.v1"
CANDIDATE_DOMAIN = "peerslate.interview.candidate.v1"
RELEASE_DOMAIN = "peerslate.interview.release.v1"

# The four identity files of every bundle, in the fixed hashing order.
BUNDLE_FILE_ORDER = (
    "constitution.md",
    "instruction.md",
    "schema.json",
    "provider.json",
)


def _reject_floats(value):
    if isinstance(value, float):
        raise ValueError("identity payloads must not contain floats")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("identity payload keys must be strings")
            _reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)


def canonical_json_bytes(value):
    """UTF-8 canonical JSON: sorted keys, no insignificant whitespace.

    The RFC 8785 subset sufficient for these payloads; floats are rejected
    rather than canonicalized, so no number-form ambiguity can exist.
    """
    _reject_floats(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _framed_entry(name, content):
    name_bytes = name.encode("utf-8")
    return (
        len(name_bytes).to_bytes(8, "big")
        + name_bytes
        + len(content).to_bytes(8, "big")
        + content
    )


def bundle_content_sha256(file_bytes_by_name):
    """Full SHA-256 over domain-framed bundle file bytes, fixed order."""
    missing = set(BUNDLE_FILE_ORDER) - set(file_bytes_by_name)
    if missing:
        raise ValueError("bundle is missing identity files: %s" % sorted(missing))
    digest = hashlib.sha256()
    digest.update(BUNDLE_DOMAIN)
    for name in BUNDLE_FILE_ORDER:
        digest.update(_framed_entry(name, file_bytes_by_name[name]))
    return digest.hexdigest()


# Consolidated correction B5: the evaluation-set identity moved to the
# shared strict parser/projector in
# services/interview_ai/evaluation_manifest.py — one implementation for
# build and runtime, never two.


def sha256_hex(content):
    return hashlib.sha256(content).hexdigest()


def runtime_core_digest(manifest_entries, external_artifacts=()):
    """SHA-256 over the canonical guarded dependency manifest.

    ``manifest_entries`` is a list of {"path": str, "sha256": str} for
    mutable repository dependencies; ``external_artifacts`` is a list of
    {"name", "coordinate", "artifacts": [{"filename", "sha256"} ...]} for
    immutable external implementations (§2: a pinned version alone never
    satisfies closure — the full implementation digest enters the
    manifest). Both are canonicalized deterministically.
    """
    entries = sorted(
        (
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in manifest_entries
        ),
        key=lambda entry: entry["path"],
    )
    externals = sorted(
        (
            {
                "name": artifact["name"],
                "coordinate": artifact["coordinate"],
                "artifacts": sorted(
                    (
                        {"filename": item["filename"], "sha256": item["sha256"]}
                        for item in artifact["artifacts"]
                    ),
                    key=lambda item: item["filename"],
                ),
            }
            for artifact in external_artifacts
        ),
        key=lambda artifact: artifact["name"],
    )
    payload = {
        "digest_domain": RUNTIME_CORE_DOMAIN,
        "entries": entries,
        "external_artifacts": externals,
    }
    return sha256_hex(canonical_json_bytes(payload))


def candidate_system_digest(
    runtime_core, bundle_slots, guardian_set_version, contracts_version,
    evaluation_set,
):
    """§2 candidate digest over the ordered structured object.

    ``bundle_slots`` is an ordered list of
    {"specialist": str, "bundle_content_sha256": str} in bundle slot order;
    labels are excluded from identity by construction.
    """
    payload = {
        "digest_domain": CANDIDATE_DOMAIN,
        "runtime_core_digest": runtime_core,
        "bundles": [
            {
                "specialist": slot["specialist"],
                "bundle_content_sha256": slot["bundle_content_sha256"],
            }
            for slot in bundle_slots
        ],
        "guardian_set_version": guardian_set_version,
        "contracts_version": contracts_version,
        "evaluation_set_hash": evaluation_set,
    }
    return sha256_hex(canonical_json_bytes(payload))


def release_set_id(
    candidate_digest, accepted_run_digests, threshold_set_id,
    threshold_set_version,
):
    payload = {
        "digest_domain": RELEASE_DOMAIN,
        "candidate_system_digest": candidate_digest,
        "accepted_run_digests": list(accepted_run_digests),
        "threshold_set_id": threshold_set_id,
        "threshold_set_version": threshold_set_version,
    }
    return sha256_hex(canonical_json_bytes(payload))


def is_full_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
