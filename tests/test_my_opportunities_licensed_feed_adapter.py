from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import inspect
import json
from pathlib import Path
import re
import socket
import time
import unittest
from unittest import mock

from services.my_opportunities.canonical_service import (
    CanonicalService,
    InMemoryCanonicalRepository,
    LiveOpportunityGateConfig,
    MyOpportunitiesCanonicalError,
    SourcePolicy,
)
from services.my_opportunities.ingestion_service import IngestionService
from services.my_opportunities.qualification_service import (
    Assessment,
    AssessmentRevision,
    GATE_NOT_FULLY_VERIFIED,
    InMemoryQualificationRepository,
    STATE_NOT_ESTABLISHED,
)
from services.my_opportunities.relationships_service import (
    CREATED_FROM_RESULT,
    LINK_STATE_LINKED,
    SAVE_STATE_SAVED,
    InMemoryRelationshipsRepository,
    SavedOpportunity,
    SlateLink,
)
from services.my_opportunities.retrieval_service import (
    InMemoryRetrievalRepository,
    OrderingInputs,
    PARTITION_BROADER,
    PreferredSummary,
    RequiredSummary,
    ResultEntry,
    ResultSnapshot,
    SearchExecution,
    STATE_COMPLETE,
)
from services.my_opportunities.licensed_feed_adapter import (
    AGGREGATOR_API_KEY_SETTING,
    AGGREGATOR_APP_ID_SETTING,
    AGGREGATOR_PROVIDER_SETTING,
    DIRECT_BOARDS_SETTING,
    DIRECT_EMPLOYER,
    GOVERNMENT_API_KEY_SETTING,
    GOVERNMENT_EMAIL_SETTING,
    GOVERNMENT_FEED,
    LICENSED_AGGREGATOR,
    AggregatorFeedAdapter,
    DirectEmployerFeedAdapter,
    FeedBudget,
    FeedRequest,
    GovernmentFeedAdapter,
    LicensedFeedError,
    LiveTransport,
    RawResponse,
    RightsProjection,
    TerminationExitRehearsal,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/my_opportunities/licensed_feed"
NOW = datetime(2026, 9, 2, 12, tzinfo=timezone.utc)
USER_KEY = "fixture-member"
ACTIONS = frozenset(
    {
        "register",
        "acquire",
        "persist",
        "display",
        "retain",
        "remove",
        "terminate",
        "export",
        "ai",
        "cache",
    }
)
DIMENSIONS = {
    "display": True,
    "excerpt": True,
    "full_description": True,
    "storage": True,
    "ai_ml_use": True,
    "caching": True,
    "retention": True,
    "attribution": True,
    "removal": True,
    "termination": True,
    "exit": True,
    "survivable_minimal_facts": True,
}


class PolicyView:
    def __init__(self) -> None:
        self.current: dict[tuple[str, str], SourcePolicy] = {}

    def __call__(self, descriptor):
        return self.current.get((descriptor.data_class, descriptor.source_id))

    def put(self, descriptor, policy: SourcePolicy) -> None:
        self.current[(descriptor.data_class, descriptor.source_id)] = policy


def fixture_bytes(relative: str) -> bytes:
    return (FIXTURES / relative).read_bytes()


def complete_policy(
    descriptor,
    *,
    version: int = 1,
    priority: int = 1,
    actions=ACTIONS,
    dimensions=None,
    retained_source_fields=(),
    effective_at=NOW - timedelta(days=1),
    expires_at=None,
):
    return SourcePolicy(
        descriptor.policy_key,
        version,
        descriptor.source_id,
        descriptor.data_class,
        frozenset(actions),
        priority,
        effective_at,
        expires_at,
        dimensions or dict(DIMENSIONS),
        "fixture-evidence",
        "fixture-decision",
        source_class=descriptor.source_class,
        retained_source_fields=retained_source_fields,
    )


def services():
    repository = InMemoryCanonicalRepository()
    canonical = CanonicalService(
        repository,
        LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2)),
    )
    return repository, canonical, IngestionService(canonical)


def case_factory(name: str, *, responses=None, policy_view=None, budget=None, **timing):
    policy_view = policy_view or PolicyView()
    employer = timing.pop("employer", None)
    relative = {
        "aggregator": "aggregator/representative.json",
        "government": "government/usajobs.json",
        "greenhouse": "direct_employer/greenhouse.json",
        "lever": "direct_employer/lever.json",
    }[name]
    responses = responses or (RawResponse(200, fixture_bytes(relative)),)
    common = {
        "policy_key": f"policy-{name}",
        "policy_version": 1,
        "policy_reader": policy_view,
        "responses": responses,
        "budget": budget,
        "clock": lambda: NOW,
        **timing,
    }
    if name == "aggregator":
        adapter = AggregatorFeedAdapter.fixture(**common)
    elif name == "government":
        adapter = GovernmentFeedAdapter.fixture(**common)
    else:
        employer = employer or {
                "greenhouse": "Canopy Example Cooperative",
                "lever": "Lumen Example Studio",
            }[name]
        adapter = DirectEmployerFeedAdapter.fixture(
            ats=name,
            board="example",
            employer=employer,
            **common,
        )
    return adapter, policy_view, relative


def ready_case(name: str, **kwargs):
    adapter, view, relative = case_factory(name, **kwargs)
    view.put(adapter.describe(), complete_policy(adapter.describe()))
    return adapter, view, relative


def production_environment(source_class: str):
    if source_class == LICENSED_AGGREGATOR:
        return {
            AGGREGATOR_PROVIDER_SETTING: "adzuna",
            AGGREGATOR_APP_ID_SETTING: "placeholder-app",
            AGGREGATOR_API_KEY_SETTING: "placeholder-key",
        }
    if source_class == GOVERNMENT_FEED:
        return {
            GOVERNMENT_API_KEY_SETTING: "placeholder-key",
            GOVERNMENT_EMAIL_SETTING: "operator@example.test",
        }
    return {
        DIRECT_BOARDS_SETTING: json.dumps(
            {
                "greenhouse:example": "Canopy Example Cooperative",
                "lever:example": "Lumen Example Studio",
            },
            separators=(",", ":"),
        )
    }


def production_aggregator(script, *, view=None, budget=None, sleeper=None):
    view = view or PolicyView()
    calls = []

    def sender(request: FeedRequest):
        calls.append(request)
        value = script.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    resolved_budget = budget or FeedBudget()
    resolved_budget = replace(
        resolved_budget,
        min_request_interval_seconds=max(
            resolved_budget.min_request_interval_seconds,
            0.001,
        ),
    )
    adapter = AggregatorFeedAdapter.production(
        production_environment(LICENSED_AGGREGATOR),
        policy_key="policy-production-aggregator",
        policy_version=1,
        policy_reader=view,
        sender=sender,
        budget=resolved_budget,
    )
    if sleeper is not None:
        adapter._sleeper = sleeper  # deterministic retry clock seam
    view.put(adapter.describe(), complete_policy(adapter.describe()))
    return adapter, view, calls


def production_case(name: str, body: bytes):
    if name == "aggregator":
        return production_aggregator([RawResponse(200, body)])
    view = PolicyView()
    calls = []

    def sender(request):
        calls.append(request)
        return RawResponse(200, body)

    if name == "government":
        adapter = GovernmentFeedAdapter.production(
            production_environment(GOVERNMENT_FEED),
            policy_key="policy-production-government",
            policy_version=1,
            policy_reader=view,
            sender=sender,
        )
    else:
        adapter = DirectEmployerFeedAdapter.production(
            production_environment(DIRECT_EMPLOYER),
            ats=name,
            board="example",
            policy_key=f"policy-production-{name}",
            policy_version=1,
            policy_reader=view,
            sender=sender,
        )
    view.put(adapter.describe(), complete_policy(adapter.describe()))
    return adapter, view, calls


def provider_document(name: str):
    relative = {
        "aggregator": "aggregator/representative.json",
        "government": "government/usajobs.json",
        "greenhouse": "direct_employer/greenhouse.json",
        "lever": "direct_employer/lever.json",
    }[name]
    document = json.loads(fixture_bytes(relative))
    document.pop("_fixture")
    if name == "lever":
        return document["postings"]
    return document


def provider_item(name: str, document):
    if name == "aggregator":
        return document["results"][0]
    if name == "government":
        return document["SearchResult"]["SearchResultItems"][0][
            "MatchedObjectDescriptor"
        ]
    if name == "greenhouse":
        return document["jobs"][0]
    return document["postings"][0]


def response_item(name: str, document):
    if name == "aggregator":
        return document["results"][0]
    if name == "government":
        return document["SearchResult"]["SearchResultItems"][0]
    if name == "greenhouse":
        return document["jobs"][0]
    if name == "lever":
        return document[0]
    return document["jobs"][0]


def member_truth_fixture(name, canonical_repository, listing):
    """Persist and re-read real C4/C5/C6 member truth around C2 lifecycle work."""

    opportunity = canonical_repository.opportunity(listing.canonical_opportunity_key)
    requirement = canonical_repository.requirement_version(
        opportunity.requirement_version_key
    )
    requirement_item = requirement.items[0]
    source_version_key = opportunity.governing_source_version_key

    relationships = InMemoryRelationshipsRepository()
    save = SavedOpportunity(
        f"save-{name}",
        USER_KEY,
        "fixture",
        opportunity.opportunity_key,
        source_version_key,
        SAVE_STATE_SAVED,
        NOW,
        None,
        None,
    )
    link = SlateLink(
        f"link-{name}",
        USER_KEY,
        "fixture",
        opportunity.opportunity_key,
        f"slate-{name}",
        CREATED_FROM_RESULT,
        source_version_key,
        LINK_STATE_LINKED,
        NOW,
        None,
    )
    relationships.persist_save(save)
    relationships.persist_link(link)

    retrieval = InMemoryRetrievalRepository()
    execution_key = f"execution-{name}"
    execution = SearchExecution(
        execution_key,
        USER_KEY,
        "fixture",
        f"criteria-{name}",
        STATE_COMPLETE,
        "canonical",
        "full",
        (),
        None,
        None,
        None,
        NOW,
        {},
        NOW,
    )
    retrieval.save_execution(execution)
    entry = ResultEntry(
        f"entry-{name}",
        PARTITION_BROADER,
        1,
        opportunity.opportunity_key,
        requirement.requirement_version_key,
        source_version_key,
        {},
        GATE_NOT_FULLY_VERIFIED,
        RequiredSummary(0, 1, 0, 0, 1),
        PreferredSummary(0, 0),
        OrderingInputs(0, None, None, None, opportunity.opportunity_key),
    )
    result = ResultSnapshot(
        f"result-{name}",
        USER_KEY,
        "fixture",
        execution_key,
        f"criteria-{name}",
        "complete",
        None,
        "full",
        (),
        0,
        1,
        False,
        (entry,),
        NOW,
    )
    retrieval.persist_snapshot(result)

    qualification = InMemoryQualificationRepository()
    assessment = Assessment(
        f"assessment-{name}",
        USER_KEY,
        requirement_item.requirement_item_key,
        requirement.requirement_version_key,
        "required",
        STATE_NOT_ESTABLISHED,
        "no_evidence_in_scope",
        1,
        (),
        NOW,
        "Not established from the member evidence in scope.",
    )
    revision = AssessmentRevision(
        1,
        STATE_NOT_ESTABLISHED,
        "no_evidence_in_scope",
        "initial",
        "system:search_worker/assessment",
        (),
        NOW,
    )
    qualification.append_assessment_revision(USER_KEY, assessment, revision)

    def snapshot():
        return (
            relationships.state_digest(),
            retrieval.state_digest(),
            qualification.state_digest(),
            relationships.saves_for_owner(USER_KEY),
            relationships.links_for_owner(USER_KEY, opportunity.opportunity_key),
            retrieval.snapshot_for_execution(USER_KEY, execution_key),
            qualification.assessments_for_version(
                USER_KEY, requirement.requirement_version_key
            ),
            qualification.revisions_for_assessment(
                USER_KEY, assessment.assessment_key
            ),
        )

    before = snapshot()
    assert len(before[3]) == len(before[4]) == 1
    assert before[5] is not None and len(before[5].entries) == 1
    assert len(before[6]) == len(before[7]) == 1
    return before, snapshot


class DescriptorAndSettingsTests(unittest.TestCase):
    def test_all_documented_source_class_shapes_describe_without_network(self):
        expected = {
            "aggregator": ("licensed:representative", LICENSED_AGGREGATOR),
            "government": ("government:usajobs", GOVERNMENT_FEED),
            "greenhouse": ("direct:greenhouse:example", DIRECT_EMPLOYER),
            "lever": ("direct:lever:example", DIRECT_EMPLOYER),
        }
        for name, identity in expected.items():
            with self.subTest(name=name):
                adapter, _, _ = case_factory(name)
                descriptor = adapter.describe()
                self.assertEqual((descriptor.source_id, descriptor.source_class), identity)
                self.assertEqual(descriptor.data_class, "fixture")
                self.assertIn("pull", descriptor.capabilities)

    def test_each_missing_or_blank_named_setting_fails_closed_with_names_only(self):
        required = {
            LICENSED_AGGREGATOR: (
                AGGREGATOR_PROVIDER_SETTING,
                AGGREGATOR_APP_ID_SETTING,
                AGGREGATOR_API_KEY_SETTING,
            ),
            GOVERNMENT_FEED: (GOVERNMENT_API_KEY_SETTING, GOVERNMENT_EMAIL_SETTING),
            DIRECT_EMPLOYER: (DIRECT_BOARDS_SETTING,),
        }
        constructors = {
            LICENSED_AGGREGATOR: lambda env: AggregatorFeedAdapter.production(
                env,
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
            ),
            GOVERNMENT_FEED: lambda env: GovernmentFeedAdapter.production(
                env,
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
            ),
            DIRECT_EMPLOYER: lambda env: DirectEmployerFeedAdapter.production(
                env,
                ats="greenhouse",
                board="example",
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
            ),
        }
        for source_class, names in required.items():
            baseline = production_environment(source_class)
            for missing in names:
                with self.subTest(source_class=source_class, missing=missing):
                    environment = dict(baseline)
                    environment[missing] = "  "
                    with self.assertRaises(LicensedFeedError) as caught:
                        constructors[source_class](environment)
                    self.assertEqual(caught.exception.code, "credentials_missing")
                    self.assertIn(missing, str(caught.exception))
                    self.assertNotIn("placeholder", str(caught.exception))

    def test_invalid_provider_email_and_board_shapes_are_content_free_refusals(self):
        bad_values = (
            (
                lambda: AggregatorFeedAdapter.production(
                    {
                        AGGREGATOR_PROVIDER_SETTING: "arbitrary-host",
                        AGGREGATOR_APP_ID_SETTING: "placeholder",
                        AGGREGATOR_API_KEY_SETTING: "placeholder",
                    },
                    policy_key="p",
                    policy_version=1,
                    policy_reader=PolicyView(),
                    sender=lambda _: None,
                ),
                AGGREGATOR_PROVIDER_SETTING,
            ),
            (
                lambda: GovernmentFeedAdapter.production(
                    {
                        GOVERNMENT_API_KEY_SETTING: "placeholder",
                        GOVERNMENT_EMAIL_SETTING: "not-an-email",
                    },
                    policy_key="p",
                    policy_version=1,
                    policy_reader=PolicyView(),
                    sender=lambda _: None,
                ),
                GOVERNMENT_EMAIL_SETTING,
            ),
            (
                lambda: DirectEmployerFeedAdapter.production(
                    {DIRECT_BOARDS_SETTING: "https://untrusted.example/board"},
                    ats="greenhouse",
                    board="example",
                    policy_key="p",
                    policy_version=1,
                    policy_reader=PolicyView(),
                    sender=lambda _: None,
                ),
                DIRECT_BOARDS_SETTING,
            ),
        )
        for operation, setting_name in bad_values:
            with self.subTest(setting_name=setting_name):
                with self.assertRaises(LicensedFeedError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertIn(setting_name, str(caught.exception))

    def test_missing_sender_never_constructs_a_network_capability(self):
        for source_class in (LICENSED_AGGREGATOR, GOVERNMENT_FEED, DIRECT_EMPLOYER):
            with self.subTest(source_class=source_class):
                if source_class == LICENSED_AGGREGATOR:
                    operation = lambda: AggregatorFeedAdapter.production(
                        production_environment(source_class),
                        policy_key="p",
                        policy_version=1,
                        policy_reader=PolicyView(),
                        sender=None,
                    )
                elif source_class == GOVERNMENT_FEED:
                    operation = lambda: GovernmentFeedAdapter.production(
                        production_environment(source_class),
                        policy_key="p",
                        policy_version=1,
                        policy_reader=PolicyView(),
                        sender=None,
                    )
                else:
                    operation = lambda: DirectEmployerFeedAdapter.production(
                        production_environment(source_class),
                        ats="greenhouse",
                        board="example",
                        policy_key="p",
                        policy_version=1,
                        policy_reader=PolicyView(),
                        sender=None,
                    )
                with self.assertRaises(LicensedFeedError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, "transport_unavailable")

    def test_direct_employer_requires_per_employer_registration_setting(self):
        with self.assertRaises(LicensedFeedError) as caught:
            DirectEmployerFeedAdapter.production(
                {DIRECT_BOARDS_SETTING: '{"greenhouse:other":"Other Employer"}'},
                ats="greenhouse",
                board="example",
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
            )
        self.assertEqual(caught.exception.code, "policy_denied")

    def test_direct_employer_binding_is_strict_and_production_identity_is_setting_owned(self):
        invalid_values = (
            "greenhouse:example,lever:example",
            "{}",
            "[]",
            '"greenhouse:example"',
            '{"greenhouse:example":"A",}',
            '{"greenhouse:example":"A","greenhouse:example":"B"}',
            '{" GREENHOUSE:example ":"A"}',
            '{"greenhouse:../example":"A"}',
            '{"unknown:example":"A"}',
            '{"greenhouse:example":null}',
            '{"greenhouse:example":1}',
            '{"greenhouse:example":" A"}',
            '{"greenhouse:example":"A\\nB"}',
            '{"greenhouse:example":"A\\u202eB"}',
            json.dumps({"greenhouse:example": "A" * 201}),
            json.dumps({f"greenhouse:board-{index}": "A" for index in range(101)}),
            json.dumps({"greenhouse:example": "A" * (32 * 1024 + 1)}),
        )
        for value in invalid_values:
            with self.subTest(value=value[:40]):
                with self.assertRaises(LicensedFeedError) as caught:
                    DirectEmployerFeedAdapter.production(
                        {DIRECT_BOARDS_SETTING: value},
                        ats="greenhouse",
                        board="example",
                        policy_key="p",
                        policy_version=1,
                        policy_reader=PolicyView(),
                        sender=lambda _: None,
                    )
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertEqual(
                    str(caught.exception),
                    f"contract_violation:{DIRECT_BOARDS_SETTING}",
                )

        self.assertIn("employer", inspect.signature(DirectEmployerFeedAdapter.fixture).parameters)
        self.assertNotIn("employer", inspect.signature(DirectEmployerFeedAdapter.production).parameters)
        for name, expected in (
            ("greenhouse", "Canopy Example Cooperative"),
            ("lever", "Lumen Example Studio"),
        ):
            with self.subTest(name=name):
                document = provider_document(name)
                item = response_item(name, document)
                item["company"] = "Injected Provider Label"
                body = json.dumps(document, separators=(",", ":")).encode()
                adapter, _, _ = production_case(name, body)
                listing = adapter.normalize(adapter.acquire()[0])
                self.assertEqual(listing.employer, expected)

        valid, _, _ = production_case(
            "greenhouse",
            json.dumps(provider_document("greenhouse")).encode(),
        )
        with self.assertRaises(LicensedFeedError) as bypass:
            DirectEmployerFeedAdapter(
                ats="greenhouse",
                board="example",
                employer="CALLER INVENTED EMPLOYER",
                descriptor=valid.describe(),
                transport=valid._transport,
                projection=valid._projection,
                endpoint_prefix=valid._endpoint_prefix,
                budget=valid._budget,
                settings=valid._settings,
            )
        self.assertEqual(bypass.exception.code, "contract_violation")
        self.assertNotIn("CALLER INVENTED EMPLOYER", str(bypass.exception))

    def test_live_transport_exposes_only_redacted_header_values(self):
        transport = LiveTransport(
            endpoint_prefix="https://api.example.test/v1",
            headers={"Authorization": "sensitive-value"},
            sender=lambda _: RawResponse(200, b"{}"),
        )
        self.assertEqual(transport.headers, {"Authorization": "<redacted>"})
        self.assertNotIn("sensitive-value", repr(transport))

    def test_live_transport_rejects_prefix_confusion_before_sender(self):
        calls = []
        transport = LiveTransport(
            endpoint_prefix="https://api.example.test/v1",
            headers={},
            sender=lambda request: calls.append(request) or RawResponse(200, b"{}"),
        )
        for url in (
            "https://api.example.test.evil/v1",
            "https://api.example.test/v10",
            "https://api.example.test/v1/../outside",
            "https://[invalid-host/v1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(LicensedFeedError) as caught:
                    transport.fetch(FeedRequest(url, 1, {}, 1.0))
                self.assertEqual(caught.exception.code, "contract_violation")
        self.assertEqual(calls, [])


class RecordedFixtureAndMappingTests(unittest.TestCase):
    def test_recorded_acquire_retains_exact_item_token_and_hash_for_each_family(self):
        expected_hashes = {
            "aggregator": "e535078c3bdfd18818d087d986901f8ef6d1384c3d0e232fffab6619ce16d0cd",
            "government": "25aa9bb31417cb9b59632ddcf20888bc55e0387b90c61181994eca151dc01697",
            "greenhouse": "e8dae3bc3248cce5b74620ff9c2e76fc686090cad3a6232243def3ed2e6413d2",
            "lever": "645b0e300af1e0ae708619a5a8b7f70ea85883819ecb9d29f18cac233310285c",
        }
        for name in ("aggregator", "government", "greenhouse", "lever"):
            with self.subTest(name=name):
                adapter, _, relative = ready_case(name)
                receipt = adapter.acquire()[0]
                response = fixture_bytes(relative)
                self.assertNotEqual(receipt.payload, response)
                self.assertEqual(response.count(receipt.payload), 1)
                self.assertEqual(sha256(receipt.payload).hexdigest(), expected_hashes[name])
                self.assertEqual(adapter.last_run.bytes_received, len(response))
                self.assertEqual(adapter.last_run.refusal_codes, ())

    def test_documented_fields_map_to_deterministic_normalized_listings(self):
        expected = {
            "aggregator": (
                "Northstar Example Labs",
                "Platform Reliability Engineer",
                ("Brussels, Belgium",),
                "jobs.example",
            ),
            "government": (
                "Example Public Digital Service",
                "Digital Service Engineer",
                ("Washington, District of Columbia",),
                "www.usajobs.gov",
            ),
            "greenhouse": (
                "Canopy Example Cooperative",
                "Product Systems Engineer",
                ("Remote in Europe",),
                "boards.greenhouse.io",
            ),
            "lever": (
                "Lumen Example Studio",
                "Member Experience Engineer",
                ("Remote",),
                "jobs.lever.co",
            ),
        }
        for name, facts in expected.items():
            with self.subTest(name=name):
                adapter, _, _ = ready_case(name)
                receipt = adapter.acquire()[0]
                first = adapter.normalize(receipt)
                second = adapter.normalize(receipt)
                self.assertEqual(first, second)
                self.assertEqual((first.employer, first.title, first.locations), facts[:3])
                self.assertEqual(first.expected_application_hosts, (facts[3],))
                self.assertTrue(first.requirement_clauses)
                self.assertEqual(first.data_class, "fixture")

    def test_fixture_header_is_required_and_unknown_response_shape_stops(self):
        valid = json.loads(fixture_bytes("aggregator/representative.json"))
        scenarios = []
        missing_header = dict(valid)
        missing_header.pop("_fixture")
        scenarios.append((missing_header, "fixture_label"))
        missing_citation = json.loads(json.dumps(valid))
        missing_citation["_fixture"]["citation_url"] = ""
        scenarios.append((missing_citation, "fixture_citation"))
        unknown_shape = dict(valid)
        unknown_shape.pop("results")
        unknown_shape["future_results"] = []
        scenarios.append((unknown_shape, "response_shape"))
        for document, context in scenarios:
            with self.subTest(context=context):
                body = json.dumps(document).encode()
                adapter, view, _ = case_factory(
                    "aggregator", responses=(RawResponse(200, body),)
                )
                view.put(adapter.describe(), complete_policy(adapter.describe()))
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertIn(context, str(caught.exception))

    def test_malformed_item_is_skipped_and_next_item_continues(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        valid = dict(document["results"][0])
        valid["id"] = "aggregator-fixture-002"
        valid["title"] = "Second Valid Role"
        malformed = dict(document["results"][0])
        malformed["company"] = []
        document["results"] = [malformed, valid]
        adapter, _, _ = ready_case(
            "aggregator",
            responses=(RawResponse(200, json.dumps(document).encode()),),
        )
        receipts = adapter.acquire()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].external_reference, "aggregator-fixture-002")
        self.assertEqual(adapter.last_run.pages, 1)
        self.assertEqual(adapter._transport.fetch_count, 1)
        self.assertEqual(adapter.last_run.refusal_codes, ("payload_malformed",))
        self.assertNotIn(b'"company": []', receipts[0].payload)

    def test_documented_raw_production_envelopes_preserve_exact_item_bytes(self):
        jooble = {
            "totalCount": 1,
            "jobs": [
                {
                    "id": "jooble-fixture-001",
                    "title": "Jooble-shaped Test Role",
                    "company": "Fictional Example Employer",
                    "location": "Remote",
                    "type": "Full-time",
                    "link": "https://jobs.example/jooble-fixture-001",
                    "snippet": "Applicants must have relevant experience.",
                }
            ],
        }
        cases = {
            name: provider_document(name)
            for name in ("aggregator", "government", "greenhouse", "lever")
        }
        cases["jooble"] = jooble
        for name, document in cases.items():
            with self.subTest(name=name):
                body = json.dumps(document, separators=(",", ":")).encode()
                if name == "jooble":
                    view = PolicyView()
                    calls = []

                    def sender(request):
                        calls.append(request)
                        return RawResponse(200, body)

                    environment = production_environment(LICENSED_AGGREGATOR)
                    environment[AGGREGATOR_PROVIDER_SETTING] = "jooble"
                    adapter = AggregatorFeedAdapter.production(
                        environment,
                        policy_key="policy-production-jooble",
                        policy_version=1,
                        policy_reader=view,
                        sender=sender,
                        budget=FeedBudget(min_request_interval_seconds=0.001),
                    )
                    view.put(adapter.describe(), complete_policy(adapter.describe()))
                else:
                    adapter, _, calls = production_case(name, body)
                receipt = adapter.acquire()[0]
                expected_item = json.dumps(
                    response_item(name, document), separators=(",", ":")
                ).encode()
                self.assertEqual(receipt.payload, expected_item)
                self.assertNotEqual(receipt.payload, body)
                self.assertEqual(body.count(receipt.payload), 1)
                self.assertEqual(adapter.normalize(receipt).external_reference, receipt.external_reference)
                self.assertEqual(len(calls), 1)

    def test_multi_item_page_emits_distinct_exact_item_receipts(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        second = dict(document["results"][0])
        second.update({"id": "aggregator-fixture-002", "title": "Second Role"})
        document["results"].append(second)
        body = json.dumps(document, separators=(",", ":")).encode()
        adapter, _, _ = ready_case(
            "aggregator", responses=(RawResponse(200, body),)
        )
        receipts = adapter.acquire()
        self.assertEqual(len(receipts), 2)
        self.assertEqual(
            {item.payload for item in receipts},
            {
                json.dumps(item, separators=(",", ":")).encode()
                for item in document["results"]
            },
        )
        self.assertTrue(all(body.count(item.payload) == 1 for item in receipts))
        self.assertEqual(len({item.external_reference for item in receipts}), 2)
        self.assertEqual(len({item.received_at for item in receipts}), 1)
        self.assertEqual(
            [adapter.normalize(item).title for item in reversed(receipts)],
            ["Second Role", "Platform Reliability Engineer"],
        )

    def test_item_slice_preserves_whitespace_key_order_escapes_and_numeric_spelling(self):
        item = (
            b'{ "title" : "Role\\u0020One", "id":"slice-1",'
            b' "company":{"display_name":"Example"},'
            b' "location":{"display_name":"Remote"},'
            b' "redirect_url":"https://jobs.example/slice-1",'
            b' "description":"Experience is required.", "score":1.00 }'
        )
        header = (
            b'{"citation_url":"https://developer.adzuna.com/overview",'
            b'"access_date":"2026-08-24","transcription_note":"no live call",'
            b'"data_class":"fixture"}'
        )
        body = b'{"_fixture":' + header + b',"results":[' + item + b']}'
        adapter, _, _ = ready_case(
            "aggregator", responses=(RawResponse(200, body),)
        )
        receipt = adapter.acquire()[0]
        self.assertEqual(receipt.payload, item)
        self.assertEqual(
            sha256(receipt.payload).hexdigest(),
            "af02c004a537d155a8c759f2e3554128f847950e08d37f0501d74513bcf3da1a",
        )
        self.assertNotEqual(receipt.payload, json.dumps(json.loads(item)).encode())

    def test_duplicate_path_member_and_duplicate_external_reference_fail_the_run(self):
        item = provider_document("aggregator")["results"][0]
        encoded = json.dumps(item, separators=(",", ":")).encode()
        fixture = json.dumps(
            json.loads(fixture_bytes("aggregator/representative.json"))["_fixture"],
            separators=(",", ":"),
        ).encode()
        bodies = (
            b'{"_fixture":' + fixture + b',"results":[' + encoded + b'],"results":[]}',
            b'{"_fixture":' + fixture + b',"results":[' + encoded + b',' + encoded + b']}',
        )
        for body in bodies:
            with self.subTest(body=body[-40:]):
                adapter, _, _ = ready_case(
                    "aggregator", responses=(RawResponse(200, body),)
                )
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, "contract_violation")

    def test_non_json_bom_trailing_material_and_forged_receipt_fail_closed(self):
        bodies = (
            b"not-json",
            b'\xef\xbb\xbf{"results":[]}',
            b'{"results":[]} trailing',
            b'{"results":[{"id":NaN}]}',
        )
        for body in bodies:
            with self.subTest(body=body[:20]):
                adapter, _, _ = ready_case(
                    "aggregator", responses=(RawResponse(200, body),)
                )
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertIn("response_shape", str(caught.exception))

        adapter, _, _ = ready_case("government")
        receipt = adapter.acquire()[0]
        with self.assertRaises(LicensedFeedError) as forged:
            adapter.normalize(replace(receipt, external_reference="forged"))
        self.assertEqual(forged.exception.code, "contract_violation")
        self.assertIn("external_reference", str(forged.exception))

    def test_untrusted_provider_html_is_reduced_to_plain_text_without_script_or_style_content(self):
        document = json.loads(fixture_bytes("direct_employer/greenhouse.json"))
        document["jobs"][0]["content"] = (
            "<p>Build <strong>accessible</strong> systems.</p>"
            "<script>steal()</script><style>body{display:none}</style>"
            "<p>Python experience is required.</p>"
        )
        body = json.dumps(document).encode()
        adapter, _, _ = ready_case(
            "greenhouse", responses=(RawResponse(200, body),)
        )
        normalized = adapter.normalize(adapter.acquire()[0])
        self.assertEqual(
            normalized.description,
            "Build accessible systems. Python experience is required.",
        )
        self.assertNotIn("steal", normalized.description)
        self.assertNotIn("display:none", normalized.description)

    def test_recorded_fixtures_use_no_socket_even_when_socket_is_guarded(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("socket called")):
            for name in ("aggregator", "government", "greenhouse", "lever"):
                adapter, _, _ = ready_case(name)
                self.assertEqual(len(adapter.acquire()), 1)

    def test_fixture_and_module_secret_scrub(self):
        suspicious_values = re.compile(
            rb"(?:sk-[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]{20,}\.)"
        )
        paths = tuple(FIXTURES.rglob("*.json")) + (
            ROOT / "services/my_opportunities/licensed_feed_adapter.py",
        )
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIsNone(suspicious_values.search(path.read_bytes()))
        for path in FIXTURES.rglob("*.json"):
            document = json.loads(path.read_text())
            self.assertEqual(document["_fixture"]["data_class"], "fixture")
            self.assertIn("no", document["_fixture"]["transcription_note"].casefold())


class PolicyAndRightsTests(unittest.TestCase):
    def test_registration_requires_matching_complete_current_policy_for_each_class(self):
        for name in ("aggregator", "government", "greenhouse"):
            with self.subTest(name=name):
                adapter, _, _ = case_factory(name)
                descriptor = adapter.describe()
                _, canonical, ingestion = services()
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_missing"):
                    ingestion.register(adapter, now=NOW)
                denied = complete_policy(
                    descriptor,
                    dimensions={**DIMENSIONS, "ai_ml_use": False},
                )
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
                    canonical.register_policy(denied, now=NOW)
                incomplete = complete_policy(
                    descriptor,
                    actions=ACTIONS - {"ai"},
                )
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
                    canonical.register_policy(incomplete, now=NOW)
                wrong_class = replace(
                    complete_policy(descriptor),
                    source_class="direct_employer" if descriptor.source_class != "direct_employer" else "permitted_public",
                )
                canonical.register_policy(wrong_class, now=NOW)
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
                    ingestion.register(adapter, now=NOW)

    def test_expired_and_not_yet_effective_policy_is_denied(self):
        for timing in (
            {"effective_at": NOW + timedelta(minutes=1)},
            {"expires_at": NOW},
        ):
            with self.subTest(timing=timing):
                adapter, _, _ = case_factory("government")
                _, canonical, ingestion = services()
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
                    canonical.register_policy(complete_policy(adapter.describe(), **timing), now=NOW)
                with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_missing"):
                    ingestion.register(adapter, now=NOW)

    def test_licensed_production_ledger_empty_refuses_registration_and_acquire_without_sender_call(self):
        view = PolicyView()
        sender_calls = []
        adapter = AggregatorFeedAdapter.production(
            production_environment(LICENSED_AGGREGATOR),
            policy_key="policy-empty-licensed",
            policy_version=1,
            policy_reader=view,
            sender=lambda request: sender_calls.append(request),
            budget=FeedBudget(min_request_interval_seconds=0.001),
        )
        _, _, ingestion = services()
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_missing"):
            ingestion.register(adapter, now=NOW)
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "policy_missing")
        self.assertEqual(sender_calls, [])

    def test_each_class_rechecks_current_policy_before_transport(self):
        for name in ("aggregator", "government", "greenhouse"):
            with self.subTest(name=name):
                adapter, view, _ = case_factory(name)
                transport = adapter._transport
                with self.assertRaises(LicensedFeedError) as missing:
                    adapter.acquire()
                self.assertEqual(missing.exception.code, "policy_missing")
                self.assertEqual(transport.fetch_count, 0)
                view.put(
                    adapter.describe(),
                    complete_policy(
                        adapter.describe(),
                        dimensions={**DIMENSIONS, "storage": False},
                    ),
                )
                with self.assertRaises(LicensedFeedError) as denied:
                    adapter.acquire()
                self.assertEqual(denied.exception.code, "policy_denied")
                self.assertEqual(transport.fetch_count, 0)

    def test_policy_narrowing_between_pages_stops_before_the_next_transport(self):
        body = fixture_bytes("aggregator/representative.json")
        adapter, view, _ = ready_case(
            "aggregator",
            responses=(
                RawResponse(200, body, next_page=True),
                RawResponse(200, body),
            ),
        )
        transport = adapter._transport
        fetch = transport.fetch

        def narrow_after_first_page(request):
            response = fetch(request)
            view.put(
                adapter.describe(),
                complete_policy(
                    adapter.describe(),
                    version=2,
                    dimensions={**DIMENSIONS, "storage": False},
                ),
            )
            return response

        transport.fetch = narrow_after_first_page
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "policy_denied")
        self.assertEqual(transport.fetch_count, 1)
        self.assertEqual(adapter.last_run.pages, 1)

    def test_policy_key_mismatch_is_denied_before_transport(self):
        adapter, view, _ = case_factory("aggregator")
        view.put(
            adapter.describe(),
            replace(complete_policy(adapter.describe()), policy_key="different-policy"),
        )
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "policy_denied")
        self.assertEqual(adapter._transport.fetch_count, 0)

        newer_descriptor = replace(adapter.describe(), policy_version=2)
        adapter._descriptor = newer_descriptor
        view.put(newer_descriptor, complete_policy(newer_descriptor, version=1))
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "policy_denied")
        self.assertEqual(adapter._transport.fetch_count, 0)

    def test_rights_projection_drops_description_excerpt_and_attribution(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        document["results"][0].update(
            {
                "snippet": "A contract-permitted excerpt candidate.",
                "attribution": "A contract-required attribution candidate.",
            }
        )
        adapter, view, _ = ready_case(
            "aggregator",
            responses=(RawResponse(200, json.dumps(document).encode()),),
        )
        receipt = adapter.acquire()[0]
        restrictive = complete_policy(
            adapter.describe(),
            version=2,
            dimensions={
                **DIMENSIONS,
                "excerpt": False,
                "full_description": False,
                "attribution": False,
            },
        )
        view.put(adapter.describe(), restrictive)
        normalized = adapter.normalize(receipt)
        self.assertEqual(normalized.description, "")
        self.assertEqual(normalized.requirement_clauses, ())
        self.assertNotIn("snippet", normalized.fields)
        self.assertNotIn("attribution", normalized.fields)
        self.assertEqual(normalized.employer, "Northstar Example Labs")

    def test_storage_denial_projects_no_source_content_and_c2_independently_denies(self):
        adapter, view, _ = ready_case("government")
        receipt = adapter.acquire()[0]
        denied = complete_policy(
            adapter.describe(),
            version=2,
            dimensions={**DIMENSIONS, "storage": False},
        )
        view.put(adapter.describe(), denied)
        normalized = adapter.normalize(receipt)
        self.assertEqual(
            (
                normalized.external_reference,
                normalized.employer,
                normalized.title,
                normalized.locations,
                normalized.application_url,
                normalized.description,
                normalized.fields,
            ),
            ("", "", "", (), "", "", {}),
        )
        repository, canonical, ingestion = services()
        initial = complete_policy(adapter.describe())
        canonical.register_policy(initial, now=NOW)
        ingestion.register(adapter, now=NOW)
        canonical.revise_policy(denied, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            canonical.record_receipt(adapter.describe(), receipt, now=NOW)
        self.assertEqual(repository._receipts, {})

    def test_fixture_production_and_source_class_mixing_are_refused(self):
        adapter, _, _ = case_factory("government")
        descriptor = adapter.describe()
        _, canonical, ingestion = services()
        production_policy = replace(complete_policy(descriptor), data_class="production")
        canonical.register_policy(production_policy, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_missing"):
            ingestion.register(adapter, now=NOW)
        wrong_class = replace(complete_policy(descriptor), source_class=LICENSED_AGGREGATOR)
        _, canonical, ingestion = services()
        canonical.register_policy(wrong_class, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            ingestion.register(adapter, now=NOW)


class BudgetAndErrorTaxonomyTests(unittest.TestCase):
    def test_package_hard_budget_ceilings_reject_unbounded_callers(self):
        for kwargs in (
            {"max_pages": 6},
            {"max_items": 201},
            {"max_total_bytes": 10 * 1024 * 1024 + 1},
            {"max_seconds": 30.1},
            {"max_transient_retries": 3},
            {"max_rate_limit_retries": 2},
            {"max_retry_delay_seconds": 2.1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    FeedBudget(**kwargs)

    def test_every_live_request_carries_a_positive_finite_remaining_timeout(self):
        body = json.dumps(provider_document("aggregator")).encode()
        adapter, _, calls = production_aggregator([RawResponse(200, body)])
        adapter.acquire()
        self.assertEqual(len(calls), 1)
        self.assertGreater(calls[0].timeout_seconds, 0)
        self.assertLessEqual(calls[0].timeout_seconds, adapter._budget.max_seconds)
        for value in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(value=value):
                with self.assertRaises(LicensedFeedError) as caught:
                    FeedRequest("https://api.example.test", 1, {}, value)
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertIn("request_timeout", str(caught.exception))

    def test_overdue_live_sender_return_is_rejected_without_a_followup_attempt(self):
        calls = []
        seen_timeouts = []

        def sender(request):
            calls.append(request)
            seen_timeouts.append(request.timeout_seconds)
            time.sleep(0.01)
            return RawResponse(200, json.dumps(provider_document("aggregator")).encode())

        view = PolicyView()
        adapter = AggregatorFeedAdapter.production(
            production_environment(LICENSED_AGGREGATOR),
            policy_key="policy-overdue-sender",
            policy_version=1,
            policy_reader=view,
            sender=sender,
            budget=FeedBudget(
                max_seconds=0.001,
                max_transient_retries=0,
                min_request_interval_seconds=0.001,
            ),
        )
        view.put(adapter.describe(), complete_policy(adapter.describe()))
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "transient_exhausted")
        self.assertEqual(len(calls), 1)
        self.assertEqual(adapter.last_run.attempts, 1)
        self.assertEqual(len(seen_timeouts), 1)
        self.assertGreater(seen_timeouts[0], 0)
        self.assertLessEqual(seen_timeouts[0], 0.001)

    def test_auth_rejection_stops_without_retry(self):
        adapter, _, calls = production_aggregator([RawResponse(401, b"denied")])
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "credentials_rejected")
        self.assertEqual((len(calls), adapter.last_run.attempts), (1, 1))

    def test_rate_limit_honors_one_bounded_backoff_then_stops(self):
        sleeps = []
        adapter, _, calls = production_aggregator(
            [
                RawResponse(429, b"limited", retry_after_seconds=0.25),
                RawResponse(429, b"limited", retry_after_seconds=0.25),
            ],
            budget=FeedBudget(max_retry_delay_seconds=0.25),
            sleeper=sleeps.append,
        )
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [0.25, 0.001])

    def test_retry_after_above_ceiling_stops_without_an_early_retry(self):
        sleeps = []
        adapter, _, calls = production_aggregator(
            [RawResponse(429, b"limited", retry_after_seconds=30)],
            budget=FeedBudget(max_retry_delay_seconds=0.25),
            sleeper=sleeps.append,
        )
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertEqual((len(calls), sleeps), (1, []))

    def test_production_class_rate_ceilings_cannot_be_weakened(self):
        operations = (
            lambda: AggregatorFeedAdapter.production(
                production_environment(LICENSED_AGGREGATOR),
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
            ),
            lambda: GovernmentFeedAdapter.production(
                production_environment(GOVERNMENT_FEED),
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
                budget=FeedBudget(min_request_interval_seconds=0.5),
            ),
            lambda: DirectEmployerFeedAdapter.production(
                production_environment(DIRECT_EMPLOYER),
                ats="greenhouse",
                board="example",
                policy_key="p",
                policy_version=1,
                policy_reader=PolicyView(),
                sender=lambda _: None,
                budget=FeedBudget(min_request_interval_seconds=0.5),
            ),
        )
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(LicensedFeedError) as caught:
                    operation()
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertIn("rate_budget", str(caught.exception))

    def test_transient_status_and_timeout_retry_at_most_twice(self):
        scenarios = (
            [RawResponse(503, b"down")] * 3,
            [TimeoutError("fixture timeout")] * 3,
        )
        for script in scenarios:
            with self.subTest(kind=type(script[0]).__name__):
                adapter, _, calls = production_aggregator(
                    list(script),
                    sleeper=lambda _: None,
                )
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, "transient_exhausted")
                self.assertEqual((len(calls), adapter.last_run.attempts), (3, 3))

    def test_oversize_total_and_page_budgets_fail_closed(self):
        body = fixture_bytes("aggregator/representative.json")
        scenarios = (
            (
                FeedBudget(max_payload_bytes=len(body) - 1),
                (RawResponse(200, body),),
                "contract_violation",
            ),
            (
                FeedBudget(max_total_bytes=len(body)),
                (RawResponse(200, body, next_page=True), RawResponse(200, body)),
                "contract_violation",
            ),
            (
                FeedBudget(max_pages=1),
                (RawResponse(200, body, next_page=True), RawResponse(200, body)),
                "budget_exhausted",
            ),
        )
        for budget, responses, error_code in scenarios:
            with self.subTest(error_code=error_code, budget=budget):
                adapter, _, _ = ready_case(
                    "aggregator",
                    responses=responses,
                    budget=budget,
                )
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, error_code)

    def test_item_budget_truncates_without_an_unbounded_followup(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        second = dict(document["results"][0])
        second["id"] = "aggregator-fixture-002"
        document["results"].append(second)
        body = json.dumps(document).encode()
        adapter, _, _ = ready_case(
            "aggregator",
            responses=(RawResponse(200, body),),
            budget=FeedBudget(max_items=1),
        )
        self.assertEqual(len(adapter.acquire()), 1)
        self.assertTrue(adapter.last_run.truncated)
        self.assertEqual(adapter.last_run.attempts, 1)

    def test_multi_item_receipts_do_not_inflate_retained_bytes_beyond_wire_bytes(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        second = dict(document["results"][0])
        second["id"] = "aggregator-fixture-002"
        document["results"].append(second)
        body = json.dumps(document).encode()
        adapter, _, _ = ready_case(
            "aggregator",
            responses=(RawResponse(200, body),),
            budget=FeedBudget(max_total_bytes=len(body)),
        )
        receipts = adapter.acquire()
        self.assertEqual(len(receipts), 2)
        self.assertLessEqual(sum(len(item.payload) for item in receipts), len(body))

    def test_wait_is_capped_by_remaining_time_and_no_retry_occurs(self):
        times = iter((0.0, 0.0, 0.0, 0.0, 0.75))
        sleeps = []
        adapter, _, calls = production_aggregator(
            [RawResponse(429, b"limited", retry_after_seconds=0.5)],
            budget=FeedBudget(max_seconds=1.0, max_retry_delay_seconds=1.0),
            sleeper=sleeps.append,
        )
        adapter._monotonic = lambda: next(times)
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertEqual((len(calls), sleeps), (1, [0.25]))

    def test_wall_clock_budget_stops_before_transport(self):
        times = iter((0.0, 2.0))
        adapter, _, _ = ready_case(
            "government",
            budget=FeedBudget(max_seconds=1.0),
            monotonic=lambda: next(times),
        )
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "budget_exhausted")
        self.assertEqual(adapter._transport.fetch_count, 0)

    def test_external_reference_mismatch_and_non_success_status_are_contract_violations(self):
        body = fixture_bytes("aggregator/representative.json")
        scenarios = (
            RawResponse(200, body, external_reference="different"),
            RawResponse(418, body),
        )
        for response in scenarios:
            adapter, _, _ = ready_case("aggregator", responses=(response,))
            with self.assertRaises(LicensedFeedError) as caught:
                adapter.acquire()
            self.assertEqual(caught.exception.code, "contract_violation")

    def test_sender_returning_an_unknown_response_shape_fails_closed(self):
        adapter, _, calls = production_aggregator([object()])
        with self.assertRaises(LicensedFeedError) as caught:
            adapter.acquire()
        self.assertEqual(caught.exception.code, "contract_violation")
        self.assertEqual(len(calls), 1)

    def test_invalid_response_metadata_and_media_type_fail_closed(self):
        body = fixture_bytes("aggregator/representative.json")
        scenarios = (
            RawResponse(200.0, body),
            RawResponse(200, body, next_page="yes"),
            RawResponse(200, body, content_type="text/html"),
            RawResponse(429, body, retry_after_seconds=float("nan")),
            RawResponse(429, body, retry_after_seconds=-1),
        )
        for response in scenarios:
            with self.subTest(response=response):
                adapter, _, calls = production_aggregator([response])
                with self.assertRaises(LicensedFeedError) as caught:
                    adapter.acquire()
                self.assertEqual(caught.exception.code, "contract_violation")
                self.assertEqual(len(calls), 1)


class IngestionAndLifecycleTests(unittest.TestCase):
    def _registered(self, name: str, *, retained=(), priority=1, responses=None):
        adapter, view, _ = case_factory(name, responses=responses)
        policy = complete_policy(
            adapter.describe(),
            retained_source_fields=retained,
            priority=priority,
        )
        view.put(adapter.describe(), policy)
        repository, canonical, ingestion = services()
        canonical.register_policy(policy, now=NOW)
        ingestion.register(adapter, now=NOW)
        return adapter, view, repository, canonical, ingestion, policy

    def test_end_to_end_ingestion_all_classes_and_duplicate_observation(self):
        for name in ("aggregator", "government", "greenhouse"):
            with self.subTest(name=name):
                adapter, _, repository, _, ingestion, _ = self._registered(name)
                listing = ingestion.ingest(adapter, now=NOW)[0]
                self.assertEqual(listing.state, "current")
                self.assertEqual(len(repository.versions_for_listing(listing.listing_key)), 1)
                replay, replay_view, _ = case_factory(name)
                replay_view.put(replay.describe(), complete_policy(replay.describe()))
                ingestion.register(replay, now=NOW)
                same = ingestion.ingest(replay, now=NOW + timedelta(minutes=1))[0]
                self.assertEqual(same.listing_key, listing.listing_key)
                self.assertEqual(len(repository.versions_for_listing(listing.listing_key)), 1)
                version = repository.version(listing.current_version_key)
                receipt = repository.receipt(version.receipt_key)
                self.assertEqual(receipt.payload_sha256, sha256(receipt.payload).hexdigest())

    def test_one_multi_item_provider_page_admits_one_listing_per_item(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        second = dict(document["results"][0])
        second.update(
            {
                "id": "aggregator-fixture-002",
                "title": "Independent Second Role",
                "redirect_url": "https://jobs.example/aggregator-fixture-002",
            }
        )
        document["results"].append(second)
        body = json.dumps(document, separators=(",", ":")).encode()
        adapter, _, repository, _, ingestion, _ = self._registered(
            "aggregator",
            responses=(RawResponse(200, body),),
        )
        listings = ingestion.ingest(adapter, now=NOW)
        self.assertEqual(len(listings), 2)
        self.assertEqual(len({item.listing_key for item in listings}), 2)
        payloads = {
            repository.receipt(
                repository.version(item.current_version_key).receipt_key
            ).payload
            for item in listings
        }
        self.assertEqual(
            payloads,
            {
                json.dumps(item, separators=(",", ":")).encode()
                for item in document["results"]
            },
        )

    def test_item_receipts_isolate_malformed_and_removed_siblings_end_to_end(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        first = dict(document["results"][0])
        first.update(
            id="isolated-a",
            title="Isolated A",
            redirect_url="https://jobs.example/isolated-a",
            description="REMOVED-ONLY-A experience is required.",
        )
        malformed = dict(first)
        malformed.update(
            id="isolated-malformed",
            company=[],
            description="MALFORMED-ONLY-M",
        )
        second = dict(first)
        second.update(
            id="isolated-b",
            title="Isolated B",
            redirect_url="https://jobs.example/isolated-b",
            description="SURVIVING-ONLY-B experience is required.",
        )
        document["results"] = [first, malformed, second]
        body = json.dumps(document, separators=(",", ":")).encode()
        adapter, view, repository, canonical, ingestion, policy = self._registered(
            "aggregator",
            responses=(RawResponse(200, body),),
        )
        listings = ingestion.ingest(adapter, now=NOW)
        self.assertEqual(len(listings), 2)
        self.assertEqual(adapter.last_run.refusal_codes, ("payload_malformed",))
        by_reference = {item.external_reference: item for item in listings}
        a_version = repository.version(by_reference["isolated-a"].current_version_key)
        b_version = repository.version(by_reference["isolated-b"].current_version_key)
        a_receipt = repository.receipt(a_version.receipt_key)
        b_receipt = repository.receipt(b_version.receipt_key)
        self.assertIn(b"REMOVED-ONLY-A", a_receipt.payload)
        self.assertNotIn(b"SURVIVING-ONLY-B", a_receipt.payload)
        self.assertIn(b"SURVIVING-ONLY-B", b_receipt.payload)
        self.assertNotIn(b"REMOVED-ONLY-A", b_receipt.payload)
        self.assertNotIn(b"MALFORMED-ONLY-M", a_receipt.payload + b_receipt.payload)

        revision = replace(
            policy,
            version=2,
            dimensions={**DIMENSIONS, "display": False},
            evidence_ref="fixture-removal-evidence",
            decision_ref="fixture-removal-decision",
        )
        view.put(adapter.describe(), revision)
        canonical.revise_policy(revision, now=NOW)
        TerminationExitRehearsal.remove(
            canonical,
            by_reference["isolated-a"].listing_key,
            now=NOW,
            reason="isolated-removal",
        )
        self.assertIsNone(repository.receipt(a_version.receipt_key).payload)
        self.assertEqual(repository.receipt(b_version.receipt_key).payload, b_receipt.payload)
        self.assertNotIn(b"REMOVED-ONLY-A", repository.receipt(b_version.receipt_key).payload)

    def test_termination_prevalidation_and_repository_policy_stop_transport(self):
        repository, canonical, ingestion = services()

        def current_policy(descriptor):
            versions = repository.policy_versions(
                descriptor.policy_key,
                descriptor.data_class,
            )
            return max(versions, key=lambda item: item.version) if versions else None

        adapter, _, _ = case_factory("aggregator", policy_view=current_policy)
        policy = complete_policy(adapter.describe())
        canonical.register_policy(policy, now=NOW)
        ingestion.register(adapter, now=NOW)
        listing = ingestion.ingest(adapter, now=NOW)[0]
        calls_before = adapter._transport.fetch_count

        weak = replace(
            policy,
            version=2,
            dimensions={**DIMENSIONS, "display": False},
            evidence_ref="fixture-weak-termination-evidence",
            decision_ref="fixture-weak-termination-decision",
        )
        with self.assertRaises(LicensedFeedError) as caught:
            TerminationExitRehearsal.terminate(
                canonical,
                repository,
                weak,
                (listing.listing_key,),
                now=NOW,
                reason="weak-termination",
            )
        self.assertEqual(caught.exception.code, "contract_violation")
        self.assertEqual(len(repository.policy_versions(policy.policy_key, "fixture")), 1)
        self.assertEqual(repository.listing(listing.listing_key).state, "current")

        strong = replace(
            weak,
            dimensions={**DIMENSIONS, "display": False, "storage": False},
            evidence_ref="fixture-strong-termination-evidence",
            decision_ref="fixture-strong-termination-decision",
        )
        self.assertFalse(strong.allows("register", NOW))
        for listing_keys in (
            (listing.listing_key, "missing-listing"),
            ("missing-listing", listing.listing_key),
        ):
            with self.subTest(listing_keys=listing_keys):
                with self.assertRaises(LicensedFeedError) as invalid_set:
                    TerminationExitRehearsal.terminate(
                        canonical,
                        repository,
                        strong,
                        listing_keys,
                        now=NOW,
                        reason="strong-termination",
                    )
                self.assertEqual(invalid_set.exception.code, "contract_violation")
                self.assertIn("termination_listing_set", str(invalid_set.exception))
                self.assertEqual(
                    len(repository.policy_versions(policy.policy_key, "fixture")), 1
                )
                self.assertEqual(repository.listing(listing.listing_key).state, "current")
        TerminationExitRehearsal.terminate(
            canonical,
            repository,
            strong,
            (listing.listing_key,),
            now=NOW,
            reason="strong-termination",
        )
        with self.assertRaises(LicensedFeedError) as stopped:
            adapter.acquire()
        self.assertEqual(stopped.exception.code, "policy_denied")
        self.assertEqual(adapter._transport.fetch_count, calls_before)
        self.assertEqual(adapter.last_run.attempts, 0)
        tombstone_count = len(repository.content_tombstones)
        TerminationExitRehearsal.terminate(
            canonical,
            repository,
            strong,
            (listing.listing_key,),
            now=NOW,
            reason="strong-termination-replay",
        )
        self.assertEqual(len(repository.content_tombstones), tombstone_count)

    def test_termination_replay_resumes_an_exact_partial_revision(self):
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        second = dict(document["results"][0])
        second.update(
            id="termination-second",
            title="Termination Second",
            redirect_url="https://jobs.example/termination-second",
        )
        document["results"].append(second)
        adapter, view, repository, canonical, ingestion, policy = self._registered(
            "aggregator",
            responses=(
                RawResponse(200, json.dumps(document, separators=(",", ":")).encode()),
            ),
        )
        listings = ingestion.ingest(adapter, now=NOW)
        revision = replace(
            policy,
            version=2,
            dimensions={**DIMENSIONS, "display": False, "storage": False},
            evidence_ref="fixture-resume-termination-evidence",
            decision_ref="fixture-resume-termination-decision",
        )
        view.put(adapter.describe(), revision)
        canonical.revise_policy(revision, now=NOW)
        canonical.tombstone_source_content(
            listings[0].listing_key,
            now=NOW,
            disposition="termination",
            reason="interrupted-termination",
        )
        TerminationExitRehearsal.terminate(
            canonical,
            repository,
            revision,
            tuple(item.listing_key for item in listings),
            now=NOW,
            reason="resumed-termination",
        )
        self.assertEqual(len(repository.content_tombstones), 2)
        self.assertTrue(
            all(repository.listing(item.listing_key).state == "invalid" for item in listings)
        )

    def test_changed_content_creates_version_and_terminal_listing_never_revives(self):
        adapter, _, repository, canonical, ingestion, _ = self._registered("aggregator")
        listing = ingestion.ingest(adapter, now=NOW)[0]
        document = json.loads(fixture_bytes("aggregator/representative.json"))
        document["results"][0]["description"] = (
            "Materially changed. Python experience is required."
        )
        body = json.dumps(document, sort_keys=True).encode()
        changed, changed_view, _ = case_factory(
            "aggregator", responses=(RawResponse(200, body),)
        )
        changed_view.put(changed.describe(), complete_policy(changed.describe()))
        ingestion.register(changed, now=NOW)
        changed_listing = ingestion.ingest(changed, now=NOW + timedelta(minutes=1))[0]
        self.assertEqual(changed_listing.state, "changed")
        self.assertEqual(len(repository.versions_for_listing(listing.listing_key)), 2)
        canonical.confirm_closed(listing.listing_key, now=NOW + timedelta(minutes=2))
        replay, replay_view, _ = case_factory("aggregator")
        replay_view.put(replay.describe(), complete_policy(replay.describe()))
        ingestion.register(replay, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "terminal_listing"):
            ingestion.ingest(replay, now=NOW + timedelta(minutes=3))

    def test_admission_refusals_for_each_class_persist_nothing(self):
        for name in ("aggregator", "government", "greenhouse"):
            for mutation in ("url", "employer", "title", "locations"):
                with self.subTest(name=name, mutation=mutation):
                    if name == "greenhouse" and mutation == "employer":
                        with self.assertRaises(LicensedFeedError) as caught:
                            case_factory(name, employer=" ")
                        self.assertEqual(caught.exception.code, "contract_violation")
                        self.assertIn("employer_registration", str(caught.exception))
                        continue
                    adapter, view, relative = case_factory(name)
                    document = json.loads(fixture_bytes(relative))
                    payload = provider_item(name, document)
                    if name == "aggregator":
                        fields = {
                            "url": "redirect_url",
                            "employer": "company",
                            "title": "title",
                            "locations": "location",
                        }
                    elif name == "government":
                        fields = {
                            "url": "PositionURI",
                            "employer": "OrganizationName",
                            "title": "PositionTitle",
                            "locations": "PositionLocation",
                        }
                    else:
                        fields = {
                            "url": "absolute_url",
                            "title": "title",
                            "locations": "location",
                        }
                    payload[fields[mutation]] = (
                        "http://unsafe.example"
                        if mutation == "url"
                        else ({} if mutation == "locations" else "")
                    )
                    body = json.dumps(document).encode()
                    adapter, view, _ = case_factory(name, responses=(RawResponse(200, body),))
                    policy = complete_policy(adapter.describe())
                    view.put(adapter.describe(), policy)
                    repository, canonical, ingestion = services()
                    canonical.register_policy(policy, now=NOW)
                    ingestion.register(adapter, now=NOW)
                    try:
                        admitted = ingestion.ingest(adapter, now=NOW)
                    except (LicensedFeedError, MyOpportunitiesCanonicalError) as error:
                        self.assertIn(
                            getattr(error, "code", ""),
                            {"payload_malformed", "admission_refused"},
                        )
                    else:
                        self.assertEqual(admitted, ())
                        self.assertIn("payload_malformed", adapter.last_run.refusal_codes)
                    self.assertEqual(repository._receipts, {})

    def test_cross_class_dedupe_and_termination_failover_preserve_member_truth(self):
        aggregate_doc = json.loads(fixture_bytes("aggregator/representative.json"))
        aggregate_doc["results"][0].update(
            {
                "title": "Shared Role",
                "company": {"display_name": "Shared Employer"},
                "location": {"display_name": "Remote"},
                "redirect_url": "https://jobs.example/shared-role",
            }
        )
        direct_doc = json.loads(fixture_bytes("direct_employer/greenhouse.json"))
        direct_doc["jobs"][0].update(
            {
                "title": "Shared Role",
                "location": {"name": "Remote"},
                "absolute_url": "https://jobs.example/shared-role",
            }
        )
        view = PolicyView()
        aggregate, _, _ = case_factory(
            "aggregator",
            policy_view=view,
            responses=(RawResponse(200, json.dumps(aggregate_doc).encode()),),
        )
        direct, _, _ = case_factory(
            "greenhouse",
            policy_view=view,
            employer="Shared Employer",
            responses=(RawResponse(200, json.dumps(direct_doc).encode()),),
        )
        aggregate_policy = complete_policy(aggregate.describe(), priority=1)
        direct_policy = complete_policy(direct.describe(), priority=2)
        view.put(aggregate.describe(), aggregate_policy)
        view.put(direct.describe(), direct_policy)
        repository, canonical, ingestion = services()
        for policy, adapter in ((aggregate_policy, aggregate), (direct_policy, direct)):
            canonical.register_policy(policy, now=NOW)
            ingestion.register(adapter, now=NOW)
        aggregate_listing = ingestion.ingest(aggregate, now=NOW)[0]
        direct_listing = ingestion.ingest(direct, now=NOW)[0]
        self.assertEqual(
            aggregate_listing.canonical_opportunity_key,
            direct_listing.canonical_opportunity_key,
        )
        opportunity_key = aggregate_listing.canonical_opportunity_key
        self.assertEqual(canonical.resolve_opportunity(opportunity_key).governing_listing_key, aggregate_listing.listing_key)
        member_truth, reread_member_truth = member_truth_fixture(
            "failover",
            repository,
            aggregate_listing,
        )
        revision = replace(
            aggregate_policy,
            version=2,
            dimensions={**DIMENSIONS, "display": False, "storage": False},
            evidence_ref="fixture-termination-evidence",
            decision_ref="fixture-termination-decision",
        )
        view.put(aggregate.describe(), revision)
        TerminationExitRehearsal.terminate(
            canonical,
            repository,
            revision,
            (aggregate_listing.listing_key,),
            now=NOW + timedelta(minutes=1),
            reason="fixture-termination",
        )
        opportunity = canonical.resolve_opportunity(opportunity_key)
        self.assertEqual(opportunity.governing_listing_key, direct_listing.listing_key)
        self.assertEqual(repository.listing(aggregate_listing.listing_key).state, "invalid")
        TerminationExitRehearsal.assert_member_truth_unchanged(
            member_truth,
            reread_member_truth(),
        )

    def test_removal_and_termination_rehearse_both_survivable_fact_branches_per_class(self):
        retained = ("source_version.employer", "source_version.title")
        for name in ("aggregator", "government", "greenhouse"):
            for disposition in ("removal", "termination"):
                for survives in (True, False):
                    with self.subTest(
                        name=name,
                        disposition=disposition,
                        survives=survives,
                    ):
                        initial_retained = retained
                        adapter, view, repository, canonical, ingestion, policy = self._registered(
                            name,
                            retained=initial_retained,
                        )
                        listing = ingestion.ingest(adapter, now=NOW)[0]
                        member_truth, reread_member_truth = member_truth_fixture(
                            f"{name}-{disposition}-{survives}",
                            repository,
                            listing,
                        )
                        revision = replace(
                            policy,
                            version=2,
                            dimensions={
                                **DIMENSIONS,
                                "display": False,
                                "storage": False,
                                "survivable_minimal_facts": survives,
                            },
                            retained_source_fields=retained if survives else (),
                            evidence_ref=f"fixture-{disposition}-evidence",
                            decision_ref=f"fixture-{disposition}-decision",
                        )
                        view.put(adapter.describe(), revision)
                        if disposition == "removal":
                            canonical.revise_policy(revision, now=NOW)
                            TerminationExitRehearsal.remove(
                                canonical,
                                listing.listing_key,
                                now=NOW,
                                reason="fixture-removal",
                            )
                        else:
                            TerminationExitRehearsal.terminate(
                                canonical,
                                repository,
                                revision,
                                (listing.listing_key,),
                                now=NOW,
                                reason="fixture-termination",
                            )
                        version = repository.version(listing.current_version_key)
                        if survives:
                            self.assertTrue(version.employer)
                            self.assertTrue(version.title)
                        else:
                            self.assertIsNone(version.employer)
                            self.assertIsNone(version.title)
                        self.assertEqual(
                            repository.listing(listing.listing_key).state,
                            "closed" if disposition == "removal" else "invalid",
                        )
                        tombstone = repository.content_tombstones[-1]
                        self.assertEqual(tombstone.disposition, disposition)
                        self.assertEqual(
                            tombstone.retained_source_fields,
                            retained if survives else (),
                        )
                        TerminationExitRehearsal.assert_member_truth_unchanged(
                            member_truth,
                            reread_member_truth(),
                        )

    def test_exit_manifest_separates_peer_slate_records_and_rights_permitted_identifiers(self):
        for name in ("aggregator", "government", "greenhouse"):
            with self.subTest(name=name):
                adapter, _, _ = ready_case(name)
                allowed = complete_policy(
                    adapter.describe(),
                    retained_source_fields=("listing.external_reference",),
                )
                repository, canonical, _ = services()
                canonical.register_policy(allowed, now=NOW)

                def current_policy(descriptor):
                    versions = repository.policy_versions(
                        descriptor.policy_key,
                        descriptor.data_class,
                    )
                    return max(versions, key=lambda item: item.version) if versions else None

                manifest = TerminationExitRehearsal.export_manifest(
                    adapter.describe(),
                    policy_reader=current_policy,
                    now=NOW,
                    peer_slate_record_keys=("save-2", "save-1"),
                    source_identifiers=("source-2", "source-1"),
                )
                self.assertEqual(manifest.peer_slate_record_keys, ("save-1", "save-2"))
                self.assertEqual(
                    manifest.permitted_source_identifiers,
                    ("source-1", "source-2"),
                )
                denied = replace(
                    allowed,
                    version=2,
                    dimensions={**DIMENSIONS, "exit": False},
                )
                canonical.revise_policy(denied, now=NOW)
                self.assertTrue(allowed.allows("export", NOW))
                with self.assertRaises(LicensedFeedError) as caught:
                    TerminationExitRehearsal.export_manifest(
                        adapter.describe(),
                        policy_reader=current_policy,
                        now=NOW,
                        peer_slate_record_keys=("save-1",),
                        source_identifiers=("source-1",),
                    )
                self.assertEqual(caught.exception.code, "policy_denied")

    def test_member_truth_rehearsal_fails_on_any_relationship_or_assessment_change(self):
        TerminationExitRehearsal.assert_member_truth_unchanged(("save", "assessment"), ("save", "assessment"))
        with self.assertRaises(LicensedFeedError) as caught:
            TerminationExitRehearsal.assert_member_truth_unchanged(("save",), ("save", "changed"))
        self.assertEqual(caught.exception.code, "contract_violation")


if __name__ == "__main__":
    unittest.main()
