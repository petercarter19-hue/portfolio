from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from qa.synthetic_member.cli import main
from qa.synthetic_member.contracts import JOURNEYS


SOURCE_COMMIT = "b" * 40


class CliTests(unittest.TestCase):
    def test_plan_lists_the_complete_matrix(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["plan", "--json"])

        self.assertEqual(result, 0)
        records = json.loads(output.getvalue())
        self.assertEqual(len(records), len(JOURNEYS))
        self.assertIn(
            "member_a_cannot_export_member_b",
            {record["journey_id"] for record in records},
        )

    def test_init_record_and_validate_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            init_output = io.StringIO()
            with contextlib.redirect_stdout(init_output):
                self.assertEqual(
                    main(
                        [
                            "init",
                            "--output",
                            str(path),
                            "--run-id",
                            "qa-round-trip",
                            "--source-commit",
                            SOURCE_COMMIT,
                            "--mode",
                            "local_contract",
                            "--browser",
                            "edge",
                            "--browser-version",
                            "140.0",
                        ]
                    ),
                    0,
                )
            self.assertEqual(json.loads(init_output.getvalue()), {"result": "created"})
            self.assertNotIn(str(path), init_output.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "record-journey",
                            "--manifest",
                            str(path),
                            "--journey",
                            "signed_out_private_baseline",
                            "--status",
                            "pass",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["validate", "--manifest", str(path)]),
                    0,
                )

            saved = json.loads(path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in saved["journeys"]
                if item["journey_id"] == "signed_out_private_baseline"
            )
            self.assertEqual(record["status"], "pass")
            self.assertEqual(record["observed_outcome"], "private_data_absent")

    def test_final_validation_refuses_a_pending_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            with contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "init",
                        "--output",
                        str(path),
                        "--run-id",
                        "qa-pending",
                        "--source-commit",
                        SOURCE_COMMIT,
                        "--mode",
                        "local_contract",
                        "--browser",
                        "edge",
                        "--browser-version",
                        "140.0",
                    ]
                )
            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(["validate", "--manifest", str(path), "--final"])
            self.assertEqual(raised.exception.code, 2)

    def test_init_refuses_to_overwrite_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            original = "existing evidence\n"
            path.write_text(original, encoding="utf-8")
            error = io.StringIO()

            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(error):
                    main(
                        [
                            "init",
                            "--output",
                            str(path),
                            "--run-id",
                            "qa-no-overwrite",
                            "--source-commit",
                            SOURCE_COMMIT,
                            "--mode",
                            "local_contract",
                            "--browser",
                            "edge",
                            "--browser-version",
                            "140.0",
                        ]
                    )

            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertNotIn(str(path), error.getvalue())

    def test_manifest_storage_inside_repository_is_refused(self):
        root = Path(__file__).resolve().parents[2]
        path = root / "qa" / "synthetic_member" / "forbidden-evidence-output.json"
        self.assertFalse(path.exists())
        error = io.StringIO()

        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(error):
                main(
                    [
                        "init",
                        "--output",
                        str(path),
                        "--run-id",
                        "qa-external-only",
                        "--source-commit",
                        SOURCE_COMMIT,
                        "--mode",
                        "local_contract",
                        "--browser",
                        "edge",
                        "--browser-version",
                        "140.0",
                    ]
                )

        self.assertEqual(raised.exception.code, 2)
        self.assertFalse(path.exists())
        self.assertNotIn(str(path), error.getvalue())

    def test_parser_refusals_do_not_echo_rejected_values(self):
        marker = "sensitive-marker-should-not-echo"
        for arguments in (
            [
                "init",
                "--output",
                "unused.json",
                "--run-id",
                "qa-parser-refusal",
                "--source-commit",
                SOURCE_COMMIT,
                "--mode",
                marker,
                "--browser",
                "edge",
                "--browser-version",
                "140.0",
            ],
            [
                "record-cleanup",
                "--manifest",
                "unused.json",
                "--created-member-a",
                marker,
            ],
        ):
            with self.subTest(arguments=arguments[0]):
                error = io.StringIO()
                with self.assertRaises(SystemExit) as raised:
                    with contextlib.redirect_stderr(error):
                        main(arguments)
                self.assertEqual(raised.exception.code, 2)
                self.assertNotIn(marker, error.getvalue())

    def test_manifest_with_forbidden_field_is_refused_before_update(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            with contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "init",
                        "--output",
                        str(path),
                        "--run-id",
                        "qa-refusal",
                        "--source-commit",
                        SOURCE_COMMIT,
                        "--mode",
                        "local_contract",
                        "--browser",
                        "edge",
                        "--browser-version",
                        "140.0",
                    ]
                )
            value = json.loads(path.read_text(encoding="utf-8"))
            value["email"] = "person@example.com"
            path.write_text(json.dumps(value), encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(
                        [
                            "record-journey",
                            "--manifest",
                            str(path),
                            "--journey",
                            "signed_out_private_baseline",
                            "--status",
                            "pass",
                        ]
                    )
            self.assertEqual(raised.exception.code, 2)

    def test_entry_point_source_has_no_browser_network_or_identity_provider(self):
        root = Path(__file__).resolve().parents[2]
        source = "\n".join(
            (root / "qa" / "synthetic_member" / name).read_text(encoding="utf-8")
            for name in ("contracts.py", "cli.py")
        ).lower()
        for forbidden_import in (
            "import requests",
            "import httpx",
            "import playwright",
            "import selenium",
            "import azure.identity",
            "import msal",
        ):
            with self.subTest(forbidden_import=forbidden_import):
                self.assertNotIn(forbidden_import, source)


if __name__ == "__main__":
    unittest.main()
