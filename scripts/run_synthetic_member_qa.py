"""Entry point for the provider-free synthetic multi-member QA foundation."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qa.synthetic_member.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
