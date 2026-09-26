"""Static contract checks for proposed PS-RESUME-MEDIA-001 SQL.

These tests do not claim SQL Server execution, transaction, concurrency,
rollback, permission, or driver serialization proof. The registry gate stays
null until a separately authorized disposable-database proof is completed, and
allowlisting a proposed procedure name does not apply the migration.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from services.database_service import ALLOWED_PROCEDURES
from services.resume_media_application import (
    RESUME_MEDIA_BROWSER_PROCEDURES,
    RESUME_MEDIA_WORKER_PROCEDURES,
    ResumeDraftBoundMediaRepository,
    ResumeMediaApplicationUnavailable,
    SqlResumeMediaDraftStore,
)
from services.resume_draft_repository import SqlResumeDraftRepository
from services.resume_media_repository import (
    InMemoryResumeMediaRepository,
    ResumeMediaRepositoryError,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
FORWARD = MIGRATIONS / "PS-RESUME-MEDIA-001_resume_media.sql"
ROLLBACK = MIGRATIONS / "PS-RESUME-MEDIA-001_resume_media_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-MEDIA-001_resume_media_verify.sql"
RESUME_DRAFT_SQL = MIGRATIONS / "PS-RESUME-DRAFT-001_resume_drafts.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"


def procedure_body(source: str, name: str) -> str:
    """The text of one CREATE OR ALTER PROCEDURE inside an EXEC(N'...') batch."""

    match = re.search(
        r"CREATE OR ALTER PROCEDURE dbo\." + re.escape(name) + r".*?\n(?:    )?'\);",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"procedure body not found: {name}")
    return match.group(0)


class ResumeMediaSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_registry_entry_is_proposed_with_null_gate(self):
        entry = next(
            item for item in self.registry["migrations"] if item["id"] == "PS-RESUME-MEDIA-001"
        )
        self.assertIsNone(entry["gate"])
        self.assertEqual(
            entry["requires"], ["PS-RESUME-DRAFT-001", "PS-CAPTURE-MEDIA-001"]
        )
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/proposed/PS-RESUME-MEDIA-001_resume_media.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-RESUME-MEDIA-001_resume_media_rollback.sql",
        )

    def test_forward_sql_is_owner_keyed_serializable_and_fences_the_shared_draft(self):
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.forward)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", self.forward)
        self.assertIn("@UserKey", self.forward)
        self.assertNotIn("@OwnerProfileId", self.forward)
        self.assertIn("usp_CommitResumeMediaCommandForOwner", self.forward)
        self.assertIn("usp_GetResumeMediaDraftForOwner", self.forward)
        self.assertIn("dbo.resume_drafts", self.forward)
        self.assertIn("draft_version", self.forward)
        self.assertIn("N'add_media'", self.forward)
        self.assertIn("N'keep_words_only'", self.forward)
        self.assertIn("N'story_banner'", self.forward)
        self.assertIn("N'experience_support'", self.forward)
        self.assertIn("N''idempotency_conflict'' AS outcome", self.forward)
        self.assertIn("stale_draft", self.forward)
        self.assertIn("member_profiles", self.forward)
        self.assertIn("PROPOSED ONLY", self.forward)

    def test_each_procedure_body_opens_its_own_transaction(self):
        """The autocommit connection only commits if the body says so."""

        for name in (
            "usp_GetResumeMediaDraftForOwner",
            "usp_CommitResumeMediaCommandForOwner",
        ):
            with self.subTest(procedure=name):
                body = procedure_body(self.forward, name)
                self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", body)
                self.assertIn("BEGIN TRY", body)
                self.assertIn("BEGIN TRANSACTION", body)
                self.assertIn("COMMIT TRANSACTION", body)
                self.assertIn("BEGIN CATCH", body)
                self.assertIn("IF XACT_STATE() <> 0 ROLLBACK TRANSACTION", body)
                self.assertIn("THROW;", body)

    def test_media_reader_uses_the_writer_shared_resource_lock_order(self):
        body = procedure_body(self.forward, "usp_GetResumeMediaDraftForOwner")
        self.assertLess(
            body.index("SELECT @ReadDraftVersion = draft.draft_version"),
            body.index("SELECT @MediaGeneration = COUNT(*)"),
        )
        self.assertLess(
            body.index("SELECT @MediaGeneration = COUNT(*)"),
            body.index("FROM dbo.resume_media_placements AS placement"),
        )

    def test_command_body_commits_every_early_return(self):
        body = procedure_body(self.forward, "usp_CommitResumeMediaCommandForOwner")
        # Every early outcome (changed-key conflict, idempotent replay, stale
        # draft, source changed, unverifiable catalog source) commits its own
        # transaction before returning, so no transaction is ever left open.
        self.assertEqual(body.count("COMMIT TRANSACTION"), 6)
        self.assertEqual(body.count("RETURN;"), 5)
        committed_returns = re.findall(
            r"COMMIT TRANSACTION;[\s\S]{0,400}?RETURN;", body
        )
        self.assertEqual(len(committed_returns), 5)
        # The success path commits before it reports the committed outcome.
        self.assertRegex(
            body,
            r"COMMIT TRANSACTION;\s+SELECT CONVERT\(bit, 1\) AS committed",
        )

    def test_command_body_validates_payload_shape_and_duplicate_slots(self):
        body = procedure_body(self.forward, "usp_CommitResumeMediaCommandForOwner")
        self.assertIn("HAVING COUNT(*) > 1", body)
        self.assertIn("GROUP BY duplicate.slot", body)
        self.assertIn("RESUME_MEDIA_VALIDATION", body)
        self.assertIn("candidate.presentation_version < 1", body)
        self.assertIn("candidate.decorative = 0", body)
        self.assertIn("candidate.crop_x + candidate.crop_width > 1", body)
        self.assertIn("LEN(ISNULL(candidate.caption, N'''')", body)
        self.assertIn("LEN(candidate.provenance_label) > 120", body)
        self.assertIn("@ExpectedVersion", body)
        self.assertIn("@DraftVersion <> @ExpectedVersion", body)

    def test_command_body_fences_the_same_shared_draft_the_text_command_uses(self):
        media_body = procedure_body(
            self.forward, "usp_CommitResumeMediaCommandForOwner"
        )
        draft_source = RESUME_DRAFT_SQL.read_text(encoding="utf-8")
        text_body = procedure_body(
            draft_source, "usp_CommitResumeDraftCommandForOwner"
        )
        for body in (media_body, text_body):
            self.assertIn("dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)", body)
            self.assertIn("draft_version", body)
            self.assertLess(
                body.index("dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)"),
                body.index("SELECT @ExistingDigest = receipt."),
            )
        self.assertIn("UPDATE dbo.resume_drafts", media_body)
        self.assertIn("SET draft_version = @NextVersion", media_body)
        self.assertIn("UPDATE dbo.resume_drafts", text_body)
        # The media proposal does not edit or replace the accepted text
        # command; it only fences the same row in its own transaction.
        self.assertNotIn("usp_CommitResumeDraftCommandForOwner", self.forward)

    def test_command_body_stores_and_compares_one_semantic_digest(self):
        body = procedure_body(self.forward, "usp_CommitResumeMediaCommandForOwner")
        # A JSON hash would never equal the semantic digest an exact retry
        # carries, so a replay must compare the payload's own receipt digest and
        # the command type, and must store that same digest.
        self.assertNotIn("HASHBYTES", body)
        self.assertIn("@IncomingDigest", body)
        self.assertIn("@IncomingDigest nvarchar(128)", body)
        self.assertIn("@IncomingType", body)
        self.assertIn("JSON_VALUE(@CommandJson, ''$.receipt.semantic_digest'')", body)
        self.assertIn("@ExistingType <> @IncomingType", body)
        self.assertIn("@ExistingDigest <> @IncomingDigest", body)
        self.assertLess(
            body.index("@IncomingDigest IS NULL"),
            body.index("IF @ExistingDigest IS NOT NULL"),
        )
        self.assertIn("N''idempotency_conflict'' AS outcome", body)
        self.assertIn(
            "(@ProfileId, @CommandType, @RequestId, @ReceiptDigest, @ReceiptOutcome)",
            body,
        )

    def test_verifier_accepts_real_replay_contract_and_rejects_weakened_guards(self):
        body = procedure_body(self.forward, "usp_CommitResumeMediaCommandForOwner").replace("''", "'")
        block = self.verify.split("-- Media reports replay conflicts", 1)[1].split(
            "INSERT @Failures VALUES (N'Payload-aware idempotency conflict is absent.');", 1
        )[0]
        expected = re.search(r"@ReplayConflict <> N'((?:''|[^'])*)'", block).group(1).replace("''", "'")
        start_text = "IF @ExistingType <> @IncomingType"

        def accepted(definition):
            start = definition.find(start_text)
            end = definition.find("END;", start)
            if start < 0 or end <= start:
                return False
            actual = " ".join(definition[start:end + 4].split())
            return actual == expected

        self.assertNotIn("RESUME_MEDIA_IDEMPOTENCY_CONFLICT", body)
        self.assertTrue(accepted(body))
        start = body.index(start_text)
        end = body.index("END;", start) + 4
        conflict = body[start:end]
        later_replay = body[end:]
        self.assertIn("CONVERT(bit, 0) AS publishes", later_replay)
        self.assertIn("RETURN;", later_replay)
        for old, new in (
            ("@ExistingType <> @IncomingType", "1 = 0"),
            ("@ExistingDigest <> @IncomingDigest", "1 = 0"),
            ("N'idempotency_conflict' AS outcome", "N'replayed' AS outcome"),
            ("CONVERT(bit, 0) AS committed", "CONVERT(bit, 1) AS committed"),
            ("CONVERT(bit, 0) AS replayed", "CONVERT(bit, 1) AS replayed"),
            ("CONVERT(bit, 0) AS publishes", "CONVERT(bit, 1) AS publishes"),
            ("RETURN;", ""),
        ):
            with self.subTest(removed_protection=old):
                self.assertIn(old, conflict)
                changed = body[:start] + conflict.replace(old, new, 1) + later_replay
                self.assertTrue(changed.endswith(later_replay))
                self.assertFalse(accepted(changed))

    def test_command_body_fences_the_authoritative_source_inside_the_transaction(self):
        body = procedure_body(self.forward, "usp_CommitResumeMediaCommandForOwner")
        source_guard = body.index("dbo.capture_media_sources")
        self.assertIn("source.scan_result = N''clean''", body)
        self.assertIn("source.state IN (N''needs_review'', N''confirmed'')", body)
        self.assertIn("LOWER(candidate.asset_digest)", body)
        self.assertIn(
            "CONVERT(bigint, source.row_version) = candidate.asset_version", body
        )
        self.assertIn("asset_version bigint", body)
        self.assertIn("N''source_changed'' AS outcome", body)
        self.assertIn("N''source_unavailable'' AS outcome", body)
        # The fence runs before any placement write and before the draft
        # version moves.
        self.assertLess(source_guard, body.index("DELETE placement"))
        self.assertLess(source_guard, body.index("UPDATE dbo.resume_drafts"))

    def test_extended_draft_procedure_is_an_internal_atomic_boundary(self):
        """The draft SQL owns its transaction and the shared version fence."""

        draft_source = RESUME_DRAFT_SQL.read_text(encoding="utf-8")
        draft_body = procedure_body(
            draft_source, "usp_CommitResumeDraftCommandForOwner"
        )
        self.assertIn("BEGIN TRANSACTION", draft_body)
        self.assertIn("COMMIT TRANSACTION", draft_body)
        self.assertIn("ROLLBACK TRANSACTION", draft_body)
        replay = draft_body.index("IF @ExistingDigest IS NOT NULL")
        fence = draft_body.index("IF ISNULL(@DraftVersion, 0) <> @ExpectedDraftVersion")
        self.assertLess(replay, fence)
        self.assertIn("N''stale_draft'' AS outcome", draft_body)
        self.assertNotIn("HASHBYTES", draft_body)
        self.assertIn("JSON_VALUE(@CommandJson, ''$.request_digest'')", draft_body)
        self.assertTrue(SqlResumeDraftRepository.atomic_command_supported)
        self.assertTrue(hasattr(SqlResumeDraftRepository, "commit_owner_command"))
        # The draft adapter is a fenced text-command port, not a media command
        # port; media uses its own procedure with an authoritative source fence.
        self.assertFalse(SqlResumeDraftRepository.media_command_supported)
        with self.assertRaises(ResumeMediaApplicationUnavailable):
            ResumeDraftBoundMediaRepository(
                draft_store=SqlResumeDraftRepository(database=object()),
                sources=InMemoryResumeMediaRepository(),
            )

    def test_draft_reader_retains_two_result_sets_inside_one_transaction(self):
        draft_source = RESUME_DRAFT_SQL.read_text(encoding="utf-8")
        body = procedure_body(draft_source, "usp_GetResumeDraftForOwner")
        self.assertIn("BEGIN TRANSACTION", body)
        self.assertIn("COMMIT TRANSACTION", body)
        self.assertIn("ROLLBACK TRANSACTION", body)
        self.assertEqual(body.count("\n            SELECT\n"), 2)
        self.assertIn("command_receipts_json", body)
        self.assertLess(
            body.index("SELECT @ReadDraftId = draft.resume_draft_id"),
            body.index("SELECT @CommandReceiptsJson ="),
        )
        self.assertLess(
            body.index("SELECT @CommandReceiptsJson ="),
            body.index("JOIN dbo.resume_draft_items AS item"),
        )

    def test_forward_sql_never_represents_portrait_publication_or_public_reads(self):
        command = re.search(
            r"CREATE OR ALTER PROCEDURE dbo\.usp_CommitResumeMediaCommandForOwner.*?\n    '\);",
            self.forward,
            re.DOTALL,
        )
        self.assertIsNotNone(command)
        self.assertNotIn("portrait", command.group(0).lower())
        self.assertNotIn("usp_Publish", self.forward)
        self.assertNotIn("entity_publications", self.forward)
        self.assertNotIn("resume_display = 1", self.forward)
        self.assertNotIn("visitor_ai = 1", self.forward)
        self.assertNotIn("publication_version", command.group(0))
        self.assertNotIn("INSERT dbo.entity_publications", self.forward)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*$", self.forward))

    def test_placement_and_receipt_constraints_are_closed(self):
        self.assertIn("CK_resume_media_placements_slot", self.forward)
        self.assertIn("CK_resume_media_placements_source_kind", self.forward)
        self.assertIn("CK_resume_media_placements_crop", self.forward)
        self.assertIn("CK_resume_media_placements_alt", self.forward)
        self.assertIn("CK_resume_media_command_receipts_type", self.forward)
        self.assertIn("CK_resume_media_command_receipts_outcome", self.forward)
        self.assertIn(
            "UQ_resume_media_command_receipts_owner_key", self.forward
        )
        self.assertIn("UQ_resume_media_placements_owner_slot", self.forward)
        self.assertIn("trg_resume_media_command_receipts_immutable", self.forward)

    def test_rollback_and_verify_are_structural_only(self):
        self.assertIn("DELETE dbo.schema_migrations", self.rollback)
        self.assertIn("PS-RESUME-MEDIA-001", self.rollback)
        self.assertIn("Rollback refused", self.rollback)
        self.assertIn("verified", self.verify)
        self.assertIn("runtime proof remains outstanding", self.verify)

    def test_browser_procedures_are_allowlisted_and_workers_are_absent(self):
        for name in RESUME_MEDIA_BROWSER_PROCEDURES:
            self.assertIn(name, self.forward)
            self.assertIn(name, ALLOWED_PROCEDURES)
        self.assertFalse(RESUME_MEDIA_WORKER_PROCEDURES)
        # No publication, worker or storage procedure is reachable from here.
        for name in ALLOWED_PROCEDURES:
            if "ResumeMedia" in name:
                self.assertIn(name, RESUME_MEDIA_BROWSER_PROCEDURES)

    def test_sql_adapter_binds_owner_and_fail_closes_without_engine_proof(self):
        class FakeDatabase:
            def __init__(self):
                self.calls = []
                self.fail = False

            def execute_procedure(self, procedure, parameters=None):
                self.calls.append((procedure, list(parameters or [])))
                if self.fail:
                    raise ValueError("unapplied")
                return [
                    [{"draft_version": 2, "base_publication_version": None, "media_generation": 1}],
                    [],
                    [],
                ]

        database = FakeDatabase()
        store = SqlResumeMediaDraftStore(database)
        snapshot = store.load_owner("owner-a")
        self.assertEqual(snapshot["draft_version"], 2)
        self.assertEqual(database.calls[0][0], "usp_GetResumeMediaDraftForOwner")
        self.assertEqual(database.calls[0][1], [("@UserKey", "owner-a")])

        database.fail = True
        with self.assertRaises(ResumeMediaRepositoryError) as raised:
            store.load_owner("owner-a")
        self.assertEqual(raised.exception.code, "storage-unavailable")

        with self.assertRaises(ResumeMediaRepositoryError) as missing:
            store.save_owner("owner-a", {"draft_version": 2})
        self.assertEqual(missing.exception.code, "storage-unavailable")


if __name__ == "__main__":
    unittest.main()
