"""Run the required Resume publication browser suite with fail-closed counts."""

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
MODULE_FILE = ROOT / "tests" / "test_resume_publication_browser.py"
MODULE_NAME = "required_resume_publication_browser"
CLASS_NAME = "ResumePublicationBrowserTests"
EXPECTED_METHODS = (
    "test_keyboard_review_control_is_operable",
    "test_owner_guest_contexts_permission_combinations_draft_isolation_and_corrections",
    "test_owner_review_publish_guest_sees_result_and_sharing_off_denies",
    "test_private_composition_preview_uses_temporary_choices_and_returns_keyboard_focus",
    "test_stale_publish_replay_conflict_private_restore_and_media_revocation",
    "test_visitor_mobile_keyboard_reflow_and_private_preview_separation",
    "test_visitor_questions_sixth_answer_citation_revocation_and_failure_recovery",
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
    executable = Path(output[0]).resolve(strict=True)
    if not executable.is_file():
        raise BrowserCiError(f"installed Playwright Chromium is absent: {executable}")
    return executable


def load_selected_suite(module_file, module_name, class_name, expected_methods):
    require_module_file(module_file)
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    test_case = getattr(module, class_name)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_case)
    actual_methods = tuple(sorted(test._testMethodName for test in _iter_tests(suite)))
    expected = tuple(sorted(expected_methods))
    if actual_methods != expected:
        raise BrowserCiError(
            f"required browser method set changed: {actual_methods!r} != {expected!r}"
        )
    return suite


def execute_suite(suite, expected_count, stream=None):
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(stream=stream or sys.stdout, verbosity=2).run(suite)
    skipped = len(result.skipped)
    ok = (
        discovered == expected_count
        and result.testsRun == expected_count
        and skipped == 0
        and result.wasSuccessful()
    )
    return ok, {
        "status": "pass" if ok else "fail",
        "expected": expected_count,
        "discovered": discovered,
        "tests_run": result.testsRun,
        "skipped": skipped,
        "failures": len(result.failures),
        "errors": len(result.errors),
    }


def main() -> int:
    expected_count = len(EXPECTED_METHODS)
    try:
        browser = resolve_browser_executable()
        os.environ["PEERSLATE_CHROME"] = str(browser)
        suite = load_selected_suite(MODULE_FILE, MODULE_NAME, CLASS_NAME, EXPECTED_METHODS)
        ok, summary = execute_suite(suite, expected_count)
    except Exception as exc:
        summary = {"status": "fail", "reason": str(exc), "expected": expected_count}
        ok = False
    print("RESUME_PUBLICATION_BROWSER_CI_SUMMARY=" + json.dumps(summary, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
