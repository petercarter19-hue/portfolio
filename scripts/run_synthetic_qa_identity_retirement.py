#!/usr/bin/env python3
"""Protected entry point for two-member synthetic QA identity retirement."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qa.synthetic_member.identity_retirement import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
