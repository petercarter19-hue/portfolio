"""Pipeline contract for the required Interview Review HTTP browser runner."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.test_interview_browser_ci_runner import (
    BROWSER_JOB,
    PIPELINE_FILE,
    RUNNER_COMMAND as ELEVEN_TEST_RUNNER,
    _browser_job_contract,
    _exact_yaml_block,
    _meaningful_yaml_lines,
)


REVIEW_HTTP_RUNNER = "python scripts/run_interview_review_http_browser.py"
BACKEND_DISCOVERY = "python -m unittest discover -s tests -q"


def _job_contents(job_marker: str) -> list[str]:
    pipeline = _meaningful_yaml_lines(PIPELINE_FILE)
    build_stage = _exact_yaml_block(pipeline, 2, "- stage: Build")
    job = _exact_yaml_block(build_stage, 6, job_marker)
    return [content for _indent, content in job]


class InterviewReviewHttpBrowserCiTests(unittest.TestCase):
    def test_required_browser_job_invokes_review_http_runner_fail_closed(self):
        job, steps = _browser_job_contract()
        self.assertEqual(Path(PIPELINE_FILE).name, "azure-pipelines.yml")
        self.assertEqual(BROWSER_JOB, "InterviewStudioBrowserCI")
        self.assertNotIn("condition", job)
        self.assertIn(job.get("continueOnError", "false").lower(), {"false", "no", "off"})

        scripts = [step["script"].strip() for step in steps if "script" in step]
        self.assertIn(ELEVEN_TEST_RUNNER, scripts)
        review_mentions = [
            script for script in scripts if "run_interview_review_http_browser.py" in script
        ]
        self.assertEqual(review_mentions, [REVIEW_HTTP_RUNNER])
        self.assertNotIn(
            BACKEND_DISCOVERY,
            scripts,
            "the browser job must not duplicate ordinary backend discovery",
        )
        self.assertFalse(
            [script for script in scripts if "test_interview_review_http_browser" in script],
            "the required job must not invoke the Review HTTP unittest module directly",
        )
        self.assertFalse(
            [script for script in scripts if "|| true" in script or "||true" in script],
            "browser CI scripts must not ignore failures",
        )

        runner_step = next(
            step for step in steps if step.get("script", "").strip() == REVIEW_HTTP_RUNNER
        )
        self.assertNotIn("condition", runner_step)
        self.assertIn(
            runner_step.get("continueOnError", "false").lower(),
            {"false", "no", "off"},
        )
        self.assertIn(
            runner_step.get("enabled", "true").lower(),
            {"true", "yes", "on"},
            "the Review HTTP runner step must be enabled",
        )
        for step in steps:
            self.assertIn(
                step.get("continueOnError", "false").lower(),
                {"false", "no", "off"},
                f"browser CI step can ignore failure: {step}",
            )
            self.assertNotIn("enabled: false", str(step).lower())

    def test_ordinary_backend_discovery_remains_in_build_job(self):
        contents = _job_contents("- job: BuildJob")
        self.assertTrue(
            any(BACKEND_DISCOVERY in content for content in contents),
            "ordinary backend discovery must remain in BuildJob",
        )
        self.assertFalse(
            any(REVIEW_HTTP_RUNNER in content for content in contents),
            "the Review HTTP runner belongs in InterviewStudioBrowserCI, not BuildJob",
        )


if __name__ == "__main__":
    unittest.main()
