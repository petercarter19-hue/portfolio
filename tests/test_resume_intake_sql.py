"""Contract tests for proposed PS-RESUME-INTAKE-001 SQL.

The point of this file is *independent* agreement evidence:

* the closed key sets, type vocabularies and column lists are EXTRACTED from the
  real predecessor migrations (PS-RESUME-EDIT-002, PS-RESUME-DRAFT-001) rather
  than restated here;
* the payloads the service actually emits are validated against those extracted
  contracts;
* a regression fixture reproduces the previous candidate's wrong command shape
  and demonstrates that the same validator rejects it;
* the declared simulator implements the *procedure contract* (key sets, column
  lists, result shapes) and never applies canonical writes through Python.

Nothing here is SQL Server engine, driver, concurrency or rollback proof. That
requires a separately authorized disposable-database run and the registry gate
stays null.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import (
    CALLEE_COMMAND_KEYS,
    CALLEE_PROCEDURES,
    CALLEE_TYPE_VOCABULARY,
    COMMAND_KEY_SETS,
    COMMAND_PROCEDURES,
    InMemoryResumeIntakeRepository,
    RESUME_INTAKE_BROWSER_PROCEDURES,
    RESUME_INTAKE_WORKER_PROCEDURES,
    ResumeIntakeStoreUnavailable,
    SqlResumeIntakeRepository,
    map_declared_workspace,
)
from services.resume_intake_service import ResumeIntakeConflictError, ResumeIntakeService


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "SQL FIles" / "Migrations" / "proposed"
FORWARD = MIGRATIONS / "PS-RESUME-INTAKE-001_resume_intake.sql"
ROLLBACK = MIGRATIONS / "PS-RESUME-INTAKE-001_resume_intake_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-RESUME-INTAKE-001_resume_intake_verify.sql"
REGISTRY = ROOT / "SQL FIles" / "Migrations" / "registry.json"
EDIT_TWO = MIGRATIONS / "PS-RESUME-EDIT-002_education_commands.sql"
DRAFT_ONE = MIGRATIONS / "PS-RESUME-DRAFT-001_resume_drafts.sql"

SQL_KEYWORDS = frozenset(
    {
        "select", "from", "where", "as", "and", "or", "null", "is", "not", "in",
        "case", "when", "then", "else", "end", "by", "group", "having", "order",
        "inner", "left", "join", "on", "for", "json", "path", "without", "array",
        "wrapper", "convert", "nvarchar", "uniqueidentifier", "char", "int", "bit",
        "date", "bigint", "datetime2", "count", "isnull", "coalesce", "json_value",
        "json_query", "openjson", "with", "merge", "using", "matched", "update",
        "set", "insert", "values", "into", "delete", "declare", "throw", "exec",
        "procedure", "begin", "if", "exists", "return", "asc", "desc", "top",
    }
)


def _quoted(text):
    return [value.strip() for value in re.findall(r"N'([^']+)'", _normalize(text))]


def _normalize(text):
    """Undo the doubled-quote escaping used inside EXEC(N'...') bodies."""

    return text.replace("''", "'")


def _procedure_region(sql, name):
    start = sql.index(f"dbo.{name}")
    nxt = sql.find("CREATE OR ALTER PROCEDURE", start + 10)
    return sql[start : nxt if nxt != -1 else len(sql)]


def living_resume_contract():
    """Extract the real closed key set + type vocabulary from EDIT-002."""

    sql = _normalize(EDIT_TWO.read_text(encoding="utf-8"))
    keys = re.search(r"WHERE \[key\] NOT IN\s*\(([^)]*)\)", sql, re.S)
    types = re.search(r"@Type NOT IN\s*\(([^)]*)\)", sql, re.S)
    return frozenset(_quoted(keys.group(1))), frozenset(_quoted(types.group(1)))


def accomplishment_requires_parent():
    """The real semantic precondition b08b04a1's key matching missed."""

    sql = _normalize(EDIT_TWO.read_text(encoding="utf-8"))
    return bool(
        re.search(r"@Type = N'create_accomplishment' AND @ParentKey IS NULL", sql)
    )


def accomplishment_parent_predicate():
    """Extract the semantic parent predicate enforced by EDIT-002."""

    sql = _normalize(EDIT_TWO.read_text(encoding="utf-8"))
    start = sql.index("IF @RecordType = N'accomplishment'")
    body = sql[start:sql.index("IF @Wording IS NULL", start)]
    required = (
        "chapter.chapter_type = N'experience'",
        "chapter.deleted_at_utc IS NULL",
        "chapter.visibility = N'private'",
        "chapter.approval_status = N'draft'",
        "chapter.publication_status = N'unpublished'",
        "entity.visibility = N'private'",
        "entity.approval_status = N'draft'",
        "entity.publication_status = N'unpublished'",
        "entity.active = 1",
        "entity.deleted_at_utc IS NULL",
        "entity_publication_versions",
        "entity_access_grants",
        "content_approval_events",
    )
    return {condition: condition in body for condition in required}


def procedure_body(sql, name):
    """Extract one declared procedure body up to the end of its EXEC string."""

    start = sql.index("dbo." + name)
    end = re.search(r"\n    '\);", sql[start:])
    return sql[start:start + end.start()]


def transaction_findings(body):
    """Static findings about a compound body's runtime transaction ownership."""

    findings = []
    if not re.search(r"BEGIN\s+TRANSACTION", body):
        findings.append("no BEGIN TRANSACTION")
    if not re.search(r"COMMIT\s+TRANSACTION", body):
        findings.append("no COMMIT TRANSACTION")
    if body.count("BEGIN TRY") != 1 or body.count("BEGIN CATCH") != 1:
        findings.append("no single TRY/CATCH rollback boundary")
    returns = len(re.findall(r"RETURN;", body))
    committed_returns = len(re.findall(r"COMMIT\s+TRANSACTION;\s*\n\s*RETURN;", body))
    if returns and committed_returns != returns:
        findings.append("early RETURN leaves the transaction open")
    return findings


def resume_draft_contract():
    """Extract the real type vocabulary + referenced JSON paths from DRAFT-001."""

    sql = _normalize(DRAFT_ONE.read_text(encoding="utf-8"))
    procedure = _procedure_region(sql, "usp_CommitResumeDraftCommandForOwner")
    types = re.search(r"IF @CommandType NOT IN\s*\(([^)]*)\)", procedure, re.S)
    paths = set(re.findall(r"\$\.([a-z_]+)", procedure))
    return frozenset(_quoted(types.group(1))), frozenset(paths)


def table_columns(sql, table):
    match = re.search(rf"CREATE TABLE dbo\.{table}\s*\((.*?)\n\s*\);", sql, re.S)
    if not match:
        raise AssertionError(f"table {table} not found")
    columns = set()
    for line in match.group(1).splitlines():
        column = re.match(
            r"\s*([a-z_][a-z0-9_]*)\s+(bigint|int|nvarchar|char|uniqueidentifier|datetime2|decimal|bit|date|varbinary)\b",
            line,
        )
        if column and column.group(1).upper() not in {"CONSTRAINT", "PRIMARY"}:
            columns.add(column.group(1))
    return columns


class CalleeContractValidator:
    """Validates one staged canonical intent against the EXTRACTED contracts."""

    def __init__(self):
        self.living_keys, self.living_types = living_resume_contract()
        self.draft_types, self.draft_paths = resume_draft_contract()

    def validate(self, boundary, request_id, command):
        if boundary == "living_resume":
            if set(command) != self.living_keys:
                raise AssertionError(
                    f"living_resume keys {sorted(command)} != declared {sorted(self.living_keys)}"
                )
            if command["type"] not in self.living_types:
                raise AssertionError(
                    f"{command['type']!r} is outside the EDIT-002 type vocabulary"
                )
            if str(command["command_id"]) != str(request_id):
                raise AssertionError("command_id must equal the staged request id")
            if command["type"].startswith("create_") and command["expected_version"] is not None:
                raise AssertionError("a create must not carry expected_version")
            if command["type"] == "create_accomplishment" and not command.get("parent_key"):
                raise AssertionError("create_accomplishment requires a parent")
        elif boundary == "resume_draft":
            declared = CALLEE_COMMAND_KEYS["resume_draft"]
            if not set(command) <= declared:
                raise AssertionError(
                    f"resume_draft keys {sorted(command)} exceed declared {sorted(declared)}"
                )
            if command["type"] not in self.draft_types:
                raise AssertionError(
                    f"{command['type']!r} is outside the DRAFT-001 type vocabulary"
                )
            missing = self.draft_paths - set(command)
            if missing and command["type"] == "save_item":
                raise AssertionError(f"save_item omits declared paths {sorted(missing)}")
            if command["type"] == "save_item":
                # A change to an existing fact is a draft overlay, never a
                # canonical/shared write and never a permission expansion.
                if "expected_content_token" not in command or "expected_access_revision" not in command:
                    raise AssertionError("save_item must carry the captured target versions")
        else:
            raise AssertionError(f"unknown boundary {boundary!r}")
        return True


class DeclaredIntakeSimulator:
    """Implements the DECLARED procedure contract -- never Python canonical code.

    It validates every emitted command against the declared key set, validates
    every staged intent against the extracted callee contract, writes the
    declared intake rows and returns the declared result sets. It deliberately
    does NOT apply canonical writes: the real callee does that inside the same
    transaction, and faking it here is exactly the shortcut this file removes.
    """

    def __init__(self, fail_on_intent=None, fail_on_receipt=False):
        self.fail_on_intent = fail_on_intent
        self.fail_on_receipt = fail_on_receipt
        self.calls = []
        self.intents = []
        self._owners = {}
        self._validator = CalleeContractValidator()
        self._handled = {}
        self._recording_claims = {}

    # -- declared read ---------------------------------------------------

    def first_result(self, procedure_name, parameters=None):
        if procedure_name != "usp_GetResumeIntakeWorkspaceForOwner":
            raise DatabaseServiceError("unexpected read")
        owner = dict(parameters)["@UserKey"]
        self.calls.append((procedure_name, dict(parameters)))
        return [{"workspace_json": json.dumps(self.state(owner))}]

    def state(self, owner):
        return self._owners.setdefault(
            owner,
            {
                "lifecycle_epoch": 0,
                "policy_version": 0,
                "guide": None,
                "last_receipt_json": None,
                "submissions": [],
                "sources": [],
                "jobs": [],
                "proposals": [],
                "receipts": [],
            },
        )

    # -- declared writes --------------------------------------------------

    def execute_procedure(self, procedure_name, parameters=None):
        bound = dict(parameters or {})
        owner = bound.get("@UserKey")
        request_id = bound.get("@RequestId")
        payload = json.loads(bound.get("@CommandJson") or "{}")
        self.calls.append((procedure_name, bound))
        before = copy.deepcopy(self.state(owner))
        claims_before = copy.deepcopy(self._recording_claims)
        intent_count = len(self.intents)
        try:
            result = self._apply(procedure_name, owner, request_id, payload)
        except Exception:
            self._owners[owner] = before
            self._recording_claims = claims_before
            del self.intents[intent_count:]
            raise
        return result

    def _validate_command(self, procedure_name, request_id, payload):
        command_type = payload.get("type")
        if procedure_name not in RESUME_INTAKE_BROWSER_PROCEDURES:
            raise DatabaseServiceError("unknown procedure")
        if procedure_name != COMMAND_PROCEDURES.get(command_type):
            raise DatabaseServiceError(
                f"{command_type} must not be committed through {procedure_name}"
            )
        declared = set(COMMAND_KEY_SETS[command_type])
        if command_type in {"add_submission", "decide_proposal"}:
            declared.add("canonical_intents")
        if set(payload) != declared:
            raise DatabaseServiceError(
                f"{command_type} keys {sorted(payload)} != declared {sorted(declared)}"
            )
        if payload.get("request_id") != str(request_id):
            raise DatabaseServiceError("request id mismatch")
        for intent in payload.get("canonical_intents") or []:
            self._validator.validate(intent["boundary"], intent["request_id"], intent["command"])
        return command_type

    def _apply(self, procedure_name, owner, request_id, payload):
        state = self.state(owner)
        command_type = self._validate_command(procedure_name, request_id, payload)
        key = (owner, request_id)
        digest = payload.get("request_digest", "")
        if command_type == "claim_recording":
            if key in self._handled:
                if self._handled[key] != digest:
                    return [[{"outcome": "conflict", "request_digest": digest}]]
                stored = next(
                    row for row in state["receipts"] if row["request_id"] == str(request_id)
                )
                return [[{"outcome": "replay", "request_digest": digest,
                          "result_json": stored["result_json"]}]]
            existing = self._recording_claims.get(key)
            bindings = {
                name: payload[name]
                for name in (
                    "request_digest", "client_key", "entrance", "policy_version",
                    "lifecycle_epoch", "audio_sha256", "byte_length", "content_type",
                    "duration_seconds",
                )
            }
            if existing is not None:
                if any(existing.get(name) != value for name, value in bindings.items()):
                    return [[{"outcome": "conflict", "request_digest": digest}]]
                return [[{"outcome": "pending", "request_digest": digest,
                          "recovery_required": 0,
                          "lease_expires_at_utc": existing["lease_expires_at_utc"]}]]
            claim = {
                **bindings,
                "lease_id": str(uuid4()),
                "source_key": str(uuid4()),
                "state": "leased",
                "lease_expires_at_utc": "2026-09-11T00:05:00Z",
            }
            self._recording_claims[key] = claim
            state["policy_version"] = int(payload["policy_version"])
            return [[{"outcome": "claimed", "request_digest": digest,
                      "lease_id": claim["lease_id"], "source_key": claim["source_key"],
                      "lease_expires_at_utc": claim["lease_expires_at_utc"]}]]
        if key in self._handled:
            if self._handled[key] != digest:
                raise DatabaseServiceError("RESUME_INTAKE_IDEMPOTENCY_CONFLICT")
            stored = next(row for row in state["receipts"] if row["request_id"] == str(request_id))
            return [[{"committed": 1, "replayed": 1, "request_digest": digest,
                      "result_json": stored["result_json"]}]]

        for index, intent in enumerate(payload.get("canonical_intents") or []):
            if self.fail_on_intent is not None and index == self.fail_on_intent:
                raise DatabaseServiceError("synthetic second-item failure")
            self.intents.append(intent)

        if command_type == "add_submission":
            state["lifecycle_epoch"] = int(payload["lifecycle_epoch"])
            state["policy_version"] = int(payload["policy_version"])
            state["last_receipt_json"] = payload["last_receipt"]
            state["submissions"].append(
                {
                    "submission_key": payload["submission_key"],
                    "version": int(payload["submission_version"]),
                    "state": "active",
                    "entrance": payload["entrance"],
                    "policy_version": int(payload["policy_version"]),
                    "request_id": payload["request_id"],
                    "request_digest": payload["request_digest"],
                    "created_at_utc": "2026-09-11T00:00:00Z",
                }
            )
            for source in payload["sources"]:
                state["sources"].append(
                    {**source, "submission_key": payload["submission_key"]}
                )
            for job in payload["jobs"]:
                state["jobs"].append({**job, "attempts": 1})
            for proposal in payload["proposals"]:
                binding = proposal["binding"]
                state["proposals"].append(
                    {
                        # Declared column shape (flat), exactly as the SQL
                        # INSERT maps the payload's nested binding.
                        "proposal_key": proposal["proposal_key"],
                        "state": "pending",
                        "kind": proposal["kind"],
                        "record_type": proposal["record_type"],
                        "confidence": proposal.get("confidence"),
                        "target_key": proposal.get("target_key"),
                        "target_content_token": proposal.get("target_content_token"),
                        "target_access_revision": proposal.get("target_access_revision"),
                        "quote": proposal.get("quote"),
                        "span_start": proposal["span_start"],
                        "span_end": proposal["span_end"],
                        "proposed_values_json": json.dumps(proposal.get("proposed_values") or {}),
                        "provided_fields_json": json.dumps(proposal.get("provided_fields") or []),
                        "explicit_clears_json": json.dumps(proposal.get("explicit_clears") or []),
                        "confirmed_values_json": None,
                        "requires_member_wording": proposal.get("requires_member_wording"),
                        "command_digest": proposal.get("command_digest"),
                        "source_key": binding["source_key"],
                        "source_version": binding["source_version"],
                        "submission_key": binding["submission_key"],
                        "submission_version": binding["submission_version"],
                        "lifecycle_epoch": binding["lifecycle_epoch"],
                        "policy_version": binding["policy_version"],
                        "source_purged": 0,
                        "decision": None,
                        "decided_at_utc": None,
                        "created_at_utc": "2026-09-11T00:00:00Z",
                    }
                )
        elif command_type == "transcribe_recording":
            claim = self._recording_claims.get(key)
            bindings = {
                "request_digest": payload["request_digest"],
                "lease_id": payload["lease_id"],
                "source_key": payload["source_key"],
                "client_key": payload["client_key"],
                "entrance": payload["entrance"],
                "policy_version": payload["policy_version"],
                "lifecycle_epoch": payload["lifecycle_epoch"],
                "audio_sha256": payload["audio_sha256"],
                "byte_length": payload["byte_length"],
                "content_type": payload["content_type"],
                "duration_seconds": payload["duration_seconds"],
            }
            if (
                not claim or claim.get("state") != "leased"
                or any(claim.get(name) != value for name, value in bindings.items())
                or int(state["lifecycle_epoch"]) != int(payload["lifecycle_epoch"])
                or int(state["policy_version"]) != int(payload["policy_version"])
            ):
                raise DatabaseServiceError("RESUME_INTAKE_RECORDING_CLAIM_CHANGED")
            if payload["outcome"] == "transcribed":
                state["sources"].append(
                    {
                        "source_key": payload["source_key"],
                        "kind": "recording",
                        "state": "active",
                        "version": payload["source_version"],
                        "text": payload["transcript"],
                        "submission_key": None,
                        "content_type": payload["content_type"],
                        "byte_length": payload["byte_length"],
                        "sha256": payload["audio_sha256"],
                        "created_at_utc": "2026-09-11T00:00:00Z",
                    }
                )
        elif command_type == "decide_proposal":
            proposal = next(
                row for row in state["proposals"] if row["proposal_key"] == payload["proposal_key"]
            )
            if proposal["state"] != "pending":
                raise DatabaseServiceError("RESUME_INTAKE_ALREADY_DECIDED")
            proposal["state"] = "rejected" if payload["decision"] == "reject" else "accepted"
            proposal["decision"] = payload["decision"]
            proposal["confirmed_values_json"] = (
                json.dumps(payload.get("confirmed_values"))
                if payload["decision"] in {"accept", "edit"}
                else None
            )
        elif command_type == "purge_source":
            source = next(row for row in state["sources"] if row["source_key"] == payload["source_key"])
            source["state"] = "purged"
            source["text"] = None
            source["structured_values"] = None
            source["version"] = int(source["version"]) + 1
            state["lifecycle_epoch"] += 1
            for proposal in state["proposals"]:
                if proposal["source_key"] == payload["source_key"]:
                    proposal["source_purged"] = 1
                    proposal["quote"] = None
                    proposal["proposed_values_json"] = '{"redacted":true}'
                    proposal["confirmed_values_json"] = None
                    if proposal["state"] == "pending":
                        proposal["state"] = "invalidated"
        elif command_type == "set_guide_status":
            state["guide"] = {"status": payload["status"], "status_source": "member"}

        if self.fail_on_receipt:
            # The canonical rows and intake rows were written in this
            # transaction; a failing receipt rolls the whole transaction back.
            raise DatabaseServiceError("synthetic receipt failure")
        state["receipts"].append(
            {
                "request_id": str(request_id),
                "request_digest": digest,
                "service_digest": digest,
                "submission_key": payload.get("submission_key"),
                "outcome": payload.get("outcome") or payload.get("status") or "saved",
                "result_json": json.dumps(payload["receipt"]),
            }
        )
        self._handled[key] = digest
        if command_type == "transcribe_recording":
            self._recording_claims[key]["state"] = "completed"
        return [[{"committed": 1, "replayed": 0, "request_digest": digest}]]


def wav_bytes(payload=b"\x00" * 64):
    return b"RIFF" + (len(payload) + 36).to_bytes(4, "little") + b"WAVE" + payload


def _sql_service(simulator, transcriber=None):
    catalog = InMemoryCanonicalCatalog()
    draft = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog)
    repository = SqlResumeIntakeRepository(simulator)
    from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter

    service = ResumeIntakeService(
        repository=repository,
        draft_service=draft,
        transcription_adapter=ResumeTranscriptionAdapter(
            service=transcriber or _RecordingStub()
        ),
        policy=selected_policy_for_tests(),
    )
    return service, repository, catalog, draft


class ResumeIntakeSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    # -- static declarations ----------------------------------------------

    def test_registry_entry_is_proposed_with_null_gate(self):
        entry = next(
            item for item in self.registry["migrations"] if item["id"] == "PS-RESUME-INTAKE-001"
        )
        self.assertIsNone(entry["gate"])
        self.assertEqual(entry["requires"], ["PS-RESUME-DRAFT-001"])
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/proposed/PS-RESUME-INTAKE-001_resume_intake.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/proposed/PS-RESUME-INTAKE-001_resume_intake_rollback.sql",
        )

    def test_forward_sql_is_owner_keyed_serializable_and_closed(self):
        self.assertIn("PROPOSED ONLY", self.forward)
        self.assertIn("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE", self.forward)
        self.assertIn("WITH (UPDLOCK, HOLDLOCK)", self.forward)
        self.assertIn("@UserKey", self.forward)
        self.assertNotIn("@OwnerProfileId", self.forward)
        self.assertIn("RESUME_INTAKE_IDEMPOTENCY_CONFLICT", self.forward)
        self.assertIn("RESUME_INTAKE_STALE_JOB", self.forward)
        self.assertIn("RESUME_INTAKE_CHANGED", self.forward)
        self.assertIn("source_text = NULL", self.forward)
        self.assertNotIn("usp_Publish", self.forward)
        self.assertNotIn("resume_display = 1", self.forward)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*$", self.forward))

    def test_both_real_canonical_boundaries_are_called_with_their_own_dispatch(self):
        contract_keys, _types = living_resume_contract()
        draft_types, _paths = resume_draft_contract()
        self.assertEqual(contract_keys, CALLEE_COMMAND_KEYS["living_resume"])
        self.assertEqual(contract_keys, frozenset({"command_id", "type", "record_key",
                                                   "parent_key", "expected_version", "values"}))
        self.assertTrue(draft_types.issubset(CALLEE_TYPE_VOCABULARY["resume_draft"]))
        self.assertIn(CALLEE_PROCEDURES["living_resume"], self.forward)
        self.assertIn(CALLEE_PROCEDURES["resume_draft"], self.forward)
        # The dispatch is boundary-driven, not a blind rename.
        self.assertIn("living_resume", self.forward)
        self.assertIn("resume_draft", self.forward)
        self.assertIn("$.canonical_intents", self.forward)

    # -- runtime transaction ownership (P1) --------------------------------

    def test_every_compound_member_body_owns_a_runtime_transaction(self):
        compound = {
            "usp_ClaimResumeIntakeRecordingForOwner": self.forward,
            "usp_CommitResumeIntakeCommandForOwner": self.forward,
            "usp_CommitResumeIntakeProposalDecisionForOwner": self.forward,
            "usp_SetResumeGuideStatusForOwner": self.forward,
            "usp_PurgeResumeIntakeSourceForOwner": self.forward,
            "usp_ClaimResumeIntakeJobsForOwner": self.forward,
            "usp_CompleteResumeIntakeJobForOwner": self.forward,
            "usp_SweepExpiredResumeIntakeSources": self.forward,
        }
        for name in compound:
            findings = transaction_findings(procedure_body(self.forward, name))
            self.assertEqual(findings, [], f"{name}: {findings}")

    def test_canonical_intent_helper_does_not_commit_on_its_own(self):
        helper = procedure_body(self.forward, "usp_ResumeIntakeApplyCanonicalIntents")
        self.assertNotIn("BEGIN TRANSACTION", helper)
        self.assertNotIn("COMMIT TRANSACTION", helper)
        # It executes the two real callees, so the caller's transaction covers
        # both the canonical write and the intake rows.
        self.assertIn("usp_CommitLivingResumeCommandForOwner", helper)
        self.assertIn("usp_CommitResumeDraftCommandForOwner", helper)

    def test_nested_callee_transaction_semantics_are_as_expected(self):
        editor = procedure_body(
            _normalize(EDIT_TWO.read_text(encoding="utf-8")),
            "usp_CommitLivingResumeCommandForOwner",
        )
        draft = procedure_body(
            _normalize(DRAFT_ONE.read_text(encoding="utf-8")),
            "usp_CommitResumeDraftCommandForOwner",
        )
        # The editor callee owns a transaction and rolls back on failure, which
        # rolls the whole outer member action back.
        self.assertIn("BEGIN TRANSACTION", editor)
        self.assertIn("ROLLBACK TRANSACTION", editor)
        # The draft callee is called directly by the autocommit driver and
        # nested inside the intake transaction. It owns a transaction only when
        # it is the outermost caller; nested, it participates and never commits
        # or rolls the caller back.
        self.assertIn("DECLARE @OwnTransaction bit = 0", draft)
        self.assertIn("IF @@TRANCOUNT = 0", draft)
        self.assertIn("SET @OwnTransaction = 1", draft)
        self.assertIn("IF @OwnTransaction = 1 COMMIT TRANSACTION;", draft)
        self.assertIn(
            "IF @OwnTransaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;",
            draft,
        )
        # Every returning path releases the transaction it owns, and no
        # unguarded commit or rollback survives inside the callee.
        self.assertEqual(
            draft.count("IF @OwnTransaction = 1 COMMIT TRANSACTION;"),
            draft.count("RETURN;"),
        )
        unguarded = draft.replace(
            "IF @OwnTransaction = 1 COMMIT TRANSACTION;", ""
        ).replace(
            "IF @OwnTransaction = 1 AND XACT_STATE() <> 0 ROLLBACK TRANSACTION;", ""
        )
        self.assertNotIn("COMMIT TRANSACTION", unguarded)
        self.assertNotIn("ROLLBACK TRANSACTION", unguarded)
        self.assertEqual(draft.count("BEGIN TRY"), 1)
        self.assertEqual(draft.count("BEGIN CATCH"), 1)
        # The exact replay still wins before the expected-version fence.
        self.assertLess(
            draft.index("IF @ExistingDigest IS NOT NULL"),
            draft.index("IF ISNULL(@DraftVersion, 0) <> @ExpectedDraftVersion"),
        )

    def test_overlay_decision_fences_the_version_observed_before_commit(self):
        catalog = InMemoryCanonicalCatalog()
        draft = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(), catalog=catalog
        )
        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=draft,
            policy=selected_policy_for_tests(),
        )
        existing_key = str(uuid4())
        catalog.put_item(
            "owner-a",
            {
                "record_key": existing_key,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {
                    "role_title": "Systems Engineer", "employer_name": "Northrop Grumman",
                    "location_text": None, "summary": "Keeps the summary.",
                    "start_date": "2025-01-01", "end_date": None, "date_precision": "month",
                    "employment_type": "full_time", "current_role": True,
                },
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        created = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role",
                           "values": {"role_title": "Systems Engineer",
                                      "employer_name": "Northrop Grumman",
                                      "location_text": "Huntsville, Alabama"},
                           "explicit_clears": []}],
            },
        )
        proposal = created["proposals"][0]

        # A concurrent draft save lands after the decision's authoritative read
        # but before the overlay commit, so the fence must reject it.
        real_workspace = draft.get_workspace
        advanced = {"done": False}

        def racing_workspace(owner):
            workspace = real_workspace(owner)
            if not advanced["done"]:
                advanced["done"] = True
                draft.commit(
                    owner,
                    {
                        "request_id": str(uuid4()),
                        "type": "save_item",
                        "record_key": existing_key,
                        "record_type": "role",
                        "expected_content_token": "1",
                        "expected_access_revision": 1,
                        "values": {"summary": "Concurrent save"},
                    },
                )
            return workspace

        draft.get_workspace = racing_workspace
        try:
            with self.assertRaises(ResumeIntakeConflictError) as caught:
                service.decide(
                    "owner-a",
                    {
                        "request_id": str(uuid4()),
                        "proposal_key": proposal["proposal_key"],
                        "decision": "accept",
                        "confirmed_values": proposal["proposed_values"],
                    },
                )
        finally:
            draft.get_workspace = real_workspace
        self.assertEqual(caught.exception.error_code, "changed")

    def test_previous_candidate_body_fails_the_transaction_assertion(self):
        """A fixture of b08b04a1's body must fail the same check."""

        old_body = (
            "AS\nBEGIN\n    SET NOCOUNT ON;\n    SET XACT_ABORT ON;\n"
            "    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;\n\n"
            "    DECLARE @ProfileId bigint;\n"
            "    SELECT CONVERT(bit, 1) AS committed;\nEND;\n"
        )
        findings = transaction_findings(old_body)
        self.assertEqual(len(findings), 3, findings)

    def test_every_declared_command_key_appears_in_the_sql(self):
        for command_type, keys in COMMAND_KEY_SETS.items():
            for key in sorted(keys):
                self.assertIn(f"$.{key}", self.forward, f"{command_type} key {key} missing from SQL")

    def test_decision_retains_confirmed_wording_only_in_the_purgeable_proposal(self):
        decision = procedure_body(self.forward, "usp_CommitResumeIntakeProposalDecisionForOwner")
        purge = procedure_body(self.forward, "usp_PurgeResumeIntakeSourceForOwner")
        self.assertIn("confirmed_values_json = CASE", decision)
        self.assertIn("JSON_QUERY(@CommandJson, '$.confirmed_values')", _normalize(decision))
        self.assertIn("confirmed_values_json = NULL", purge)
        self.assertIn("JSON_QUERY(@CommandJson, '$.receipt')", _normalize(decision))

    def test_guide_replay_compares_service_digest_before_returning(self):
        guide = _normalize(procedure_body(self.forward, "usp_SetResumeGuideStatusForOwner"))
        self.assertIn("DECLARE @ServiceDigest", guide)
        self.assertIn("IF @ExistingDigest <> @ServiceDigest", guide)
        self.assertIn("RESUME_INTAKE_IDEMPOTENCY_CONFLICT", guide)

    def test_recording_claim_never_transfers_expired_provider_custody(self):
        claim = _normalize(
            procedure_body(self.forward, "usp_ClaimResumeIntakeRecordingForOwner")
        )
        finalize = _normalize(
            procedure_body(self.forward, "usp_CommitResumeIntakeCommandForOwner")
        )
        self.assertIn("'pending' AS outcome", claim)
        self.assertIn("recovery_required", claim)
        self.assertNotIn("SET lease_id = NEWID", claim)
        for field in (
            "request_digest", "lease_id", "source_key", "policy_version",
            "lifecycle_epoch", "audio_sha256", "byte_length", "content_type",
            "duration_seconds", "lease_expires_at_utc",
        ):
            self.assertIn(field, finalize)

    def test_every_member_replay_returns_the_stored_structural_receipt(self):
        for name in (
            "usp_CommitResumeIntakeCommandForOwner",
            "usp_CommitResumeIntakeProposalDecisionForOwner",
            "usp_SetResumeGuideStatusForOwner",
            "usp_PurgeResumeIntakeSourceForOwner",
        ):
            body = _normalize(procedure_body(self.forward, name))
            replay = body.split("IF @ExistingDigest IS NOT NULL", 1)[1].split("RETURN;", 1)[0]
            self.assertIn("@ExistingResult AS result_json", replay, name)
            self.assertIn("@ExistingDigest AS request_digest", replay, name)

    def test_sweep_keeps_a_fresh_pre_add_recording(self):
        sweep = _normalize(procedure_body(self.forward, "usp_SweepExpiredResumeIntakeSources"))
        self.assertIn("MAX(source.created_at_utc) < DATEADD", sweep)
        self.assertIn("MAX(submission.created_at_utc)", sweep)
        self.assertNotIn("MAX(ISNULL((", sweep)

    def test_browser_procedures_are_allowlisted_and_workers_are_not(self):
        for name in RESUME_INTAKE_BROWSER_PROCEDURES:
            self.assertIn(name, self.forward)
            self.assertIn(name, ALLOWED_PROCEDURES)
        self.assertTrue(RESUME_INTAKE_WORKER_PROCEDURES)
        self.assertTrue(
            RESUME_INTAKE_WORKER_PROCEDURES.isdisjoint(RESUME_INTAKE_BROWSER_PROCEDURES)
        )
        for name in RESUME_INTAKE_WORKER_PROCEDURES:
            self.assertIn(name, self.forward)
            self.assertNotIn(name, ALLOWED_PROCEDURES)

    def test_rollback_and_verify_are_structural_only(self):
        self.assertIn("DELETE dbo.schema_migrations", self.rollback)
        self.assertIn("PS-RESUME-INTAKE-001", self.rollback)
        self.assertIn("Rollback refused", self.rollback)
        self.assertIn("verified", self.verify)
        self.assertIn("runtime proof remains outstanding", self.verify)
        # The verifier must require the CORRECT boundaries, not the wrong one.
        self.assertIn("usp_CommitLivingResumeCommandForOwner", self.verify)
        self.assertIn("usp_CommitResumeDraftCommandForOwner", self.verify)
        self.assertIn("service_digest", self.verify)
        self.assertIn("structured_values_json = NULL", self.verify)

    # -- T-SQL dialect lint (static, not engine proof) ---------------------

    def _lint(self, sql):
        findings = []
        if re.search(r"ISJSON\s*\([^()]*,[^)]*\)", sql):
            findings.append("ISJSON with a second argument")
        for statement in re.finditer(r"EXEC\s+dbo\.\w+\s*(.*?);", sql, re.S):
            if re.search(r"@\w+\s*=\s*[A-Za-z_][A-Za-z0-9_]*\s*\(", statement.group(1)):
                findings.append("function call passed directly to EXEC")
                break
        if re.search(r"\bDECLARE\s+@\w+\s+json\b", sql, re.I):
            findings.append("native json type")
        if re.search(r"JSON_(?:VALUE|QUERY)\s*\([^,]+,\s*CONCAT\s*\(", sql, re.I):
            findings.append("computed JSON path")
        return findings

    def test_declared_sql_passes_the_dialect_lint(self):
        self.assertEqual(self._lint(self.forward), [])

    def test_lint_rejects_the_previous_candidates_constructs(self):
        """A fixture of e5572993's constructs must fail the same lint."""

        old_snippet = (
            "IF ISJSON(@CommandJson, '$.sources') IS NULL THROW 52304, 'x', 1;\n"
            "EXEC dbo.usp_CommitLivingResumeCommandForOwner\n"
            "    @UserKey = @UserKey,\n"
            "    @CommandId = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, '$.command_id')),\n"
            "    @CommandJson = @IntentCommand;\n"
            "DECLARE @Canonical json = JSON_QUERY(@CommandJson, '$.canonical_intents');\n"
            "SET @C = JSON_QUERY(@Canonical, CONCAT('$[', @Index, '].command'));\n"
        )
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / "previous_candidate.sql"
            fixture.write_text(old_snippet, encoding="utf-8")
            findings = self._lint(fixture.read_text(encoding="utf-8"))
        self.assertEqual(len(findings), 4, findings)

    def test_previous_candidate_payload_is_rejected_by_the_extracted_contract(self):
        """The old draft-shaped create must fail the real EDIT-002 contract."""

        validator = CalleeContractValidator()
        old_payload = {
            "request_id": str(uuid4()),
            "type": "create_private_item",
            "record_key": str(uuid4()),
            "record_type": "skill",
            "values": {"name": "MBSE", "summary": None},
            "intended_permission_expansions": {"resume_display": False, "visitor_ai": False},
        }
        with self.assertRaises(AssertionError):
            validator.validate("living_resume", old_payload["request_id"], old_payload)
        # ...and it also fails the draft boundary, because create_private_item is
        # not the overlay command a change to an existing fact uses here.
        with self.assertRaises(AssertionError):
            validator.validate("resume_draft", old_payload["request_id"], old_payload)

    def test_accomplishment_parent_precondition_is_extracted_and_enforced(self):
        """b08b04a1 staged create_accomplishment with parent_key = None."""

        self.assertTrue(accomplishment_requires_parent())
        validator = CalleeContractValidator()
        bad = {
            "command_id": str(uuid4()),
            "type": "create_accomplishment",
            "record_key": str(uuid4()),
            "parent_key": None,
            "expected_version": None,
            "values": {"wording": "Led the migration", "metric_value": None, "metric_label": None},
        }
        with self.assertRaises(AssertionError):
            validator.validate("living_resume", bad["command_id"], bad)
        good = dict(bad, parent_key=str(uuid4()))
        self.assertTrue(validator.validate("living_resume", good["command_id"], good))

    def test_accomplishment_parent_full_eligibility_predicate_is_extracted(self):
        extracted = accomplishment_parent_predicate()
        self.assertTrue(all(extracted.values()), extracted)

    # -- accomplishment parent (P2) ----------------------------------------

    def _seed_role(self, catalog, owner, record_key):
        catalog.put_item(
            owner,
            {
                "record_key": record_key,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {
                    "role_title": "Engineering Manager", "employer_name": "Northrop Grumman",
                    "location_text": None, "summary": None, "start_date": None, "end_date": None,
                    "date_precision": "unknown", "employment_type": None, "current_role": False,
                },
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )

    def _accomplishment_item(self, client_key, parent_key=None):
        item = {
            "client_key": client_key,
            "record_type": "accomplishment",
            "values": {"wording": "Led the migration", "metric_value": None, "metric_label": None},
        }
        if parent_key:
            item["parent_key"] = parent_key
        return item

    def test_accomplishment_intent_serializes_a_real_owner_parent(self):
        simulator = DeclaredIntakeSimulator()
        service, _repository, catalog, _draft = _sql_service(simulator)
        parent_key = str(uuid4())
        self._seed_role(catalog, "owner-a", parent_key)
        receipt = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [self._accomplishment_item("a1", parent_key)],
            },
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        intent = simulator.intents[0]
        self.assertEqual(intent["command"]["type"], "create_accomplishment")
        self.assertEqual(intent["command"]["parent_key"], parent_key)
        CalleeContractValidator().validate("living_resume", intent["request_id"], intent["command"])

    def test_unresolved_or_foreign_parent_stays_an_actionable_proposal(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, catalog, _draft = _sql_service(simulator)
        missing = service.submit(
            "owner-a",
            {"type": "add_submission", "request_id": str(uuid4()),
             "items": [self._accomplishment_item("a1")]},
        )
        self.assertEqual(missing["summary"]["saved"], 0)
        self.assertEqual(missing["summary"]["unresolved"], 1)
        self.assertEqual(missing["results"][0]["code"], "parent_required")
        self.assertEqual(len(repository.load_owner("owner-a")["receipts"]), 1)
        self.assertEqual(simulator.intents, [])

        foreign = service.submit(
            "owner-a",
            {"type": "add_submission", "request_id": str(uuid4()),
             "items": [self._accomplishment_item("a2", str(uuid4()))]},
        )
        self.assertEqual(foreign["summary"]["saved"], 0)
        self.assertEqual(foreign["summary"]["unresolved"], 1)
        self.assertEqual(foreign["results"][0]["code"], "parent_not_found")
        self.assertEqual(simulator.intents, [])

    def test_wrong_type_and_history_bearing_role_never_stage_an_intent(self):
        forbidden = (
            ("education", True, "canonical", "parent_type_ineligible"),
            ("credential", True, "canonical", "parent_type_ineligible"),
            ("role", False, "draft_overlay", "parent_ineligible"),
        )
        for record_type, editable, save_mode, expected_code in forbidden:
            with self.subTest(record_type=record_type, editable=editable):
                simulator = DeclaredIntakeSimulator()
                service, _repository, catalog, _draft = _sql_service(simulator)
                parent_key = str(uuid4())
                catalog.put_item(
                    "owner-a",
                    {
                        "record_key": parent_key,
                        "record_type": record_type,
                        "content_token": "1",
                        "access_revision": 1,
                        "editable": editable,
                        "blocked_reason": None if editable else "published_or_history_bearing",
                        "save_mode": save_mode,
                        "values": {"title": "Education"} if record_type == "education" else (
                            {"name": "Credential"} if record_type == "credential" else {
                                "role_title": "Published role", "employer_name": "Example"
                            }
                        ),
                        "resume_display": not editable,
                        "visitor_ai": False,
                        "private_assistance_excluded": False,
                    },
                )
                receipt = service.submit(
                    "owner-a",
                    {
                        "type": "add_submission",
                        "request_id": str(uuid4()),
                        "items": [self._accomplishment_item("impact", parent_key)],
                    },
                )
                self.assertEqual(receipt["summary"]["unresolved"], 1)
                self.assertEqual(receipt["results"][0]["code"], expected_code)
                self.assertEqual(simulator.intents, [])

    # -- replay content (P1b) ----------------------------------------------

    def test_recording_replay_recovers_content_before_purge_and_not_after(self):
        provider = _RecordingStub("Transcript words for recovery.")
        simulator = DeclaredIntakeSimulator()
        service, repository, _c, _d = _sql_service(simulator, transcriber=provider)
        body = {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0}
        first = service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        retry = service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        self.assertEqual(first["transcript"], "Transcript words for recovery.")
        self.assertEqual(retry["transcript"], "Transcript words for recovery.")
        self.assertTrue(retry["replayed"])
        self.assertTrue(retry["content_recovered"])
        self.assertEqual(len(provider.calls), 1)  # no second provider call

        service.purge_source(
            "owner-a", {"request_id": str(uuid4()), "source_key": first["source_key"]}
        )
        after = service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        self.assertIsNone(after["transcript"])
        self.assertTrue(after["source_purged"])
        self.assertFalse(after["content_recovered"])
        self.assertNotIn("Transcript words for recovery.", json.dumps(after))
        self.assertEqual(len(provider.calls), 1)

    def test_unresolved_add_replay_recovers_live_wording(self):
        simulator = DeclaredIntakeSimulator()
        service, _repository, _catalog, _draft = _sql_service(simulator)
        request_id = str(uuid4())
        body = {"type": "add_submission", "request_id": request_id, "text": "Live proposal words."}
        service.submit("owner-a", body)
        retry = service.submit("owner-a", body)
        self.assertTrue(retry["replayed"])
        self.assertEqual([row["quote"] for row in retry["proposals"]], ["Live proposal words."])

    def test_decision_replay_recovers_the_live_proposal_view(self):
        simulator = DeclaredIntakeSimulator()
        service, _repository, _catalog, _draft = _sql_service(simulator)
        created = service.submit(
            "owner-a",
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Decision replay words."},
        )
        body = {
            "request_id": str(uuid4()),
            "proposal_key": created["proposals"][0]["proposal_key"],
            "decision": "reject",
        }
        service.decide("owner-a", body)
        retry = service.decide("owner-a", body)
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["proposal"]["state"], "rejected")
        self.assertEqual(retry["proposal"]["quote"], "Decision replay words.")

    def test_sql_shaped_round_trip_retains_then_purges_accepted_wording(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, _catalog, _draft = _sql_service(simulator)
        created = service.submit(
            "owner-a",
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Source wording."},
        )
        proposal_key = created["proposals"][0]["proposal_key"]
        source_key = created["proposals"][0]["provenance"]["source_key"]
        service.decide(
            "owner-a",
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": {"record_type": "skill", "name": "Accepted wording"},
            },
        )
        retained = repository.load_owner("owner-a")["proposals"][proposal_key]
        self.assertEqual(retained["confirmed_values"]["name"], "Accepted wording")
        service.purge_source(
            "owner-a", {"request_id": str(uuid4()), "source_key": source_key}
        )
        purged = repository.load_owner("owner-a")["proposals"][proposal_key]
        self.assertIsNone(purged["confirmed_values"])

    # -- column cross-checks ------------------------------------------------

    def test_every_inserted_and_updated_intake_column_exists(self):
        tables = {
            name: table_columns(self.forward, name)
            for name in (
                "resume_intake_owner_state",
                "resume_intake_submissions",
                "resume_intake_sources",
                "resume_intake_jobs",
                "resume_intake_proposals",
                "resume_intake_results",
                "resume_intake_command_receipts",
                "resume_intake_recording_claims",
            )
        }
        for table, columns in tables.items():
            self.assertTrue(columns, table)
        for match in re.finditer(
            r"INSERT dbo\.(resume_intake_\w+)\s*\(([^)]*)\)", self.forward, re.S
        ):
            table = match.group(1)
            if table not in tables:
                continue
            for name in re.findall(r"([a-z_][a-z0-9_]*)", match.group(2)):
                self.assertIn(name, tables[table], f"{table}.{name} missing from CREATE TABLE")
        for match in re.finditer(
            r"UPDATE dbo\.(resume_intake_\w+)\s+SET(.*?)(?:WHERE|;)", self.forward, re.S
        ):
            table = match.group(1)
            if table not in tables:
                continue
            for name in re.findall(r"^\s*([a-z_][a-z0-9_]*)\s*=", match.group(2), re.M):
                self.assertIn(name, tables[table], f"{table}.{name} missing from CREATE TABLE")
        # The workspace read selects only declared columns.
        read_region = self.forward[self.forward.index("usp_GetResumeIntakeWorkspaceForOwner"):]
        for match in re.finditer(r"FROM dbo\.(resume_intake_\w+)", read_region):
            table = match.group(1)
            if table not in tables:
                continue
            start = read_region.rfind("SELECT", 0, match.start())
            if start == -1:
                continue
            for item in read_region[start + len("SELECT"): match.start()].split(","):
                item = item.strip()
                converted = re.match(r"CONVERT\([^,]+,\s*([a-z_][a-z0-9_]*)\)$", item)
                bare = re.match(r"^([a-z_][a-z0-9_]*)$", item)
                name = converted.group(1) if converted else (bare.group(1) if bare else None)
                if name:
                    self.assertIn(name, tables[table], f"{table}.{name} missing from CREATE TABLE")

    # -- declared-shape mapping ---------------------------------------------

    def test_read_mapping_uses_only_declared_columns(self):
        declared = {
            "lifecycle_epoch": 3,
            "policy_version": 1,
            "guide": {"status": "in_progress", "status_source": "member"},
            "last_receipt_json": {"outcome": "saved", "summary": {"saved": 1}},
            "submissions": [],
            "sources": [],
            "jobs": [],
            "proposals": [
                {
                    "proposal_key": str(UUID(int=5, version=4)),
                    "state": "pending", "kind": "ambiguous_match", "record_type": "skill",
                    "confidence": "similar",
                    "target_key": str(UUID(int=7, version=4)),
                    "target_content_token": "1", "target_access_revision": 2,
                    "quote": "MBSE", "span_start": 0, "span_end": 4,
                    "proposed_values_json": '{"name":"mbse"}',
                    "provided_fields_json": '["name"]', "explicit_clears_json": "[]",
                    "confirmed_values_json": None, "requires_member_wording": 1,
                    "command_digest": "a" * 64,
                    "source_key": str(UUID(int=6, version=4)), "source_version": 1,
                    "submission_key": str(UUID(int=8, version=4)), "submission_version": 1,
                    "lifecycle_epoch": 3, "policy_version": 1, "source_purged": 0,
                    "decision": None, "decided_at_utc": None,
                    "created_at_utc": "2026-09-11T00:00:00Z",
                }
            ],
            "receipts": [],
        }
        mapped = map_declared_workspace(declared)
        self.assertEqual(mapped["guide"]["status"], "in_progress")
        self.assertEqual(mapped["last_receipt"]["outcome"], "saved")
        proposal = next(iter(mapped["proposals"].values()))
        self.assertEqual(proposal["confidence"], "similar")
        self.assertEqual(proposal["binding"]["source_version"], 1)
        self.assertEqual(proposal["proposed_values"], {"name": "mbse"})

    def test_read_mapping_fails_closed_on_an_undeclared_shape(self):
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            map_declared_workspace({"lifecycle_epoch": 0})
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            map_declared_workspace({"lifecycle_epoch": 0, "policy_version": 0, "receipts": {}})

    def test_sql_adapter_fails_closed_without_engine_proof(self):
        class DownDatabase:
            def first_result(self, *args, **kwargs):
                raise ValueError("unapplied")

            def execute_procedure(self, *args, **kwargs):
                raise ValueError("unapplied")

        repository = SqlResumeIntakeRepository(DownDatabase())
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            repository.load_owner("owner-a")
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            repository.save_owner("owner-a", {"submissions": {}})
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            repository.save_owner(
                "owner-a", {}, {"procedure": "usp_NotIntake", "request_id": "x", "payload": {}}
            )

    # -- real service against the declared contract -------------------------

    def test_emitted_living_resume_intent_matches_the_real_edit_002_contract(self):
        simulator = DeclaredIntakeSimulator()
        service, _repository, _catalog, _draft = _sql_service(simulator)
        service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s1", "record_type": "skill",
                           "values": {"name": "MBSE"}, "explicit_clears": []}],
            },
        )
        self.assertEqual(len(simulator.intents), 1)
        intent = simulator.intents[0]
        self.assertEqual(intent["boundary"], "living_resume")
        self.assertEqual(intent["procedure"], "usp_CommitLivingResumeCommandForOwner")
        self.assertEqual(intent["command"]["type"], "create_skill")
        self.assertIsNone(intent["command"]["expected_version"])
        CalleeContractValidator().validate("living_resume", intent["request_id"], intent["command"])

    def test_emitted_draft_intent_matches_the_real_draft_contract(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, catalog, draft = _sql_service(simulator)
        existing_key = str(uuid4())
        catalog.put_item(
            "owner-a",
            {
                "record_key": existing_key,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {
                    "role_title": "Systems Engineer", "employer_name": "Northrop Grumman",
                    "location_text": None, "summary": "Keeps the summary.",
                    "start_date": "2025-01-01", "end_date": None, "date_precision": "month",
                    "employment_type": "full_time", "current_role": True,
                },
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        created = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role",
                           "values": {"role_title": "Systems Engineer",
                                      "employer_name": "Northrop Grumman",
                                      "location_text": "Huntsville, Alabama"},
                           "explicit_clears": []}],
            },
        )
        proposal = created["proposals"][0]
        # Advance the authoritative draft first so a fabricated default version
        # cannot satisfy the contract.
        draft.commit(
            "owner-a",
            {
                "request_id": str(uuid4()),
                "type": "save_item",
                "record_key": existing_key,
                "record_type": "role",
                "expected_content_token": "1",
                "expected_access_revision": 1,
                "values": {"summary": "Existing draft wording"},
            },
        )
        observed_version = draft.get_workspace("owner-a")["draft_version"]
        self.assertEqual(observed_version, 1)
        service.decide(
            "owner-a",
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal["proposal_key"],
                "decision": "accept",
                "confirmed_values": proposal["proposed_values"],
            },
        )
        draft_intents = [row for row in simulator.intents if row["boundary"] == "resume_draft"]
        self.assertEqual(len(draft_intents), 1)
        command = draft_intents[0]["command"]
        self.assertEqual(command["type"], "save_item")
        self.assertEqual(command["expected_content_token"], "1")
        self.assertEqual(command["expected_access_revision"], 1)
        self.assertEqual(set(command["values"]),
                         {"role_title", "employer_name", "location_text"})
        # The staged intent carries the authoritative version and the canonical
        # semantic digest of exactly this command, not placeholders.
        self.assertEqual(command["expected_draft_version"], observed_version)
        rebuilt = {
            key: value for key, value in command.items() if key != "request_digest"
        }
        rebuilt["request_id"] = draft_intents[0]["request_id"]
        self.assertRegex(command["request_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(draft.command_digest(rebuilt), command["request_digest"])
        CalleeContractValidator().validate("resume_draft", draft_intents[0]["request_id"], command)

    def test_each_operation_emits_its_declared_key_set(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, _catalog, _draft = _sql_service(simulator)
        from services.resume_guide_service import ResumeGuideService

        created = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s1", "record_type": "skill",
                           "values": {"name": "MBSE"}, "explicit_clears": []}],
                "text": "A private note.",
            },
        )
        service.transcribe_recording(
            "owner-a",
            _Upload(wav_bytes()),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0},
        )
        source_key = created["submission"]["source_keys"][0]
        service.decide(
            "owner-a",
            {"request_id": str(uuid4()),
             "proposal_key": created["proposals"][0]["proposal_key"],
             "decision": "reject"},
        )
        service.purge_source("owner-a", {"request_id": str(uuid4()), "source_key": source_key})
        ResumeGuideService(repository=repository).set_status("owner-a", {"status": "completed"})

        writes = {}
        for procedure, bound in simulator.calls:
            if procedure == "usp_GetResumeIntakeWorkspaceForOwner":
                continue
            payload = json.loads(bound["@CommandJson"])
            declared = set(COMMAND_KEY_SETS[payload["type"]])
            if payload["type"] in {"add_submission", "decide_proposal"}:
                declared.add("canonical_intents")
            writes[payload["type"]] = set(payload)
            self.assertEqual(set(payload), declared, payload["type"])
        self.assertEqual(
            set(writes),
            {"add_submission", "claim_recording", "transcribe_recording", "decide_proposal",
             "purge_source", "set_guide_status"},
        )

    def test_durable_round_trip_keeps_receipt_last_receipt_and_replay(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, catalog, _draft = _sql_service(simulator)
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "s1", "record_type": "skill",
                       "values": {"name": "MBSE"}, "explicit_clears": []}],
        }
        first = service.submit("owner-a", body)
        self.assertTrue(first["persisted"])
        self.assertTrue(first["saved_items"][0]["persisted"])
        catalog.put_item(
            "owner-a",
            {
                "record_key": first["saved_items"][0]["record_key"],
                "record_type": "skill",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {"name": "MBSE", "summary": None},
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        # A durable reload shows the confirmed receipt (R5).
        reloaded = service.get_workspace("owner-a")
        self.assertIsNotNone(reloaded["last_receipt"])
        self.assertEqual(reloaded["last_receipt"]["summary"]["saved"], 1)
        # Same key + same payload replays the stored structural receipt.
        replay = service.submit("owner-a", body)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["saved_items"][0]["values"]["name"], "MBSE")
        self.assertTrue(replay["saved_items"][0]["content_equivalent_to_first_response"])
        self.assertEqual(
            replay["submission"]["submission_key"], first["submission"]["submission_key"]
        )
        with self.assertRaises(Exception):
            service.submit(
                "owner-a",
                {**body, "items": [{"client_key": "s1", "record_type": "skill",
                                    "values": {"name": "Different"}, "explicit_clears": []}]},
            )

    def test_sql_replay_output_replaces_a_stale_callers_local_structural_ids(self):
        simulator = DeclaredIntakeSimulator()
        service, _repository, _catalog, _draft = _sql_service(simulator)
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "s1", "record_type": "skill",
                       "values": {"name": "MBSE"}, "explicit_clears": []}],
        }
        winner = service.submit("owner-a", body)
        winner_submission = winner["submission"]["submission_key"]

        # Reproduce a caller that loaded just before another connection won.
        # Its local plan creates fresh IDs, but the procedure reports replay
        # and returns the already persisted owner-qualified receipt.
        original_read = simulator.first_result
        stale_once = {"remaining": 1}

        def stale_read(procedure_name, parameters=None):
            if stale_once["remaining"]:
                stale_once["remaining"] -= 1
                owner = dict(parameters)["@UserKey"]
                state = copy.deepcopy(simulator.state(owner))
                state["receipts"] = []
                return [{"workspace_json": json.dumps(state)}]
            return original_read(procedure_name, parameters)

        simulator.first_result = stale_read
        replay = service.submit("owner-a", body)
        second_command = json.loads(simulator.calls[-2][1]["@CommandJson"])

        self.assertNotEqual(second_command["submission_key"], winner_submission)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["submission"]["submission_key"], winner_submission)
        self.assertNotEqual(
            replay["submission"]["submission_key"], second_command["submission_key"]
        )

    def test_recording_persists_honestly_and_replays(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, _catalog, _draft = _sql_service(simulator)
        request_id = str(uuid4())
        body = {"request_id": request_id, "client_key": "mic-1", "duration_seconds": 3.0}
        first = service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        self.assertTrue(first["success"])
        snapshot = repository.load_owner("owner-a")
        source = next(iter(snapshot["sources"].values()))
        self.assertIsNone(source["submission_key"])  # pre-Add, not a submission
        self.assertEqual(source["kind"], "recording")
        # The stored receipt carries no transcript copy.
        stored = snapshot["receipts"][request_id]["result"]
        self.assertNotIn("transcript", json.dumps(stored))
        self.assertIsNotNone(snapshot["receipts"][request_id]["request_digest"])
        replay = service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        self.assertTrue(replay["replayed"])

    def test_sql_shaped_claim_prevents_cross_instance_provider_duplication(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingProvider(_RecordingStub):
            def transcribe(self, audio_bytes, content_type, locale="en-US"):
                result = super().transcribe(audio_bytes, content_type, locale)
                entered.set()
                release.wait(timeout=5)
                return result

        simulator = DeclaredIntakeSimulator()
        provider = BlockingProvider("one durable winner")
        holder_service, _r1, _c1, _d1 = _sql_service(simulator, transcriber=provider)
        competing_service, _r2, _c2, _d2 = _sql_service(simulator, transcriber=provider)
        body = {
            "request_id": str(uuid4()), "client_key": "mic-sql-race",
            "duration_seconds": 3.0,
        }
        holder_results = []

        holder = threading.Thread(target=lambda: holder_results.append(
            holder_service.transcribe_recording("owner-a", _Upload(wav_bytes()), body)
        ))
        holder.start()
        self.assertTrue(entered.wait(timeout=5))
        pending = competing_service.transcribe_recording(
            "owner-a", _Upload(wav_bytes()), body
        )

        self.assertEqual(pending["outcome"], "pending")
        self.assertFalse(pending["provider_called_by_this_attempt"])
        self.assertEqual(len(provider.calls), 1)
        with self.assertRaises(ResumeIntakeConflictError):
            competing_service.transcribe_recording(
                "owner-a", _Upload(wav_bytes()),
                {**body, "duration_seconds": 4.0},
            )
        self.assertEqual(len(provider.calls), 1)
        release.set()
        holder.join(timeout=5)
        replay = competing_service.transcribe_recording(
            "owner-a", _Upload(wav_bytes()), body
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["source_key"], holder_results[0]["source_key"])
        self.assertEqual(len(provider.calls), 1)

    def test_decision_replay_after_a_dropped_response(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, _catalog, _draft = _sql_service(simulator)
        created = service.submit(
            "owner-a",
            {"type": "add_submission", "request_id": str(uuid4()), "text": "A note."},
        )
        proposal_key = created["proposals"][0]["proposal_key"]
        request_id = str(uuid4())
        body = {"request_id": request_id, "proposal_key": proposal_key, "decision": "reject"}
        first = service.decide("owner-a", body)
        replay = service.decide("owner-a", body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["proposal"]["state"], "rejected")
        snapshot = repository.load_owner("owner-a")
        self.assertIsNotNone(snapshot["receipts"][request_id]["request_digest"])

    def test_purge_is_idempotent_and_redacts_structured_and_recording_paths(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, catalog, _draft = _sql_service(simulator)
        created = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s1", "record_type": "skill",
                           "values": {"name": "Secret strength"}, "explicit_clears": []}],
                "text": "Secret typed words.",
            },
        )
        saved_key = created["saved_items"][0]["record_key"]
        catalog.put_item(
            "owner-a",
            {
                "record_key": saved_key,
                "record_type": "skill",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": {"name": "Secret strength", "summary": None},
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )
        source_key, structured_source_key = created["submission"]["source_keys"]
        body = {"request_id": str(uuid4()), "source_key": source_key}
        first = service.purge_source("owner-a", body)
        replay = service.purge_source("owner-a", body)
        service.purge_source(
            "owner-a", {"request_id": str(uuid4()), "source_key": structured_source_key}
        )
        self.assertEqual(first["outcome"], "purged")
        self.assertTrue(replay["replayed"])
        blob = json.dumps(repository.load_owner("owner-a"))
        self.assertNotIn("Secret typed words.", blob)
        self.assertNotIn("Secret strength", blob)
        self.assertIn(source_key, blob)  # structural provenance survives
        # Neither the browser workspace nor a same-key replay can recover it.
        workspace = json.dumps(service.get_workspace("owner-a"))
        self.assertNotIn("Secret typed words.", workspace)
        self.assertNotIn("Secret strength", workspace)
        replay_body = {
            "type": "add_submission",
            "request_id": created["request_id"],
            "items": [{"client_key": "s1", "record_type": "skill",
                       "values": {"name": "Secret strength"}, "explicit_clears": []}],
            "text": "Secret typed words.",
        }
        replayed = service.submit("owner-a", replay_body)
        self.assertTrue(replayed["replayed"])
        self.assertNotIn("Secret typed words.", json.dumps(replayed))
        # The accepted canonical fact survives source cleanup. Replay labels it
        # as current canonical state and does not pretend to recover the purged
        # structured source.
        self.assertEqual(replayed["saved_items"][0]["values"]["name"], "Secret strength")
        self.assertEqual(replayed["saved_items"][0]["values_source"], "current_canonical_at_replay")
        self.assertEqual(replayed["saved_items"][0]["first_response_comparison"], "source_unavailable")

        spoken = _sql_service(DeclaredIntakeSimulator(), transcriber=_RecordingStub("Secret spoken words."))
        spoken_service, spoken_repository, _c, _d = spoken
        recorded = spoken_service.transcribe_recording(
            "owner-a",
            _Upload(wav_bytes()),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0},
        )
        spoken_service.purge_source(
            "owner-a", {"request_id": str(uuid4()), "source_key": recorded["source_key"]}
        )
        spoken_blob = json.dumps(spoken_repository.load_owner("owner-a"))
        self.assertNotIn("Secret spoken words.", spoken_blob)

    def test_second_item_failure_leaves_nothing_and_retries_clean(self):
        simulator = DeclaredIntakeSimulator(fail_on_intent=1)
        service, repository, _catalog, _draft = _sql_service(simulator)
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [
                {"client_key": "s1", "record_type": "skill", "values": {"name": "First"}},
                {"client_key": "s2", "record_type": "skill", "values": {"name": "Second"}},
            ],
        }
        with self.assertRaises(Exception):
            service.submit("owner-a", body)
        snapshot = repository.load_owner("owner-a")
        self.assertEqual(snapshot["receipts"], {})
        self.assertEqual(snapshot["submissions"], {})
        self.assertEqual(snapshot["sources"], {})
        simulator.fail_on_intent = None
        retried = service.submit("owner-a", body)
        self.assertEqual(retried["summary"]["saved"], 2)
        self.assertEqual(retried["summary"]["unresolved"], 0)

    def test_partial_validation_results_are_not_persistence_failures(self):
        simulator = DeclaredIntakeSimulator()
        service, repository, _catalog, _draft = _sql_service(simulator)
        receipt = service.submit(
            "owner-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s1", "record_type": "skill",
                           "values": {"name": "MBSE"}}],
                "attachments": [{"client_key": "d1", "kind": "document",
                                 "declared_content_type": "application/zip",
                                 "filename": "bad.zip"}],
            },
            files={"d1": _Upload(b"PK\x03\x04nope", "application/zip")},
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertEqual(receipt["outcome"], "partial")
        self.assertEqual(len(repository.load_owner("owner-a")["submissions"]), 1)

    def test_receipt_failure_rolls_back_the_whole_transaction(self):
        simulator = DeclaredIntakeSimulator(fail_on_receipt=True)
        service, repository, _catalog, _draft = _sql_service(simulator)
        with self.assertRaises(Exception):
            service.submit(
                "owner-a",
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "items": [{"client_key": "s1", "record_type": "skill",
                               "values": {"name": "MBSE"}, "explicit_clears": []}],
                },
            )
        snapshot = repository.load_owner("owner-a")
        self.assertEqual(snapshot["receipts"], {})
        self.assertEqual(snapshot["submissions"], {})
        self.assertEqual(snapshot["sources"], {})
        self.assertEqual(simulator.intents, [])  # the canonical intent never survived


class _RecordingStub:
    def __init__(self, transcript="I led the migration."):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"content_type": content_type, "byte_length": len(audio_bytes)})
        return {"provider_transcript": self.transcript, "provider_request_id": "stub",
                "duration_seconds": 3.0}


class _Upload:
    def __init__(self, data, mimetype="audio/wav", filename="recording.wav"):
        import io

        self.mimetype = mimetype
        self.filename = filename
        self.stream = io.BytesIO(data)


if __name__ == "__main__":
    unittest.main()
