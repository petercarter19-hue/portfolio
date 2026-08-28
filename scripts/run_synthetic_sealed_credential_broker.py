#!/usr/bin/env python3
"""Protected local entry point for the sealed synthetic-QA credential broker."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qa.synthetic_member.sealed_credential_broker import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
