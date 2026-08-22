"""Execute the B3 runtime-lock proof cases with real pip operations.

One hash-verified ``pip download`` builds a local wheelhouse of the exact
locked artifacts; every case then installs offline from it with the same
flags the deployment pipeline uses, into disposable scratch targets. The
report is content-free JSON mapping each B3 mandatory-proof case to its
command results. No provider call, no production system, no repository
mutation.

Covered here: successful --require-hashes vendored install (case 3), the
staged-artifact verification the pipeline runs (cases 4/5 at artifact
level), wrong-hash install failure (6), missing-transitive closure
failure (7), substituted same-version artifact failure (8), modified
installed-byte failure (9), wrong-version failure (10), unchanged valid
closure (12). Case 11 (lock/manifest/verifier edits trip B1) runs in the
tripwire mutation matrix; case 13 is the ordinary regression battery;
cases 1–2 are the committed manifest itself.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.interview_ai.runtime_lock import (  # noqa: E402
    load_manifest,
    verify_vendored_directory,
)

CONTROL = ROOT / "prompts" / "interview" / "control"
LOCK = CONTROL / "interview-runtime-lock.txt"
VENDOR_ARGS = CONTROL / "interview-runtime-vendor-args.txt"


def vendor_flags():
    return VENDOR_ARGS.read_text(encoding="utf-8").split()


def pip(*arguments):
    completed = subprocess.run(
        [sys.executable, "-m", "pip"] + list(arguments),
        capture_output=True, text=True,
    )
    tail = (completed.stdout + completed.stderr).strip().splitlines()[-4:]
    return completed.returncode, tail


def install_from(lock_path, wheelhouse, target):
    return pip(
        "install", "--require-hashes", "--no-deps", "--only-binary=:all:",
        "--no-index", "--find-links", str(wheelhouse),
        *vendor_flags(),
        "-r", str(lock_path), "--target", str(target),
        "--quiet",
    )


def main():
    manifest = load_manifest()
    report = {"cases": {}, "result": "pass"}

    def record(name, ok, **details):
        report["cases"][name] = {"ok": bool(ok), **details}
        if not ok:
            report["result"] = "FAIL"

    with tempfile.TemporaryDirectory() as scratch:
        scratch = Path(scratch)
        wheelhouse = scratch / "wheelhouse"
        wheelhouse.mkdir()
        download_rc, download_tail = pip(
            "download", "--require-hashes", "--no-deps",
            "--only-binary=:all:", *vendor_flags(),
            "-r", str(LOCK), "--dest", str(wheelhouse), "--quiet",
        )
        record(
            "wheelhouse_download_hash_verified",
            download_rc == 0 and len(list(wheelhouse.glob("*.whl")))
            == len(manifest["distributions"]),
            rc=download_rc, wheels=len(list(wheelhouse.glob("*.whl"))),
            tail=download_tail,
        )

        # Case 3 + 12: the unchanged, valid closure vendors and verifies.
        target = scratch / "vendored"
        rc, tail = install_from(LOCK, wheelhouse, target)
        violations = verify_vendored_directory(target, manifest)
        record("case3_require_hashes_vendored_install", rc == 0,
               rc=rc, tail=tail)
        record("case12_unchanged_valid_closure_verifies",
               rc == 0 and violations == [], violations=violations[:3])

        # Cases 4/5 at artifact level: the pipeline's staged verification
        # command against the exact directory that gets archived.
        staged_rc = subprocess.run(
            [sys.executable,
             str(ROOT / "scripts" / "interview_ai"
                 / "verify_staged_runtime.py"),
             "--staged-site-packages", str(target)],
            capture_output=True, text=True,
        )
        record("case5_staged_verification_command", staged_rc.returncode == 0,
               rc=staged_rc.returncode)

        # Case 6: a wrong artifact hash fails installation.
        bad_lock = scratch / "bad-hash.lock"
        lock_text = LOCK.read_text(encoding="utf-8")
        anthropic_hash = next(
            record_["artifact_sha256"]
            for record_ in manifest["distributions"]
            if record_["name"] == "anthropic"
        )
        bad_lock.write_text(
            lock_text.replace(anthropic_hash,
                              "0" * 8 + anthropic_hash[8:]),
            encoding="utf-8",
        )
        rc, tail = install_from(bad_lock, wheelhouse, scratch / "t6")
        record("case6_wrong_hash_fails_install", rc != 0, rc=rc,
               tail=tail[-2:])

        # Case 7: a missing transitive record fails closure verification.
        thin_lock = scratch / "missing-transitive.lock"
        lines = lock_text.splitlines()
        keep = []
        skip_next = False
        for line in lines:
            if line.startswith("httpcore=="):
                skip_next = True
                continue
            if skip_next and line.strip().startswith("--hash"):
                skip_next = False
                continue
            keep.append(line)
        thin_lock.write_text("\n".join(keep) + "\n", encoding="utf-8")
        target7 = scratch / "t7"
        rc, _ = install_from(thin_lock, wheelhouse, target7)
        violations = verify_vendored_directory(target7, manifest)
        record(
            "case7_missing_transitive_fails_closure",
            rc == 0 and any("missing" in v and "httpcore" in v
                            for v in violations),
            violations=[v for v in violations if "httpcore" in v],
        )

        # Case 8: a substituted artifact under the same version fails —
        # the lock line for idna is given sniffio's (real, valid) hash.
        swap_lock = scratch / "substituted.lock"
        idna_hash = next(
            record_["artifact_sha256"]
            for record_ in manifest["distributions"]
            if record_["name"] == "idna"
        )
        sniffio_hash = next(
            record_["artifact_sha256"]
            for record_ in manifest["distributions"]
            if record_["name"] == "sniffio"
        )
        swap_lock.write_text(
            lock_text.replace(idna_hash, sniffio_hash), encoding="utf-8",
        )
        rc, tail = install_from(swap_lock, wheelhouse, scratch / "t8")
        record("case8_substituted_artifact_fails", rc != 0, rc=rc,
               tail=tail[-2:])

        # Case 9: one modified installed byte fails verification.
        target9 = scratch / "t9"
        rc, _ = install_from(LOCK, wheelhouse, target9)
        anthropic_init = target9 / "anthropic" / "__init__.py"
        anthropic_init.write_bytes(
            anthropic_init.read_bytes() + b"\n# drifted byte\n"
        )
        violations = verify_vendored_directory(target9, manifest)
        record(
            "case9_modified_installed_byte_fails",
            any("anthropic" in v and "projection" in v for v in violations),
            violations=[v for v in violations if "anthropic" in v][:1],
        )

        # Case 10: a wrong distribution version fails.
        target10 = scratch / "t10"
        rc, _ = install_from(LOCK, wheelhouse, target10)
        idna_info = next(target10.glob("idna-*.dist-info"))
        metadata_path = idna_info / "METADATA"
        metadata_path.write_bytes(
            metadata_path.read_bytes().replace(
                b"Version: 3.18", b"Version: 3.17", 1,
            )
        )
        violations = verify_vendored_directory(target10, manifest)
        record(
            "case10_wrong_version_fails",
            any("idna" in v and ("version" in v or "projection" in v)
                for v in violations),
            violations=[v for v in violations if "idna" in v][:1],
        )

        # Origin variant of case 10: content outside the locked closure in
        # the vendored directory is refused.
        target10b = scratch / "t10b"
        rc, _ = install_from(LOCK, wheelhouse, target10b)
        foreign = target10b / "foreign_pkg-1.0.dist-info"
        foreign.mkdir()
        (foreign / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: foreign-pkg\nVersion: 1.0\n",
            encoding="utf-8",
        )
        (foreign / "RECORD").write_text("", encoding="utf-8")
        violations = verify_vendored_directory(target10b, manifest)
        record(
            "case10b_outside_closure_distribution_fails",
            any("outside the locked closure" in v for v in violations),
            violations=[v for v in violations
                        if "outside" in v][:1],
        )

    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
