"""Run the required Interview Studio browser suite with fail-closed counts."""

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
MODULE_FILE = ROOT / "tests" / "test_interview_studio_operability_browser.py"
MODULE_NAME = "required_interview_studio_operability_browser"
CLASS_NAME = "InterviewStudioOperabilityBrowserTests"
EXPECTED_METHODS = (
    "test_authenticated_flow_omits_finish_and_keeps_setup_dismissible",
    "test_history_is_one_guarded_destination_and_persists_a_draft",
    "test_no_javascript_keeps_real_links_and_hides_js_only_launchers",
    "test_public_flag_off_composition_does_not_receive_member_launchers",
    "test_review_and_unsaved_improvement_survive_modes_history_and_refresh",
    "test_session_setup_keyboard_open_cancel_and_apply",
    "test_settings_focus_trap_escape_close_and_backdrop_return",
    "test_single_controls_targets_and_reflow_at_supported_widths",
    "test_storage_failures_keep_review_actions_visible_and_truthful",
    "test_text_spacing_forced_colors_and_reduced_motion_remain_operable",
    "test_video_history_guard_refusal_preserves_the_local_transcript",
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
