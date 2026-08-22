"""Verify the staged deployment artifact's vendored Interview closure (B3).

Runs in the deployment pipeline against the exact directory that is about
to be archived into the deployment ZIP — the artifact that would be
deployed, not a unit-test scratch. Pure metadata and byte verification
(nothing is imported), so the cp314 Linux artifacts verify on the build
agent regardless of its own interpreter.

Exit 0 only when every locked distribution is present exactly once, at
the locked version, with a byte-exact installed projection, and nothing
outside the locked closure is vendored. The report is content-free.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.interview_ai.runtime_lock import (  # noqa: E402
    load_manifest,
    verify_vendored_directory,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged-site-packages", required=True)
    arguments = parser.parse_args()
    staged = Path(arguments.staged_site_packages)
    if not staged.is_dir():
        print(json.dumps({"result": "FAIL",
                          "reason": "staged directory missing"}))
        return 1
    manifest = load_manifest()
    violations = verify_vendored_directory(staged, manifest)
    report = {
        "result": "pass" if not violations else "FAIL",
        "staged_path": str(staged),
        "locked_distributions": len(manifest["distributions"]),
        "violations": violations,
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
