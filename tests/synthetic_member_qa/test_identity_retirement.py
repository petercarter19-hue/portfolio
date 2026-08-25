from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from qa.synthetic_member import identity_retirement as retirement


NOW = datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=1)
SUBJECT_A = "qa-subject-a"
SUBJECT_B = "qa-subject-b"


def target(seed: int, *, state: str = "active", role: str = "user"):
    active = state == "active"
    return retirement.Target(
        identity_id=seed,
        user_id=seed + 10,
        profile_id=seed + 20,
        identity_status="active" if active else "revoked",
        user_active=active,
        account_status="active" if active else "closed",
        user_role=role,
        profile_active=active,
        visibility="private",
        identity_created_at=NOW - timedelta(hours=2),
        user_created_at=NOW - timedelta(hours=2),
        profile_created_at=NOW - timedelta(hours=2),
        identity_last_seen_at=NOW - timedelta(minutes=5),
        user_last_seen_at=NOW - timedelta(minutes=5),
        auth_fields_match=True,
    )


def reference(key, *, disabled=False, untrusted=False):
    return retirement.Reference(*key, disabled, untrusted)


class FakeStore:
    def __init__(self, *, state="active"):
        self.targets = [target(1, state=state), target(2, state=state)]
        self.reference_rows = [reference(key) for key in retirement.REQUIRED_REFERENCES]
        self.reference_counts = {}
        self.workshop_items = 0
        self.identity_rows = 2
        self.profile_rows = 2
        self.private_preferences = 2
        self.began = []
        self.load_locks = []
        self.database_validated = False
        self.mutations = []

    def begin(self, *, serializable):
        self.began.append(serializable)

    def validate_database(self):
        self.database_validated = True

    def load_targets(self, _subjects, _issuer, *, lock):
        self.load_locks.append(lock)
        return list(self.targets)

    def references(self):
        return list(self.reference_rows)

    def identity_count(self, _targets):
        return self.identity_rows

    def profile_count(self, _targets):
        return self.profile_rows

    def private_preference_count(self, _targets):
        return self.private_preferences

    def workshop_item_count(self, _targets):
        return self.workshop_items

    def reference_count(self, reference_row, _targets):
        return self.reference_counts.get(reference_row.key, 0)

    def mutate(self, action, _targets):
        self.mutations.append(action)
        if action == "retire":
            self.targets = [
                replace(
                    row,
                    identity_status="revoked",
                    user_active=False,
                    account_status="closed",
                    profile_active=False,
                )
                for row in self.targets
            ]
        else:
            self.targets = [
                replace(
                    row,
                    identity_status="active",
                    user_active=True,
                    account_status="active",
                    profile_active=True,
                )
                for row in self.targets
            ]


class FakeConnection:
    def __init__(self, *, fail_commit=False, fail_rollback=False, fail_close=False):
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.fail_commit = fail_commit
        self.fail_rollback = fail_rollback
        self.fail_close = fail_close

    def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("private commit detail")

    def rollback(self):
        self.rollbacks += 1
        if self.fail_rollback:
            raise RuntimeError("private rollback detail")

    def close(self):
        self.closed += 1
        if self.fail_close:
            raise RuntimeError("private close detail")


class InputBoundaryTests(unittest.TestCase):
    def test_subjects_require_an_interactive_terminal(self):
        with self.assertRaisesRegex(retirement.RetirementRefusal, "interactive"):
            retirement.read_subjects(lambda _prompt: "hidden", stdin_isatty=lambda: False)

    def test_subjects_are_confirmed_and_distinct(self):
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        self.assertEqual(
            retirement.read_subjects(lambda _prompt: next(answers), stdin_isatty=lambda: True),
            (SUBJECT_A, SUBJECT_B),
        )
        duplicate = iter([SUBJECT_A, SUBJECT_A, SUBJECT_A, SUBJECT_A])
        with self.assertRaisesRegex(retirement.RetirementRefusal, "not_distinct"):
            retirement.read_subjects(
                lambda _prompt: next(duplicate), stdin_isatty=lambda: True
            )

    def test_cutoff_is_recent_exact_utc_input(self):
        parsed = retirement.parse_cutoff("2026-08-24T18:00:00Z", NOW)
        self.assertEqual(parsed, CUTOFF)
        for invalid in ("2026-08-24T18:00:00", "2026-08-01T00:00:00Z"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(retirement.RetirementRefusal):
                    retirement.parse_cutoff(invalid, NOW)


class EligibilityTests(unittest.TestCase):
    def test_plan_accepts_only_the_closed_structural_shape(self):
        store = FakeStore()
        report = retirement.execute(
            store,
            mode="plan",
            subjects=(SUBJECT_A, SUBJECT_B),
            issuer="https://issuer.invalid/",
            cutoff=CUTOFF,
        )
        self.assertEqual(report["state"], "eligible")
        self.assertEqual(report["counts"]["eligible_members"], 2)
        self.assertEqual(store.mutations, [])
        self.assertEqual(store.began, [True])
        self.assertEqual(store.load_locks, [True])
        self.assertTrue(store.database_validated)

    def test_nonordinary_or_duplicate_mapping_is_refused(self):
        store = FakeStore()
        store.targets[0] = replace(store.targets[0], user_role="admin")
        with self.assertRaisesRegex(retirement.RetirementRefusal, "ordinary"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )
        store = FakeStore()
        store.targets[1] = replace(store.targets[1], user_id=store.targets[0].user_id)
        with self.assertRaisesRegex(retirement.RetirementRefusal, "not_distinct"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )

    def test_missing_or_untrusted_foreign_key_boundary_is_refused(self):
        store = FakeStore()
        store.reference_rows.pop()
        with self.assertRaisesRegex(retirement.RetirementRefusal, "metadata_missing"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )
        store = FakeStore()
        store.reference_rows[0] = replace(store.reference_rows[0], untrusted=True)
        with self.assertRaisesRegex(retirement.RetirementRefusal, "not_enforced"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )

    def test_workshop_or_any_other_product_reference_is_refused(self):
        store = FakeStore()
        store.workshop_items = 1
        with self.assertRaisesRegex(retirement.RetirementRefusal, "residue"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )
        store = FakeStore()
        extra_key = (
            "dbo",
            "moments",
            "owner_profile_id",
            "dbo",
            "member_profiles",
            "profile_id",
        )
        store.reference_rows.append(reference(extra_key))
        store.reference_counts[extra_key] = 1
        with self.assertRaisesRegex(retirement.RetirementRefusal, "residue"):
            retirement.assess(
                store,
                (SUBJECT_A, SUBJECT_B),
                "issuer",
                CUTOFF,
                expected_state="active",
                lock=False,
            )


class StateTransitionTests(unittest.TestCase):
    def test_retire_rechecks_closed_state_in_the_same_serializable_operation(self):
        store = FakeStore()
        report = retirement.execute(
            store,
            mode="retire",
            subjects=(SUBJECT_A, SUBJECT_B),
            issuer="issuer",
            cutoff=CUTOFF,
        )
        self.assertEqual(report["state"], "retired")
        self.assertEqual(store.mutations, ["retire"])
        self.assertEqual(store.began, [True])

    def test_recover_requires_and_rechecks_the_retired_state(self):
        store = FakeStore(state="retired")
        report = retirement.execute(
            store,
            mode="recover",
            subjects=(SUBJECT_A, SUBJECT_B),
            issuer="issuer",
            cutoff=CUTOFF,
        )
        self.assertEqual(report["state"], "active_recovered")
        self.assertEqual(store.mutations, ["recover"])

    def test_verify_retired_is_read_only(self):
        store = FakeStore(state="retired")
        report = retirement.execute(
            store,
            mode="verify-retired",
            subjects=(SUBJECT_A, SUBJECT_B),
            issuer="issuer",
            cutoff=CUTOFF,
        )
        self.assertEqual(report["state"], "retired_verified")
        self.assertEqual(store.mutations, [])
        self.assertEqual(store.began, [True])
        self.assertEqual(store.load_locks, [True])

    def test_verify_retired_holds_the_target_view_against_recovery(self):
        class RecoveryRaceStore(FakeStore):
            def load_targets(self, subjects, issuer, *, lock):
                rows = super().load_targets(subjects, issuer, lock=lock)
                if not lock:
                    self.mutate("recover", rows)
                return rows

        store = RecoveryRaceStore(state="retired")
        report = retirement.execute(
            store,
            mode="verify-retired",
            subjects=(SUBJECT_A, SUBJECT_B),
            issuer="issuer",
            cutoff=CUTOFF,
        )
        self.assertEqual(report["state"], "retired_verified")
        self.assertEqual(store.mutations, [])
        self.assertFalse(any(row.user_active for row in store.targets))


class CliBoundaryTests(unittest.TestCase):
    def test_database_parameter_diagnostics_are_a_hard_stop(self):
        import mssql_python

        with patch.object(mssql_python.logger, "isEnabledFor", return_value=True), patch.object(
            mssql_python, "connect"
        ) as connect:
            with self.assertRaisesRegex(retirement.RetirementRefusal, "diagnostic_logging"):
                retirement.open_production_connection()
        connect.assert_not_called()

    def test_retire_confirmation_failure_happens_before_secret_or_connection(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "retire",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                ],
                connection_factory=lambda: self.fail("must not connect"),
                secret_reader=lambda _prompt: self.fail("must not prompt"),
                clock=lambda: NOW,
            )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(output.getvalue())["reason_code"],
            "retirement_confirmations_required",
        )

    def test_success_output_never_contains_identity_or_authorization_material(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection()
        safe_report = {
            "result": "pass",
            "state": "eligible",
            "counts": {"eligible_members": 2},
        }
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "private-issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(retirement, "execute", return_value=safe_report), contextlib.redirect_stdout(
            output
        ):
            code = retirement.main(
                [
                    "plan",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 0)
        rendered = output.getvalue()
        for forbidden in (
            SUBJECT_A,
            SUBJECT_B,
            "private-issuer",
            "approval:valid-123",
        ):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closed, 1)

    def test_unexpected_error_is_class_only_and_rolls_back(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection()
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement, "execute", side_effect=RuntimeError("secret database detail")
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "plan",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 2)
        report = json.loads(output.getvalue())
        self.assertEqual(report["reason_code"], "operation_failed")
        self.assertEqual(report["error_class"], "RuntimeError")
        self.assertNotIn("secret database detail", output.getvalue())
        self.assertEqual(connection.rollbacks, 1)

    def test_rollback_failure_is_one_closed_report_with_no_driver_detail(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_rollback=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement, "execute", side_effect=RuntimeError("private operation detail")
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "plan",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 2)
        report = json.loads(output.getvalue())
        self.assertEqual(report["reason_code"], "connection_cleanup_failed")
        self.assertEqual(report["error_class"], "RuntimeError")
        self.assertNotIn("private", output.getvalue())
        self.assertEqual(connection.closed, 1)

    def test_close_failure_after_read_only_rollback_is_closed(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_close=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement,
            "execute",
            return_value={"result": "pass", "state": "eligible", "counts": {}},
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "plan",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 2)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "refused")
        self.assertEqual(report["reason_code"], "connection_cleanup_failed")
        self.assertNotIn("private", output.getvalue())

    def test_close_failure_after_commit_is_indeterminate_not_a_false_pass(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_close=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement,
            "execute",
            return_value={"result": "pass", "state": "retired", "counts": {}},
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "retire",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-workshop-cleanup-complete",
                    "--confirm-retire",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 3)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "indeterminate")
        self.assertEqual(
            report["reason_code"], "connection_cleanup_failed_after_commit"
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertNotIn("private", output.getvalue())

    def test_commit_failure_is_indeterminate_and_attempts_rollback(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_commit=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement,
            "execute",
            return_value={"result": "pass", "state": "retired", "counts": {}},
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "retire",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-workshop-cleanup-complete",
                    "--confirm-retire",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 3)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "indeterminate")
        self.assertEqual(report["reason_code"], "commit_state_unknown")
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("private", output.getvalue())

    def test_commit_and_rollback_failures_preserve_indeterminate_state(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_commit=True, fail_rollback=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement,
            "execute",
            return_value={"result": "pass", "state": "retired", "counts": {}},
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "retire",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-workshop-cleanup-complete",
                    "--confirm-retire",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 3)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "indeterminate")
        self.assertEqual(
            report["reason_code"],
            "connection_cleanup_failed_after_commit_attempt",
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 1)
        self.assertNotIn("private", output.getvalue())

    def test_commit_and_close_failures_preserve_indeterminate_state(self):
        output = io.StringIO()
        answers = iter([SUBJECT_A, SUBJECT_A, SUBJECT_B, SUBJECT_B])
        connection = FakeConnection(fail_commit=True, fail_close=True)
        with patch.dict(os.environ, {"PEERSLATE_AUTH_ISSUER": "issuer"}), patch.object(
            retirement, "SqlRetirementStore", return_value=object()
        ), patch.object(
            retirement,
            "execute",
            return_value={"result": "pass", "state": "retired", "counts": {}},
        ), contextlib.redirect_stdout(output):
            code = retirement.main(
                [
                    "retire",
                    "--authorization-ref",
                    "approval:valid-123",
                    "--created-after-utc",
                    "2026-08-24T18:00:00Z",
                    "--confirm-exact-two-synthetic-members",
                    "--confirm-workshop-cleanup-complete",
                    "--confirm-retire",
                ],
                connection_factory=lambda: connection,
                secret_reader=lambda _prompt: next(answers),
                stdin_isatty=lambda: True,
                clock=lambda: NOW,
            )
        self.assertEqual(code, 3)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "indeterminate")
        self.assertEqual(
            report["reason_code"],
            "connection_cleanup_failed_after_commit_attempt",
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closed, 1)
        self.assertNotIn("private", output.getvalue())


if __name__ == "__main__":
    unittest.main()
