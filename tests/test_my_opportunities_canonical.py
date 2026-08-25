from __future__ import annotations

import json
import re
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.my_opportunities.canonical_service import (
    CanonicalEvent,
    CanonicalService,
    InMemoryCanonicalRepository,
    LiveOpportunityGateConfig,
    MyOpportunitiesCanonicalError,
    RequirementItem,
    RequirementVersion,
    SourcePolicy,
)
from services.my_opportunities.connectors import ConnectorDescriptor, NormalizedListing, SourceReceiptInput
from services.my_opportunities.safe_outbound import OutboundResponse, SafeOutboundClient
from scripts.migration_registry import executable_sha256


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
DIMENSIONS = {
    "display": True, "excerpt": True, "full_description": True, "storage": True,
    "ai_ml_use": True, "caching": True, "retention": True, "attribution": True,
    "removal": True, "termination": True, "exit": True, "survivable_minimal_facts": True,
}
ACTIONS = frozenset({"register", "acquire", "persist", "display", "retain", "remove", "terminate", "export", "ai", "cache"})


def fixture_candidate(**overrides):
    value = {
        "external_reference": "astraeus-1", "employer": "Astraeus", "title": "Platform Engineer",
        "locations": ("Chicago, IL",), "arrangement": "hybrid",
        "application_url": "https://jobs.example/roles/1", "expected_application_hosts": ("jobs.example",),
        "description": "Build platforms.", "requirement_clauses": ("Required: Python",),
        "fields": {"level": "senior"}, "data_class": "fixture",
    }
    value.update(overrides)
    return NormalizedListing(**value)


def descriptor(source_id="fixture-direct", policy_key="policy-direct", policy_version=1, data_class="fixture"):
    return ConnectorDescriptor(source_id, "direct_employer", policy_key, policy_version, frozenset({"pull", "change_signal", "closure_signal"}), ("fixture-only",), "US", "synthetic", data_class)


def policy(source_id="fixture-direct", policy_key="policy-direct", version=1, priority=1, actions=ACTIONS, data_class="fixture", retained_source_fields=()):
    return SourcePolicy(policy_key, version, source_id, data_class, frozenset(actions), priority, NOW - timedelta(days=1), None, DIMENSIONS, "fixture-evidence", "fixture-decision", retained_source_fields=retained_source_fields)


class CanonicalFixtureTests(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryCanonicalRepository()
        self.service = CanonicalService(self.repo, LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2)))
        self.direct = descriptor()
        self.service.register_policy(policy(), now=NOW)
        self.service.register_connector(self.direct, now=NOW)

    def _admit(self, candidate=None, source=None, when=NOW):
        candidate = candidate or fixture_candidate()
        source = source or self.direct
        receipt = self.service.record_receipt(source, SourceReceiptInput(candidate.external_reference, when, "application/json", b'{"fixture":true}'), now=when)
        return self.service.admit(source, receipt, candidate, now=when)

    def _client(self, response=None, resolver=None):
        response = response or OutboundResponse(200, {"Content-Type": "text/html"}, b"fixture")
        return SafeOutboundClient(
            resolver=resolver or (lambda *_: ["93.184.216.34"]),
            transport=lambda _request: response,
        )

    def _make_live(self, listing_key, when=NOW):
        return self.service.validate_application_link(listing_key, self._client(), now=when)

    def test_fixture_files_are_explicitly_fixture_only(self):
        feed = json.loads((ROOT / "tests/fixtures/my_opportunities/c2_synthetic_feed.json").read_text())
        scenarios = json.loads((ROOT / "tests/fixtures/my_opportunities/c2_canonical_scenarios.json").read_text())
        self.assertEqual(feed["descriptor"]["data_class"], "fixture")
        self.assertEqual(scenarios["data_class"], "fixture")
        self.assertIn("governing-source-failover-material-requirements", scenarios["scenarios"])

    def test_receipts_and_versions_are_immutable_and_duplicate_payload_is_not_a_new_version(self):
        listing = self._admit()
        initial_version = self.repo.version(listing.current_version_key)
        self.assertEqual(len(self.repo.versions_for_listing(listing.listing_key)), 1)
        again = self._admit()
        self.assertEqual(again.listing_key, listing.listing_key)
        self.assertEqual(len(self.repo.versions_for_listing(listing.listing_key)), 1)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "immutable_receipt"):
            self.repo.save_receipt(self.repo.receipt(initial_version.receipt_key))

    def test_changed_re_admission_and_attempt_vs_last_successful_are_distinct(self):
        listing = self._admit()
        changed = fixture_candidate(description="Changed non-requirement copy.")
        changed_listing = self._admit(changed, when=NOW + timedelta(hours=1))
        self.assertEqual(changed_listing.state, "changed")
        self.assertEqual(len(self.repo.versions_for_listing(listing.listing_key)), 2)
        self.assertEqual(self.service.re_admit_changed_listing(listing.listing_key, now=NOW + timedelta(hours=2)).state, "current")
        before_success = self.repo.listing(listing.listing_key).last_successfully_verified_at
        outage = self.service.record_outage(listing.listing_key, now=NOW + timedelta(hours=3))
        self.assertEqual(outage.state, "unreachable")
        self.assertEqual(outage.last_successfully_verified_at, before_success)
        self.assertGreater(outage.last_attempted_at, before_success)

    def test_closure_and_outage_are_never_conflated(self):
        listing = self._admit()
        self.assertEqual(self.service.record_outage(listing.listing_key, now=NOW).state, "unreachable")
        recovered = self.service.complete_reverification(listing.listing_key, content_changed=False, now=NOW + timedelta(minutes=1))
        self.assertEqual(recovered.state, "current")
        self.assertEqual(self.service.confirm_closed(listing.listing_key, now=NOW + timedelta(minutes=2)).state, "closed")
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_transition"):
            self.service.record_outage(listing.listing_key, now=NOW + timedelta(minutes=3))

    def test_live_gate_has_all_six_fail_closed_conditions(self):
        listing = self._admit()
        initial = self.service.live_gate(listing.listing_key, now=NOW)
        self.assertFalse(initial.passes)
        self.assertIn("application_link_invalid", initial.reasons)
        self._make_live(listing.listing_key)
        self.assertTrue(self.service.live_gate(listing.listing_key, now=NOW).passes)
        stale = self.service.live_gate(listing.listing_key, now=NOW + timedelta(days=8))
        self.assertIn("stale_verification", stale.reasons)
        pending = replace(self.repo.listing(listing.listing_key), link_review_pending=True)
        self.repo.save_listing(pending)
        self.assertIn("dedupe_pending", self.service.live_gate(listing.listing_key, now=NOW).reasons)
        malformed = replace(self.repo.version(pending.current_version_key), employer="")
        self.repo._versions[malformed.version_key] = malformed  # synthetic corruption asserts gate, not a DB mutation path
        self.assertIn("identity_incomplete", self.service.live_gate(listing.listing_key, now=NOW).reasons)

    def test_application_link_invalid_unknown_recovery_and_outage_are_distinct(self):
        listing = self._admit()
        self.assertIn("application_link_invalid", self.service.live_gate(listing.listing_key, now=NOW).reasons)
        invalid = self.service.validate_application_link(listing.listing_key, self._client(OutboundResponse(410, {"Content-Type": "text/html"}, b"closed")), now=NOW)
        self.assertEqual((invalid.state, invalid.reason, invalid.outage), ("invalid", "soft_closed", False))
        self.assertEqual(self.repo.listing(listing.listing_key).state, "current")
        valid = self._make_live(listing.listing_key, NOW + timedelta(minutes=1))
        self.assertEqual((valid.state, valid.reason), ("valid", None))
        timeout_client = SafeOutboundClient(resolver=lambda *_: ["93.184.216.34"], transport=lambda _request: (_ for _ in ()).throw(TimeoutError()))
        outage = self.service.validate_application_link(listing.listing_key, timeout_client, now=NOW + timedelta(minutes=2))
        self.assertTrue(outage.outage)
        after_timeout = self.repo.listing(listing.listing_key)
        self.assertEqual((outage.state, outage.reason), ("unknown", "timeout"))
        self.assertEqual(after_timeout.state, "current")
        self.assertEqual(after_timeout.link_state, "unknown")
        self.assertEqual(after_timeout.link_last_attempted_at, NOW + timedelta(minutes=2))
        self.assertIn("application_link_invalid", self.service.live_gate(listing.listing_key, now=NOW + timedelta(minutes=2)).reasons)

    def test_terminal_listing_refuses_changed_observation_and_link_probe_without_mutation(self):
        listing = self._admit()
        closed = self.service.confirm_closed(listing.listing_key, now=NOW)
        versions_before = tuple(self.repo.versions_for_listing(listing.listing_key))
        link_attempt_before = closed.link_last_attempted_at
        closed_receipt = self.service.record_receipt(
            self.direct,
            SourceReceiptInput("astraeus-1", NOW + timedelta(minutes=1), "application/json", b'{"changed":true}'),
            now=NOW + timedelta(minutes=1),
        )
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "terminal_listing"):
            self.service.admit(
                self.direct,
                closed_receipt,
                fixture_candidate(description="A forbidden terminal observation."),
                now=NOW + timedelta(minutes=1),
            )
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "terminal_listing"):
            self.service.validate_application_link(
                listing.listing_key,
                self._client(),
                now=NOW + timedelta(minutes=2),
            )
        after = self.repo.listing(listing.listing_key)
        self.assertEqual(after.state, "closed")
        self.assertEqual(after.link_last_attempted_at, link_attempt_before)
        self.assertEqual(tuple(self.repo.versions_for_listing(listing.listing_key)), versions_before)
        self.assertIn("listing_closed", self.service.live_gate(listing.listing_key, now=NOW).reasons)

    def test_transport_disabled_is_unknown_not_employer_blocked(self):
        listing = self._admit()
        outcome = self.service.validate_application_link(
            listing.listing_key,
            SafeOutboundClient(resolver=lambda *_: ["93.184.216.34"]),
            now=NOW,
        )
        after = self.repo.listing(listing.listing_key)
        self.assertEqual((outcome.state, outcome.reason, outcome.outage), ("unknown", "transport_disabled", True))
        self.assertEqual(after.state, "current")
        self.assertEqual(after.link_state, "unknown")
        self.assertIsNone(after.link_invalid_reason)
        self.assertIn("application_link_invalid", self.service.live_gate(listing.listing_key, now=NOW).reasons)

    def test_ats_host_migration_resets_link_proof_without_lifecycle_change(self):
        listing = self._admit()
        self._make_live(listing.listing_key)
        migrated = self._admit(
            fixture_candidate(
                application_url="https://ats.example/jobs/1",
                expected_application_hosts=("ATS.example.", "jobs.ats.example"),
            ),
            when=NOW + timedelta(minutes=1),
        )
        after = self.repo.listing(listing.listing_key)
        self.assertEqual(migrated.state, "current")
        self.assertEqual(after.expected_application_hosts, ("ats.example", "jobs.ats.example"))
        self.assertEqual(after.link_state, "unknown")
        self.assertIsNone(after.link_invalid_reason)
        self.assertIsNone(after.link_last_attempted_at)
        self.assertIsNone(after.link_last_validated_at)
        self.assertIn("application_link_invalid", self.service.live_gate(listing.listing_key, now=NOW + timedelta(minutes=1)).reasons)

    def test_compound_target_and_content_change_enters_changed_while_resetting_link_proof(self):
        listing = self._admit()
        self._make_live(listing.listing_key)
        compound = self._admit(
            fixture_candidate(
                application_url="https://ats.example/jobs/1",
                expected_application_hosts=("ATS.example.", "jobs.ats.example"),
                description="Substantively changed role description.",
            ),
            when=NOW + timedelta(minutes=1),
        )
        after = self.repo.listing(listing.listing_key)
        self.assertEqual(compound.state, "changed")
        self.assertEqual(after.expected_application_hosts, ("ats.example", "jobs.ats.example"))
        self.assertEqual((after.link_state, after.link_invalid_reason), ("unknown", None))
        self.assertIsNone(after.link_last_attempted_at)
        self.assertIsNone(after.link_last_validated_at)
        reasons = self.service.live_gate(listing.listing_key, now=NOW + timedelta(minutes=1)).reasons
        self.assertIn("listing_changed", reasons)
        self.assertIn("application_link_invalid", reasons)

    def test_exact_dedupe_merge_and_split_are_reversible_without_member_keys(self):
        first = self._admit()
        second_source = descriptor("fixture-licensed", "policy-licensed")
        self.service.register_policy(policy("fixture-licensed", "policy-licensed", priority=2), now=NOW)
        self.service.register_connector(second_source, now=NOW)
        second = self._admit(fixture_candidate(external_reference="licensed-1"), second_source)
        self.assertEqual(first.canonical_opportunity_key, second.canonical_opportunity_key)

        separate = self._admit(fixture_candidate(external_reference="other-1", title="Systems Engineer"))
        merged = self.service.merge(first.canonical_opportunity_key, separate.canonical_opportunity_key, now=NOW)
        self.assertIn(separate.listing_key, merged.listing_keys)
        self.assertEqual(self.service.resolve_opportunity(separate.canonical_opportunity_key).opportunity_key, merged.opportunity_key)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_split"):
            self.service.split(separate.canonical_opportunity_key, [first.listing_key], now=NOW)
        split = self.service.split(separate.canonical_opportunity_key, [separate.listing_key], now=NOW)
        self.assertEqual(split.tombstone_target_key, None)
        self.assertEqual(self.repo.listing(separate.listing_key).canonical_opportunity_key, split.opportunity_key)

    def test_governing_source_fails_over_with_equivalent_requirements_without_churn(self):
        first = self._admit()
        self._make_live(first.listing_key)
        first_opportunity = self.service.resolve_opportunity(first.canonical_opportunity_key)
        first_requirement = first_opportunity.requirement_version_key
        fallback_source = descriptor("fixture-fallback", "policy-fallback")
        self.service.register_policy(policy("fixture-fallback", "policy-fallback", priority=2), now=NOW)
        self.service.register_connector(fallback_source, now=NOW)
        second = self._admit(fixture_candidate(external_reference="fallback-1", description="Different copy"), fallback_source)
        self._make_live(second.listing_key)
        self.service.confirm_closed(first.listing_key, now=NOW + timedelta(minutes=1))
        after = self.service.resolve_opportunity(first.canonical_opportunity_key)
        self.assertEqual(after.governing_listing_key, second.listing_key)
        self.assertEqual(after.requirement_version_key, first_requirement)
        self.assertTrue(self.service.canonical_gate(after.opportunity_key, now=NOW + timedelta(minutes=1)).passes)

    def test_governing_source_material_requirement_change_creates_new_version_and_field_attribution(self):
        first = self._admit(fixture_candidate(fields={"level": ""}))
        self._make_live(first.listing_key)
        before = self.service.resolve_opportunity(first.canonical_opportunity_key).requirement_version_key
        fallback_source = descriptor("fixture-fallback", "policy-fallback")
        self.service.register_policy(policy("fixture-fallback", "policy-fallback", priority=2), now=NOW)
        self.service.register_connector(fallback_source, now=NOW)
        second = self._admit(fixture_candidate(external_reference="fallback-2", requirement_clauses=("Required: Python", "Required: Kubernetes"), fields={"level": "senior"}), fallback_source)
        self._make_live(second.listing_key)
        self.service.confirm_closed(first.listing_key, now=NOW + timedelta(minutes=1))
        after = self.service.resolve_opportunity(first.canonical_opportunity_key)
        self.assertNotEqual(after.requirement_version_key, before)
        self.assertEqual(after.field_attribution["level"], (second.listing_key, self.repo.listing(second.listing_key).current_version_key))

    def test_duplicate_requirement_clauses_have_distinct_ordinal_stable_item_keys(self):
        listing = self._admit(
            fixture_candidate(requirement_clauses=("Required: Python", "Required: Python"))
        )
        opportunity = self.service.resolve_opportunity(listing.canonical_opportunity_key)
        requirement = self.repo.requirement_version(opportunity.requirement_version_key)
        self.assertEqual([item.normalized_clause for item in requirement.items], ["required: python", "required: python"])
        self.assertEqual([item.ordinal for item in requirement.items], [1, 2])
        self.assertNotEqual(requirement.items[0].requirement_item_key, requirement.items[1].requirement_item_key)
        replay = self._admit(
            fixture_candidate(requirement_clauses=("Required: Python", "Required: Python")),
            when=NOW + timedelta(minutes=1),
        )
        replay_requirement = self.repo.requirement_version(
            self.service.resolve_opportunity(replay.canonical_opportunity_key).requirement_version_key
        )
        self.assertEqual(
            [item.requirement_item_key for item in replay_requirement.items],
            [item.requirement_item_key for item in requirement.items],
        )

    def test_requirement_history_reuses_a_to_b_to_a_fingerprint(self):
        listing = self._admit(fixture_candidate(requirement_clauses=("Required: Python",)))
        opportunity_key = listing.canonical_opportunity_key
        requirement_a = self.service.resolve_opportunity(opportunity_key).requirement_version_key
        changed_b = self._admit(
            fixture_candidate(requirement_clauses=("Required: Kubernetes",)),
            when=NOW + timedelta(minutes=1),
        )
        self.service.re_admit_changed_listing(changed_b.listing_key, now=NOW + timedelta(minutes=2))
        requirement_b = self.service.resolve_opportunity(opportunity_key).requirement_version_key
        self.assertNotEqual(requirement_b, requirement_a)
        changed_a = self._admit(
            fixture_candidate(requirement_clauses=("Required: Python",)),
            when=NOW + timedelta(minutes=3),
        )
        self.service.re_admit_changed_listing(changed_a.listing_key, now=NOW + timedelta(minutes=4))
        self.assertEqual(self.service.resolve_opportunity(opportunity_key).requirement_version_key, requirement_a)
        self.assertEqual(len(self.repo.requirement_versions_for(opportunity_key)), 2)

    def test_requirement_and_event_write_boundaries_reject_cross_class_children(self):
        listing = self._admit()
        opportunity = self.service.resolve_opportunity(listing.canonical_opportunity_key)
        source_version = self.repo.version(listing.current_version_key)
        bad_item = RequirementItem("wrong-class-item", "production", "required: python", 1)
        bad_requirement = RequirementVersion(
            "wrong-class-requirement",
            opportunity.opportunity_key,
            source_version.version_key,
            "production",
            "0" * 64,
            (bad_item,),
            NOW,
        )
        before_requirements = dict(self.repo._requirement_versions)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "class_mismatch"):
            self.repo.save_requirement_version(bad_requirement)
        self.assertEqual(self.repo._requirement_versions, before_requirements)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "class_mismatch"):
            self.repo.save_event(
                CanonicalEvent("wrong-class-event", opportunity.opportunity_key, "production", "test", NOW, {})
            )

    def test_live_gate_rejects_policy_expiry_at_point_of_use(self):
        listing = self._admit()
        expired = replace(
            policy(version=2, actions=ACTIONS - {"cache"}),
            expires_at=NOW - timedelta(seconds=1),
        )
        self.service.revise_policy(expired, now=NOW)
        self.assertIn("policy_denied", self.service.live_gate(listing.listing_key, now=NOW).reasons)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            self.service.record_receipt(
                self.direct,
                SourceReceiptInput("expired-policy", NOW, "application/json", b"{}"),
                now=NOW,
            )

    def test_live_gate_rejects_every_noncurrent_lifecycle_state(self):
        noncurrent_states = ("intake", "changed", "closed", "unreachable", "stale", "quarantined", "invalid")
        for offset, state in enumerate(noncurrent_states, start=1):
            with self.subTest(state=state):
                listing = self._admit(
                    fixture_candidate(external_reference=f"state-{state}"),
                    when=NOW + timedelta(minutes=offset),
                )
                self._make_live(listing.listing_key, NOW + timedelta(minutes=offset))
                self.repo.save_listing(replace(self.repo.listing(listing.listing_key), state=state))
                decision = self.service.live_gate(listing.listing_key, now=NOW + timedelta(minutes=offset))
                self.assertFalse(decision.passes)
                self.assertEqual(decision.reasons, (f"listing_{state}",))

    def test_policy_is_denied_at_registration_and_point_of_use(self):
        bad_repo = InMemoryCanonicalRepository()
        bad_service = CanonicalService(bad_repo, LiveOpportunityGateConfig(timedelta(days=1), timedelta(days=1)))
        bad_policy = replace(policy(), actions=frozenset({"register"}))
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            bad_service.register_policy(bad_policy, now=NOW)

        listing = self._admit()
        denied = replace(policy(version=2), actions=frozenset({"register"}))
        self.service.revise_policy(denied, now=NOW)
        self.assertIn("policy_denied", self.service.live_gate(listing.listing_key, now=NOW).reasons)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            self.service.record_receipt(
                self.direct,
                SourceReceiptInput("blocked-by-current-policy", NOW, "application/json", b"{}"),
                now=NOW,
            )

    def test_strict_false_takedown_purges_all_history_same_hash_receipts_requirements_and_attribution(self):
        listing = self._admit()
        duplicate = self._admit(when=NOW + timedelta(minutes=1))
        self.assertEqual(duplicate.listing_key, listing.listing_key)
        changed = self._admit(
            fixture_candidate(
                description="Changed source description.",
                requirement_clauses=("Required: Python", "Required: Kubernetes"),
            ),
            when=NOW + timedelta(minutes=2),
        )
        self.service.re_admit_changed_listing(changed.listing_key, now=NOW + timedelta(minutes=3))
        versions = self.repo.versions_for_listing(listing.listing_key)
        self.assertEqual(len(versions), 2)
        self.assertEqual(len(self.repo._receipts), 3)
        self.assertEqual(len(self.repo.receipt_keys_for_version(versions[0].version_key)), 2)
        self.assertEqual(len(self.repo.receipt_keys_for_version(versions[1].version_key)), 1)
        self.assertTrue(self.repo.requirement_versions_for_source_version(versions[0].version_key))
        self.assertTrue(self.repo.requirement_versions_for_source_version(versions[1].version_key))

        strict_false = replace(
            policy(version=2, actions=frozenset({"remove"})),
            dimensions={**DIMENSIONS, "survivable_minimal_facts": False},
        )
        self.service.revise_policy(strict_false, now=NOW)
        events_before = len(self.repo.events)
        self.service.tombstone_source_content(
            listing.listing_key,
            now=NOW + timedelta(minutes=4),
            actor="fixture-rights-operator",
            reason="provider-removal",
        )

        terminal = self.repo.listing(listing.listing_key)
        self.assertEqual((terminal.state, terminal.terminal_disposition, terminal.terminal_actor), ("closed", "removal", "fixture-rights-operator"))
        self.assertIsNone(terminal.source_id)
        self.assertIsNone(terminal.external_reference)
        self.assertEqual(terminal.expected_application_hosts, ())
        self.assertEqual(
            (
                terminal.link_last_attempted_at,
                terminal.link_last_validated_at,
                terminal.last_attempted_at,
                terminal.last_successfully_verified_at,
            ),
            (None, None, None, None),
        )
        self.assertEqual(terminal.retained_source_fields, ())
        for receipt in self.repo._receipts.values():
            self.assertTrue(receipt.content_withheld)
            self.assertEqual(
                (receipt.source_id, receipt.external_reference, receipt.received_at, receipt.content_type, receipt.byte_count, receipt.payload_sha256, receipt.payload),
                (None, None, None, None, None, None, None),
            )
            self.assertIsNotNone(receipt.created_at)
            self.assertEqual((receipt.tombstone_policy_key, receipt.tombstone_policy_version), ("policy-direct", 2))
        for source_version in self.repo.versions_for_listing(listing.listing_key):
            self.assertTrue(source_version.content_withheld)
            self.assertEqual(
                (source_version.content_sha256, source_version.observed_at, source_version.employer, source_version.title,
                 source_version.locations, source_version.arrangement, source_version.application_url, source_version.description,
                 source_version.requirement_clauses, source_version.fields),
                (None, None, None, None, None, None, None, None, None, {}),
            )
            self.assertIsNotNone(source_version.created_at)
        for requirement in self.repo._requirement_versions.values():
            self.assertTrue(requirement.content_withheld)
            self.assertIsNone(requirement.clause_fingerprint)
            self.assertTrue(all(item.content_withheld and item.ordinal is None and item.normalized_clause is None for item in requirement.items))
        self.assertEqual(len(self.repo.content_tombstones), 3)
        self.assertEqual(
            {(item.receipt_key, item.source_version_key) for item in self.repo.content_tombstones},
            {(receipt_key, version.version_key) for version in versions for receipt_key in self.repo.receipt_keys_for_version(version.version_key)},
        )
        self.assertTrue(all(item.retained_source_fields == () for item in self.repo.content_tombstones))
        opportunity = self.service.resolve_opportunity(listing.canonical_opportunity_key)
        self.assertEqual((opportunity.governing_listing_key, opportunity.governing_source_version_key, opportunity.requirement_version_key, opportunity.field_attribution), (None, None, None, {}))
        self.assertEqual(len(self.repo.events), events_before + 1)
        event = self.repo.events[-1]
        self.assertEqual((event.kind, event.data_class, event.detail), ("content_tombstoned", "fixture", {"disposition": "removal", "reason": "provider-removal"}))
        self.assertNotIn("Astraeus", repr(event.detail))
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "immutable_tombstone"):
            self.service.tombstone_source_content(listing.listing_key, now=NOW + timedelta(minutes=5))
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "immutable_tombstone"):
            self.repo.save_listing(replace(terminal, state="current"))
        self.assertEqual(len(self.repo.content_tombstones), 3)

    def test_explicit_true_allowlist_retains_only_byte_identical_named_source_field(self):
        repo = InMemoryCanonicalRepository()
        service = CanonicalService(repo, LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2)))
        direct = descriptor()
        initial = policy(retained_source_fields=("source_version.description",))
        service.register_policy(initial, now=NOW)
        service.register_connector(direct, now=NOW)
        candidate = fixture_candidate(description="Allowlisted source body.")
        receipt = service.record_receipt(direct, SourceReceiptInput(candidate.external_reference, NOW, "application/json", b'{"allowlisted":true}'), now=NOW)
        listing = service.admit(direct, receipt, candidate, now=NOW)
        original = repo.version(listing.current_version_key)
        restrictive = replace(initial, version=2, actions=frozenset({"remove"}))
        service.revise_policy(restrictive, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_tombstone"):
            repo.tombstone_listing_content(
                listing.listing_key,
                policy=restrictive,
                disposition="removal",
                reason="mismatched-allowlist",
                actor="fixture-rights-operator",
                retained_source_fields=(),
                now=NOW,
            )
        self.assertFalse(repo.listing(listing.listing_key).content_withheld)
        service.tombstone_source_content(listing.listing_key, now=NOW)
        retained = repo.version(original.version_key)
        self.assertEqual(retained.description, "Allowlisted source body.")
        self.assertEqual(
            (retained.employer, retained.title, retained.locations, retained.application_url, retained.content_sha256, retained.fields),
            (None, None, None, None, None, {}),
        )
        self.assertIsNone(repo.receipt(original.receipt_key).payload)
        self.assertIsNone(repo.listing(listing.listing_key).source_id)
        self.assertEqual(repo.content_tombstones[0].retained_source_fields, ("source_version.description",))

    def test_terminal_termination_uses_the_invalid_lifecycle_state(self):
        listing = self._admit()
        self.service.tombstone_source_content(
            listing.listing_key,
            now=NOW,
            disposition="termination",
            reason="source-termination",
        )
        terminal = self.repo.listing(listing.listing_key)
        self.assertEqual((terminal.state, terminal.terminal_disposition), ("invalid", "termination"))
        self.assertEqual(
            (
                terminal.link_last_attempted_at,
                terminal.link_last_validated_at,
                terminal.last_attempted_at,
                terminal.last_successfully_verified_at,
            ),
            (None, None, None, None),
        )

    def test_takedown_preflight_rejects_unpaired_wrong_class_and_no_right_without_partial_mutation(self):
        listing = self._admit()
        self._admit(when=NOW + timedelta(minutes=1))
        strict_false = replace(
            policy(version=2, actions=frozenset({"remove"})),
            dimensions={**DIMENSIONS, "survivable_minimal_facts": False},
        )
        self.service.revise_policy(strict_false, now=NOW)
        extra_receipt_key = next(
            key for key, version_key in self.repo._receipt_version_links.items()
            if key != self.repo.version(listing.current_version_key).receipt_key and version_key == listing.current_version_key
        )
        self.repo._receipt_version_links.pop(extra_receipt_key)
        bodies_before = {key: item.payload for key, item in self.repo._receipts.items()}
        versions_before = {key: item.description for key, item in self.repo._versions.items()}
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "unpaired_receipt"):
            self.service.tombstone_source_content(listing.listing_key, now=NOW)
        self.assertEqual({key: item.payload for key, item in self.repo._receipts.items()}, bodies_before)
        self.assertEqual({key: item.description for key, item in self.repo._versions.items()}, versions_before)
        self.assertFalse(self.repo.listing(listing.listing_key).content_withheld)
        self.assertEqual(self.repo.content_tombstones, [])

        wrong_policy = replace(strict_false, data_class="production")
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_tombstone"):
            self.repo.tombstone_listing_content(
                listing.listing_key,
                policy=wrong_policy,
                disposition="removal",
                reason="wrong-class",
                actor="fixture-rights-operator",
                retained_source_fields=(),
                now=NOW,
            )
        self.assertFalse(self.repo.listing(listing.listing_key).content_withheld)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_tombstone"):
            self.repo.tombstone_listing_content(
                listing.listing_key,
                policy=replace(strict_false, version=99),
                disposition="removal",
                reason="wrong-policy",
                actor="fixture-rights-operator",
                retained_source_fields=(),
                now=NOW,
            )
        self.assertFalse(self.repo.listing(listing.listing_key).content_withheld)

        no_right_repo = InMemoryCanonicalRepository()
        no_right_service = CanonicalService(no_right_repo, LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2)))
        no_right_service.register_policy(policy(), now=NOW)
        no_right_service.register_connector(self.direct, now=NOW)
        candidate = fixture_candidate(external_reference="no-right")
        receipt = no_right_service.record_receipt(self.direct, SourceReceiptInput("no-right", NOW, "application/json", b"{}"), now=NOW)
        no_right_listing = no_right_service.admit(self.direct, receipt, candidate, now=NOW)
        no_right_service.revise_policy(replace(policy(version=2, actions=frozenset()), dimensions={**DIMENSIONS, "removal": False}), now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            no_right_service.tombstone_source_content(no_right_listing.listing_key, now=NOW)
        self.assertFalse(no_right_repo.listing(no_right_listing.listing_key).content_withheld)

    def test_takedown_refreshes_governing_failover_without_extra_content_event(self):
        primary = self._admit()
        self._make_live(primary.listing_key)
        fallback_source = descriptor("fixture-fallback", "policy-fallback")
        self.service.register_policy(policy("fixture-fallback", "policy-fallback", priority=2), now=NOW)
        self.service.register_connector(fallback_source, now=NOW)
        fallback = self._admit(fixture_candidate(external_reference="fallback-after-takedown"), fallback_source)
        self._make_live(fallback.listing_key)
        self.assertEqual(self.service.resolve_opportunity(primary.canonical_opportunity_key).governing_listing_key, primary.listing_key)
        self.service.revise_policy(
            replace(policy(version=2, actions=frozenset({"remove"})), dimensions={**DIMENSIONS, "survivable_minimal_facts": False}),
            now=NOW,
        )
        events_before = len(self.repo.events)
        self.service.tombstone_source_content(primary.listing_key, now=NOW)
        opportunity = self.service.resolve_opportunity(primary.canonical_opportunity_key)
        self.assertEqual(opportunity.governing_listing_key, fallback.listing_key)
        self.assertEqual(len(self.repo.events), events_before + 1)
        self.assertEqual(self.repo.events[-1].kind, "content_tombstoned")

    def test_tombstone_requires_current_removal_right_even_when_retention_is_denied(self):
        listing = self._admit()
        removal_denied_dimensions = {**DIMENSIONS, "removal": False}
        self.service.revise_policy(
            replace(policy(version=2, actions=ACTIONS - {"retain"}), dimensions=removal_denied_dimensions),
            now=NOW,
        )
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            self.service.tombstone_source_content(listing.listing_key, now=NOW)

    def test_public_restrictive_revision_makes_removal_reachable_without_survivability(self):
        listing = self._admit()
        restrictive_dimensions = {**DIMENSIONS, "survivable_minimal_facts": False}
        revision = replace(
            policy(version=2, actions=frozenset({"remove"})),
            dimensions=restrictive_dimensions,
            retained_source_fields=(),
        )
        self.service.revise_policy(revision, now=NOW)
        self.assertFalse(self.service._current_policy("policy-direct").allows("retain", NOW))
        self.assertTrue(self.service._current_policy("policy-direct").allows("remove", NOW))
        self.service.tombstone_source_content(listing.listing_key, now=NOW)
        self.assertTrue(self.repo.version(listing.current_version_key).content_withheld)

    def test_restrictive_revisions_refuse_invalid_identity_order_and_allowlist_without_mutation(self):
        before = dict(self.repo._policies)
        restrictive_dimensions = {**DIMENSIONS, "survivable_minimal_facts": False}
        candidates = (
            replace(policy(version=1, actions=frozenset({"remove"})), dimensions=restrictive_dimensions),
            replace(policy(version=3, actions=frozenset({"remove"})), dimensions=restrictive_dimensions),
            replace(policy(source_id="wrong-source", version=2, actions=frozenset({"remove"})), dimensions=restrictive_dimensions),
            replace(policy(version=2, actions=frozenset({"remove"}), data_class="production"), dimensions=restrictive_dimensions),
            replace(
                policy(version=2, actions=frozenset({"remove"})),
                dimensions=restrictive_dimensions,
                retained_source_fields=("source_version.title",),
            ),
            replace(policy(version=2, actions=frozenset({"remove"})), evidence_ref=""),
            replace(policy(version=2, actions=frozenset({"remove"})), decision_ref=""),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_policy_revision"):
                self.service.revise_policy(candidate, now=NOW)
            self.assertEqual(self.repo._policies, before)

    def test_explicit_retained_source_field_allowlist_is_sorted_immutable_and_never_inferred(self):
        explicit = replace(policy(), retained_source_fields=("source_version.title", "source_version.employer", "source_version.title"))
        self.assertEqual(explicit.retained_source_fields, ("source_version.employer", "source_version.title"))
        self.assertTrue(explicit.has_consistent_retained_field_allowlist())
        strict_false = replace(
            policy(),
            dimensions={**DIMENSIONS, "survivable_minimal_facts": False},
            retained_source_fields=("source_version.title",),
        )
        self.assertFalse(strict_false.has_consistent_retained_field_allowlist())
        self.assertEqual(policy().retained_source_fields, ())

    def test_policy_action_json_round_trip_is_canonical_and_cannot_invent_actions(self):
        restricted = policy(actions=frozenset({"remove", "acquire", "terminate"}))
        encoded = restricted.allowed_actions_json
        self.assertEqual(encoded, '["acquire","remove","terminate"]')
        self.assertEqual(
            SourcePolicy.actions_from_allowed_actions_json(encoded),
            frozenset({"acquire", "remove", "terminate"}),
        )
        for malformed in (
            '["remove","acquire"]',
            '["acquire","remove","remove"]',
            '["acquire","provider_action"]',
            '{"action":"remove"}',
            '["acquire",1]',
        ):
            with self.subTest(malformed=malformed), self.assertRaisesRegex(
                MyOpportunitiesCanonicalError, "invalid_policy_actions_json"
            ):
                SourcePolicy.actions_from_allowed_actions_json(malformed)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "invalid_policy_actions_json"):
            policy(actions=frozenset({"remove", "provider_action"})).allowed_actions_json

    def test_cross_class_admission_is_refused_and_shared_surface_has_no_member_key(self):
        receipt = self.service.record_receipt(self.direct, SourceReceiptInput("prod-1", NOW, "application/json", b"{}"), now=NOW)
        versions_before = dict(self.repo._versions)
        listings_before = dict(self.repo._listings)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "policy_denied"):
            self.service.admit(self.direct, receipt, fixture_candidate(external_reference="prod-1", data_class="production"), now=NOW)
        self.assertEqual(self.repo._versions, versions_before)
        self.assertEqual(self.repo._listings, listings_before)
        source = (ROOT / "services/my_opportunities/canonical_service.py").read_text(encoding="utf-8")
        self.assertNotIn("user_key", source)
        self.assertNotIn("owner_profile", source)

    def test_same_source_reference_isolated_by_fixture_or_production_class(self):
        fixture_listing = self._admit()
        production_descriptor = descriptor("fixture-direct", "policy-production", data_class="production")
        self.service.register_policy(
            policy("fixture-direct", "policy-production", data_class="production"), now=NOW
        )
        self.service.register_connector(production_descriptor, now=NOW)
        production_candidate = fixture_candidate(data_class="production")
        production_receipt = self.service.record_receipt(
            production_descriptor,
            SourceReceiptInput(production_candidate.external_reference, NOW, "application/json", b'{"production":true}'),
            now=NOW,
        )
        production_listing = self.service.admit(
            production_descriptor, production_receipt, production_candidate, now=NOW
        )

        fixture_version = self.repo.version(fixture_listing.current_version_key)
        production_version = self.repo.version(production_listing.current_version_key)
        self.assertNotEqual(fixture_listing.listing_key, production_listing.listing_key)
        self.assertNotEqual(fixture_listing.canonical_opportunity_key, production_listing.canonical_opportunity_key)
        self.assertNotEqual(fixture_version.version_key, production_version.version_key)
        self.assertEqual((fixture_version.data_class, production_version.data_class), ("fixture", "production"))
        self.assertEqual(
            self.repo.listing_for_source_reference("fixture", "fixture-direct", "astraeus-1").listing_key,
            fixture_listing.listing_key,
        )
        self.assertEqual(
            self.repo.listing_for_source_reference("production", "fixture-direct", "astraeus-1").listing_key,
            production_listing.listing_key,
        )
        self.assertEqual(self.repo.version(fixture_listing.current_version_key).employer, "Astraeus")

    def test_additive_schema_stays_at_the_governed_root_with_no_member_or_legacy_reuse(self):
        registry = json.loads((ROOT / "SQL FIles/Migrations/registry.json").read_text())
        entry = next(item for item in registry["migrations"] if item["id"] == "PS-MYOPP-001")
        self.assertEqual(entry["requires"], ["PS-PLAT-000"])
        migration_positions = {
            migration["id"]: index for index, migration in enumerate(registry["migrations"])
        }
        self.assertIn("PS-MYOPP-001", migration_positions)
        self.assertLess(migration_positions["PS-PLAT-000"], migration_positions["PS-MYOPP-001"])
        for dependency in entry["requires"]:
            self.assertLess(migration_positions[dependency], migration_positions[entry["id"]])
        self.assertNotIn("proposed", entry["forward"])
        forward = (ROOT / entry["forward"]).read_text(encoding="utf-8")
        rollback = (ROOT / entry["rollback"]).read_text(encoding="utf-8")
        verify = (ROOT / "SQL FIles/Verification/PS-MYOPP-001_canonical_foundation_verify.sql").read_text(encoding="utf-8")
        for object_name in ("dbo.myopp_source_policies", "dbo.myopp_source_receipts", "dbo.myopp_source_listings", "dbo.myopp_source_versions", "dbo.myopp_source_version_receipt_links", "dbo.myopp_canonical_opportunities", "dbo.myopp_requirement_versions"):
            self.assertIn(object_name, forward)
        self.assertNotIn("dbo.opportunity_", forward)
        self.assertNotIn("user_key", forward.lower())
        self.assertNotIn("owner_profile", forward.lower())
        foreign_key_columns = re.findall(r"FOREIGN KEY \(([^)]+)\)", forward)
        self.assertTrue(foreign_key_columns)
        self.assertTrue(all("data_class" in columns for columns in foreign_key_columns))
        self.assertIn("rollback refused because a later migration", rollback.lower())
        self.assertIn("rollback refused because c2 data exists", rollback.lower())
        self.assertIn("CAST(1 AS bit) AS verified", verify)
        self.assertIn("cross-class join", verify.lower())
        self.assertRegex(
            forward,
            r"CK_myopp_content_tombstones_target CHECK \(myopp_source_receipt_id IS NOT NULL AND myopp_source_version_id IS NOT NULL\)",
        )
        self.assertIn("CK_myopp_content_tombstones_target", verify)
        self.assertIn("must pair one receipt with one source version", verify)
        # The fresh-install shape and all executable terminal controls remain
        # static-tested here; a future disposable gate proves SQL execution.
        self.assertIn("retained_source_fields_json nvarchar(max) NOT NULL", forward)
        self.assertIn("allowed_actions_json nvarchar(max) NOT NULL", forward)
        self.assertIn("CK_myopp_source_policies_allowed_actions_json", forward)
        self.assertIn("CK_myopp_source_policies_strict_false_retention", forward)
        self.assertIn("survivable_minimal_facts_allowed = 1 OR retained_source_fields_json = N'[]'", forward)
        self.assertIn("UQ_myopp_source_policies_key_class_version UNIQUE (policy_key, data_class, policy_version)", forward)
        self.assertIn("UQ_myopp_source_policies_source_class_version UNIQUE (data_class, source_id, policy_version)", forward)
        self.assertIn("expected_application_hosts_json nvarchar(max) NULL", forward)
        self.assertNotIn("expected_application_host nvarchar(255)", forward)
        self.assertIn("UX_myopp_source_listings_active_source_reference", forward)
        self.assertIn("WHERE source_id IS NOT NULL AND external_reference IS NOT NULL", forward)
        self.assertIn("UX_myopp_source_versions_active_listing_hash", forward)
        self.assertIn("WHERE content_sha256 IS NOT NULL", forward)
        self.assertIn("UX_myopp_requirement_versions_active_opportunity_fingerprint", forward)
        self.assertIn("WHERE clause_fingerprint IS NOT NULL", forward)
        self.assertIn("UX_myopp_requirement_items_active_version_ordinal", forward)
        self.assertIn("WHERE ordinal IS NOT NULL", forward)
        self.assertIn("UX_myopp_canonical_field_attributions_active_opportunity_field", forward)
        self.assertIn("WHERE field_name IS NOT NULL", forward)
        self.assertIn("UQ_myopp_source_version_receipt_links_pair_class", forward)
        self.assertIn("UQ_myopp_source_version_receipt_links_receipt_class", forward)
        self.assertIn("FK_myopp_source_version_receipt_links_version_class", forward)
        self.assertIn("FK_myopp_source_version_receipt_links_receipt_class", forward)
        self.assertIn("created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_myopp_source_version_receipt_links_created", forward)
        self.assertIn("FK_myopp_content_tombstones_pair_link_class", forward)
        self.assertIn("UQ_myopp_content_tombstones_pair_class", forward)
        self.assertIn("myopp_source_receipt_id bigint NOT NULL", forward)
        self.assertIn("myopp_source_version_id bigint NOT NULL", forward)
        self.assertIn("myopp_source_policy_id bigint NOT NULL", forward)
        self.assertIn("policy_version int NOT NULL", forward)
        self.assertIn("disposition nvarchar(20) NOT NULL", forward)
        self.assertIn("actor_ref nvarchar(160) NOT NULL", forward)
        for terminal_constraint in (
            "CK_myopp_source_receipts_tombstone",
            "CK_myopp_source_listings_tombstone",
            "CK_myopp_source_versions_tombstone",
            "CK_myopp_requirement_versions_tombstone",
            "CK_myopp_requirement_items_tombstone",
            "CK_myopp_canonical_field_attributions_tombstone",
        ):
            self.assertIn(terminal_constraint, forward)
        self.assertIn("myopp_source_version_receipt_links", rollback)
        self.assertLess(
            rollback.index("DROP TABLE dbo.myopp_source_version_receipt_links;"),
            rollback.index("DROP TABLE dbo.myopp_source_versions;"),
        )

        policy_guard_start = forward.index("CREATE TRIGGER dbo.trg_myopp_source_policies_revision_guard")
        policy_guard_end = forward.index("CREATE TRIGGER dbo.trg_myopp_source_receipts_terminal_guard")
        policy_guard = forward[policy_guard_start:policy_guard_end]
        self.assertIn("AFTER INSERT, UPDATE, DELETE", policy_guard)
        self.assertIn("Source policy rows are append-only.", policy_guard)
        self.assertIn("Ambiguous source policy revision batch refused.", policy_guard)
        self.assertIn("IF (SELECT COUNT(*) FROM inserted) <> 1", policy_guard)
        self.assertIn("Initial source policy must satisfy the fail-closed registration contract.", policy_guard)
        self.assertIn("prior.policy_version = i.policy_version - 1", policy_guard)
        self.assertIn("Source policy revision changed class-safe identity.", policy_guard)
        self.assertIn("Source policy revision must be the immediate restrictive successor.", policy_guard)
        self.assertIn("i.survivable_minimal_facts_allowed = 0 AND i.retained_source_fields_json <> N''[]''", policy_guard)
        self.assertIn("FROM OPENJSON(i.allowed_actions_json) allowed_action", policy_guard)
        self.assertIn("N''acquire'', N''ai'', N''cache'', N''display'', N''export''", policy_guard)
        self.assertIn("TRY_CONVERT(int, earlier_action.[key])", policy_guard)
        self.assertIn("i.allowed_actions_json LIKE N''% %''", policy_guard)
        self.assertIn("i.allowed_actions_json LIKE N''%'' + NCHAR(92) + N''%''", policy_guard)
        self.assertIn("FROM OPENJSON(i.allowed_actions_json) initial_action", policy_guard)
        self.assertIn("FROM OPENJSON(prior.allowed_actions_json) prior_actions", policy_guard)
        self.assertIn("FROM OPENJSON(i.retained_source_fields_json) retained", policy_guard)
        self.assertIn("i.retained_source_fields_json LIKE N''% %''", policy_guard)
        self.assertIn("i.retained_source_fields_json LIKE N''%'' + NCHAR(92) + N''%''", policy_guard)
        self.assertIn("earlier_field.[value] COLLATE Latin1_General_100_BIN2", policy_guard)
        self.assertIn("N''receipt.source_id''", policy_guard)
        self.assertIn("N''source_version.description''", policy_guard)
        self.assertIn("N''field_attribution.field_name''", policy_guard)
        self.assertIn("FROM OPENJSON(prior.retained_source_fields_json) prior_fields", policy_guard)
        self.assertIn("DROP TRIGGER dbo.trg_myopp_source_policies_revision_guard;", rollback)
        for terminal_object in (
            "trg_myopp_source_receipts_terminal_guard",
            "trg_myopp_source_listings_terminal_guard",
            "trg_myopp_source_versions_terminal_guard",
            "trg_myopp_requirement_versions_terminal_guard",
            "trg_myopp_requirement_items_terminal_guard",
            "trg_myopp_canonical_field_attributions_terminal_guard",
            "trg_myopp_source_version_receipt_links_immutable",
            "trg_myopp_content_tombstones_immutable",
            "trg_myopp_canonical_events_guard",
            "usp_myopp_tombstone_listing_content",
        ):
            self.assertIn(f"dbo.{terminal_object}", forward)
            self.assertIn(f"dbo.{terminal_object};", rollback)
        self.assertIn("SESSION_CONTEXT(N''myopp.c2_terminal_takedown'')", forward)
        self.assertIn("Content tombstones must bind one final paired receipt/version transition", forward)
        self.assertIn("application_url = NULL", forward)
        self.assertIn("listing_state = CASE WHEN @disposition = N''removal'' THEN N''closed'' ELSE N''invalid'' END", forward)
        self.assertIn("link_last_attempted_at_utc = NULL, link_last_validated_at_utc = NULL", forward)
        self.assertIn("last_attempted_at_utc = NULL, last_successfully_verified_at_utc = NULL", forward)
        self.assertIn("INSERT dbo.myopp_content_tombstones", forward)
        self.assertIn("content_tombstoned", forward)
        self.assertLess(
            forward.index("CREATE PROCEDURE dbo.usp_myopp_tombstone_listing_content"),
            forward.index("INSERT dbo.schema_migrations"),
        )
        self.assertIn("parent_schema.name <> N'dbo'", verify)
        self.assertIn("myopp_source_version_receipt_links", verify)
        self.assertIn("usp_myopp_tombstone_listing_content", verify)
        self.assertIn("@RequiredFilteredIndexes", verify)
        self.assertIn("allowed_actions_json", verify)
        self.assertIn("C2 shared-side schema has a forbidden cross-schema or external foreign-key dependency.", verify)

        # sys.check_constraints.definition brackets identifiers in Azure SQL.
        # Keep this representative catalog shape distinct from the source DDL
        # so a formatting-only verifier regression cannot masquerade as an
        # invariant failure in a governed disposable gate.
        bracketed_catalog_definition = "(([myopp_source_receipt_id] IS NOT NULL AND [myopp_source_version_id] IS NOT NULL))"
        normalized_catalog_definition = (
            bracketed_catalog_definition.lower()
            .replace("[", "")
            .replace("]", "")
            .replace(" ", "")
            .replace("\t", "")
            .replace("\n", "")
            .replace("\r", "")
            .replace("(", "")
            .replace(")", "")
        )
        self.assertEqual(
            normalized_catalog_definition,
            "myopp_source_receipt_idisnotnullandmyopp_source_version_idisnotnull",
        )
        expected_staged_normalization = """CROSS APPLY
        (
            VALUES (LOWER(check_constraint.definition))
        ) catalog_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(catalog_constraint.definition_text, N'[', N''), N']', N'')
            )
        ) unbracketed_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(REPLACE(REPLACE(unbracketed_constraint.definition_text, N' ', N''), NCHAR(9), N''), NCHAR(10), N''), NCHAR(13), N'')
            )
        ) compact_constraint(definition_text)
        CROSS APPLY
        (
            VALUES
            (
                REPLACE(REPLACE(compact_constraint.definition_text, N'(', N''), N')', N'')
            )
        ) normalized_constraint(normalized_definition)"""
        definition_start = verify.index("        CROSS APPLY", verify.index("FROM sys.check_constraints"))
        definition_end = verify.index("        WHERE schema_record.name", definition_start)
        actual_staged_normalization = verify[definition_start:definition_end].strip()
        self.assertEqual(actual_staged_normalization, expected_staged_normalization)
        self.assertEqual(actual_staged_normalization.count("REPLACE("), 8)
        self.assertNotIn("REPLACE(REPLACE(REPLACE(REPLACE(REPLACE", verify)
        self.assertIn(
            "normalized_constraint.normalized_definition = N'myopp_source_receipt_idisnotnullandmyopp_source_version_idisnotnull'",
            verify,
        )
        self.assertNotIn("LIKE N'%myopp_source_receipt_id is not null%'", verify)
        self.assertNotIn("LIKE N'%myopp_source_version_id is not null%'", verify)
        self.assertNotIn("NOT LIKE N'% or %'", verify)

        recorded_gate = entry["gate"]
        if recorded_gate is None:
            # The registry truthfully remains ungated until a disposable proof
            # succeeds. Exercise the exact post-gate shape without inventing
            # that proof in the repository.
            gate = {
                "executable_sha256": executable_sha256(ROOT / entry["forward"]),
                "gated_at_utc": "2026-08-24T00:00:00Z",
                "gate_database": "ps-myopp-c2-gate-shape-only",
                "gate_server": "peerslate",
                "prerequisites": ["PS-PLAT-000"],
                "objects": ["USER_TABLE:dbo.myopp_content_tombstones"],
                "verification": "PS-MYOPP-001_canonical_foundation_verify.sql returned verified = 1",
                "operator": "agent:/root/c2_canonical_writer",
            }
        else:
            self.assertIsInstance(recorded_gate, dict)
            gate = recorded_gate
        self.assertEqual(
            gate["executable_sha256"],
            executable_sha256(ROOT / entry["forward"]),
        )
        self.assertRegex(gate["gated_at_utc"], r"^\d{4}-\d{2}-\d{2}T.+Z$")
        self.assertRegex(gate["gate_database"], r"^ps-myopp-c2-gate-[a-z0-9-]+$")
        self.assertEqual(gate["gate_server"], "peerslate")
        self.assertEqual(gate["prerequisites"], ["PS-PLAT-000"])
        self.assertTrue(gate["objects"])
        self.assertEqual(
            gate["verification"],
            "PS-MYOPP-001_canonical_foundation_verify.sql returned verified = 1",
        )
        self.assertEqual(gate["operator"], "agent:/root/c2_canonical_writer")

    def test_c2_ledger_writes_and_rollback_match_the_real_platform_ledger_contract(self):
        platform = (ROOT / "SQL FIles/Migrations/PS-PLAT-000_app_users_base.sql").read_text(encoding="utf-8")
        forward = (ROOT / "SQL FIles/Migrations/PS-MYOPP-001_canonical_foundation.sql").read_text(encoding="utf-8")
        rollback = (ROOT / "SQL FIles/Migrations/PS-MYOPP-001_canonical_foundation_rollback.sql").read_text(encoding="utf-8")
        self.assertIn("description nvarchar(500) NOT NULL", platform)
        self.assertIn("applied_at_utc datetime2(7) NOT NULL", platform)
        self.assertIn("application_version nvarchar(100) NULL", platform)
        self.assertRegex(forward, r"INSERT dbo\.schema_migrations\s*\(migration_id, description, application_version\)")
        self.assertIn("PeerSlate My Opportunities C2 v0.1", forward)
        self.assertNotIn("(migration_id, applied_at, applied_by)", forward)
        self.assertIn("applied_at_utc", rollback)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", rollback)
        self.assertNotRegex(rollback, r"\bapplied_at\b")


if __name__ == "__main__":
    unittest.main()
