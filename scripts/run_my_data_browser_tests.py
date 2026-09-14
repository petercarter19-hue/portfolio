"""Run the required My Data browser suite with fail-closed counts."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODULE_FILE = ROOT / "tests" / "test_my_data_browser.py"
MODULE_NAME = "required_my_data_browser"
CLASS_NAME = "MyDataBrowserTests"
EXPECTED_METHODS = (
    "test_add_result_survives_debounced_draft_autosave",
    "test_composer_add_captures_text_and_routes_proposals",
    "test_composer_traps_focus_and_restores_opener",
    "test_deleted_activity_uses_the_lifecycle_timestamp",
    "test_delete_moves_to_recently_deleted_and_restore_returns",
    "test_desktop_keeps_mixed_actions_draft_and_proposal",
    "test_delayed_draft_get_after_typing_shows_conflict",
    "test_draft_conflict_offers_recovery_choice",
    "test_draft_recovers_text_after_reload",
    "test_extracted_duplicate_offers_keep_as_separate",
    "test_every_extracted_equivalent_renders_its_own_bound_action",
    "test_inventory_groups_seeded_entries_and_search_narrows",
    "test_mobile_composer_opens_reachable_add",
    "test_mobile_keeps_mixed_actions_draft_and_proposal",
    "test_mobile_reopen_after_other_device_save_shows_conflict",
    "test_oversize_file_refused_before_attach",
    "test_proposal_wording_keeps_field_boundaries",
    "test_provider_failure_keeps_manual_path",
    "test_reopen_after_other_device_save_shows_conflict",
    "test_role_correction_preserves_current_role_flag",
    "test_sharing_badges_and_filters_render_each_permission",
    "test_sharing_change_marks_resume_flag",
    "test_touch_targets_measure_44px_at_390px",
    "test_view_tabs_support_arrow_key_selection",
)


class BrowserCiError(RuntimeError):
    """The selected browser suite could not be proven complete and runnable."""


def _iter_tests(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def require_module_file(module_file: Path) -> None:
    if not module_file.is_file():
        raise BrowserCiError(f"required browser suite is absent: {module_file}")


def resolve_playwright_chromium() -> Path:
    probe = (
        "from playwright.sync_api import sync_playwright; "
        "manager = sync_playwright().start(); "
        "print(manager.chromium.executable_path); "
        "manager.stop()"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BrowserCiError(
            f"Playwright Chromium resolution failed: {type(exc).__name__}"
        ) from exc
    if completed.returncode != 0:
        raise BrowserCiError("pinned Playwright dependency or Chromium is unavailable")
    output = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if len(output) != 1:
        raise BrowserCiError("Playwright Chromium resolution returned an invalid path")
    executable = Path(output[0]).resolve()
    if not executable.is_file():
        raise BrowserCiError(f"installed Playwright Chromium is absent: {executable}")
    return executable


def load_selected_suite(
    module_file: Path,
    module_name: str,
    class_name: str,
    expected_methods: tuple[str, ...],
) -> unittest.TestSuite:
    require_module_file(module_file)
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise BrowserCiError(f"required browser suite cannot be loaded: {module_file}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise BrowserCiError(
            f"required browser suite import failed: {type(exc).__name__}: {exc}"
        ) from exc

    test_case = getattr(module, class_name, None)
    if not isinstance(test_case, type) or not issubclass(test_case, unittest.TestCase):
        raise BrowserCiError(f"required browser test class is absent: {class_name}")

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case)
    actual_methods = tuple(sorted(test._testMethodName for test in _iter_tests(suite)))
    expected = tuple(sorted(expected_methods))
    if not actual_methods:
        raise BrowserCiError("required browser suite discovered zero tests")
    if actual_methods != expected:
        missing = sorted(set(expected) - set(actual_methods))
        unexpected = sorted(set(actual_methods) - set(expected))
        raise BrowserCiError(
            "required browser method set changed: "
            f"missing={missing}, unexpected={unexpected}"
        )
    return suite


def execute_suite(
    suite: unittest.TestSuite,
    expected_count: int,
    stream=None,
) -> tuple[bool, dict[str, int | str]]:
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(stream=stream or sys.stdout, verbosity=2).run(suite)
    skipped = len(result.skipped)
    failures = len(result.failures)
    errors = len(result.errors)
    expected_failures = len(result.expectedFailures)
    unexpected_successes = len(result.unexpectedSuccesses)
    executed = result.testsRun - skipped
    passed = (
        executed
        - failures
        - errors
        - expected_failures
        - unexpected_successes
    )
    ok = (
        discovered == expected_count
        and result.testsRun == expected_count
        and executed == expected_count
        and skipped == 0
        and expected_failures == 0
        and result.wasSuccessful()
    )
    return ok, {
        "status": "pass" if ok else "fail",
        "expected": expected_count,
        "discovered": discovered,
        "tests_run": result.testsRun,
        "executed": executed,
        "passed": passed,
        "skipped": skipped,
        "failures": failures,
        "errors": errors,
        "expected_failures": expected_failures,
        "unexpected_successes": unexpected_successes,
    }


def _print_summary(summary: dict[str, int | str]) -> None:
    print("BROWSER_CI_SUMMARY=" + json.dumps(summary, sort_keys=True))


def main() -> int:
    expected_count = len(EXPECTED_METHODS)
    try:
        require_module_file(MODULE_FILE)
        os.environ.pop("PEERSLATE_CHROME", None)
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
