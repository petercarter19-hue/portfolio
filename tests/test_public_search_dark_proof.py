from __future__ import annotations

import copy
import compileall
import datetime as dt
import fnmatch
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_public_content_fixture_manifest as fixture_builder  # noqa: E402
import run_public_search_dark_proof as proof  # noqa: E402


def built_manifest() -> dict:
    return fixture_builder.build()


def candidate(document: dict, score: float = 1.0) -> dict:
    value = {name: copy.deepcopy(document[name]) for name in proof.INDEX_FIELDS}
    value["@search.score"] = score
    return value


def uuid(number: int) -> str:
    return f"{number:08x}-1111-4111-8111-{number:012x}"


def filled_cleanup_manifest() -> dict:
    template = json.loads(proof.DEFAULT_CLEANUP_TEMPLATE.read_text(encoding="utf-8"))
    subscription_id = uuid(1)
    template["service"]["subscription_id"] = subscription_id
    template["service"]["tenant_id"] = uuid(2)
    scope = (
        f"/subscriptions/{subscription_id}/resourceGroups/peerslate/"
        "providers/Microsoft.Search/searchServices/proj-default-srch-f0z1/"
        "indexes/peerslate-public-content-v1/providers/"
        "Microsoft.Authorization/roleAssignments/"
    )
    template["targets"]["role_assignment_resource_ids"] = [
        scope + uuid(3),
        scope + uuid(4),
    ]
    template["targets"]["service_principal_object_ids"] = [uuid(5), uuid(6)]
    template["targets"]["application_ids"] = [uuid(7), uuid(8)]
    template["confirmation_phrase_sha256"] = proof.sha256_text("TEARDOWN SEARCH 3F")
    return template


def matching_preflight_rows(manifest: dict, operation: str, target: str) -> list[dict]:
    targets = manifest["targets"]
    if operation == "preflight_role_assignment":
        index = targets["role_assignment_resource_ids"].index(target)
        return [
            {
                "id": target,
                "principalId": targets["service_principal_object_ids"][index],
                "roleDefinitionId": proof.EXPECTED_ROLE_DEFINITION_IDS[index],
            }
        ]
    if operation == "preflight_service_principal":
        index = targets["service_principal_object_ids"].index(target)
        return [{"id": target, "appId": targets["application_ids"][index]}]
    if operation == "preflight_application":
        return [{"appId": target}]
    return []


class CanonicalizationTests(unittest.TestCase):
    def test_manifest_reproduces_exact_historical_fixture_root(self):
        manifest = built_manifest()
        self.assertEqual(manifest["document_count"], 20)
        self.assertEqual(manifest["member_count"], 3)
        self.assertEqual(
            manifest["content_digest_root"],
            "52db612cf0dd21a5e63d95abbef758aaf8ed4de8094bc4dadee9f69e41786d2d",
        )
        proof.validate_fixture_manifest(manifest)

    def test_alias_order_and_unicode_form_are_digest_insensitive(self):
        document = copy.deepcopy(built_manifest()["documents"][3])
        expected = proof.canonical_digest(document)
        document["aliases"].reverse()
        document["title"] = "Ku\u0308bernetes Operations"
        document["title"] = proof.unicodedata.normalize("NFC", document["title"])
        document["title"] = proof.unicodedata.normalize("NFD", document["title"])
        # Use a decomposed form that normalizes to the same text only when possible.
        original = built_manifest()["documents"][3]
        document["title"] = proof.unicodedata.normalize("NFD", original["title"])
        self.assertEqual(proof.canonical_digest(document), expected)

    def test_optional_absent_and_null_have_same_digest(self):
        document = copy.deepcopy(built_manifest()["documents"][0])
        with_null = proof.canonical_digest(document)
        document.pop("period_label")
        self.assertEqual(proof.canonical_digest(document), with_null)

    def test_every_digest_field_mutation_changes_digest(self):
        source = built_manifest()["documents"][3]
        for field_name in proof.DIGEST_FIELDS:
            with self.subTest(field=field_name):
                mutated = copy.deepcopy(source)
                if field_name == "aliases":
                    mutated[field_name] = list(mutated[field_name]) + ["changed"]
                elif mutated[field_name] is None:
                    mutated[field_name] = "changed"
                else:
                    mutated[field_name] = str(mutated[field_name]) + " changed"
                self.assertNotEqual(proof.canonical_digest(mutated), source["projection_digest"])

    def test_manifest_rejects_unknown_keys_and_real_namespace(self):
        manifest = built_manifest()
        manifest["unknown"] = True
        with self.assertRaises(proof.ContractError):
            proof.validate_fixture_manifest(manifest)
        manifest = built_manifest()
        manifest["documents"][0]["document_id"] = "member_123"
        with self.assertRaises(proof.ContractError):
            proof.validate_fixture_manifest(manifest)


class SchemaAndQueryTests(unittest.TestCase):
    def test_schema_is_exact_twenty_field_lexical_contract(self):
        schema = proof.schema_body()
        proof.validate_index_schema(schema)
        fields = schema["fields"]
        self.assertEqual([item["name"] for item in fields], list(proof.INDEX_FIELDS))
        self.assertEqual(sum(item["searchable"] for item in fields), 5)
        self.assertEqual(sum(item["filterable"] for item in fields), 13)
        self.assertEqual(sum(item["sortable"] for item in fields), 3)
        self.assertTrue(all(item["stored"] for item in fields))
        self.assertIsNone(schema["semantic"])
        self.assertIsNone(schema["vectorSearch"])

    def test_schema_rejects_stored_or_semantic_claim_drift(self):
        schema = proof.schema_body()
        schema["fields"][0]["stored"] = False
        with self.assertRaises(proof.ContractError):
            proof.validate_index_schema(schema)
        schema = proof.schema_body()
        schema["semantic"] = {"configurations": []}
        with self.assertRaises(proof.ContractError):
            proof.validate_index_schema(schema)

    def test_query_body_pins_every_required_option(self):
        body = proof.build_query_body("  grid   migration  ")
        self.assertEqual(body["search"], "grid migration")
        self.assertEqual(body["queryType"], "simple")
        self.assertEqual(body["searchMode"], "all")
        self.assertEqual(body["searchFields"], ",".join(proof.SEARCH_FIELDS))
        self.assertEqual(body["filter"], "audience eq 'public' and schema_version eq '1'")
        self.assertEqual(body["orderby"], "search.score() desc,document_id asc")
        self.assertEqual(body["select"], ",".join(proof.INDEX_FIELDS))
        self.assertNotIn("*", body["select"])
        self.assertEqual(body["top"], 20)
        self.assertEqual(body["skip"], 0)

    def test_query_rejects_semantic_and_vector_nested_anywhere(self):
        body = proof.build_query_body("grid")
        for key, value in (
            ("queryType", "semantic"),
            ("vectorQueries", [{"vector": [1.0]}]),
            ("semanticConfiguration", "x"),
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(body)
                mutated["nested"] = {key: value}
                with self.assertRaises(proof.ContractError):
                    proof.assert_request_contract(mutated)

    def test_query_bounds_are_fail_closed(self):
        for kwargs in (
            {"skip": -1},
            {"skip": 200},
            {"top": 0},
            {"top": 21},
            {"skip": 190, "top": 20},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(proof.ContractError):
                proof.build_query_body("grid", **kwargs)

    def test_request_contract_rejects_search_field_drift(self):
        body = proof.build_query_body("grid")
        body["searchFields"] = ",".join(proof.SEARCH_FIELDS[:-1])
        with self.assertRaisesRegex(proof.ContractError, "searchFields"):
            proof.assert_request_contract(body)


class FenceAndSerializerTests(unittest.TestCase):
    def setUp(self):
        self.manifest = built_manifest()
        self.source = self.manifest["documents"][0]

    def test_valid_candidate_passes(self):
        fenced = proof.fence_candidates([candidate(self.source)], self.manifest)
        self.assertEqual([item["document_id"] for item in fenced], [self.source["document_id"]])

    def test_every_canonical_index_field_mutation_fails(self):
        for field_name in proof.CANONICAL_MATCH_FIELDS:
            with self.subTest(field=field_name):
                mutated = candidate(self.source)
                value = mutated[field_name]
                if isinstance(value, list):
                    mutated[field_name] = value + ["changed"]
                elif isinstance(value, str):
                    mutated[field_name] = value + " changed"
                else:
                    mutated[field_name] = "changed"
                mutated["projection_digest"] = proof.canonical_digest(mutated)
                self.assertEqual(proof.fence_candidates([mutated], self.manifest), [])

    def test_alias_reordering_and_unicode_normalization_pass(self):
        source = self.manifest["documents"][3]
        value = candidate(source)
        value["aliases"].reverse()
        value["title"] = proof.unicodedata.normalize("NFD", value["title"])
        value["projection_digest"] = proof.canonical_digest(value)
        fenced = proof.fence_candidates([value], self.manifest)
        self.assertEqual(len(fenced), 1)

    def test_unknown_slot_wrong_owner_revision_digest_and_visibility_fail(self):
        mutations = [
            ("projection_key", "unknown"),
            ("profile_key", "pk_synth_999"),
            ("publication_revision_key", "rev_other"),
            ("projection_digest", "cv1:" + "0" * 64),
            ("audience", "private"),
            ("schema_version", "2"),
            ("result_type", "secret"),
        ]
        for field_name, replacement in mutations:
            with self.subTest(field=field_name):
                value = candidate(self.source)
                value[field_name] = replacement
                self.assertEqual(proof.fence_candidates([value], self.manifest), [])

    def test_local_withdrawal_closes_without_network(self):
        withdrawn = copy.deepcopy(self.manifest)
        withdrawn["documents"][0]["withdrawn"] = True
        self.assertEqual(proof.fence_candidates([candidate(self.source)], withdrawn), [])

    def test_fifty_shuffles_preserve_score_then_id_order(self):
        values = [
            candidate(item, score=float((index % 3) + 1))
            for index, item in enumerate(self.manifest["documents"][:10])
        ]
        expected = [
            item["document_id"]
            for item in sorted(
                values,
                key=lambda item: (-item["@search.score"], item["document_id"]),
            )
        ]
        rng = random.Random(42)
        for _ in range(50):
            rng.shuffle(values)
            actual = [item["document_id"] for item in proof.fence_candidates(values, self.manifest)]
            self.assertEqual(actual, expected)

    def test_serializer_is_exact_and_constructs_from_local_source(self):
        value = candidate(self.source)
        fenced = proof.fence_candidates([value], self.manifest)
        value["title"] = "ATTACKER TITLE AFTER FENCE"
        value["destination"] = "attacker-destination"
        output = proof.serialize_public_results(fenced, self.manifest)
        self.assertEqual(set(output[0]), set(proof.PUBLIC_OUTPUT_FIELDS))
        self.assertEqual(output[0]["title"], self.source["title"])
        self.assertEqual(output[0]["destination"], self.source["destination"])
        self.assertFalse(set(output[0]) & {"document_id", "profile_key", "projection_digest"})

    def test_adaptive_paging_continues_until_six_survive(self):
        good = [candidate(item, 100 - index) for index, item in enumerate(self.manifest["documents"][:6])]
        bad = [candidate(item) for item in self.manifest["documents"][6:8]]
        for item in bad:
            item["audience"] = "private"
        pages = [bad, good[:2], good[2:4], good[4:6]]
        bodies = []

        def fetch(body):
            bodies.append(dict(body))
            return pages[len(bodies) - 1]

        output = proof.collect_fenced_results(
            fetch,
            "synthetic",
            self.manifest,
            page_size=2,
            max_candidates=8,
        )
        self.assertEqual(len(output), 6)
        self.assertEqual([body["skip"] for body in bodies], [0, 2, 4, 6])
        self.assertTrue(all(body["top"] == 2 for body in bodies))


class CensusAndBudgetTests(unittest.TestCase):
    def test_census_captures_body_shape_without_content_or_token(self):
        census = proof.RequestCensus()
        body = proof.build_query_body("top secret synthetic phrase")
        row = census.before_dispatch(
            transport="https",
            operation="query_page",
            method="POST",
            target="https://example.invalid/indexes/private/docs/search",
            api_version=proof.FUTURE_CONTRACT_API_VERSION,
            body=body,
        )
        census.finish(row, 200)
        encoded = json.dumps(census.rows)
        self.assertNotIn("top secret synthetic phrase", encoded)
        self.assertNotIn("example.invalid", encoded)
        self.assertNotIn("private/docs", encoded)
        self.assertIn("queryType", census.rows[0]["body_keys"])
        self.assertEqual(census.rows[0]["query_type"], "simple")
        self.assertFalse(census.rows[0]["semantic_or_vector"])

    def test_census_refuses_forbidden_body_before_recording(self):
        census = proof.RequestCensus()
        body = proof.build_query_body("synthetic")
        body["vectorQueries"] = []
        with self.assertRaises(proof.ContractError):
            census.before_dispatch(
                transport="https",
                operation="query_page",
                method="POST",
                target="target",
                body=body,
            )
        self.assertEqual(census.rows, [])

    def test_budget_persists_across_invocations(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            first = proof.PersistentBudget("a" * 64, state_path=state, max_process_requests=2)
            first.authorize("process")
            second = proof.PersistentBudget("a" * 64, state_path=state, max_process_requests=2)
            second.authorize("process")
            third = proof.PersistentBudget("a" * 64, state_path=state, max_process_requests=2)
            with self.assertRaises(proof.CeilingError):
                third.authorize("process")

    def test_budget_binds_manifest_and_enforces_bytes_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            budget = proof.PersistentBudget(
                "a" * 64,
                state_path=state,
                max_request_bytes=10,
            )
            with self.assertRaises(proof.CeilingError):
                budget.authorize("index", request_bytes=11)
            self.assertEqual(budget.counts["index_requests"], 0)
            budget.authorize("process")
            proof.PersistentBudget("a" * 64, state_path=state)
            with self.assertRaises(proof.ContractError):
                proof.PersistentBudget("b" * 64, state_path=state)

    def test_budget_enforces_document_and_request_count(self):
        budget = proof.PersistentBudget("a" * 64, max_documents=1, max_query_requests=1)
        budget.authorize("query", documents=1)
        with self.assertRaises(proof.CeilingError):
            budget.authorize("query")
        with self.assertRaises(proof.CeilingError):
            budget.authorize("index", documents=1)


class CleanupManifestTests(unittest.TestCase):
    def setUp(self):
        manifest = filled_cleanup_manifest()
        self.target_hash_patch = mock.patch.multiple(
            proof,
            EXPECTED_APPLICATION_ID_SHA256=tuple(
                proof.sha256_text(value.casefold())
                for value in manifest["targets"]["application_ids"]
            ),
            EXPECTED_ROLE_ASSIGNMENT_ID_SHA256=tuple(
                proof.sha256_text(value.casefold())
                for value in manifest["targets"]["role_assignment_resource_ids"]
            ),
        )
        self.target_hash_patch.start()
        self.addCleanup(self.target_hash_patch.stop)

    def test_committed_template_is_valid_only_as_template(self):
        template = json.loads(proof.DEFAULT_CLEANUP_TEMPLATE.read_text(encoding="utf-8"))
        proof.validate_cleanup_manifest(template, allow_placeholders=True)
        with self.assertRaises(proof.ContractError):
            proof.validate_cleanup_manifest(template, allow_placeholders=False)

    def test_filled_manifest_is_exact_and_plan_is_redacted(self):
        manifest = filled_cleanup_manifest()
        proof.validate_cleanup_manifest(manifest, allow_placeholders=False)
        plan = proof.build_teardown_plan(manifest)
        encoded = json.dumps(plan)
        self.assertNotIn(manifest["service"]["subscription_id"], encoded)
        for resource_id in manifest["targets"]["role_assignment_resource_ids"]:
            self.assertNotIn(resource_id, encoded)
        self.assertEqual(
            [step["action"] for step in plan["ordered_steps"]],
            [
                "preflight_exact_targets",
                "delete_role_assignment",
                "delete_index",
                "verify_index_absent",
                "delete_service_principal",
                "delete_application_registration",
                "verify_identity_targets_absent",
            ],
        )

    def test_manifest_rejects_ask_pete_wrong_scope_duplicates_and_extra_keys(self):
        variants = []
        ask = filled_cleanup_manifest()
        ask["service"]["name"] = "ask-pete-ai"
        ask["service"]["endpoint"] = "https://ask-pete-ai.search.windows.net"
        variants.append(ask)
        scope = filled_cleanup_manifest()
        scope["targets"]["role_assignment_resource_ids"][0] = (
            scope["targets"]["role_assignment_resource_ids"][0].replace(
                "peerslate-public-content-v1", "other-index"
            )
        )
        variants.append(scope)
        duplicate = filled_cleanup_manifest()
        duplicate["targets"]["application_ids"][1] = duplicate["targets"]["application_ids"][0]
        variants.append(duplicate)
        extra = filled_cleanup_manifest()
        extra["targets"]["search_service"] = "delete"
        variants.append(extra)
        for manifest in variants:
            with self.subTest(manifest=manifest), self.assertRaises(proof.ContractError):
                proof.validate_cleanup_manifest(manifest, allow_placeholders=False)

    def test_manifest_rejects_retargeting_or_date_extension(self):
        variants = []
        service = filled_cleanup_manifest()
        service["service"]["name"] = "different-service"
        service["service"]["endpoint"] = "https://different-service.search.windows.net"
        variants.append(service)
        extension = filled_cleanup_manifest()
        extension["teardown_not_before"] = "2026-08-24T23:59:00-05:00"
        extension["expires_at"] = "2026-08-24T23:59:00-05:00"
        variants.append(extension)
        authority = filled_cleanup_manifest()
        authority["authorization"]["authorized_by"] = "someone-else"
        variants.append(authority)
        application = filled_cleanup_manifest()
        application["targets"]["application_ids"][0] = uuid(99)
        variants.append(application)
        role = filled_cleanup_manifest()
        role["targets"]["role_assignment_resource_ids"][0] = (
            role["targets"]["role_assignment_resource_ids"][0].rsplit("/", 1)[0]
            + "/"
            + uuid(99)
        )
        variants.append(role)
        for manifest in variants:
            with self.subTest(manifest=manifest), self.assertRaises(proof.ContractError):
                proof.validate_cleanup_manifest(manifest, allow_placeholders=False)

    def test_teardown_refuses_before_not_before_and_allows_after_expiry(self):
        manifest = filled_cleanup_manifest()
        before = dt.datetime.fromisoformat("2026-08-23T23:58:59-05:00")
        with self.assertRaises(proof.ExecutionRefused):
            proof._ensure_teardown_time(manifest, before)
        after = dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00")
        proof._ensure_teardown_time(manifest, after)

    def test_teardown_requires_manifest_bound_confirmation(self):
        manifest = filled_cleanup_manifest()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(proof.ExecutionRefused):
                proof.execute_teardown(
                    manifest,
                    confirmation="wrong",
                    state_path=Path(directory) / "state.json",
                    census_path=Path(directory) / "census.json",
                    now=dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00"),
                )

    def test_teardown_preflight_refuses_mismatched_identity_before_delete(self):
        manifest = filled_cleanup_manifest()
        holder = {"operations": []}

        class MismatchedIdentityTransport:
            def __init__(self, budget, census):
                pass

            def process(self, argv, *, operation, target, allow_failure=False):
                holder["operations"].append(operation)
                if operation == "preflight_service_principal":
                    object_id = manifest["targets"]["service_principal_object_ids"][0]
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        stdout=json.dumps([{"id": object_id, "appId": uuid(99)}]),
                        stderr="",
                    )
                stdout = json.dumps(matching_preflight_rows(manifest, operation, target))
                return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(proof.ExecutionRefused, "not linked"):
                proof.execute_teardown(
                    manifest,
                    confirmation="TEARDOWN SEARCH 3F",
                    state_path=Path(directory) / "state.json",
                    census_path=Path(directory) / "census.json",
                    now=dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00"),
                    transport_factory=MismatchedIdentityTransport,
                )
        self.assertFalse(any(item.startswith("delete_") for item in holder["operations"]))

    def test_teardown_preflight_refuses_empty_relationships_before_delete(self):
        manifest = filled_cleanup_manifest()

        for missing_operation in (
            "preflight_role_assignment",
            "preflight_service_principal",
            "preflight_application",
        ):
            holder = {"operations": []}

            class EmptyRelationshipTransport:
                def __init__(self, budget, census):
                    pass

                def process(self, argv, *, operation, target, allow_failure=False):
                    holder["operations"].append(operation)
                    rows = (
                        []
                        if operation == missing_operation
                        else matching_preflight_rows(manifest, operation, target)
                    )
                    return subprocess.CompletedProcess(
                        argv,
                        0,
                        stdout=json.dumps(rows),
                        stderr="",
                    )

            with self.subTest(operation=missing_operation):
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaisesRegex(
                        proof.ExecutionRefused,
                        "exactly one pre-authorized target",
                    ):
                        proof.execute_teardown(
                            manifest,
                            confirmation="TEARDOWN SEARCH 3F",
                            state_path=Path(directory) / "state.json",
                            census_path=Path(directory) / "census.json",
                            now=dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00"),
                            transport_factory=EmptyRelationshipTransport,
                        )
                self.assertFalse(
                    any(item.startswith("delete_") for item in holder["operations"])
                )

    def test_exact_target_preflight_refuses_duplicate_matches(self):
        target = uuid(5)
        rows = [{"id": target}, {"id": target.upper()}]
        with self.assertRaisesRegex(proof.ExecutionRefused, "found 2"):
            proof._require_exact_target_row(
                rows,
                identifier=target,
                fields=("id",),
                label="service principal preflight",
            )

    def test_complete_teardown_sequence_uses_every_exact_target(self):
        manifest = filled_cleanup_manifest()
        holder = {}

        class FakeTransport:
            def __init__(self, budget, census):
                self.budget = budget
                self.census = census
                self.operations = []
                self.argvs = []
                holder["transport"] = self

            def process(self, argv, *, operation, target, allow_failure=False):
                self.budget.authorize("process")
                row = self.census.before_dispatch(
                    transport="fake_cli",
                    operation=operation,
                    method="EXEC",
                    target=target,
                    argv_shape=argv[:3],
                )
                self.operations.append(operation)
                self.argvs.append(list(argv))
                return_code = 0
                if operation == "acquire_search_teardown_token":
                    stdout = "fake-token\n"
                elif operation.startswith("preflight_"):
                    stdout = json.dumps(
                        matching_preflight_rows(manifest, operation, target)
                    )
                elif operation.startswith("verify_"):
                    stdout = "[]"
                else:
                    stdout = ""
                self.census.finish(row, return_code)
                return subprocess.CompletedProcess(argv, return_code, stdout=stdout, stderr="")

            def http(self, method, url, *, operation, target, token, body=None, allowed_statuses=(200,)):
                self.budget.authorize("index")
                row = self.census.before_dispatch(
                    transport="fake_https",
                    operation=operation,
                    method=method,
                    target=target,
                    api_version=proof.FUTURE_CONTRACT_API_VERSION,
                )
                self.operations.append(operation)
                self.argvs.append([])
                status = 404 if operation == "verify_proof_index_absent" else 204
                self.census.finish(row, status)
                return mock.Mock(status_code=status)

        with tempfile.TemporaryDirectory() as directory:
            result = proof.execute_teardown(
                manifest,
                confirmation="TEARDOWN SEARCH 3F",
                state_path=Path(directory) / "state.json",
                census_path=Path(directory) / "census.json",
                now=dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00"),
                transport_factory=FakeTransport,
            )
            operations = holder["transport"].operations
            self.assertEqual(operations.count("delete_role_assignment"), 2)
            role_verifications = [
                argv
                for operation, argv in zip(operations, holder["transport"].argvs)
                if operation == "verify_role_assignment_absent"
            ]
            self.assertEqual(len(role_verifications), 2)
            role_queries = [
                argv
                for operation, argv in zip(operations, holder["transport"].argvs)
                if operation in {
                    "preflight_role_assignment",
                    "verify_role_assignment_absent",
                }
            ]
            role_scope = manifest["targets"]["role_assignment_resource_ids"][0].rsplit(
                "/providers/Microsoft.Authorization/roleAssignments/", 1
            )[0]
            expected_role_query = [
                "az",
                "role",
                "assignment",
                "list",
                "--scope",
                role_scope,
                "--fill-role-definition-name",
                "false",
                "--fill-principal-name",
                "false",
                "--only-show-errors",
                "-o",
                "json",
            ]
            self.assertEqual(role_queries, [expected_role_query] * 4)
            self.assertNotIn("--all", expected_role_query)
            self.assertEqual(operations.count("delete_proof_index"), 1)
            self.assertEqual(operations.count("delete_service_principal"), 2)
            self.assertEqual(operations.count("delete_application_registration"), 2)
            self.assertEqual(result["result"], "teardown_converged")
            census_text = (Path(directory) / "census.json").read_text(encoding="utf-8")
            for secret_value in (
                manifest["service"]["subscription_id"],
                *manifest["targets"]["role_assignment_resource_ids"],
                *manifest["targets"]["service_principal_object_ids"],
                *manifest["targets"]["application_ids"],
                "fake-token",
            ):
                self.assertNotIn(secret_value, census_text)

    def test_teardown_fails_when_exact_role_assignment_remains(self):
        manifest = filled_cleanup_manifest()
        role_id = manifest["targets"]["role_assignment_resource_ids"][0]

        class RoleStillPresentTransport:
            def __init__(self, budget, census):
                pass

            def process(self, argv, *, operation, target, allow_failure=False):
                if operation == "verify_role_assignment_absent":
                    stdout = json.dumps([{"id": role_id}])
                elif operation == "acquire_search_teardown_token":
                    stdout = "fake-token\n"
                elif operation.startswith("preflight_"):
                    stdout = json.dumps(
                        matching_preflight_rows(manifest, operation, target)
                    )
                else:
                    stdout = "[]"
                return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

            def http(self, method, url, *, operation, target, token, body=None, allowed_statuses=(200,)):
                return mock.Mock(status_code=200)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "role assignment still exists"):
                proof.execute_teardown(
                    manifest,
                    confirmation="TEARDOWN SEARCH 3F",
                    state_path=Path(directory) / "state.json",
                    census_path=Path(directory) / "census.json",
                    now=dt.datetime.fromisoformat("2026-08-24T00:00:01-05:00"),
                    transport_factory=RoleStillPresentTransport,
                )


class CliSafetyTests(unittest.TestCase):
    def test_default_command_is_zero_network_plan(self):
        output = io.StringIO()
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("network/process")):
            with redirect_stdout(output):
                self.assertEqual(proof.main([]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["mode"], "ZERO_NETWORK_PLAN")
        self.assertFalse(result["network_dispatched"])

    def test_teardown_without_execute_is_zero_network_plan(self):
        output = io.StringIO()
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("network/process")):
            with redirect_stdout(output):
                self.assertEqual(proof.main(["teardown"]), 0)
        self.assertFalse(json.loads(output.getvalue())["network_dispatched"])

    def test_teardown_does_not_depend_on_fixture_availability(self):
        output = io.StringIO()
        missing_fixture = ROOT / "does-not-exist-fixture.json"
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("network/process")):
            with redirect_stdout(output):
                self.assertEqual(
                    proof.main(
                        [
                            "teardown",
                            "--fixture-manifest",
                            str(missing_fixture),
                        ]
                    ),
                    0,
                )
        self.assertFalse(json.loads(output.getvalue())["network_dispatched"])

    def test_execute_requires_all_explicit_arguments(self):
        with self.assertRaises(proof.ExecutionRefused):
            proof.main(["teardown", "--execute"])

    def test_imports_create_no_files_in_clean_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            script_path = str(ROOT / "scripts")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-c",
                    (
                        f"import sys; sys.path.insert(0, {script_path!r}); "
                        "import run_public_search_dark_proof; "
                        "import build_public_content_fixture_manifest"
                    ),
                ],
                cwd=directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(list(Path(directory).rglob("*")), [])


class RepositoryIntegrationTests(unittest.TestCase):
    def test_generated_fixture_and_schema_are_current(self):
        fixture_path = (
            ROOT
            / "docs"
            / "initiatives"
            / proof.PACKAGE_ID
            / "fixtures"
            / "public-content-proof-manifest.json"
        )
        schema_path = (
            ROOT
            / "docs"
            / "initiatives"
            / proof.PACKAGE_ID
            / "schema"
            / "public-content-index-v3.json"
        )
        self.assertEqual(
            json.loads(fixture_path.read_text(encoding="utf-8")),
            fixture_builder.build(),
        )
        self.assertEqual(
            json.loads(schema_path.read_text(encoding="utf-8")),
            proof.schema_body(),
        )

    def test_proof_operator_scripts_are_deployment_excluded(self):
        pipeline = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")
        lines = pipeline.splitlines()
        contents_index = next(
            index for index, line in enumerate(lines) if line.strip() == "Contents: |"
        )
        target_index = next(
            index
            for index in range(contents_index + 1, len(lines))
            if lines[index].strip().startswith("TargetFolder:")
        )
        patterns = [
            line.strip()
            for line in lines[contents_index + 1 : target_index]
            if line.strip()
        ]

        def selected(relative_path: str) -> bool:
            included = False
            for raw_pattern in patterns:
                excluded = raw_pattern.startswith("!")
                pattern = raw_pattern[1:] if excluded else raw_pattern
                if fnmatch.fnmatchcase(relative_path, pattern):
                    included = not excluded
            return included

        script_names = (
            "run_public_search_dark_proof.py",
            "build_public_content_fixture_manifest.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            scripts = source / "scripts"
            scripts.mkdir()
            for name in script_names:
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            self.assertTrue(compileall.compile_dir(scripts, quiet=1))
            compiled = list(scripts.rglob("*.pyc"))
            self.assertEqual(len(compiled), 2)

            for name in script_names:
                self.assertFalse(selected(f"scripts/{name}"))
            for path in compiled:
                relative = path.relative_to(source).as_posix()
                self.assertFalse(selected(relative), relative)

    def test_package_contains_no_tracked_bytecode_source(self):
        package = ROOT / "docs" / "initiatives" / proof.PACKAGE_ID
        self.assertFalse(list(package.rglob("*.pyc")))


if __name__ == "__main__":
    unittest.main()
