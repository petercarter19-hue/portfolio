"""Fake-only adversarial tests for the exact Graph deletion contract."""

from __future__ import annotations

import base64
import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from qa.synthetic_member import sealed_credential_broker as broker


NOW = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 8, 29, 9, 0, tzinfo=timezone.utc)
TENANT_ID = "33333333-3333-3333-3333-333333333333"
OPERATOR_ID = "44444444-4444-4444-4444-444444444444"
OTHER_OPERATOR_ID = "55555555-5555-5555-5555-555555555555"
SUBJECT_A = "11111111-1111-1111-1111-111111111111"
SUBJECT_B = "22222222-2222-2222-2222-222222222222"
GRAPH_ISSUER = "synthetic-tenant.onmicrosoft.com"
AUTHORIZATION_ORIGIN = "https://synthetic-tenant.ciamlogin.com"
OIDC_ISSUER = f"https://{TENANT_ID}.ciamlogin.com/{TENANT_ID}/v2.0"


def graph_token(operator: str = OPERATOR_ID) -> str:
    claims = {
        "tid": TENANT_ID,
        "oid": operator,
        "aud": "https://graph.microsoft.com",
        "scp": "User.Read User.ReadWrite.All User.DeleteRestore.All",
        "wids": ["fe930be7-5e62-47db-91af-98c3a49a38b1"],
        "exp": int((NOW + timedelta(hours=1)).timestamp()),
    }
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode()
    return f"header.{payload.rstrip('=')}.signature"


class TokenProvider:
    def __init__(self, operators=None):
        self.operators = list(operators or [OPERATOR_ID])
        self.calls = []

    def acquire(self, tenant_id):
        self.calls.append(tenant_id.reveal())
        index = min(len(self.calls) - 1, len(self.operators) - 1)
        return broker.SealedValue(
            graph_token(self.operators[index]), max_length=broker.MAX_TOKEN_LENGTH
        )


class Response:
    def __init__(self, url, *, status=200, payload=None, body=None):
        self._url = url
        self.status = status
        self._body = (
            body
            if body is not None
            else json.dumps(payload if payload is not None else {}).encode()
        )

    def geturl(self):
        return self._url

    def getcode(self):
        return self.status

    def read(self, limit=-1):
        return self._body if limit < 0 else self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def not_found(url):
    return HTTPError(url, 404, "not found", {}, io.BytesIO(b""))


def unavailable(url):
    return HTTPError(url, 503, "unavailable", {}, io.BytesIO(b""))


def conflict(url):
    return HTTPError(url, 409, "conflict", {}, io.BytesIO(b""))


class StatefulGraph:
    def __init__(self, *, faults=()):
        self.active = {}
        self.deleted = {}
        self.faults = set(faults)
        self.operations = []

    @staticmethod
    def organization():
        return {
            "value": [
                {
                    "id": TENANT_ID,
                    "verifiedDomains": [
                        {"name": GRAPH_ISSUER, "isInitial": True}
                    ],
                }
            ]
        }

    @staticmethod
    def record(subject, identity, *, created="2026-08-29T09:30:00Z"):
        return {
            "id": subject,
            "accountEnabled": True,
            "userType": "Member",
            "creationType": "LocalAccount",
            "displayName": f"PeerSlate synthetic QA {identity.alias}",
            "mailNickname": identity.mail_nickname.reveal(),
            "passwordPolicies": "DisablePasswordExpiration",
            "createdDateTime": created,
            "identities": [
                {
                    "signInType": "emailAddress",
                    "issuer": GRAPH_ISSUER,
                    "issuerAssignedId": identity.login_identifier.reveal(),
                }
            ],
        }

    def add_active(self, subject, identity, **kwargs):
        self.active[subject] = self.record(subject, identity, **kwargs)

    def add_deleted(self, subject, identity, **kwargs):
        self.deleted[subject] = self.record(subject, identity, **kwargs)

    def _filtered(self, request, container):
        query = parse_qs(urlparse(request.full_url).query)
        self.operations.append(("lookup", container, request.full_url, request.headers))
        if f"lookup:{container}" in self.faults:
            raise unavailable(request.full_url)
        if f"lookup_next:{container}" in self.faults:
            return Response(
                request.full_url,
                payload={"value": [], "@odata.nextLink": "forbidden"},
            )
        expression = query.get("$filter", [""])[0]
        values = [
            record
            for record in (self.active if container == "active" else self.deleted).values()
            if any(
                candidate["issuerAssignedId"] in expression
                and candidate["issuer"] in expression
                for candidate in record["identities"]
            )
        ]
        return Response(request.full_url, payload={"value": values})

    def __call__(self, request, timeout):
        if timeout != 60:
            raise AssertionError("unexpected timeout")
        url = request.full_url
        method = request.get_method()
        if url == broker.ALLOWED_GRAPH_ORGANIZATION_ENDPOINT:
            return Response(url, payload=self.organization())
        if method == "POST" and url == broker.ALLOWED_GRAPH_ENDPOINT:
            self.operations.append(("post", "customer", url, request.headers))
            if "create_409" in self.faults:
                raise conflict(url)
            if "create_mismatched_201" in self.faults:
                return Response(url, status=201, payload={"id": SUBJECT_B})
            raise AssertionError("unexpected unconfigured Graph POST")
        if method == "GET" and url.startswith(
            f"{broker.ALLOWED_GRAPH_ENDPOINT}?"
        ):
            return self._filtered(request, "active")
        if method == "GET" and url.startswith(
            f"{broker.ALLOWED_GRAPH_DELETED_ITEMS_ENDPOINT}/microsoft.graph.user?"
        ):
            return self._filtered(request, "deleted")

        parsed = urlparse(url)
        subject = parsed.path.rsplit("/", 1)[-1]
        is_deleted = "/directory/deletedItems/" in parsed.path
        container = "deleted" if is_deleted else "active"
        if method == "DELETE":
            operation = "purge" if is_deleted else "soft"
            self.operations.append((operation, subject, url, request.headers))
            if f"{operation}:{subject}" in self.faults:
                raise unavailable(url)
            if operation == "soft":
                record = self.active.pop(subject, None)
                if record is None:
                    raise not_found(url)
                self.deleted[subject] = record
            else:
                if self.deleted.pop(subject, None) is None:
                    raise not_found(url)
            return Response(url, status=204, body=b"")

        operation = f"probe_{container}"
        self.operations.append((operation, subject, url, request.headers))
        if f"{operation}:{subject}" in self.faults:
            raise unavailable(url)
        records = self.deleted if is_deleted else self.active
        if subject not in records:
            raise not_found(url)
        if parse_qs(parsed.query).get("$select") == [
            broker.GRAPH_CUSTOMER_SHAPE_SELECT
        ]:
            return Response(url, payload=records[subject])
        return Response(url, payload={"id": subject})


def authority_binding():
    return broker.AuthorityBinding(
        oidc_issuer=broker.SealedValue(OIDC_ISSUER),
        authorization_origin=broker.SealedValue(AUTHORIZATION_ORIGIN),
        tenant_id=broker.SealedValue(TENANT_ID),
        tenant_label=broker.SealedValue("synthetic-tenant"),
    )


def identities():
    return broker._generate_identities(
        broker.SealedValue(GRAPH_ISSUER),
        run_id="qa-20260829-0001",
        choice=lambda _alphabet: "z",
    )


def prepared_graph(*, state=None, operators=None):
    state = state or StatefulGraph()
    provider = TokenProvider(operators)
    graph = broker.MicrosoftGraphAdapter(provider, state, clock=lambda: NOW)
    authority = authority_binding()
    issuer = graph.prepare(authority)
    return graph, authority, issuer, state, provider


class ExactGraphDeletionTests(unittest.TestCase):
    def test_successful_pair_deletion_has_exact_order_and_no_retry(self):
        graph, authority, issuer, state, provider = prepared_graph()
        pair = identities()
        state.add_active(SUBJECT_A, pair[0])
        state.add_active(SUBJECT_B, pair[1])

        result = graph.delete_exact_pair(
            [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
            authority=authority,
            graph_issuer=issuer,
        )

        self.assertEqual(result, broker.GraphDeletionOutcome(2, 4, 2, 4))
        self.assertEqual(state.active, {})
        self.assertEqual(state.deleted, {})
        self.assertEqual(
            [(kind, subject) for kind, subject, *_ in state.operations],
            [
                ("soft", SUBJECT_A),
                ("soft", SUBJECT_B),
                ("probe_active", SUBJECT_A),
                ("probe_deleted", SUBJECT_A),
                ("probe_active", SUBJECT_B),
                ("probe_deleted", SUBJECT_B),
                ("purge", SUBJECT_A),
                ("purge", SUBJECT_B),
                ("probe_active", SUBJECT_A),
                ("probe_deleted", SUBJECT_A),
                ("probe_active", SUBJECT_B),
                ("probe_deleted", SUBJECT_B),
            ],
        )
        self.assertTrue(provider.calls)
        self.assertEqual(set(provider.calls), {TENANT_ID})

    def test_soft_failure_attempts_other_member_but_never_purges(self):
        state = StatefulGraph(faults={f"soft:{SUBJECT_A}"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        pair = identities()
        state.add_active(SUBJECT_A, pair[0])
        state.add_active(SUBJECT_B, pair[1])

        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "graph_deletion_indeterminate"
        ):
            graph.delete_exact_pair(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                authority=authority,
                graph_issuer=issuer,
            )
        kinds = [(kind, subject) for kind, subject, *_ in state.operations]
        self.assertEqual(kinds.count(("soft", SUBJECT_A)), 1)
        self.assertEqual(kinds.count(("soft", SUBJECT_B)), 1)
        self.assertFalse(any(kind == "purge" for kind, *_ in state.operations))

    def test_soft_proof_failure_blocks_all_permanent_deletion(self):
        state = StatefulGraph(faults={f"probe_deleted:{SUBJECT_B}"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        pair = identities()
        state.add_active(SUBJECT_A, pair[0])
        state.add_active(SUBJECT_B, pair[1])

        with self.assertRaises(broker.BrokerIndeterminate):
            graph.delete_exact_pair(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                authority=authority,
                graph_issuer=issuer,
            )
        self.assertFalse(any(kind == "purge" for kind, *_ in state.operations))

    def test_purge_failure_attempts_other_member_and_final_probes_once(self):
        state = StatefulGraph(faults={f"purge:{SUBJECT_A}"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        pair = identities()
        state.add_active(SUBJECT_A, pair[0])
        state.add_active(SUBJECT_B, pair[1])

        with self.assertRaises(broker.BrokerIndeterminate):
            graph.delete_exact_pair(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                authority=authority,
                graph_issuer=issuer,
            )
        kinds = [(kind, subject) for kind, subject, *_ in state.operations]
        self.assertEqual(kinds.count(("purge", SUBJECT_A)), 1)
        self.assertEqual(kinds.count(("purge", SUBJECT_B)), 1)
        self.assertEqual(kinds.count(("probe_active", SUBJECT_A)), 2)
        self.assertEqual(kinds.count(("probe_deleted", SUBJECT_A)), 2)
        self.assertEqual(kinds.count(("probe_active", SUBJECT_B)), 2)
        self.assertEqual(kinds.count(("probe_deleted", SUBJECT_B)), 2)

    def test_operator_switch_refuses_before_any_delete_request(self):
        graph, authority, issuer, state, _provider = prepared_graph(
            operators=[OPERATOR_ID, OTHER_OPERATOR_ID]
        )
        with self.assertRaises(broker.BrokerIndeterminate):
            graph.delete_exact_pair(
                [broker.SealedValue(SUBJECT_A), broker.SealedValue(SUBJECT_B)],
                authority=authority,
                graph_issuer=issuer,
            )
        self.assertEqual(state.operations, [])

    def test_four_exact_collision_reads_and_existing_match_refusal(self):
        graph, authority, issuer, state, _provider = prepared_graph()
        pair = identities()
        self.assertEqual(
            graph.prove_customer_absence(
                pair, authority=authority, graph_issuer=issuer
            ),
            4,
        )
        lookups = [entry for entry in state.operations if entry[0] == "lookup"]
        self.assertEqual([entry[1] for entry in lookups], ["active", "deleted"] * 2)
        for _kind, _container, url, headers in lookups:
            query = parse_qs(urlparse(url).query)
            self.assertEqual(set(query), {"$select", "$top", "$filter"})
            self.assertEqual(query["$select"], ["id,identities,createdDateTime"])
            self.assertEqual(query["$top"], ["2"])
            self.assertNotIn("ConsistencyLevel", headers)

        state.operations.clear()
        state.add_active(SUBJECT_A, pair[0])
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "graph_customer_absence_unverified"
        ):
            graph.prove_customer_absence(
                pair, authority=authority, graph_issuer=issuer
            )
        self.assertFalse(any(kind in {"soft", "purge"} for kind, *_ in state.operations))

    def test_ambiguous_create_reconciles_once_and_soft_contains_without_purge(self):
        graph, authority, issuer, state, _provider = prepared_graph()
        pair = identities()
        state.add_active(SUBJECT_A, pair[0])

        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": "ambiguous_maybe_created",
                "member_b": "not_attempted",
            },
            attempted_after={"member_a": CUTOFF},
            authority=authority,
            graph_issuer=issuer,
        )

        self.assertEqual(state.active, {})
        self.assertEqual(set(state.deleted), {SUBJECT_A})
        kinds = [(entry[0], entry[1]) for entry in state.operations]
        self.assertEqual(kinds.count(("lookup", "active")), 1)
        self.assertEqual(kinds.count(("lookup", "deleted")), 1)
        self.assertEqual(kinds.count(("soft", SUBJECT_A)), 1)
        self.assertEqual(kinds.count(("purge", SUBJECT_A)), 0)
        self.assertFalse(any(kind == "post" for kind, *_ in state.operations))

    def test_zero_result_ambiguous_create_is_unknown_and_never_deleted(self):
        graph, authority, issuer, state, _provider = prepared_graph()
        pair = identities()
        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": "ambiguous_maybe_created",
                "member_b": "not_attempted",
            },
            attempted_after={"member_a": CUTOFF},
            authority=authority,
            graph_issuer=issuer,
        )
        self.assertFalse(any(kind in {"soft", "purge"} for kind, *_ in state.operations))

    def test_reconciled_deleted_create_remains_recoverable_and_unpurged(self):
        graph, authority, issuer, state, _provider = prepared_graph()
        pair = identities()
        state.add_deleted(SUBJECT_A, pair[0])

        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": "ambiguous_maybe_created",
                "member_b": "not_attempted",
            },
            attempted_after={"member_a": CUTOFF},
            authority=authority,
            graph_issuer=issuer,
        )

        self.assertIn(SUBJECT_A, state.deleted)
        self.assertFalse(
            any(kind in {"soft", "purge"} for kind, *_ in state.operations)
        )

    def test_unbounded_collision_lookup_refuses_before_mutation(self):
        state = StatefulGraph(faults={"lookup_next:active"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "graph_customer_absence_unverified"
        ):
            graph.prove_customer_absence(
                identities(), authority=authority, graph_issuer=issuer
            )
        self.assertFalse(any(kind in {"soft", "purge"} for kind, *_ in state.operations))

    def test_reconciliation_rejects_identity_older_than_local_attempt(self):
        graph, authority, issuer, state, _provider = prepared_graph()
        pair = identities()
        state.add_active(
            SUBJECT_A, pair[0], created="2026-08-29T08:59:59Z"
        )
        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": "ambiguous_maybe_created",
                "member_b": "not_attempted",
            },
            attempted_after={"member_a": CUTOFF},
            authority=authority,
            graph_issuer=issuer,
        )
        self.assertIn(SUBJECT_A, state.active)
        self.assertFalse(any(kind in {"soft", "purge"} for kind, *_ in state.operations))

    def test_mismatched_201_subject_is_never_cleanup_eligible(self):
        state = StatefulGraph(faults={"create_mismatched_201"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        pair = identities()
        state.add_active(SUBJECT_B, pair[1], created="2026-08-29T10:00:00Z")

        outcome = graph.create_customer(
            pair[0], authority=authority, graph_issuer=issuer
        )
        self.assertEqual(outcome.state, "ambiguous_maybe_created")
        self.assertIsNone(outcome.subject)
        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": outcome.state,
                "member_b": "not_attempted",
            },
            attempted_after={"member_a": outcome.attempted_after},
            authority=authority,
            graph_issuer=issuer,
        )

        self.assertIn(SUBJECT_B, state.active)
        self.assertFalse(any(kind in {"soft", "purge"} for kind, *_ in state.operations))

    def test_409_skips_concurrent_alias_but_contains_prior_bound_alias(self):
        state = StatefulGraph(faults={"create_409"})
        graph, authority, issuer, state, _provider = prepared_graph(state=state)
        pair = identities()
        state.add_active(SUBJECT_A, pair[0], created="2026-08-29T10:00:00Z")
        state.add_active(SUBJECT_B, pair[1], created="2026-08-29T10:00:00Z")
        pair[0].subject = broker.SealedValue(SUBJECT_A)

        rejected = graph.create_customer(
            pair[1], authority=authority, graph_issuer=issuer
        )
        self.assertEqual(rejected.state, "known_not_created")
        graph.contain_partial_creation(
            pair,
            creation_states={
                "member_a": "known_created",
                "member_b": rejected.state,
            },
            attempted_after={
                "member_a": NOW,
                "member_b": rejected.attempted_after,
            },
            authority=authority,
            graph_issuer=issuer,
        )

        self.assertNotIn(SUBJECT_A, state.active)
        self.assertIn(SUBJECT_A, state.deleted)
        self.assertIn(SUBJECT_B, state.active)
        mutations = [
            (kind, subject)
            for kind, subject, *_ in state.operations
            if kind in {"soft", "purge"}
        ]
        self.assertEqual(mutations, [("soft", SUBJECT_A)])


if __name__ == "__main__":
    unittest.main()
