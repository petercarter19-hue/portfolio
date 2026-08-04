import io
import json
import unittest

from scripts.production_operation_preflight import (
    PreflightError,
    parse_boolean,
    read_exact_sha_runs,
    reject_duplicate_manual_fallback,
    validate_request,
)


SHA = "a" * 40


class ProductionOperationRequestTests(unittest.TestCase):
    def request(self, **overrides):
        values = {
            "build_reason": "IndividualCI",
            "source_branch": "refs/heads/main",
            "source_version": SHA,
            "force_production_deploy": False,
            "manual_source_version": "",
            "schema_action": "none",
            "schema_migration_id": "",
            "schema_rollback_confirm": "",
        }
        values.update(overrides)
        return validate_request(**values)

    def test_automatic_main_is_an_application_operation(self):
        operation = self.request()
        self.assertTrue(operation.deploy_application)
        self.assertEqual("none", operation.schema_action)

    def test_manual_fallback_requires_exact_typed_sha(self):
        operation = self.request(
            build_reason="Manual",
            force_production_deploy=True,
            manual_source_version=SHA,
        )
        self.assertTrue(operation.deploy_application)

        with self.assertRaisesRegex(
            PreflightError, "manualProductionSourceVersion"
        ):
            self.request(
                build_reason="Manual",
                force_production_deploy=True,
                manual_source_version="b" * 40,
            )

    def test_application_and_schema_cannot_share_a_run(self):
        with self.assertRaisesRegex(PreflightError, "cannot share one run"):
            self.request(
                build_reason="Manual",
                force_production_deploy=True,
                manual_source_version=SHA,
                schema_action="report",
            )

    def test_schema_is_manual_and_apply_requires_one_id(self):
        with self.assertRaisesRegex(PreflightError, "manual-only"):
            self.request(schema_action="report")
        with self.assertRaisesRegex(PreflightError, "migration id"):
            self.request(build_reason="Manual", schema_action="apply")

        operation = self.request(
            build_reason="Manual",
            schema_action="apply",
            schema_migration_id="PS-EXAMPLE-001",
        )
        self.assertFalse(operation.deploy_application)
        self.assertEqual("apply", operation.schema_action)

    def test_rollback_requires_two_matching_ids(self):
        with self.assertRaisesRegex(PreflightError, "exactly repeat"):
            self.request(
                build_reason="Manual",
                schema_action="rollback",
                schema_migration_id="PS-EXAMPLE-001",
                schema_rollback_confirm="PS-EXAMPLE-002",
            )

    def test_false_by_default_boolean_is_strict(self):
        self.assertFalse(parse_boolean("false"))
        self.assertTrue(parse_boolean("TRUE"))
        with self.assertRaises(PreflightError):
            parse_boolean("yes")


class ExactShaRunTests(unittest.TestCase):
    def test_active_or_successful_automatic_run_blocks_fallback(self):
        with self.assertRaisesRegex(PreflightError, "still active"):
            reject_duplicate_manual_fallback(
                [
                    {
                        "id": 510,
                        "reason": "individualCI",
                        "status": "inProgress",
                        "result": None,
                    }
                ],
                current_build_id="511",
            )

        with self.assertRaisesRegex(PreflightError, "already succeeded"):
            reject_duplicate_manual_fallback(
                [
                    {
                        "id": 510,
                        "reason": "batchedCI",
                        "status": "completed",
                        "result": "succeeded",
                    }
                ],
                current_build_id="511",
            )

    def test_failed_automatic_run_allows_deliberate_fallback(self):
        reject_duplicate_manual_fallback(
            [
                {
                    "id": 510,
                    "reason": "individualCI",
                    "status": "completed",
                    "result": "failed",
                },
                {
                    "id": 511,
                    "reason": "manual",
                    "status": "inProgress",
                },
            ],
            current_build_id="511",
        )

    def test_azure_query_uses_bearer_token_without_returning_it(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"value": [{"id": 1}]}).encode()

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return Response()

        runs = read_exact_sha_runs(
            collection_uri="https://dev.azure.com/peerslate19/",
            project_id="project-id",
            definition_id="1",
            source_version=SHA,
            token="secret-token",
            opener=opener,
        )
        self.assertEqual([{"id": 1}], runs)
        self.assertIn("sourceVersion=" + SHA, captured["url"])
        self.assertEqual("Bearer secret-token", captured["authorization"])
        self.assertNotIn("secret-token", captured["url"])


if __name__ == "__main__":
    unittest.main()
