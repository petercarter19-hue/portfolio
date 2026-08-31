from __future__ import annotations

import inspect
import json
import random
import re
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.migration_registry import executable_sha256

from services.my_opportunities.canonical_service import (
    CanonicalService,
    InMemoryCanonicalRepository,
    LiveOpportunityGateConfig,
    MyOpportunitiesCanonicalError,
    SourcePolicy,
)
from services.my_opportunities.connectors import ConnectorDescriptor, NormalizedListing, SourceReceiptInput
from services.my_opportunities.criteria_service import CriteriaService, InMemoryCriteriaRepository
from services.my_opportunities.evidence_port import EVIDENCE_CLASS_WORKSHOP, EvidenceRecord, InMemoryEvidencePort
from services.my_opportunities.index_fence import FENCE_DROP_REASONS, FenceDecision, fence_candidate
from services.my_opportunities.index_projection import (
    FORBIDDEN_PROJECTION_TOKENS,
    IndexCandidate,
    IndexUnavailable,
    InMemoryDiscoveryIndex,
    PROJECTION_FIELDS,
    ProjectionContractError,
    ProjectionDocument,
    build_projection_document,
    rebuild_index,
)
from services.my_opportunities.qualification_service import (
    AssessmentPersistenceError,
    AssessmentProposalSet,
    AssessmentProposalUnavailable,
    AssessmentRunResult,
    EvidenceClaim,
    FailingQualificationRepository,
    GATE_FULLY_VERIFIED,
    GATE_NOT_FULLY_VERIFIED,
    GateResult,
    GrantScope,
    InMemoryAuditSink as QualInMemoryAuditSink,
    InMemoryQualificationRepository,
    QualificationService,
)
from services.my_opportunities.retrieval_service import (
    CANCEL_REASONS,
    COMPLETENESS,
    DEFAULT_STALENESS_HORIZON,
    ENTRY_DROP_REASONS,
    EXECUTION_STATES,
    FAILED_REASONS,
    FORBIDDEN_LOADING_PHRASES,
    FORBIDDEN_SERIALIZATION_TOKENS,
    InMemoryAuditSink,
    InMemoryRetrievalRepository,
    FailingRetrievalRepository,
    LOADING_COPY,
    PARTIAL_ASSESSMENT_PERSISTENCE,
    PARTIAL_BUDGET_EXHAUSTED,
    PARTIAL_REASON_PRECEDENCE,
    PARTIAL_REASONS,
    PARTITION_BROADER,
    PARTITION_QUALIFIED,
    PARTITIONS,
    PUBLIC_ENTRY_FIELDS,
    RepositoryWriteError,
    RETRIEVAL_PATHS,
    RetrievalLimits,
    RetrievalService,
    RetrievalServiceError,
    SearchExecution,
    SNAPSHOT_COVERAGE,
    STATUS_COVERAGE,
    STATE_ASSESSING,
    STATE_CANCELLED,
    STATE_COMPLETE,
    STATE_FAILED,
    STATE_ORDERING,
    STATE_PARTIAL,
    STATE_RETRIEVING,
    STATE_SUBMITTED,
    TERMINAL_STATES,
)
from services.my_opportunities.safe_outbound import OutboundResponse, SafeOutboundClient
from services.my_opportunities.search_worker import (
    EntryEvaluation,
    SearchWorker,
    broader_sort_key,
    matches_criteria,
    qualified_sort_key,
    spec_from_requirement_version,
)


ROOT = Path(__file__).resolve().parents[1]

NOW = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
GATE_CONFIG = LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2))
DIMENSIONS = {
    "display": True, "excerpt": True, "full_description": True, "storage": True,
    "ai_ml_use": True, "caching": True, "retention": True, "attribution": True,
    "removal": True, "termination": True, "exit": True, "survivable_minimal_facts": True,
}
ACTIONS = frozenset(
    {"register", "acquire", "persist", "display", "retain", "remove", "terminate", "export", "ai", "cache"}
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def descriptor(source_id="fixture-direct", policy_key="policy-direct", policy_version=1, data_class="fixture"):
    return ConnectorDescriptor(
        source_id, "direct_employer", policy_key, policy_version,
        frozenset({"pull", "change_signal", "closure_signal"}), ("fixture-only",), "US", "synthetic", data_class,
    )


def policy(source_id="fixture-direct", policy_key="policy-direct", version=1, priority=1, data_class="fixture"):
    return SourcePolicy(
        policy_key, version, source_id, data_class, frozenset(ACTIONS), priority,
        NOW - timedelta(days=60), None, DIMENSIONS, "fixture-evidence", "fixture-decision",
    )


def fixture_candidate(**overrides):
    value = {
        "external_reference": "astraeus-1", "employer": "Astraeus", "title": "Platform Engineer",
        "locations": ("Chicago, IL",), "arrangement": "hybrid",
        "application_url": "https://jobs.example/roles/astraeus-1", "expected_application_hosts": ("jobs.example",),
        "description": "Build platforms with Python and Kubernetes.",
        "requirement_clauses": ("Required: 5 years Python", "Required: Kubernetes experience"),
        "fields": {"posted_at": "2026-08-01", "compensation_minimum": "150000"},
        "data_class": "fixture",
    }
    value.update(overrides)
    return NormalizedListing(**value)


def other_candidate(**overrides):
    value = {
        "external_reference": "borealis-1", "employer": "Borealis", "title": "Backend Developer",
        "locations": ("Remote",), "arrangement": "remote",
        "application_url": "https://jobs.example/roles/borealis-1", "expected_application_hosts": ("jobs.example",),
        "description": "Build services with Ruby on Rails.",
        "requirement_clauses": ("Required: Ruby on Rails",),
        "fields": {"posted_at": "2026-07-01", "compensation_minimum": "120000"},
        "data_class": "fixture",
    }
    value.update(overrides)
    return NormalizedListing(**value)


def _firm_record(key, *, body="Five years building distributed systems in Python and Kubernetes.", version=1):
    return EvidenceRecord(
        evidence_key=key, evidence_class=EVIDENCE_CLASS_WORKSHOP, version=version,
        title="Experience note", body=body, updated_at=NOW, strength="firm", time_span=None,
    )


class FixtureAssessmentProvider:
    """Deterministic canned claims, keyed by requirement item key (C5 test
    idiom, reused per the blueprint's instruction). ``claims_by_item`` is a
    plain public dict so a test can wire it after discovering item keys
    from a freshly admitted canonical fixture."""

    def __init__(self, claims_by_item=None, *, fail_with=None, hook=None):
        self.claims_by_item = dict(claims_by_item or {})
        self.fail_with = fail_with
        self.hook = hook
        self.calls = []

    def propose(self, prompt):
        self.calls.append(prompt)
        if self.hook is not None:
            self.hook(prompt)
        if self.fail_with == "unavailable":
            raise AssessmentProposalUnavailable("fixture_down")
        if self.fail_with == "timeout":
            from services.my_opportunities.qualification_service import AssessmentProposalTimeout

            raise AssessmentProposalTimeout("fixture_slow")
        if self.fail_with == "error":
            raise RuntimeError("fixture_boom")
        item_keys = {item_key for item_key, _clause in prompt.requirement_items}
        admitted_triples = {
            (record.evidence_key, record.evidence_class, record.version) for record in prompt.evidence_records
        }
        claims = []
        for item_key in item_keys:
            for claim in self.claims_by_item.get(item_key, ()):
                triple = (claim.evidence_key, claim.evidence_class, claim.evidence_version)
                if triple in admitted_triples:
                    claims.append(claim)
        return AssessmentProposalSet(claims=tuple(claims))


class Harness:
    """Full C2+C3+C5+C4 stack over in-memory fakes, following the
    blueprint's shared-fixture description (§10): real C2/C3/C5 services,
    plus InMemoryRetrievalRepository / InMemoryDiscoveryIndex / a
    ``_run_search`` style helper."""

    def __init__(self, *, index=None, retrieval_limits=None, members=("alice", "bob")):
        self.canonical_repo = InMemoryCanonicalRepository()
        self.canonical_service = CanonicalService(self.canonical_repo, GATE_CONFIG)
        self.direct = descriptor()
        self.canonical_service.register_policy(policy(), now=NOW)
        self.canonical_service.register_connector(self.direct, now=NOW)

        self.criteria_repo = InMemoryCriteriaRepository()
        self.criteria_service = CriteriaService(self.criteria_repo)

        self.qual_repo = InMemoryQualificationRepository()
        self.evidence_records = {member: [_firm_record(f"{member}-ev-1")] for member in members}
        self.evidence_port = InMemoryEvidencePort(self.evidence_records)
        self.provider = FixtureAssessmentProvider()
        self.qual_audit = QualInMemoryAuditSink()
        self.qual_service = QualificationService(
            self.qual_repo,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: self.evidence_port},
            provider=self.provider,
            audit_sink=self.qual_audit,
        )

        self.limits = retrieval_limits or RetrievalLimits()
        self.retrieval_repo = InMemoryRetrievalRepository()
        self.retrieval_audit = InMemoryAuditSink()
        self.retrieval_service = RetrievalService(
            self.retrieval_repo, criteria_reader=self.criteria_repo, limits=self.limits,
            audit_sink=self.retrieval_audit, display_resolver=self.canonical_repo,
        )
        self.worker_audit = InMemoryAuditSink()
        self.index = index
        self.worker = SearchWorker(
            retrieval_repository=self.retrieval_repo, criteria_reader=self.criteria_repo,
            canonical_service=self.canonical_service, canonical_repository=self.canonical_repo,
            qualification_service=self.qual_service, index=self.index, limits=self.limits,
            audit_sink=self.worker_audit,
        )
        self._n = 0

    def _next(self, label):
        self._n += 1
        return f"{label}-{self._n}"

    def admit(self, candidate=None, *, when=NOW):
        candidate = candidate or fixture_candidate()
        receipt = self.canonical_service.record_receipt(
            self.direct, SourceReceiptInput(candidate.external_reference, when, "application/json", b'{"fixture":true}'), now=when
        )
        listing = self.canonical_service.admit(self.direct, receipt, candidate, now=when)
        client = SafeOutboundClient(
            resolver=lambda *_: ["93.184.216.34"],
            transport=lambda _request: OutboundResponse(200, {"Content-Type": "text/html"}, b"ok"),
        )
        self.canonical_service.validate_application_link(listing.listing_key, client, now=when)
        listing = self.canonical_repo.listing(listing.listing_key)
        opportunity = self.canonical_service.resolve_opportunity(listing.canonical_opportunity_key)
        requirement_version = self.canonical_repo.requirement_version(opportunity.requirement_version_key)
        return opportunity, listing, requirement_version

    def grant(self, user_key, *, expires_at=None):
        return self.qual_service.create_grant(
            user_key, scope=GrantScope(frozenset({EVIDENCE_CLASS_WORKSHOP})),
            expires_at=expires_at or (NOW + timedelta(days=30)), idempotency_key=self._next("grant"), now=NOW,
        )

    def verify_all_items(self, user_key, requirement_version, *, evidence_key=None):
        evidence_key = evidence_key or f"{user_key}-ev-1"
        for item in requirement_version.items:
            self.provider.claims_by_item[item.requirement_item_key] = (
                EvidenceClaim(item.requirement_item_key, evidence_key, EVIDENCE_CLASS_WORKSHOP, 1, "supports"),
            )

    def apply_criteria(self, user_key, operations, *, verification_scope=None):
        draft = self.criteria_service.create_draft(user_key, idempotency_key=self._next("draft"), now=NOW)
        ops = list(operations)
        if verification_scope:
            ops.append({"op": "set_verification_scope", "verification_scope": verification_scope})
        if ops:
            draft = self.criteria_service.edit_draft(
                user_key, draft_key=draft.draft_key, draft_version_token=draft.draft_version_token,
                operations=ops, idempotency_key=self._next("edit"), now=NOW,
            )
        return self.criteria_service.apply(
            user_key, draft_key=draft.draft_key, draft_version_token=draft.draft_version_token,
            idempotency_key=self._next("apply"), now=NOW,
        )

    def register(self, user_key, receipt, *, data_class="fixture", now=NOW):
        return self.retrieval_service.register_execution(
            user_key, snapshot_key=receipt.snapshot_key, execution_key=receipt.execution_key,
            data_class=data_class, now=now,
        )

    def search(self, user_key, operations, *, verification_scope=None, data_class="fixture", now=NOW, deadline=None, clock=None):
        receipt = self.apply_criteria(user_key, operations, verification_scope=verification_scope)
        execution = self.register(user_key, receipt, data_class=data_class, now=now)
        final = self.worker.run(execution.execution_key, now=now, deadline=deadline, clock=clock)
        return final, receipt


def term_op(value, *, kind="free_text_term"):
    return {"op": "set_criterion", "kind": kind, "display_label": value, "value": value}


class RetrievalTestCase(unittest.TestCase):
    def setUp(self):
        self.harness = Harness()


# ---------------------------------------------------------------------------
# A. Registration, ceilings, cancellation
# ---------------------------------------------------------------------------


class RegistrationTests(RetrievalTestCase):
    def test_register_requires_owned_snapshot_and_not_found_shape_matches_absent(self):
        with self.assertRaises(RetrievalServiceError) as unknown_ctx:
            self.harness.retrieval_service.register_execution(
                "alice", snapshot_key="bogus-snapshot", execution_key="exec-1", data_class="fixture", now=NOW
            )
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        with self.assertRaises(RetrievalServiceError) as cross_owner_ctx:
            self.harness.retrieval_service.register_execution(
                "bob", snapshot_key=receipt.snapshot_key, execution_key="exec-2", data_class="fixture", now=NOW
            )
        self.assertEqual(unknown_ctx.exception.failure_code, "not_found")
        self.assertEqual(cross_owner_ctx.exception.failure_code, "not_found")
        self.assertEqual(unknown_ctx.exception.member_message, cross_owner_ctx.exception.member_message)

    def test_register_is_idempotent_for_same_execution_key_and_binding(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        first = self.harness.register("alice", receipt)
        second = self.harness.register("alice", receipt)
        self.assertEqual(first, second)
        self.assertEqual(self.harness.retrieval_repo.executions_registered_on("alice", NOW.date()), 1)

    def test_register_same_key_different_binding_refuses_conflict_nothing_mutated(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        self.harness.register("alice", receipt)
        digest_before = self.harness.retrieval_repo.state_digest()
        other_receipt = self.harness.apply_criteria("alice", [term_op("ruby")])
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.retrieval_service.register_execution(
                "alice", snapshot_key=other_receipt.snapshot_key, execution_key=receipt.execution_key,
                data_class="fixture", now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "execution_key_conflict")
        self.assertEqual(self.harness.retrieval_repo.state_digest(), digest_before)

    def test_register_supersedes_previous_active_execution_cancel_and_replace(self):
        receipt1 = self.harness.apply_criteria("alice", [term_op("python")])
        first = self.harness.register("alice", receipt1)
        receipt2 = self.harness.apply_criteria("alice", [term_op("ruby")])
        self.harness.register("alice", receipt2)
        superseded = self.harness.retrieval_repo.execution_for_owner("alice", first.execution_key)
        self.assertEqual(superseded.state, "cancelled")
        self.assertEqual(superseded.cancel_reason, "superseded")
        events = [event for event in self.harness.retrieval_audit.events if event.event_kind == "execution_superseded"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].keys, (first.execution_key,))

    def test_daily_execution_budget_refuses_truthfully_with_retry_after(self):
        self.harness = Harness(retrieval_limits=RetrievalLimits(daily_execution_budget=1))
        receipt1 = self.harness.apply_criteria("alice", [term_op("python")])
        self.harness.register("alice", receipt1)
        receipt2 = self.harness.apply_criteria("alice", [term_op("ruby")])
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.register("alice", receipt2)
        self.assertEqual(ctx.exception.failure_code, "daily_budget_exhausted")
        self.assertTrue(ctx.exception.recoverable)
        self.assertIsInstance(ctx.exception.retry_after, int)
        self.assertGreater(ctx.exception.retry_after, 0)

    def test_cancel_is_idempotent_and_terminal_cancel_returns_state_unchanged(self):
        opportunity, listing, requirement_version = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", requirement_version)
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertIn(final.state, ("complete", "partial"))
        cancelled_once = self.harness.retrieval_service.cancel("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(cancelled_once, final)  # already terminal -> unchanged, no error
        cancelled_twice = self.harness.retrieval_service.cancel("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(cancelled_twice, final)

    def test_cancel_mid_run_writes_no_snapshot(self):
        opportunity1, listing1, rv1 = self.harness.admit()
        opportunity2, listing2, rv2 = self.harness.admit(other_candidate())
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv1)
        self.harness.verify_all_items("alice", rv2)
        receipt = self.harness.apply_criteria("alice", [])  # empty criteria matches everything in scope
        execution = self.harness.register("alice", receipt)

        class CancelAfterHook(InMemoryRetrievalRepository):
            pass

        # A repository subclass whose `execution()` read cancels the run
        # after the first per-entry checkpoint -- deterministically
        # simulating a member cancel arriving mid-run (doc 03 §4).
        repo = self.harness.retrieval_repo
        original_execution_read = repo.execution
        calls = {"n": 0}

        def hooked_execution_read(execution_key):
            calls["n"] += 1
            if calls["n"] == 3:
                self.harness.retrieval_service.cancel("alice", execution_key=execution_key, now=NOW)
            return original_execution_read(execution_key)

        repo.execution = hooked_execution_read
        final = self.harness.worker.run(execution.execution_key, now=NOW)
        self.assertEqual(final.state, "cancelled")
        self.assertIsNone(repo.snapshot_for_execution("alice", execution.execution_key))

    def test_cancel_racing_the_persist_write_returns_cancelled_record_with_no_snapshot(self):
        """Independent-review FINDING 4: the existing
        test_cancel_mid_run_writes_no_snapshot only injects a cancel at the
        guarded per-entry checkpoint. This one lands the cancel from
        *inside* persist_snapshot itself -- the narrowest possible window,
        between the worker's pre-persist re-read and the actual write.

        Against the pre-fix code shape (before independent-review FINDING 1)
        this fails two different ways: (1) InMemoryRetrievalRepository.
        persist_snapshot had no state guard at all, so a snapshot for a
        now-cancelled execution would be silently persisted; (2) even with
        only the repository-side guard added, the pre-fix except-block
        called `self._terminal_failed(execution, ...)`, which wrote
        `failed(snapshot_persistence_failure)` directly from the caller's
        stale local `execution` object with no re-read -- `save_execution`'s
        own transition guard would then raise `RepositoryWriteError`
        because the *stored* row was already cancelled (terminal), and
        that exception would escape `run()` uncaught rather than the
        cancelled record being returned.
        """
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)

        class CancelDuringPersistRepository(InMemoryRetrievalRepository):
            def persist_snapshot(self, snapshot):
                current = self._executions[snapshot.execution_key]
                # A real concurrent RetrievalService.cancel() call would do
                # exactly this write; going through save_execution (not a
                # raw dict mutation) also proves ordering->cancelled is
                # itself a legal transition at this point in the run.
                self.save_execution(
                    replace(
                        current, state=STATE_CANCELLED, cancel_reason="member_cancelled",
                        terminal_at=current.submitted_at,
                    )
                )
                super().persist_snapshot(snapshot)

        hostile_repo = CancelDuringPersistRepository()
        hostile_repo.save_execution(execution)
        self.harness.worker._repository = hostile_repo
        self.harness.retrieval_service.repository = hostile_repo

        final = self.harness.worker.run(execution.execution_key, now=NOW)

        self.assertEqual(final.state, "cancelled")
        self.assertIsNone(hostile_repo.snapshot_for_execution("alice", execution.execution_key))
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.retrieval_service.results("alice", execution_key=execution.execution_key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_cancel_racing_the_retrieve_read_before_terminal_failed_write_returns_cancelled_record(self):
        """Independent-review FINDING 4 (second half): lands the cancel
        from *inside* the canonical read `_retrieve` depends on, so that by
        the time `_retrieve` returns `("failed", ...)` and `run()` reaches
        the "wide `_terminal_failed` after `_retrieve`" write (independent-
        review FINDING 2), the stored execution is already cancelled.

        Against the pre-fix `_terminal_failed` (no re-read, wrote directly
        on the stale local `execution`), `save_execution`'s own transition
        guard would raise `RepositoryWriteError` on that write -- the
        stored row is already terminal -- and that exception would escape
        `run()` rather than the cancelled record being returned.
        """
        opportunity, listing, rv = self.harness.admit()
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)
        execution_key = execution.execution_key

        real_canonical_repo = self.harness.canonical_repo
        retrieval_repo = self.harness.retrieval_repo

        class CancelDuringRetrieveCanonicalRepo:
            def __getattr__(self, name):
                return getattr(real_canonical_repo, name)

            def opportunities(self, data_class):
                current = retrieval_repo.execution(execution_key)
                retrieval_repo.save_execution(
                    replace(
                        current, state=STATE_CANCELLED, cancel_reason="member_cancelled",
                        terminal_at=current.submitted_at,
                    )
                )
                raise RuntimeError("canonical store outage racing the cancel")

        self.harness.worker._canonical_repository = CancelDuringRetrieveCanonicalRepo()
        final = self.harness.worker.run(execution_key, now=NOW)

        self.assertEqual(final.state, "cancelled")
        self.assertIsNone(self.harness.retrieval_repo.snapshot_for_execution("alice", execution_key))
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.retrieval_service.results("alice", execution_key=execution_key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_execution_state_machine_rejects_illegal_transitions(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)
        illegal = replace(execution, state=STATE_COMPLETE, terminal_at=NOW)
        with self.assertRaises(RepositoryWriteError):
            self.harness.retrieval_repo.save_execution(illegal)
        terminal = replace(execution, state=STATE_CANCELLED, cancel_reason="member_cancelled", terminal_at=NOW)
        self.harness.retrieval_repo.save_execution(terminal)
        resurrection = replace(
            execution, state=STATE_RETRIEVING, stage_started_at={**execution.stage_started_at, STATE_RETRIEVING: NOW}
        )
        with self.assertRaises(RepositoryWriteError):
            self.harness.retrieval_repo.save_execution(resurrection)

    def test_unsupported_criterion_kind_refuses_at_registration(self):
        receipt = self.harness.apply_criteria(
            "alice", [{"op": "set_criterion", "kind": "seniority_level", "display_label": "Seniority", "value": "senior"}]
        )
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.register("alice", receipt)
        self.assertEqual(ctx.exception.failure_code, "criterion_unsupported")

    def test_unsupported_direct_filter_key_refuses_at_registration(self):
        receipt = self.harness.apply_criteria(
            "alice", [{"op": "set_direct_filter", "filter_key": "visa-sponsorship", "value": "required"}]
        )
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.register("alice", receipt)
        self.assertEqual(ctx.exception.failure_code, "criterion_unsupported")

    def test_supported_only_snapshot_registers(self):
        receipt = self.harness.apply_criteria(
            "alice",
            [
                term_op("python"),
                {"op": "set_criterion", "kind": "arrangement", "display_label": "Arrangement", "value": "hybrid"},
                {"op": "set_direct_filter", "filter_key": "location", "value": "chicago"},
            ],
        )
        execution = self.harness.register("alice", receipt)
        self.assertEqual(execution.state, "submitted")

    def test_unsupported_kind_refusal_is_identical_regardless_of_kind(self):
        receipt_one = self.harness.apply_criteria(
            "alice", [{"op": "set_criterion", "kind": "seniority_level", "display_label": "S", "value": "senior"}]
        )
        receipt_two = self.harness.apply_criteria(
            "alice", [{"op": "set_criterion", "kind": "years_experience", "display_label": "Y", "value": "5"}]
        )
        with self.assertRaises(RetrievalServiceError) as first:
            self.harness.register("alice", receipt_one)
        with self.assertRaises(RetrievalServiceError) as second:
            self.harness.register("alice", receipt_two)
        self.assertEqual(first.exception.failure_code, second.exception.failure_code)
        self.assertEqual(first.exception.member_message, second.exception.member_message)

    def test_user_key_too_long_is_reachable(self):
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.retrieval_service.register_execution(
                "x" * 400, snapshot_key="snap", execution_key="exec", data_class="fixture", now=NOW
            )
        self.assertEqual(ctx.exception.failure_code, "user_key_too_long")

    def test_missing_display_resolver_raises_display_resolver_unavailable(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        bare_service = RetrievalService(
            self.harness.retrieval_repo, criteria_reader=self.harness.criteria_repo, limits=self.harness.limits,
        )
        with self.assertRaises(RetrievalServiceError) as ctx:
            bare_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "display_resolver_unavailable")
        self.assertNotEqual(ctx.exception.member_message, "That item is not available.")

    def test_register_execution_conflict_oracle_is_indistinguishable_and_same_input_replays(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        original = self.harness.register("alice", receipt)

        # Own key, different binding (a different snapshot for the same owner).
        other_receipt = self.harness.apply_criteria("alice", [term_op("ruby")])
        with self.assertRaises(RetrievalServiceError) as own_key_diff_binding:
            self.harness.retrieval_service.register_execution(
                "alice", snapshot_key=other_receipt.snapshot_key, execution_key=receipt.execution_key,
                data_class="fixture", now=NOW,
            )

        # A DIFFERENT owner presenting the SAME execution_key (held by alice).
        bob_receipt = self.harness.apply_criteria("bob", [term_op("python")])
        with self.assertRaises(RetrievalServiceError) as cross_owner:
            self.harness.retrieval_service.register_execution(
                "bob", snapshot_key=bob_receipt.snapshot_key, execution_key=receipt.execution_key,
                data_class="fixture", now=NOW,
            )

        self.assertEqual(own_key_diff_binding.exception.failure_code, cross_owner.exception.failure_code)
        self.assertEqual(own_key_diff_binding.exception.member_message, cross_owner.exception.member_message)
        self.assertEqual(own_key_diff_binding.exception.failure_code, "execution_key_conflict")

        # Own key, SAME binding -> idempotent replay, not an error.
        replayed = self.harness.register("alice", receipt)
        self.assertEqual(replayed, original)


# ---------------------------------------------------------------------------
# B. Worker binding and authority (doc 08 §2a)
# ---------------------------------------------------------------------------


class WorkerBindingTests(RetrievalTestCase):
    def test_worker_derives_owner_solely_from_execution_record(self):
        params = inspect.signature(SearchWorker.run).parameters
        self.assertNotIn("user_key", params)
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.user_key, "alice")

    def test_worker_run_takes_only_execution_key_and_unknown_key_is_not_found(self):
        params = list(inspect.signature(SearchWorker.run).parameters)
        self.assertEqual(params[0], "self")
        self.assertIn("execution_key", params)
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.worker.run("does-not-exist", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_worker_terminal_rerun_returns_recorded_outcome_without_side_effects(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, receipt = self.harness.search("alice", [term_op("python")])
        criteria_digest = self.harness.criteria_repo.state_digest()
        qual_digest = self.harness.qual_repo.state_digest()
        retrieval_digest = self.harness.retrieval_repo.state_digest()
        rerun = self.harness.worker.run(final.execution_key, now=NOW)
        self.assertEqual(rerun, final)
        self.assertEqual(self.harness.criteria_repo.state_digest(), criteria_digest)
        self.assertEqual(self.harness.qual_repo.state_digest(), qual_digest)
        self.assertEqual(self.harness.retrieval_repo.state_digest(), retrieval_digest)

    def test_worker_writes_only_executions_snapshot_and_c5_assessments(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)
        grants_before = len(self.harness.qual_repo._grants)
        observations_before = len(self.harness.qual_repo._observations)
        criteria_digest = self.harness.criteria_repo.state_digest()
        canonical_opportunities_before = set(self.harness.canonical_repo._opportunities)
        final = self.harness.worker.run(execution.execution_key, now=NOW)
        self.assertEqual(self.harness.criteria_repo.state_digest(), criteria_digest)
        self.assertEqual(set(self.harness.canonical_repo._opportunities), canonical_opportunities_before)
        self.assertEqual(len(self.harness.qual_repo._grants), grants_before)
        self.assertEqual(len(self.harness.qual_repo._observations), observations_before)
        self.assertGreater(len(self.harness.qual_repo._assessments), 0)
        self.assertIsNotNone(self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key))

    def test_worker_never_calls_canonical_mutating_methods(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        mutating_names = {
            "admit", "admit_observation", "record_receipt", "complete_reverification",
            "re_admit_changed_listing", "record_outage", "mark_stale", "confirm_closed",
            "validate_application_link", "merge", "split", "tombstone_source_content",
            "register_policy", "revise_policy", "register_connector",
        }
        calls = []
        real_service = self.harness.canonical_service

        class Spy:
            def __getattr__(self, name):
                calls.append(name)
                return getattr(real_service, name)

        self.harness.worker._canonical_service = Spy()
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertTrue(set(calls) & {"resolve_opportunity", "canonical_gate"})
        self.assertEqual(set(calls) & mutating_names, set())

    def test_assessment_actor_is_system_search_worker_assessment(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, receipt = self.harness.search("alice", [term_op("python")])
        for assessment_key, assessment in self.harness.qual_repo._assessments.items():
            for revision in self.harness.qual_repo._revisions[assessment_key]:
                self.assertEqual(revision.actor, "system:search_worker/assessment")

    def test_worker_passes_no_member_context_text_to_c5(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertGreater(len(self.harness.provider.calls), 0)
        for prompt in self.harness.provider.calls:
            self.assertIsNone(prompt.member_context_text)


# ---------------------------------------------------------------------------
# C. Recheck at execution and final recheck
# ---------------------------------------------------------------------------


class RecheckTests(RetrievalTestCase):
    def test_missing_snapshot_at_start_fails_stale_criteria_no_snapshot_written(self):
        opportunity, listing, rv = self.harness.admit()
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)
        del self.harness.criteria_repo._snapshots[receipt.snapshot_key]
        final = self.harness.worker.run(execution.execution_key, now=NOW)
        self.assertEqual(final.state, "failed")
        self.assertEqual(final.failed_reason, "stale_criteria")
        self.assertIsNone(self.harness.retrieval_repo.snapshot_for_execution("alice", execution.execution_key))

    def test_snapshot_owner_mismatch_at_start_fails_stale_criteria(self):
        opportunity, listing, rv = self.harness.admit()
        bob_receipt = self.harness.apply_criteria("bob", [term_op("python")])
        # Bypass register_execution's own ownership check to construct a
        # record pointing at another owner's snapshot key directly.
        execution = SearchExecution(
            execution_key="forged-exec", user_key="alice", data_class="fixture",
            snapshot_key=bob_receipt.snapshot_key, state=STATE_SUBMITTED, retrieval_path=None,
            coverage="full", unavailable_checks=(), failed_reason=None, partial_reason=None,
            cancel_reason=None, submitted_at=NOW, stage_started_at={STATE_SUBMITTED: NOW}, terminal_at=None,
        )
        self.harness.retrieval_repo.save_execution(execution)
        final = self.harness.worker.run("forged-exec", now=NOW)
        self.assertEqual(final.state, "failed")
        self.assertEqual(final.failed_reason, "stale_criteria")

    def test_snapshot_removed_mid_run_fails_authorization_changed_before_persistence(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)

        real = self.harness.criteria_repo
        calls = {"n": 0}

        class FlakyCriteriaReader:
            def snapshot_for_owner(self, user_key, snapshot_key):
                calls["n"] += 1
                if calls["n"] >= 2:
                    return None  # simulate the snapshot vanishing before the final recheck
                return real.snapshot_for_owner(user_key, snapshot_key)

        self.harness.worker._criteria_reader = FlakyCriteriaReader()
        final = self.harness.worker.run(execution.execution_key, now=NOW)
        self.assertEqual(final.state, "failed")
        self.assertEqual(final.failed_reason, "authorization_changed")
        self.assertIsNone(self.harness.retrieval_repo.snapshot_for_execution("alice", execution.execution_key))
        events = [event for event in self.harness.worker_audit.events if event.event_kind == "authorization_changed"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].reason_code, "authorization_changed")
        self.assertEqual(events[0].keys, (execution.execution_key,))  # content-free: no query text/criteria carried
        self.assertGreater(len(self.harness.qual_repo._assessments), 0)  # C5 rows remain durable

    def test_failed_final_recheck_permits_no_additional_member_result_persistence(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)

        real = self.harness.criteria_repo
        calls = {"n": 0}

        class FlakyCriteriaReader:
            def snapshot_for_owner(self, user_key, snapshot_key):
                calls["n"] += 1
                if calls["n"] >= 2:
                    return None
                return real.snapshot_for_owner(user_key, snapshot_key)

        original_persist = self.harness.retrieval_repo.persist_snapshot
        persist_calls = []
        self.harness.retrieval_repo.persist_snapshot = lambda snapshot: (
            persist_calls.append(snapshot) or original_persist(snapshot)
        )
        self.harness.worker._criteria_reader = FlakyCriteriaReader()
        self.harness.worker.run(execution.execution_key, now=NOW)
        self.assertEqual(persist_calls, [])

    def test_assessments_written_before_authorization_change_follow_recompute_policy_untouched_by_c4(self):
        opportunity, listing, rv = self.harness.admit()
        grant = self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)

        real = self.harness.criteria_repo
        calls = {"n": 0}

        class FlakyCriteriaReader:
            def snapshot_for_owner(self, user_key, snapshot_key):
                calls["n"] += 1
                if calls["n"] >= 2:
                    return None
                return real.snapshot_for_owner(user_key, snapshot_key)

        self.harness.worker._criteria_reader = FlakyCriteriaReader()
        self.harness.worker.run(execution.execution_key, now=NOW)
        # C5's own revocation/recompute path still works untouched by C4.
        outcome = self.harness.qual_service.revoke_grant(
            "alice", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW
        )
        self.assertEqual(outcome.grant.grant_key, grant.grant_key)


# ---------------------------------------------------------------------------
# D. Retrieval, matching, scope, counts
# ---------------------------------------------------------------------------


class RetrievalMatchingTests(RetrievalTestCase):
    def test_empty_one_many_results_fixture_matrix_with_real_counts(self):
        # zero
        final0, _ = self.harness.search("alice", [term_op("nonexistentterm")])
        page0 = self.harness.retrieval_service.results("alice", execution_key=final0.execution_key, now=NOW)
        self.assertEqual((page0.total_qualified, page0.total_broader), (0, 0))

        # one
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("bob")
        self.harness.verify_all_items("bob", rv)
        final1, _ = self.harness.search("bob", [term_op("python")])
        page1 = self.harness.retrieval_service.results("bob", execution_key=final1.execution_key, now=NOW)
        self.assertEqual(page1.total_qualified, 1)

        # many
        self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Senior Platform Engineer"))
        self.harness.admit(fixture_candidate(external_reference="astraeus-3", title="Staff Platform Engineer"))
        final_many, _ = self.harness.search("bob", [term_op("python")])
        page_many = self.harness.retrieval_service.results("bob", execution_key=final_many.execution_key, now=NOW)
        self.assertEqual(page_many.total_qualified + page_many.total_broader, 3)

    def test_matcher_is_deterministic_and_case_folded_per_kind(self):
        opportunity, listing, rv = self.harness.admit()
        version = self.harness.canonical_repo.version(opportunity.governing_source_version_key)
        free_text = type("C", (), {"kind": "free_text_term", "value": "PYTHON"})()
        self.assertTrue(matches_criteria(version, [free_text], ()))
        arrangement_ok = type("C", (), {"kind": "arrangement", "value": "HYBRID"})()
        self.assertTrue(matches_criteria(version, [arrangement_ok], ()))
        arrangement_bad = type("C", (), {"kind": "arrangement", "value": "remote"})()
        self.assertFalse(matches_criteria(version, [arrangement_bad], ()))
        location_ok = type("C", (), {"kind": "location", "value": "chicago, il"})()
        self.assertTrue(matches_criteria(version, [location_ok], ()))
        comp_ok = type("C", (), {"kind": "compensation_floor", "value": "100000"})()
        self.assertTrue(matches_criteria(version, [comp_ok], ()))
        comp_bad = type("C", (), {"kind": "compensation_floor", "value": "999000"})()
        self.assertFalse(matches_criteria(version, [comp_bad], ()))
        # absent-fact no-match rule
        no_arrangement = replace(version, arrangement=None)
        self.assertFalse(matches_criteria(no_arrangement, [arrangement_ok], ()))

    def test_direct_filter_parity_manual_and_ai_snapshots_produce_identical_entries_and_order(self):
        # MINOR 19: the name promises an end-to-end claim (identical
        # ENTRIES AND ORDER from two full snapshots) -- the original body
        # only compared matches_criteria() in isolation and never built or
        # ran either snapshot. Build one snapshot the "manual" way (a
        # structured criterion) and one the way an AI-interpreted draft
        # would carry the same constraint (a direct filter), run both, and
        # compare the actual result entries.
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        manual_final, _ = self.harness.search(
            "alice",
            [
                term_op("python"),
                {"op": "set_criterion", "kind": "arrangement", "display_label": "Arrangement", "value": "hybrid"},
            ],
        )
        filter_final, _ = self.harness.search(
            "alice",
            [term_op("python"), {"op": "set_direct_filter", "filter_key": "arrangement", "value": "hybrid"}],
        )
        manual_snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", manual_final.execution_key)
        filter_snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", filter_final.execution_key)
        self.assertEqual(len(manual_snapshot.entries), 1)

        def _shape(entries):
            return [(e.opportunity_key, e.partition, e.ordinal, e.gate_outcome) for e in entries]

        self.assertEqual(_shape(manual_snapshot.entries), _shape(filter_snapshot.entries))

        # A criterion naming a DIFFERENT arrangement produces no match --
        # proving the parity above is a genuine match, not a vacuous one.
        mismatched_final, _ = self.harness.search(
            "alice",
            [term_op("python"), {"op": "set_direct_filter", "filter_key": "arrangement", "value": "remote"}],
        )
        mismatched_snapshot = self.harness.retrieval_repo.snapshot_for_execution(
            "alice", mismatched_final.execution_key
        )
        self.assertEqual(len(mismatched_snapshot.entries), 0)

    def test_verification_scope_fully_verified_excludes_broader_and_vice_versa(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)  # -> fully_verified
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        # rv2 left unverified -> not_fully_verified (still matches "python")
        final_full, _ = self.harness.search("alice", [term_op("python")], verification_scope="fully_verified")
        page_full = self.harness.retrieval_service.results("alice", execution_key=final_full.execution_key, now=NOW)
        self.assertTrue(all(entry["gate_outcome"] == GATE_FULLY_VERIFIED for entry in page_full.entries))
        self.assertEqual(page_full.total_broader, 0)

        final_broader, _ = self.harness.search("alice", [term_op("python")], verification_scope="not_fully_verified")
        page_broader = self.harness.retrieval_service.results(
            "alice", execution_key=final_broader.execution_key, now=NOW
        )
        self.assertTrue(all(entry["gate_outcome"] == GATE_NOT_FULLY_VERIFIED for entry in page_broader.entries))
        self.assertEqual(page_broader.total_qualified, 0)

    def test_partitions_never_mix_and_pairing_check_holds(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        final, _ = self.harness.search("alice", [term_op("python")])
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        for entry in snapshot.entries:
            if entry.partition == PARTITION_QUALIFIED:
                self.assertEqual(entry.gate_outcome, GATE_FULLY_VERIFIED)
            else:
                self.assertEqual(entry.partition, PARTITION_BROADER)
                self.assertEqual(entry.gate_outcome, GATE_NOT_FULLY_VERIFIED)

    def test_gate_ineligible_and_withheld_requirement_candidates_dropped_with_content_free_events(self):
        # A listing that is admitted but never gets its application link
        # validated never passes the Live Opportunity Gate.
        candidate = fixture_candidate()
        receipt = self.harness.canonical_service.record_receipt(
            self.harness.direct, SourceReceiptInput(candidate.external_reference, NOW, "application/json", b'{}'),
            now=NOW,
        )
        self.harness.canonical_service.admit(self.harness.direct, receipt, candidate, now=NOW)
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual((final.state,), ("complete",))
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual((page.total_qualified, page.total_broader), (0, 0))
        events = [e for e in self.harness.worker_audit.events if e.event_kind == "entry_dropped"]
        self.assertTrue(events)
        for event in events:
            self.assertIn(event.reason_code, ENTRY_DROP_REASONS)
            self.assertEqual(event.keys, ())  # content-free: no opportunity identity carried

    def test_fixture_and_production_data_classes_never_mix_in_one_execution(self):
        opportunity, listing, rv = self.harness.admit()  # fixture
        prod_descriptor = descriptor(source_id="prod-direct", policy_key="prod-policy", data_class="production")
        self.harness.canonical_service.register_policy(policy(source_id="prod-direct", policy_key="prod-policy", data_class="production"), now=NOW)
        self.harness.canonical_service.register_connector(prod_descriptor, now=NOW)
        prod_candidate = fixture_candidate(external_reference="prod-1", data_class="production")
        receipt = self.harness.canonical_service.record_receipt(
            prod_descriptor, SourceReceiptInput(prod_candidate.external_reference, NOW, "application/json", b'{}'), now=NOW,
        )
        prod_listing = self.harness.canonical_service.admit(prod_descriptor, receipt, prod_candidate, now=NOW)
        client = SafeOutboundClient(resolver=lambda *_: ["93.184.216.34"], transport=lambda _r: OutboundResponse(200, {}, b"ok"))
        self.harness.canonical_service.validate_application_link(prod_listing.listing_key, client, now=NOW)

        final, _ = self.harness.search("alice", [term_op("python")], data_class="fixture")
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        for entry in page.entries:
            self.assertNotEqual(entry["opportunity_key"], prod_listing.canonical_opportunity_key)


# ---------------------------------------------------------------------------
# E. Partial executions (doc 04 §11) and the durable-row split
# ---------------------------------------------------------------------------


class PartialExecutionTests(RetrievalTestCase):
    def test_assessment_persistence_failure_excludes_entry_and_terminates_partial(self):
        opp1, listing1, rv1 = self.harness.admit()
        opp2, listing2, rv2 = self.harness.admit(other_candidate())
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv1)
        self.harness.verify_all_items("alice", rv2)
        failing_item = rv1.items[0].requirement_item_key
        self.harness.qual_repo = FailingQualificationRepository(fail_on_revision_for={failing_item})
        self.harness.qual_service = QualificationService(
            self.harness.qual_repo, evidence_ports={EVIDENCE_CLASS_WORKSHOP: self.harness.evidence_port},
            provider=self.harness.provider, audit_sink=self.harness.qual_audit,
        )
        self.harness.worker._qualification_service = self.harness.qual_service
        final, _ = self.harness.search("alice", [])
        self.assertEqual(final.state, "partial")
        self.assertEqual(final.partial_reason, "assessment_persistence_failure")
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        opportunity_keys = {entry["opportunity_key"] for entry in page.entries}
        self.assertNotIn(opp1.opportunity_key, opportunity_keys)
        self.assertIn(opp2.opportunity_key, opportunity_keys)
        events = [e for e in self.harness.worker_audit.events if e.event_kind == "entry_excluded_persistence"]
        self.assertEqual(len(events), 1)

    def test_computation_failure_writes_durable_review_unavailable_row_and_entry_is_included(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.provider.fail_with = "unavailable"
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "complete")
        self.assertIn("ai_unavailable", final.unavailable_checks)
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(len(page.entries), 1)
        self.assertGreater(page.entries[0]["required_summary"]["review_unavailable"], 0)
        for assessment in self.harness.qual_repo._assessments.values():
            self.assertEqual(assessment.state, "review_unavailable")

    def test_every_reported_per_item_state_has_a_durable_backing_row(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        for entry in snapshot.entries:
            assessments = self.harness.qual_repo.assessments_for_version("alice", entry.requirement_version_key)
            self.assertEqual(len(assessments), entry.required_summary.total + entry.preferred_summary.total)

    def test_retrieval_ceiling_after_admission_yields_partial_budget_exhausted_with_lower_bound_totals(self):
        self.harness = Harness(retrieval_limits=RetrievalLimits(retrieval_ceiling=1))
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        self.assertEqual(final.partial_reason, "budget_exhausted")
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertTrue(snapshot.totals_are_lower_bound)
        self.assertEqual(len(snapshot.entries), 1)

    def test_deadline_exhaustion_yields_partial_timeout_with_only_fully_evaluated_entries(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search(
            "alice", [term_op("python")], deadline=NOW, clock=lambda: NOW + timedelta(seconds=1)
        )
        self.assertEqual(final.state, "partial")
        self.assertEqual(final.partial_reason, "timeout")
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertEqual(len(snapshot.entries), 0)

    def test_canonical_read_failure_mid_run_yields_partial_provider_failure(self):
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        real_repo = self.harness.canonical_repo
        calls = {"n": 0}

        class FlakyCanonicalRepo:
            def __getattr__(self, name):
                return getattr(real_repo, name)

            def requirement_version(self, key):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise RuntimeError("storage outage")
                return real_repo.requirement_version(key)

        self.harness.worker._canonical_repository = FlakyCanonicalRepo()
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        self.assertEqual(final.partial_reason, "provider_failure")

    def test_index_failure_mid_search_yields_partial_index_failure(self):
        self.harness = Harness(index=InMemoryDiscoveryIndex())
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        rebuild_index(self.harness.index, self.harness.canonical_repo, "fixture", canonical_service=self.harness.canonical_service, now=NOW)
        real_repo = self.harness.canonical_repo
        calls = {"n": 0}

        class FlakyCanonicalRepo:
            def __getattr__(self, name):
                return getattr(real_repo, name)

            def version(self, key):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise RuntimeError("storage outage")
                return real_repo.version(key)

        self.harness.worker._canonical_repository = FlakyCanonicalRepo()
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        self.assertEqual(final.partial_reason, "index_failure")

    def test_partial_reason_precedence_is_deterministic(self):
        # IMPORTANT 9: three distinct opportunities (opportunity_key is a
        # random uuid4, so which two of the three survive ceiling=2
        # truncation is not itself deterministic) with a ceiling of two --
        # budget_exhausted ALWAYS fires (3 candidates > ceiling 2, whatever
        # the sort order). Every opportunity's distinguishing item is
        # pre-marked to fail persistence, so assessment_persistence_failure
        # ALSO fires no matter which two candidates the ceiling admits --
        # both causes are genuinely, deterministically produced together.
        self.harness = Harness(retrieval_limits=RetrievalLimits(retrieval_ceiling=2))
        opp1, listing1, rv1 = self.harness.admit(
            fixture_candidate(external_reference="astraeus-1", title="Platform Engineer One")
        )
        opp2, listing2, rv2 = self.harness.admit(
            fixture_candidate(external_reference="astraeus-2", title="Platform Engineer Two")
        )
        opp3, listing3, rv3 = self.harness.admit(
            fixture_candidate(external_reference="astraeus-3", title="Platform Engineer Three")
        )
        self.harness.grant("alice")
        for rv in (rv1, rv2, rv3):
            self.harness.verify_all_items("alice", rv)
        failing_items = {rv.items[0].requirement_item_key for rv in (rv1, rv2, rv3)}
        self.harness.qual_repo = FailingQualificationRepository(fail_on_revision_for=failing_items)
        self.harness.qual_service = QualificationService(
            self.harness.qual_repo, evidence_ports={EVIDENCE_CLASS_WORKSHOP: self.harness.evidence_port},
            provider=self.harness.provider, audit_sink=self.harness.qual_audit,
        )
        self.harness.worker._qualification_service = self.harness.qual_service
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        # Precedence names assessment_persistence_failure ahead of
        # budget_exhausted (PARTIAL_REASON_PRECEDENCE), but BOTH causes'
        # disclosures must still be present -- precedence picks the
        # headline reason, it does not erase the other cause's evidence.
        self.assertEqual(final.partial_reason, PARTIAL_ASSESSMENT_PERSISTENCE)
        self.assertLess(
            PARTIAL_REASON_PRECEDENCE.index(PARTIAL_ASSESSMENT_PERSISTENCE),
            PARTIAL_REASON_PRECEDENCE.index(PARTIAL_BUDGET_EXHAUSTED),
        )
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertTrue(any("retrieval ceiling reached" in d for d in snapshot.disclosures))
        self.assertTrue(any("could not be saved" in d for d in snapshot.disclosures))
        excluded_events = [
            e for e in self.harness.worker_audit.events if e.event_kind == "entry_excluded_persistence"
        ]
        self.assertTrue(excluded_events)

    def test_partial_snapshot_is_immutable_pageable_and_restorable_like_complete(self):
        self.harness = Harness(retrieval_limits=RetrievalLimits(retrieval_ceiling=1))
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        final, _ = self.harness.search("alice", [term_op("python")])
        # IMPORTANT 9: this test's own name promises a partial snapshot --
        # confirm the scenario actually produced one (two distinct
        # candidates, ceiling one) rather than trivially exercising a
        # complete snapshot of a single, accidentally-merged opportunity.
        self.assertEqual(final.state, "partial")
        page1 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        page2 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(page1.entries, page2.entries)

    def test_retry_is_a_new_apply_and_never_mutates_the_partial_snapshot(self):
        self.harness = Harness(retrieval_limits=RetrievalLimits(retrieval_ceiling=1))
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        before = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        final2, receipt2 = self.harness.search("alice", [term_op("python")])
        self.assertNotEqual(receipt.execution_key, receipt2.execution_key)
        after = self.harness.retrieval_repo.snapshot_for_owner("alice", before.result_key)
        self.assertEqual(before, after)

    def test_register_replay_returns_same_execution_and_partial_snapshot_never_reruns(self):
        self.harness = Harness(retrieval_limits=RetrievalLimits(retrieval_ceiling=1))
        opp1, listing1, rv1 = self.harness.admit(fixture_candidate(external_reference="astraeus-1"))
        opp2, listing2, rv2 = self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer"))
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "partial")
        replayed = self.harness.register("alice", receipt)
        self.assertEqual(replayed, final)
        snapshot_count_before = len(self.harness.retrieval_repo._snapshots_by_result_key)
        rerun = self.harness.worker.run(final.execution_key, now=NOW)
        self.assertEqual(rerun, final)
        self.assertEqual(len(self.harness.retrieval_repo._snapshots_by_result_key), snapshot_count_before)


# ---------------------------------------------------------------------------
# F. Degraded modes / index path
# ---------------------------------------------------------------------------


class DegradedModeTests(RetrievalTestCase):
    def test_index_unavailable_falls_back_to_canonical_with_degraded_status_and_reduced_snapshot_disclosure(self):
        self.harness = Harness(index=InMemoryDiscoveryIndex(fail_with=IndexUnavailable))
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "complete")
        self.assertEqual(final.coverage, "degraded")
        self.assertEqual(final.retrieval_path, "canonical")
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertEqual(snapshot.coverage, "reduced")
        self.assertTrue(any("discovery index unavailable" in disclosure for disclosure in snapshot.disclosures))

    def test_index_and_canonical_both_unavailable_fails_index_unavailable_truthfully(self):
        self.harness = Harness(index=InMemoryDiscoveryIndex(fail_with=IndexUnavailable))
        opportunity, listing, rv = self.harness.admit()
        real_repo = self.harness.canonical_repo

        class BrokenCanonicalRepo:
            def __getattr__(self, name):
                return getattr(real_repo, name)

            def opportunities(self, data_class):
                raise RuntimeError("storage down")

        self.harness.worker._canonical_repository = BrokenCanonicalRepo()
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "failed")
        self.assertEqual(final.failed_reason, "index_unavailable")

    def test_canonical_path_executions_carry_no_relevance_for_any_entry(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.retrieval_path, "canonical")
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertTrue(snapshot.entries)
        for entry in snapshot.entries:
            self.assertIsNone(entry.ordering_inputs.retrieval_relevance)


# ---------------------------------------------------------------------------
# G. Reduced coverage
# ---------------------------------------------------------------------------


class ReducedCoverageTests(RetrievalTestCase):
    def test_review_unavailable_reasons_populate_unavailable_checks_and_reduced_coverage(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.provider.fail_with = "unavailable"
        final, _ = self.harness.search("alice", [term_op("python")])
        self.assertIn("ai_unavailable", final.unavailable_checks)
        self.assertEqual(final.coverage, "reduced")
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertEqual(snapshot.coverage, "reduced")

    def test_reduced_coverage_disclosure_names_the_checks_verbatim(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.provider.fail_with = "unavailable"
        final, _ = self.harness.search("alice", [term_op("python")])
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertTrue(any("ai_unavailable" in disclosure for disclosure in snapshot.disclosures))

    def test_no_silent_upgrade_of_incomplete_evidence(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.provider.fail_with = "unavailable"
        final, _ = self.harness.search("alice", [term_op("python")])
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertEqual(len(snapshot.entries), 1)
        self.assertEqual(snapshot.entries[0].partition, PARTITION_BROADER)
        self.assertEqual(snapshot.entries[0].gate_outcome, GATE_NOT_FULLY_VERIFIED)


# ---------------------------------------------------------------------------
# H. Pagination, restoration, staleness, result-time basis
# ---------------------------------------------------------------------------


class PaginationRestorationTests(RetrievalTestCase):
    def _three_entries(self):
        self.harness.admit(fixture_candidate(external_reference="astraeus-1", title="Platform Engineer A"))
        self.harness.admit(fixture_candidate(external_reference="astraeus-2", title="Platform Engineer B"))
        self.harness.admit(fixture_candidate(external_reference="astraeus-3", title="Platform Engineer C"))
        final, _ = self.harness.search("alice", [term_op("python")])
        return final

    def test_cursor_pagination_is_stable_and_snapshot_bound(self):
        final = self._three_entries()
        page1 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, page_size=1, now=NOW)
        self.assertEqual(len(page1.entries), 1)
        self.assertIsNotNone(page1.next_cursor)
        page2 = self.harness.retrieval_service.results(
            "alice", result_key=page1.result_key, cursor=page1.next_cursor, page_size=1, now=NOW
        )
        self.assertEqual(len(page2.entries), 1)
        self.assertNotEqual(page1.entries[0]["opportunity_key"], page2.entries[0]["opportunity_key"])
        page3 = self.harness.retrieval_service.results(
            "alice", result_key=page1.result_key, cursor=page2.next_cursor, page_size=1, now=NOW
        )
        self.assertIsNone(page3.next_cursor)
        default_page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(len(default_page.entries), 3)
        with self.assertRaises(RetrievalServiceError) as too_big:
            self.harness.retrieval_service.results("alice", execution_key=final.execution_key, page_size=51, now=NOW)
        self.assertEqual(too_big.exception.failure_code, "page_size_invalid")
        with self.assertRaises(RetrievalServiceError) as zero:
            self.harness.retrieval_service.results("alice", execution_key=final.execution_key, page_size=0, now=NOW)
        self.assertEqual(zero.exception.failure_code, "page_size_invalid")

    def test_cursor_for_other_result_key_or_garbage_is_cursor_invalid(self):
        final = self._three_entries()
        page1 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, page_size=1, now=NOW)
        with self.assertRaises(RetrievalServiceError) as garbage:
            self.harness.retrieval_service.results(
                "alice", result_key=page1.result_key, cursor="not-a-real-cursor", page_size=1, now=NOW
            )
        self.assertEqual(garbage.exception.failure_code, "cursor_invalid")
        wrong_key_cursor = self.harness.retrieval_service.results(
            "alice", execution_key=final.execution_key, page_size=1, now=NOW
        ).next_cursor
        with self.assertRaises(RetrievalServiceError) as mismatched:
            self.harness.retrieval_service.results(
                "alice", result_key="some-other-result-key", cursor=wrong_key_cursor, page_size=1, now=NOW
            )
        self.assertEqual(mismatched.exception.failure_code, "not_found")

    def test_restoration_renders_from_bound_governing_source_version_only(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        before = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        changed = fixture_candidate(description="A totally different, unrelated description.")
        self.harness.canonical_service.record_receipt  # (no-op reference; re-admit below)
        receipt = self.harness.canonical_service.record_receipt(
            self.harness.direct,
            SourceReceiptInput(changed.external_reference, NOW + timedelta(hours=1), "application/json", b'{}'),
            now=NOW + timedelta(hours=1),
        )
        self.harness.canonical_service.admit(self.harness.direct, receipt, changed, now=NOW + timedelta(hours=1))
        after = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(before.entries, after.entries)

    def test_rights_removed_referenced_content_renders_unavailable_never_substituted(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        self.harness.canonical_service.tombstone_source_content(listing.listing_key, now=NOW + timedelta(hours=1))
        after = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(after.entries[0]["display_projection"], {"unavailable_under_rights": True})

    def test_snapshot_age_and_stale_flag_past_horizon_with_disclosures_verbatim(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.provider.fail_with = "unavailable"
        final, _ = self.harness.search("alice", [term_op("python")])
        snapshot = self.harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        fresh = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertFalse(fresh.stale)
        later = NOW + DEFAULT_STALENESS_HORIZON + timedelta(seconds=1)
        stale = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=later)
        self.assertTrue(stale.stale)
        self.assertEqual(stale.disclosures, snapshot.disclosures)

    def test_results_never_requery_or_reorder(self):
        final = self._three_entries()
        real_repo = self.harness.canonical_repo
        opportunity_calls = []

        class SpyRepo:
            def __getattr__(self, name):
                return getattr(real_repo, name)

            def opportunities(self, data_class):
                opportunity_calls.append(data_class)
                return real_repo.opportunities(data_class)

        self.harness.retrieval_service._display_resolver = SpyRepo()
        page1 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        page2 = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual([e["opportunity_key"] for e in page1.entries], [e["opportunity_key"] for e in page2.entries])
        self.assertEqual(opportunity_calls, [])  # results() never enumerates opportunities


# ---------------------------------------------------------------------------
# I. Interrupted search (TTL)
# ---------------------------------------------------------------------------


class InterruptedSearchTests(RetrievalTestCase):
    def test_purge_abandoned_deletes_only_nonterminal_snapshotless_executions_past_ttl(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)  # left submitted, never run
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("bob")
        self.harness.verify_all_items("bob", rv)
        completed, completed_receipt = self.harness.search("bob", [term_op("python")])
        purge_time = NOW + self.harness.limits.abandoned_ttl + timedelta(seconds=1)
        purged = self.harness.retrieval_service.purge_abandoned(now=purge_time)
        self.assertEqual(purged, 1)
        self.assertIsNone(self.harness.retrieval_repo.execution_for_owner("alice", execution.execution_key))
        self.assertIsNotNone(self.harness.retrieval_repo.execution_for_owner("bob", completed.execution_key))

    def test_purged_execution_leaves_no_restorable_snapshot_and_status_is_not_found(self):
        receipt = self.harness.apply_criteria("alice", [term_op("python")])
        execution = self.harness.register("alice", receipt)
        purge_time = NOW + self.harness.limits.abandoned_ttl + timedelta(seconds=1)
        self.harness.retrieval_service.purge_abandoned(now=purge_time)
        with self.assertRaises(RetrievalServiceError) as ctx:
            self.harness.retrieval_service.status("alice", execution.execution_key, now=purge_time)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_purge_is_content_blind_key_and_age_only(self):
        # MINOR 19: the blueprint's own binding description for this test
        # (§10) is "works with a repository stub whose content accessors
        # raise" -- the original body never built one; it only checked the
        # method's parameter names and called the real implementation.
        params = inspect.signature(InMemoryRetrievalRepository.purge_abandoned_executions).parameters
        self.assertEqual(set(params) - {"self"}, {"now", "ttl"})

        class ContentBlindRepository(InMemoryRetrievalRepository):
            def execution_for_owner(self, user_key, execution_key):
                raise AssertionError("purge must never read execution content")

            def snapshot_for_owner(self, user_key, result_key):
                raise AssertionError("purge must never read snapshot content")

            def snapshot_for_execution(self, user_key, execution_key):
                raise AssertionError("purge must never read snapshot content")

            def active_executions_for_owner(self, user_key):
                raise AssertionError("purge must never enumerate by owner")

        repo = ContentBlindRepository()
        stale = SearchExecution(
            execution_key="stale-exec", user_key="alice", data_class="fixture", snapshot_key="snap-1",
            state=STATE_SUBMITTED, retrieval_path=None, coverage="full", unavailable_checks=(),
            failed_reason=None, partial_reason=None, cancel_reason=None, submitted_at=NOW,
            stage_started_at={STATE_SUBMITTED: NOW}, terminal_at=None,
        )
        fresh = SearchExecution(
            execution_key="fresh-exec", user_key="alice", data_class="fixture", snapshot_key="snap-2",
            state=STATE_SUBMITTED, retrieval_path=None, coverage="full", unavailable_checks=(),
            failed_reason=None, partial_reason=None, cancel_reason=None,
            submitted_at=NOW + self.harness.limits.abandoned_ttl,
            stage_started_at={STATE_SUBMITTED: NOW + self.harness.limits.abandoned_ttl}, terminal_at=None,
        )
        repo.save_execution(stale)
        repo.save_execution(fresh)
        purge_time = NOW + self.harness.limits.abandoned_ttl + timedelta(seconds=1)
        purged = repo.purge_abandoned_executions(now=purge_time, ttl=self.harness.limits.abandoned_ttl)
        self.assertEqual(purged, 1)
        self.assertIsNone(repo.execution("stale-exec"))
        self.assertIsNotNone(repo.execution("fresh-exec"))


# ---------------------------------------------------------------------------
# J. Ordering determinism (doc 04 §4)
# ---------------------------------------------------------------------------


def _evaluation(
    key, *, preferred_verified=0, relevance=None, verified_at=None, posted=None, gate=GATE_FULLY_VERIFIED
):
    from services.my_opportunities.retrieval_service import PreferredSummary, RequiredSummary

    return EntryEvaluation(
        opportunity_key=key, requirement_version_key=f"{key}-rv", governing_source_version_key=f"{key}-sv",
        gate=gate, required_summary=RequiredSummary(1, 0, 0, 0, 1),
        preferred_summary=PreferredSummary(preferred_verified, preferred_verified),
        preferred_verified=preferred_verified, retrieval_relevance=relevance,
        last_successfully_verified_at=verified_at, posted_at=posted,
    )


class OrderingTests(unittest.TestCase):
    def test_qualified_chain_position1_preferred_verified_count_desc_absent_is_zero(self):
        low = _evaluation("low", preferred_verified=0)
        high = _evaluation("high", preferred_verified=3)
        ordered = sorted([low, high], key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in ordered], ["high", "low"])

    def test_qualified_chain_position2_relevance_index_path_only_null_sorts_lowest(self):
        none_relevance = _evaluation("none-rel", relevance=None)
        some_relevance = _evaluation("some-rel", relevance=2.0)
        ordered = sorted([none_relevance, some_relevance], key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in ordered], ["some-rel", "none-rel"])

    def test_qualified_chain_position3_last_successfully_verified_at_desc_null_oldest(self):
        older = _evaluation("older", verified_at=NOW - timedelta(days=5))
        newer = _evaluation("newer", verified_at=NOW)
        null_verified = _evaluation("null-verified", verified_at=None)
        ordered = sorted([older, newer, null_verified], key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in ordered], ["newer", "older", "null-verified"])

    def test_qualified_chain_position4_posting_date_desc_null_oldest(self):
        older = _evaluation("older-post", posted=date(2026, 1, 1))
        newer = _evaluation("newer-post", posted=date(2026, 8, 1))
        null_posted = _evaluation("null-post", posted=None)
        ordered = sorted([older, newer, null_posted], key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in ordered], ["newer-post", "older-post", "null-post"])

    def test_qualified_chain_position5_opportunity_key_total_order_no_ties(self):
        a = _evaluation("a-key")
        b = _evaluation("b-key")
        ordered = sorted([b, a], key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in ordered], ["a-key", "b-key"])

    def test_broader_chain_uses_no_preferred_count_and_no_unmet_signal(self):
        # IMPORTANT 10: names deliberately DISAGREE with what preferred_count
        # would produce -- "z-high-pref" sorts LAST by opportunity_key but
        # would sort FIRST if broader_sort_key incorrectly weighed
        # preferred_verified the way qualified_sort_key does. The original
        # naming ("high-pref"/"low-pref") happened to agree with both
        # orderings and could not actually distinguish "correctly ignores
        # preferred_count" from "bug: uses it" -- this can.
        low_preferred = _evaluation("a-low-pref", preferred_verified=0, relevance=1.0, gate=GATE_NOT_FULLY_VERIFIED)
        high_preferred = _evaluation("z-high-pref", preferred_verified=5, relevance=1.0, gate=GATE_NOT_FULLY_VERIFIED)
        ordered = sorted([high_preferred, low_preferred], key=broader_sort_key)
        # Correct (preferred-blind) order is pure opportunity_key ascending.
        self.assertEqual([e.opportunity_key for e in ordered], ["a-low-pref", "z-high-pref"])

    def test_ordering_is_stable_under_candidate_shuffle(self):
        entries = [
            _evaluation(f"key-{i}", relevance=float(i % 3), verified_at=NOW - timedelta(days=i), posted=date(2026, 1, 1) + timedelta(days=i))
            for i in range(10)
        ]
        baseline = sorted(entries, key=qualified_sort_key)
        shuffled = list(entries)
        random.Random(42).shuffle(shuffled)
        result = sorted(shuffled, key=qualified_sort_key)
        self.assertEqual([e.opportunity_key for e in baseline], [e.opportunity_key for e in result])

    def test_ordering_uses_no_wall_clock_or_randomness(self):
        # IMPORTANT 10: exercises the real worker end to end (not just the
        # bare sort-key functions) under armed tripwires, run twice with two
        # DIFFERENT injected `now` values -- if anything in the run path
        # secretly consulted the wall clock or randomness, either the
        # tripwire fires or the two runs would disagree on order.
        import random as random_module

        import services.my_opportunities.search_worker as search_worker_module

        class _TripwireDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                raise AssertionError("search_worker must never call datetime.now")

        def _forbidden_random(*args, **kwargs):
            raise AssertionError("search_worker must never call random")

        def _run_once(now):
            # Every admitted candidate is functionally identical (same
            # relevance, same freshness, same posted_at) so the ONLY thing
            # that can legitimately decide their order is opportunity_key
            # ascending (chain position 5) -- a fresh, random uuid4 each
            # run, so this proves the correct tiebreak was used without
            # needing to compare literal key values *across* runs.
            harness = Harness()
            harness.admit(fixture_candidate(external_reference="astraeus-1", title="Platform Engineer One"), when=now)
            harness.admit(
                fixture_candidate(external_reference="astraeus-2", title="Platform Engineer Two"), when=now
            )
            harness.admit(
                fixture_candidate(external_reference="astraeus-3", title="Platform Engineer Three"), when=now
            )
            final, _ = harness.search("alice", [term_op("python")], now=now)
            self.assertEqual(final.state, "complete")
            snapshot = harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
            return tuple(entry.opportunity_key for entry in snapshot.entries)

        original_datetime = search_worker_module.datetime
        original_random = random_module.random
        search_worker_module.datetime = _TripwireDatetime
        random_module.random = _forbidden_random
        try:
            order_one = _run_once(NOW)
            order_two = _run_once(NOW + timedelta(days=40))
        finally:
            search_worker_module.datetime = original_datetime
            random_module.random = original_random

        self.assertEqual(len(order_one), 3)
        self.assertEqual(order_one, tuple(sorted(order_one)))
        self.assertEqual(len(order_two), 3)
        self.assertEqual(order_two, tuple(sorted(order_two)))

    def test_ordering_inputs_stored_on_entries_and_never_serialized(self):
        harness = Harness()
        opportunity, listing, rv = harness.admit()
        harness.grant("alice")
        harness.verify_all_items("alice", rv)
        final, _ = harness.search("alice", [term_op("python")])
        snapshot = harness.retrieval_repo.snapshot_for_execution("alice", final.execution_key)
        self.assertTrue(hasattr(snapshot.entries[0], "ordering_inputs"))
        page = harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        dumped = json.dumps(page.entries)
        self.assertNotIn("ordering_inputs", dumped)


# ---------------------------------------------------------------------------
# K. Cross-member isolation (doc 08 §7) and REC-05
# ---------------------------------------------------------------------------


class CrossMemberIsolationTests(RetrievalTestCase):
    def test_member_b_cannot_read_status_results_or_cancel_member_a_execution_by_direct_key(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])

        with self.assertRaises(RetrievalServiceError) as status_ctx:
            self.harness.retrieval_service.status("bob", final.execution_key, now=NOW)
        with self.assertRaises(RetrievalServiceError) as results_ctx:
            self.harness.retrieval_service.results("bob", execution_key=final.execution_key, now=NOW)
        with self.assertRaises(RetrievalServiceError) as cancel_ctx:
            self.harness.retrieval_service.cancel("bob", execution_key=final.execution_key, now=NOW)
        with self.assertRaises(RetrievalServiceError) as absent_ctx:
            self.harness.retrieval_service.status("bob", "truly-absent-key", now=NOW)
        for ctx in (status_ctx, results_ctx, cancel_ctx, absent_ctx):
            self.assertEqual(ctx.exception.failure_code, "not_found")
        self.assertEqual(status_ctx.exception.member_message, absent_ctx.exception.member_message)

    def test_no_listing_surface_exists_that_could_enumerate_another_members_results(self):
        public_methods = {name for name in dir(RetrievalService) if not name.startswith("_")}
        forbidden = {name for name in public_methods if "list" in name.lower() or "all" in name.lower()}
        self.assertEqual(forbidden, set())

    def test_member_b_identical_criteria_produce_independent_executions_and_entries(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.grant("bob")
        self.harness.verify_all_items("alice", rv, evidence_key="alice-ev-1")
        self.harness.verify_all_items("bob", rv, evidence_key="bob-ev-1")
        final_a, _ = self.harness.search("alice", [term_op("python")])
        final_b, _ = self.harness.search("bob", [term_op("python")])
        self.assertNotEqual(final_a.execution_key, final_b.execution_key)
        snapshot_a = self.harness.retrieval_repo.snapshot_for_execution("alice", final_a.execution_key)
        snapshot_b = self.harness.retrieval_repo.snapshot_for_execution("bob", final_b.execution_key)
        self.assertNotEqual(snapshot_a.result_key, snapshot_b.result_key)
        self.assertNotEqual(snapshot_a.entries[0].entry_key, snapshot_b.entries[0].entry_key)

    def test_projection_document_field_names_are_structurally_member_free(self):
        opportunity, listing, rv = self.harness.admit()
        version = self.harness.canonical_repo.version(opportunity.governing_source_version_key)
        document = build_projection_document(opportunity, listing, version, rv)
        for field_name in PROJECTION_FIELDS:
            lowered = field_name.lower()
            for token in FORBIDDEN_PROJECTION_TOKENS:
                self.assertNotIn(token, lowered)
        self.assertIsInstance(document, ProjectionDocument)

    def test_projection_builder_signature_accepts_no_owner_or_member_input(self):
        params = list(inspect.signature(build_projection_document).parameters)
        for token in ("user", "member", "owner"):
            for param in params:
                self.assertNotIn(token, param.lower())

    def test_member_canary_values_never_appear_in_any_projection_or_index_content(self):
        canary_user = "CANARY-MEMBER-KEY-9f2c"
        canary_evidence = "CANARY-EVIDENCE-BODY-Q7"
        harness = Harness(index=InMemoryDiscoveryIndex(), members=(canary_user,))
        harness.evidence_records[canary_user] = [_firm_record(f"{canary_user}-ev-1", body=canary_evidence)]
        harness.evidence_port = InMemoryEvidencePort(harness.evidence_records)
        harness.qual_service = QualificationService(
            harness.qual_repo, evidence_ports={EVIDENCE_CLASS_WORKSHOP: harness.evidence_port},
            provider=harness.provider, audit_sink=harness.qual_audit,
        )
        harness.worker._qualification_service = harness.qual_service
        opportunity, listing, rv = harness.admit()
        harness.grant(canary_user)
        harness.verify_all_items(canary_user, rv, evidence_key=f"{canary_user}-ev-1")
        rebuild_index(harness.index, harness.canonical_repo, "fixture", canonical_service=harness.canonical_service, now=NOW)
        criterion = term_op(canary_user)  # a canary in the search criteria itself must not leak either
        final, _ = harness.search(canary_user, [criterion])
        for document in harness.index.documents():
            blob = json.dumps(
                {
                    "employer": document.employer, "title": document.title,
                    "locations": document.locations, "arrangement": document.arrangement,
                    "description_terms": document.description_terms,
                }
            )
            self.assertNotIn(canary_user.lower(), blob.lower())
            self.assertNotIn(canary_evidence.lower(), blob.lower())

    def test_no_member_keyed_row_exists_in_the_index_after_full_rebuild(self):
        harness = Harness(index=InMemoryDiscoveryIndex())
        opportunity, listing, rv = harness.admit()
        rebuild_index(harness.index, harness.canonical_repo, "fixture", canonical_service=harness.canonical_service, now=NOW)
        for document in harness.index.documents():
            for field in ("alice", "bob"):
                self.assertNotEqual(document.opportunity_key, field)
                self.assertNotIn(field, (document.employer or "").lower())

    def test_rebuild_index_counts_rather_than_swallows_gate_evaluation_failures(self):
        """MINOR 17: a canonical_gate exception during rebuild is counted
        as skipped_gate_failures, not silently dropped -- and does not
        abort indexing the other, healthy opportunities."""
        harness = Harness(index=InMemoryDiscoveryIndex())
        opportunity, listing, rv = harness.admit()
        opportunity2, listing2, rv2 = harness.admit(
            fixture_candidate(external_reference="astraeus-2", title="Staff Platform Engineer")
        )
        real_service = harness.canonical_service
        poisoned_key = opportunity.opportunity_key

        class FlakyCanonicalService:
            def __getattr__(self, name):
                return getattr(real_service, name)

            def canonical_gate(self, opportunity_key, *, now):
                if opportunity_key == poisoned_key:
                    raise RuntimeError("gate storage outage")
                return real_service.canonical_gate(opportunity_key, now=now)

        result = rebuild_index(
            harness.index, harness.canonical_repo, "fixture",
            canonical_service=FlakyCanonicalService(), now=NOW,
        )
        self.assertEqual(result.skipped_gate_failures, 1)
        self.assertEqual(result.indexed, 1)
        indexed_keys = {document.opportunity_key for document in harness.index.documents()}
        self.assertEqual(indexed_keys, {opportunity2.opportunity_key})


# ---------------------------------------------------------------------------
# L. Index fence (doc 04 §10)
# ---------------------------------------------------------------------------


class IndexFenceTests(RetrievalTestCase):
    def _document_and_candidate(self, harness, opportunity, listing, version, requirement_version):
        document = build_projection_document(opportunity, listing, version, requirement_version)
        return document, IndexCandidate(document=document, retrieval_relevance=1.0)

    def test_non_finite_or_negative_relevance_is_shape_invalid(self):
        """A hostile or corrupt index relevance value must never reach the
        ordering chain: NaN in a sort key makes ordering nondeterministic, so
        the fence refuses it as shape_invalid before admission."""
        harness = Harness()
        opportunity, listing, rv = harness.admit()
        version = harness.canonical_repo.version(opportunity.governing_source_version_key)
        document, _ = self._document_and_candidate(harness, opportunity, listing, version, rv)
        for bad in (float("nan"), float("inf"), float("-inf"), -0.5, "1.0", None):
            decision = fence_candidate(
                IndexCandidate(document, bad),
                data_class="fixture",
                canonical_service=harness.canonical_service,
                canonical_repository=harness.canonical_repo,
                now=NOW,
            )
            self.assertEqual(
                (decision.admitted, decision.reason), (False, "shape_invalid"), repr(bad)
            )

    def test_fence_drops_each_reason_and_emits_fence_dropped_counts(self):
        harness = Harness()
        opportunity, listing, rv = harness.admit()
        version = harness.canonical_repo.version(opportunity.governing_source_version_key)
        document, candidate = self._document_and_candidate(harness, opportunity, listing, version, rv)

        # data_class_mismatch
        mismatched = replace(document, data_class="production")
        decision = fence_candidate(
            IndexCandidate(mismatched, 1.0), data_class="fixture", canonical_service=harness.canonical_service,
            canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual((decision.admitted, decision.reason), (False, "data_class_mismatch"))

        # opportunity_missing
        missing = replace(document, opportunity_key="00000000-0000-0000-0000-000000000000")
        decision = fence_candidate(
            IndexCandidate(missing, 1.0), data_class="fixture", canonical_service=harness.canonical_service,
            canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual((decision.admitted, decision.reason), (False, "opportunity_missing"))

        # not_current (never linked / gate ineligible)
        unlinked_candidate = fixture_candidate(external_reference="unlinked-1", title="Unlinked Platform Engineer")
        receipt = harness.canonical_service.record_receipt(
            harness.direct, SourceReceiptInput(unlinked_candidate.external_reference, NOW, "application/json", b'{}'), now=NOW
        )
        unlinked_listing = harness.canonical_service.admit(harness.direct, receipt, unlinked_candidate, now=NOW)
        unlinked_opportunity = harness.canonical_service.resolve_opportunity(unlinked_listing.canonical_opportunity_key)
        # This opportunity has no governing basis yet (gate never passed) --
        # build a synthetic document directly rather than through the
        # allowlist builder (which would itself refuse a None governing key).
        synthetic_not_current = replace(
            document, opportunity_key=unlinked_opportunity.opportunity_key,
            governing_listing_key=unlinked_listing.listing_key,
        )
        decision = fence_candidate(
            IndexCandidate(synthetic_not_current, 1.0), data_class="fixture",
            canonical_service=harness.canonical_service, canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual((decision.admitted, decision.reason), (False, "not_current"))

        # governing_version_mismatch
        stale = replace(document, governing_source_version_key="00000000-0000-0000-0000-000000000099")
        decision = fence_candidate(
            IndexCandidate(stale, 1.0), data_class="fixture", canonical_service=harness.canonical_service,
            canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual((decision.admitted, decision.reason), (False, "governing_version_mismatch"))

        # shape_invalid
        malformed = object.__new__(ProjectionDocument)
        object.__setattr__(malformed, "opportunity_key", document.opportunity_key)
        object.__setattr__(malformed, "data_class", "fixture")
        object.__setattr__(malformed, "governing_listing_key", document.governing_listing_key)
        object.__setattr__(malformed, "governing_source_version_key", document.governing_source_version_key)
        object.__setattr__(malformed, "requirement_version_key", document.requirement_version_key)
        object.__setattr__(malformed, "employer", 12345)  # wrong type
        object.__setattr__(malformed, "title", document.title)
        object.__setattr__(malformed, "locations", document.locations)
        object.__setattr__(malformed, "arrangement", document.arrangement)
        object.__setattr__(malformed, "description_terms", document.description_terms)
        object.__setattr__(malformed, "last_successfully_verified_at", document.last_successfully_verified_at)
        object.__setattr__(malformed, "posted_at", document.posted_at)
        decision = fence_candidate(
            IndexCandidate(malformed, 1.0), data_class="fixture", canonical_service=harness.canonical_service,
            canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual((decision.admitted, decision.reason), (False, "shape_invalid"))

        # via the worker: fence_dropped counts emitted with content-free events.
        # The document keeps data_class="fixture" so the index's own
        # data-class partitioning still returns it to the fence; its
        # opportunity_key is redirected to a key absent from this harness's
        # canonical store, so the FENCE itself (not the index) is what drops
        # it, with reason "opportunity_missing".
        harness2 = Harness(index=InMemoryDiscoveryIndex())
        opportunity2, listing2, rv2 = harness2.admit()
        version2 = harness2.canonical_repo.version(opportunity2.governing_source_version_key)
        document2 = build_projection_document(opportunity2, listing2, version2, rv2)
        orphaned = replace(document2, opportunity_key="00000000-0000-0000-0000-000000000000")
        harness2.index.overwrite_document(opportunity2.opportunity_key, orphaned)
        final, _ = harness2.search("alice", [term_op("python")])
        events = [e for e in harness2.worker_audit.events if e.event_kind == "fence_dropped"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].reason_code, "opportunity_missing")
        self.assertEqual(events[0].count, 1)
        self.assertEqual(events[0].keys, ())

    def test_fence_dropped_entries_never_surface_index_only_data(self):
        harness = Harness(index=InMemoryDiscoveryIndex())
        opportunity, listing, rv = harness.admit()
        version = harness.canonical_repo.version(opportunity.governing_source_version_key)
        document = build_projection_document(opportunity, listing, version, rv)
        harness.index.overwrite_document(opportunity.opportunity_key, replace(document, employer="INDEX-ONLY-EMPLOYER", data_class="production"))
        final, _ = harness.search("alice", [term_op("python")])
        page = harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(len(page.entries), 0)

    def test_tampered_index_field_never_renders_because_display_resolves_from_canonical(self):
        harness = Harness(index=InMemoryDiscoveryIndex())
        opportunity, listing, rv = harness.admit()
        harness.grant("alice")
        harness.verify_all_items("alice", rv)
        version = harness.canonical_repo.version(opportunity.governing_source_version_key)
        document = build_projection_document(opportunity, listing, version, rv)
        tampered = replace(document, employer="TAMPERED-EMPLOYER", title="TAMPERED-TITLE")
        harness.index.overwrite_document(opportunity.opportunity_key, tampered)
        final, _ = harness.search("alice", [term_op("python")])
        page = harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(len(page.entries), 1)
        self.assertEqual(page.entries[0]["display_projection"]["employer"], "Astraeus")
        self.assertNotEqual(page.entries[0]["display_projection"]["employer"], "TAMPERED-EMPLOYER")

    def test_fence_admits_exact_canonical_match(self):
        harness = Harness()
        opportunity, listing, rv = harness.admit()
        version = harness.canonical_repo.version(opportunity.governing_source_version_key)
        document = build_projection_document(opportunity, listing, version, rv)
        decision = fence_candidate(
            IndexCandidate(document, 1.0), data_class="fixture", canonical_service=harness.canonical_service,
            canonical_repository=harness.canonical_repo, now=NOW,
        )
        self.assertEqual(decision, FenceDecision(True, None))


# ---------------------------------------------------------------------------
# M. Truth bindings (doc 16 §4)
# ---------------------------------------------------------------------------


class TruthBindingTests(RetrievalTestCase):
    def test_loading_copy_bound_to_topology_never_implies_live_source_checks(self):
        for (path, stage), copy in LOADING_COPY.items():
            self.assertIn(path, ("index", "canonical"))
            lowered = copy.lower()
            for phrase in FORBIDDEN_LOADING_PHRASES:
                self.assertNotIn(phrase, lowered)
        self.assertNotEqual(LOADING_COPY[("index", "retrieving")], LOADING_COPY[("canonical", "retrieving")])

    def test_serialized_payload_contains_no_score_probability_rank_or_relevance_key(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        dumped = json.dumps(
            {
                "result_key": page.result_key, "snapshot_key": page.snapshot_key, "coverage": page.coverage,
                "completeness": page.completeness, "disclosures": page.disclosures,
                "total_qualified": page.total_qualified, "total_broader": page.total_broader,
                "totals_are_lower_bound": page.totals_are_lower_bound, "entries": page.entries,
                "contract_version": page.contract_version,
            }
        )
        lowered = dumped.lower()
        for token in FORBIDDEN_SERIALIZATION_TOKENS:
            self.assertNotIn(token, lowered)

    def test_serialized_entry_fields_are_exactly_the_public_contract(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(set(page.entries[0]), PUBLIC_ENTRY_FIELDS)

    def test_freshness_serializes_success_and_attempt_timestamps_separately(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, _ = self.harness.search("alice", [term_op("python")])
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        projection = page.entries[0]["display_projection"]
        self.assertIn("last_successfully_verified_at", projection)
        self.assertIn("last_attempted_at", projection)
        self.assertIsNotNone(projection["last_successfully_verified_at"])
        self.assertIsNotNone(projection["last_attempted_at"])


# ---------------------------------------------------------------------------
# N. C5-integration contract (Python half); SQL/registry file-content test
# group follows below.
# ---------------------------------------------------------------------------


class C5IntegrationTests(RetrievalTestCase):
    def test_full_run_with_real_c3_c5_services_yields_fully_verified_entries(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final, receipt = self.harness.search("alice", [term_op("python")])
        self.assertEqual(final.state, "complete")
        page = self.harness.retrieval_service.results("alice", execution_key=final.execution_key, now=NOW)
        self.assertEqual(len(page.entries), 1)
        self.assertEqual(page.entries[0]["gate_outcome"], GATE_FULLY_VERIFIED)
        self.assertEqual(page.entries[0]["required_summary"]["verified"], page.entries[0]["required_summary"]["total"])

    def test_second_execution_reuses_c5_current_assessments_idempotently(self):
        opportunity, listing, rv = self.harness.admit()
        self.harness.grant("alice")
        self.harness.verify_all_items("alice", rv)
        final1, _ = self.harness.search("alice", [term_op("python")])
        assessment_count_after_first = len(self.harness.qual_repo._assessments)
        final2, _ = self.harness.search("alice", [term_op("python")])
        self.assertEqual(len(self.harness.qual_repo._assessments), assessment_count_after_first)
        snapshot1 = self.harness.retrieval_repo.snapshot_for_execution("alice", final1.execution_key)
        snapshot2 = self.harness.retrieval_repo.snapshot_for_execution("alice", final2.execution_key)
        self.assertEqual(
            {e.opportunity_key for e in snapshot1.entries}, {e.opportunity_key for e in snapshot2.entries}
        )

    def test_c5_contract_shapes_unchanged(self):
        params = set(inspect.signature(QualificationService.assess_requirements).parameters)
        self.assertEqual(
            params, {"self", "user_key", "spec", "member_context_text", "actor", "now"}
        )
        self.assertEqual(set(AssessmentRunResult.__dataclass_fields__), {"requirement_version_key", "assessments", "gate", "reused"})
        self.assertEqual(
            set(GateResult.__dataclass_fields__),
            {"requirement_version_key", "gate", "required_total", "required_verified", "non_verified_required", "label"},
        )
        error = AssessmentPersistenceError("item-1", "version-1")
        self.assertEqual(error.requirement_item_key, "item-1")
        self.assertEqual(error.requirement_version_key, "version-1")


# ---------------------------------------------------------------------------
# O. SQL / registry / verifier file-content tests (PS-MYOPP-004): mirrors
# QualificationMigrationTests.test_c5_migration_registry_and_verifier_are_bounded_and_gate_proven
# in tests/test_my_opportunities_qualification.py.
# ---------------------------------------------------------------------------

FORWARD_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-004_search_execution_results.sql"
ROLLBACK_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-004_search_execution_results_rollback.sql"
VERIFY_PATH = ROOT / "SQL FIles/Verification/PS-MYOPP-004_search_execution_results_verify.sql"
REGISTRY_PATH = ROOT / "SQL FIles/Migrations/registry.json"

_C4_TABLES = ("myopp_search_executions", "myopp_result_snapshots", "myopp_result_entries")
_SCORING_PATTERNS = ("score", "probab", "percent", "rank", "predict", "confidence", "match_rate", "relevance")
_COPIED_CONTENT_TOKENS = (
    "title", "employer", "location", "locations", "description",
    "compensation", "content", "body", "excerpt", "wording",
)


def _c4_table_body(sql: str, table: str) -> str:
    """The column/constraint block for one C4 table, bounded to the next
    CREATE TABLE, CREATE INDEX, or EXEC(trigger) statement -- so the scan
    never sweeps into the ledger INSERT or a later table's DDL even for the
    last table declared in the file (unlike a naive "to EOF" slice)."""
    start = sql.index(f"CREATE TABLE dbo.{table}")
    candidates = [
        sql.find("CREATE TABLE dbo.", start + 1),
        sql.find("CREATE INDEX ", start + 1),
        sql.find("EXEC(N'", start + 1),
    ]
    ends = [c for c in candidates if c != -1]
    end = min(ends) if ends else len(sql)
    return sql[start:end]


class RetrievalMigrationTests(unittest.TestCase):
    def test_c4_migration_registry_and_verifier_are_bounded_and_gate_proven(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        entry = next(item for item in registry["migrations"] if item["id"] == "PS-MYOPP-004")

        self.assertEqual(len([item for item in registry["migrations"] if item["id"] == "PS-MYOPP-004"]), 1)
        self.assertEqual(entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003"])
        self.assertEqual(entry["forward"], FORWARD_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(entry["rollback"], ROLLBACK_PATH.relative_to(ROOT).as_posix())

        # The disposable gate proof is recorded by the writer before merge
        # (blueprint C4_ARCHITECTURE.md 8.7); until then the entry carries
        # "gate": null and every assertion below on the populated proof is
        # expected to fail here -- that failure is the honest signal that the
        # gate has not been run yet, not a defect in this test (mirrors C5's
        # QualificationMigrationTests exactly).
        gate = entry["gate"]
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD_PATH))
        self.assertEqual(gate["prerequisites"], ["PS-PLAT-000", "PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003"])
        self.assertEqual(
            gate["verification"],
            "PS-MYOPP-004_search_execution_results_verify.sql returned verified = 1",
        )
        self.assertEqual(len(executable_sha256(FORWARD_PATH)), 64)

        # The gate must never point at a real database, and its
        # server/operator fields must actually be populated (not blank).
        self.assertTrue(gate["gate_database"])
        self.assertNotIn(gate["gate_database"], {"peerslate-database", "peerslate-staging"})
        self.assertTrue(gate["gate_server"])
        self.assertTrue(gate["operator"])

        for table in _C4_TABLES:
            self.assertIn(f"CREATE TABLE dbo.{table}", forward)
            self.assertIn(f"DROP TABLE dbo.{table};", rollback)
            self.assertIn(table, verify)
            body = _c4_table_body(forward, table)
            for pattern in _SCORING_PATTERNS:
                self.assertNotIn(pattern, body)

        self.assertIn("PS-MYOPP-004 requires PS-MYOPP-001", forward)
        self.assertIn("PS-MYOPP-004 requires PS-MYOPP-002", forward)
        self.assertIn("PS-MYOPP-004 requires PS-MYOPP-003", forward)
        self.assertIn("user_key nvarchar(300) NOT NULL", forward)
        self.assertIn("CK_myopp_search_executions_state", forward)
        self.assertIn("CK_myopp_search_executions_state_reason", forward)
        self.assertIn("CK_myopp_result_snapshots_completeness_reason", forward)
        self.assertIn("CK_myopp_result_entries_partition_gate", forward)

        entries_body = _c4_table_body(forward, "myopp_result_entries")
        for token in _COPIED_CONTENT_TOKENS:
            self.assertNotIn(token, entries_body)
        self.assertIn("myopp_governing_source_version_id", entries_body)
        self.assertIn("display_attribution_json", entries_body)
        self.assertIn("ordering_inputs_json", entries_body)

        self.assertIn("trg_myopp_search_executions_transition_guard", forward)
        self.assertIn("trg_myopp_result_snapshots_immutable", forward)
        self.assertIn("trg_myopp_result_entries_immutable", forward)

        self.assertIn("PS-MYOPP-004 is not recorded", rollback)
        self.assertIn("later migration is recorded", rollback)
        self.assertIn("C4 member data exists", rollback)

        self.assertIn("SELECT CAST(1 AS bit) AS verified", verify)
        self.assertIn("content-free", verify)
        self.assertIn("reference", verify)
        for pattern in _SCORING_PATTERNS:
            self.assertIn(f"%{pattern}%", verify)

    def test_c4_migration_state_and_reason_vocabulary_matches_module_constants(self):
        # Every enum literal the Python vocabulary module closes over must be
        # byte-equal (as an N'...' literal) to what the CHECK constraints
        # admit -- one vocabulary, per the blueprint.
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for group in (
            EXECUTION_STATES,
            FAILED_REASONS,
            PARTIAL_REASONS,
            CANCEL_REASONS,
            PARTITIONS,
            COMPLETENESS,
            SNAPSHOT_COVERAGE,
            STATUS_COVERAGE,
            RETRIEVAL_PATHS,
            {GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED},
        ):
            for value in group:
                self.assertIn(f"N'{value}'", forward, f"{value!r} missing from PS-MYOPP-004 forward DDL")

    def test_c4_rollback_refuses_on_member_data_and_later_ledger_rows_and_drops_in_dependency_order(self):
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        self.assertIn("PS-MYOPP-004 is not recorded", rollback)
        self.assertIn("later migration is recorded", rollback)
        self.assertIn("C4 member data exists", rollback)

        entries_index = rollback.index("DROP TABLE dbo.myopp_result_entries;")
        snapshots_index = rollback.index("DROP TABLE dbo.myopp_result_snapshots;")
        executions_index = rollback.index("DROP TABLE dbo.myopp_search_executions;")
        ledger_delete_index = rollback.index(
            "DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-004';"
        )

        self.assertLess(entries_index, snapshots_index)
        self.assertLess(snapshots_index, executions_index)
        self.assertLess(executions_index, ledger_delete_index)

    def test_c4_verifier_names_every_table_trigger_and_ends_with_verified_bit(self):
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        for table in _C4_TABLES:
            self.assertIn(table, verify)
        for trigger in (
            "trg_myopp_search_executions_transition_guard",
            "trg_myopp_result_snapshots_immutable",
            "trg_myopp_result_entries_immutable",
        ):
            self.assertIn(trigger, verify)
        verified_index = verify.index("SELECT CAST(1 AS bit) AS verified")
        # The verified row must be the terminal statement, not a mid-file check.
        self.assertGreater(verified_index, verify.index("THROW 55776"))

    def test_c4_throw_numbers_are_in_reserved_ranges_and_unique_repo_wide(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")

        forward_throws = {int(n) for n in re.findall(r"THROW (\d{5})", forward)}
        rollback_throws = {int(n) for n in re.findall(r"THROW (\d{5})", rollback)}
        verify_throws = {int(n) for n in re.findall(r"THROW (\d{5})", verify)}

        self.assertTrue(forward_throws)
        self.assertTrue(all(55720 <= n <= 55749 for n in forward_throws))
        self.assertTrue(rollback_throws)
        self.assertTrue(all(55750 <= n <= 55759 for n in rollback_throws))
        self.assertTrue(verify_throws)
        self.assertTrue(all(55760 <= n <= 55799 for n in verify_throws))

        # MINOR 11: intra-file reuse. The set-based checks above collapse
        # duplicate numbers within one file to a single member and would
        # never catch e.g. THROW 55770 appearing on three separate,
        # unrelated assertions in the same file -- count raw occurrences
        # per distinct message instead: two different THROW statements must
        # never share a number even inside the same file.
        for label, raw in (("forward", forward), ("rollback", rollback), ("verify", verify)):
            numbers = re.findall(r"THROW (\d{5})", raw)
            if len(numbers) != len(set(numbers)):
                duplicated = sorted({n for n in numbers if numbers.count(n) > 1})
                self.fail(f"{label} file reuses THROW number(s) {duplicated} across distinct assertions")

        # Repo-wide uniqueness: PS-MYOPP-004's own THROW numbers must not
        # collide with any OTHER tracked migration/verify file. This does
        # not assert that no two files anywhere share a number (a migration
        # and its own rollback are free to reuse a number between
        # themselves, as several already-merged packages do); it asserts
        # only that the newly claimed 55720-55799 block is genuinely unused
        # elsewhere, which is the actual collision risk the blueprint's
        # repo-wide THROW scan is guarding against.
        c4_numbers = forward_throws | rollback_throws | verify_throws
        c4_paths = {FORWARD_PATH, ROLLBACK_PATH, VERIFY_PATH}
        migrations_dir = ROOT / "SQL FIles" / "Migrations"
        verification_dir = ROOT / "SQL FIles" / "Verification"
        for path in sorted(migrations_dir.glob("*.sql")) + sorted(verification_dir.glob("*.sql")):
            if path in c4_paths:
                continue
            text = path.read_text(encoding="utf-8")
            other_numbers = {int(n) for n in re.findall(r"THROW (\d{5})", text)}
            collision = c4_numbers & other_numbers
            if collision:
                self.fail(f"THROW {sorted(collision)} claimed by PS-MYOPP-004 already used in {path.name}")

    def test_registry_entry_shape_and_requires(self):
        # The gate block starts null and is populated by the governed
        # disposable proof; the gate-proven test above asserts its populated
        # content, so this shape test accepts either lifecycle state rather
        # than pinning the pre-proof snapshot.
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        migrations = registry["migrations"]
        entries = [item for item in migrations if item["id"] == "PS-MYOPP-004"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(list(entry.keys()), ["id", "forward", "rollback", "requires", "summary", "gate"])
        self.assertEqual(entry["forward"], "SQL FIles/Migrations/PS-MYOPP-004_search_execution_results.sql")
        self.assertEqual(
            entry["rollback"], "SQL FIles/Migrations/PS-MYOPP-004_search_execution_results_rollback.sql"
        )
        self.assertEqual(entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003"])
        self.assertTrue(entry["gate"] is None or isinstance(entry["gate"], dict))
        self.assertIs(migrations[-1], entry)

    def test_no_forbidden_scoring_or_copied_content_column_in_c4_ddl(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for table in _C4_TABLES:
            body = _c4_table_body(forward, table)
            for pattern in _SCORING_PATTERNS:
                self.assertNotIn(pattern, body)
        entries_body = _c4_table_body(forward, "myopp_result_entries")
        for token in _COPIED_CONTENT_TOKENS:
            self.assertNotIn(token, entries_body)

    def test_registry_json_remains_well_formed_with_exactly_one_c4_entry(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertIn("migrations", registry)
        ids = [item["id"] for item in registry["migrations"]]
        self.assertEqual(ids.count("PS-MYOPP-004"), 1)

    def test_c4_snapshot_insert_backstop_requires_ordering_complete_or_partial_execution_state(self):
        """BLOCKER 1 SQL backstop: a myopp_result_snapshots row can only be
        inserted against an execution already in ordering/complete/partial
        -- a schema-level proof of the Python worker's write ordering."""
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        self.assertIn("AFTER INSERT, UPDATE, DELETE", forward)
        self.assertIn("THROW 55731", forward)
        backstop_index = forward.index("THROW 55731")
        trigger_start = forward.index("trg_myopp_result_snapshots_immutable")
        self.assertGreater(backstop_index, trigger_start)
        backstop_body = forward[trigger_start:backstop_index]
        self.assertIn("x.state NOT IN (N''ordering'', N''complete'', N''partial'')", backstop_body)
        self.assertIn("myopp_search_executions x", backstop_body)
        # The backstop must run before the pre-existing immutability check,
        # so a legitimate INSERT is never mistaken for a mutation of history.
        self.assertLess(backstop_index, forward.index("THROW 55728"))

    def test_c4_terminal_execution_row_guard_fires_on_any_update_not_only_state_changes(self):
        """IMPORTANT 8: the 55725 predicate no longer requires the state to
        have actually changed -- any update at all of an already-terminal
        row is refused."""
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        throw_index = forward.index("THROW 55725")
        # Bound the scan to the WHERE clause immediately preceding this
        # THROW (from the nearest prior IF EXISTS) so the check cannot be
        # satisfied by unrelated state-comparison text elsewhere in the file.
        clause_start = forward.rindex("IF EXISTS", 0, throw_index)
        clause = forward[clause_start:throw_index]
        self.assertIn("d.state IN (N''complete'', N''partial'', N''failed'', N''cancelled'')", clause)
        self.assertNotIn("i.state <> d.state", clause)
        self.assertIn("cannot be updated", forward)

    def test_c4_timestamp_check_orders_terminal_at_after_every_stage(self):
        """MINOR 12: terminal_at_utc must be >= every non-null stage
        timestamp, not only internally ordered among the stages themselves."""
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for stage_column in ("retrieving_at_utc", "assessing_at_utc", "ordering_at_utc"):
            self.assertIn(f"terminal_at_utc >= {stage_column}", forward)

    def test_c4_entries_and_snapshots_pair_data_class_through_to_the_execution(self):
        """MINOR 13: the entries->snapshots and snapshot->execution FKs
        additionally pair data_class end to end, not only user_key."""
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        self.assertIn("UQ_myopp_search_executions_id_user_class", forward)
        self.assertIn("UQ_myopp_result_snapshots_id_user_class", forward)
        self.assertIn(
            "FOREIGN KEY (myopp_search_execution_id, user_key, data_class)\n"
            "                REFERENCES dbo.myopp_search_executions (myopp_search_execution_id, user_key, data_class)",
            forward,
        )
        self.assertIn(
            "FOREIGN KEY (myopp_result_snapshot_id, user_key, data_class)\n"
            "                REFERENCES dbo.myopp_result_snapshots (myopp_result_snapshot_id, user_key, data_class)",
            forward,
        )
        self.assertIn("FK_myopp_result_snapshots_execution_owner", verify)
        self.assertIn("FK_myopp_result_entries_snapshot_owner", verify)

    def test_c4_entries_trigger_ignores_a_zero_row_update(self):
        """MINOR 18: consistent with the snapshots trigger, the entries
        immutability trigger only throws when rows were actually touched."""
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        trigger_start = forward.index("trg_myopp_result_entries_immutable")
        trigger_body = forward[trigger_start : forward.index("END')", trigger_start)]
        self.assertIn("IF EXISTS (SELECT 1 FROM inserted)", trigger_body)
        self.assertIn("THROW 55730", trigger_body)
