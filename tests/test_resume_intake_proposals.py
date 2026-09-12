"""Proposal-binding tests for MVP1 increment C.

A proposal carries exact source spans, source/submission versions, a command
digest and a lifecycle fence. These tests pin the binding, the first-decision
path, invalidation on a manual edit, and that retained historical provenance
never resurrects purged source text.
"""

from __future__ import annotations

import unittest

from services.resume_intake_proposals import (
    ProposalError,
    ProposalSpec,
    binding_is_current,
    create,
    decide,
    invalidate_for_source,
    invalidate_for_target,
    present,
)
from services.resume_intake_repository import empty_intake_snapshot


def snapshot():
    state = empty_intake_snapshot()
    state["submissions"]["sub-1"] = {"submission_key": "sub-1", "version": 1, "state": "active"}
    state["sources"]["src-1"] = {"source_key": "src-1", "version": 1, "state": "active", "text": "I led it."}
    return state


def spec(**overrides):
    base = dict(
        source_key="src-1", source_version=1, submission_key="sub-1",
        submission_version=1, kind="inferred_wording", record_type="unspecified",
        quote="I led it.", span_start=0, span_end=9, proposed_values={"text": "I led it."},
    )
    base.update(overrides)
    return ProposalSpec(**base)


class ProposalBindingTests(unittest.TestCase):
    def test_create_records_exact_span_versions_and_digest(self):
        state = snapshot()
        proposal = create(state, spec(command_digest="abc"))
        self.assertEqual(proposal["span_start"], 0)
        self.assertEqual(proposal["span_end"], 9)
        self.assertEqual(proposal["binding"]["source_version"], 1)
        self.assertEqual(proposal["binding"]["submission_version"], 1)
        self.assertEqual(proposal["command_digest"], "abc")
        self.assertEqual(proposal["provenance"]["source_key"], "src-1")
        view = present(proposal)
        self.assertEqual(view["span"], [0, 9])
        self.assertTrue(view["requires_member_wording"])

    def test_unambiguous_kind_does_not_require_member_wording(self):
        proposal = create(snapshot(), spec(kind="new_fact", confidence="certain", record_type="skill"))
        self.assertFalse(proposal["requires_member_wording"])

    def test_missing_quote_is_rejected(self):
        with self.assertRaises(ProposalError):
            create(snapshot(), spec(quote="  "))

    def test_binding_goes_stale_when_the_source_changes(self):
        state = snapshot()
        proposal = create(state, spec())
        self.assertTrue(binding_is_current(state, proposal))
        state["sources"]["src-1"]["version"] = 2
        self.assertFalse(binding_is_current(state, proposal))
        state["sources"]["src-1"]["version"] = 1
        state["submissions"]["sub-1"]["state"] = "superseded"
        self.assertFalse(binding_is_current(state, proposal))


class ProposalDecisionTests(unittest.TestCase):
    def test_first_acceptance_needs_no_earlier_receipt(self):
        state = snapshot()
        proposal = create(state, spec(kind="new_fact", confidence="certain", record_type="skill",
                                      proposed_values={"name": "MBSE"}))
        decided = decide(state, proposal["proposal_key"], decision="accept")
        self.assertEqual(decided["state"], "accepted")
        self.assertEqual(decided["confirmed_values"], {"name": "MBSE"})

    def test_uncertain_acceptance_requires_member_wording(self):
        state = snapshot()
        proposal = create(state, spec())
        with self.assertRaises(ProposalError) as caught:
            decide(state, proposal["proposal_key"], decision="accept")
        self.assertEqual(caught.exception.code, "reconciliation_required")
        self.assertIsNotNone(caught.exception.proposed)
        # The refusal did not consume the proposal.
        self.assertEqual(state["proposals"][proposal["proposal_key"]]["state"], "pending")

    def test_accepting_a_stale_binding_conflicts_without_losing_wording(self):
        state = snapshot()
        proposal = create(state, spec())
        state["lifecycle_epoch"] = 3
        with self.assertRaises(ProposalError) as caught:
            decide(state, proposal["proposal_key"], decision="accept",
                   confirmed_values={"text": "kept"})
        self.assertEqual(caught.exception.code, "changed")
        self.assertEqual(caught.exception.proposed, {"text": "I led it."})

    def test_manual_edit_invalidates_pending_references_to_that_target(self):
        state = snapshot()
        target_one = create(state, spec(target_key="rec-1"))
        target_two = create(state, spec(target_key="rec-1"))
        other = create(state, spec(target_key="rec-2"))
        affected = invalidate_for_target(state, "rec-1")
        self.assertEqual(affected, 2)
        self.assertEqual(state["proposals"][target_one["proposal_key"]]["state"], "invalidated")
        self.assertEqual(state["proposals"][target_two["proposal_key"]]["state"], "invalidated")
        self.assertEqual(state["proposals"][other["proposal_key"]]["state"], "pending")

    def test_rejecting_does_not_require_a_current_binding(self):
        state = snapshot()
        proposal = create(state, spec())
        state["sources"]["src-1"]["state"] = "purged"
        decided = decide(state, proposal["proposal_key"], decision="reject")
        self.assertEqual(decided["state"], "rejected")

    def test_source_purge_retains_provenance_and_invalidates_pending(self):
        state = snapshot()
        proposal = create(state, spec())
        invalidate_for_source(state, "src-1")
        stored = state["proposals"][proposal["proposal_key"]]
        self.assertTrue(stored["source_purged"])
        self.assertEqual(stored["state"], "invalidated")
        self.assertEqual(stored["provenance"]["source_key"], "src-1")
        # Retained provenance is not source text: nothing was resurrected.
        self.assertEqual(stored["proposed_values"], {"text": "I led it."})

    def test_already_decided_proposal_conflicts(self):
        state = snapshot()
        proposal = create(state, spec())
        decide(state, proposal["proposal_key"], decision="reject")
        with self.assertRaises(ProposalError) as caught:
            decide(state, proposal["proposal_key"], decision="reject")
        self.assertEqual(caught.exception.code, "already_decided")


if __name__ == "__main__":
    unittest.main()
