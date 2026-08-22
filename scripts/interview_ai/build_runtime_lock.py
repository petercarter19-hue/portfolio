"""Generate the Interview external runtime lock (correction B3).

Produces, from the actual Interview runtime import closure and PyPI's
immutable release records:

  prompts/interview/contracts/external-runtime-1.json
      the complete dependency record: name, exact version, dependency
      edge/reason, production ABI/platform, permitted artifact filename,
      artifact SHA-256, installed-file projection (sorted normalized
      paths + raw-file SHA-256), projection digest, responsible version;
  prompts/interview/control/interview-runtime-lock.txt
      the hash-locked pip requirements file (every line --hash pinned);
  prompts/interview/control/interview-runtime-vendor-args.txt
      the exact cross-target pip flags the deployment vendoring uses;
  prompts/interview/control/interview-runtime-constraints.txt
      versions-only constraints aligning test environments with the lock.

The generator downloads each selected wheel, verifies its SHA-256
against the PyPI record, and computes the projection from the verified
wheel payload itself — the same projection rule the boot verifier
recomputes from the running environment. Run manually; the ordinary
build and verification consume the committed outputs offline.
"""

import hashlib
import json
import sys
import tempfile
import urllib.request
import zipfile
from importlib import metadata as importlib_metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from packaging.requirements import Requirement  # noqa: E402

from services.interview_ai.runtime_lock import (  # noqa: E402
    is_projected_path,
    projection_digest,
)

PRODUCTION = {
    "python_version": "3.14",
    "implementation": "cp",
    "abi": "cp314",
    "platform": "linux",
    "machine": "x86_64",
    "app_service_runtime": "PYTHON|3.14",
}
PRODUCTION_MARKERS = {
    "python_version": "3.14", "python_full_version": "3.14.0",
    "sys_platform": "linux", "platform_system": "Linux",
    "platform_machine": "x86_64", "os_name": "posix",
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
    "extra": "",
}
RESPONSIBLE_VERSION = "interview-contracts@6"

ROOTS = {
    "anthropic": "provider stack (services/interview_ai/jobs.py, telemetry.py)",
    "itsdangerous": "signing stack (services/interview_ai/context_tokens.py)",
    "python-dotenv": "environment/configuration stack (db.py)",
    "mssql-python": "SQL telemetry stack (services/database_service.py -> db.py)",
    # Consolidated B3 review: the guarded Interview HTTP boundary executes
    # through Flask (routing, request parsing, JSON serialization, response
    # objects, error handling) and Flask-Limiter (call eligibility), so
    # both stacks belong to the locked external closure.
    "flask": "HTTP boundary stack (app.py guarded fragments)",
    "Flask-Limiter": "rate-limit stack (app.py interview_abuse_and_rate_limit)",
}

CONTRACTS_ROOT = ROOT / "prompts" / "interview" / "contracts"
CONTROL_ROOT = ROOT / "prompts" / "interview" / "control"


def normalize(name):
    return name.lower().replace("_", "-").replace(".", "-")


def resolve_closure():
    closure = {}
    edges = {}
    pending = [(name, "interview-runtime-root", reason)
               for name, reason in sorted(ROOTS.items())]
    while pending:
        name, parent, reason = pending.pop(0)
        key = normalize(name)
        edges.setdefault(key, []).append(
            {"parent": parent, "reason": reason}
        )
        if key in closure:
            continue
        dist = importlib_metadata.distribution(name)
        closure[key] = dist.version
        for spec in (dist.requires or []):
            requirement = Requirement(spec)
            if requirement.marker is not None and not requirement.marker.evaluate(
                PRODUCTION_MARKERS
            ):
                continue
            pending.append((requirement.name, key, "requires: %s" % spec))
    for key in edges:
        deduped = {json.dumps(e, sort_keys=True) for e in edges[key]}
        edges[key] = [json.loads(e) for e in sorted(deduped)]
    return closure, edges


def parse_wheel_tags(filename):
    stem = filename[:-4]  # drop .whl
    parts = stem.split("-")
    python_tags, abi_tags, platform_tags = parts[-3], parts[-2], parts[-1]
    return (python_tags.split("."), abi_tags.split("."),
            platform_tags.split("."))


def _acceptable_platform(tag):
    return tag == "any" or (
        (tag.startswith("manylinux") or tag.startswith("linux"))
        and tag.endswith("x86_64")
    )


def score_wheel(filename):
    """Higher is better; None means not usable on cp314/linux/x86_64."""
    python_tags, abi_tags, platform_tags = parse_wheel_tags(filename)
    if not any(_acceptable_platform(tag) for tag in platform_tags):
        return None
    if "cp314" in python_tags and "cp314" in abi_tags:
        return 400
    if "abi3" in abi_tags:
        eligible = [
            int(tag[2:]) for tag in python_tags
            if tag.startswith("cp3") and tag[2:].isdigit()
            and int(tag[2:]) <= 314
        ]
        if eligible:
            return 300 + max(eligible)
    if "none" in abi_tags and any(
        tag in ("py3", "py2.py3", "cp314") for tag in python_tags
    ):
        if all(tag == "any" for tag in platform_tags):
            return 100
        return 200
    return None


def select_artifact(name, version):
    url = "https://pypi.org/pypi/%s/%s/json" % (name, version)
    with urllib.request.urlopen(url, timeout=60) as response:
        release = json.load(response)
    candidates = []
    for artifact in release["urls"]:
        if artifact.get("packagetype") != "bdist_wheel":
            continue
        if artifact.get("yanked"):
            continue
        score = score_wheel(artifact["filename"])
        if score is not None:
            candidates.append((score, artifact))
    if not candidates:
        raise SystemExit(
            "no cp314/linux-compatible wheel for %s==%s" % (name, version)
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def wheel_projection(wheel_path):
    files_by_path = {}
    with zipfile.ZipFile(wheel_path) as wheel:
        for info in wheel.infolist():
            if info.is_dir():
                continue
            path = info.filename
            if ".data/" in path:
                # scripts/data trees install outside site-packages and are
                # layout-dependent; payload behaviour lives in purelib.
                continue
            if not is_projected_path(path):
                continue
            files_by_path[path] = hashlib.sha256(
                wheel.read(info)
            ).hexdigest()
    return files_by_path


def main():
    closure, edges = resolve_closure()
    print("closure: %d distributions" % len(closure))
    records = []
    with tempfile.TemporaryDirectory() as cache:
        for name in sorted(closure):
            version = closure[name]
            artifact = select_artifact(name, version)
            wheel_path = Path(cache) / artifact["filename"]
            urllib.request.urlretrieve(artifact["url"], wheel_path)
            actual_sha = hashlib.sha256(
                wheel_path.read_bytes()
            ).hexdigest()
            if actual_sha != artifact["digests"]["sha256"]:
                raise SystemExit(
                    "downloaded artifact hash mismatch for %s" % name
                )
            files_by_path = wheel_projection(wheel_path)
            records.append({
                "name": name,
                "version": version,
                "edges": edges[name],
                "production_abi": PRODUCTION["abi"],
                "production_platform": "%s-%s" % (
                    PRODUCTION["platform"], PRODUCTION["machine"],
                ),
                "artifact_filename": artifact["filename"],
                "artifact_sha256": artifact["digests"]["sha256"],
                "platform_independent": artifact["filename"].endswith(
                    ("py3-none-any.whl", "py2.py3-none-any.whl")
                ),
                "installed_projection": {
                    "files": [
                        {"path": path, "sha256": files_by_path[path]}
                        for path in sorted(files_by_path)
                    ],
                    "projection_sha256": projection_digest(files_by_path),
                },
                "responsible_version": RESPONSIBLE_VERSION,
            })
            print("locked %s==%s -> %s" % (
                name, version, artifact["filename"],
            ))

    manifest = {
        "schema": "interview-external-runtime@1",
        "production": PRODUCTION,
        "roots": ROOTS,
        "responsible_version": RESPONSIBLE_VERSION,
        "distributions": records,
    }
    manifest_bytes = (
        json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")
    (CONTRACTS_ROOT / "external-runtime-1.json").write_bytes(manifest_bytes)

    lock_lines = [
        "# Interview AI production runtime lock (correction B3).",
        "# Generated by scripts/interview_ai/build_runtime_lock.py from the",
        "# Interview import closure; every artifact is hash-pinned for",
        "# %s / %s-%s. Install with:" % (
            PRODUCTION["abi"], PRODUCTION["platform"], PRODUCTION["machine"],
        ),
        "#   pip install --require-hashes --no-deps --only-binary=:all: \\",
        "#     $(cat interview-runtime-vendor-args.txt) -r <this file> -t <target>",
        "",
    ]
    platform_tags = set()
    for record in records:
        lock_lines.append(
            "%s==%s \\" % (record["name"], record["version"])
        )
        lock_lines.append(
            "    --hash=sha256:%s" % record["artifact_sha256"]
        )
        _py, _abi, wheel_platforms = parse_wheel_tags(
            record["artifact_filename"]
        )
        platform_tags.update(wheel_platforms)
    (CONTROL_ROOT / "interview-runtime-lock.txt").write_text(
        "\n".join(lock_lines) + "\n", encoding="utf-8", newline="\n",
    )

    vendor_arguments = [
        "--python-version", PRODUCTION["python_version"],
        "--implementation", PRODUCTION["implementation"],
        "--abi", PRODUCTION["abi"], "--abi", "abi3", "--abi", "none",
    ]
    for tag in sorted(platform_tags):
        if tag != "any":
            vendor_arguments += ["--platform", tag]
    (CONTROL_ROOT / "interview-runtime-vendor-args.txt").write_text(
        "\n".join(vendor_arguments) + "\n", encoding="utf-8", newline="\n",
    )

    constraint_lines = [
        "# Versions-only mirror of interview-runtime-lock.txt (B3): aligns",
        "# test environments with the locked closure without hash pins.",
    ] + [
        "%s==%s" % (record["name"], record["version"]) for record in records
    ]
    (CONTROL_ROOT / "interview-runtime-constraints.txt").write_text(
        "\n".join(constraint_lines) + "\n", encoding="utf-8", newline="\n",
    )
    print("lock, vendor-args, constraints, and manifest written")


if __name__ == "__main__":
    main()
