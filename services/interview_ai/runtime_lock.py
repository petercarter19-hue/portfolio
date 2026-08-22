"""External runtime-lock verification for Interview AI (correction B3).

The external-runtime manifest
(`prompts/interview/contracts/external-runtime-1.json`) records, for every
executable distribution reachable from the Interview runtime — provider,
HTTP, validation, signing, environment/configuration, and SQL telemetry
stacks — its exact version, dependency edge, permitted production
artifact (filename + full SHA-256, Linux/cp314), and the installed-file
projection of that artifact: sorted normalized paths with raw-file
SHA-256 values over executable Python, native-library, and stable
distribution metadata bytes (install-time bookkeeping such as RECORD,
INSTALLER, REQUESTED, direct_url.json, and bytecode caches is excluded —
nothing behaviour-bearing is).

Boot verification here runs before an active Interview release becomes
ready: it recomputes the projections from the distributions the running
interpreter actually resolves and compares them with the manifest. A
missing, duplicated/shadowed, substituted, wrong-version, or
byte-different reachable distribution leaves Interview
`service_not_configured`; nothing here can crash unrelated PeerSlate
behaviour.

Strictness is platform-aware and honest: on the locked production
platform (Linux, the locked Python), every projection is enforced
byte-for-byte. On other platforms (Windows/macOS development, a
different-minor CI interpreter) the platform-INDEPENDENT artifacts are
still enforced byte-for-byte — a pure wheel installs identical bytes
everywhere — while platform-DEPENDENT distributions are enforced by
exact version and presence, because their locked artifacts are Linux
binaries by definition. The pipeline's staged-artifact check runs the
strict path against the vendored directory itself.
"""

import hashlib
import json
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path

from services.interview_ai.identity import canonical_json_bytes, sha256_hex

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_RELATIVE = "prompts/interview/contracts/external-runtime-1.json"

PROJECTION_DOMAIN = "peerslate.interview.runtime-lock.v1"
PROJECTION_EXCLUDED_BASENAMES = {
    "RECORD", "INSTALLER", "REQUESTED", "direct_url.json",
}


def is_projected_path(path_posix):
    parts = path_posix.split("/")
    if "__pycache__" in parts:
        return False
    if path_posix.endswith(".pyc"):
        return False
    if parts[-1] in PROJECTION_EXCLUDED_BASENAMES:
        return False
    return True


def projection_digest(files_by_path):
    payload = {
        "digest_domain": PROJECTION_DOMAIN,
        "files": [
            {"path": path, "sha256": files_by_path[path]}
            for path in sorted(files_by_path)
        ],
    }
    return sha256_hex(canonical_json_bytes(payload))


def load_manifest(root=None):
    manifest_path = (root or ROOT) / Path(MANIFEST_RELATIVE)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _normalize_name(name):
    return name.lower().replace("_", "-").replace(".", "-")


def _installed_projection(dist):
    """Recompute the projection from the files the environment resolves."""
    files_by_path = {}
    for file_entry in (dist.files or []):
        path_posix = file_entry.as_posix()
        if path_posix.startswith(".."):
            # Script/data entries outside site-packages (e.g. bin/) are
            # install-layout dependent, not payload bytes.
            continue
        if not is_projected_path(path_posix):
            continue
        located = dist.locate_file(file_entry)
        try:
            content = Path(located).read_bytes()
        except OSError:
            files_by_path[path_posix] = "UNREADABLE"
            continue
        files_by_path[path_posix] = hashlib.sha256(content).hexdigest()
    return files_by_path


def _running_on_locked_platform(manifest):
    production = manifest.get("production", {})
    locked_python = production.get("python_version", "")
    running_python = "%d.%d" % sys.version_info[:2]
    return sys.platform == "linux" and running_python == locked_python


def verify_vendored_directory(directory, manifest=None):
    """Strict verification of a staged/vendored site-packages directory.

    Used by the deployment pipeline against the artifact that will be
    deployed: every locked distribution must be present exactly once at
    the locked version with a byte-exact installed projection, and no
    distribution outside the locked closure may be present. Pure
    metadata+byte work — nothing is imported, so a cp314 Linux artifact
    verifies on any build agent.
    """
    if manifest is None:
        manifest = load_manifest()
    violations = []
    found = {}
    for dist in importlib_metadata.distributions(path=[str(directory)]):
        name = _normalize_name(dist.metadata["Name"] or "")
        if name in found:
            violations.append("duplicate vendored distribution: %s" % name)
            continue
        found[name] = dist
    closure = {
        _normalize_name(record["name"]): record
        for record in manifest.get("distributions", [])
    }
    for extra in sorted(set(found) - set(closure)):
        violations.append(
            "distribution outside the locked closure: %s" % extra
        )
    for name, record in sorted(closure.items()):
        dist = found.get(name)
        if dist is None:
            violations.append("missing vendored distribution: %s" % name)
            continue
        if dist.version != record["version"]:
            violations.append(
                "wrong vendored version for %s: %s, locked %s"
                % (name, dist.version, record["version"])
            )
            continue
        expected_map = {
            entry["path"]: entry["sha256"]
            for entry in record["installed_projection"]["files"]
        }
        actual = _installed_projection(dist)
        if actual != expected_map:
            violations.append(
                "vendored byte-projection mismatch for %s "
                "(missing=%d extra=%d changed=%d)"
                % (name, len(set(expected_map) - set(actual)),
                   len(set(actual) - set(expected_map)),
                   len([p for p in set(actual) & set(expected_map)
                        if actual[p] != expected_map[p]]))
            )
    return violations


def verify_runtime_lock(manifest=None, strict=None):
    """Return the violation list; empty means the runtime closure verifies."""
    violations = []
    if manifest is None:
        manifest = load_manifest()
    if strict is None:
        strict = _running_on_locked_platform(manifest)

    # Duplicate/shadow detection: a closure distribution visible twice on
    # the path means an unverified copy could win the import race.
    closure_names = {
        _normalize_name(record["name"])
        for record in manifest.get("distributions", [])
    }
    seen_paths = {}
    for dist in importlib_metadata.distributions():
        dist_name = _normalize_name(dist.metadata["Name"] or "")
        if dist_name in closure_names:
            location = str(dist.locate_file("")).rstrip("/\\")
            seen_paths.setdefault(dist_name, set()).add(location)
    for dist_name, locations in sorted(seen_paths.items()):
        if len(locations) > 1:
            violations.append(
                "duplicate installations visible for %s" % dist_name
            )

    for record in manifest.get("distributions", []):
        name = record["name"]
        try:
            dist = importlib_metadata.distribution(name)
        except importlib_metadata.PackageNotFoundError:
            violations.append("missing distribution: %s" % name)
            continue
        if dist.version != record["version"]:
            violations.append(
                "wrong version for %s: installed %s, locked %s"
                % (name, dist.version, record["version"])
            )
            continue
        enforce_bytes = strict or record.get("platform_independent", False)
        if not enforce_bytes:
            continue
        expected = record["installed_projection"]["files"]
        actual = _installed_projection(dist)
        expected_map = {
            entry["path"]: entry["sha256"] for entry in expected
        }
        if actual != expected_map:
            missing = sorted(set(expected_map) - set(actual))[:3]
            extra = sorted(set(actual) - set(expected_map))[:3]
            changed = sorted(
                path for path in set(actual) & set(expected_map)
                if actual[path] != expected_map[path]
            )[:3]
            violations.append(
                "byte-projection mismatch for %s (missing=%d extra=%d "
                "changed=%d; e.g. %s)"
                % (name, len(set(expected_map) - set(actual)),
                   len(set(actual) - set(expected_map)),
                   len([p for p in set(actual) & set(expected_map)
                        if actual[p] != expected_map[p]]),
                   (missing + extra + changed)[:3])
            )
            continue
        recorded_digest = record["installed_projection"]["projection_sha256"]
        if projection_digest(actual) != recorded_digest:
            violations.append(
                "projection digest mismatch for %s" % name
            )

    return violations
