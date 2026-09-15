"""Run the Interview recovery/mobile-nav browser contract with fail-closed counts."""

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


MODULE_FILE = ROOT / "tests" / "test_interview_recovery_mobile_nav_browser.py"
MODULE_NAME = "required_interview_recovery_mobile_nav_browser"
CLASS_NAME = "InterviewRecoveryMobileNavBrowserTests"
EXPECTED_METHODS = (
    "test_keep_editing_makes_no_request_and_restores_review",
    "test_menu_escape_returns_to_opener_and_keyboard_departure_closes_without_stealing_focus",
    "test_mobile_menu_hides_interview_dock_at_390_and_320",
    "test_one_retry_activation_posts_once_without_duplicate_history",
    "test_pending_retry_ignores_duplicate_activation",
    "test_public_and_authenticated_recovery_remain_distinct",
    "test_unreadable_provider_preserves_answer_and_one_recovery_control",
)


def _print_summary(summary: dict[str, int | str]) -> None:
    print("RECOVERY_MOBILE_NAV_BROWSER_SUMMARY=" + json.dumps(summary, sort_keys=True))


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
