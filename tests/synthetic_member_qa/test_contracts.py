from __future__ import annotations

import copy
import unittest

from qa.synthetic_member.contracts import (
    ContractError,
    EphemeralCleanupLedger,
    JOURNEYS,
    MemberAlias,
    compute_result,
    create_manifest,
    record_cleanup,
    record_journey,
    validate_manifest,
)


SOURCE_COMMIT = "a" * 40
CREATED_AT = "2026-08-20T23:00:00Z"


def manifest() -> dict:
    return create_manifest(
        run_id="qa-20260820-001",
        source_commit=SOURCE_COMMIT,
        mode="candidate_attended",
        browser="edge",
        browser_version="140.0",
        surface_code="foundation",
        created_at=CREATED_AT,
    )


def pass_all_journeys(value: dict) -> dict:
    updated = value
    for journey in JOURNEYS:
        updated = record_journey(
            updated,
            journey_id=journey.journey_id,
            status="pass",
        )
    return updated


def clean_with_items(value: dict) -> dict:
    return record_cleanup(
        value,
        pre_run_baseline="pass",
        created_member_a=1,
        created_member_b=1,
        residue_member_a=0,
        residue_member_b=0,
        retention_disclosure="soft_delete_disclosed",
        client_a_destroyed="pass",
        client_b_destroyed="pass",
        signed_out_control_destroyed="pass",
        switch_client_destroyed="pass",
    )


class ManifestContractTests(unittest.TestCase):
    def test_pending_manifest_is_exact_and_valid(self):
        value = manifest()

        self.assertEqual(value["identity_aliases"], ["member_a", "member_b"])
        self.assertEqual(value["result"], "pending")
        self.assertEqual(len(value["journeys"]), len(JOURNEYS))
        self.assertEqual(
            len({record["journey_id"] for record in value["journeys"]}),
            len(JOURNEYS),
        )
        self.assertIs(validate_manifest(value), value)

    def test_matrix_covers_bidirectional_private_operations_and_switching(self):
        journey_ids = {journey.journey_id for journey in JOURNEYS}
        for actor, peer in (("member_a", "member_b"), ("member_b", "member_a")):
            for operation in ("list", "read", "update", "delete", "export"):
                self.assertIn(f"{actor}_cannot_{operation}_{peer}", journey_ids)
            self.assertIn(f"{actor}_forged_reference_denied", journey_ids)
        self.assertIn("account_switch_member_a_to_member_b", journey_ids)
        self.assertIn("account_switch_member_b_to_member_a", journey_ids)
        self.assertIn("clean_signed_out_control_start", journey_ids)
        self.assertIn("member_a_cross_tab_signout_safe", journey_ids)
        self.assertIn("member_b_cross_tab_signout_safe", journey_ids)
        self.assertIn("repeat_run_clean_start", journey_ids)

    def test_canonical_plan_cannot_be_shortened_or_reordered(self):
        shortened = manifest()
        shortened["journeys"].pop()
        with self.assertRaisesRegex(ContractError, "complete canonical matrix"):
            validate_manifest(shortened)

        reordered = manifest()
        reordered["journeys"][0], reordered["journeys"][1] = (
            reordered["journeys"][1],
            reordered["journeys"][0],
        )
        with self.assertRaisesRegex(ContractError, "canonical plan"):
            validate_manifest(reordered)

    def test_exact_shape_rejects_unapproved_identity_or_evidence_fields(self):
        for key in (
            "email",
            "provider_subject",
            "account_key",
            "user_key",
            "cookie",
            "access_token",
            "session_file",
            "screenshot",
            "record_id",
        ):
            with self.subTest(key=key):
                value = manifest()
                value[key] = "redacted"
                with self.assertRaises(ContractError):
                    validate_manifest(value)

    def test_refusal_errors_do_not_echo_untrusted_keys_or_values(self):
        value = manifest()
        value["person@example.com"] = "private-value"
        with self.assertRaises(ContractError) as raised:
            validate_manifest(value)
        self.assertNotIn("person@example.com", str(raised.exception))
        self.assertNotIn("private-value", str(raised.exception))

        value = manifest()
        value["result"] = "person@example.com"
        with self.assertRaises(ContractError) as raised:
            validate_manifest(value)
        self.assertNotIn("person@example.com", str(raised.exception))

    def test_safe_labels_reject_pii_urls_private_ids_and_tokens(self):
        unsafe_values = (
            "person@example.com",
            "https://example.test/private",
            "123e4567-e89b-42d3-a456-426614174000",
            "abcdefghijklmnop.qrstuvwxyzabcdef.ghijklmnopqrstuv",
        )
        for unsafe in unsafe_values:
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(ContractError):
                    create_manifest(
                        run_id="qa-safe",
                        source_commit=SOURCE_COMMIT,
                        mode="local_contract",
                        browser="edge",
                        browser_version=unsafe,
                        created_at=CREATED_AT,
                    )

    def test_pass_records_only_the_expected_structural_outcome(self):
        updated = record_journey(
            manifest(), journey_id="signed_out_private_baseline", status="pass"
        )
        record = next(
            item
            for item in updated["journeys"]
            if item["journey_id"] == "signed_out_private_baseline"
        )
        self.assertEqual(record["observed_outcome"], "private_data_absent")
        self.assertEqual(record["note_code"], "none")
        self.assertNotIn("details", record)

    def test_conditional_and_fail_require_closed_note_codes(self):
        with self.assertRaisesRegex(ContractError, "requires a note code"):
            record_journey(
                manifest(),
                journey_id="member_a_expired_session_safe",
                status="conditional",
            )
        with self.assertRaisesRegex(ContractError, "requires a note code"):
            record_journey(
                manifest(),
                journey_id="member_a_cannot_read_member_b",
                status="fail",
            )
        with self.assertRaisesRegex(ContractError, "not approved"):
            record_journey(
                manifest(),
                journey_id="member_a_expired_session_safe",
                status="conditional",
                note_code="free form explanation",
            )

    def test_safety_note_codes_cannot_be_downgraded_to_conditional(self):
        for note_code in (
            "mapping_not_distinct",
            "private_state_exposed",
            "unexpected_authenticated_state",
        ):
            with self.subTest(note_code=note_code):
                with self.assertRaisesRegex(ContractError, "requires Fail"):
                    record_journey(
                        manifest(),
                        journey_id="member_pair_distinct_mapping",
                        status="conditional",
                        note_code=note_code,
                    )

        direct = manifest()
        record = next(
            item
            for item in direct["journeys"]
            if item["journey_id"] == "member_pair_distinct_mapping"
        )
        record.update(
            {
                "status": "conditional",
                "observed_outcome": "limitation_recorded",
                "note_code": "mapping_not_distinct",
            }
        )
        direct["result"] = "conditional"
        with self.assertRaisesRegex(ContractError, "requires Fail"):
            validate_manifest(direct)

        updated = record_journey(
            manifest(),
            journey_id="member_pair_distinct_mapping",
            status="fail",
            note_code="mapping_not_distinct",
        )
        self.assertEqual(updated["result"], "fail")

    def test_limitations_cannot_be_misrecorded_as_safety_failures(self):
        with self.assertRaisesRegex(ContractError, "safety note code"):
            record_journey(
                manifest(),
                journey_id="member_a_expired_session_safe",
                status="fail",
                note_code="session_expiry_not_controllable",
            )

    def test_full_pass_requires_every_journey_and_cleanup(self):
        updated = clean_with_items(pass_all_journeys(manifest()))

        self.assertEqual(updated["cleanup"]["status"], "pass")
        self.assertEqual(updated["result"], "pass")
        validate_manifest(updated, final=True)

    def test_known_session_limitation_produces_conditional_not_pass(self):
        updated = pass_all_journeys(manifest())
        for journey_id in (
            "member_a_cross_tab_signout_safe",
            "member_b_cross_tab_signout_safe",
            "member_a_expired_session_safe",
            "member_b_expired_session_safe",
        ):
            note_code = (
                "cross_tab_signout_unreconciled"
                if "cross_tab" in journey_id
                else "session_expiry_not_controllable"
            )
            updated = record_journey(
                updated,
                journey_id=journey_id,
                status="conditional",
                note_code=note_code,
            )
        updated = clean_with_items(updated)

        self.assertEqual(updated["result"], "conditional")
        validate_manifest(updated, final=True)

    def test_zero_or_one_sided_item_creation_prevents_pass(self):
        for created_a, created_b in ((0, 0), (1, 0), (0, 1)):
            with self.subTest(created_a=created_a, created_b=created_b):
                updated = record_cleanup(
                    pass_all_journeys(manifest()),
                    pre_run_baseline="pass",
                    created_member_a=created_a,
                    created_member_b=created_b,
                    residue_member_a=0,
                    residue_member_b=0,
                    retention_disclosure="soft_delete_disclosed",
                    client_a_destroyed="pass",
                    client_b_destroyed="pass",
                    signed_out_control_destroyed="pass",
                    switch_client_destroyed="pass",
                )
                self.assertEqual(updated["cleanup"]["status"], "conditional")
                self.assertEqual(updated["result"], "conditional")
                validate_manifest(updated, final=True)

    def test_deployed_evidence_requires_valid_custody_metadata(self):
        for release_id, browser_version in (
            ("not_recorded", "140.0"),
            ("abcdef0", "not_recorded"),
        ):
            with self.subTest(
                release_id=release_id,
                browser_version=browser_version,
            ):
                with self.assertRaisesRegex(ContractError, "deployed evidence"):
                    create_manifest(
                        run_id="qa-deployed",
                        source_commit=SOURCE_COMMIT,
                        mode="deployed_attended",
                        browser="edge",
                        browser_version=browser_version,
                        release_id=release_id,
                        created_at=CREATED_AT,
                    )

        with self.assertRaisesRegex(ContractError, "real second-precision"):
            create_manifest(
                run_id="qa-impossible-time",
                source_commit=SOURCE_COMMIT,
                mode="candidate_attended",
                browser="edge",
                browser_version="140.0",
                created_at="2026-99-99T99:99:99Z",
            )

    def test_cleanup_residue_forces_fail(self):
        updated = record_cleanup(
            pass_all_journeys(manifest()),
            pre_run_baseline="pass",
            created_member_a=1,
            created_member_b=1,
            residue_member_a=0,
            residue_member_b=1,
            retention_disclosure="soft_delete_disclosed",
            client_a_destroyed="pass",
            client_b_destroyed="pass",
            signed_out_control_destroyed="pass",
            switch_client_destroyed="pass",
        )

        self.assertEqual(updated["cleanup"]["status"], "fail")
        self.assertEqual(updated["result"], "fail")
        validate_manifest(updated, final=True)

    def test_unverified_retention_prevents_pass(self):
        updated = record_cleanup(
            pass_all_journeys(manifest()),
            pre_run_baseline="pass",
            created_member_a=1,
            created_member_b=1,
            residue_member_a=0,
            residue_member_b=0,
            retention_disclosure="application_delete_completed_retention_unverified",
            client_a_destroyed="pass",
            client_b_destroyed="pass",
            signed_out_control_destroyed="pass",
            switch_client_destroyed="pass",
        )

        self.assertEqual(updated["cleanup"]["status"], "conditional")
        self.assertEqual(updated["result"], "conditional")

    def test_stored_result_and_cleanup_status_cannot_be_overclaimed(self):
        value = manifest()
        value["result"] = "pass"
        with self.assertRaisesRegex(ContractError, "computed as pending"):
            validate_manifest(value)

        value = manifest()
        value["cleanup"]["status"] = "pass"
        with self.assertRaisesRegex(ContractError, "computed as pending"):
            validate_manifest(value)

    def test_final_validation_refuses_pending_evidence(self):
        with self.assertRaisesRegex(ContractError, "cannot contain pending"):
            validate_manifest(manifest(), final=True)

    def test_compute_result_does_not_trust_manifest_result(self):
        value = manifest()
        value["result"] = "fail"
        self.assertEqual(compute_result(value), "pending")


class EphemeralCleanupLedgerTests(unittest.TestCase):
    def test_handles_are_never_rendered_or_returned(self):
        ledger = EphemeralCleanupLedger()
        ledger.add(MemberAlias.MEMBER_A, "private-handle-a")
        ledger.add(MemberAlias.MEMBER_B, "private-handle-b")

        self.assertEqual(ledger.created_counts(), {"member_a": 1, "member_b": 1})
        self.assertNotIn("private-handle", repr(ledger))
        self.assertIn("handles=redacted", repr(ledger))

        ledger.clear()
        self.assertEqual(ledger.created_counts(), {"member_a": 0, "member_b": 0})

    def test_alias_must_be_the_closed_enum(self):
        ledger = EphemeralCleanupLedger()
        with self.assertRaisesRegex(ContractError, "must be MemberAlias"):
            ledger.add("member_a", "handle")  # type: ignore[arg-type]
