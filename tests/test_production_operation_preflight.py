import json
import unittest
from urllib.parse import parse_qs, urlsplit

from scripts.production_operation_preflight import (
    PreflightError,
    parse_boolean,
    read_exact_sha_runs,
    reject_overlapping_exact_sha_run,
    validate_request,
)


SHA = "a" * 40
AUTH = "task:owner/decision:deploy-2026-08-23"


def build(build_id, sha=SHA, *, reason="individualCI", status="inProgress"):
    return {"id": build_id, "sourceVersion": sha, "reason": reason, "status": status}


class BuildResponse:
    def __init__(self, value, continuation=""):
        self.value = value
        self.headers = (
            {"x-ms-continuationtoken": continuation} if continuation else {}
        )

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"value": self.value}).encode()


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
    def read_runs(self, opener):
        return read_exact_sha_runs(
            collection_uri="https://dev.azure.com/peerslate19/",
            project_id="project-id",
            definition_id="1",
            source_version=SHA,
            token="secret-token",
            opener=opener,
        )

    def test_all_nonterminal_automatic_ci_statuses_block_production(self):
        for status in ("notStarted", "inProgress", "postponed", "cancelling"):
            for reason in ("individualCI", "batchedCI"):
                with self.subTest(status=status, reason=reason), self.assertRaisesRegex(
                    PreflightError, "still active"
                ):
                    reject_overlapping_exact_sha_run(
                        [build(510, reason=reason, status=status)],
                        current_build_id="511",
                    )

    def test_manual_or_current_run_does_not_block(self):
        reject_overlapping_exact_sha_run(
            [build(510, reason="manual"), build(511)], current_build_id="511"
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

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return BuildResponse([build(1), build(2, "b" * 40)])

        runs = read_exact_sha_runs(
            collection_uri="https://dev.azure.com/peerslate19/",
            project_id="project-id",
            definition_id="1",
            source_version=SHA,
            token="secret-token",
            opener=opener,
        )
        self.assertEqual([build(1)], runs)
        self.assertNotIn("sourceVersion=", captured["url"])
        self.assertIn("branchName=refs%2Fheads%2Fmain", captured["url"])
        query = parse_qs(urlsplit(captured["url"]).query)
        self.assertEqual(["45"], query["statusFilter"])
        self.assertEqual(["1"], query["definitions"])
        self.assertEqual("Bearer secret-token", captured["authorization"])
        self.assertNotIn("secret-token", captured["url"])

    def test_azure_query_checks_continuation_pages(self):
        urls = []
        pages = [
            BuildResponse([build(1, "b" * 40)], "page-two"),
            BuildResponse([build(2)]),
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
        self.assertEqual([build(2)], runs)
        self.assertIn("continuationToken=page-two", urls[1])
        self.assertEqual(["45"], parse_qs(urlsplit(urls[1]).query)["statusFilter"])

    def test_completed_history_is_excluded_before_bounded_pagination(self):
        completed_history = [
            build(build_id, "b" * 40, status="completed")
            for build_id in range(1, 1201)
        ]
        active = build(1202)
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            query = parse_qs(urlsplit(request.full_url).query)
            self.assertEqual(["45"], query["statusFilter"])
            self.assertEqual(["refs/heads/main"], query["branchName"])
            returned = [run for run in completed_history + [active]
                        if run["status"] != "completed"]
            return BuildResponse(returned)

        self.assertEqual([active], self.read_runs(opener))
        self.assertEqual(1, len(calls))

    def test_multiple_active_pages_check_all_statuses_and_exact_sha(self):
        pages = [
            BuildResponse([build(1, "b" * 40, status="notStarted")], "two"),
            BuildResponse([build(2, status="inProgress")], "three"),
            BuildResponse([build(3, status="postponed")], "four"),
            BuildResponse([build(4, status="cancelling")]),
        ]
        seen = []

        def opener(request, timeout):
            seen.append(parse_qs(urlsplit(request.full_url).query))
            return pages.pop(0)

        self.assertEqual(
            [build(2, status="inProgress"), build(3, status="postponed"),
             build(4, status="cancelling")],
            self.read_runs(opener),
        )
        self.assertEqual(4, len(seen))
        self.assertEqual(["two"], seen[1]["continuationToken"])
        self.assertEqual(["three"], seen[2]["continuationToken"])
        self.assertEqual(["four"], seen[3]["continuationToken"])
        self.assertTrue(all(query["statusFilter"] == ["45"] for query in seen))

    def test_repeated_continuation_is_refused(self):
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            return BuildResponse([], "same-token")

        with self.assertRaisesRegex(PreflightError, "repeated a token"):
            self.read_runs(opener)
        self.assertEqual(2, len(calls))

    def test_continuation_page_cap_is_refused(self):
        count = 0

        def opener(request, timeout):
            nonlocal count
            count += 1
            return BuildResponse([], f"page-{count}")

        with self.assertRaisesRegex(PreflightError, "exceeded its safe bound"):
            self.read_runs(opener)
        self.assertEqual(20, count)

    def test_malformed_envelope_or_run_is_refused_even_for_other_sha(self):
        class RawResponse(BuildResponse):
            def read(self):
                return json.dumps(self.value).encode()

        bad_payloads = [
            [], {"value": {}}, {"value": [None]},
            {"value": [{"id": 1, "sourceVersion": "b" * 40}]},
            {"value": [build(1, "b" * 40, status="completed")]},
            {"value": [build(1, "b" * 40, reason="")]},
            {"value": [build(1, "b" * 40, reason="unrecognizedCI")]},
            {"value": [build(1, "b" * 40, reason=" individualCI ")]},
            {"value": [build(1, "b" * 40, reason="none")]},
            {"value": [build(1, "b" * 40) | {"id": "1"}]},
            {"value": [build(1, "not-a-sha")]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload), self.assertRaisesRegex(
                PreflightError, "invalid"
            ):
                self.read_runs(lambda request, timeout: RawResponse(payload))

    def test_documented_non_ci_reasons_remain_allowed(self):
        reasons = (
            "manual", "schedule", "scheduleForced", "userCreated",
            "validateShelveset", "checkInShelveset", "pullRequest",
            "buildCompletion", "resourceTrigger", "triggered",
        )
        for reason in reasons:
            with self.subTest(reason=reason):
                run = build(510, reason=reason)
                runs = self.read_runs(
                    lambda request, timeout: BuildResponse([run])
                )
                self.assertEqual([run], runs)
                reject_overlapping_exact_sha_run(runs, current_build_id="511")

    def test_unknown_or_whitespace_exact_sha_reason_fails_before_classification(self):
        for reason in ("unrecognizedCI", " ", " individualCI "):
            with self.subTest(reason=reason), self.assertRaisesRegex(
                PreflightError, "invalid run"
            ):
                self.read_runs(
                    lambda request, timeout: BuildResponse([build(510, reason=reason)])
                )

    def test_transport_and_json_errors_fail_closed_without_token(self):
        def opener(request, timeout):
            raise OSError("network unavailable")

        with self.assertRaisesRegex(PreflightError, "could not read") as caught:
            self.read_runs(opener)
        self.assertNotIn("secret-token", str(caught.exception))

        class BadJsonResponse(BuildResponse):
            def read(self):
                return b"{bad-json"

        with self.assertRaisesRegex(PreflightError, "could not read"):
            self.read_runs(lambda request, timeout: BadJsonResponse([]))


if __name__ == "__main__":
    unittest.main()
