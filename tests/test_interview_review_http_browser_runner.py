import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.run_interview_browser_ci import (
    BrowserCiError,
    execute_suite,
    load_selected_suite,
    require_module_file,
)
from scripts.run_interview_review_http_browser import (
    CLASS_NAME,
    EXPECTED_METHODS,
    MODULE_FILE,
    MODULE_NAME,
)


class InterviewReviewHttpBrowserRunnerTests(unittest.TestCase):
    def _module(self, source: str) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "review_http_suite.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return temporary, path

    def test_required_method_contract_pins_the_one_http_review_test(self):
        self.assertEqual(EXPECTED_METHODS, ("test_review_click_reaches_flask_with_stubbed_provider",))
        self.assertEqual(CLASS_NAME, "InterviewReviewHttpBrowserTests")
        self.assertEqual(MODULE_NAME, "required_interview_review_http_browser")
        self.assertEqual(MODULE_FILE.name, "test_interview_review_http_browser.py")

    def test_missing_suite_fails_closed(self):
        with self.assertRaisesRegex(BrowserCiError, "suite is absent"):
            require_module_file(Path("definitely-absent-review-http-suite.py"))

    def test_zero_discovery_fails_closed(self):
        temporary, path = self._module(
            """
            import unittest
            class EmptyReviewHttpTests(unittest.TestCase):
                pass
            """
        )
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(BrowserCiError, "discovered zero tests"):
            load_selected_suite(
                path,
                "zero_review_http_suite",
                "EmptyReviewHttpTests",
                ("test_required",),
            )

    def test_renamed_required_method_fails_closed(self):
        temporary, path = self._module(
            """
            import unittest
            class RenamedReviewHttpTests(unittest.TestCase):
                def test_renamed(self):
                    pass
            """
        )
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(
            BrowserCiError,
            r"missing=\['test_required'\].*unexpected=\['test_renamed'\]",
        ):
            load_selected_suite(
                path,
                "renamed_review_http_suite",
                "RenamedReviewHttpTests",
                ("test_required",),
            )

    def test_skipped_required_method_reports_zero_executed_and_fails(self):
        temporary, path = self._module(
            """
            import unittest
            class SkippedReviewHttpTests(unittest.TestCase):
                @unittest.skip('synthetic missing browser')
                def test_required(self):
                    pass
            """
        )
        self.addCleanup(temporary.cleanup)
        suite = load_selected_suite(
            path,
            "skipped_review_http_suite",
            "SkippedReviewHttpTests",
            ("test_required",),
        )
        ok, summary = execute_suite(suite, 1, stream=io.StringIO())
        self.assertFalse(ok)
        self.assertEqual(summary["discovered"], 1)
        self.assertEqual(summary["executed"], 0)
        self.assertEqual(summary["skipped"], 1)

    def test_success_reports_one_executed_and_zero_skipped(self):
        temporary, path = self._module(
            """
            import unittest
            class PassingReviewHttpTests(unittest.TestCase):
                def test_required(self):
                    pass
            """
        )
        self.addCleanup(temporary.cleanup)
        suite = load_selected_suite(
            path,
            "passing_review_http_suite",
            "PassingReviewHttpTests",
            ("test_required",),
        )
        ok, summary = execute_suite(suite, 1, stream=io.StringIO())
        self.assertTrue(ok)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["executed"], 1)
        self.assertEqual(summary["skipped"], 0)


if __name__ == "__main__":
    unittest.main()
