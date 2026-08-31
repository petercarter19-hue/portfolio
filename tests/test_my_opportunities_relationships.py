from __future__ import annotations

import ast
import inspect
import json
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.migration_registry import executable_sha256

from services.my_opportunities.canonical_service import DATA_CLASSES, LISTING_STATES
from services.my_opportunities.qualification_service import GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED
from services.my_opportunities.relationships_service import (
    CREATED_FROM_RESULT,
    CREATED_FROM_SAVED,
    CREATED_FROM_SOURCES,
    DEFAULT_UNDO_WINDOW,
    FailingRelationshipsRepository,
    GoverningBasis,
    InMemoryAuditSink,
    InMemoryRelationshipsRepository,
    LINK_STATE_LINKED,
    LINK_STATE_UNLINKED,
    LINK_STATES,
    OVERLAY_CLOSED_BY_SOURCE,
    OVERLAY_COULD_NOT_REVERIFY,
    OVERLAY_ORDER,
    OVERLAY_POSTING_CHANGED,
    OVERLAYS,
    RelationshipsLimits,
    RelationshipsRepository,
    RelationshipsService,
    RelationshipsServiceError,
    RepositoryWriteError,
    SAVED_FILTER_ALL,
    SAVED_FILTER_CHANGED,
    SAVED_FILTER_CLOSED,
    SAVED_FILTER_CURRENT,
    SAVED_FILTER_UNREACHABLE,
    SAVED_STATE_FILTERS,
    SAVE_STATE_REMOVED,
    SAVE_STATE_REMOVING,
    SAVE_STATE_SAVED,
    SAVE_STATES,
    SavedDisplayFacts,
    SavedListEntry,
    SavedOpportunity,
    SlateLink,
    VERIFICATION_FILTERS,
    VERIFICATION_NOT_ASSESSED,
    VERIFICATION_OUTCOMES,
    derive_lifecycle_overlays,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes / harness
# ---------------------------------------------------------------------------


class FakeBasisReader:
    """In-memory GoverningBasisReader fake: bases/display keyed by
    (opportunity_key, data_class)."""

    def __init__(self):
        self._bases: dict[tuple[str, str], GoverningBasis] = {}
        self._display: dict[tuple[str, str], SavedDisplayFacts] = {}

    def set_basis(self, opportunity_key, data_class, **fields):
        defaults = dict(
            opportunity_key=opportunity_key,
            data_class=data_class,
            listing_state="current",
            governing_source_version_key="v1",
            last_attempted_at=NOW,
            last_successfully_verified_at=NOW,
        )
        defaults.update(fields)
        self._bases[(opportunity_key, data_class)] = GoverningBasis(**defaults)

    def clear_basis(self, opportunity_key, data_class):
        self._bases.pop((opportunity_key, data_class), None)

    def set_display(self, opportunity_key, data_class, role_title, employer_name):
        self._display[(opportunity_key, data_class)] = SavedDisplayFacts(role_title, employer_name)

    def governing_basis(self, opportunity_key, data_class):
        return self._bases.get((opportunity_key, data_class))

    def display_facts(self, opportunity_key, data_class):
        return self._display.get((opportunity_key, data_class))


class FakeVerificationReader:
    def __init__(self):
        self._outcomes: dict[tuple[str, str], str] = {}

    def set_outcome(self, user_key, opportunity_key, outcome):
        self._outcomes[(user_key, opportunity_key)] = outcome

    def latest_gate_outcome(self, user_key, opportunity_key):
        return self._outcomes.get((user_key, opportunity_key))


class Harness:
    def __init__(self, *, repository=None, limits=None):
        self.basis_reader = FakeBasisReader()
        self.verification_reader = FakeVerificationReader()
        self.audit = InMemoryAuditSink()
        self.repository = repository or InMemoryRelationshipsRepository()
        self.limits = limits or RelationshipsLimits()
        self.service = RelationshipsService(
            self.repository, self.basis_reader, self.verification_reader, self.audit, self.limits
        )
        self._n = 0

    def key(self, label):
        self._n += 1
        return f"{label}-{self._n}"

    def admit(self, opportunity_key="opp-1", data_class="fixture", **basis_fields):
        self.basis_reader.set_basis(opportunity_key, data_class, **basis_fields)
        self.basis_reader.set_display(opportunity_key, data_class, "Platform Engineer", "Astraeus")
        return opportunity_key

    def save(self, user_key, opportunity_key="opp-1", data_class="fixture", reviewed="v1", now=NOW):
        return self.service.save_opportunity(
            user_key,
            opportunity_key=opportunity_key,
            data_class=data_class,
            reviewed_source_version_key=reviewed,
            idempotency_key=self.key("save"),
            now=now,
        )


class RelationshipsTestCase(unittest.TestCase):
    def setUp(self):
        self.harness = Harness()
        self.harness.admit()


# ---------------------------------------------------------------------------
# A. Save machine (doc 16 row 32; doc 03 §7)
# ---------------------------------------------------------------------------


class SaveMachineTests(RelationshipsTestCase):
    def test_save_from_result_basis_creates_saved_row_with_reviewed_version(self):
        save = self.harness.save("alice", reviewed="v1")
        self.assertEqual(save.state, SAVE_STATE_SAVED)
        self.assertEqual(save.last_reviewed_source_version_key, "v1")
        self.assertEqual(save.opportunity_key, "opp-1")
        self.assertIsNone(save.removal_requested_at)
        self.assertIsNone(save.removed_at)

    def test_save_is_idempotent_by_key_and_input(self):
        key = self.harness.key("idem")
        first = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        second = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(self.harness.repository.saves_for_owner("alice")), 1)

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture",
                reviewed_source_version_key="v2", idempotency_key=key, now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "idempotency_mismatch")
        self.assertEqual(len(self.harness.repository.saves_for_owner("alice")), 1)

    def test_save_opportunity_replay_re_renders_live_state_not_frozen_receipt(self):
        # MINOR 8: the identity guarantee (no duplicate row, no
        # re-execution) is proven by the receipt; the RETURNED snapshot is
        # re-read live. If the save is later removed and finalized (via a
        # separate command/idempotency key), replaying the ORIGINAL
        # save_opportunity call must reflect that current truth.
        key = self.harness.key("idem")
        first = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        self.harness.service.remove_saved("alice", save_key=first.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)

        replay = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=late,
        )
        self.assertEqual(replay.save_key, first.save_key)  # same identity, no duplicate
        self.assertEqual(replay.state, SAVE_STATE_REMOVED)  # live truth, not the frozen "saved" snapshot

    def test_save_during_undo_window_performs_undo_and_survives_window_elapse(self):
        # BLOCKING 1 self-review fix: a Save pressed while the row is
        # `removing` (inside the undo window) must express intent to KEEP
        # the item -- the old code silently no-op'd (echoed success, wrote
        # nothing), and the row still vanished when the window elapsed.
        save = self.harness.save("alice")
        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW
        )
        resaved = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
        )
        self.assertEqual(resaved.save_key, save.save_key)  # same row, no duplicate
        self.assertEqual(resaved.state, SAVE_STATE_SAVED)
        self.assertIsNone(resaved.removal_requested_at)

        late = NOW + self.harness.limits.undo_window + timedelta(seconds=5)
        stored = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(stored.state, SAVE_STATE_SAVED)  # never finalized -- it was truly saved
        entries = self.harness.service.list_saved("alice", now=late)
        self.assertEqual([e.save.save_key for e in entries], [save.save_key])
        self.assertEqual(entries[0].save.state, SAVE_STATE_SAVED)

    def test_save_during_undo_window_receipt_replays_correctly(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW
        )
        key = self.harness.key("save")
        first = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        replay = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        self.assertEqual(first, replay)
        self.assertEqual(replay.state, SAVE_STATE_SAVED)
        self.assertEqual(len(self.harness.repository.saves_for_owner("alice")), 1)

    def test_cross_member_save_against_removing_row_is_untouched_not_found_isolation(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW
        )
        alice_row_before = self.harness.repository.save_for_owner("alice", save.save_key)

        # Bob's save_opportunity against the SAME opportunity looks up his
        # OWN owner-scoped active-save index entry (keyed by (user_key,
        # opportunity_key)) -- it structurally cannot see or touch Alice's
        # `removing` row, so it creates Bob's own new row instead.
        bob_save = self.harness.service.save_opportunity(
            "bob", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
        )
        self.assertNotEqual(bob_save.save_key, save.save_key)
        alice_row_after = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(alice_row_after, alice_row_before)  # byte-unchanged

        # Cross-member direct key access remains the identical not_found
        # isolation.
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.get_saved("bob", save.save_key, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_found")

    def test_save_during_window_then_explicit_undo_remove_is_refused_sanely_no_duplicate(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW
        )
        resaved = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
        )
        self.assertEqual(resaved.state, SAVE_STATE_SAVED)

        # An explicit undo_remove now that the row is already `saved` (no
        # window open) is refused not_removing -- sanely, not a crash, and
        # this refusal is itself naturally idempotent on replay (a refused
        # call records no receipt).
        undo_key = self.harness.key("undo")
        with self.assertRaises(RelationshipsServiceError) as first_ctx:
            self.harness.service.undo_remove(
                "alice", save_key=save.save_key, idempotency_key=undo_key, now=NOW
            )
        self.assertEqual(first_ctx.exception.failure_code, "not_removing")
        with self.assertRaises(RelationshipsServiceError) as second_ctx:
            self.harness.service.undo_remove(
                "alice", save_key=save.save_key, idempotency_key=undo_key, now=NOW
            )
        self.assertEqual(second_ctx.exception.failure_code, "not_removing")
        self.assertEqual(len(self.harness.repository.saves_for_owner("alice")), 1)

    def test_different_key_on_already_active_save_returns_existing_row_no_duplicate_no_event(self):
        # This test covers the `saved`-state no-op branch specifically;
        # see test_save_during_undo_window_performs_undo_and_survives_window_elapse
        # above for the sibling `removing`-state undo-transition branch.
        first = self.harness.save("alice")
        digest_before = self.harness.repository.state_digest()
        events_before = len(self.harness.audit.events)
        second = self.harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
        )
        self.assertEqual(first.save_key, second.save_key)
        self.assertEqual(len(self.harness.repository.saves_for_owner("alice")), 1)
        self.assertEqual(self.harness.repository.state_digest(), digest_before)
        self.assertEqual(len(self.harness.audit.events), events_before)

    def test_save_never_opens_or_creates_a_slate(self):
        self.harness.save("alice")
        self.assertEqual(self.harness.repository.links_for_owner("alice"), ())
        kinds = {event.event_kind for event in self.harness.audit.events}
        self.assertNotIn("slate_link_recorded", kinds)

    def test_resave_after_removal_creates_new_row_old_row_stays_removed_byte_identical(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)
        removed_row = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(removed_row.state, SAVE_STATE_REMOVED)

        resaved = self.harness.save("alice", now=late)
        self.assertNotEqual(resaved.save_key, save.save_key)
        self.assertEqual(resaved.state, SAVE_STATE_SAVED)
        still_removed = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(still_removed, removed_row)

    def test_unknown_opportunity_or_wrong_data_class_is_not_found_no_bleed(self):
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.save_opportunity(
                "alice", opportunity_key="ghost", data_class="fixture",
                reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "not_found")

        with self.assertRaises(RelationshipsServiceError) as ctx2:
            self.harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="production",
                reviewed_source_version_key="v1", idempotency_key=self.harness.key("save"), now=NOW,
            )
        self.assertEqual(ctx2.exception.failure_code, "not_found")


# ---------------------------------------------------------------------------
# B. Remove/undo/window (doc 16 rows 32, 68)
# ---------------------------------------------------------------------------


class RemoveUndoWindowTests(RelationshipsTestCase):
    def test_remove_transitions_to_removing_replay_safe(self):
        save = self.harness.save("alice")
        key = self.harness.key("rm")
        removed = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(removed.state, SAVE_STATE_REMOVING)
        self.assertEqual(removed.removal_requested_at, NOW)
        replay = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(replay, removed)

    def test_second_remove_different_key_is_noop_returning_removing(self):
        save = self.harness.save("alice")
        first = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        second = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        self.assertEqual(first, second)
        self.assertEqual(second.state, SAVE_STATE_REMOVING)

    def test_undo_inside_window_returns_to_saved_replay_safe(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        key = self.harness.key("undo")
        undone = self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(undone.state, SAVE_STATE_SAVED)
        self.assertIsNone(undone.removal_requested_at)
        replay = self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(replay, undone)

    def test_undo_at_exact_boundary_and_after_finalizes_and_refuses_never_resurrects(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        boundary = NOW + self.harness.limits.undo_window
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=self.harness.key("undo"), now=boundary)
        self.assertEqual(ctx.exception.failure_code, "undo_window_elapsed")
        self.assertEqual(ctx.exception.current_state.state, SAVE_STATE_REMOVED)
        self.assertEqual(ctx.exception.current_state.removed_at, boundary)

        with self.assertRaises(RelationshipsServiceError) as ctx2:
            self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=self.harness.key("undo"), now=boundary + timedelta(minutes=5))
        self.assertEqual(ctx2.exception.failure_code, "undo_window_elapsed")
        self.assertEqual(ctx2.exception.current_state.state, SAVE_STATE_REMOVED)

    def test_undo_on_saved_is_not_removing_on_removed_is_window_elapsed(self):
        save = self.harness.save("alice")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=self.harness.key("undo"), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "not_removing")
        self.assertEqual(ctx.exception.current_state.state, SAVE_STATE_SAVED)

        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)
        with self.assertRaises(RelationshipsServiceError) as ctx2:
            self.harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=self.harness.key("undo"), now=late)
        self.assertEqual(ctx2.exception.failure_code, "undo_window_elapsed")

    def test_lazy_finalization_reads_as_removed_and_excluded_from_list(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=5)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.get_saved("alice", save.save_key, now=late)
        self.assertEqual(ctx.exception.failure_code, "not_found")
        entries = self.harness.service.list_saved("alice", now=late)
        self.assertEqual(entries, ())
        stored = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(stored.state, SAVE_STATE_REMOVED)
        # removed_at is the exact boundary (removal_requested_at + undo_window),
        # not the observation time `late`.
        self.assertEqual(stored.removed_at, stored.removal_requested_at + self.harness.limits.undo_window)

    def test_finalize_elapsed_removals_is_bounded_idempotent_content_blind(self):
        saves = [self.harness.save("alice", opportunity_key=self.harness.admit(f"opp-{i}")) for i in range(3)]
        for save in saves:
            self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        count_first = self.harness.service.finalize_elapsed_removals(now=late, limit=2)
        self.assertEqual(count_first, 2)
        count_second = self.harness.service.finalize_elapsed_removals(now=late, limit=500)
        self.assertEqual(count_second, 1)
        count_third = self.harness.service.finalize_elapsed_removals(now=late, limit=500)
        self.assertEqual(count_third, 0)
        for save in saves:
            self.assertEqual(self.harness.repository.save_for_owner("alice", save.save_key).state, SAVE_STATE_REMOVED)
        # content-blind: audit events carry only keys, never opportunity/display content
        for event in self.harness.audit.events:
            if event.event_kind == "save_remove_finalized":
                self.assertEqual(event.actor, "system:finalize_sweep")

    def test_configurable_undo_window_is_honored_and_nonpositive_refused_at_construction(self):
        harness = Harness(limits=RelationshipsLimits(undo_window=timedelta(seconds=5)))
        harness.admit()
        save = harness.save("alice")
        harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=harness.key("rm"), now=NOW)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.undo_remove("alice", save_key=save.save_key, idempotency_key=harness.key("undo"), now=NOW + timedelta(seconds=6))
        self.assertEqual(ctx.exception.failure_code, "undo_window_elapsed")

        with self.assertRaises(ValueError):
            RelationshipsLimits(undo_window=timedelta(0))
        with self.assertRaises(ValueError):
            RelationshipsLimits(undo_window=timedelta(seconds=-1))

    def test_replay_after_terminal_finalization_returns_removed_with_no_undo_affordance(self):
        # MINOR 8: replay re-renders live state rather than echoing the
        # frozen receipt -- a member retrying the same remove_saved
        # request after the row has since finalized to `removed` must see
        # that truth (state == removed, no undo affordance), not a stale
        # "removing" snapshot.
        save = self.harness.save("alice")
        key = self.harness.key("rm")
        removed = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(removed.state, SAVE_STATE_REMOVING)

        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)

        replay = self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=late)
        self.assertEqual(replay.state, SAVE_STATE_REMOVED)
        self.assertIsNotNone(replay.removed_at)
        # An undo affordance is only ever offered while state == removing;
        # the replay must never resurrect that stale affordance.
        self.assertNotEqual(replay.state, SAVE_STATE_REMOVING)

    def test_undo_remove_replay_after_re_remove_and_window_elapse_returns_removed_not_saved(self):
        # IMPORTANT 2 self-review fix (reviewer's exact scenario): undo,
        # re-remove, let the window elapse, then replay the ORIGINAL undo
        # idempotency key. The receipt proves that exact undo command was
        # already accepted, but the RETURNED snapshot must reflect current
        # truth -- the row has since been removed again and finalized --
        # not the stale `saved` snapshot frozen at the original undo.
        save = self.harness.save("alice")
        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm1"), now=NOW
        )
        undo_key = self.harness.key("undo")
        undone = self.harness.service.undo_remove(
            "alice", save_key=save.save_key, idempotency_key=undo_key, now=NOW
        )
        self.assertEqual(undone.state, SAVE_STATE_SAVED)

        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm2"), now=NOW
        )
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)

        replay = self.harness.service.undo_remove(
            "alice", save_key=save.save_key, idempotency_key=undo_key, now=late
        )
        self.assertEqual(replay.state, SAVE_STATE_REMOVED)
        self.assertNotEqual(replay.state, SAVE_STATE_SAVED)


# ---------------------------------------------------------------------------
# C. Overlays (doc 16 rows 31, 34, 35, 65; doc 03 §§1-2, 7; REC-03)
# ---------------------------------------------------------------------------


class OverlayDerivationTests(unittest.TestCase):
    def test_current_and_same_governing_version_yields_no_overlays(self):
        basis = GoverningBasis("opp-1", "fixture", "current", "v1", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), ())

    def test_listing_changed_yields_posting_changed(self):
        basis = GoverningBasis("opp-1", "fixture", "changed", "v1", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_POSTING_CHANGED,))

    def test_governing_version_differs_from_reference_yields_posting_changed_after_readmission(self):
        # REC-03: listing back to current, but the governing version moved
        # past what the member last reviewed -- posting_changed persists in
        # the member's context until they review it.
        basis = GoverningBasis("opp-1", "fixture", "current", "v2", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_POSTING_CHANGED,))

    def test_governing_failover_with_equivalent_clauses_still_yields_posting_changed(self):
        # doc 03 §2: any accepted governing change drives posting_changed,
        # including an equivalent-clause failover -- the derivation has no
        # notion of "equivalent," it only compares version identity.
        basis = GoverningBasis("opp-1", "fixture", "current", "v1-failover", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_POSTING_CHANGED,))

    def test_closed_yields_closed_by_source(self):
        basis = GoverningBasis("opp-1", "fixture", "closed", "v1", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_CLOSED_BY_SOURCE,))

    def test_unreachable_family_yields_could_not_reverify(self):
        for listing_state in ("unreachable", "stale", "quarantined", "invalid", "intake"):
            basis = GoverningBasis("opp-1", "fixture", listing_state, "v1", NOW, NOW)
            self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_COULD_NOT_REVERIFY,))

    def test_absent_basis_yields_could_not_reverify(self):
        self.assertEqual(derive_lifecycle_overlays("v1", None), (OVERLAY_COULD_NOT_REVERIFY,))

    def test_coexistence_unreviewed_change_then_closure_yields_both_in_order(self):
        basis = GoverningBasis("opp-1", "fixture", "closed", "v2", NOW, NOW)
        self.assertEqual(derive_lifecycle_overlays("v1", basis), (OVERLAY_POSTING_CHANGED, OVERLAY_CLOSED_BY_SOURCE))

    def test_derivation_accepts_no_repository_signature_fenced(self):
        params = list(inspect.signature(derive_lifecycle_overlays).parameters)
        self.assertEqual(params, ["reference_source_version_key", "basis"])


class OverlayServiceIntegrationTests(RelationshipsTestCase):
    def test_list_saved_and_get_saved_leave_state_digest_unchanged_when_no_finalization_due(self):
        save = self.harness.save("alice")
        digest_before = self.harness.repository.state_digest()
        self.harness.service.list_saved("alice", now=NOW)
        self.harness.service.get_saved("alice", save.save_key, now=NOW)
        self.assertEqual(self.harness.repository.state_digest(), digest_before)

    def test_mark_change_reviewed_clears_posting_changed_for_that_member_only(self):
        save_a = self.harness.save("alice", reviewed="v1")
        save_b = self.harness.save("bob", reviewed="v1")
        self.harness.basis_reader.set_basis("opp-1", "fixture", listing_state="current", governing_source_version_key="v2")

        entry_a = self.harness.service.get_saved("alice", save_a.save_key, now=NOW)
        self.assertIn(OVERLAY_POSTING_CHANGED, entry_a.overlays)

        updated = self.harness.service.mark_change_reviewed(
            "alice", save_key=save_a.save_key, reviewed_source_version_key="v2",
            idempotency_key=self.harness.key("rev"), now=NOW,
        )
        self.assertEqual(updated.last_reviewed_source_version_key, "v2")
        entry_a_after = self.harness.service.get_saved("alice", save_a.save_key, now=NOW)
        self.assertEqual(entry_a_after.overlays, ())

        entry_b = self.harness.service.get_saved("bob", save_b.save_key, now=NOW)
        self.assertIn(OVERLAY_POSTING_CHANGED, entry_b.overlays)

    def test_mark_change_reviewed_refuses_while_listing_state_is_changed_no_mutation(self):
        # BLOCKER 2 self-review adjudication (option b): while the listing
        # is mid re-verification, reviewing even the CURRENT governing
        # version would be a dead end -- derive_lifecycle_overlays's rule 2
        # keeps posting_changed live for any "changed" listing_state
        # regardless of version match, so the write must refuse rather than
        # silently no-op the member's review.
        save = self.harness.save("alice", reviewed="v1")
        self.harness.basis_reader.set_basis("opp-1", "fixture", listing_state="changed", governing_source_version_key="v1")
        digest_before = self.harness.repository.state_digest()
        events_before = len(self.harness.audit.events)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_change_reviewed(
                "alice", save_key=save.save_key, reviewed_source_version_key="v1",
                idempotency_key=self.harness.key("rev"), now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "review_version_not_governing")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(ctx.exception.current_state, save)
        self.assertEqual(self.harness.repository.state_digest(), digest_before)
        self.assertEqual(len(self.harness.audit.events), events_before)
        entry = self.harness.service.get_saved("alice", save.save_key, now=NOW)
        self.assertIn(OVERLAY_POSTING_CHANGED, entry.overlays)

    def test_mark_change_reviewed_succeeds_when_version_moved_and_listing_is_current(self):
        # The successful-clear sibling of the refusal above: once the
        # listing has settled back to "current" (re-verification
        # confirmed) and the member reviews the now-governing version,
        # the write proceeds and clears the overlay.
        save = self.harness.save("alice", reviewed="v1")
        self.harness.basis_reader.set_basis("opp-1", "fixture", listing_state="current", governing_source_version_key="v2")
        updated = self.harness.service.mark_change_reviewed(
            "alice", save_key=save.save_key, reviewed_source_version_key="v2",
            idempotency_key=self.harness.key("rev"), now=NOW,
        )
        self.assertEqual(updated.last_reviewed_source_version_key, "v2")
        entry = self.harness.service.get_saved("alice", save.save_key, now=NOW)
        self.assertEqual(entry.overlays, ())

    def test_mark_change_reviewed_with_stale_version_refuses_and_overlay_stays(self):
        save = self.harness.save("alice", reviewed="v1")
        self.harness.basis_reader.set_basis("opp-1", "fixture", listing_state="current", governing_source_version_key="v3")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_change_reviewed(
                "alice", save_key=save.save_key, reviewed_source_version_key="v2",
                idempotency_key=self.harness.key("rev"), now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "review_version_not_governing")
        self.assertTrue(ctx.exception.recoverable)
        entry = self.harness.service.get_saved("alice", save.save_key, now=NOW)
        self.assertIn(OVERLAY_POSTING_CHANGED, entry.overlays)

    def test_mark_change_reviewed_on_removed_save_refuses_save_removed(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_change_reviewed(
                "alice", save_key=save.save_key, reviewed_source_version_key="v1",
                idempotency_key=self.harness.key("rev"), now=late,
            )
        self.assertEqual(ctx.exception.failure_code, "save_removed")

    def test_mark_change_reviewed_replay_after_later_removal_and_window_elapse_returns_removed(self):
        # IMPORTANT 2 self-review fix: same shape as the undo_remove
        # replay-staleness fix -- a successful mark_change_reviewed's
        # receipt proves that exact review command was accepted, but a
        # later replay must re-render LIVE state. If the row is removed
        # and finalized after the review, replaying the original review
        # key must return `removed`, not the stale `saved` snapshot
        # frozen at review time.
        save = self.harness.save("alice", reviewed="v1")
        self.harness.basis_reader.set_basis(
            "opp-1", "fixture", listing_state="current", governing_source_version_key="v2"
        )
        review_key = self.harness.key("rev")
        reviewed = self.harness.service.mark_change_reviewed(
            "alice", save_key=save.save_key, reviewed_source_version_key="v2",
            idempotency_key=review_key, now=NOW,
        )
        self.assertEqual(reviewed.state, SAVE_STATE_SAVED)
        self.assertEqual(reviewed.last_reviewed_source_version_key, "v2")

        self.harness.service.remove_saved(
            "alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW
        )
        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        self.harness.service.finalize_elapsed_removals(now=late)

        replay = self.harness.service.mark_change_reviewed(
            "alice", save_key=save.save_key, reviewed_source_version_key="v2",
            idempotency_key=review_key, now=late,
        )
        self.assertEqual(replay.state, SAVE_STATE_REMOVED)
        self.assertNotEqual(replay.state, SAVE_STATE_SAVED)

    def test_row_65_stale_result_slice_reuses_pure_derivation_without_touching_c4(self):
        # C8's stale-result rendering reuses the same pure function against a
        # result entry's result-time basis; proven here by calling it with a
        # bare reference string with no SavedOpportunity/repository involved.
        basis = GoverningBasis("opp-9", "fixture", "unreachable", "v9", NOW, NOW)
        overlays = derive_lifecycle_overlays("v9", basis)
        self.assertEqual(overlays, (OVERLAY_COULD_NOT_REVERIFY,))


# ---------------------------------------------------------------------------
# D. Saved-view local search/filter (doc 16 rows 31, 55; doc 03 §7)
# ---------------------------------------------------------------------------


class SavedViewTests(RelationshipsTestCase):
    def _seed_mixed(self, user_key="alice"):
        current_opp = self.harness.admit("opp-current")
        self.harness.basis_reader.set_display(current_opp, "fixture", "Backend Engineer", "Zenith")
        changed_opp = self.harness.admit("opp-changed")
        self.harness.basis_reader.set_display(changed_opp, "fixture", "Data Engineer", "Astraeus")
        closed_opp = self.harness.admit("opp-closed", listing_state="closed")
        self.harness.basis_reader.set_display(closed_opp, "fixture", "Recruiter", "Halcyon")
        unreachable_opp = self.harness.admit("opp-unreachable", listing_state="unreachable")
        self.harness.basis_reader.set_display(unreachable_opp, "fixture", "Ops Engineer", "Meridian")

        current = self.harness.service.save_opportunity(
            user_key, opportunity_key=current_opp, data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("s"), now=NOW,
        )
        changed = self.harness.service.save_opportunity(
            user_key, opportunity_key=changed_opp, data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("s"), now=NOW,
        )
        self.harness.basis_reader.set_basis(changed_opp, "fixture", listing_state="changed", governing_source_version_key="v1")
        closed = self.harness.service.save_opportunity(
            user_key, opportunity_key=closed_opp, data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("s"), now=NOW,
        )
        unreachable = self.harness.service.save_opportunity(
            user_key, opportunity_key=unreachable_opp, data_class="fixture",
            reviewed_source_version_key="v1", idempotency_key=self.harness.key("s"), now=NOW,
        )
        return current, changed, closed, unreachable

    def test_owner_scoped_and_mixed_states_visible_under_all(self):
        current, changed, closed, unreachable = self._seed_mixed("alice")
        entries = self.harness.service.list_saved("alice", now=NOW)
        self.assertEqual(len(entries), 4)
        keys = {entry.save.save_key for entry in entries}
        self.assertEqual(keys, {current.save_key, changed.save_key, closed.save_key, unreachable.save_key})

    def test_each_saved_state_filter_selects_exactly_its_overlay_class(self):
        current, changed, closed, unreachable = self._seed_mixed("alice")
        by_filter = {
            SAVED_FILTER_CURRENT: {current.save_key},
            SAVED_FILTER_CHANGED: {changed.save_key},
            SAVED_FILTER_CLOSED: {closed.save_key},
            SAVED_FILTER_UNREACHABLE: {unreachable.save_key},
        }
        for filter_value, expected_keys in by_filter.items():
            entries = self.harness.service.list_saved("alice", saved_state_filter=filter_value, now=NOW)
            self.assertEqual({entry.save.save_key for entry in entries}, expected_keys, filter_value)
        all_entries = self.harness.service.list_saved("alice", saved_state_filter=SAVED_FILTER_ALL, now=NOW)
        self.assertEqual(len(all_entries), 4)

    def test_verification_filter_matches_gate_vocabulary_plus_not_assessed(self):
        self._seed_mixed("alice")
        self.harness.verification_reader.set_outcome("alice", "opp-current", GATE_FULLY_VERIFIED)
        self.harness.verification_reader.set_outcome("alice", "opp-changed", GATE_NOT_FULLY_VERIFIED)
        verified = self.harness.service.list_saved("alice", verification_filter=GATE_FULLY_VERIFIED, now=NOW)
        self.assertEqual({e.save.opportunity_key for e in verified}, {"opp-current"})
        not_verified = self.harness.service.list_saved("alice", verification_filter=GATE_NOT_FULLY_VERIFIED, now=NOW)
        self.assertEqual({e.save.opportunity_key for e in not_verified}, {"opp-changed"})
        not_assessed = self.harness.service.list_saved("alice", verification_filter=VERIFICATION_NOT_ASSESSED, now=NOW)
        self.assertEqual({e.save.opportunity_key for e in not_assessed}, {"opp-closed", "opp-unreachable"})

    def test_unknown_filter_values_refuse_filter_invalid(self):
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.list_saved("alice", saved_state_filter="bogus", now=NOW)
        self.assertEqual(ctx.exception.failure_code, "filter_invalid")
        with self.assertRaises(RelationshipsServiceError) as ctx2:
            self.harness.service.list_saved("alice", verification_filter="bogus", now=NOW)
        self.assertEqual(ctx2.exception.failure_code, "filter_invalid")

    def test_free_text_search_casefolded_over_role_title_and_employer_only(self):
        self._seed_mixed("alice")
        by_role = self.harness.service.list_saved("alice", search_text="BACKEND", now=NOW)
        self.assertEqual({e.save.opportunity_key for e in by_role}, {"opp-current"})
        by_employer = self.harness.service.list_saved("alice", search_text="astraeus", now=NOW)
        self.assertEqual({e.save.opportunity_key for e in by_employer}, {"opp-changed"})
        none_match = self.harness.service.list_saved("alice", search_text="nonexistent-employer-xyz", now=NOW)
        self.assertEqual(none_match, ())

    def test_search_text_bounded_past_300_units(self):
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.list_saved("alice", search_text="x" * 301, now=NOW)
        self.assertEqual(ctx.exception.failure_code, "search_text_too_long")

    def test_rights_removed_display_facts_yield_truthful_unavailable_never_match_but_reachable_under_all(self):
        opp = "opp-hidden"
        self.harness.basis_reader.set_basis(opp, "fixture")  # basis present, NO display_facts set -> unavailable
        save = self.harness.service.save_opportunity(
            "alice", opportunity_key=opp, data_class="fixture", reviewed_source_version_key="v1",
            idempotency_key=self.harness.key("s"), now=NOW,
        )
        matched = self.harness.service.list_saved("alice", search_text="anything", now=NOW)
        self.assertEqual(matched, ())
        under_all = self.harness.service.list_saved("alice", now=NOW)
        self.assertEqual({e.save.save_key for e in under_all}, {save.save_key})
        entry = under_all[0]
        self.assertIsNone(entry.display.role_title)
        self.assertIsNone(entry.display.employer_name)

    def test_no_ai_index_snapshot_dependency_and_deterministic_order(self):
        params = inspect.signature(RelationshipsService.__init__).parameters
        for forbidden in ("index", "snapshot", "provider", "ai"):
            self.assertNotIn(forbidden, params)

        opp_a = self.harness.admit("opp-a")
        opp_b = self.harness.admit("opp-b")
        save_a = self.harness.service.save_opportunity(
            "alice", opportunity_key=opp_a, data_class="fixture", reviewed_source_version_key="v1",
            idempotency_key=self.harness.key("s"), now=NOW,
        )
        save_b = self.harness.service.save_opportunity(
            "alice", opportunity_key=opp_b, data_class="fixture", reviewed_source_version_key="v1",
            idempotency_key=self.harness.key("s"), now=NOW + timedelta(seconds=1),
        )
        entries = self.harness.service.list_saved("alice", now=NOW + timedelta(minutes=1))
        self.assertEqual([e.save.save_key for e in entries], [save_b.save_key, save_a.save_key])

    def test_removing_rows_listed_removed_rows_excluded(self):
        save = self.harness.save("alice")
        self.harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        entries = self.harness.service.list_saved("alice", now=NOW)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].save.state, SAVE_STATE_REMOVING)

        late = NOW + self.harness.limits.undo_window + timedelta(seconds=1)
        entries_after = self.harness.service.list_saved("alice", now=late)
        self.assertEqual(entries_after, ())

    def test_cross_member_row_55_bs_filters_never_surface_alices_rows(self):
        self._seed_mixed("alice")
        for filter_value in SAVED_STATE_FILTERS:
            entries = self.harness.service.list_saved("bob", saved_state_filter=filter_value, now=NOW)
            self.assertEqual(entries, ())
        for verification_value in VERIFICATION_FILTERS:
            entries = self.harness.service.list_saved("bob", verification_filter=verification_value, now=NOW)
            self.assertEqual(entries, ())
        entries = self.harness.service.list_saved("bob", search_text="astraeus", now=NOW)
        self.assertEqual(entries, ())


# ---------------------------------------------------------------------------
# E. Slate-link persistence (doc 03 §8 slice; doc 02 §1)
# ---------------------------------------------------------------------------


class SlateLinkTests(RelationshipsTestCase):
    def _record(self, user_key="alice", opportunity_key="opp-1", created_from=CREATED_FROM_RESULT, ref="ws-1", now=NOW):
        return self.harness.service.record_slate_link(
            user_key, opportunity_key=opportunity_key, data_class="fixture",
            slate_workspace_ref=ref, created_from=created_from, handoff_source_version_key="v1",
            idempotency_key=self.harness.key("link"), now=now,
        )

    def test_record_link_creates_linked_row_replay_safe(self):
        key = self.harness.key("link")
        link = self.harness.service.record_slate_link(
            "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
            created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        self.assertEqual(link.state, LINK_STATE_LINKED)
        self.assertEqual(link.created_from, CREATED_FROM_RESULT)
        self.assertEqual(link.handoff_source_version_key, "v1")
        replay = self.harness.service.record_slate_link(
            "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
            created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1", idempotency_key=key, now=NOW,
        )
        self.assertEqual(replay, link)

    def test_second_active_link_same_opportunity_refuses_active_link_exists_carrying_existing(self):
        link = self._record()
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self._record(ref="ws-2")
        self.assertEqual(ctx.exception.failure_code, "active_link_exists")
        self.assertEqual(ctx.exception.current_state, link)

    def test_different_opportunity_links_fine(self):
        opp2 = self.harness.admit("opp-2")
        link1 = self._record(opportunity_key="opp-1")
        link2 = self._record(opportunity_key=opp2, ref="ws-2")
        self.assertNotEqual(link1.link_key, link2.link_key)

    def test_after_unlinked_new_link_may_be_recorded_history_preserved(self):
        link1 = self._record()
        self.harness.service.mark_slate_unlinked("alice", link_key=link1.link_key, idempotency_key=self.harness.key("un"), now=NOW)
        link2 = self._record(ref="ws-2", now=NOW + timedelta(seconds=1))
        self.assertNotEqual(link1.link_key, link2.link_key)
        all_links = self.harness.service.list_slate_links("alice")
        self.assertEqual({link.link_key for link in all_links}, {link1.link_key, link2.link_key})

    def test_mark_slate_unlinked_terminal_and_never_cascades_to_save(self):
        save = self.harness.save("alice")
        link = self._record()
        digest_saves_before = self.harness.repository.saves_for_owner("alice")
        unlinked = self.harness.service.mark_slate_unlinked("alice", link_key=link.link_key, idempotency_key=self.harness.key("un"), now=NOW)
        self.assertEqual(unlinked.state, LINK_STATE_UNLINKED)
        self.assertEqual(unlinked.unlinked_at, NOW)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_slate_unlinked("alice", link_key=link.link_key, idempotency_key=self.harness.key("un2"), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "link_unlinked")
        after = self.harness.repository.save_for_owner("alice", save.save_key)
        self.assertEqual(after, save)
        self.assertEqual(self.harness.repository.saves_for_owner("alice"), digest_saves_before)

    def test_link_create_never_saves_save_store_digest_unchanged(self):
        save_before = self.harness.repository.saves_for_owner("alice")
        self._record()
        save_after = self.harness.repository.saves_for_owner("alice")
        self.assertEqual(save_before, save_after)

    def test_c7_boundary_no_command_symbol_exported_no_workspace_creation_import(self):
        import services.my_opportunities.relationships_service as module

        for forbidden in ("create_slate_from_opportunity", "continue_slate", "list_slate_history"):
            self.assertFalse(hasattr(module, forbidden))

        # MINOR 11: a plain "import slate" substring search is weak (it
        # both misses non-substring import spellings and can false-positive
        # on unrelated text/comments). Parse the module's own source into
        # an AST and collect the actual imported module set instead.
        source = inspect.getsource(module)
        tree = ast.parse(source)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        self.assertFalse(
            any("slate" in name.lower() for name in imported_modules),
            f"relationships_service.py must import no Slate module (found: {imported_modules})",
        )


# ---------------------------------------------------------------------------
# F. Negative multi-member proofs (doc 08 §7; doc 14 C6 verifier row)
# ---------------------------------------------------------------------------


class CrossMemberIsolationTests(RelationshipsTestCase):
    def test_direct_key_access_cross_owner_and_absent_are_not_found(self):
        save = self.harness.save("alice")
        link = self.harness.service.record_slate_link(
            "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
            created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
            idempotency_key=self.harness.key("link"), now=NOW,
        )

        cross_owner_errors = []
        absent_errors = []

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.get_saved("bob", save.save_key, now=NOW)
        cross_owner_errors.append(ctx.exception)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.get_saved("alice", "totally-absent-key", now=NOW)
        absent_errors.append(ctx.exception)

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.remove_saved("bob", save_key=save.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        cross_owner_errors.append(ctx.exception)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.remove_saved("alice", save_key="totally-absent-key", idempotency_key=self.harness.key("rm"), now=NOW)
        absent_errors.append(ctx.exception)

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.undo_remove("bob", save_key=save.save_key, idempotency_key=self.harness.key("undo"), now=NOW)
        cross_owner_errors.append(ctx.exception)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.undo_remove("alice", save_key="totally-absent-key", idempotency_key=self.harness.key("undo"), now=NOW)
        absent_errors.append(ctx.exception)

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_change_reviewed(
                "bob", save_key=save.save_key, reviewed_source_version_key="v1",
                idempotency_key=self.harness.key("rev"), now=NOW,
            )
        cross_owner_errors.append(ctx.exception)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_change_reviewed(
                "alice", save_key="totally-absent-key", reviewed_source_version_key="v1",
                idempotency_key=self.harness.key("rev"), now=NOW,
            )
        absent_errors.append(ctx.exception)

        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_slate_unlinked("bob", link_key=link.link_key, idempotency_key=self.harness.key("un"), now=NOW)
        cross_owner_errors.append(ctx.exception)
        with self.assertRaises(RelationshipsServiceError) as ctx:
            self.harness.service.mark_slate_unlinked("alice", link_key="totally-absent-key", idempotency_key=self.harness.key("un"), now=NOW)
        absent_errors.append(ctx.exception)

        for cross_error, absent_error in zip(cross_owner_errors, absent_errors):
            self.assertEqual(cross_error.failure_code, absent_error.failure_code)
            self.assertEqual(cross_error.member_message, absent_error.member_message)
            self.assertEqual(cross_error.failure_code, "not_found")
            self.assertIsNone(cross_error.current_state)
            self.assertIsNone(absent_error.current_state)
            self.assertEqual(type(cross_error), type(absent_error))

    def test_listing_surfaces_return_only_the_caller_owner(self):
        self.harness.save("alice")
        self.harness.service.record_slate_link(
            "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
            created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
            idempotency_key=self.harness.key("link"), now=NOW,
        )
        self.assertEqual(self.harness.service.list_saved("bob", now=NOW), ())
        self.assertEqual(self.harness.service.list_slate_links("bob"), ())

    def test_no_listing_surface_can_enumerate_another_members_rows(self):
        # Repository API census: every READ method on the
        # RelationshipsRepository Protocol takes user_key first and filters
        # IN the query -- no "all rows"/"all owners" listing method exists.
        # Write methods (persist_*/update_*) take a whole record whose
        # owner is embedded in the record, not a listing surface. The one
        # deliberate exception is `saves_with_elapsed_removals`, the
        # content-blind cross-owner sweep primitive (doc 08 §5 TTL
        # discipline): it is a system-only primitive never exposed to a
        # member, and it is content-blind (key + age only) even though it
        # necessarily spans owners to do its job.
        read_methods = (
            "save_for_owner",
            "active_save_for_opportunity",
            "saves_for_owner",
            "link_for_owner",
            "active_link_for_opportunity",
            "links_for_owner",
        )
        all_names = {
            name
            for name, _ in inspect.getmembers(RelationshipsRepository, predicate=inspect.isfunction)
            if not name.startswith("_")
        }
        self.assertEqual(set(read_methods), all_names - {"persist_save", "update_save", "persist_link", "update_link", "saves_with_elapsed_removals"})
        for name in read_methods:
            member = getattr(RelationshipsRepository, name)
            params = list(inspect.signature(member).parameters)
            self.assertIn("user_key", params, name)
            self.assertEqual(params[1] if params[0] == "self" else params[0], "user_key", name)

    def test_bs_own_operations_proceed_independently_alices_rows_byte_unchanged(self):
        save_a = self.harness.save("alice")
        save_b = self.harness.save("bob")
        digest_a_saves = self.harness.repository.save_for_owner("alice", save_a.save_key)

        self.harness.service.remove_saved("bob", save_key=save_b.save_key, idempotency_key=self.harness.key("rm"), now=NOW)
        self.harness.service.undo_remove("bob", save_key=save_b.save_key, idempotency_key=self.harness.key("undo"), now=NOW)

        still_a = self.harness.repository.save_for_owner("alice", save_a.save_key)
        self.assertEqual(still_a, digest_a_saves)

    def test_cross_owner_and_absent_probes_execute_same_code_path_no_early_exit_oracle(self):
        save = self.harness.save("alice")
        try:
            self.harness.service.get_saved("bob", save.save_key, now=NOW)
        except RelationshipsServiceError as cross_exc:
            cross_type, cross_code = type(cross_exc), cross_exc.failure_code
        try:
            self.harness.service.get_saved("alice", "nonexistent-key-zzz", now=NOW)
        except RelationshipsServiceError as absent_exc:
            absent_type, absent_code = type(absent_exc), absent_exc.failure_code
        self.assertEqual(cross_type, absent_type)
        self.assertEqual(cross_code, absent_code)


# ---------------------------------------------------------------------------
# G. Unknown-outcome write discipline (doc 16 row 68; doc 09 §4)
# ---------------------------------------------------------------------------


class UnknownOutcomeTests(RelationshipsTestCase):
    def _harness_with_failing_repo(self, fail_on, *, fail_mode="pre"):
        repo = FailingRelationshipsRepository(fail_on=fail_on, fail_mode=fail_mode)
        harness = Harness(repository=repo)
        harness.admit()
        return harness

    def test_persist_save_failure_is_save_outcome_unknown_recoverable_no_receipt_no_row(self):
        harness = self._harness_with_failing_repo({"persist_save"})
        key = harness.key("save")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=key, now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "save_outcome_unknown")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(harness.repository.saves_for_owner("alice"), ())
        kinds = [event.event_kind for event in harness.audit.events]
        self.assertIn("persistence_failure", kinds)
        for event in harness.audit.events:
            self.assertNotIn("opp-1", event.keys)  # content-free: no opportunity_key leaked into audit keys

    def test_immediate_blind_retry_same_key_is_retry_locked_before_any_repository_call(self):
        harness = self._harness_with_failing_repo({"persist_save"})
        key = harness.key("save")
        with self.assertRaises(RelationshipsServiceError):
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=key, now=NOW,
            )
        digest_before = harness.repository.state_digest()
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=key, now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "retry_locked_state_reload_required")
        self.assertTrue(ctx.exception.recoverable)
        self.assertEqual(harness.repository.state_digest(), digest_before)

    def test_state_reload_unlocks_retry_is_fresh_write_when_persist_did_not_land(self):
        # IMPORTANT 6 self-review correction: this test's original name and
        # docstring claimed to cover "the write actually landed," but with
        # the default fail_mode="pre" the simulated failure fires BEFORE
        # persist_save ever runs, so nothing is persisted on the first
        # attempt -- this exercises the DID-NOT-LAND branch (a fresh write
        # on retry), the sibling of
        # test_state_reload_unlocks_retry_is_fresh_write_when_update_did_not_land
        # for the save_opportunity/persist_save path specifically. See
        # test_state_reload_unlocks_retry_returns_the_landed_save_when_persist_did_land
        # below for the true landed-branch coverage this test previously,
        # incorrectly, claimed to provide.
        harness = self._harness_with_failing_repo({"persist_save"})
        key = harness.key("save")
        with self.assertRaises(RelationshipsServiceError):
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=key, now=NOW,
            )
        self.assertEqual(harness.repository.saves_for_owner("alice"), ())
        harness.service.list_saved("alice", now=NOW)  # state reload unlocks
        harness.repository._fail_on.discard("persist_save")
        result = harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
            idempotency_key=key, now=NOW,
        )
        self.assertEqual(result.state, SAVE_STATE_SAVED)
        self.assertEqual(len(harness.repository.saves_for_owner("alice")), 1)

    def test_state_reload_unlocks_retry_returns_the_landed_save_when_persist_did_land(self):
        # IMPORTANT 6: true landed-branch coverage using fail_mode="post"
        # -- the write DOES complete durably (super().persist_save
        # succeeds) but the confirmation never reaches the caller, so the
        # service still raises save_outcome_unknown and locks the
        # idempotency key. After a state reload, a retry with the SAME
        # idempotency key must discover the already-landed row via natural
        # idempotency (active_save_for_opportunity's "already active"
        # no-op branch) rather than create a duplicate -- it never even
        # needs to reach persist_save again on retry.
        harness = self._harness_with_failing_repo({"persist_save"}, fail_mode="post")
        key = harness.key("save")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=key, now=NOW,
            )
        self.assertEqual(ctx.exception.failure_code, "save_outcome_unknown")
        landed_rows = harness.repository.saves_for_owner("alice")
        self.assertEqual(len(landed_rows), 1)
        landed_save_key = landed_rows[0].save_key

        harness.service.list_saved("alice", now=NOW)  # state reload unlocks
        result = harness.service.save_opportunity(
            "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
            idempotency_key=key, now=NOW,
        )
        self.assertEqual(result.save_key, landed_save_key)
        self.assertEqual(len(harness.repository.saves_for_owner("alice")), 1)

    def test_state_reload_unlocks_retry_is_fresh_write_when_update_did_not_land(self):
        harness = self._harness_with_failing_repo({"update_save"})
        save = harness.save("alice")
        key = harness.key("rm")
        with self.assertRaises(RelationshipsServiceError):
            harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(harness.repository.save_for_owner("alice", save.save_key).state, SAVE_STATE_SAVED)
        harness.service.get_saved("alice", save.save_key, now=NOW)  # state reload unlocks
        harness.repository._fail_on.discard("update_save")
        result = harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=key, now=NOW)
        self.assertEqual(result.state, SAVE_STATE_REMOVING)

    def test_remove_undo_link_unlink_writes_all_go_through_unknown_outcome_path(self):
        harness = self._harness_with_failing_repo({"update_save"})
        save = harness.save("alice")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=harness.key("rm"), now=NOW)
        self.assertEqual(ctx.exception.failure_code, "save_outcome_unknown")

        harness2 = self._harness_with_failing_repo({"persist_link"})
        with self.assertRaises(RelationshipsServiceError) as ctx2:
            harness2.service.record_slate_link(
                "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
                created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
                idempotency_key=harness2.key("link"), now=NOW,
            )
        self.assertEqual(ctx2.exception.failure_code, "save_outcome_unknown")

        harness3 = self._harness_with_failing_repo({"update_link"})
        link = harness3.service.record_slate_link(
            "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
            created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
            idempotency_key=harness3.key("link"), now=NOW,
        )
        with self.assertRaises(RelationshipsServiceError) as ctx3:
            harness3.service.mark_slate_unlinked("alice", link_key=link.link_key, idempotency_key=harness3.key("un"), now=NOW)
        self.assertEqual(ctx3.exception.failure_code, "save_outcome_unknown")

    def test_get_saved_on_removed_row_still_clears_the_lock_minor_9(self):
        # MINOR 9: a successful owner load (found the row, confirmed
        # ownership) is itself the state reload doc 09 §4 promises unlocks
        # the blind-retry lockout -- even when that row turns out to be
        # `removed` and get_saved refuses not_found for it. A locked
        # member whose only row is removed must not be stuck.
        harness = self._harness_with_failing_repo({"persist_link"})
        save = harness.save("alice")
        harness.service.remove_saved("alice", save_key=save.save_key, idempotency_key=harness.key("rm"), now=NOW)
        late = NOW + harness.limits.undo_window + timedelta(seconds=1)
        harness.service.finalize_elapsed_removals(now=late)
        self.assertEqual(harness.repository.save_for_owner("alice", save.save_key).state, SAVE_STATE_REMOVED)

        link_key = harness.key("link")
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.record_slate_link(
                "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
                created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
                idempotency_key=link_key, now=late,
            )
        self.assertEqual(ctx.exception.failure_code, "save_outcome_unknown")
        with self.assertRaises(RelationshipsServiceError) as locked_ctx:
            harness.service.record_slate_link(
                "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
                created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
                idempotency_key=link_key, now=late,
            )
        self.assertEqual(locked_ctx.exception.failure_code, "retry_locked_state_reload_required")

        # The member's only row is removed: get_saved refuses not_found,
        # but this successful owner load must still clear the lock.
        with self.assertRaises(RelationshipsServiceError) as get_ctx:
            harness.service.get_saved("alice", save.save_key, now=late)
        self.assertEqual(get_ctx.exception.failure_code, "not_found")

        # A retry now proceeds (re-attempts the write) instead of being
        # refused retry_locked_state_reload_required.
        with self.assertRaises(RelationshipsServiceError) as retry_ctx:
            harness.service.record_slate_link(
                "alice", opportunity_key="opp-1", data_class="fixture", slate_workspace_ref="ws-1",
                created_from=CREATED_FROM_RESULT, handoff_source_version_key="v1",
                idempotency_key=link_key, now=late,
            )
        self.assertEqual(retry_ctx.exception.failure_code, "save_outcome_unknown")

    def test_failure_message_never_claims_write_did_or_did_not_land(self):
        harness = self._harness_with_failing_repo({"persist_save"})
        with self.assertRaises(RelationshipsServiceError) as ctx:
            harness.service.save_opportunity(
                "alice", opportunity_key="opp-1", data_class="fixture", reviewed_source_version_key="v1",
                idempotency_key=harness.key("save"), now=NOW,
            )
        message = ctx.exception.member_message.lower()
        for claim in ("was saved", "was not saved", "succeeded", "failed to save"):
            self.assertNotIn(claim, message)
        self.assertIn("couldn't confirm", message)


# ---------------------------------------------------------------------------
# H. Contract-freeze and cross-child shape tests
# ---------------------------------------------------------------------------


class ContractFreezeTests(unittest.TestCase):
    def test_c2_c5_contract_shapes_unchanged(self):
        self.assertEqual(DATA_CLASSES, frozenset({"fixture", "production"}))
        self.assertEqual(
            LISTING_STATES,
            frozenset({"intake", "current", "changed", "closed", "unreachable", "stale", "quarantined", "invalid"}),
        )
        self.assertEqual(GATE_FULLY_VERIFIED, "fully_verified")
        self.assertEqual(GATE_NOT_FULLY_VERIFIED, "not_fully_verified")

    def test_module_vocabulary_closure(self):
        self.assertEqual(SAVE_STATES, {SAVE_STATE_SAVED, SAVE_STATE_REMOVING, SAVE_STATE_REMOVED})
        self.assertEqual(OVERLAYS, {OVERLAY_POSTING_CHANGED, OVERLAY_CLOSED_BY_SOURCE, OVERLAY_COULD_NOT_REVERIFY})
        self.assertEqual(OVERLAY_ORDER, (OVERLAY_POSTING_CHANGED, OVERLAY_CLOSED_BY_SOURCE, OVERLAY_COULD_NOT_REVERIFY))
        self.assertEqual(LINK_STATES, {LINK_STATE_LINKED, LINK_STATE_UNLINKED})
        self.assertEqual(CREATED_FROM_SOURCES, {CREATED_FROM_RESULT, CREATED_FROM_SAVED})
        self.assertEqual(
            SAVED_STATE_FILTERS,
            {SAVED_FILTER_ALL, SAVED_FILTER_CURRENT, SAVED_FILTER_CHANGED, SAVED_FILTER_CLOSED, SAVED_FILTER_UNREACHABLE},
        )
        self.assertEqual(VERIFICATION_FILTERS, {"all", GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED, VERIFICATION_NOT_ASSESSED})
        self.assertEqual(VERIFICATION_OUTCOMES, {GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED, VERIFICATION_NOT_ASSESSED})

    def test_record_shape_pairing_validation(self):
        with self.assertRaises(ValueError):
            SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_SAVED, NOW, NOW, None)
        with self.assertRaises(ValueError):
            SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_REMOVING, NOW, None, None)
        with self.assertRaises(ValueError):
            SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_REMOVED, NOW, NOW, None)
        with self.assertRaises(ValueError):
            SlateLink("k", "u", "fixture", "o", "ws", CREATED_FROM_RESULT, "v1", LINK_STATE_LINKED, NOW, NOW)
        with self.assertRaises(ValueError):
            SlateLink("k", "u", "fixture", "o", "ws", CREATED_FROM_RESULT, "v1", LINK_STATE_UNLINKED, NOW, None)
        with self.assertRaises(ValueError):
            GoverningBasis("o", "fixture", "bogus-state", "v1", NOW, NOW)

    def test_python_post_init_mirrors_the_sql_timestamp_ordering_checks(self):
        # MINOR 10: CK_myopp_saved_opportunities_removal_after_save
        # (removal_requested_at >= saved_at) and the unlinked_at >=
        # created_at clause of CK_myopp_slate_links_state_timestamps are
        # SQL invariants that must also be enforced in Python, not only at
        # the database layer.
        earlier = NOW - timedelta(seconds=1)
        with self.assertRaises(ValueError):
            SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_REMOVING, NOW, earlier, None)
        with self.assertRaises(ValueError):
            SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_REMOVED, NOW, earlier, NOW)
        with self.assertRaises(ValueError):
            SlateLink("k", "u", "fixture", "o", "ws", CREATED_FROM_RESULT, "v1", LINK_STATE_UNLINKED, NOW, earlier)
        # The equal-boundary case (>=) is legal, not just (>).
        SavedOpportunity("k", "u", "fixture", "o", "v1", SAVE_STATE_REMOVING, NOW, NOW, None)
        SlateLink("k", "u", "fixture", "o", "ws", CREATED_FROM_RESULT, "v1", LINK_STATE_UNLINKED, NOW, NOW)

    def test_governing_basis_refuses_current_or_changed_with_no_governing_key(self):
        # MINOR 4 (doc 03 §9.3): "current" and "changed" both describe an
        # existing, tracked governing head, so a None governing_source_version_key
        # paired with either state is a C2 composition bug, not a
        # legitimate absence -- refuse loudly (ValueError) rather than let
        # derive_lifecycle_overlays silently render a wrong overlay from
        # inconsistent input.
        with self.assertRaises(ValueError):
            GoverningBasis("o", "fixture", "current", None, NOW, NOW)
        with self.assertRaises(ValueError):
            GoverningBasis("o", "fixture", "changed", None, NOW, NOW)
        # Every other listing state legitimately allows a None governing
        # key (an opportunity that never had, or has lost, a governing
        # head can still be intake/closed/unreachable/stale/quarantined/invalid).
        for listing_state in ("intake", "closed", "unreachable", "stale", "quarantined", "invalid"):
            GoverningBasis("o", "fixture", listing_state, None, NOW, NOW)
        # The non-None cases remain legal for current/changed.
        GoverningBasis("o", "fixture", "current", "v1", NOW, NOW)
        GoverningBasis("o", "fixture", "changed", "v1", NOW, NOW)


# ---------------------------------------------------------------------------
# I. Migration/registry/verifier file-content tests (byte-level)
# ---------------------------------------------------------------------------

FORWARD_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-005_relationships.sql"
ROLLBACK_PATH = ROOT / "SQL FIles/Migrations/PS-MYOPP-005_relationships_rollback.sql"
VERIFY_PATH = ROOT / "SQL FIles/Verification/PS-MYOPP-005_relationships_verify.sql"
REGISTRY_PATH = ROOT / "SQL FIles/Migrations/registry.json"

_C6_TABLES = ("myopp_saved_opportunities", "myopp_slate_links")
_FORBIDDEN_PATTERNS = (
    "title", "employer", "company", "description", "content", "text",
    "overlay", "score", "probability", "rank", "relevance",
)


def _c6_table_body(sql: str, table: str) -> str:
    start = sql.index(f"CREATE TABLE dbo.{table}")
    candidates = [
        sql.find("CREATE TABLE dbo.", start + 1),
        sql.find("CREATE UNIQUE INDEX ", start + 1),
        sql.find("CREATE INDEX ", start + 1),
        sql.find("EXEC(N'", start + 1),
    ]
    ends = [c for c in candidates if c != -1]
    end = min(ends) if ends else len(sql)
    return sql[start:end]


class RelationshipsMigrationTests(unittest.TestCase):
    def test_c6_migration_registry_and_verifier_are_bounded_and_gate_proven(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        entry = next(item for item in registry["migrations"] if item["id"] == "PS-MYOPP-005")

        self.assertEqual(len([item for item in registry["migrations"] if item["id"] == "PS-MYOPP-005"]), 1)
        self.assertEqual(entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003", "PS-MYOPP-004"])
        self.assertEqual(entry["forward"], FORWARD_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(entry["rollback"], ROLLBACK_PATH.relative_to(ROOT).as_posix())

        # The disposable gate proof is recorded by the writer before merge;
        # until then the entry carries "gate": null and every assertion
        # below on the populated proof is expected to fail here -- that
        # failure is the honest signal the gate has not been run yet, not a
        # defect in this test (mirrors C4/C5's equivalent tests).
        gate = entry["gate"]
        self.assertEqual(gate["executable_sha256"], executable_sha256(FORWARD_PATH))
        self.assertEqual(gate["prerequisites"], ["PS-PLAT-000", "PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003", "PS-MYOPP-004"])
        self.assertEqual(gate["verification"], "PS-MYOPP-005_relationships_verify.sql returned verified = 1")
        self.assertEqual(len(executable_sha256(FORWARD_PATH)), 64)

        self.assertTrue(gate["gate_database"])
        self.assertNotIn(gate["gate_database"], {"peerslate-database", "peerslate-staging"})
        self.assertTrue(gate["gate_server"])
        self.assertTrue(gate["operator"])

        for table in _C6_TABLES:
            self.assertIn(f"CREATE TABLE dbo.{table}", forward)
            self.assertIn(f"DROP TABLE dbo.{table};", rollback)
            self.assertIn(table, verify)
            body = _c6_table_body(forward, table)
            for pattern in _FORBIDDEN_PATTERNS:
                self.assertNotIn(pattern, body.lower())

        self.assertIn("PS-MYOPP-005 requires PS-MYOPP-001", forward)
        self.assertIn("PS-MYOPP-005 requires PS-MYOPP-002", forward)
        self.assertIn("PS-MYOPP-005 requires PS-MYOPP-003", forward)
        self.assertIn("PS-MYOPP-005 requires PS-MYOPP-004", forward)
        self.assertIn("user_key nvarchar(300) NOT NULL", forward)
        self.assertIn("CK_myopp_saved_opportunities_state", forward)
        self.assertIn("CK_myopp_slate_links_state", forward)

        self.assertIn("trg_myopp_saved_opportunities_guard", forward)
        self.assertIn("trg_myopp_slate_links_guard", forward)

        self.assertIn("PS-MYOPP-005 is not recorded", rollback)
        self.assertIn("later migration is recorded", rollback)
        self.assertIn("C6 member data exists", rollback)

        self.assertIn("SELECT CAST(1 AS bit) AS verified", verify)
        for pattern in _FORBIDDEN_PATTERNS:
            self.assertIn(f"%{pattern}%", verify)

    def test_c6_migration_state_and_reason_vocabulary_matches_module_constants(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for group in (SAVE_STATES, LINK_STATES, CREATED_FROM_SOURCES, DATA_CLASSES):
            for value in group:
                self.assertIn(f"N'{value}'", forward, f"{value!r} missing from PS-MYOPP-005 forward DDL")

    def test_c6_rollback_refuses_on_member_data_and_later_ledger_rows_and_drops_in_dependency_order(self):
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        self.assertIn("PS-MYOPP-005 is not recorded", rollback)
        self.assertIn("later migration is recorded", rollback)
        self.assertIn("C6 member data exists", rollback)

        trigger_slate_index = rollback.index("DROP TRIGGER dbo.trg_myopp_slate_links_guard;")
        trigger_saved_index = rollback.index("DROP TRIGGER dbo.trg_myopp_saved_opportunities_guard;")
        table_slate_index = rollback.index("DROP TABLE dbo.myopp_slate_links;")
        table_saved_index = rollback.index("DROP TABLE dbo.myopp_saved_opportunities;")
        ledger_delete_index = rollback.index("DELETE dbo.schema_migrations WHERE migration_id = N'PS-MYOPP-005';")

        self.assertLess(trigger_slate_index, table_slate_index)
        self.assertLess(trigger_saved_index, table_slate_index)
        self.assertLess(table_slate_index, table_saved_index)
        self.assertLess(table_saved_index, ledger_delete_index)

    def test_c6_verifier_names_every_table_trigger_and_ends_with_verified_bit(self):
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        for table in _C6_TABLES:
            self.assertIn(table, verify)
        for trigger in ("trg_myopp_saved_opportunities_guard", "trg_myopp_slate_links_guard"):
            self.assertIn(trigger, verify)
        verified_index = verify.index("SELECT CAST(1 AS bit) AS verified")
        self.assertGreater(verified_index, verify.index("THROW 55823"))

    def test_c6_throw_numbers_are_in_reserved_ranges_and_unique_repo_wide(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        rollback = ROLLBACK_PATH.read_text(encoding="utf-8")
        verify = VERIFY_PATH.read_text(encoding="utf-8")

        forward_throws = {int(n) for n in re.findall(r"THROW (\d{5})", forward)}
        rollback_throws = {int(n) for n in re.findall(r"THROW (\d{5})", rollback)}
        verify_throws = {int(n) for n in re.findall(r"THROW (\d{5})", verify)}

        self.assertTrue(forward_throws)
        self.assertTrue(all(55780 <= n <= 55799 for n in forward_throws))
        self.assertTrue(rollback_throws)
        self.assertTrue(all(55800 <= n <= 55809 for n in rollback_throws))
        self.assertTrue(verify_throws)
        self.assertTrue(all(55810 <= n <= 55839 for n in verify_throws))

        for label, raw in (("forward", forward), ("rollback", rollback), ("verify", verify)):
            numbers = re.findall(r"THROW (\d{5})", raw)
            if len(numbers) != len(set(numbers)):
                duplicated = sorted({n for n in numbers if numbers.count(n) > 1})
                self.fail(f"{label} file reuses THROW number(s) {duplicated} across distinct assertions")

        c6_numbers = forward_throws | rollback_throws | verify_throws
        c6_paths = {FORWARD_PATH, ROLLBACK_PATH, VERIFY_PATH}
        migrations_dir = ROOT / "SQL FIles" / "Migrations"
        verification_dir = ROOT / "SQL FIles" / "Verification"
        for path in sorted(migrations_dir.glob("*.sql")) + sorted(verification_dir.glob("*.sql")):
            if path in c6_paths:
                continue
            text = path.read_text(encoding="utf-8")
            other_numbers = {int(n) for n in re.findall(r"THROW (\d{5})", text)}
            collision = c6_numbers & other_numbers
            if collision:
                self.fail(f"THROW {sorted(collision)} claimed by PS-MYOPP-005 already used in {path.name}")

    def test_registry_entry_shape_and_requires(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        migrations = registry["migrations"]
        entries = [item for item in migrations if item["id"] == "PS-MYOPP-005"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(list(entry.keys()), ["id", "forward", "rollback", "requires", "summary", "gate"])
        self.assertEqual(entry["forward"], "SQL FIles/Migrations/PS-MYOPP-005_relationships.sql")
        self.assertEqual(entry["rollback"], "SQL FIles/Migrations/PS-MYOPP-005_relationships_rollback.sql")
        self.assertEqual(entry["requires"], ["PS-MYOPP-001", "PS-MYOPP-002", "PS-MYOPP-003", "PS-MYOPP-004"])
        self.assertTrue(entry["gate"] is None or isinstance(entry["gate"], dict))
        # IMPORTANT 5: no "must be literally last" assertion here -- see
        # test_every_migrations_requires_appear_earlier_in_the_array for
        # the durable, order-relative invariant that replaces it.

    def test_no_forbidden_scoring_overlay_or_copied_content_column_in_c6_ddl(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for table in _C6_TABLES:
            body = _c6_table_body(forward, table)
            for pattern in _FORBIDDEN_PATTERNS:
                self.assertNotIn(pattern, body.lower())

    def test_registry_json_remains_well_formed_with_exactly_one_c6_entry(self):
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertIn("migrations", registry)
        ids = [item["id"] for item in registry["migrations"]]
        self.assertEqual(ids.count("PS-MYOPP-005"), 1)

    def test_terminal_row_guards_fire_on_any_update_not_only_state_changes(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        for throw_number, expected_clause in (
            (55786, "d.state = N''removed''"),
            (55792, "d.state = N''unlinked''"),
        ):
            throw_index = forward.index(f"THROW {throw_number}")
            clause_start = forward.rindex("IF EXISTS", 0, throw_index)
            clause = forward[clause_start:throw_index]
            self.assertIn(expected_clause, clause)
            self.assertNotIn("i.state <> d.state", clause)

    def test_legal_transition_values_tables_match_the_module_machine(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "(N''saved'', N''removing''), (N''removing'', N''saved''), (N''removing'', N''removed'')",
            forward,
        )
        self.assertIn("d.state = N''linked'' AND i.state = N''unlinked''", forward)

    def test_delete_blocked_on_both_tables(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        self.assertIn("no erasure path exists", forward)
        self.assertEqual(forward.count("no erasure path exists"), 2)

    def test_filtered_unique_index_definitions_verbatim(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        self.assertIn("WHERE state <> N'removed';", forward)
        self.assertIn("WHERE state = N'linked';", forward)
        verify = VERIFY_PATH.read_text(encoding="utf-8")
        # IMPORTANT 4: the verifier normalizes filter_definition (lowercase,
        # strip brackets/parens/whitespace -- PS-MYOPP-001's idiom) rather
        # than comparing SQL Server's own pretty-printed form byte-for-byte;
        # these are the normalized expected literals it compares against.
        self.assertIn("N'state<>n''removed'''", verify)
        self.assertIn("N'state=n''linked'''", verify)

    def test_data_class_pairing_every_composite_fk_pairs_id_and_data_class(self):
        forward = FORWARD_PATH.read_text(encoding="utf-8")
        composite_fks = re.findall(
            r"FOREIGN KEY \(([a-z_]+), data_class\)\s*\n\s*REFERENCES dbo\.[a-z_]+ \(([a-z_]+), data_class\)",
            forward,
        )
        self.assertEqual(len(composite_fks), 4)  # opportunity + version FKs on both tables

    def test_every_migrations_requires_appear_earlier_in_the_array(self):
        # IMPORTANT 5: "this package's entry is literally last" is not a
        # durable invariant -- it breaks the instant any later package
        # appends to the shared, append-only registry.json (as this very
        # session discovered happened to C4's own equivalent assertion).
        # The durable invariant "apply order = list order" (registry.json's
        # own $comment) actually needs is relative, not absolute: every
        # migration's `requires` entries must appear EARLIER in the array
        # than the migration itself. This holds for PS-MYOPP-005 today and
        # for every future package's append, forever.
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        migrations = registry["migrations"]
        index_by_id = {item["id"]: position for position, item in enumerate(migrations)}
        for entry in migrations:
            for required_id in entry.get("requires", []):
                self.assertIn(required_id, index_by_id, f"{entry['id']} requires unknown {required_id}")
                self.assertLess(
                    index_by_id[required_id],
                    index_by_id[entry["id"]],
                    f"{entry['id']} requires {required_id}, which must appear earlier in registry.json",
                )
        self.assertIn("PS-MYOPP-005", index_by_id)


if __name__ == "__main__":
    unittest.main()
