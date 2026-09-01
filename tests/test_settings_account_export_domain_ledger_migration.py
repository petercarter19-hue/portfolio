"""Offline text assertions over PS-SETTINGS-EXPORT-010.

Same discipline as tests/test_settings_account_export_migration.py: every
assertion is a static read of the committed SQL text. No database is
contacted; the live proof lives in the paired Verification file, run only
on a disposable gate database.
"""

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FORWARD = ROOT / "SQL FIles" / "Migrations" / "PS-SETTINGS-EXPORT-010_domain_ledger_writer.sql"
ROLLBACK = ROOT / "SQL FIles" / "Migrations" / "PS-SETTINGS-EXPORT-010_domain_ledger_writer_rollback.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"

forward_text = FORWARD.read_text(encoding="utf-8")
rollback_text = ROLLBACK.read_text(encoding="utf-8")


class DomainLedgerWriterMigrationTests(unittest.TestCase):
    def test_creates_only_the_new_procedure_and_never_touches_c1s(self):
        created = re.findall(r"CREATE OR ALTER PROCEDURE dbo\.(\w+)", forward_text)
        self.assertEqual(created, ["usp_CompleteAccountExportWithDomains"])
        # C1's procedure may be MENTIONED in prose but never redefined,
        # altered, or dropped. Word boundary matters: the new name extends
        # the old one, so a plain substring check would self-trigger.
        pattern = re.compile(r"(?:CREATE OR )?ALTER PROCEDURE dbo\.usp_CompleteAccountExportJob\b")
        drop = re.compile(r"DROP PROCEDURE dbo\.usp_CompleteAccountExportJob\b")
        for text in (forward_text, rollback_text):
            self.assertIsNone(pattern.search(text))
            self.assertIsNone(drop.search(text))

    def test_pinned_canonical_set_equals_domains_exactly(self):
        from services.account_export_domain_readers import DOMAINS

        start = forward_text.index("@Canonical (domain_code) VALUES")
        segment = forward_text[start: forward_text.index("THROW 57273", start)]
        pinned = set(re.findall(r"N''([a-z_]+)''", segment))
        self.assertEqual(pinned, set(DOMAINS))
        self.assertEqual(len(pinned), 30)

    def test_identity_is_derived_from_the_locked_row_never_a_parameter(self):
        # No owner-selecting parameter of any kind.
        header = forward_text[
            forward_text.index("usp_CompleteAccountExportWithDomains"):
            forward_text.index("        AS\n")
        ]
        params = re.findall(r"@(\w+)\s+(?:uniqueidentifier|nvarchar|datetime2|varbinary|bigint|char|int)",
                            header)
        for forbidden in ("UserKey", "OwnerProfileId", "OwnerUserId", "ProfileId", "UserId", "Email"):
            self.assertNotIn(forbidden, params)
        # ...and the values used come from the locked job row.
        self.assertIn("@OwnerProfileId = job.owner_profile_id", forward_text)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", forward_text)

    def test_the_four_way_lease_fence_is_verbatim(self):
        for predicate in (
            "job.job_key = @JobKey",
            "job.state = N''running''",
            "job.lease_token = @LeaseToken",
            "job.lease_expires_at_utc > @Now",
        ):
            self.assertIn(predicate, forward_text)
        self.assertIn("THROW 57279", forward_text)

    def test_owner_active_is_rechecked_inside_the_transaction(self):
        transaction_body = forward_text[
            forward_text.index("BEGIN TRANSACTION;", forward_text.index("THROW 57278")):
            forward_text.index("COMMIT TRANSACTION;", forward_text.index("THROW 57280"))
        ]
        self.assertIn("app_user.active = 1", transaction_body)
        self.assertIn("profile.active = 1", transaction_body)
        self.assertIn("THROW 57280", transaction_body)

    def test_insert_and_ready_share_one_transaction(self):
        transaction_body = forward_text[
            forward_text.index("BEGIN TRANSACTION;", forward_text.index("THROW 57278")):
            forward_text.index("COMMIT TRANSACTION;", forward_text.index("THROW 57280"))
        ]
        self.assertIn("INSERT dbo.account_export_job_domains", transaction_body)
        self.assertIn("SET state = N''ready''", transaction_body)
        # Both-or-neither: no COMMIT between the insert and the update.
        between = transaction_body[
            transaction_body.index("INSERT dbo.account_export_job_domains"):
            transaction_body.index("SET state = N''ready''")
        ]
        self.assertNotIn("COMMIT", between)

    def test_c1s_argument_validations_are_reused_verbatim(self):
        for number in ("57230", "57231", "57232", "57233", "57234", "57235"):
            self.assertIn("THROW %s" % number, forward_text)

    def test_payload_refusals_have_distinct_numbers(self):
        for number, fragment in (
            ("57271", "must be JSON"),
            ("57272", "canonical domain set"),
            ("57273", "repeats a domain"),
            ("57274", "closed vocabulary"),
            ("57275", "disposition shape"),
            ("57276", "64 lowercase hex"),
            ("57277", "non-negative"),
            ("57278", "out of order"),
            ("57281", "exceeds the ledger bound"),
        ):
            self.assertIn("THROW %s" % number, forward_text)
            self.assertIn(fragment, forward_text)

    def test_reasons_parse_wide_so_the_engine_can_never_narrow_silently(self):
        """Reinstating F1's mechanism -- narrowing these back to 200 --
        must fail offline, not only at the gate: the Python bounding
        would mask it everywhere else."""
        self.assertIn("omission_reason    nvarchar(max) NULL", forward_text)
        self.assertIn("failure_reason     nvarchar(max) NULL", forward_text)
        self.assertIn("omission_reason     nvarchar(max)  ''$.omission_reason''", forward_text)
        self.assertIn("failure_reason      nvarchar(max)  ''$.failure_reason''", forward_text)

    def test_owner_approved_constants_are_not_caller_configurable(self):
        self.assertIn("@ReadyWindowDays int = 7", forward_text)
        self.assertNotIn("@ReadyWindowDays int =", re.sub(
            r"DECLARE @ReadyWindowDays int = 7", "", forward_text))

    def test_schema_identifier_and_marker_rules_are_the_decided_ones(self):
        self.assertIn("N''peerslate.account_export.'' + p.domain_code + N''.v1''", forward_text)
        self.assertIn("THEN @ConsistencyMarkerCutoff ELSE NULL END", forward_text)

    def test_insert_order_is_deterministic(self):
        self.assertIn("ORDER BY p.domain_code", forward_text)

    def test_forward_asserts_the_ledger_table_exists(self):
        self.assertIn("THROW 57270", forward_text)
        self.assertIn("OBJECT_ID(N'dbo.account_export_job_domains', N'U') IS NULL", forward_text)

    def test_audit_metadata_is_content_free(self):
        match = re.search(r"@MetadataJson = N''(\{[^']*\})''", forward_text)
        self.assertIsNotNone(match)
        metadata = json.loads(match.group(1))
        self.assertEqual(set(metadata), {"state", "domain_rows"})

    def test_rollback_drops_only_the_new_procedure(self):
        drops = re.findall(r"DROP PROCEDURE dbo\.(\w+)", rollback_text)
        self.assertEqual(drops, ["usp_CompleteAccountExportWithDomains"])
        self.assertNotIn("account_export_job_domains", re.sub(
            r"/\*.*?\*/", "", rollback_text, flags=re.S))  # prose only; no DDL on the table

    def test_registry_entry_is_wellformed_and_never_reuses_002(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        ids = [m["id"] for m in registry["migrations"]]
        self.assertIn("PS-SETTINGS-EXPORT-010", ids)
        self.assertNotIn("PS-SETTINGS-EXPORT-002", ids)
        entry = next(m for m in registry["migrations"] if m["id"] == "PS-SETTINGS-EXPORT-010")
        self.assertEqual(entry["forward"], str(FORWARD.relative_to(ROOT)).replace("\\", "/"))
        self.assertEqual(entry["rollback"], str(ROLLBACK.relative_to(ROOT)).replace("\\", "/"))
        self.assertIn("PS-SETTINGS-EXPORT-001", entry["requires"])
        self.assertIn("gate", entry)

    def test_no_worker_procedure_takes_a_member_user_key(self):
        self.assertNotIn("@UserKey", forward_text)


if __name__ == "__main__":
    unittest.main()
