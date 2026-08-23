import json
import unittest

from scripts.production_operation_preflight import (
    PreflightError,
    parse_boolean,
    read_exact_sha_runs,
    reject_overlapping_exact_sha_run,
    validate_request,
)


SHA = "a" * 40
AUTH = "task:owner/decision:deploy-2026-08-23"


class ProductionOperationRequestTests(unittest.TestCase):
    def request(self, **overrides):
        values = {
            "build_reason": "IndividualCI",
            "source_branch": "refs/heads/main",
            "source_version": SHA,
            "force_production_deploy": False,
            "manual_source_version": "",
            "production_authorization_reference": "",
            "schema_action": "none",
            "schema_migration_id": "",
            "schema_rollback_confirm": "",
        }
        values.update(overrides)
        return validate_request(**values)

    def test_automatic_main_is_ci_only(self):
        operation = self.request()
        self.assertFalse(operation.deploy_application)
        self.assertEqual("none", operation.schema_action)
        self.assertEqual("", operation.authorization_reference)

    def test_manual_deployment_requires_exact_sha_and_owner_reference(self):
        operation = self.request(
            build_reason="Manual",
            force_production_deploy=True,
            manual_source_version=SHA,
            production_authorization_reference=AUTH,
        )
        self.assertTrue(operation.deploy_application)
        self.assertEqual(AUTH, operation.authorization_reference)

        for changes, phrase in (
            ({"manual_source_version": "b" * 40}, "manualProductionSourceVersion"),
            ({"production_authorization_reference": ""}, "productionAuthorizationReference"),
            ({"production_authorization_reference": " short "}, "productionAuthorizationReference"),
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                PreflightError, phrase
            ):
                request = {
                    "build_reason": "Manual",
                    "force_production_deploy": True,
                    "manual_source_version": SHA,
                    "production_authorization_reference": AUTH,
                }
                request.update(changes)
                self.request(**request)

    def test_automatic_or_nonmain_deployment_is_refused(self):
        with self.assertRaisesRegex(PreflightError, "manual-only"):
            self.request(
                force_production_deploy=True,
                manual_source_version=SHA,
                production_authorization_reference=AUTH,
            )
        with self.assertRaisesRegex(PreflightError, "refs/heads/main"):
            self.request(source_branch="refs/heads/work/example")

    def test_sha_and_authorization_inputs_cannot_float_without_deploy(self):
        for changes in (
            {"manual_source_version": SHA},
            {"production_authorization_reference": AUTH},
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                PreflightError, "allowed only"
            ):
                self.request(build_reason="Manual", **changes)

    def test_application_and_schema_cannot_share_a_run(self):
        with self.assertRaisesRegex(PreflightError, "cannot share one run"):
            self.request(
                build_reason="Manual",
                force_production_deploy=True,
                manual_source_version=SHA,
                production_authorization_reference=AUTH,
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

    def test_boolean_is_strict(self):
        self.assertFalse(parse_boolean("false"))
        self.assertTrue(parse_boolean("TRUE"))
        with self.assertRaises(PreflightError):
            parse_boolean("yes")


class ExactShaRunTests(unittest.TestCase):
    def test_active_automatic_ci_for_same_sha_blocks_production(self):
        with self.assertRaisesRegex(PreflightError, "still active"):
            reject_overlapping_exact_sha_run(
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

    def test_completed_automatic_ci_is_expected_and_does_not_block(self):
        reject_overlapping_exact_sha_run(
            [
                {
                    "id": 510,
                    "reason": "batchedCI",
                    "status": "completed",
                    "result": "succeeded",
                },
                {
                    "id": 509,
                    "reason": "individualCI",
                    "status": "completed",
                    "result": "failed",
                },
            ],
            current_build_id="511",
        )

    def test_azure_query_uses_bearer_token_and_filters_exact_sha(self):
        captured = {}

        class Response:
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(
                    {
                        "value": [
                            {"id": 1, "sourceVersion": SHA},
                            {"id": 2, "sourceVersion": "b" * 40},
                        ]
                    }
                ).encode()

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
        self.assertEqual([{"id": 1, "sourceVersion": SHA}], runs)
        self.assertNotIn("sourceVersion=", captured["url"])
        self.assertIn("branchName=refs%2Fheads%2Fmain", captured["url"])
        self.assertEqual("Bearer secret-token", captured["authorization"])
        self.assertNotIn("secret-token", captured["url"])

    def test_azure_query_checks_continuation_pages(self):
        urls = []

        class Response:
            def __init__(self, value, continuation=""):
                self.value = value
                self.headers = (
                    {"x-ms-continuationtoken": continuation}
                    if continuation
                    else {}
                )

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps({"value": self.value}).encode()

        pages = [
            Response([{"id": 1, "sourceVersion": "b" * 40}], "page-two"),
            Response([{"id": 2, "sourceVersion": SHA}]),
        ]

        def opener(request, timeout):
            urls.append(request.full_url)
            self.assertEqual(20, timeout)
            return pages.pop(0)

        runs = read_exact_sha_runs(
            collection_uri="https://dev.azure.com/peerslate19/",
            project_id="project-id",
            definition_id="1",
            source_version=SHA,
            token="secret-token",
            opener=opener,
        )
        self.assertEqual([{"id": 2, "sourceVersion": SHA}], runs)
        self.assertIn("continuationToken=page-two", urls[1])


if __name__ == "__main__":
    unittest.main()
