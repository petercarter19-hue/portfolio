"""Browser-runner contract. Does not launch Chromium by itself."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.run_resume_publication_browser_tests import (
    CLASS_NAME,
    EXPECTED_METHODS,
    MODULE_FILE,
    load_selected_suite,
)


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "azure-pipelines.yml"
PUBLICATION_RUNNER = "python scripts/run_resume_publication_browser_tests.py"
FULL_PRODUCT_CONDITION = (
    "and(succeeded(), ne(variables['ProveBrowserDisposition.deliveryControlOnly'], 'true'))"
)
PRESERVED_RUNNERS = (
    "python scripts/run_interview_browser_ci.py",
    "python scripts/run_interview_review_http_browser.py",
    "python scripts/run_resume_media_browser_tests.py",
)


class ResumePublicationBrowserRunnerTests(unittest.TestCase):
    def test_required_method_set_is_exact(self):
        suite = load_selected_suite(
            MODULE_FILE,
            "publication_browser_contract",
            CLASS_NAME,
            EXPECTED_METHODS,
        )
        self.assertEqual(suite.countTestCases(), len(EXPECTED_METHODS))

    def test_required_ci_wires_fail_closed_publication_suite_without_weakening_existing_jobs(self):
        contents = PIPELINE_FILE.read_text(encoding="utf-8")
        self.assertNotIn("\t", contents)
        job_marker = "- job: InterviewStudioBrowserCI"
        start = contents.index(job_marker)
        rest = contents[start + len(job_marker) :]
        next_job = rest.find("\n      - job:")
        job = rest if next_job < 0 else rest[:next_job]
        self.assertIn(PUBLICATION_RUNNER, job)
        publication_index = job.index(PUBLICATION_RUNNER)
        window = job[publication_index : publication_index + 500]
        self.assertIn(FULL_PRODUCT_CONDITION, window)
        self.assertNotIn("continueOnError: true", window.lower())
        for command in PRESERVED_RUNNERS:
            self.assertIn(command, job)
            idx = job.index(command)
            nearby = job[idx : idx + 500]
            self.assertIn(FULL_PRODUCT_CONDITION, nearby)
            self.assertNotIn("continueOnError: true", nearby.lower())


if __name__ == "__main__":
    unittest.main()
