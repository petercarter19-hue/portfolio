import io
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.run_interview_browser_ci import (
    BrowserCiError,
    EXPECTED_METHODS,
    execute_suite,
    load_selected_suite,
    require_module_file,
)


class InterviewBrowserCiRunnerTests(unittest.TestCase):
    def _module(self, source: str) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "browser_suite.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return temporary, path

    def test_required_method_contract_pins_all_eleven_selected_tests(self):
        self.assertEqual(len(EXPECTED_METHODS), 11)
        self.assertEqual(len(set(EXPECTED_METHODS)), 11)
        self.assertIn(
            "test_single_controls_targets_and_reflow_at_supported_widths",
            EXPECTED_METHODS,
        )
        self.assertIn(
            "test_text_spacing_forced_colors_and_reduced_motion_remain_operable",
            EXPECTED_METHODS,
        )

    def test_missing_suite_fails_closed(self):
        with self.assertRaisesRegex(BrowserCiError, "suite is absent"):
            require_module_file(Path("definitely-absent-browser-suite.py"))

    def test_zero_discovery_fails_closed(self):
        temporary, path = self._module(
            """
            import unittest
            class EmptyBrowserTests(unittest.TestCase):
                pass
            """
        )
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(BrowserCiError, "discovered zero tests"):
            load_selected_suite(
                path,
                "zero_browser_suite",
                "EmptyBrowserTests",
                ("test_required",),
            )

    def test_renamed_required_method_fails_closed(self):
        temporary, path = self._module(
            """
            import unittest
            class RenamedBrowserTests(unittest.TestCase):
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
                "renamed_browser_suite",
                "RenamedBrowserTests",
                ("test_required",),
            )

    def test_skipped_required_method_reports_zero_executed_and_fails(self):
        temporary, path = self._module(
            """
            import unittest
            class SkippedBrowserTests(unittest.TestCase):
                @unittest.skip('synthetic missing browser')
                def test_required(self):
                    pass
            """
        )
        self.addCleanup(temporary.cleanup)
        suite = load_selected_suite(
            path,
            "skipped_browser_suite",
            "SkippedBrowserTests",
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
            class PassingBrowserTests(unittest.TestCase):
                def test_required(self):
                    pass
            """
        )
        self.addCleanup(temporary.cleanup)
        suite = load_selected_suite(
            path,
            "passing_browser_suite",
            "PassingBrowserTests",
            ("test_required",),
        )
        ok, summary = execute_suite(suite, 1, stream=io.StringIO())
        self.assertTrue(ok)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["executed"], 1)
        self.assertEqual(summary["skipped"], 0)


if __name__ == "__main__":
    unittest.main()
