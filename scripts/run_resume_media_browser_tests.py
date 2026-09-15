"""Run the required MVP1 Resume media browser suite with fail-closed counts.

Strict by design: a missing suite, an empty discovery, a changed required
method set, any skip, or any failure exits non-zero with a machine-readable
summary. The browser is the pinned Playwright Chromium unless PEERSLATE_CHROME
names another real executable for this machine, which is how the existing
Interview browser job already supplies its browser.
"""

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
MODULE_FILE = ROOT / "tests" / "test_resume_media_browser.py"
MODULE_NAME = "required_resume_media_browser"
CLASS_NAME = "ResumeMediaBrowserTests"
EXPECTED_METHODS = (
    "test_add_saves_one_private_draft_version_and_reload_returns_crops",
    "test_caption_cleared_before_add_clears_the_saved_caption",
    "test_index_marks_exactly_one_hide_guide_in_placement_review",
    "test_in_flight_command_gates_cross_actions_before_the_response",
    "test_keyboard_tabs_and_focus_are_operable",
    "test_keep_words_only_discards_pending_and_keeps_saved_media",
    "test_later_workspace_refresh_is_not_overwritten_by_an_earlier_request",
    "test_library_empty_and_error_states_are_honest",
    "test_library_search_places_an_illustration_and_shows_attribution",
    "test_lost_command_response_is_retried_with_the_same_request",
    "test_mixed_selection_swap_and_per_slot_crops",
    "test_mobile_layout_stacks_and_has_no_horizontal_overflow",
    "test_no_photo_choice_keeps_the_editor_usable",
    "test_old_workspace_refresh_cannot_overwrite_new_local_intent",
    "test_preview_does_not_change_the_private_draft",
    "test_removal_is_slot_local_and_keeps_the_other_photo",
    "test_saved_placement_bytes_render_after_add_and_after_reload",
    "test_stale_library_response_does_not_replace_newer_search",
    "test_tab_switch_and_hide_reopen_keep_pending_state",
    "test_unresolved_command_blocks_every_other_committing_action",
    "test_unresolved_remove_cannot_be_displaced_by_another_slot_removal",
    "test_upload_scan_ready_and_personal_selection",
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


def resolve_browser_executable() -> Path:
    """Resolve one real browser, refusing to guess or to fake a pinned path."""

    override = os.environ.get("PEERSLATE_CHROME", "").strip()
    if override:
        configured = Path(override)
        if configured.is_file():
            return configured.resolve()
        raise BrowserCiError(f"PEERSLATE_CHROME does not name a file: {override}")
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
            timeout=60,
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
    try:
        executable = Path(output[0]).resolve(strict=True)
    except OSError as exc:
        raise BrowserCiError(
            f"installed Playwright Chromium is absent: {output[0]}"
        ) from exc
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
    passed = max(
        0, executed - failures - errors - expected_failures - unexpected_successes
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
    print("RESUME_MEDIA_BROWSER_CI_SUMMARY=" + json.dumps(summary, sort_keys=True))


def main() -> int:
    expected_count = len(EXPECTED_METHODS)
    try:
        require_module_file(MODULE_FILE)
        browser = resolve_browser_executable()
        os.environ["PEERSLATE_CHROME"] = str(browser)
        suite = load_selected_suite(
            MODULE_FILE, MODULE_NAME, CLASS_NAME, EXPECTED_METHODS
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
