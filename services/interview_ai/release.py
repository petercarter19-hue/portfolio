"""Fail-closed active-release resolution for Interview AI.

Runtime configuration (`PEERSLATE_INTERVIEW_ACTIVE_RELEASE_SET`) selects
among the release sets recorded in
`prompts/interview/control/registry.json`; the registry never selects and
the configuration never defines. Any doubt resolves to *unresolved*, which
the routes answer with the frozen Interview-only 503 and zero provider
dispatch (01_FROZEN_CONTRACTS.md §3).
"""

import json
import logging
from pathlib import Path

from services.interview_ai.bundles import BundleError, load_bundle
from services.interview_ai.fragments import (
    extract_fragments,
    split_fragment_path,
)
from services.interview_ai.constants import (
    BUNDLE_SLOT_ORDER,
    CONTRACTS_VERSION,
    GUARDIAN_SET_VERSION,
    THRESHOLD_SET_ID,
    THRESHOLD_SET_VERSION,
)
from services.interview_ai import evaluation_manifest
from services.interview_ai.identity import (
    candidate_system_digest,
    is_full_sha256,
    release_set_id,
    runtime_core_digest,
    sha256_hex,
)
from services.interview_ai.runtime_lock import (
    load_manifest as load_runtime_lock_manifest,
    verify_runtime_lock,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CONTROL_REGISTRY_PATH = ROOT / "prompts" / "interview" / "control" / "registry.json"
BUNDLE_CATALOG_ROOT = ROOT / "prompts" / "interview" / "bundles"
GUARDED_PATHS_PATH = ROOT / "prompts" / "interview" / "contracts" / "guarded-paths.json"

_UNSET = object()
_cached_resolution = _UNSET
_cached_configured_id = None


class ActiveRelease:
    """One successfully resolved, fully re-verified release set."""

    def __init__(self, release_id, record, bundles):
        self.release_set_id = release_id
        self.record = record
        self.bundles = bundles


def reset_resolution_cache():
    """Test hook simulating a process restart: clears the resolution cache
    AND the frozen boot state (B3), so the next request re-boots from the
    configuration then in effect. Never called at runtime."""
    global _cached_resolution, _cached_configured_id
    _cached_resolution = _UNSET
    _cached_configured_id = None
    from services.interview_ai import boot
    boot.reset_for_tests()


def resolve_active_release(configured_id, root=None):
    """Resolve and verify the configured release set. None when unresolved.

    The result is cached per process per configured id; the first Interview
    AI request pays the verification cost once.
    """
    global _cached_resolution, _cached_configured_id
    if _cached_resolution is not _UNSET and _cached_configured_id == configured_id:
        return _cached_resolution
    resolution = _resolve_uncached(configured_id, root or ROOT)
    _cached_resolution = resolution
    _cached_configured_id = configured_id
    return resolution


def _resolve_uncached(configured_id, root):
    try:
        return _verify(configured_id, root)
    except Exception as error:
        # Content-free by construction: only the normalized class is logged
        # (correction C7 — never a raw Python/SDK class name).
        from services.interview_ai.telemetry import normalize_exception_class
        logger.warning(
            "interview release resolution failed closed: class=%s",
            normalize_exception_class(error),
        )
        return None


def _verify(configured_id, root):
    if not is_full_sha256(configured_id):
        return None
    registry_path = root / "prompts" / "interview" / "control" / "registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1:
        return None

    record = None
    active = registry.get("active_release_set")
    if isinstance(active, dict) and active.get("interview_release_set_id") == configured_id:
        record = active
    else:
        for prior in registry.get("prior_release_sets", []):
            if (
                isinstance(prior, dict)
                and prior.get("interview_release_set_id") == configured_id
            ):
                record = prior
                break
    if record is None:
        return None

    # Correction C2: an internally consistent registry record is not enough
    # — the record must be COMPATIBLE with the running system, or resolution
    # fails closed. A record that recomputes perfectly under
    # `incompatible-guardian@999` is still not this runtime's release.
    if record.get("guardian_set_version") != GUARDIAN_SET_VERSION:
        return None
    if record.get("contracts_version") != CONTRACTS_VERSION:
        return None
    accepted_runs = record.get("accepted_run_digests")
    if record.get("initial_extraction") is True:
        # The reserved parity sentinel is valid only for the initial
        # extraction, which by definition carries zero evaluation runs.
        if accepted_runs != []:
            return None
        if (
            record.get("threshold_set_id") != THRESHOLD_SET_ID
            or record.get("threshold_set_version") != THRESHOLD_SET_VERSION
        ):
            return None
    else:
        # A later behaviour-changing release may never reuse the
        # initial-extraction sentinel and must reference at least one
        # accepted judged run by full digest.
        if record.get("threshold_set_id") == THRESHOLD_SET_ID:
            return None
        if (
            not isinstance(accepted_runs, list)
            or not accepted_runs
            or not all(is_full_sha256(digest) for digest in accepted_runs)
        ):
            return None

    bundle_refs = record.get("bundle_refs")
    if not isinstance(bundle_refs, list) or len(bundle_refs) != len(BUNDLE_SLOT_ORDER):
        return None

    bundles = {}
    slots = []
    for specialist, ref in zip(BUNDLE_SLOT_ORDER, bundle_refs):
        if not isinstance(ref, dict) or ref.get("specialist") != specialist:
            return None
        if not is_full_sha256(ref.get("bundle_content_sha256")):
            return None
        directory = (
            root / "prompts" / "interview" / "bundles" / specialist
            / ref.get("bundle_label", "")
        )
        try:
            bundle = load_bundle(directory, expected_specialist=specialist)
        except (BundleError, OSError, ValueError):
            return None
        if bundle.content_sha256 != ref.get("bundle_content_sha256"):
            return None
        bundles[specialist] = bundle
        slots.append(
            {
                "specialist": specialist,
                "bundle_content_sha256": bundle.content_sha256,
            }
        )

    guarded_path = root / "prompts" / "interview" / "contracts" / "guarded-paths.json"
    manifest = json.loads(guarded_path.read_text(encoding="utf-8"))
    if manifest.get("contracts_version") != CONTRACTS_VERSION:
        return None
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        return None
    fragment_cache = {}
    for entry in entries:
        entry_path = entry.get("path", "")
        base_path, fragment_name = split_fragment_path(entry_path)
        file_path = root / Path(base_path)
        if not file_path.is_file():
            return None
        if fragment_name is None:
            content = file_path.read_bytes()
        else:
            if base_path not in fragment_cache:
                # A deployed app.py whose guarded fragments are missing,
                # duplicated, ambiguous, or stripped of their expected
                # executed symbols fails closed here (B2).
                fragment_cache[base_path] = extract_fragments(
                    file_path.read_bytes()
                )
            fragments_by_name = fragment_cache[base_path]
            if fragment_name not in fragments_by_name:
                return None
            content = fragments_by_name[fragment_name]
        if sha256_hex(content) != entry.get("sha256"):
            return None
    # Immutable external implementations (the locked provider SDK): the
    # recorded artifact digests enter the core digest; their shape must be
    # complete full hashes or resolution fails closed.
    external_artifacts = manifest.get("external_artifacts", [])
    if not isinstance(external_artifacts, list):
        return None
    for artifact in external_artifacts:
        if not isinstance(artifact, dict):
            return None
        if not artifact.get("name") or not artifact.get("coordinate"):
            return None
        items = artifact.get("artifacts")
        if not isinstance(items, list) or not items:
            return None
        for item in items:
            if not isinstance(item, dict) or not item.get("filename"):
                return None
            if not is_full_sha256(item.get("sha256")):
                return None
    computed_core = runtime_core_digest(entries, external_artifacts)
    if computed_core != record.get("runtime_core_digest"):
        return None

    # Correction B3: before an active release becomes ready, the external
    # runtime closure the interpreter ACTUALLY resolves must verify against
    # the locked manifest - missing, duplicated/shadowed, substituted,
    # wrong-version, or byte-different reachable distributions leave
    # Interview service_not_configured (platform-aware strictness lives in
    # the verifier). Unrelated PeerSlate behaviour is untouched.
    lock_violations = verify_runtime_lock(
        manifest=load_runtime_lock_manifest(root)
    )
    if lock_violations:
        logger.warning(
            "interview runtime lock failed closed: %d violation(s)",
            len(lock_violations),
        )
        return None

    # Consolidated correction B5: the evaluation-set identity is ALWAYS
    # recomputed from the strict, guarded, deployable manifest through
    # the SAME shared parser the builder uses — never trusted as recorded
    # data. tests/** need not exist at production runtime; the manifest
    # bytes are a runtime-core guarded entry under the B1 anchor; any
    # evaluation file that IS present must match its recorded digest
    # byte-for-byte; and a missing, malformed, duplicated, reordered,
    # miscounted, or substituted manifest, a manifest/record hash
    # mismatch, or a divergent present file all fail closed.
    recorded_eval_hash = record.get("evaluation_set_hash")
    if not is_full_sha256(recorded_eval_hash):
        return None
    evaluation_manifest_path = (
        root / "prompts" / "interview" / "contracts" / "evaluation-set-1.json"
    )
    evaluation_entries, recomputed_eval_hash = (
        evaluation_manifest.parse_manifest_bytes(
            evaluation_manifest_path.read_bytes()
        )
    )
    for evaluation_entry in evaluation_entries:
        source_path = root / Path(evaluation_entry["path"])
        if source_path.is_file():
            if sha256_hex(source_path.read_bytes()) != evaluation_entry["sha256"]:
                return None
    if recomputed_eval_hash != recorded_eval_hash:
        return None

    computed_candidate = candidate_system_digest(
        computed_core,
        slots,
        record.get("guardian_set_version"),
        record.get("contracts_version"),
        recorded_eval_hash,
    )
    if computed_candidate != record.get("candidate_system_digest"):
        return None

    computed_release = release_set_id(
        computed_candidate,
        record.get("accepted_run_digests", []),
        record.get("threshold_set_id"),
        record.get("threshold_set_version"),
    )
    if computed_release != configured_id:
        return None

    return ActiveRelease(configured_id, record, bundles)
