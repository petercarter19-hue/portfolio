"""Generate ``control_room_snapshot.json`` for the PeerSlate Control Room.

Run by the Azure Pipeline after tests pass and before the ``CopyFiles`` step
packages the deployment artifact (which excludes ``.git``). Captures a fixed
slice of git history plus the pipeline's own build identity, so the deployed
application can show truthful "recent changes" and "what's deployed"
information without runtime access to ``.git``.

Never fails the build: any error here is swallowed and the script still exits
0. A partial snapshot (missing ``commits``) is written rather than none at all,
because Tier 0's build identity is useful even when git history is not.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT, "control_room_snapshot.json")
SCHEMA_VERSION = 1
COMMIT_LIMIT = 30


def _git_commits(limit=COMMIT_LIMIT):
    """Return recent commit records, or ``None`` if git is unavailable.

    Includes both the short and full SHA: the full SHA lets the deployed
    app compare its build against a live Azure DevOps branch tip (drift);
    the short SHA is what the UI displays.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{int(limit)}",
                "--date=short",
                "--pretty=format:%h\x1f%H\x1f%ad\x1f%an\x1f%s",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    commits = []
    for line in result.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 5:
            continue
        short, full, date, author, subject = parts
        commits.append(
            {
                "commit": short,
                "full": full,
                "date": date,
                "author": author,
                "subject": subject,
            }
        )
    return commits


def build_snapshot():
    """Assemble the snapshot dict. Pure function; never raises."""
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "build": {
            "id": os.environ.get("BUILD_BUILDID"),
            "source_version": os.environ.get("BUILD_SOURCEVERSION"),
            "source_branch": os.environ.get("BUILD_SOURCEBRANCH"),
        },
    }
    commits = _git_commits()
    if commits is not None:
        snapshot["commits"] = commits
    return snapshot


def main():
    try:
        snapshot = build_snapshot()
        with open(SNAPSHOT_PATH, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
            handle.write("\n")
        print(f"Control Room snapshot written to {SNAPSHOT_PATH}")
    except Exception as error:  # noqa: BLE001 - must never fail the build
        print(
            f"Control Room snapshot generation skipped: {error}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
