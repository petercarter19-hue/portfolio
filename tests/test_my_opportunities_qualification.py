from __future__ import annotations

import json
import random
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scripts.migration_registry import executable_body, executable_sha256
from services.my_opportunities.evidence_port import (
    EVIDENCE_CLASS_WORKSHOP,
    EvidencePortError,
    EvidenceRecord,
    InMemoryEvidencePort,
    WorkshopEvidencePort,
)
from services.my_opportunities.qualification_service import (
    ACTORS,
    AdmittedRecord,
    Assessment,
    AssessmentPersistenceError,
    AssessmentProposalSet,
    AssessmentProposalTimeout,
    AssessmentProposalUnavailable,
    EvidenceClaim,
    EvidenceGrant,
    FailingQualificationRepository,
    GATE_FULLY_VERIFIED,
    GATE_NOT_FULLY_VERIFIED,
    GRANT_PURPOSE,
    GrantScope,
    InMemoryAuditSink,
    InMemoryQualificationRepository,
    ProposalContractError,
    QualificationService,
    QualificationServiceError,
    RequirementConstraints,
    RequirementItemSpec,
    RequirementVersionSpec,
    STATE_APPEARS_UNMET,
    STATE_NOT_ESTABLISHED,
    STATE_REVIEW_UNAVAILABLE,
    STATE_VERIFIED,
    UnavailableAssessmentProvider,
    _derive_gate,
    _gate_label,
    _validate_proposal,
    evaluate_item,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _item(
    key,
    ordinal,
    clause,
    *,
    requirement_class="required",
    classification_basis="stated_required",
    constraints=None,
    reading_flagged=False,
):
    return RequirementItemSpec(
        requirement_item_key=key,
        ordinal=ordinal,
        normalized_clause=clause,
        requirement_class=requirement_class,
        classification_basis=classification_basis,
        constraints=constraints or RequirementConstraints(),
        reading_flagged=reading_flagged,
    )


def _spec(items, *, version_key="version-1", opportunity_key="opportunity-1"):
    return RequirementVersionSpec(
        requirement_version_key=version_key,
        opportunity_key=opportunity_key,
        items=tuple(items),
    )


def _firm_record(
    key,
    *,
    title="Platform engineering role",
    body="Five years building distributed systems in Python.",
    updated_at=NOW,
    version=1,
    time_span=None,
):
    return EvidenceRecord(
        evidence_key=key,
        evidence_class=EVIDENCE_CLASS_WORKSHOP,
        version=version,
        title=title,
        body=body,
        updated_at=updated_at,
        strength="firm",
        time_span=time_span,
    )


def _candidate_record(key, *, title="Draft note", body="Unconfirmed note.", updated_at=NOW, version=1):
    return EvidenceRecord(
        evidence_key=key,
        evidence_class=EVIDENCE_CLASS_WORKSHOP,
        version=version,
        title=title,
        body=body,
        updated_at=updated_at,
        strength="candidate",
        time_span=None,
    )


def _claim(item_key, record, *, relation="supports", time_span=None, credential_name=None):
    return EvidenceClaim(
        requirement_item_key=item_key,
        evidence_key=record.evidence_key,
        evidence_class=record.evidence_class,
        evidence_version=record.version,
        relation=relation,
        time_span=time_span,
        credential_name=credential_name,
    )


class FixtureAssessmentProvider:
    """Deterministic canned claims, keyed by requirement item key.

    ``claims_by_item`` maps ``requirement_item_key -> Sequence[EvidenceClaim]``.
    Only claims for items actually present in the prompt are ever returned
    (mirrors a real provider only ever answering about what it was asked).
    """

    def __init__(self, claims_by_item=None, *, fail_with=None, hook=None):
        self.claims_by_item = dict(claims_by_item or {})
        self.fail_with = fail_with  # "unavailable" | "timeout" | "error" | None
        self.hook = hook  # optional callable(prompt) invoked before responding
        self.calls = []  # recorded FencedAssessmentPrompt objects

    def propose(self, prompt):
        self.calls.append(prompt)
        if self.hook is not None:
            self.hook(prompt)
        if self.fail_with == "unavailable":
            raise AssessmentProposalUnavailable("fixture_down")
        if self.fail_with == "timeout":
            raise AssessmentProposalTimeout("fixture_slow")
        if self.fail_with == "error":
            raise RuntimeError("fixture_boom")
        item_keys = {item_key for item_key, _clause in prompt.requirement_items}
        admitted_triples = {
            (record.evidence_key, record.evidence_class, record.version)
            for record in prompt.evidence_records
        }
        claims = []
        for item_key in item_keys:
            for claim in self.claims_by_item.get(item_key, ()):
                # A real provider only ever proposes about evidence it was
                # actually shown -- never about another member's record that
                # happens to share this fixture's canned claim table.
                triple = (claim.evidence_key, claim.evidence_class, claim.evidence_version)
                if triple in admitted_triples:
                    claims.append(claim)
        return AssessmentProposalSet(claims=tuple(claims))


class RawProvider:
    """Returns a caller-supplied raw proposal verbatim (for contract-violation
    and shape-refusal tests)."""

    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def propose(self, prompt):
        del prompt
        self.calls += 1
        return self.proposal


class SpyEvidencePort:
    def __init__(self, inner):
        self._inner = inner
        self.evidence_class = inner.evidence_class
        self.calls = 0

    def list_records_for_owner(self, user_key, *, max_items=24):
        self.calls += 1
        return self._inner.list_records_for_owner(user_key, max_items=max_items)


class SpyProvider:
    def __init__(self, inner):
        self._inner = inner
        self.calls = 0

    def propose(self, prompt):
        self.calls += 1
        return self._inner.propose(prompt)


class SwitchableProvider:
    """Test-only indirection so a single service instance can be repointed
    at a different provider mid-test (e.g. AI comes back up between calls)."""

    def __init__(self, provider):
        self._provider = provider

    def set(self, provider):
        self._provider = provider

    def propose(self, prompt):
        return self._provider.propose(prompt)


def _grant_scope(*, record_keys=None, classes=(EVIDENCE_CLASS_WORKSHOP,)):
    return GrantScope(evidence_classes=frozenset(classes), record_keys=record_keys)


def _admitted_map(records, grant_key="grant-x"):
    return {
        (record.evidence_key, record.evidence_class, record.version): AdmittedRecord(
            record=record, admitting_grant_key=grant_key
        )
        for record in records
    }


class QualificationServiceTestCase(unittest.TestCase):
    """Common harness: fresh repository, in-memory port, fixture provider."""

    def setUp(self):
        self.repository = InMemoryQualificationRepository()
        self.audit = InMemoryAuditSink()

    def build_service(self, *, records_by_owner=None, port_fail_with=None, provider=None, ports=None):
        port = InMemoryEvidencePort(records_by_owner or {}, fail_with=port_fail_with)
        self.port = port
        self.provider = provider if provider is not None else FixtureAssessmentProvider()
        self.service = QualificationService(
            self.repository,
            evidence_ports=ports if ports is not None else {EVIDENCE_CLASS_WORKSHOP: port},
            provider=self.provider,
            audit_sink=self.audit,
        )
        return self.service

    def grant(self, service, user_key, *, scope=None, expires_at=None, key="grant-1", now=NOW):
        return service.create_grant(
            user_key,
            scope=scope or _grant_scope(),
            expires_at=expires_at or (now + timedelta(days=30)),
            idempotency_key=key,
            now=now,
        )


# ---------------------------------------------------------------------------
# A. Grants
# ---------------------------------------------------------------------------


class GrantTests(QualificationServiceTestCase):
    def test_create_grant_fixed_purpose_scope_expiry_and_inspection(self):
        service = self.build_service()
        scope = _grant_scope()
        grant = self.grant(service, "member-a", scope=scope)

        self.assertEqual(grant.purpose, GRANT_PURPOSE)
        self.assertEqual(grant.scope, scope)
        self.assertEqual(grant.state(NOW), "granted")

        self.assertEqual(service.list_grants("member-a"), (grant,))
        self.assertEqual(service.get_grant("member-a", grant.grant_key), grant)

        with self.assertRaises(ValueError):
            EvidenceGrant(
                grant_key="bad-purpose",
                user_key="member-a",
                purpose="something_else",
                scope=scope,
                granted_at=NOW,
                expires_at=NOW + timedelta(days=1),
                revoked_at=None,
            )

    def test_create_grant_refuses_invalid_scope_and_expiry(self):
        service = self.build_service()

        with self.assertRaises(QualificationServiceError) as empty_classes:
            service.create_grant(
                "member-a",
                scope=GrantScope(evidence_classes=frozenset()),
                expires_at=NOW + timedelta(days=1),
                idempotency_key="k1",
                now=NOW,
            )
        self.assertEqual(empty_classes.exception.failure_code, "scope_invalid")

        with self.assertRaises(QualificationServiceError) as unknown_class:
            service.create_grant(
                "member-a",
                scope=GrantScope(evidence_classes=frozenset({"bogus_class"})),
                expires_at=NOW + timedelta(days=1),
                idempotency_key="k2",
                now=NOW,
            )
        self.assertEqual(unknown_class.exception.failure_code, "scope_invalid")

        with self.assertRaises(QualificationServiceError) as empty_keys:
            service.create_grant(
                "member-a",
                scope=_grant_scope(record_keys=frozenset()),
                expires_at=NOW + timedelta(days=1),
                idempotency_key="k3",
                now=NOW,
            )
        self.assertEqual(empty_keys.exception.failure_code, "scope_invalid")

        with self.assertRaises(QualificationServiceError) as past_expiry:
            service.create_grant(
                "member-a",
                scope=_grant_scope(),
                expires_at=NOW - timedelta(days=1),
                idempotency_key="k4",
                now=NOW,
            )
        self.assertEqual(past_expiry.exception.failure_code, "expiry_invalid")

        with self.assertRaises(QualificationServiceError) as naive_expiry:
            service.create_grant(
                "member-a",
                scope=_grant_scope(),
                expires_at=datetime(2026, 9, 30, 0, 0),
                idempotency_key="k5",
                now=NOW,
            )
        self.assertEqual(naive_expiry.exception.failure_code, "expiry_invalid")

    def test_grant_expiry_is_derived_and_terminal(self):
        service = self.build_service()
        grant = self.grant(service, "member-a", expires_at=NOW + timedelta(hours=1))

        self.assertEqual(grant.state(NOW), "granted")
        later = NOW + timedelta(hours=2)
        self.assertEqual(grant.state(later), "expired")

        with self.assertRaises(QualificationServiceError) as caught:
            service.revoke_grant(
                "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=later
            )
        self.assertEqual(caught.exception.failure_code, "grant_terminal")

        second = self.grant(service, "member-a", key="grant-2", now=later)
        self.assertNotEqual(second.grant_key, grant.grant_key)

    def test_revoke_grant_is_one_way_and_idempotency_replay_safe(self):
        service = self.build_service()
        grant = self.grant(service, "member-a")

        outcome = service.revoke_grant(
            "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=1)
        )
        self.assertIsNotNone(outcome.grant.revoked_at)

        replay = service.revoke_grant(
            "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=2)
        )
        self.assertEqual(replay, outcome)

        second_grant = self.grant(service, "member-a", key="grant-2", now=NOW + timedelta(minutes=1))
        with self.assertRaises(QualificationServiceError) as mismatch:
            service.revoke_grant(
                "member-a",
                grant_key=second_grant.grant_key,
                idempotency_key="revoke-1",
                now=NOW + timedelta(minutes=3),
            )
        self.assertEqual(mismatch.exception.failure_code, "idempotency_mismatch")

        with self.assertRaises(QualificationServiceError) as terminal:
            service.revoke_grant(
                "member-a", grant_key=grant.grant_key, idempotency_key="revoke-again", now=NOW + timedelta(minutes=4)
            )
        self.assertEqual(terminal.exception.failure_code, "grant_terminal")

    def test_grant_commands_are_idempotent_with_c3_precedence(self):
        service = self.build_service()
        first = self.grant(service, "member-a", key="create-1")
        replay = self.grant(service, "member-a", key="create-1")
        self.assertEqual(first, replay)

        before = self.repository.state_digest()
        with self.assertRaises(QualificationServiceError) as mismatch:
            service.create_grant(
                "member-a",
                scope=_grant_scope(record_keys=frozenset({"only-this-one"})),
                expires_at=NOW + timedelta(days=30),
                idempotency_key="create-1",
                now=NOW,
            )
        self.assertEqual(mismatch.exception.failure_code, "idempotency_mismatch")
        self.assertEqual(self.repository.state_digest(), before)


# ---------------------------------------------------------------------------
# B. Authorization boundary (no grant / insufficient scope)
# ---------------------------------------------------------------------------


class AuthorizationBoundaryTests(QualificationServiceTestCase):
    def test_no_grant_means_not_established_no_evidence_in_scope_and_no_port_or_ai_call(self):
        record = _firm_record("evidence-1")
        raw_port = InMemoryEvidencePort({"member-a": (record,)})
        spy_port = SpyEvidencePort(raw_port)
        raw_provider = FixtureAssessmentProvider(
            {"item-1": (_claim("item-1", record),)}
        )
        spy_provider = SpyProvider(raw_provider)
        service = QualificationService(
            self.repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: spy_port},
            provider=spy_provider,
            audit_sink=self.audit,
        )
        spec = _spec([_item("item-1", 1, "Five years of Python")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        self.assertEqual(len(result.assessments), 1)
        self.assertEqual(result.assessments[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(result.assessments[0].reason_code, "no_evidence_in_scope")
        self.assertEqual(spy_port.calls, 0)
        self.assertEqual(spy_provider.calls, 0)

    def test_insufficient_scope_record_allowlist_excludes_evidence(self):
        record = _firm_record("evidence-1")
        raw_port = InMemoryEvidencePort({"member-a": (record,)})
        spy_port = SpyEvidencePort(raw_port)
        raw_provider = FixtureAssessmentProvider(
            {"item-1": (_claim("item-1", record),)}
        )
        spy_provider = SpyProvider(raw_provider)
        service = QualificationService(
            self.repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: spy_port},
            provider=spy_provider,
            audit_sink=self.audit,
        )
        self.grant(service, "member-a", scope=_grant_scope(record_keys=frozenset({"some-other-record"})))
        spec = _spec([_item("item-1", 1, "Five years of Python")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        self.assertEqual(result.assessments[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(result.assessments[0].reason_code, "no_evidence_in_scope")
        self.assertEqual(result.assessments[0].evidence_links, ())
        self.assertGreaterEqual(spy_port.calls, 1)
        self.assertEqual(spy_provider.calls, 0)

    def test_cross_purpose_reuse_impossible_by_construction(self):
        service = self.build_service()
        public_methods = {
            name
            for name in dir(service)
            if not name.startswith("_") and callable(getattr(service, name))
        }
        # No generic "read evidence" surface exists: evidence only ever
        # reaches a caller through a qualification_verification-scoped
        # grant and the admitted-evidence pipeline inside assess_requirements
        # / the recompute paths.
        forbidden = {"read_evidence", "list_evidence", "get_evidence", "evidence_for_owner"}
        self.assertEqual(public_methods & forbidden, set())


# ---------------------------------------------------------------------------
# C. Deterministic evaluation (P-1 gate fixtures)
# ---------------------------------------------------------------------------


class EvaluateItemTests(unittest.TestCase):
    def test_firm_direct_evidence_verifies_with_direct_evidence_reason(self):
        record = _firm_record("r1")
        item = _item("item-1", 1, "Five years of Python")
        claims = (_claim("item-1", record),)

        state, reason, links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "direct_evidence")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].reference.evidence_key, "r1")

    def test_one_explicit_firm_record_suffices_no_two_record_rule(self):
        record = _firm_record("solo-record")
        item = _item("item-1", 1, "Direct experience with distributed systems")
        claims = (_claim("item-1", record),)

        state, reason, _links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        # Policy rule 3: no blanket two-record rule -- one explicit firm
        # record may suffice.
        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "direct_evidence")

    def test_candidate_evidence_never_verifies(self):
        record = _candidate_record("draft-1")
        item = _item("item-1", 1, "Five years of Python")
        claims = (_claim("item-1", record),)

        state, reason, links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "candidate_evidence_only")
        self.assertEqual(len(links), 1)

    def test_partial_relation_alone_is_partial_evidence(self):
        record = _firm_record("r1")
        item = _item("item-1", 1, "Five years of Python")
        claims = (_claim("item-1", record, relation="partial"),)

        state, reason, _links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "partial_evidence")

    def test_ambiguous_mixture_is_ambiguous_evidence(self):
        supporting = _firm_record("support-1")
        contradicting = _firm_record("contradict-1")
        item = _item("item-1", 1, "Five years of Python")
        claims = (
            _claim("item-1", supporting, relation="supports"),
            _claim("item-1", contradicting, relation="contradicts"),
        )

        state, reason, links = evaluate_item(
            item, claims, _admitted_map((supporting, contradicting)), evaluation_time=NOW
        )

        # Mixed-signals rule (§0.3): firm confirming evidence AND firm
        # affirmative contradiction together -> ambiguous, never verified.
        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "ambiguous_evidence")
        self.assertEqual(
            {link.reference.evidence_key for link in links}, {"support-1", "contradict-1"}
        )

    def test_contradiction_requires_affirmative_firm_evidence(self):
        firm_contradiction = _firm_record("contra-firm")
        item = _item("item-1", 1, "Five years of Python")
        state, reason, links = evaluate_item(
            item,
            (_claim("item-1", firm_contradiction, relation="contradicts"),),
            _admitted_map((firm_contradiction,)),
            evaluation_time=NOW,
        )
        self.assertEqual(state, STATE_APPEARS_UNMET)
        self.assertEqual(reason, "affirmative_contradiction")
        self.assertEqual(len(links), 1)

        candidate_contradiction = _candidate_record("contra-candidate")
        state2, reason2, _links2 = evaluate_item(
            item,
            (_claim("item-1", candidate_contradiction, relation="contradicts"),),
            _admitted_map((candidate_contradiction,)),
            evaluation_time=NOW,
        )
        self.assertNotEqual(state2, STATE_APPEARS_UNMET)
        self.assertEqual(state2, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason2, "candidate_evidence_only")

    def test_mixed_support_and_contradiction_is_ambiguous_never_verified_never_unmet(self):
        constraints = RequirementConstraints(minimum_duration_months=24)
        item = _item("item-1", 1, "At least two years of experience", constraints=constraints)
        support_a = _firm_record("dur-a")
        support_b = _firm_record("dur-b")
        contradiction = _firm_record("dur-contra")
        claims = (
            _claim("item-1", support_a, relation="supports", time_span=(date(2015, 1, 1), date(2018, 1, 1))),
            _claim("item-1", support_b, relation="supports", time_span=(date(2018, 1, 1), date(2020, 1, 1))),
            _claim("item-1", contradiction, relation="contradicts"),
        )

        state, reason, _links = evaluate_item(
            item,
            claims,
            _admitted_map((support_a, support_b, contradiction)),
            evaluation_time=NOW,
        )

        self.assertNotIn(state, (STATE_VERIFIED, STATE_APPEARS_UNMET))
        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "ambiguous_evidence")

    def test_absence_of_evidence_is_not_established_never_negative(self):
        from services.my_opportunities.qualification_service import _member_explanation

        item = _item("item-1", 1, "Five years of Python")
        state, reason, links = evaluate_item(item, (), {}, evaluation_time=NOW)

        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "no_evidence_in_scope")
        self.assertEqual(links, ())
        self.assertIn("does not mean you lack", _member_explanation(state, reason))

    def test_duration_aggregates_dated_records_with_overlap_merge(self):
        constraints = RequirementConstraints(minimum_duration_months=84)  # 7 years
        item = _item("item-1", 1, "At least seven years of experience", constraints=constraints)
        record_a = _firm_record("dur-a")
        record_b = _firm_record("dur-b")
        record_c = _firm_record("dur-c")
        claims = (
            _claim("item-1", record_a, time_span=(date(2013, 1, 1), date(2016, 1, 1))),
            # Overlaps record_a by one year (2015-2016); overlap must be
            # counted once, not double-counted.
            _claim("item-1", record_b, time_span=(date(2015, 1, 1), date(2019, 1, 1))),
            # Disjoint/adjacent tail.
            _claim("item-1", record_c, time_span=(date(2019, 1, 1), date(2020, 1, 1))),
        )

        state, reason, links = evaluate_item(
            item, claims, _admitted_map((record_a, record_b, record_c)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "corroborated")
        self.assertGreaterEqual(len({link.reference.evidence_key for link in links}), 2)

    def test_duration_shortfall_is_partial_evidence(self):
        constraints = RequirementConstraints(minimum_duration_months=60)  # 5 years
        item = _item("item-1", 1, "At least five years of experience", constraints=constraints)
        record = _firm_record("short-tenure")
        claims = (_claim("item-1", record, time_span=(date(2022, 1, 1), date(2024, 1, 1))),)  # 2 years

        state, reason, _links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "partial_evidence")

    def test_undated_claims_never_count_toward_duration(self):
        constraints = RequirementConstraints(minimum_duration_months=12)
        item = _item("item-1", 1, "At least a year of experience", constraints=constraints)
        record = _firm_record("undated")  # no time_span
        claims = (_claim("item-1", record),)  # claim also carries no time_span

        state, reason, _links = evaluate_item(
            item, claims, _admitted_map((record,)), evaluation_time=NOW
        )

        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "partial_evidence")

    def test_named_credential_rule(self):
        constraints = RequirementConstraints(credential_names=("PMP",))
        item = _item("item-1", 1, "Holds a PMP credential", constraints=constraints)
        matching = _firm_record("cred-match")
        state, reason, _links = evaluate_item(
            item,
            (_claim("item-1", matching, credential_name="pmp"),),
            _admitted_map((matching,)),
            evaluation_time=NOW,
        )
        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "direct_evidence")

        unnamed = _firm_record("cred-unnamed")
        state2, reason2, _links2 = evaluate_item(
            item, (_claim("item-1", unnamed),), _admitted_map((unnamed,)), evaluation_time=NOW
        )
        self.assertEqual(state2, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason2, "partial_evidence")

        mismatched = _firm_record("cred-mismatch")
        state3, reason3, _links3 = evaluate_item(
            item,
            (_claim("item-1", mismatched, credential_name="CAPM"),),
            _admitted_map((mismatched,)),
            evaluation_time=NOW,
        )
        self.assertEqual(state3, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason3, "partial_evidence")

    def test_recency_window_applies_only_when_posting_establishes_one(self):
        record = _firm_record("stale-evidence")
        old_span = (date(2005, 1, 1), date(2007, 1, 1))
        claim = _claim("item-1", record, time_span=old_span)

        windowed = _item(
            "item-1", 1, "Recent experience",
            constraints=RequirementConstraints(recency_window_months=24),
        )
        state, reason, _links = evaluate_item(
            windowed, (claim,), _admitted_map((record,)), evaluation_time=NOW
        )
        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "temporal_mismatch")

        unwindowed = _item("item-1", 1, "Experience, any time")
        state2, reason2, _links2 = evaluate_item(
            unwindowed, (claim,), _admitted_map((record,)), evaluation_time=NOW
        )
        self.assertEqual(state2, STATE_VERIFIED)
        self.assertEqual(reason2, "direct_evidence")

    def test_alternative_path_met_reason(self):
        # Base constraint (a named credential) is unmet, but a plain
        # alternative path (any firm supporting record) is satisfied.
        constraints = RequirementConstraints(
            credential_names=("PMP",), alternative_paths=(RequirementConstraints(),)
        )
        item = _item("item-1", 1, "PMP or equivalent plain experience", constraints=constraints)
        record = _firm_record("alt-record")
        state, reason, _links = evaluate_item(
            item, (_claim("item-1", record),), _admitted_map((record,)), evaluation_time=NOW
        )
        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "alternative_path_met")

    def test_reading_flagged_item_is_classification_ambiguous(self):
        record = _firm_record("flagged-record")
        item = _item("item-1", 1, "Ambiguous clause", reading_flagged=True)
        state, reason, links = evaluate_item(
            item, (_claim("item-1", record),), _admitted_map((record,)), evaluation_time=NOW
        )
        self.assertEqual(state, STATE_NOT_ESTABLISHED)
        self.assertEqual(reason, "classification_ambiguous")
        self.assertEqual(links, ())

    def test_ambiguous_default_required_item_verifies_normally_but_gates_as_required(self):
        record = _firm_record("default-required")
        item = _item(
            "item-1",
            1,
            "Ambiguous placement, defaults required",
            requirement_class="required",
            classification_basis="ambiguous_default_required",
        )
        state, reason, _links = evaluate_item(
            item, (_claim("item-1", record),), _admitted_map((record,)), evaluation_time=NOW
        )
        self.assertEqual(state, STATE_VERIFIED)
        self.assertEqual(reason, "direct_evidence")

        from services.my_opportunities.qualification_service import Assessment, _derive_gate

        assessment = Assessment(
            assessment_key="a1",
            user_key="member-a",
            requirement_item_key="item-1",
            requirement_version_key="version-1",
            assessment_type=item.requirement_class,
            state=state,
            reason_code=reason,
            current_revision_number=1,
            evidence_links=(),
            assessed_at=NOW,
            member_explanation="x",
        )
        gate = _derive_gate(_spec([item]), (assessment,))
        self.assertEqual(gate.gate, GATE_FULLY_VERIFIED)
        self.assertEqual(gate.required_total, 1)
        self.assertEqual(gate.required_verified, 1)

    def test_evaluation_is_deterministic_across_claim_orderings(self):
        constraints = RequirementConstraints(minimum_duration_months=36)
        item = _item("item-1", 1, "Three years combined", constraints=constraints)
        record_a = _firm_record("shuffle-a")
        record_b = _firm_record("shuffle-b")
        record_c = _candidate_record("shuffle-c")
        claims = [
            _claim("item-1", record_a, time_span=(date(2018, 1, 1), date(2020, 1, 1))),
            _claim("item-1", record_b, time_span=(date(2020, 1, 1), date(2022, 6, 1))),
            _claim("item-1", record_c),
        ]
        admitted = _admitted_map((record_a, record_b, record_c))

        baseline = evaluate_item(item, tuple(claims), admitted, evaluation_time=NOW)
        rng = random.Random(1234)
        for _ in range(5):
            shuffled = list(claims)
            rng.shuffle(shuffled)
            result = evaluate_item(item, tuple(shuffled), admitted, evaluation_time=NOW)
            self.assertEqual(result, baseline)


# ---------------------------------------------------------------------------
# D. Gate derivation
# ---------------------------------------------------------------------------


class GateDerivationTests(QualificationServiceTestCase):
    def test_gate_fully_verified_iff_every_required_item_verified(self):
        record_1 = _firm_record("gate-r1")
        record_2 = _firm_record("gate-r2")
        provider = FixtureAssessmentProvider(
            {
                "req-1": (_claim("req-1", record_1),),
                "req-2": (_claim("req-2", record_2),),
            }
        )
        service = self.build_service(
            records_by_owner={"member-a": (record_1, record_2)}, provider=provider
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python"), _item("req-2", 2, "SQL")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.gate.gate, GATE_FULLY_VERIFIED)
        self.assertEqual(result.gate.label, "Fully verified")

        # A different version where one required item never verifies.
        spec_b = _spec(
            [_item("req-1", 1, "Python"), _item("req-3", 2, "Kubernetes")],
            version_key="version-2",
        )
        result_b = service.assess_requirements("member-a", spec=spec_b, now=NOW)
        self.assertEqual(result_b.gate.gate, GATE_NOT_FULLY_VERIFIED)

    def test_single_review_unavailable_blocks_gate_with_truthful_label(self):
        down = FixtureAssessmentProvider(fail_with="unavailable")
        switch = SwitchableProvider(down)
        records = tuple(_firm_record(f"label-r{i}") for i in range(1, 6))
        service = self.build_service(
            records_by_owner={"member-a": records}, provider=switch
        )
        self.grant(service, "member-a")
        items = [_item(f"req-{i}", i, f"Requirement {i}") for i in range(1, 7)]
        spec = _spec(items)

        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertTrue(all(a.state == STATE_REVIEW_UNAVAILABLE for a in result.assessments))

        working = FixtureAssessmentProvider(
            {f"req-{i}": (_claim(f"req-{i}", records[i - 1]),) for i in range(1, 6)}
        )
        switch.set(working)
        for i in range(1, 6):
            service.retry_assessment(
                "member-a", spec=spec, requirement_item_key=f"req-{i}", now=NOW + timedelta(minutes=i)
            )

        gate = service.derive_gate("member-a", spec=spec)
        self.assertEqual(gate.gate, GATE_NOT_FULLY_VERIFIED)
        self.assertEqual(gate.required_verified, 5)
        self.assertEqual(gate.required_total, 6)
        self.assertEqual(gate.label, "5 of 6 required verified · 1 review unavailable")

    def test_preferred_items_never_affect_gate_in_either_direction(self):
        required_record = _firm_record("pref-required")
        preferred_record = _firm_record("pref-preferred")
        provider = FixtureAssessmentProvider(
            {"req-1": (_claim("req-1", required_record),)}
        )
        service = self.build_service(
            records_by_owner={"member-a": (required_record, preferred_record)}, provider=provider
        )
        self.grant(service, "member-a")
        spec_failed_preferred = _spec(
            [_item("req-1", 1, "Python"), _item("pref-1", 2, "Rust", requirement_class="preferred")]
        )
        result = service.assess_requirements("member-a", spec=spec_failed_preferred, now=NOW)
        preferred = next(a for a in result.assessments if a.requirement_item_key == "pref-1")
        self.assertNotEqual(preferred.state, STATE_VERIFIED)
        self.assertEqual(result.gate.gate, GATE_FULLY_VERIFIED)
        self.assertEqual(result.gate.required_total, 1)

        provider2 = FixtureAssessmentProvider(
            {
                "req-1": (_claim("req-1", required_record),),
                "pref-1": (_claim("pref-1", preferred_record),),
            }
        )
        service2 = self.build_service(
            records_by_owner={"member-a": (required_record, preferred_record)}, provider=provider2
        )
        self.grant(service2, "member-a")
        spec_verified_preferred = _spec(
            [_item("req-1", 1, "Python"), _item("pref-1", 2, "Rust", requirement_class="preferred")],
            version_key="version-2",
        )
        result2 = service2.assess_requirements("member-a", spec=spec_verified_preferred, now=NOW)
        preferred2 = next(a for a in result2.assessments if a.requirement_item_key == "pref-1")
        self.assertEqual(preferred2.state, STATE_VERIFIED)
        self.assertEqual(result2.gate.gate, GATE_FULLY_VERIFIED)
        self.assertEqual(result2.gate.required_total, 1)
        self.assertEqual(result2.gate.required_verified, 1)

    def test_practical_fit_never_affects_gate_or_assessments(self):
        record = _firm_record("fit-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])

        before = service.assess_requirements("member-a", spec=spec, now=NOW)
        before_digest = self.repository.state_digest()
        before_grants = dict(self.repository._grants)
        before_assessments = dict(self.repository._assessments)
        before_revisions = {key: tuple(items) for key, items in self.repository._revisions.items()}

        service.record_practical_fit(
            "member-a",
            opportunity_key="opportunity-1",
            note_text="This commute would be rough for me.",
            idempotency_key="fit-1",
            now=NOW + timedelta(minutes=1),
        )
        service.record_practical_fit(
            "member-a",
            opportunity_key="opportunity-1",
            note_text="Actually the team culture sounds great.",
            idempotency_key="fit-2",
            now=NOW + timedelta(minutes=2),
        )

        after = service.assess_requirements("member-a", spec=spec, now=NOW + timedelta(minutes=3))
        self.assertEqual(after.assessments, before.assessments)
        self.assertEqual(after.gate, before.gate)
        gate_only = service.derive_gate("member-a", spec=spec)
        self.assertEqual(gate_only, before.gate)
        # Assessment/grant state is untouched; only the idempotency ledger
        # and the new practical-fit rows differ.
        self.assertNotEqual(self.repository.state_digest(), before_digest)
        self.assertEqual(dict(self.repository._grants), before_grants)
        self.assertEqual(dict(self.repository._assessments), before_assessments)
        self.assertEqual(
            {key: tuple(items) for key, items in self.repository._revisions.items()}, before_revisions
        )

    def test_no_score_probability_or_ranking_fields_anywhere(self):
        import services.my_opportunities.evidence_port as ep
        import services.my_opportunities.qualification_service as qs
        from dataclasses import fields, is_dataclass

        forbidden = ("score", "probab", "percent", "rank", "predict", "confidence", "match_rate")
        checked = 0
        for module in (qs, ep):
            for name in module.__all__:
                value = getattr(module, name)
                if not (isinstance(value, type) and is_dataclass(value)):
                    continue
                checked += 1
                for field in fields(value):
                    lowered = field.name.lower()
                    for token in forbidden:
                        self.assertNotIn(
                            token, lowered, f"{module.__name__}.{name}.{field.name} looks like a forbidden scoring field"
                        )
        self.assertGreater(checked, 0)

        # The migration file's own column scan (deferred until the SQL trio
        # exists): scan the executable body only -- the leading block comment
        # legitimately names these same tokens ("no score/probability/ranking
        # field anywhere") and must not trip the scan.
        forward_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-003_qualification.sql"
        forward_sql = executable_body(forward_path.read_text(encoding="utf-8")).lower()
        for token in forbidden:
            self.assertNotIn(
                token, forward_sql, f"migration file contains a forbidden scoring token: {token}"
            )


# ---------------------------------------------------------------------------
# E. Identity, idempotency, history
# ---------------------------------------------------------------------------


class IdentityIdempotencyHistoryTests(QualificationServiceTestCase):
    def test_one_current_assessment_per_member_item_version_reused_not_duplicated(self):
        record = _firm_record("reuse-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        spy_provider = SpyProvider(provider)
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=spy_provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])

        first = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(first.reused, ())
        self.assertEqual(spy_provider.calls, 1)

        second = service.assess_requirements("member-a", spec=spec, now=NOW + timedelta(minutes=1))
        self.assertEqual(second.reused, ("req-1",))
        self.assertEqual(second.assessments, first.assessments)
        self.assertEqual(spy_provider.calls, 1)

    def test_new_requirement_version_creates_new_rows_and_old_rows_are_history(self):
        record = _firm_record("version-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec_v1 = _spec([_item("req-1", 1, "Python")], version_key="version-1")
        result_v1 = service.assess_requirements("member-a", spec=spec_v1, now=NOW)

        spec_v2 = _spec([_item("req-1", 1, "Python")], version_key="version-2")
        service.assess_requirements("member-a", spec=spec_v2, now=NOW + timedelta(minutes=1))

        still_v1 = service.list_assessments("member-a", "version-1")
        self.assertEqual(still_v1, result_v1.assessments)

    def test_append_only_history_revision_numbers_are_contiguous(self):
        record_v1 = _firm_record("history-1")
        record_v2 = _candidate_record("history-2")
        switch = SwitchableProvider(FixtureAssessmentProvider({"req-1": (_claim("req-1", record_v1),)}))
        service = self.build_service(
            records_by_owner={"member-a": (record_v1, record_v2)}, provider=switch
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])

        service.assess_requirements("member-a", spec=spec, now=NOW)
        switch.set(FixtureAssessmentProvider({"req-1": (_claim("req-1", record_v2),)}))
        corrected = service.reassess_after_correction(
            "member-a",
            spec=spec,
            requirement_item_key="req-1",
            cause="member_correction",
            now=NOW + timedelta(minutes=1),
        )
        self.assertEqual(corrected.current_revision_number, 2)

        switch.set(FixtureAssessmentProvider({}))  # no claims at all this time
        corrected_again = service.reassess_after_correction(
            "member-a",
            spec=spec,
            requirement_item_key="req-1",
            cause="member_correction",
            now=NOW + timedelta(minutes=2),
        )
        self.assertEqual(corrected_again.current_revision_number, 3)

        history = service.assessment_history("member-a", corrected_again.assessment_key)
        self.assertEqual([r.revision_number for r in history], [1, 2, 3])

    def test_correction_recompute_appends_revision_and_preserves_prior(self):
        record_v1 = _firm_record("keep-1")
        record_v2 = _candidate_record("keep-2")
        switch = SwitchableProvider(FixtureAssessmentProvider({"req-1": (_claim("req-1", record_v1),)}))
        service = self.build_service(
            records_by_owner={"member-a": (record_v1, record_v2)}, provider=switch
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        first = service.assess_requirements("member-a", spec=spec, now=NOW)
        first_assessment = first.assessments[0]

        switch.set(FixtureAssessmentProvider({"req-1": (_claim("req-1", record_v2),)}))
        corrected = service.reassess_after_correction(
            "member-a",
            spec=spec,
            requirement_item_key="req-1",
            cause="member_correction",
            now=NOW + timedelta(minutes=1),
        )

        self.assertEqual(corrected.current_revision_number, 2)
        self.assertNotEqual(corrected.state, first_assessment.state)
        history = service.assessment_history("member-a", corrected.assessment_key)
        self.assertEqual(history[0].revision_number, 1)
        self.assertEqual(history[0].state, first_assessment.state)
        self.assertEqual(history[0].evidence_links, first_assessment.evidence_links)
        self.assertEqual(history[0].cause, "initial")
        self.assertEqual(history[1].cause, "member_correction")
        self.assertEqual(history[1].actor, "member")

    def test_reading_flagged_recompute_cause_and_actor(self):
        record = _firm_record("flag-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        service.assess_requirements("member-a", spec=spec, now=NOW)

        flagged_spec = _spec([_item("req-1", 1, "Python", reading_flagged=True)])
        corrected = service.reassess_after_correction(
            "member-a",
            spec=flagged_spec,
            requirement_item_key="req-1",
            cause="reading_flagged",
            now=NOW + timedelta(minutes=1),
        )
        self.assertEqual(corrected.state, STATE_NOT_ESTABLISHED)
        self.assertEqual(corrected.reason_code, "classification_ambiguous")
        history = service.assessment_history("member-a", corrected.assessment_key)
        self.assertEqual(history[-1].cause, "reading_flagged")
        self.assertEqual(history[-1].actor, "correction")

    def test_retry_only_from_review_unavailable_and_never_inherits_failure(self):
        record = _firm_record("retry-record")
        switch = SwitchableProvider(FixtureAssessmentProvider(fail_with="unavailable"))
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=switch)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        down = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(down.assessments[0].state, STATE_REVIEW_UNAVAILABLE)

        switch.set(FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)}))
        retried = service.retry_assessment(
            "member-a", spec=spec, requirement_item_key="req-1", now=NOW + timedelta(minutes=1)
        )
        self.assertEqual(retried.state, STATE_VERIFIED)
        history = service.assessment_history("member-a", retried.assessment_key)
        self.assertEqual(history[-1].cause, "retry")
        self.assertEqual(history[-1].actor, "member")

        with self.assertRaises(QualificationServiceError) as caught:
            service.retry_assessment(
                "member-a", spec=spec, requirement_item_key="req-1", now=NOW + timedelta(minutes=2)
            )
        self.assertEqual(caught.exception.failure_code, "cause_invalid")

    def test_unchanged_recompute_outcome_appends_no_revision(self):
        record = _firm_record("stable-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        first = service.assess_requirements("member-a", spec=spec, now=NOW)

        unchanged = service.reassess_after_correction(
            "member-a",
            spec=spec,
            requirement_item_key="req-1",
            cause="member_correction",
            now=NOW + timedelta(minutes=1),
        )
        self.assertEqual(unchanged, first.assessments[0])
        self.assertEqual(unchanged.current_revision_number, 1)
        history = service.assessment_history("member-a", unchanged.assessment_key)
        self.assertEqual(len(history), 1)


# ---------------------------------------------------------------------------
# F. Revocation / expiry recompute
# ---------------------------------------------------------------------------


class RevocationExpiryRecomputeTests(QualificationServiceTestCase):
    def test_revocation_recomputes_verified_to_not_established_evidence_revoked(self):
        record = _firm_record("revoke-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        grant = self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)

        outcome = service.revoke_grant(
            "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=1)
        )

        self.assertEqual(len(outcome.recomputed), 1)
        recomputed = outcome.recomputed[0]
        self.assertEqual(recomputed.state, STATE_NOT_ESTABLISHED)
        self.assertEqual(recomputed.reason_code, "evidence_revoked")
        self.assertEqual(recomputed.current_revision_number, 2)

        history = service.assessment_history("member-a", recomputed.assessment_key)
        self.assertEqual(history[0].state, STATE_VERIFIED)
        self.assertNotEqual(history[0].evidence_links, ())
        self.assertEqual(history[1].cause, "grant_revoked")
        self.assertEqual(history[1].actor, "system:recompute")

    def test_revocation_with_surviving_other_grant_keeps_verified(self):
        record = _firm_record("shared-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        grant_a = self.grant(service, "member-a", key="grant-a", now=NOW)
        self.grant(service, "member-a", key="grant-b", now=NOW + timedelta(seconds=1))
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW + timedelta(seconds=2))
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)

        outcome = service.revoke_grant(
            "member-a", grant_key=grant_a.grant_key, idempotency_key="revoke-a", now=NOW + timedelta(minutes=1)
        )

        self.assertEqual(outcome.recomputed, ())
        still_current = service.get_assessment("member-a", result.assessments[0].assessment_key)
        self.assertEqual(still_current.state, STATE_VERIFIED)
        self.assertEqual(still_current.current_revision_number, 1)

    def test_expired_grant_recompute_cause_grant_expired(self):
        record = _firm_record("expiry-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a", expires_at=NOW + timedelta(hours=1))
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)

        after_expiry = NOW + timedelta(hours=2)
        recomputed = service.recompute_for_expired_grants(
            "member-a", spec_by_version={"version-1": spec}, now=after_expiry
        )

        self.assertEqual(len(recomputed), 1)
        self.assertEqual(recomputed[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(recomputed[0].reason_code, "evidence_revoked")
        history = service.assessment_history("member-a", recomputed[0].assessment_key)
        self.assertEqual(history[-1].cause, "grant_expired")
        self.assertEqual(history[-1].actor, "system:recompute")

    def test_per_write_grant_recheck_drops_mid_run_dead_evidence(self):
        record = _firm_record("race-record")
        service = self.build_service(records_by_owner={"member-a": (record,)})
        grant = self.grant(service, "member-a")

        def hook(prompt):
            del prompt
            service.revoke_grant(
                "member-a", grant_key=grant.grant_key, idempotency_key="mid-run-revoke", now=NOW
            )

        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)}, hook=hook)
        service._provider = provider  # swap after grant setup, before assessment
        spec = _spec([_item("req-1", 1, "Python")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        assessment = result.assessments[0]
        # No link at all survives the mid-run revocation (the only claim
        # cited the now-dead grant), so evidence_links is empty -- which
        # already proves no link carries the dead grant's key.
        self.assertEqual(assessment.evidence_links, ())
        self.assertEqual(assessment.state, STATE_NOT_ESTABLISHED)


# ---------------------------------------------------------------------------
# G. Failure semantics
# ---------------------------------------------------------------------------


class FailureSemanticsTests(QualificationServiceTestCase):
    def test_ai_unavailable_writes_durable_review_unavailable_rows(self):
        records = (_firm_record("ai-down-r1"), _firm_record("ai-down-r2"))
        service = self.build_service(
            records_by_owner={"member-a": records}, provider=UnavailableAssessmentProvider()
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python"), _item("req-2", 2, "SQL")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        for assessment in result.assessments:
            self.assertEqual(assessment.state, STATE_REVIEW_UNAVAILABLE)
            self.assertEqual(assessment.reason_code, "ai_unavailable")
        stored = service.list_assessments("member-a", "version-1")
        self.assertEqual(stored, result.assessments)
        self.assertEqual(result.gate.gate, GATE_NOT_FULLY_VERIFIED)

    def test_provider_timeout_and_unexpected_error_reason_codes(self):
        record = _firm_record("timeout-record")
        timeout_service = self.build_service(
            records_by_owner={"member-a": (record,)}, provider=FixtureAssessmentProvider(fail_with="timeout")
        )
        self.grant(timeout_service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        timeout_result = timeout_service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(timeout_result.assessments[0].state, STATE_REVIEW_UNAVAILABLE)
        self.assertEqual(timeout_result.assessments[0].reason_code, "timeout")

        error_repository = InMemoryQualificationRepository()
        error_service = QualificationService(
            error_repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: InMemoryEvidencePort({"member-a": (record,)})},
            provider=FixtureAssessmentProvider(fail_with="error"),
            audit_sink=InMemoryAuditSink(),
        )
        error_service.create_grant(
            "member-a", scope=_grant_scope(), expires_at=NOW + timedelta(days=1),
            idempotency_key="g1", now=NOW,
        )
        error_result = error_service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(error_result.assessments[0].state, STATE_REVIEW_UNAVAILABLE)
        self.assertEqual(error_result.assessments[0].reason_code, "assessment_error")

    def test_evidence_source_unavailable_is_durable_review_unavailable(self):
        service = self.build_service(port_fail_with="evidence_source_unavailable")
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_REVIEW_UNAVAILABLE)
        self.assertEqual(result.assessments[0].reason_code, "evidence_source_unavailable")

        class BadRowDatabase:
            def execute_procedure(self, name, params):
                del name, params
                return [[{"evidence_key": "x"}]]  # missing fields -> evidence_row_invalid

        bad_port = WorkshopEvidencePort(BadRowDatabase())
        with self.assertRaises(EvidencePortError) as caught:
            bad_port.list_records_for_owner("member-a")
        self.assertEqual(caught.exception.code, "evidence_row_invalid")

        repository2 = InMemoryQualificationRepository()
        service2 = QualificationService(
            repository2,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: bad_port},
            provider=FixtureAssessmentProvider(),
            audit_sink=InMemoryAuditSink(),
        )
        service2.create_grant(
            "member-a", scope=_grant_scope(), expires_at=NOW + timedelta(days=1),
            idempotency_key="g1", now=NOW,
        )
        result2 = service2.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result2.assessments[0].state, STATE_REVIEW_UNAVAILABLE)
        self.assertEqual(result2.assessments[0].reason_code, "evidence_source_unavailable")

    def test_proposal_contract_violation_rejects_whole_run_as_assessment_error(self):
        record = _firm_record("valid-record")
        bad_claim = EvidenceClaim(
            requirement_item_key="req-1",
            evidence_key="not-admitted",
            evidence_class=EVIDENCE_CLASS_WORKSHOP,
            evidence_version=1,
            relation="supports",
        )
        provider = RawProvider(AssessmentProposalSet(claims=(bad_claim,)))
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python"), _item("req-2", 2, "SQL")])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        for assessment in result.assessments:
            self.assertEqual(assessment.state, STATE_REVIEW_UNAVAILABLE)
            self.assertEqual(assessment.reason_code, "assessment_error")
        kinds = [event.event_kind for event in self.audit.events]
        self.assertIn("proposal_contract_violation", kinds)

    def test_persistence_failure_raises_distinct_error_and_fabricates_no_state(self):
        record = _firm_record("persist-record")
        repository = FailingQualificationRepository(fail_on_revision_for={"item-2"})
        port = InMemoryEvidencePort({"member-a": (record,)})
        provider = FixtureAssessmentProvider(
            {
                "item-1": (_claim("item-1", record),),
                "item-2": (_claim("item-2", record),),
                "item-3": (_claim("item-3", record),),
            }
        )
        service = QualificationService(
            repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: port},
            provider=provider,
            audit_sink=self.audit,
        )
        service.create_grant(
            "member-a", scope=_grant_scope(), expires_at=NOW + timedelta(days=1),
            idempotency_key="g1", now=NOW,
        )
        spec = _spec(
            [_item("item-1", 1, "Python"), _item("item-2", 2, "SQL"), _item("item-3", 3, "Go")]
        )

        with self.assertRaises(AssessmentPersistenceError) as caught:
            service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertNotIsInstance(caught.exception, QualificationServiceError)
        self.assertEqual(caught.exception.requirement_item_key, "item-2")

        self.assertIsNotNone(repository.current_assessment_for_owner("member-a", "item-1", "version-1"))
        self.assertIsNone(repository.current_assessment_for_owner("member-a", "item-2", "version-1"))
        self.assertIsNone(repository.current_assessment_for_owner("member-a", "item-3", "version-1"))

    def test_audit_events_are_content_free(self):
        record = _firm_record(
            "canary-check", title="CANARY-TITLE-should-never-leak", body="CANARY-BODY-should-never-leak"
        )
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "This clause text CANARY-CLAUSE must never leak")])
        service.assess_requirements("member-a", spec=spec, now=NOW)
        # Practical fit emits no audit events by design (record_practical_fit
        # never calls self._emit): a canary note recorded there would never
        # reach self.audit.events, so asserting against it below would be
        # vacuous. It is deliberately not recorded in this test.

        self.assertTrue(self.audit.events)
        forbidden = ("CANARY", "clause", "distributed systems")
        for event in self.audit.events:
            serialized = repr(event)
            for token in forbidden:
                self.assertNotIn(token, serialized)


# ---------------------------------------------------------------------------
# H. Prompt fence and canaries (doc 08 §§2, 7)
# ---------------------------------------------------------------------------


class PromptFenceTests(QualificationServiceTestCase):
    def test_prompt_contains_only_admitted_evidence_and_member_clauses(self):
        from services.my_opportunities.qualification_service import build_assessment_prompt
        import json

        record = _firm_record("fence-record", title="Fence title", body="Fence body text.")
        spec = _spec([_item("req-1", 1, "Five years of Python")])

        prompt = build_assessment_prompt(spec, (record,), "I led the migration myself.")
        payload = json.loads(prompt.to_prompt_json())

        self.assertEqual(
            set(payload.keys()),
            {"requirement_version_key", "requirement_items", "evidence_records", "member_context_text"},
        )
        self.assertEqual(payload["requirement_version_key"], "version-1")
        self.assertEqual(
            payload["requirement_items"],
            [{"requirement_item_key": "req-1", "normalized_clause": "Five years of Python"}],
        )
        self.assertEqual(len(payload["evidence_records"]), 1)
        self.assertEqual(payload["evidence_records"][0]["evidence_key"], "fence-record")
        self.assertEqual(payload["evidence_records"][0]["title"], "Fence title")
        self.assertEqual(payload["evidence_records"][0]["body"], "Fence body text.")
        self.assertEqual(payload["member_context_text"], "I led the migration myself.")

    def test_member_b_canary_never_reaches_member_a_prompt(self):
        record_a = _firm_record("record-a", title="A's record", body="A's own experience.")
        record_b = _firm_record("record-b", title="CANARY-B-9f3", body="CANARY-B-9f3 body text.")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record_a),)})
        service = self.build_service(
            records_by_owner={"member-a": (record_a,), "member-b": (record_b,)}, provider=provider
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])

        service.assess_requirements("member-a", spec=spec, now=NOW)

        self.assertEqual(len(provider.calls), 1)
        serialized = provider.calls[0].to_prompt_json()
        self.assertNotIn("CANARY-B-9f3", serialized)

    def test_unadmitted_same_member_canary_never_reaches_prompt(self):
        admitted_record = _firm_record("admitted", title="Admitted", body="Admitted body.")
        excluded_record = _firm_record(
            "excluded", title="CANARY-A-out", body="CANARY-A-out body text."
        )
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", admitted_record),)})
        service = self.build_service(
            records_by_owner={"member-a": (admitted_record, excluded_record)}, provider=provider
        )
        self.grant(service, "member-a", scope=_grant_scope(record_keys=frozenset({"admitted"})))
        spec = _spec([_item("req-1", 1, "Python")])

        service.assess_requirements("member-a", spec=spec, now=NOW)

        serialized = provider.calls[0].to_prompt_json()
        self.assertNotIn("CANARY-A-out", serialized)
        self.assertIn("Admitted", serialized)

    def test_grants_and_telemetry_identifiers_never_serialize_into_prompt(self):
        record = _firm_record("identity-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        grant = self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])

        service.assess_requirements("member-a", spec=spec, now=NOW)

        serialized = provider.calls[0].to_prompt_json()
        self.assertNotIn(grant.grant_key, serialized)
        self.assertNotIn("member-a", serialized)
        self.assertNotIn("grant_key", serialized)
        self.assertNotIn("user_key", serialized)


# ---------------------------------------------------------------------------
# I. Negative multi-member isolation (doc 08 §7)
# ---------------------------------------------------------------------------


class MultiMemberIsolationTests(QualificationServiceTestCase):
    def test_cross_member_reads_writes_and_probes_are_indistinguishable_from_absent(self):
        record = _firm_record("isolation-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        grant = self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        assessment = result.assessments[0]
        observation = service.record_practical_fit(
            "member-a", opportunity_key="opportunity-1", note_text="Some note.",
            idempotency_key="fit-1", now=NOW,
        )

        absent_grant_error = self._failure("member-b", "absent-grant", service.get_grant)
        real_grant_error = self._failure("member-b", grant.grant_key, service.get_grant)
        self.assertEqual(absent_grant_error.failure_code, real_grant_error.failure_code)
        self.assertEqual(absent_grant_error.member_message, real_grant_error.member_message)
        self.assertEqual(real_grant_error.failure_code, "not_found")

        absent_assessment_error = self._failure("member-b", "absent-assessment", service.get_assessment)
        real_assessment_error = self._failure("member-b", assessment.assessment_key, service.get_assessment)
        self.assertEqual(absent_assessment_error.failure_code, real_assessment_error.failure_code)
        self.assertEqual(real_assessment_error.failure_code, "not_found")

        absent_history_error = self._failure("member-b", "absent-assessment", service.assessment_history)
        real_history_error = self._failure("member-b", assessment.assessment_key, service.assessment_history)
        self.assertEqual(absent_history_error.failure_code, real_history_error.failure_code)

        before = self.repository.state_digest()
        with self.assertRaises(QualificationServiceError) as revoke_absent:
            service.revoke_grant("member-b", grant_key="absent-grant", idempotency_key="b-revoke-1", now=NOW)
        with self.assertRaises(QualificationServiceError) as revoke_real:
            service.revoke_grant("member-b", grant_key=grant.grant_key, idempotency_key="b-revoke-2", now=NOW)
        self.assertEqual(revoke_absent.exception.failure_code, revoke_real.exception.failure_code)
        self.assertEqual(revoke_real.exception.failure_code, "not_found")

        with self.assertRaises(QualificationServiceError) as archive_absent:
            service.archive_practical_fit(
                "member-b", observation_key="absent-observation", idempotency_key="b-archive-1", now=NOW
            )
        with self.assertRaises(QualificationServiceError) as archive_real:
            service.archive_practical_fit(
                "member-b", observation_key=observation.observation_key, idempotency_key="b-archive-2", now=NOW
            )
        self.assertEqual(archive_absent.exception.failure_code, archive_real.exception.failure_code)
        self.assertEqual(archive_real.exception.failure_code, "not_found")

        self.assertEqual(self.repository.state_digest(), before)

    def _failure(self, user_key, key, method):
        with self.assertRaises(QualificationServiceError) as caught:
            method(user_key, key)
        return caught.exception

    def test_revoking_a_grant_changes_nothing_for_b(self):
        record_a = _firm_record("member-a-record")
        record_b = _firm_record("member-b-record")
        provider = FixtureAssessmentProvider(
            {"req-1": (_claim("req-1", record_a), _claim("req-1", record_b))}
        )
        service = self.build_service(
            records_by_owner={"member-a": (record_a,), "member-b": (record_b,)}, provider=provider
        )
        grant_a = self.grant(service, "member-a", key="grant-a")
        self.grant(service, "member-b", key="grant-b")
        spec = _spec([_item("req-1", 1, "Python")])

        before_b = service.assess_requirements("member-b", spec=spec, now=NOW)
        self.assertEqual(before_b.assessments[0].state, STATE_VERIFIED)

        service.revoke_grant(
            "member-a", grant_key=grant_a.grant_key, idempotency_key="revoke-a", now=NOW + timedelta(minutes=1)
        )

        after_b = service.get_assessment("member-b", before_b.assessments[0].assessment_key)
        self.assertEqual(after_b, before_b.assessments[0])
        self.assertEqual(after_b.current_revision_number, 1)

    def test_listings_are_owner_scoped(self):
        record_a = _firm_record("list-record-a")
        record_b = _firm_record("list-record-b")
        provider = FixtureAssessmentProvider(
            {"req-1": (_claim("req-1", record_a), _claim("req-1", record_b))}
        )
        service = self.build_service(
            records_by_owner={"member-a": (record_a,), "member-b": (record_b,)}, provider=provider
        )
        grant_a = self.grant(service, "member-a", key="grant-a")
        grant_b = self.grant(service, "member-b", key="grant-b")
        spec = _spec([_item("req-1", 1, "Python")])
        result_a = service.assess_requirements("member-a", spec=spec, now=NOW)
        result_b = service.assess_requirements(
            "member-b", spec=spec, now=NOW + timedelta(minutes=1)
        )
        service.record_practical_fit(
            "member-a", opportunity_key="opportunity-1", note_text="A's note",
            idempotency_key="fit-a", now=NOW,
        )
        service.record_practical_fit(
            "member-b", opportunity_key="opportunity-1", note_text="B's note",
            idempotency_key="fit-b", now=NOW,
        )

        b_grants = service.list_grants("member-b")
        self.assertNotIn(grant_a.grant_key, [g.grant_key for g in b_grants])
        self.assertIn(grant_b.grant_key, [g.grant_key for g in b_grants])

        b_assessments = service.list_assessments("member-b", "version-1")
        self.assertNotIn(result_a.assessments[0].assessment_key, [a.assessment_key for a in b_assessments])
        self.assertIn(result_b.assessments[0].assessment_key, [a.assessment_key for a in b_assessments])

        b_fit = service.list_practical_fit("member-b")
        self.assertTrue(all(o.note_text != "A's note" for o in b_fit))
        self.assertTrue(any(o.note_text == "B's note" for o in b_fit))


# ---------------------------------------------------------------------------
# J. Practical fit
# ---------------------------------------------------------------------------


class PracticalFitTests(QualificationServiceTestCase):
    def test_record_list_archive_practical_fit_owner_scoped_idempotent(self):
        service = self.build_service()

        created = service.record_practical_fit(
            "member-a",
            opportunity_key="opportunity-1",
            note_text="  The commute would be long.  ",
            idempotency_key="fit-1",
            now=NOW,
        )
        self.assertEqual(created.note_text, "The commute would be long.")
        self.assertIsNone(created.archived_at)

        replay = service.record_practical_fit(
            "member-a",
            opportunity_key="opportunity-1",
            note_text="  The commute would be long.  ",
            idempotency_key="fit-1",
            now=NOW + timedelta(minutes=1),
        )
        self.assertEqual(replay, created)

        listed = service.list_practical_fit("member-a", opportunity_key="opportunity-1")
        self.assertEqual(listed, (created,))

        archived = service.archive_practical_fit(
            "member-a", observation_key=created.observation_key, idempotency_key="archive-1", now=NOW + timedelta(minutes=2)
        )
        self.assertIsNotNone(archived.archived_at)

        with self.assertRaises(QualificationServiceError) as again:
            service.archive_practical_fit(
                "member-a",
                observation_key=created.observation_key,
                idempotency_key="archive-2",
                now=NOW + timedelta(minutes=3),
            )
        self.assertEqual(again.exception.failure_code, "observation_archived")

        with self.assertRaises(QualificationServiceError) as required:
            service.record_practical_fit(
                "member-a", opportunity_key="opportunity-1", note_text="   ",
                idempotency_key="fit-empty", now=NOW,
            )
        self.assertEqual(required.exception.failure_code, "note_required")

        with self.assertRaises(QualificationServiceError) as too_long:
            service.record_practical_fit(
                "member-a", opportunity_key="opportunity-1", note_text="x" * 2_001,
                idempotency_key="fit-long", now=NOW,
            )
        self.assertEqual(too_long.exception.failure_code, "note_too_long")


# ---------------------------------------------------------------------------
# Self-review fix regressions (writer's independent Opus pass, findings
# empirically confirmed by execution). One binding test per finding.
# ---------------------------------------------------------------------------


class _LocklessRepository(InMemoryQualificationRepository):
    """A conforming repository that does not expose a private ``_lock``
    attribute (minor a): the service must fall back to owning its own."""

    def __init__(self) -> None:
        super().__init__()
        del self._lock


class SelfReviewFixTests(QualificationServiceTestCase):
    # -- Blocker 1: zero/negative duration constraints -----------------

    def test_blocker1_zero_or_negative_duration_constraint_is_rejected_by_spec_validation(self):
        service = self.build_service()
        self.grant(service, "member-a")
        for bad_value in (0, -5):
            spec = _spec(
                [
                    _item(
                        "req-1",
                        1,
                        "Any tenure at all",
                        constraints=RequirementConstraints(minimum_duration_months=bad_value),
                    )
                ]
            )
            with self.assertRaises(QualificationServiceError) as caught:
                service.assess_requirements("member-a", spec=spec, now=NOW)
            self.assertEqual(caught.exception.failure_code, "spec_invalid")

    def test_blocker1_zero_or_negative_recency_window_is_rejected_by_spec_validation(self):
        service = self.build_service()
        self.grant(service, "member-a")
        for bad_value in (0, -1):
            spec = _spec(
                [
                    _item(
                        "req-1",
                        1,
                        "Recent experience",
                        constraints=RequirementConstraints(recency_window_months=bad_value),
                    )
                ]
            )
            with self.assertRaises(QualificationServiceError) as caught:
                service.assess_requirements("member-a", spec=spec, now=NOW)
            self.assertEqual(caught.exception.failure_code, "spec_invalid")

    def test_blocker1_blank_credential_name_is_rejected_by_spec_validation(self):
        service = self.build_service()
        self.grant(service, "member-a")
        spec = _spec(
            [
                _item(
                    "req-1",
                    1,
                    "Holds a credential",
                    constraints=RequirementConstraints(credential_names=("   ",)),
                )
            ]
        )
        with self.assertRaises(QualificationServiceError) as caught:
            service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(caught.exception.failure_code, "spec_invalid")

    def test_blocker1_bad_constraint_inside_an_alternative_path_is_also_rejected(self):
        service = self.build_service()
        self.grant(service, "member-a")
        spec = _spec(
            [
                _item(
                    "req-1",
                    1,
                    "Direct or alternative path",
                    constraints=RequirementConstraints(
                        credential_names=("PMP",),
                        alternative_paths=(RequirementConstraints(minimum_duration_months=0),),
                    ),
                )
            ]
        )
        with self.assertRaises(QualificationServiceError) as caught:
            service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(caught.exception.failure_code, "spec_invalid")

    def test_blocker1_defense_in_depth_zero_duration_never_verifies_off_zero_claims(self):
        # Exercises _satisfies directly through evaluate_item with a
        # constraints object that bypassed _validate_spec (e.g. a future
        # caller that builds specs without going through the service) --
        # the "not contributing" guard must still refuse to verify.
        item = _item(
            "item-1", 1, "Any tenure",
            constraints=RequirementConstraints(minimum_duration_months=0),
        )
        state, _reason, links = evaluate_item(item, (), {}, evaluation_time=NOW)
        self.assertNotEqual(state, STATE_VERIFIED)
        self.assertEqual(links, ())

    # -- Blocker 2: revoking the last live grant must always recompute -

    def test_blocker2_revoking_the_last_live_grant_recomputes_despite_stale_admitting_grant_key(self):
        record = _firm_record("last-grant-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        grant_a = self.grant(service, "member-a", key="grant-a", now=NOW)
        grant_b = self.grant(service, "member-a", key="grant-b", now=NOW + timedelta(seconds=1))
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW + timedelta(seconds=2))
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)
        # grant_a (earlier granted_at) is the recorded admitting grant --
        # confirm the premise this repro depends on.
        self.assertEqual(result.assessments[0].evidence_links[0].admitting_grant_key, grant_a.grant_key)

        # Revoke A first: B is still live and covers the same evidence, so
        # this is correctly a no-op -- but the link keeps citing A, which is
        # now dead (links are only rewritten when that exact assessment
        # changes).
        outcome_a = service.revoke_grant(
            "member-a", grant_key=grant_a.grant_key, idempotency_key="revoke-a", now=NOW + timedelta(minutes=1)
        )
        self.assertEqual(outcome_a.recomputed, ())
        still_verified = service.get_assessment("member-a", result.assessments[0].assessment_key)
        self.assertEqual(still_verified.state, STATE_VERIFIED)
        self.assertEqual(still_verified.evidence_links[0].admitting_grant_key, grant_a.grant_key)

        # Revoke B -- now the LAST live grant. B was never the assessment's
        # recorded admitting_grant_key, so scanning only
        # assessments_linking_grant(B) (the pre-fix behavior) would find
        # nothing, even though zero live grants now remain. The fix scans
        # candidates from ANY of the owner's grants.
        outcome_b = service.revoke_grant(
            "member-a", grant_key=grant_b.grant_key, idempotency_key="revoke-b", now=NOW + timedelta(minutes=2)
        )
        self.assertEqual(len(outcome_b.recomputed), 1)
        collapsed = service.get_assessment("member-a", result.assessments[0].assessment_key)
        self.assertEqual(collapsed.state, STATE_NOT_ESTABLISHED)
        self.assertEqual(collapsed.reason_code, "evidence_revoked")

    # -- Important 4: recompute_for_expired_grants ignores spec_by_version --

    def test_important4_recompute_for_expired_grants_ignores_spec_by_version_membership(self):
        record = _firm_record("expiry-scope-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a", expires_at=NOW + timedelta(hours=1))
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)

        after_expiry = NOW + timedelta(hours=2)
        # spec_by_version deliberately omits "version-1": the previous
        # behavior used this mapping as a membership gate and would have
        # silently skipped this assessment. The fix processes it anyway,
        # since spec_by_version is advisory/unused by the structural
        # recompute.
        recomputed = service.recompute_for_expired_grants("member-a", spec_by_version={}, now=after_expiry)

        self.assertEqual(len(recomputed), 1)
        self.assertEqual(recomputed[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(recomputed[0].reason_code, "evidence_revoked")

    # -- Blocker 3: appears_unmet must not survive with a dead contradiction

    def test_blocker3_appears_unmet_collapses_when_contradiction_evidence_is_revoked(self):
        contradiction_record = _firm_record("contradiction-record")
        provider = FixtureAssessmentProvider(
            {"req-1": (_claim("req-1", contradiction_record, relation="contradicts"),)}
        )
        service = self.build_service(
            records_by_owner={"member-a": (contradiction_record,)}, provider=provider
        )
        grant = self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Never worked with Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_APPEARS_UNMET)
        self.assertEqual(result.assessments[0].reason_code, "affirmative_contradiction")

        outcome = service.revoke_grant(
            "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=1)
        )

        self.assertEqual(len(outcome.recomputed), 1)
        collapsed = outcome.recomputed[0]
        self.assertEqual(collapsed.state, STATE_NOT_ESTABLISHED)
        self.assertEqual(collapsed.reason_code, "evidence_revoked")
        self.assertEqual(collapsed.evidence_links, ())

    # -- Important 5: derive_gate must not silently drop a missing item --

    def test_important5_derive_gate_treats_missing_assessment_as_review_unavailable_not_dropped(self):
        item_present = _item("req-1", 1, "Python")
        item_missing = _item("req-2", 2, "SQL")
        spec = _spec([item_present, item_missing])
        present_assessment = Assessment(
            assessment_key="a1",
            user_key="member-a",
            requirement_item_key="req-1",
            requirement_version_key="version-1",
            assessment_type="required",
            state=STATE_VERIFIED,
            reason_code="direct_evidence",
            current_revision_number=1,
            evidence_links=(),
            assessed_at=NOW,
            member_explanation="x",
        )

        gate = _derive_gate(spec, (present_assessment, None))

        self.assertEqual(gate.gate, GATE_NOT_FULLY_VERIFIED)
        self.assertEqual(gate.required_total, 2)
        self.assertEqual(gate.required_verified, 1)
        self.assertIn(("req-2", STATE_REVIEW_UNAVAILABLE, "assessment_error"), gate.non_verified_required)
        self.assertEqual(gate.label, "1 of 2 required verified · 1 review unavailable")

    def test_important5_gate_label_never_renders_a_dangling_separator(self):
        self.assertEqual(_gate_label(0, 0, ()), "Fully verified")
        # Defensive branch: non_verified is non-empty but carries a state
        # that maps to no phrase -- should not occur in practice (every
        # real non_verified entry uses a phrase-mapped state), but the
        # label must degrade to a well-formed string, never a dangling "· ".
        label = _gate_label(1, 2, (("req-x", "made_up_state", "made_up_reason"),))
        self.assertFalse(label.endswith("· "))
        self.assertEqual(label, "1 of 2 required verified")

    # -- Important 6 is a strengthening of the K1 migration test itself;
    # see QualificationMigrationTests below.

    # -- Important 7: an unknown evidence strength must never vanish -----

    def test_important7_in_memory_port_rejects_unknown_strength_at_construction(self):
        bad_record = EvidenceRecord(
            evidence_key="bad-strength",
            evidence_class=EVIDENCE_CLASS_WORKSHOP,
            version=1,
            title="Title",
            body="Body",
            updated_at=NOW,
            strength="maybe",
            time_span=None,
        )
        with self.assertRaises(EvidencePortError) as caught:
            InMemoryEvidencePort({"member-a": (bad_record,)})
        self.assertEqual(caught.exception.code, "evidence_row_invalid")

    def test_important7_proposal_validation_rejects_unknown_admitted_record_strength(self):
        # Independent defense from the port-level guard above: prove
        # _validate_proposal itself refuses an admitted record whose
        # strength is not in EVIDENCE_STRENGTHS, in case a future port
        # implementation does not construct through InMemoryEvidencePort.
        bad_record = EvidenceRecord(
            evidence_key="bad-strength",
            evidence_class=EVIDENCE_CLASS_WORKSHOP,
            version=1,
            title="Title",
            body="Body",
            updated_at=NOW,
            strength="maybe",
            time_span=None,
        )
        spec = _spec([_item("req-1", 1, "Python")])
        proposal = AssessmentProposalSet(claims=(_claim("req-1", bad_record),))
        with self.assertRaises(ProposalContractError) as caught:
            _validate_proposal(proposal, spec, (bad_record,))
        self.assertEqual(str(caught.exception), "claim_evidence_strength_invalid")

    # -- Important 8: flagged reading must short-circuit before port/AI --

    def test_important8_flagged_item_short_circuits_even_when_provider_is_down(self):
        service = self.build_service(provider=UnavailableAssessmentProvider())
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Ambiguous clause", reading_flagged=True)])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        self.assertEqual(result.assessments[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(result.assessments[0].reason_code, "classification_ambiguous")

    def test_important8_all_flagged_spec_never_calls_port_or_provider(self):
        record = _firm_record("unused-record")
        raw_port = InMemoryEvidencePort({"member-a": (record,)})
        spy_port = SpyEvidencePort(raw_port)
        raw_provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        spy_provider = SpyProvider(raw_provider)
        service = QualificationService(
            self.repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: spy_port},
            provider=spy_provider,
            audit_sink=self.audit,
        )
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Ambiguous clause", reading_flagged=True)])

        result = service.assess_requirements("member-a", spec=spec, now=NOW)

        self.assertEqual(result.assessments[0].state, STATE_NOT_ESTABLISHED)
        self.assertEqual(result.assessments[0].reason_code, "classification_ambiguous")
        self.assertEqual(spy_port.calls, 0)
        self.assertEqual(spy_provider.calls, 0)

    def test_important8_recompute_of_flagged_item_never_calls_port_or_provider(self):
        record = _firm_record("recompute-record")
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = self.build_service(records_by_owner={"member-a": (record,)}, provider=provider)
        self.grant(service, "member-a")
        spec = _spec([_item("req-1", 1, "Python")])
        service.assess_requirements("member-a", spec=spec, now=NOW)

        spy_port = SpyEvidencePort(InMemoryEvidencePort({"member-a": (record,)}))
        spy_provider = SpyProvider(provider)
        service._evidence_ports = {EVIDENCE_CLASS_WORKSHOP: spy_port}
        service._provider = spy_provider

        flagged_spec = _spec([_item("req-1", 1, "Python", reading_flagged=True)])
        corrected = service.reassess_after_correction(
            "member-a",
            spec=flagged_spec,
            requirement_item_key="req-1",
            cause="reading_flagged",
            now=NOW + timedelta(minutes=1),
        )

        self.assertEqual(corrected.state, STATE_NOT_ESTABLISHED)
        self.assertEqual(corrected.reason_code, "classification_ambiguous")
        self.assertEqual(spy_port.calls, 0)
        self.assertEqual(spy_provider.calls, 0)

    # -- Important 9: revoke_grant persistence failure must stay replayable

    def test_important9_revoke_grant_persistence_failure_leaves_a_replayable_receipt(self):
        record = _firm_record("persist-revoke-record")
        repository = FailingQualificationRepository(
            fail_on_revision_for={"req-1"}, fail_from_revision_number=2
        )
        port = InMemoryEvidencePort({"member-a": (record,)})
        provider = FixtureAssessmentProvider({"req-1": (_claim("req-1", record),)})
        service = QualificationService(
            repository,
            evidence_ports={EVIDENCE_CLASS_WORKSHOP: port},
            provider=provider,
            audit_sink=self.audit,
        )
        grant = service.create_grant(
            "member-a", scope=_grant_scope(), expires_at=NOW + timedelta(days=1),
            idempotency_key="g1", now=NOW,
        )
        spec = _spec([_item("req-1", 1, "Python")])
        result = service.assess_requirements("member-a", spec=spec, now=NOW)
        self.assertEqual(result.assessments[0].state, STATE_VERIFIED)

        with self.assertRaises(AssessmentPersistenceError):
            service.revoke_grant(
                "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=1)
            )

        # The grant is durably revoked even though the recompute write
        # failed mid-loop.
        still_revoked = service.get_grant("member-a", grant.grant_key)
        self.assertIsNotNone(still_revoked.revoked_at)

        # A retry with the SAME idempotency key must replay the receipt
        # recorded before the re-raise, not refuse grant_terminal.
        replay = service.revoke_grant(
            "member-a", grant_key=grant.grant_key, idempotency_key="revoke-1", now=NOW + timedelta(minutes=2)
        )
        self.assertEqual(replay.grant.grant_key, grant.grant_key)
        self.assertIsNotNone(replay.grant.revoked_at)
        self.assertEqual(replay.recomputed, ())

    # -- Minor a: service must not require a private repository lock -----

    def test_minora_service_accepts_repository_without_private_lock_attribute(self):
        repository = _LocklessRepository()
        service = QualificationService(repository)
        grant = service.create_grant(
            "member-a", scope=_grant_scope(), expires_at=NOW + timedelta(days=1),
            idempotency_key="k1", now=NOW,
        )
        self.assertEqual(service.get_grant("member-a", grant.grant_key), grant)

    # -- Minor c: practical-fit keys are bounded ---------------------------

    def test_minorc_practical_fit_keys_are_bounded(self):
        service = self.build_service()
        with self.assertRaises(QualificationServiceError) as empty_opportunity:
            service.record_practical_fit(
                "member-a", opportunity_key="   ", note_text="A note.",
                idempotency_key="fit-bad-1", now=NOW,
            )
        self.assertEqual(empty_opportunity.exception.failure_code, "opportunity_key_required")

        with self.assertRaises(QualificationServiceError) as long_opportunity:
            service.record_practical_fit(
                "member-a", opportunity_key="x" * 201, note_text="A note.",
                idempotency_key="fit-bad-2", now=NOW,
            )
        self.assertEqual(long_opportunity.exception.failure_code, "opportunity_key_too_long")

        with self.assertRaises(QualificationServiceError) as long_observation:
            service.archive_practical_fit(
                "member-a", observation_key="x" * 81, idempotency_key="fit-bad-3", now=NOW,
            )
        self.assertEqual(long_observation.exception.failure_code, "observation_key_too_long")


# ---------------------------------------------------------------------------
# K. Migration / registry / verifier / rollback (file-content tests)
# ---------------------------------------------------------------------------


class QualificationMigrationTests(unittest.TestCase):
    def test_c5_migration_registry_and_verifier_are_bounded_and_gate_proven(self):
        forward_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-003_qualification.sql"
        rollback_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-003_qualification_rollback.sql"
        verify_path = ROOT / "SQL FIles/Verification/PS-MYOPP-003_qualification_verify.sql"
        forward = forward_path.read_text(encoding="utf-8")
        rollback = rollback_path.read_text(encoding="utf-8")
        verify = verify_path.read_text(encoding="utf-8")
        registry = json.loads((ROOT / "SQL FIles/Migrations/registry.json").read_text(encoding="utf-8"))
        entry = next(item for item in registry["migrations"] if item["id"] == "PS-MYOPP-003")

        self.assertEqual(len([item for item in registry["migrations"] if item["id"] == "PS-MYOPP-003"]), 1)
        self.assertEqual(entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002"])
        self.assertEqual(entry["forward"], forward_path.relative_to(ROOT).as_posix())
        self.assertEqual(entry["rollback"], rollback_path.relative_to(ROOT).as_posix())

        # The disposable gate proof is recorded by the writer before merge
        # (blueprint C5_ARCHITECTURE.md §6); until then the entry carries
        # "gate": null and every assertion below on the populated proof is
        # expected to fail here -- that failure is the honest signal that the
        # gate has not been run yet, not a defect in this test.
        gate = entry["gate"]
        self.assertEqual(gate["executable_sha256"], executable_sha256(forward_path))
        self.assertEqual(gate["prerequisites"], ["PS-PLAT-000", "PS-MYOPP-001", "PS-MYOPP-002"])
        self.assertEqual(
            gate["verification"],
            "PS-MYOPP-003_qualification_verify.sql returned verified = 1",
        )
        self.assertEqual(len(executable_sha256(forward_path)), 64)

        # Important 6: the gate must never point at a real database, and its
        # server/operator fields must actually be populated (not blank).
        self.assertTrue(gate["gate_database"])
        self.assertNotIn(gate["gate_database"], {"peerslate-database", "peerslate-staging"})
        self.assertTrue(gate["gate_server"])
        self.assertTrue(gate["operator"])

        for table in (
            "myopp_evidence_grants",
            "myopp_assessments",
            "myopp_assessment_revisions",
            "myopp_assessment_evidence_links",
            "myopp_practical_fit_observations",
            "myopp_qualification_commands",
        ):
            self.assertIn(f"CREATE TABLE dbo.{table}", forward)
            self.assertIn(f"DROP TABLE dbo.{table};", rollback)
            self.assertIn(table, verify)
            self.assertNotIn("score", _table_body(forward, table))
            self.assertNotIn("probab", _table_body(forward, table))
            self.assertNotIn("percent", _table_body(forward, table))
            self.assertNotIn("rank", _table_body(forward, table))
            self.assertNotIn("predict", _table_body(forward, table))
            self.assertNotIn("confidence", _table_body(forward, table))
            self.assertNotIn("match_rate", _table_body(forward, table))

        self.assertIn("PS-MYOPP-003 requires PS-MYOPP-001", forward)
        self.assertIn("PS-MYOPP-003 requires PS-MYOPP-002", forward)
        self.assertIn("user_key nvarchar(300) NOT NULL", forward)
        self.assertIn("CK_myopp_assessments_state", forward)
        self.assertIn("N'verified', N'not_established', N'appears_unmet', N'review_unavailable'", forward)
        self.assertIn("CK_myopp_assessments_state_reason", forward)
        self.assertIn("CK_myopp_assessment_revisions_state_reason", forward)

        links_body = _table_body(forward, "myopp_assessment_evidence_links")
        self.assertNotIn("evidence_title", links_body)
        self.assertNotIn("evidence_body", links_body)
        self.assertIn("evidence_key", links_body)
        self.assertIn("evidence_version", links_body)
        self.assertIn("myopp_evidence_grant_id", links_body)

        self.assertIn("trg_myopp_assessments_requirement_consistency", forward)
        self.assertIn("trg_myopp_assessments_head_guard", forward)
        self.assertIn("trg_myopp_assessment_revisions_immutable", forward)
        self.assertIn("trg_myopp_assessment_evidence_links_immutable", forward)
        self.assertIn("trg_myopp_practical_fit_observations_guard", forward)
        self.assertIn("trg_myopp_qualification_commands_immutable", forward)
        self.assertIn("trg_myopp_evidence_grants_transition_guard", forward)

        self.assertIn("PS-MYOPP-003 is not recorded", rollback)
        self.assertIn("later migration is recorded", rollback)
        self.assertIn("C5 member data exists", rollback)

        self.assertIn("SELECT CAST(1 AS bit) AS verified", verify)
        self.assertIn("content-free", verify)
        self.assertIn("%score%", verify)
        self.assertIn("%probab%", verify)
        self.assertIn("%percent%", verify)
        self.assertIn("%rank%", verify)
        self.assertIn("%predict%", verify)
        self.assertIn("%confidence%", verify)
        self.assertIn("%match_rate%", verify)

    def test_rollback_drops_in_dependency_order(self):
        rollback_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-003_qualification_rollback.sql"
        rollback = rollback_path.read_text(encoding="utf-8")

        commands_index = rollback.index("DROP TABLE dbo.myopp_qualification_commands;")
        links_index = rollback.index("DROP TABLE dbo.myopp_assessment_evidence_links;")
        revisions_index = rollback.index("DROP TABLE dbo.myopp_assessment_revisions;")
        assessments_index = rollback.index("DROP TABLE dbo.myopp_assessments;")
        observations_index = rollback.index("DROP TABLE dbo.myopp_practical_fit_observations;")
        grants_index = rollback.index("DROP TABLE dbo.myopp_evidence_grants;")
        ledger_delete_index = rollback.index(
            "DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-003';"
        )

        self.assertLess(commands_index, links_index)
        self.assertLess(links_index, revisions_index)
        self.assertLess(revisions_index, assessments_index)
        self.assertLess(assessments_index, observations_index)
        self.assertLess(observations_index, grants_index)
        self.assertLess(grants_index, ledger_delete_index)

    def test_package_registry_contains_c5_once_and_counts_reconcile(self):
        # This is expected to fail until the C5 claim activation registers
        # PS-MYOPP-QUALIFICATION-001 in docs/governance/PACKAGE_REGISTRY.json --
        # that surface is owned by another active claim and is not touched by
        # this writer. See C5_ARCHITECTURE.md §9.
        registry = json.loads((ROOT / "docs/governance/PACKAGE_REGISTRY.json").read_text(encoding="utf-8"))
        packages = [item for values in registry["categories"].values() for item in values]
        self.assertEqual(packages.count("PS-MYOPP-QUALIFICATION-001"), 1)
        self.assertEqual(registry["counts"]["total"], len(packages))
        for category, values in registry["categories"].items():
            self.assertEqual(registry["counts"][category], len(values))


def _table_body(sql: str, table: str) -> str:
    start = sql.index(f"CREATE TABLE dbo.{table}")
    next_create = sql.find("CREATE TABLE dbo.", start + 1)
    return sql[start:] if next_create == -1 else sql[start:next_create]


# ---------------------------------------------------------------------------
# L. Focused C2/C3 regression (contracts C5 relies on)
# ---------------------------------------------------------------------------


class RegressionTests(unittest.TestCase):
    def test_c2_requirement_shapes_match_c5_spec_expectations(self):
        from services.my_opportunities.canonical_service import RequirementItem, RequirementVersion

        item = RequirementItem(
            requirement_item_key="c2-item-1",
            data_class="fixture",
            normalized_clause="five years of python",
            ordinal=1,
        )
        version = RequirementVersion(
            requirement_version_key="c2-version-1",
            opportunity_key="c2-opportunity-1",
            source_version_key="c2-source-1",
            data_class="fixture",
            clause_fingerprint="fp-1",
            items=(item,),
            derived_at=NOW,
        )

        # The exact field names C5's RequirementItemSpec/RequirementVersionSpec
        # map from -- an import-level canary against C2 drift.
        self.assertEqual(item.requirement_item_key, "c2-item-1")
        self.assertEqual(item.normalized_clause, "five years of python")
        self.assertEqual(item.ordinal, 1)
        self.assertEqual(version.requirement_version_key, "c2-version-1")
        self.assertEqual(version.opportunity_key, "c2-opportunity-1")
        self.assertIn("requirement_item_key", RequirementItem.__dataclass_fields__)
        self.assertIn("normalized_clause", RequirementItem.__dataclass_fields__)
        self.assertIn("ordinal", RequirementItem.__dataclass_fields__)
        self.assertIn("requirement_version_key", RequirementVersion.__dataclass_fields__)
        self.assertIn("opportunity_key", RequirementVersion.__dataclass_fields__)

    def test_c3_verification_scope_vocabulary_unchanged(self):
        from services.my_opportunities import criteria_service
        from services.my_opportunities.qualification_service import (
            GATE_FULLY_VERIFIED as _GATE_FULLY_VERIFIED,
            GATE_NOT_FULLY_VERIFIED as _GATE_NOT_FULLY_VERIFIED,
        )

        snapshot = frozenset({"fully_verified", "not_fully_verified", "both"})
        self.assertEqual(criteria_service._SCOPES, snapshot)
        # C5's gate strings must stay consistent with what C3 scopes filter on.
        self.assertIn(_GATE_FULLY_VERIFIED, snapshot)
        self.assertIn(_GATE_NOT_FULLY_VERIFIED, snapshot)

    def test_workshop_evidence_port_row_contract(self):
        class StubDatabase:
            def __init__(self, rows=None, *, raise_error=False):
                self.rows = rows if rows is not None else []
                self.raise_error = raise_error
                self.calls = []

            def execute_procedure(self, name, params):
                self.calls.append((name, params))
                if self.raise_error:
                    raise RuntimeError("connection lost")
                return [self.rows]

        good_row = {
            "evidence_key": "11111111-1111-1111-1111-111111111111",
            "evidence_version": 3,
            "evidence_title": "Platform work",
            "evidence_body": "Built distributed systems for five years.",
            "evidence_updated_at_utc": NOW,
        }
        database = StubDatabase([good_row])
        port = WorkshopEvidencePort(database)
        records = port.list_records_for_owner("member-a", max_items=999)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].evidence_key, good_row["evidence_key"])
        self.assertEqual(records[0].version, 3)
        self.assertEqual(records[0].strength, "firm")
        self.assertIsNone(records[0].time_span)
        self.assertEqual(database.calls, [("usp_ListOpportunityEvidenceForOwner", [("@UserKey", "member-a"), ("@MaxItems", 24)])])

        extra_field_row = dict(good_row, extra_field="unexpected")
        with self.assertRaises(EvidencePortError) as extra:
            WorkshopEvidencePort(StubDatabase([extra_field_row])).list_records_for_owner("member-a")
        self.assertEqual(extra.exception.code, "evidence_row_invalid")

        missing_field_row = dict(good_row)
        del missing_field_row["evidence_title"]
        with self.assertRaises(EvidencePortError) as missing:
            WorkshopEvidencePort(StubDatabase([missing_field_row])).list_records_for_owner("member-a")
        self.assertEqual(missing.exception.code, "evidence_row_invalid")

        bad_version_row = dict(good_row, evidence_version=0)
        with self.assertRaises(EvidencePortError) as bad_version:
            WorkshopEvidencePort(StubDatabase([bad_version_row])).list_records_for_owner("member-a")
        self.assertEqual(bad_version.exception.code, "evidence_row_invalid")

        naive_row = dict(good_row, evidence_updated_at_utc=datetime(2026, 8, 1, 0, 0))
        with self.assertRaises(EvidencePortError) as naive:
            WorkshopEvidencePort(StubDatabase([naive_row])).list_records_for_owner("member-a")
        self.assertEqual(naive.exception.code, "evidence_row_invalid")

        failing_database = StubDatabase(raise_error=True)
        with self.assertRaises(EvidencePortError) as unavailable:
            WorkshopEvidencePort(failing_database).list_records_for_owner("member-a")
        self.assertEqual(unavailable.exception.code, "evidence_source_unavailable")


if __name__ == "__main__":
    unittest.main()
