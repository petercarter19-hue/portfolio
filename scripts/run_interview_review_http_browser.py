"""Run the Interview Review HTTP browser contract with fail-closed counts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_interview_browser_ci import (
    BrowserCiError,
    execute_suite,
    load_selected_suite,
    require_module_file,
    resolve_playwright_chromium,
)


MODULE_FILE = ROOT / "tests" / "test_interview_review_http_browser.py"
MODULE_NAME = "required_interview_review_http_browser"
CLASS_NAME = "InterviewReviewHttpBrowserTests"
EXPECTED_METHODS = ("test_review_click_reaches_flask_with_stubbed_provider",)


def _print_summary(summary: dict[str, int | str]) -> None:
    print("REVIEW_HTTP_BROWSER_SUMMARY=" + json.dumps(summary, sort_keys=True))


def main() -> int:
    expected_count = len(EXPECTED_METHODS)
    try:
        require_module_file(MODULE_FILE)
        chromium = resolve_playwright_chromium()
        os.environ["PEERSLATE_CHROME"] = str(chromium)
        suite = load_selected_suite(
            MODULE_FILE,
            MODULE_NAME,
            CLASS_NAME,
            EXPECTED_METHODS,
        )
        ok, summary = execute_suite(suite, expected_count)
    except BrowserCiError as exc:
        summary = {
            "status": "fail",
            "expected": expected_count,
            "discovered": 0,
            "tests_run": 0,
            "executed": 0,
            "passed": 0,
            "skipped": 0,
            "failures": 0,
            "errors": 1,
            "expected_failures": 0,
            "unexpected_successes": 0,
            "reason": str(exc),
        }
        ok = False
    _print_summary(summary)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
