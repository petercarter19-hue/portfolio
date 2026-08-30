from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.migration_registry import executable_sha256
from services.my_opportunities.criteria_service import (
    CriteriaService,
    CriteriaServiceError,
    InMemoryCriteriaRepository,
)
from services.my_opportunities.interpretation_service import (
    InterpretationContractError,
    InterpretationProposal,
    InterpretationService,
    InterpretationUnavailable,
    ProposedClarification,
    ProposedClarificationOption,
    ProposedCriterion,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 29, 12, tzinfo=timezone.utc)


class FixtureProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def interpret(self, request_text, *, locale, timezone):
        self.calls.append((request_text, locale, timezone))
        if request_text == "ambiguous":
            return InterpretationProposal(
                criteria=(ProposedCriterion("role_family", "Product leadership", "product"),),
                clarification=ProposedClarification(
                    "arrangement",
                    "Which arrangement works?",
                    (
                        ProposedClarificationOption(
                            "remote",
                            "Remote",
                            (ProposedCriterion("arrangement", "Remote", "remote"),),
                        ),
                        ProposedClarificationOption(
                            "hybrid",
                            "Hybrid",
                            (ProposedCriterion("arrangement", "Hybrid", "hybrid"),),
                        ),
                    ),
                    "arrangement",
                ),
            )
        return InterpretationProposal(
            criteria=(
                ProposedCriterion("role_family", "Product leadership", "product"),
                ProposedCriterion("location", "Chicago", "Chicago, IL"),
            ),
            verification_scope="fully_verified",
            direct_filters=(("posted_within", "30_days"),),
        )


class DownProvider:
    def interpret(self, request_text, *, locale, timezone):
        del request_text, locale, timezone
        raise InterpretationUnavailable("fixture_down")


class InvalidProvider:
    def interpret(self, request_text, *, locale, timezone):
        del request_text, locale, timezone
        return InterpretationProposal(
            criteria=(ProposedCriterion("Bad Kind", "Bad", "bad"),)
        )


class CriteriaContractTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryCriteriaRepository()
        self.provider = FixtureProvider()
        self.service = CriteriaService(
            self.repository,
            InterpretationService(self.provider),
        )

    def interpret(self, text="clear", key="interpret-1", **overrides):
        values = {
            "request_text": text,
            "locale": "en-US",
            "timezone_name": "America/Chicago",
            "idempotency_key": key,
            "now": NOW,
        }
        values.update(overrides)
        return self.service.interpret("member-a", **values)

    def test_interpret_returns_visible_draft_and_only_explicit_apply_freezes_snapshot(self):
        draft = self.interpret()
        self.assertEqual(draft.state, "live")
        self.assertIsNotNone(draft.draft_version_token)
        self.assertEqual(draft.interpretation_status, "ai_interpreted")
        self.assertEqual([item.kind for item in draft.criteria], ["role_family", "location"])
        self.assertEqual(self.repository.snapshots_for_owner("member-a"), ())

        receipt = self.service.apply(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            idempotency_key="apply-1",
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(receipt.outcome, "applied")
        self.assertIsNotNone(receipt.execution_key)
        snapshot = self.service.get_snapshot("member-a", receipt.snapshot_key)
        self.assertEqual(snapshot.criteria, draft.criteria)
        self.assertEqual(self.service.get_draft("member-a", draft.draft_key).state, "applied")
        self.assertFalse(hasattr(self.service, "execute_search"))

    def test_clarification_has_no_selection_and_fences_apply_until_answered(self):
        draft = self.interpret("ambiguous")
        self.assertIsNotNone(draft.clarification)
        self.assertEqual([item.option_key for item in draft.clarification.options], ["remote", "hybrid"])
        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as caught:
            self.service.apply(
                "member-a",
                draft_key=draft.draft_key,
                draft_version_token=draft.draft_version_token,
                idempotency_key="apply-blocked",
                now=NOW,
            )
        self.assertEqual(caught.exception.failure_code, "clarification_required")
        self.assertEqual(self.repository.state_digest(), before)

        answered = self.service.answer_clarification(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            clarification_key="arrangement",
            selected_option_key="remote",
            idempotency_key="answer-1",
            now=NOW + timedelta(seconds=1),
        )
        self.assertIsNone(answered.clarification)
        self.assertNotEqual(answered.draft_version_token, draft.draft_version_token)
        self.assertIn(("arrangement", "remote"), [(item.kind, item.value) for item in answered.criteria])

    def test_dismiss_clarification_changes_only_clarification_and_rotates_token(self):
        draft = self.interpret("ambiguous")
        dismissed = self.service.dismiss_clarification(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            clarification_key="arrangement",
            idempotency_key="dismiss-1",
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(dismissed.criteria, draft.criteria)
        self.assertIsNone(dismissed.clarification)
        self.assertEqual(dismissed.version_number, draft.version_number + 1)

    def test_manual_draft_parity_edit_scope_filters_and_atomic_validation(self):
        draft = self.service.create_draft("member-a", idempotency_key="manual-1", now=NOW)
        operations = [
            {"op": "set_criterion", "kind": "role_family", "display_label": "Engineering", "value": "engineering"},
            {"op": "set_criterion", "kind": "arrangement", "display_label": "Hybrid", "value": "hybrid"},
            {"op": "set_criterion", "kind": "compensation_floor", "display_label": "$150k+", "value": "150000"},
            {"op": "set_criterion", "kind": "domain", "display_label": "Climate", "value": "climate"},
            {"op": "set_criterion", "kind": "location", "display_label": "Chicago", "value": "Chicago, IL"},
            {"op": "set_criterion", "kind": "free_text_term", "display_label": "Platform", "value": "platform"},
            {"op": "set_verification_scope", "verification_scope": "both"},
            {"op": "set_direct_filter", "filter_key": "posted_within", "value": "7_days"},
        ]
        edited = self.service.edit_draft(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            operations=operations,
            idempotency_key="edit-manual",
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(len(edited.criteria), 6)
        self.assertTrue(all(item.source == "manual" for item in edited.criteria))
        self.assertEqual(dict(edited.direct_filters), {"posted_within": "7_days"})
        reduced = self.service.edit_draft(
            "member-a",
            draft_key=edited.draft_key,
            draft_version_token=edited.draft_version_token,
            operations=[
                {"op": "remove_criterion", "criterion_key": edited.criteria[-1].criterion_key},
                {"op": "clear_direct_filter", "filter_key": "posted_within"},
            ],
            idempotency_key="edit-remove-clear",
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(len(reduced.criteria), 5)
        self.assertEqual(reduced.direct_filters, ())
        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as caught:
            self.service.edit_draft(
                "member-a",
                draft_key=reduced.draft_key,
                draft_version_token=reduced.draft_version_token,
                operations=[
                    {"op": "set_direct_filter", "filter_key": "hours", "value": "full_time"},
                    {"op": "set_verification_scope", "verification_scope": "invented"},
                ],
                idempotency_key="edit-invalid",
                now=NOW + timedelta(seconds=3),
            )
        self.assertEqual(caught.exception.failure_code, "verification_scope_invalid")
        self.assertEqual(self.repository.state_digest(), before)

    def test_ai_unavailable_is_same_manual_surface_and_full_manual_journey(self):
        service = CriteriaService(
            InMemoryCriteriaRepository(), InterpretationService(DownProvider())
        )
        draft = service.interpret(
            "member-a",
            request_text="platform work",
            locale="en-US",
            timezone_name="America/Chicago",
            idempotency_key="down-1",
            now=NOW,
        )
        self.assertEqual(draft.interpretation_status, "manual_required")
        self.assertEqual(draft.interpretation_provenance, "manual")
        self.assertEqual(draft.criteria, ())
        edited = service.edit_draft(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            operations=[
                {"op": "set_criterion", "kind": "free_text_term", "display_label": "Platform", "value": "platform"}
            ],
            idempotency_key="down-edit",
            now=NOW + timedelta(seconds=1),
        )
        receipt = service.apply(
            "member-a",
            draft_key=edited.draft_key,
            draft_version_token=edited.draft_version_token,
            idempotency_key="down-apply",
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(receipt.outcome, "applied")

    def test_complete_idempotency_and_token_refusal_precedence(self):
        draft = self.interpret()
        edit_args = dict(
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            operations=[{"op": "set_direct_filter", "filter_key": "sort", "value": "recent"}],
            idempotency_key="precedence-edit",
            now=NOW + timedelta(seconds=1),
        )
        edited = self.service.edit_draft("member-a", **edit_args)
        later = self.service.edit_draft(
            "member-a",
            draft_key=edited.draft_key,
            draft_version_token=edited.draft_version_token,
            operations=[{"op": "set_verification_scope", "verification_scope": "both"}],
            idempotency_key="later-edit",
            now=NOW + timedelta(seconds=2),
        )
        replay = self.service.edit_draft("member-a", **edit_args)
        self.assertEqual(replay, edited)
        self.assertNotEqual(replay.draft_version_token, later.draft_version_token)

        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as mismatch:
            self.service.edit_draft(
                "member-a",
                **{
                    **edit_args,
                    "operations": [
                        {
                            "op": "set_verification_scope",
                            "verification_scope": "fully_verified",
                        }
                    ],
                },
            )
        self.assertEqual(mismatch.exception.failure_code, "idempotency_mismatch")
        self.assertEqual(self.repository.state_digest(), before)

        with self.assertRaises(CriteriaServiceError) as stale:
            self.service.edit_draft(
                "member-a",
                draft_key=draft.draft_key,
                draft_version_token=draft.draft_version_token,
                operations=[{"op": "set_verification_scope", "verification_scope": "both"}],
                idempotency_key="stale-new",
                now=NOW + timedelta(seconds=3),
            )
        self.assertEqual(stale.exception.failure_code, "stale_draft")
        self.assertEqual(stale.exception.current_state, later)
        self.assertEqual(self.repository.state_digest(), before)

        receipt = self.service.apply(
            "member-a",
            draft_key=later.draft_key,
            draft_version_token=later.draft_version_token,
            idempotency_key="terminal-apply",
            now=NOW + timedelta(seconds=4),
        )
        self.assertEqual(
            self.service.apply(
                "member-a",
                draft_key=later.draft_key,
                draft_version_token=later.draft_version_token,
                idempotency_key="terminal-apply",
                now=NOW + timedelta(seconds=5),
            ),
            receipt,
        )
        before_terminal_refusal = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as terminal:
            self.service.apply(
                "member-a",
                draft_key=later.draft_key,
                draft_version_token=later.draft_version_token,
                idempotency_key="terminal-new",
                now=NOW + timedelta(seconds=5),
            )
        self.assertEqual(terminal.exception.failure_code, "terminal_draft")
        self.assertEqual(terminal.exception.terminal_receipt, receipt)
        self.assertIsNone(terminal.exception.current_state)
        self.assertEqual(self.repository.state_digest(), before_terminal_refusal)

    def test_idempotency_key_is_scoped_per_owner_and_command(self):
        first = self.service.create_draft("member-a", idempotency_key="shared-key", now=NOW)
        second = self.service.create_draft("member-b", idempotency_key="shared-key", now=NOW)
        self.assertNotEqual(first.draft_key, second.draft_key)
        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as caught:
            self.service.discard_draft(
                "member-a",
                draft_key=first.draft_key,
                draft_version_token=first.draft_version_token,
                idempotency_key="shared-key",
                now=NOW,
            )
        self.assertEqual(caught.exception.failure_code, "idempotency_mismatch")
        self.assertEqual(self.repository.state_digest(), before)

    def test_post_result_refinement_and_keep_current_leave_applied_snapshot_unchanged(self):
        first = self.interpret()
        applied = self.service.apply(
            "member-a",
            draft_key=first.draft_key,
            draft_version_token=first.draft_version_token,
            idempotency_key="apply-original",
            now=NOW + timedelta(seconds=1),
        )
        snapshot_before = self.service.get_snapshot("member-a", applied.snapshot_key)
        refined = self.service.refine_from_results(
            "member-a",
            snapshot_key=applied.snapshot_key,
            operations=[{"op": "set_direct_filter", "filter_key": "posted_within", "value": "3_days"}],
            idempotency_key="refine-1",
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(refined.parent_snapshot_key, applied.snapshot_key)
        self.assertEqual(self.service.get_snapshot("member-a", applied.snapshot_key), snapshot_before)
        keep = self.service.keep_current_criteria(
            "member-a",
            draft_key=refined.draft_key,
            draft_version_token=refined.draft_version_token,
            idempotency_key="keep-1",
            now=NOW + timedelta(seconds=3),
        )
        self.assertEqual(keep.outcome, "discarded")
        self.assertEqual(self.service.get_snapshot("member-a", applied.snapshot_key), snapshot_before)
        self.assertEqual(len(self.repository.snapshots_for_owner("member-a")), 1)

    def test_natural_language_refinement_is_new_draft_and_canonical_input_includes_snapshot(self):
        original = self.interpret()
        receipt = self.service.apply(
            "member-a",
            draft_key=original.draft_key,
            draft_version_token=original.draft_version_token,
            idempotency_key="apply-for-natural-refine",
            now=NOW + timedelta(seconds=1),
        )
        refined = self.interpret(
            "clear",
            key="natural-refine",
            parent_snapshot_key=receipt.snapshot_key,
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(refined.parent_snapshot_key, receipt.snapshot_key)
        self.assertNotEqual(refined.draft_key, original.draft_key)
        with self.assertRaises(CriteriaServiceError) as caught:
            self.interpret(
                "clear",
                key="natural-refine",
                parent_snapshot_key=None,
                now=NOW + timedelta(seconds=3),
            )
        self.assertEqual(caught.exception.failure_code, "idempotency_mismatch")

    def test_interpret_into_existing_rotates_token_and_discard_is_terminal(self):
        empty = self.service.create_draft("member-a", idempotency_key="existing-create", now=NOW)
        interpreted = self.interpret(
            key="existing-interpret",
            existing_draft_key=empty.draft_key,
            existing_draft_version_token=empty.draft_version_token,
            now=NOW + timedelta(seconds=1),
        )
        self.assertEqual(interpreted.draft_key, empty.draft_key)
        self.assertEqual(interpreted.version_number, empty.version_number + 1)
        self.assertNotEqual(interpreted.draft_version_token, empty.draft_version_token)
        self.assertEqual(self.repository.snapshots_for_owner("member-a"), ())

        receipt = self.service.discard_draft(
            "member-a",
            draft_key=interpreted.draft_key,
            draft_version_token=interpreted.draft_version_token,
            idempotency_key="existing-discard",
            now=NOW + timedelta(seconds=2),
        )
        self.assertEqual(receipt.outcome, "discarded")
        self.assertEqual(
            self.service.discard_draft(
                "member-a",
                draft_key=interpreted.draft_key,
                draft_version_token=interpreted.draft_version_token,
                idempotency_key="existing-discard",
                now=NOW + timedelta(seconds=3),
            ),
            receipt,
        )
        terminal = self.service.get_draft("member-a", interpreted.draft_key)
        self.assertEqual(terminal.state, "discarded")
        self.assertIsNone(terminal.draft_version_token)

    def test_cross_member_direct_keys_are_indistinguishable_from_absent(self):
        draft = self.interpret()
        receipt = self.service.apply(
            "member-a",
            draft_key=draft.draft_key,
            draft_version_token=draft.draft_version_token,
            idempotency_key="owner-apply",
            now=NOW + timedelta(seconds=1),
        )
        for key in (draft.draft_key, "absent-draft"):
            with self.assertRaises(CriteriaServiceError) as caught:
                self.service.get_draft("member-b", key)
            self.assertEqual(caught.exception.failure_code, "not_found")
            self.assertEqual(caught.exception.member_message, "That criteria draft is not available.")
        for key in (receipt.snapshot_key, "absent-snapshot"):
            with self.assertRaises(CriteriaServiceError) as caught:
                self.service.get_snapshot("member-b", key)
            self.assertEqual(caught.exception.failure_code, "not_found")
        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as mutation:
            self.service.discard_draft(
                "member-b",
                draft_key=draft.draft_key,
                draft_version_token=draft.draft_version_token,
                idempotency_key="cross-owner-discard",
                now=NOW + timedelta(seconds=2),
            )
        self.assertEqual(mutation.exception.failure_code, "not_found")
        with self.assertRaises(CriteriaServiceError) as refinement:
            self.service.refine_from_results(
                "member-b",
                snapshot_key=receipt.snapshot_key,
                operations=[
                    {"op": "set_verification_scope", "verification_scope": "both"}
                ],
                idempotency_key="cross-owner-refine",
                now=NOW + timedelta(seconds=2),
            )
        self.assertEqual(refinement.exception.failure_code, "not_found")
        self.assertEqual(self.repository.state_digest(), before)

    def test_unknown_clarification_option_and_invalid_provider_never_mutate(self):
        draft = self.interpret("ambiguous")
        before = self.repository.state_digest()
        with self.assertRaises(CriteriaServiceError) as caught:
            self.service.answer_clarification(
                "member-a",
                draft_key=draft.draft_key,
                draft_version_token=draft.draft_version_token,
                clarification_key="arrangement",
                selected_option_key="invented",
                idempotency_key="bad-answer",
                now=NOW,
            )
        self.assertEqual(caught.exception.failure_code, "unknown_clarification_option")
        self.assertEqual(self.repository.state_digest(), before)

        invalid_repository = InMemoryCriteriaRepository()
        invalid_service = CriteriaService(
            invalid_repository, InterpretationService(InvalidProvider())
        )
        with self.assertRaises(CriteriaServiceError) as invalid:
            invalid_service.interpret(
                "member-a",
                request_text="bad provider",
                locale="en-US",
                timezone_name="America/Chicago",
                idempotency_key="bad-provider",
                now=NOW,
            )
        self.assertEqual(invalid.exception.failure_code, "criterion_kind_invalid")
        self.assertEqual(invalid_repository.state_digest(), InMemoryCriteriaRepository().state_digest())

    def test_request_bounds_and_idempotency_ttl_are_explicit(self):
        with self.assertRaises(CriteriaServiceError) as caught:
            self.service.interpret(
                "member-a",
                request_text="😀" * 2_001,
                locale="en-US",
                timezone_name="America/Chicago",
                idempotency_key="too-long",
                now=NOW,
            )
        self.assertEqual(caught.exception.failure_code, "request_text_too_long")
        created = self.service.create_draft("member-a", idempotency_key="expires", now=NOW)
        self.assertEqual(
            self.repository.purge_expired_idempotency(now=NOW + timedelta(hours=24)),
            1,
        )
        replacement = self.service.create_draft(
            "member-a", idempotency_key="expires", now=NOW + timedelta(hours=24)
        )
        self.assertNotEqual(created.draft_key, replacement.draft_key)


class CriteriaMigrationTests(unittest.TestCase):
    def test_c3_migration_registry_and_verifier_are_bounded_and_gate_proven(self):
        forward_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-002_criteria_state.sql"
        rollback_path = ROOT / "SQL FIles/Migrations/PS-MYOPP-002_criteria_state_rollback.sql"
        verify_path = ROOT / "SQL FIles/Verification/PS-MYOPP-002_criteria_state_verify.sql"
        forward = forward_path.read_text(encoding="utf-8")
        rollback = rollback_path.read_text(encoding="utf-8")
        verify = verify_path.read_text(encoding="utf-8")
        registry = json.loads((ROOT / "SQL FIles/Migrations/registry.json").read_text(encoding="utf-8"))
        entry = next(item for item in registry["migrations"] if item["id"] == "PS-MYOPP-002")

        self.assertEqual(entry["requires"], ["PS-MYOPP-001"])
        gate = entry["gate"]
        self.assertEqual(gate["executable_sha256"], executable_sha256(forward_path))
        self.assertEqual(gate["gate_database"], "ps-myopp-c3-gate-20260829-a1")
        self.assertEqual(gate["gate_server"], "peerslate")
        self.assertEqual(gate["prerequisites"], ["PS-PLAT-000", "PS-MYOPP-001"])
        self.assertEqual(
            gate["verification"],
            "PS-MYOPP-002_criteria_state_verify.sql returned verified = 1",
        )
        self.assertEqual(gate["operator"], "agent:/root/c3_criteria_writer")
        self.assertEqual(entry["forward"], forward_path.relative_to(ROOT).as_posix())
        self.assertEqual(entry["rollback"], rollback_path.relative_to(ROOT).as_posix())
        self.assertEqual(len([item for item in registry["migrations"] if item["id"] == "PS-MYOPP-002"]), 1)
        self.assertEqual(len(executable_sha256(forward_path)), 64)

        for table in (
            "myopp_criteria_drafts",
            "myopp_criteria_draft_versions",
            "myopp_applied_criteria_snapshots",
            "myopp_criteria_commands",
        ):
            self.assertIn(f"CREATE TABLE dbo.{table}", forward)
            self.assertIn(f"DROP TABLE dbo.{table};", rollback)
            self.assertIn(table, verify)
        self.assertIn("user_key nvarchar(300) NOT NULL", forward)
        self.assertIn("FK_myopp_criteria_drafts_user", forward)
        self.assertIn("canonical_input_sha256", forward)
        self.assertIn("idempotency_key_sha256", forward)
        self.assertNotIn("request_text", _table_body(forward, "myopp_criteria_commands"))
        self.assertNotIn("criteria_json", _table_body(forward, "myopp_criteria_commands"))
        self.assertIn("trg_myopp_applied_criteria_snapshots_immutable", forward)
        self.assertIn("trg_myopp_criteria_draft_versions_immutable", forward)
        self.assertIn("trg_myopp_criteria_commands_immutable", forward)
        self.assertIn("PS-MYOPP-002 is not recorded", rollback)
        self.assertIn("C3 member data exists", rollback)
        self.assertIn("SELECT CAST(1 AS bit) AS verified", verify)
        self.assertIn("content-free", verify)

    def test_package_registry_contains_c3_once_and_counts_reconcile(self):
        registry = json.loads((ROOT / "docs/governance/PACKAGE_REGISTRY.json").read_text(encoding="utf-8"))
        packages = [item for values in registry["categories"].values() for item in values]
        self.assertEqual(packages.count("PS-MYOPP-CRITERIA-001"), 1)
        self.assertEqual(registry["counts"]["total"], len(packages))
        for category, values in registry["categories"].items():
            self.assertEqual(registry["counts"][category], len(values))


def _table_body(sql: str, table: str) -> str:
    start = sql.index(f"CREATE TABLE dbo.{table}")
    next_create = sql.find("CREATE TABLE dbo.", start + 1)
    return sql[start:] if next_create == -1 else sql[start:next_create]


if __name__ == "__main__":
    unittest.main()
