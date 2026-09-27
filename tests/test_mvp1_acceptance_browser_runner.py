"""Fail-closed G collection and preserved browser CI admission."""
import io
from pathlib import Path
import tempfile
import unittest
from scripts import run_mvp1_acceptance_browser_tests as runner


class Mvp1BrowserRunnerTests(unittest.TestCase):
    def test_exact_required_collection(self):
        suite = runner.selected_suite()
        self.assertEqual(suite.countTestCases(), len(runner.EXPECTED_METHODS) + len(runner.INTAKE_METHODS))

    def test_missing_empty_changed_and_skipped_suites_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'suite.py'
            with self.assertRaises(runner.BrowserCiError):
                runner.load_selected_suite(path, 'missing_g', 'Tests', ('test_one',))
            path.write_text('import unittest\nclass Tests(unittest.TestCase):\n    pass\n')
            with self.assertRaises(runner.BrowserCiError):
                runner.load_selected_suite(path, 'empty_g', 'Tests', ('test_one',))
            path.write_text('import unittest\nclass Tests(unittest.TestCase):\n    @unittest.skip("missing browser")\n    def test_one(self): pass\n')
            with self.assertRaises(runner.BrowserCiError):
                runner.load_selected_suite(path, 'changed_g', 'Tests', ('test_other',))
            suite = runner.load_selected_suite(path, 'skipped_g', 'Tests', ('test_one',))
            ok, result = runner.execute_suite(suite, 1, stream=io.StringIO())
            self.assertFalse(ok)
            self.assertEqual(result['skipped'], 1)

    def test_pipeline_keeps_existing_required_browser_gates(self):
        pipeline = (runner.ROOT / 'azure-pipelines.yml').read_text(encoding='utf-8')
        block = pipeline.split('- job: InterviewStudioBrowserCI', 1)[1].split('- job: BuildJob', 1)[0]
        for filename in ('run_interview_browser_ci.py', 'run_interview_review_http_browser.py',
                         'run_resume_media_browser_tests.py', 'run_resume_publication_browser_tests.py',
                         'run_mvp1_acceptance_browser_tests.py'):
            command = 'python scripts/' + filename
            self.assertEqual(block.count(command), 1)
            step = block.split(command, 1)[1].split('\n          - ', 1)[0]
            self.assertIn("and(succeeded(), ne(variables['ProveBrowserDisposition.deliveryControlOnly'], 'true'))", step)
            self.assertNotIn('continueonerror', step.lower())
