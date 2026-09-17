import io
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.run_interview_browser_ci import (
    BrowserCiError,
    CLASS_NAME,
    EXPECTED_METHODS,
    MODULE_FILE,
    MODULE_NAME,
    execute_suite,
    load_selected_suite,
    require_module_file,
)


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "azure-pipelines.yml"
BROWSER_JOB = "InterviewStudioBrowserCI"
RUNNER_COMMAND = "python scripts/run_interview_browser_ci.py"
FULL_PRODUCT_CONDITION = "and(succeeded(), ne(variables['ProveBrowserDisposition.deliveryControlOnly'], 'true'))"


def _meaningful_yaml_lines(path: Path) -> list[tuple[int, str]]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("\t"):
            raise AssertionError("pipeline YAML must not use tab indentation")
        content = raw.lstrip(" ")
        if not content or content.startswith("#"):
            continue
        lines.append((len(raw) - len(content), content))
    return lines


def _exact_yaml_block(
    lines: list[tuple[int, str]], indent: int, marker: str
) -> list[tuple[int, str]]:
    matches = [
        index
        for index, (line_indent, content) in enumerate(lines)
        if line_indent == indent and content == marker
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly one YAML node {marker!r} at indent {indent}"
        )
    start = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index][0] <= indent:
            end = index
            break
    return lines[start + 1 : end]


def _mapping(lines: list[tuple[int, str]], indent: int) -> dict[str, str]:
    fields = {}
    for index, (line_indent, content) in enumerate(lines):
        if line_indent != indent or ":" not in content:
            continue
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in fields:
            raise AssertionError(f"duplicate scoped YAML key: {key}")
        if value in {"|", "|-", ">", ">-"}:
            scalar = []
            for nested_indent, nested_content in lines[index + 1 :]:
                if nested_indent <= indent:
                    break
                scalar.append(nested_content)
            value = ("\n" if value.startswith("|") else " ").join(scalar)
        fields[key] = value.strip("'\"")
    return fields


def _browser_job_contract() -> tuple[dict[str, str], list[dict[str, str]]]:
    pipeline = _meaningful_yaml_lines(PIPELINE_FILE)
    build_stage = _exact_yaml_block(pipeline, 2, "- stage: Build")
    browser_job = _exact_yaml_block(build_stage, 6, f"- job: {BROWSER_JOB}")
    job_fields = _mapping(browser_job, 8)
    steps_block = _exact_yaml_block(browser_job, 8, "steps:")
    starts = [
        index
        for index, (indent, content) in enumerate(steps_block)
        if indent == 10 and content.startswith("- ")
    ]
    steps = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(steps_block)
        first_indent, first_content = steps_block[start]
        normalized = [(first_indent + 2, first_content[2:])]
        normalized.extend(steps_block[start + 1 : end])
        steps.append(_mapping(normalized, 12))
    if not steps:
        raise AssertionError("browser CI job has no parsed steps")
    return job_fields, steps


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

    def test_required_pipeline_job_invokes_only_the_strict_runner(self):
        job, steps = _browser_job_contract()
        self.assertNotIn("condition", job)
        self.assertIn(job.get("continueOnError", "false").lower(), {"false", "no", "off"})

        scripts = [step["script"].strip() for step in steps if "script" in step]
        runner_mentions = [script for script in scripts if "run_interview_browser_ci.py" in script]
        self.assertEqual(runner_mentions, [RUNNER_COMMAND])
        self.assertFalse(
            [script for script in scripts if "test_interview_studio_operability_browser" in script],
            "the required job must not invoke the browser unittest module directly",
        )

        runner_step = next(step for step in steps if step.get("script", "").strip() == RUNNER_COMMAND)
        self.assertEqual(FULL_PRODUCT_CONDITION, runner_step.get("condition"))
        self.assertIn(
            runner_step.get("continueOnError", "false").lower(),
            {"false", "no", "off"},
        )
        self.assertIn(
            runner_step.get("enabled", "true").lower(),
            {"true", "yes", "on"},
            "the strict runner step must be enabled",
        )
        for step in steps:
            self.assertIn(
                step.get("continueOnError", "false").lower(),
                {"false", "no", "off"},
                f"browser CI step can ignore failure: {step}",
            )
        for command in (
            "python scripts/run_interview_browser_ci.py",
            "python scripts/run_interview_review_http_browser.py",
            "python scripts/run_resume_media_browser_tests.py",
        ):
            required = next(step for step in steps if step.get("script", "").strip() == command)
            self.assertEqual(FULL_PRODUCT_CONDITION, required.get("condition"))
        self.assertTrue(any(
            "tests.test_delivery_change_classification" in step.get("script", "")
            and step.get("condition") == "and(succeeded(), eq(variables['ProveBrowserDisposition.deliveryControlOnly'], 'true'))"
            for step in steps
        ))

    def test_actual_suite_import_matches_contract_without_execution_or_live_access(self):
        probe = textwrap.dedent(
            """
            import sys
            import types
            from unittest.mock import patch

            from scripts.run_interview_browser_ci import (
                CLASS_NAME,
                EXPECTED_METHODS,
                MODULE_FILE,
                MODULE_NAME,
                load_selected_suite,
            )

            def forbidden(*_args, **_kwargs):
                raise AssertionError("browser or account access occurred during import")

            fake_playwright = types.ModuleType("playwright")
            fake_playwright.__path__ = []
            fake_sync_api = types.ModuleType("playwright.sync_api")
            fake_sync_api.sync_playwright = forbidden
            fake_playwright.sync_api = fake_sync_api

            with patch.dict(
                sys.modules,
                {"playwright": fake_playwright, "playwright.sync_api": fake_sync_api},
            ):
                with patch("identity.database_service.first_row", side_effect=forbidden), patch(
                    "identity.database_service.execute_procedure", side_effect=forbidden
                ):
                    if MODULE_NAME in sys.modules:
                        raise AssertionError("selected suite was already cached")
                    suite = load_selected_suite(
                        MODULE_FILE, MODULE_NAME, CLASS_NAME, EXPECTED_METHODS
                    )
                    if suite.countTestCases() != len(EXPECTED_METHODS) or len(EXPECTED_METHODS) != 11:
                        raise AssertionError("actual selected suite count changed")
                    if MODULE_NAME in sys.modules:
                        raise AssertionError("selected suite leaked into the module cache")

            print("actual-suite-contract=11")
            """
        )
        environment = os.environ.copy()
        environment.pop("PEERSLATE_INTERVIEW_EVIDENCE_DIR", None)
        environment["ANTHROPIC_API_KEY"] = "test-key-for-ci-only"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [os.sys.executable, "-B", "-c", probe],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "actual-suite-contract=11")

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
