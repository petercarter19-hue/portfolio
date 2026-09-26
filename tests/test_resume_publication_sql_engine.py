"""Meaningful engine-adapter tests. Live DSN execution stays gated."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from services.resume_publication_adapters import (
    CAPTURE_ROLLBACK_GUARD_CASES,
    CLIENT_LOCK_INTENT,
    EngineProofError,
    MANDATORY_ENGINE_CASES,
    PROOF_CORRECTED_SUMMARY,
    PROOF_CATALOG_ASSET_ID,
    PROOF_BATCH_ENTRY_KEY,
    PROOF_ENTRY_KEY,
    PROOF_EDITOR_CONTROL_KEY,
    PROOF_EDITOR_INVALID_FIELDS,
    PROOF_FOREIGN_ENTRY_KEY,
    PROOF_ID,
    PROOF_PUBLIC_SLUG,
    PROOF_POPULATED_DATABASE,
    PROOF_RACE_SUMMARY,
    PROOF_SEED_SUMMARY,
    REQUIRED_PUBLICATION_CLOSURE_IDS,
    IsolatedDockerCliRuntime,
    _capture_owner_state,
    _commit_parameters,
    _expect_sql_permission_denial,
    acquire_isolated_sql_runtime,
    assert_application_principal_permissions,
    assert_executed_mandatory_cases,
    assert_race_pair_state,
    assert_reviewed_source,
    checkout_sha,
    classify_sql_commit_error,
    cleanup_owned_resources,
    connect_from_client_environment,
    execute_procedure,
    is_expected_populated_publication_rollback_refusal,
    prepare_hashed_wheelhouse,
    refuse_client_supplied_dsn,
    resolve_publication_migration_closure,
    run_codec_and_evidence,
    run_capture_rollback_contracts,
    run_sql_sequence_contracts,
    run_verifier_mutation_contracts,
    run_injected_rollback,
    run_migration_closure,
    run_publication_sql_oracles,
    run_two_connection_race,
    sanitize_proof_error,
    seed_publication_owner,
    source_manifest,
    verify_downloaded_wheelhouse,
)
from services.resume_publication_contracts import (
    encode_canonical_source,
    hash_canonical_source,
)


AUTHORIZED = (
    os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE", "").strip().lower()
    == "authorized"
)


def _correct_json(summary=PROOF_RACE_SUMMARY, content=1, access=2):
    return json.dumps(
        {
            "type": "correct",
            "entry_key": PROOF_ENTRY_KEY,
            "expected_content_version": content,
            "expected_access_revision": access,
            "values": {
                "summary": summary,
                "wording": summary,
                "role_title": "Lead",
                "employer_name": "PeerSlate",
            },
        }
    )


def _publish_json(digest="a" * 64, slug=PROOF_PUBLIC_SLUG):
    return json.dumps({"type": "publish", "reviewed_digest": digest, "slug": slug})


def _display_json(summary):
    return json.dumps({PROOF_ENTRY_KEY: {"wording": {"role_title": "Lead", "summary": summary}}})


def _display_from_store(store):
    display = {}
    if store.get("resume_display") and store.get("lifecycle") == "active":
        display[PROOF_ENTRY_KEY] = {"wording": {"role_title": "Lead", "summary": store.get("canonical_summary")}}
    extra = store.get("extra_policy") or {}
    if extra.get("resume_display") and extra.get("lifecycle") == "active":
        display[extra["entry_key"]] = {"wording": {"role_title": "Second role", "summary": extra.get("summary")}}
    return json.dumps(display)


class _EngineCursor:
    def __init__(self, connection):
        self.connection = connection
        self.statements = []
        self._rows = []
        self._one = None
        self.description = []

    def execute(self, statement, params=None):
        sql = statement if isinstance(statement, str) else str(statement)
        self.statements.append(sql)
        if "-- capture rollback metadata proof" in sql:
            # Protocol simulation only. Actual catalog and rollback evidence
            # must come from the independently authorized SQL job.
            self.description = [(key,) for key in ("capture_object_id", "index_id", "index_name",
                                                  "has_filter", "filter_definition", "self_dependency")]
            self._rows = [(123, 2, "IX_captures_owner_created", 1, "([deleted_at_utc] IS NULL)", 1)]
            return None
        if "-- capture rollback guard proof:" in sql:
            name = re.search(r"-- capture rollback guard proof:(\w+)", sql).group(1)
            expected = CAPTURE_ROLLBACK_GUARD_CASES[name]
            self.description = [(key,) for key in ("capture_guard_error", "fixture_applied",
                                                   "table_removed", "baseline_restored")]
            self._rows = [(expected, 1, int(expected == 0), 1)]
            return None
        if "-- capture rollback standalone state proof:" in sql:
            marker = re.search(r"-- capture rollback standalone state proof:(\w+)", sql).group(1)
            present = int(marker != "removed")
            self.description = [(key,) for key in ("capture_table", "create_proc", "list_proc",
                                                   "migration_record", "owned_index", "transaction_count")]
            self._rows = [(present, present, present, present, present, 0)]
            return None
        if sql.lstrip().startswith("/*") and "PS-CAPTURE-001" in sql[:200]:
            return None
        if "-- publication verifier mutation proof" in sql:
            # Protocol simulation only; real rejection is required by the
            # independently authorized SQL job, using these actual verifier files.
            match = re.search(r"THROW (52\d{3}), ''Publication wrapper", sql)
            expected = int(match.group(1)) if match else (54114 if
                "CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyAfterPolicyInternal AS RETURN;" in sql else 54113)
            self.description = [("probe_error",), ("mutation_applied",), ("module_restored",)]
            self._rows = [(expected, 1, 1)]
            return None
        if sql.lstrip().startswith("/*") and "DECLARE @PublicationInstalled bit" in sql:
            return None
        if sql.lstrip().startswith("/*") and "PS-RESUME-PUBLICATION-001" in sql[:180]:
            self.connection.store["publication_migration_applied"] = not sql.lstrip().startswith("/*\nRollback")
            return None
        if sql.startswith("GRANT EXECUTE ON dbo.[") and "Core] TO [peerslate_app]" in sql:
            self.connection.store.setdefault("predecessor_grants", set()).add(sql.split("[", 1)[1].split("]", 1)[0])
            return None
        if sql.startswith("SELECT HAS_PERMS_BY_NAME("):
            name = str(params[0]).split(".", 1)[-1] if params else ""
            key = name if name.endswith("Core") else name + "Core"
            granted = key in self.connection.store.get("predecessor_grants", set())
            denied = bool(self.connection.store.get("publication_migration_applied"))
            self._one = (1 if granted and not denied else 0,)
            return None
        if sql.startswith("INSERT dbo.resume_catalog_assets"):
            self.connection.store["catalog_lifecycle"] = "active"
            return None
        if sql.startswith("SELECT lifecycle FROM dbo.resume_catalog_assets"):
            state = self.connection.store.get("catalog_lifecycle")
            self._rows = [(state,)] if state else []
            self._one = self._rows[0] if self._rows else None
            return None
        if sql.startswith("SELECT d.draft_version FROM dbo.resume_drafts"):
            version = self.connection.store.get("draft_version")
            self._rows = [(version,)] if version is not None else []
            return None
        if sql == "SELECT COUNT(*) FROM dbo.entry_policy_records":
            store = self.connection.store
            self._one = ((1 if store.get("policy_present") else 0)
                         + (1 if store.get("extra_policy") else 0)
                         + len(store.get("foreign_policy_keys") or []),)
            return None
        if sql.startswith("SELECT COUNT_BIG(*) FROM dbo."):
            key = str(params[0]) if params else ""
            store = self.connection.store
            if "dbo.slate_entities" in sql:
                present = key in store.get("editor_probe_entities", set())
            elif "dbo.career_chapters" in sql:
                present = key in store.get("editor_probe_chapters", set())
            elif "dbo.living_resume_command_receipts" in sql:
                present = key in store.get("editor_probe_receipts", set())
            else:
                raise AssertionError(f"unexpected editor observation: {sql}")
            self._one = (int(present),)
            return None
        if sql.startswith(("GRANT EXECUTE", "DENY EXECUTE", "IF DATABASE_PRINCIPAL_ID")):
            return None
        if sql.startswith("EXECUTE AS USER = '"):
            self.connection.principal = sql.split("'", 2)[1]
            return None
        if sql == "REVERT":
            self.connection.principal = "dbo"
            return None
        if sql == "SELECT USER_NAME()":
            self._one = (self.connection.principal,)
            self.description = [("principal",)]
            return None
        if (self.connection.principal == "peerslate_app"
                and sql.lstrip().upper().startswith(("SELECT", "UPDATE", "DELETE", "INSERT"))
                and "dbo.entry_policy_records" in sql):
            raise RuntimeError("The SELECT or DML permission was denied on dbo.entry_policy_records. (229)")
        if sql.startswith("SELECT entry_key, lifecycle, access_revision FROM dbo.entry_policy_records"):
            key = params[0] if params else None
            self._rows = [(key, "active", 1)] if key in self.connection.store.get("foreign_policy_keys", []) else []
            return None
        if sql.startswith("SELECT policy.entry_key, policy.resume_display, policy.visitor_ai, policy.access_revision"):
            store = self.connection.store
            self._rows = []
            if params and params[0] == store.get("user_key"):
                if store.get("policy_present"):
                    self._rows.append((store["entry_key"], store["resume_display"],
                                       store["visitor_ai"], store["access_revision"]))
                extra = store.get("extra_policy")
                if extra:
                    self._rows.append((extra["entry_key"], extra["resume_display"],
                                       extra["visitor_ai"], extra["access_revision"]))
            self._rows.sort(key=lambda row: row[0])
            return None
        if "publication draft version token proof" in sql:
            self._rows = [("publication:proof-token", "[]")]
            self.description = [("base_publication_version",), ("command_receipts_json",)]
            self._pending_sets = []
            if "EXEC dbo.usp_GetResumeMediaDraftForOwner @UserKey = @Owner;" in sql:
                self._pending_sets.append(([("base_publication_version",), ("media_generation",)], [("publication:proof-token", 0)]))
            return None
        if "publication slug constraint proof" in sql:
            self._one = (2, 1, 2)
            self.description = [("before",), ("rejected",), ("restored",)]
            return None
        if "BEGIN TRANSACTION" in sql.upper() and "sp_set_session_context" not in sql:
            raise RuntimeError("Ambient transactions are not permitted.")
        if "sp_set_session_context" in sql:
            self.connection.fail_after_evidence = True
            return None
        if "usp_UpsertAppUserFromAuth" in sql:
            subject = "proof-owner-a"
            if params:
                for item in params:
                    if isinstance(item, str) and item.startswith("proof-owner"):
                        subject = item
                        break
            self.connection.store["owner_present"] = True
            if subject == "proof-owner-b":
                self.connection.store["second_owner"] = subject
            else:
                self.connection.store["user_key"] = subject
            self._rows = [(subject,)]
            self.description = [("user_key",)]
            return None
        if "usp_ListResumePublicationPolicyForOwner" in sql or "usp_ListEntryPolicyEntriesForOwner" in sql:
            store = self.connection.store
            owner = str(params[0]) if params else ""
            if owner != store.get("user_key"):
                self._rows = []
            else:
                self._rows = [(
                    store.get("entry_key"), "role", store.get("entry_key"), "experience", None,
                    store.get("content_version"), store.get("access_revision"),
                    store.get("resume_display"), store.get("visitor_ai"), 0,
                    store.get("lifecycle"), None,
                    json.dumps({"role_title": "Lead", "employer_name": "PeerSlate", "summary": store.get("canonical_summary")}),
                )]
                extra = store.get("extra_policy")
                if extra:
                    self._rows.append((
                        extra["entry_key"], "role", extra["entry_key"], "experience", None,
                        1, extra["access_revision"], extra["resume_display"], extra["visitor_ai"], 0,
                        extra["lifecycle"], None,
                        json.dumps({"role_title": "Second role", "employer_name": "PeerSlate", "summary": extra["summary"]}),
                    ))
            self.description = [(name,) for name in (
                "entry_key", "canonical_type", "canonical_key", "category", "parent_entry_key",
                "content_version", "access_revision", "resume_display", "visitor_ai",
                "private_assistance_excluded", "lifecycle", "recover_until_utc", "values_json",
            )]
            return None
        if "usp_CommitLivingResumeCommandForOwner" in sql:
            payload = self._payload(params)
            values = payload.get("values") or {}
            if payload.get("type") == "create_role":
                if (not values.get("role_title") or not values.get("employer_name")
                        or values.get("date_precision") not in {"day", "month", "year", "unknown"}
                        or not isinstance(values.get("current_role"), bool)):
                    raise RuntimeError("RESUME_EDITOR_VALIDATION")
                forbidden = set(values) - {
                    "role_title", "employer_name", "location_text", "summary",
                    "start_date", "end_date", "date_precision", "employment_type",
                    "current_role",
                }
                if forbidden and self.connection.enforce_editor_allowlist:
                    if self.connection.editor_reject_with_write:
                        self.connection.store.setdefault("editor_probe_entities", set()).add(payload["record_key"])
                        self.connection.store.setdefault("editor_probe_receipts", set()).add(payload["command_id"])
                    raise RuntimeError("RESUME_EDITOR_VALIDATION")
            if payload.get("record_key") in {PROOF_EDITOR_CONTROL_KEY, *(item[1] for item in PROOF_EDITOR_INVALID_FIELDS)}:
                self.connection.store.setdefault("editor_probe_entities", set()).add(payload["record_key"])
                self.connection.store.setdefault("editor_probe_chapters", set()).add(payload["record_key"])
                self.connection.store.setdefault("editor_probe_receipts", set()).add(payload["command_id"])
                self._rows = []
                self.description = []
                return None
            if params and str(params[0]) == self.connection.store.get("second_owner"):
                self.connection.store["foreign_entry_key"] = payload.get("record_key")
                self._rows = []
                self.description = []
                return None
            if payload.get("record_key") == PROOF_BATCH_ENTRY_KEY:
                self.connection.store["extra_summary"] = values.get("summary")
                self._rows = []
                self.description = []
                return None
            self.connection.store["canonical_summary"] = values.get("summary") or PROOF_SEED_SUMMARY
            self.connection.store["approved_wording"] = values.get("summary") or PROOF_SEED_SUMMARY
            self.connection.store["entry_key"] = payload.get("record_key") or PROOF_ENTRY_KEY
            self._rows = []
            self.description = []
            return None
        if "usp_CommitEntryPolicyCommandForOwner" in sql:
            payload = self._payload(params)
            if params and str(params[0]) == self.connection.store.get("second_owner"):
                self.connection.store.setdefault("foreign_policy_keys", []).append(payload.get("entry_key"))
                self.connection.store["foreign_policy_key"] = payload.get("entry_key")
                self._rows = []
                self.description = []
                return None
            store = self.connection.store
            command_type = payload.get("type")
            if command_type in {"edit", "change_permissions"}:
                self._apply_commit((params[0], params[1], json.dumps(payload)))
                store.setdefault("policy_commands", []).append((command_type, self.connection.principal))
                return None
            else:
                if payload.get("entry_key") == PROOF_BATCH_ENTRY_KEY:
                    self.connection.store["extra_policy"] = {
                        "entry_key": PROOF_BATCH_ENTRY_KEY, "summary": self.connection.store.get("extra_summary"),
                        "resume_display": 0, "visitor_ai": 0, "access_revision": 1, "lifecycle": "active",
                    }
                else:
                    self.connection.store["policy_present"] = True
                    self.connection.store["lifecycle"] = "active"
                    self.connection.store["content_version"] = 1
                    self.connection.store["access_revision"] = 1
                    self.connection.store["entry_key"] = payload.get("entry_key") or PROOF_ENTRY_KEY
                    self.connection.store["canonical_type"] = payload.get("canonical_type") or "role"
            self._rows = [(1, 0, "applied", "a" * 64)]
            self.description = [("committed",), ("replayed",), ("outcome",), ("request_digest",)]
            store.setdefault("policy_commands", []).append((command_type, self.connection.principal))
            return None
        if "usp_ResumePublicationApplyCanonicalInternal" in sql:
            raise RuntimeError("permission denied")
        if "usp_GetResumePublicationReceiptForOwner" in sql:
            request_id = str(params[1]) if params and len(params) >= 2 else ""
            rec = (self.connection.store.get("receipt_index") or {}).get(request_id)
            if rec:
                self._rows = [
                    (
                        rec.get("request_digest"),
                        rec.get("request_id"),
                        rec.get("type"),
                        rec.get("outcome"),
                        rec.get("publication_revision"),
                    )
                ]
                self.description = [
                    ("request_digest",),
                    ("request_id",),
                    ("command_type",),
                    ("outcome",),
                    ("publication_revision",),
                ]
            else:
                self._rows = []
                self.description = [("request_digest",)]
            return None
        if "usp_GetResumePublicationForOwner" in sql:
            store = self.connection.store
            self._rows = [
                (
                    store.get("display_json"),
                    store.get("media_json"),
                    store.get("publication_revision"),
                    store.get("sharing_enabled"),
                )
            ]
            self.description = [
                ("display_json",),
                ("media_json",),
                ("publication_revision",),
                ("sharing_enabled",),
            ]
            return None
        if "usp_GetPublicResumePublicationBySlug" in sql:
            store = self.connection.store
            if not store.get("sharing_enabled"):
                raise RuntimeError("54030 Publication is unavailable.")
            self._rows = [
                (
                    store.get("publication_revision"),
                    store.get("reviewed_digest") or "a" * 64,
                    store.get("display_json"),
                    store.get("media_json") or "{}",
                )
            ]
            self.description = [
                ("publication_revision",),
                ("reviewed_digest",),
                ("display_json",),
                ("media_json",),
            ]
            return None
        if "usp_GetResumePublicationMediaAuthorization" in sql:
            media = json.loads(self.connection.store.get("media_json") or "{}")
            slot = str(params[1]) if params and len(params) > 1 else "portrait"
            item = media.get(slot) or {}
            if not self.connection.store.get("sharing_enabled") or not item.get("active"):
                raise RuntimeError("54033 Media is unavailable.")
            if item.get("source_kind") == "generated_illustration" and self.connection.store.get("catalog_lifecycle") != "active":
                raise RuntimeError("54034 Media is unavailable.")
            self._rows = [(1, slot, 1, item.get("content_sha256"), item.get("source_kind"))]
            self.description = [("authorized",), ("slot",), ("rechecked",), ("content_sha256",), ("source_kind",)]
            return None
        if "usp_CommitResumePublicationCommandForOwner" in sql:
            if getattr(self.connection, "principal", "peerslate_app") == "peerslate_restricted":
                raise RuntimeError("permission denied")
            if self.connection.fail_after_evidence:
                self.connection.evidence_written = True
                raise RuntimeError("54999 PROOF_INJECTED_FAILURE")
            self._apply_commit(params)
            return None
        if "usp_CommitResumeDraftCommandForOwner" in sql:
            payload = self._payload(params)
            store = self.connection.store
            if payload.get("type") != "save_item":
                raise RuntimeError("52204 RESUME_DRAFT_VALIDATION")
            if int(payload.get("expected_draft_version", -1)) != int(store.get("draft_version") or 0):
                self._rows = [(0, 0, "stale_draft")]
            else:
                store["draft_version"] = int(store.get("draft_version") or 0) + 1
                store["draft_summary"] = payload.get("values", {}).get("summary")
                self._rows = [(1, 0, "saved")]
            self.description = [("committed",), ("replayed",), ("outcome",)]
            return None
        if "FROM dbo.career_chapters" in sql:
            store = self.connection.store
            self._rows = [
                (
                    store.get("canonical_summary"),
                    store.get("approved_wording"),
                    store.get("resume_display"),
                    store.get("visitor_ai"),
                    store.get("content_version"),
                    store.get("access_revision"),
                    store.get("lifecycle"),
                )
            ]
            self.description = [
                ("summary",),
                ("approved_wording",),
                ("resume_display",),
                ("visitor_ai",),
                ("content_version",),
                ("access_revision",),
                ("lifecycle",),
            ]
            return None
        if "display_json" in sql:
            store = self.connection.store
            self._rows = [
                (
                    store.get("display_json"),
                    store.get("visitor_ai_json"),
                    store.get("publication_revision"),
                    store.get("media_json"),
                )
            ]
            self.description = [("display_json",), ("visitor_ai_json",), ("publication_revision",), ("media_json",)]
            return None
        if "FROM dbo.resume_publication_outbox" in sql:
            self._rows = list(self.connection.store.get("outbox") or [])
            self.description = [("outbox_id",), ("event_type",), ("publication_revision",)]
            return None
        if "command_receipt_id" in sql:
            self._rows = list(self.connection.store.get("receipts") or [])
            self.description = [("command_receipt_id",), ("request_id",), ("command_type",), ("outcome")]
            return None
        if "FROM dbo.app_users AS u JOIN dbo.member_profiles" in sql:
            self._one = (1 if params and params[0] == self.connection.store.get("second_owner") else 0,)
            self.description = [("count",)]
            return None
        if "FROM dbo.entry_policy_records AS policy JOIN dbo.member_profiles" in sql:
            store = self.connection.store
            owner = params[0] if params else None
            if "policy.entry_key = ?" in sql:
                count = 1 if owner == store.get("second_owner") and params[1] in (store.get("foreign_policy_keys") or []) else 0
            elif owner == store.get("second_owner"):
                count = len(store.get("foreign_policy_keys") or [])
            elif owner == store.get("user_key"):
                count = (1 if store.get("policy_present") else 0) + (1 if store.get("extra_policy") else 0)
            else:
                count = 0
            self._one = (count,)
            self.description = [("count",)]
            return None
        if "FROM dbo.app_users" in sql:
            self._rows = [(1 if self.connection.store.get("owner_present") else 0,)]
            self.description = [("count",)]
            return None
        if "FROM dbo.member_profiles" in sql:
            self._rows = [(1 if self.connection.store.get("owner_present") else 0,)]
            self.description = [("count",)]
            return None
        if "FROM dbo.resume_sharing_state" in sql:
            store = self.connection.store
            self._rows = [
                (
                    store["sharing_enabled"],
                    store["sharing_epoch"],
                    store["publication_revision"],
                    store["current_revision"],
                    store.get("public_slug"),
                )
            ]
            self.description = [
                ("sharing_enabled",),
                ("sharing_epoch",),
                ("publication_revision",),
                ("current_revision",),
                ("public_slug",),
            ]
            return None
        if "FROM dbo.resume_publication_receipts" in sql:
            self._rows = [(self.connection.store["receipt_count"],)]
            self.description = [("count",)]
            return None
        if "FROM dbo.resume_publication_revisions" in sql:
            self._rows = [(self.connection.store["revision_count"],)]
            self.description = [("count",)]
            return None
        if "publication codec rejection proof" in sql:
            pairs = json.loads(params[0], object_pairs_hook=list)
            keys = [key for key, _value in pairs]
            invalid_key = len(keys) != len(set(keys)) or any(key not in {"summary", "current_role"} for key in keys)
            self._one = (54012 if invalid_key else 54013,)
            self.description = [("error_number",)]
            return None
        if "usp_ResumePublicationEncodeSourceInternal" in sql:
            payload_json = None
            if params:
                payload_json = params[0] if not isinstance(params, dict) else None
            fields = json.loads(payload_json) if payload_json else self.connection.codec_fields
            payload = encode_canonical_source(fields)
            self._one = (payload, hash_canonical_source(payload))
            self.description = [("content_bytes",), ("content_sha256",)]
            return None
        if "sys.database_permissions" in sql:
            from scripts.configure_resume_publication_sql_authority import PROPOSED_PROCEDURES

            self._rows = [("EXECUTE", "DENY", "usp_ResumePublicationEncodeSourceInternal")]
            self._rows.extend(("EXECUTE", "GRANT", name) for name in PROPOSED_PROCEDURES)
            return None
        self._rows = []
        self._one = None
        return None

    def _payload(self, params):
        command_json = "{}"
        if params:
            for item in reversed(list(params)):
                if isinstance(item, str) and item.startswith("{"):
                    command_json = item
                    break
        if isinstance(command_json, dict):
            return command_json
        try:
            return json.loads(command_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    def _apply_commit(self, params):
        payload = self._payload(params)
        command_type = payload.get("type")
        request_id = ""
        user_key = ""
        command_json = "{}"
        if params:
            values = list(params)
            if values:
                user_key = str(values[0] or "")
            if len(values) >= 2:
                request_id = str(values[1] or "")
            if len(values) >= 3:
                command_json = values[2] if isinstance(values[2], str) else json.dumps(values[2], separators=(",", ":"))
        digest = hashlib.sha256(str(command_json).encode("utf-8")).hexdigest()
        with _EngineConnection._store_lock:
            store = self.connection.store
            if user_key == store.get("second_owner") and payload.get("entry_key") == store.get("entry_key"):
                raise RuntimeError("54026 Entry is unavailable.")
            if store.get("user_key") and user_key and user_key != store.get("user_key"):
                raise RuntimeError("54021 Owner is unavailable.")
            index = store.setdefault("receipt_index", {})
            existing = index.get(request_id)
            if existing is not None:
                if existing.get("request_digest") != digest:
                    raise RuntimeError("54022 That request already used a different payload.")
                self._rows = [
                    (
                        1,
                        1,
                        existing.get("outcome"),
                        existing.get("request_digest"),
                        "current",
                        store.get("publication_revision"),
                    )
                ]
                self.description = [
                    ("committed",),
                    ("replayed",),
                    ("outcome",),
                    ("request_digest",),
                    ("read_state",),
                    ("publication_revision",),
                ]
                return
            expected_publication = payload.get("expected_publication_revision")
            if expected_publication is not None and int(expected_publication) != int(store.get("publication_revision") or 0):
                raise RuntimeError("54023 The publication changed.")
            if command_type in {"correct", "edit"}:
                entry = payload.get("entry_key")
                if not entry:
                    raise RuntimeError("54026 Entry is unavailable.")
                if payload.get("expected_content_version") is None or payload.get("expected_access_revision") is None:
                    raise RuntimeError("54027 Expected content and access versions are required.")
                if entry != store.get("entry_key"):
                    raise RuntimeError("54026 Entry is unavailable.")
                if store.get("lifecycle") not in (None, "active"):
                    raise RuntimeError("54028 Entry is not active.")
                if not store.get("canonical_summary"):
                    raise RuntimeError("54026 Canonical source is unavailable.")
                if int(payload["expected_content_version"]) != int(store.get("content_version") or 0) or int(
                    payload["expected_access_revision"]
                ) != int(store.get("access_revision") or 0):
                    raise RuntimeError("54023 The publication changed.")
                values = payload.get("values") or {}
                new_summary = values.get("summary")
                submitted_wording = values.get("wording")
                displayed = store.get("approved_wording") or store.get("canonical_summary")
                if new_summary is not None and new_summary != displayed:
                    next_wording = new_summary
                elif submitted_wording is not None and submitted_wording != displayed:
                    next_wording = submitted_wording
                else:
                    next_wording = new_summary if new_summary is not None else submitted_wording
                    if next_wording is None:
                        next_wording = store.get("canonical_summary")
                store["canonical_summary"] = next_wording
                store["approved_wording"] = next_wording
                store["content_version"] = int(store.get("content_version") or 1) + 1
                store["publication_revision"] = int(store["publication_revision"] or 0) + 1
                store["current_revision"] = store["publication_revision"]
                store["revision_count"] = int(store["revision_count"] or 0) + 1
                store["display_json"] = _display_json(next_wording)
                store["visitor_ai_json"] = json.dumps({"summary": next_wording})
                store["outbox_id"] = int(store.get("outbox_id") or 0) + 1
                store.setdefault("outbox", []).append(
                    (store["outbox_id"], "correct", store["publication_revision"])
                )
            elif command_type == "publish":
                store["sharing_enabled"] = 1
                store["sharing_epoch"] = int(store["sharing_epoch"] or 0) + 1
                store["publication_revision"] = int(store["publication_revision"] or 0) + 1
                store["current_revision"] = store["publication_revision"]
                store["revision_count"] = int(store["revision_count"] or 0) + 1
                store["public_slug"] = payload.get("slug") or PROOF_PUBLIC_SLUG
                store["reviewed_digest"] = payload.get("reviewed_digest") or "a" * 64
                summary = store.get("canonical_summary") or PROOF_SEED_SUMMARY
                store["display_json"] = _display_from_store(store)
                store["visitor_ai_json"] = json.dumps({"summary": summary})
                store["media_json"] = json.dumps(payload.get("media") or {})
                store["outbox_id"] = int(store.get("outbox_id") or 0) + 1
                store.setdefault("outbox", []).append(
                    (store["outbox_id"], "publish", store["publication_revision"])
                )
            elif command_type == "sharing_off":
                store["sharing_enabled"] = 0
                store["sharing_epoch"] = int(store["sharing_epoch"] or 0) + 1
                store["outbox_id"] = int(store.get("outbox_id") or 0) + 1
                store.setdefault("outbox", []).append(
                    (store["outbox_id"], "sharing_off", store["publication_revision"])
                )
            elif command_type == "change_permissions":
                targets = payload.get("targets") or [{
                    "entry_key": payload.get("entry_key"),
                    "expected_access_revision": payload.get("expected_access_revision"),
                    "permissions": payload.get("permissions") or {},
                }]
                seen = set()
                for target in targets:
                    key = target.get("entry_key")
                    if key in seen:
                        raise RuntimeError("54061 Invalid permission targets.")
                    seen.add(key)
                    policy = store if key == store.get("entry_key") else store.get("extra_policy")
                    if policy is None or (key != store.get("entry_key") and key != policy.get("entry_key")):
                        raise RuntimeError("54014 ENTRY_POLICY_CHANGED")
                    if int(target.get("expected_access_revision") or 0) != int(policy.get("access_revision") or 0):
                        raise RuntimeError("54014 ENTRY_POLICY_CHANGED")
                for target in targets:
                    key = target["entry_key"]
                    policy = store if key == store.get("entry_key") else store["extra_policy"]
                    permissions = target["permissions"]
                    for field in ("resume_display", "visitor_ai"):
                        if field in permissions:
                            policy[field] = 1 if permissions[field] else 0
                    policy["access_revision"] = int(policy.get("access_revision") or 1) + 1
                if store.get("publication_revision"):
                    store["publication_revision"] = int(store["publication_revision"]) + 1
                    store["current_revision"] = store["publication_revision"]
                    summary = store.get("canonical_summary")
                    store["display_json"] = _display_from_store(store)
                    store["visitor_ai_json"] = json.dumps({"summary": summary}) if store["visitor_ai"] else "{}"
            elif command_type == "delete":
                store["lifecycle"] = "deleted"
                store["resume_display"] = 0
                store["visitor_ai"] = 0
                store["access_revision"] = int(store.get("access_revision") or 1) + 1
                store["publication_revision"] = int(store.get("publication_revision") or 0) + 1
                store["current_revision"] = store["publication_revision"]
                store["display_json"] = "{}"
            elif command_type == "restore":
                if int(payload.get("expected_access_revision") or 0) != int(store.get("access_revision") or 0):
                    raise RuntimeError("52105 ENTRY_POLICY_CHANGED")
                store["lifecycle"] = "active"
                store["resume_display"] = 0
                store["visitor_ai"] = 0
                store["access_revision"] = int(store.get("access_revision") or 1) + 1
                store["display_json"] = "{}"
            elif command_type == "draft_change":
                store["draft_summary"] = (payload.get("values") or {}).get("summary")
            elif command_type == "media_restrict":
                store["media_active"] = 0
                media = json.loads(store.get("media_json") or "{}")
                if "portrait" in media:
                    media["portrait"]["active"] = False
                store["media_json"] = json.dumps(media)
                store["publication_revision"] = int(store.get("publication_revision") or 0) + 1
                store["current_revision"] = store["publication_revision"]
            elif command_type == "catalog_withdraw":
                if store.get("catalog_lifecycle") != "active":
                    raise RuntimeError("53110 Catalog asset is unavailable.")
                store["catalog_lifecycle"] = "withdrawn"
                store["publication_revision"] = int(store.get("publication_revision") or 0) + 1
                store["current_revision"] = store["publication_revision"]
            if command_type in {"delete", "restore", "change_permissions", "media_restrict", "catalog_withdraw"}:
                store["outbox_id"] = int(store.get("outbox_id") or 0) + 1
                store.setdefault("outbox", []).append((store["outbox_id"], command_type, store.get("publication_revision")))
            store["receipt_id"] = int(store.get("receipt_id") or 0) + 1
            store["receipt_count"] = int(store["receipt_count"] or 0) + 1
            receipt = {
                "request_id": request_id or payload.get("request_id"),
                "request_digest": digest,
                "type": command_type,
                "outcome": {"publish": "published", "correct": "corrected", "edit": "corrected"}.get(command_type, "applied"),
                "publication_revision": store.get("publication_revision"),
            }
            store.setdefault("receipts", []).append(
                (store["receipt_id"], receipt["request_id"], command_type, receipt["outcome"])
            )
            if receipt["request_id"]:
                index[str(receipt["request_id"])] = receipt
            self._rows = [
                (
                    1,
                    0,
                    receipt["outcome"],
                    digest,
                    "current",
                    store.get("publication_revision"),
                )
            ]
            self.description = [
                ("committed",),
                ("replayed",),
                ("outcome",),
                ("request_digest",),
                ("read_state",),
                ("publication_revision",),
            ]

    def nextset(self):
        if getattr(self, "_pending_sets", None):
            self.description, self._rows = self._pending_sets.pop(0)
            return True
        return False

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._one

    def close(self):
        return None

class _EngineConnection:
    _stores: dict[str, dict] = {}
    _store_lock = threading.Lock()
    enforce_editor_allowlist = True
    editor_reject_with_write = False

    @classmethod
    def reset(cls):
        with cls._store_lock:
            cls._stores.clear()

    def __init__(self, identity, codec_fields=None):
        self.identity = identity
        self.fail_after_evidence = False
        self.evidence_written = False
        self.principal = "dbo"
        with self._store_lock:
            self.store = self._stores.setdefault(
                identity,
                {
                    "sharing_enabled": 0,
                    "sharing_epoch": 0,
                    "publication_revision": 0,
                    "current_revision": None,
                    "receipt_count": 0,
                    "revision_count": 0,
                    "public_slug": None,
                    "canonical_summary": None,
                    "approved_wording": None,
                    "resume_display": 0,
                    "visitor_ai": 0,
                    "content_version": None,
                    "access_revision": None,
                    "lifecycle": None,
                    "entry_key": None,
                    "media_json": None,
                    "reviewed_digest": None,
                    "receipt_index": {},
                    "display_json": None,
                    "visitor_ai_json": None,
                    "owner_present": False,
                    "user_key": None,
                    "policy_present": False,
                    "receipts": [],
                    "outbox": [],
                    "outbox_id": 0,
                    "receipt_id": 0,
                },
            )
        self.codec_fields = codec_fields or {
            "canonical_type": "education",
            "role_title": None,
            "employer_name": None,
            "location_text": None,
            "summary": "Studied computing.",
            "start_date": None,
            "end_date": None,
            "date_precision": None,
            "employment_type": None,
            "current_role": None,
            "title": None,
            "institution_name": "State University",
            "degree_name": "B.S.",
            "field_of_study": "Computing",
            "education_status": "completed",
            "grade_text": None,
            "credential_name": None,
            "issuer_name": None,
            "credential_identifier": None,
            "issue_date": None,
            "expiration_date": None,
            "name": None,
            "skill_summary": None,
            "wording": None,
            "metric_value": None,
            "metric_label": None,
            "accomplishment_to_achievement": None,
            "parent_canonical_type": None,
        }

    def cursor(self):
        return _EngineCursor(self)

    def close(self):
        return None

    def commit(self):
        return None


def _simulated_capture_forward(identity):
    return {"capture_rollback": run_capture_rollback_contracts(_EngineConnection(identity))}


class ResumePublicationSqlEngineContractTests(unittest.TestCase):
    def test_direct_sql_denial_accepts_numberless_sql_server_wording_only(self):
        def reject(message):
            raise RuntimeError(message)

        for message in (
            "permission denied",
            "The SELECT permission was denied on the object entry_policy_records.",
            "The UPDATE permission was denied on the object entry_policy_records.",
            "The DELETE permission was denied on the object entry_policy_records.",
            "SQL Server error (229)",
        ):
            with self.subTest(message=message):
                _expect_sql_permission_denial(lambda: reject(message))
        with self.assertRaisesRegex(EngineProofError, "proof_unexpected_principal_error:RuntimeError: deadlock"):
            _expect_sql_permission_denial(lambda: reject("deadlock"))
        with self.assertRaisesRegex(EngineProofError, "proof_principal_allowed"):
            _expect_sql_permission_denial(lambda: None)

    def test_populated_rollback_refusal_requires_the_publication_guard(self):
        self.assertTrue(is_expected_populated_publication_rollback_refusal(
            RuntimeError("SQL Server error 54120")))
        exact = (
            "migration_phase_rollback_migration_PS-RESUME-PUBLICATION-001_batch_1_failed: "
            "migration_file_PS-RESUME-PUBLICATION-001_publication_rollback.sql_failed: "
            "[SQL Server]Rollback refused: publication state is populated."
        )
        self.assertTrue(is_expected_populated_publication_rollback_refusal(RuntimeError(exact)))
        self.assertFalse(is_expected_populated_publication_rollback_refusal(
            RuntimeError(exact.replace("PS-RESUME-PUBLICATION-001_batch_1", "PS-RESUME-MEDIA-001_batch_1"))))
        self.assertFalse(is_expected_populated_publication_rollback_refusal(
            RuntimeError(exact.replace("publication_rollback.sql", "resume_media_rollback.sql"))))
        self.assertFalse(is_expected_populated_publication_rollback_refusal(
            RuntimeError(exact.replace("publication state is populated", "predecessor permissions are unavailable"))))

    def test_engine_oracle_refuses_missing_capture_rollback_evidence(self):
        with self.assertRaisesRegex(EngineProofError, "capture_rollback_guard_evidence_missing"):
            run_publication_sql_oracles(
                "docker:capture-evidence-missing", _EngineConnection,
                apply_forward=lambda identity: None, apply_rollback=lambda identity: None,
                verify=lambda identity: None,
                ordered_ids=[item["id"] for item in resolve_publication_migration_closure()],
            )

    def test_capture_rollback_requires_observed_metadata_guard_and_restoration(self):
        result = run_capture_rollback_contracts(_EngineConnection("docker:capture-probes"))
        self.assertEqual(result["cases"], {name: "pass" for name in CAPTURE_ROLLBACK_GUARD_CASES})
        mutations = [
            ("metadata", []),
            ("metadata", [(123, 2, "IX_captures_owner_created", 1, "([deleted_at_utc] IS NULL)", 0)]),
            ("metadata", [(123, 2, "IX_captures_owner_created", 1, "([active]=(1))", 1)]),
        ]
        for name, expected in CAPTURE_ROLLBACK_GUARD_CASES.items():
            if name == "own_index":
                continue
            valid = (expected, 1, int(expected == 0), 1)
            for column, wrong in ((0, 99999), (1, 0), (2, int(expected != 0)), (3, 0)):
                row = list(valid)
                row[column] = wrong
                mutations.append((name, [tuple(row)]))
        for target, rows in mutations:
            with self.subTest(target=target, rows=rows):
                class FaultyConnection(_EngineConnection):
                    def cursor(self):
                        cursor = super().cursor()
                        execute = cursor.execute
                        def faulty(sql, params=None):
                            execute(sql, params)
                            marker = ("-- capture rollback metadata proof" if target == "metadata"
                                      else f"-- capture rollback guard proof:{target}")
                            if marker in sql:
                                cursor._rows = rows
                        cursor.execute = faulty
                        return cursor
                with self.assertRaisesRegex(EngineProofError, "capture_(owned_filter|rollback_guard)"):
                    run_capture_rollback_contracts(FaultyConnection("docker:capture-fault"))

        for marker, field in (("removed", 0), ("reapplied", 4)):
            with self.subTest(marker=marker):
                class FaultyConnection(_EngineConnection):
                    def cursor(self):
                        cursor = super().cursor()
                        execute = cursor.execute
                        def faulty(sql, params=None):
                            execute(sql, params)
                            if f"-- capture rollback standalone state proof:{marker}" in sql:
                                row = list(cursor._rows[0])
                                row[field] = int(not row[field])
                                cursor._rows = [tuple(row)]
                        cursor.execute = faulty
                        return cursor
                with self.assertRaisesRegex(EngineProofError, "capture_rollback_(owned_removal|reapply)_failed"):
                    run_capture_rollback_contracts(FaultyConnection("docker:capture-standalone-fault"))

    def test_capture_standalone_failure_retains_bounded_catalog_observations(self):
        class DiagnosticConnection(_EngineConnection):
            def cursor(self):
                cursor = super().cursor()
                execute = cursor.execute

                def with_catalog(sql, params=None):
                    if "SELECT TOP (17) dependency.referencing_id" in sql:
                        cursor.description = [(name,) for name in (
                            "referencing_id", "referencing_name", "referencing_type",
                            "parent_object_id", "referencing_minor_id", "referenced_minor_id",
                        )]
                        cursor._rows = [(124, "CK_captures_type", "C", 123, 0, 0)]
                        return None
                    if "SELECT TOP (17) index_id" in sql:
                        cursor.description = [(name,) for name in (
                            "index_id", "name", "is_primary_key", "is_unique_constraint", "has_filter",
                        )]
                        cursor._rows = [(2, "IX_captures_owner_created", 0, 0, 1)]
                        return None
                    if "SELECT TOP (17) statistic.stats_id" in sql:
                        cursor.description = [(name,) for name in (
                            "stats_id", "name", "user_created", "auto_created",
                            "has_filter", "index_backed",
                        )]
                        cursor._rows = [(2, "IX_captures_owner_created", 0, 0, 1, 1)]
                        return None
                    return execute(sql, params)

                cursor.execute = with_catalog
                return cursor

        with patch("services.resume_publication_adapters.apply_sql_file",
                   side_effect=EngineProofError("native guard 52022")):
            with self.assertRaisesRegex(EngineProofError, "capture_rollback_standalone_failed") as raised:
                run_capture_rollback_contracts(DiagnosticConnection("docker:capture-catalog"))
        detail = str(raised.exception)
        self.assertIn("native guard 52022", detail)
        self.assertIn("catalog_before=", detail)
        self.assertIn("catalog_after=", detail)
        self.assertIn("CK_captures_type", detail)
        self.assertIn("IX_captures_owner_created", detail)

    def test_verifier_probes_require_rejection_actual_mutation_and_complete_rollback(self):
        result = run_verifier_mutation_contracts(_EngineConnection("docker:verifier-probes"))
        self.assertEqual(result["count"], 31)
        self.assertEqual(len(set(result["rejected_and_restored"])), 31)
        for wrong in ((0, 1, 1), (99999, 1, 1), (52010, 0, 1), (52010, 1, 0)):
            with self.subTest(observation=wrong):
                class FaultyConnection(_EngineConnection):
                    def cursor(self):
                        cursor = super().cursor()
                        execute = cursor.execute
                        def faulty(sql, params=None):
                            execute(sql, params)
                            if "-- publication verifier mutation proof" in sql:
                                cursor._rows = [wrong]
                        cursor.execute = faulty
                        return cursor
                with self.assertRaisesRegex(EngineProofError, "verifier_mutation_contract_failed"):
                    run_verifier_mutation_contracts(FaultyConnection("docker:verifier-fault"))

    def test_verifier_definition_probes_alter_existing_modules(self):
        class RecordingConnection(_EngineConnection):
            def __init__(self, dsn):
                super().__init__(dsn)
                self.probes = []

            def cursor(self):
                cursor = super().cursor()
                execute = cursor.execute

                def record(sql, params=None):
                    if "-- publication verifier mutation proof" in sql:
                        self.probes.append(sql)
                    return execute(sql, params)

                cursor.execute = record
                return cursor

        connection = RecordingConnection("docker:verifier-definition-probes")
        run_verifier_mutation_contracts(connection)
        living = [sql for sql in connection.probes if
                  "Verifier probe call is missing." in sql and
                  "DECLARE @D nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N''dbo.usp_CommitLivingResumeCommandForOwner''))" in sql]
        media = [sql for sql in connection.probes if
                 "Verifier probe target is missing." in sql and
                 "usp_CommitResumeMediaCommandForOwnerCore" in sql]
        self.assertEqual(len(living), 4)
        self.assertEqual(len(media), 5)
        for sql, declared, actual in (
            *[(sql, "usp_CommitLivingResumeCommandForOwner",
               "usp_CommitLivingResumeCommandForOwner") for sql in living],
            *[(sql, "usp_CommitResumeMediaCommandForOwner",
               "usp_CommitResumeMediaCommandForOwnerCore") for sql in media],
        ):
            self.assertIn(f"@DeclaredName nvarchar(128)=N''{declared}''", sql)
            self.assertIn(f"ALTER PROCEDURE dbo.{actual}", sql)
            self.assertIn("@NamePosition>256", sql)
            self.assertIn("CHARINDEX(N''PROC'', @Prefix)=0", sql)
            self.assertIn("Verifier probe declaration missing; name_pos=", sql)
            self.assertIn("SUBSTRING(@D, @SuffixStart, LEN(@D))", sql)

    def setUp(self):
        _EngineConnection.reset()

    def _protocol_runtime(self, *, fail_create=None, unavailable_after_remove=False,
                          unrelated_id_error_after_remove=False):
        from services.resume_publication_adapters import (
            PROOF_CLIENT_IMAGE_NAME, PROOF_NETWORK, PROOF_SQL_CONTAINER,
        )

        resources = {}
        removed = set()
        removed_ids = set()
        calls = []

        def completed(args, code=0, stdout="", stderr=""):
            return subprocess.CompletedProcess(args, code, stdout=stdout, stderr=stderr)

        def runner(args, **_kwargs):
            cmd = args[1:]
            calls.append(cmd)
            if cmd[:3] == ["exec", "ps-mvp1-ef-sql-proof-20260916-01-client", "python"]:
                return completed(args, stdout=json.dumps({"python": "3.12.0", "libc": ["glibc", "2.36"],
                                                          "mssql_python": "1.0.0"}) + "\n")
            if cmd[:3] == ["exec", "ps-mvp1-ef-sql-proof-20260916-01-client", "dpkg-query"]:
                return completed(args, stdout="libltdl7=2.4\nlibkrb5-3=1.20\nlibgssapi-krb5-2=1.20\n")
            if cmd[:2] == ["network", "create"] or cmd[:2] == ["run", "-d"]:
                name = cmd[-1] if cmd[0] == "network" else cmd[cmd.index("--name") + 1]
                marker = cmd[cmd.index("--label") + 1].split("=", 1)[1]
                kind = "network" if cmd[0] == "network" else "container"
                resource_id = "net-1" if kind == "network" else ("sql-1" if name == PROOF_SQL_CONTAINER else "client-1")
                resources[name] = {"id": resource_id, "marker": marker, "kind": kind}
                if fail_create == ("network" if kind == "network" else "sql" if name == PROOF_SQL_CONTAINER else "client"):
                    raise subprocess.TimeoutExpired(args, 1)
                return completed(args, stdout=resource_id + "\n")
            if "inspect" in cmd:
                name = cmd[-1]
                prefix = cmd[:2]
                current = resources.get(name) or next(
                    (value for value in resources.values() if value["id"] == name), None
                )
                if current is None:
                    if unrelated_id_error_after_remove and name in removed_ids:
                        return completed(args, 1, stderr="Error response from daemon: plugin not found")
                    if unavailable_after_remove and name in removed:
                        return completed(args, 1, stderr="Cannot connect to the Docker daemon")
                    missing = (f"network {name} not found" if prefix == ["network", "inspect"]
                               else f"No such image: {name}" if prefix == ["image", "inspect"]
                               else f"No such object: {name}")
                    return completed(args, 1, stderr=missing)
                expected_prefix = (["network", "inspect"] if current["kind"] == "network"
                                   else ["image", "inspect"] if current["kind"] == "image"
                                   else ["container", "inspect"])
                if prefix != expected_prefix:
                    return completed(args, 1, stderr="wrong Docker resource kind")
                template = cmd[cmd.index("--format") + 1]
                if template == "{{.Id}}":
                    return completed(args, stdout=current["id"] + "\n")
                expected_labels = ".Labels" if current["kind"] == "network" else ".Config.Labels"
                if expected_labels not in template:
                    return completed(args, 1, stderr="can't evaluate field Config in type network")
                return completed(args, stdout=current["marker"] + "\n")
            if cmd[:2] == ["network", "rm"] or cmd[:2] == ["rm", "-f"] or cmd[:2] == ["rmi", "-f"]:
                target = cmd[-1]
                name = next((item for item, value in resources.items() if item == target or value["id"] == target), None)
                if name is None:
                    return completed(args, 1, stderr="No such object")
                removed.add(name)
                removed_ids.add(resources[name]["id"])
                del resources[name]
                return completed(args, stdout=target + "\n")
            raise AssertionError(f"unexpected intercepted Docker command: {cmd}")

        class ProtocolRuntime(IsolatedDockerCliRuntime):
            def verify_downloaded_wheelhouse(self, _wheelhouse):
                return {"downloaded_bytes_independently_verified": True, "artifact_count": 1, "source": "downloaded_bytes"}

            def build_client_image(self, _root, _wheelhouse, _manifest):
                image_id = "sha256:" + "a" * 64
                resources[PROOF_CLIENT_IMAGE_NAME] = {"id": image_id, "marker": self.invocation_marker, "kind": "image"}
                return {"id": image_id, "marker": self.invocation_marker}

            def wait_for_sql(self, _name):
                return None

            def verify_copied_client_source(self, _container, manifest):
                return manifest

            def verify_sql_identity(self, _sql):
                return {"production_connection": False, "sql_build": "16.0.4265.3", "database": "PeerSlateMvp1EFEmpty_20260916_01"}

            def verify_isolation(self):
                return {"internal": True, "host_ports": False, "host_mounts": False}

            def ensure_databases(self, _names):
                return None

        return ProtocolRuntime(runner=runner), resources, calls

    def test_lock_intent_and_adapter_surface_exist(self):
        self.assertEqual(len(CLIENT_LOCK_INTENT), 64)
        self.assertTrue(callable(run_two_connection_race))
        self.assertTrue(callable(run_injected_rollback))
        self.assertTrue(callable(assert_application_principal_permissions))
        self.assertTrue(callable(run_migration_closure))
        self.assertTrue(callable(run_codec_and_evidence))

    def test_client_dsn_is_not_the_resource_identity(self):
        with self.assertRaisesRegex(EngineProofError, "client_dsn_forbidden"):
            refuse_client_supplied_dsn("Driver={ODBC};Server=127.0.0.1;Database=does_not_authorize;")
        with self.assertRaisesRegex(EngineProofError, "client_dsn_forbidden"):
            run_two_connection_race(
                "Driver={ODBC};Server=127.0.0.1;",
                "owner-a",
                "owner-b",
                {"request_id": "11111111-1111-4111-8111-111111111111", "json": "{}"},
                {"request_id": "22222222-2222-4222-8222-222222222222", "json": "{}"},
                connect=lambda _identity: _EngineConnection(_identity),
            )

    def test_two_connection_race_requires_barrier_interleaving(self):
        identities = []

        def connect(identity):
            identities.append(identity)
            return _EngineConnection(identity)

        result = run_two_connection_race(
            "docker:ps-mvp1-ef-sql-proof-20260916-01-sql",
            "owner-a",
            "owner-b",
            {"request_id": "11111111-1111-4111-8111-111111111111", "json": '{"type":"sharing_off"}'},
            {"request_id": "22222222-2222-4222-8222-222222222222", "json": '{"type":"sharing_off"}'},
            connect=connect,
        )
        self.assertEqual(identities, ["docker:ps-mvp1-ef-sql-proof-20260916-01-sql"] * 2)
        self.assertTrue(result["interleaved"])
        self.assertTrue(result["barrier"])
        self.assertEqual(result["outcomes"], ("committed", "committed"))

    def _seed_publish(self, identity, owner="owner-a"):
        connection = _EngineConnection(identity)
        connection.store["owner_present"] = True
        connection.store["canonical_summary"] = PROOF_SEED_SUMMARY
        connection.store["approved_wording"] = PROOF_SEED_SUMMARY
        connection.store["resume_display"] = 1
        connection.store["visitor_ai"] = 1
        connection.store["user_key"] = owner
        connection.store["entry_key"] = PROOF_ENTRY_KEY
        connection.store["lifecycle"] = "active"
        connection.store["content_version"] = 1
        connection.store["access_revision"] = 2
        execute_procedure(
            connection,
            "usp_CommitResumePublicationCommandForOwner",
            _commit_parameters(
                owner,
                {
                    "request_id": "00000000-0000-4000-8000-00000000000a",
                    "json": _publish_json(),
                },
            ),
        )
        connection.close()

    def test_publish_versus_correction_race_keeps_sharing_enabled(self):
        identity = "docker:proof-publish-correct"

        def connect(_identity):
            return _EngineConnection(identity)

        self._seed_publish(identity)
        result = run_two_connection_race(
            identity,
            "owner-a",
            "owner-a",
            {
                "request_id": "11111111-1111-4111-8111-111111111111",
                "json": _publish_json("b" * 64),
            },
            {
                "request_id": "22222222-2222-4222-8222-222222222222",
                "json": _correct_json(),
            },
            connect=connect,
            pair="publish_versus_correction",
            observe=_capture_owner_state,
        )
        self.assertIn("committed", result["outcomes"])
        self.assertNotIn("conflict_or_error", result["outcomes"])
        self.assertEqual(result["final_state"]["sharing"][0][0], 1)
        self.assertGreaterEqual(result["final_state"]["sharing"][0][2], 1)

    def test_publish_versus_revocation_race_matches_committed_side(self):
        identity = "docker:proof-publish-revoke"

        def connect(_identity):
            return _EngineConnection(identity)

        self._seed_publish(identity)
        result = run_two_connection_race(
            identity,
            "owner-a",
            "owner-a",
            {
                "request_id": "44444444-4444-4444-8444-444444444444",
                "json": _publish_json("c" * 64),
            },
            {
                "request_id": "55555555-5555-4555-8555-555555555555",
                "json": '{"type":"sharing_off"}',
            },
            connect=connect,
            pair="publish_versus_revocation",
            observe=_capture_owner_state,
        )
        self.assertIn("committed", result["outcomes"])
        enabled = bool(result["final_state"]["sharing_enabled"])
        publish_committed = result["outcomes"][0] == "committed"
        revoke_committed = result["outcomes"][1] == "committed"
        if publish_committed and not revoke_committed:
            self.assertTrue(enabled)
            self.assertEqual(result["final_state"]["public_slug"], PROOF_PUBLIC_SLUG)
        elif revoke_committed and not publish_committed:
            self.assertFalse(enabled)
        else:
            winner = None
            for row in reversed(result["final_state"]["outbox"] or []):
                if row[1] in {"publish", "sharing_off"}:
                    winner = row[1]
                    break
            if winner == "publish":
                self.assertTrue(enabled)
                self.assertEqual(result["final_state"]["public_slug"], PROOF_PUBLIC_SLUG)
            else:
                self.assertEqual(winner, "sharing_off")
                self.assertFalse(enabled)

    def test_two_connection_race_rejects_both_failures(self):
        class ConflictConnection:
            def cursor(self):
                class Cursor:
                    def execute(self, statement, params=None):
                        if statement == "SET LOCK_TIMEOUT 5000":
                            return None
                        raise RuntimeError("54022 already used a different payload")

                    def close(self):
                        return None

                return Cursor()

            def close(self):
                return None

        with self.assertRaisesRegex(EngineProofError, "race_both_failed"):
            run_two_connection_race(
                "docker:proof-both-fail",
                "owner-a",
                "owner-a",
                {
                    "request_id": "11111111-1111-4111-8111-111111111111",
                    "json": '{"type":"publish","slug":"alice"}',
                },
                {
                    "request_id": "22222222-2222-4222-8222-222222222222",
                    "json": '{"type":"correct"}',
                },
                connect=lambda _identity: ConflictConnection(),
                pair="publish_versus_correction",
                observe=lambda _connection: {
                    "sharing": [(1, 1, 1, 1)],
                    "receipts": [(1,)],
                    "revisions": [(1,)],
                },
            )

    def test_two_connection_race_rejects_unexpected_error(self):
        class BoomConnection:
            def cursor(self):
                class Cursor:
                    def execute(self, statement, params=None):
                        if statement == "SET LOCK_TIMEOUT 5000":
                            return None
                        raise RuntimeError("disk full")

                    def close(self):
                        return None

                return Cursor()

            def close(self):
                return None

        with self.assertRaisesRegex(EngineProofError, "race_unexpected_error"):
            run_two_connection_race(
                "docker:proof-unexpected",
                "owner-a",
                "owner-a",
                {"request_id": "11111111-1111-4111-8111-111111111111", "json": _publish_json()},
                {"request_id": "22222222-2222-4222-8222-222222222222", "json": _correct_json()},
                connect=lambda _identity: BoomConnection(),
                pair="publish_versus_correction",
            )

    def test_two_connection_race_rejects_invalid_final_state(self):
        identity = "docker:proof-invalid-state"

        def connect(_identity):
            return _EngineConnection(identity)

        self._seed_publish(identity)
        with self.assertRaisesRegex(EngineProofError, "race_invalid_final_state"):
            run_two_connection_race(
                identity,
                "owner-a",
                "owner-a",
                {
                    "request_id": "11111111-1111-4111-8111-111111111111",
                    "json": _publish_json(),
                },
                {
                    "request_id": "22222222-2222-4222-8222-222222222222",
                    "json": _correct_json(),
                },
                connect=connect,
                pair="publish_versus_correction",
                observe=lambda _connection: {
                    "sharing": [(0, 1, 2, 2, "alice")],
                    "sharing_enabled": False,
                    "publication_revision": 2,
                    "resume_display": True,
                    "canonical_summary": PROOF_SEED_SUMMARY,
                    "owner_present": True,
                },
            )

    def test_assert_race_pair_state_rejects_two_failures_and_invalid_sharing(self):
        with self.assertRaisesRegex(EngineProofError, "race_both_failed"):
            assert_race_pair_state(
                "publish_versus_correction",
                ("conflict", "conflict"),
                {"json": _publish_json()},
                {"json": _correct_json()},
                {"sharing": [(1, 1, 1, 1, "alice")], "sharing_enabled": True, "publication_revision": 1},
            )
        with self.assertRaisesRegex(EngineProofError, "race_invalid_final_state"):
            assert_race_pair_state(
                "publish_versus_correction",
                ("committed", "committed"),
                {"json": _publish_json()},
                {"json": _correct_json()},
                {
                    "sharing": [(0, 1, 2, 2, "alice")],
                    "sharing_enabled": False,
                    "publication_revision": 2,
                    "resume_display": True,
                    "canonical_summary": PROOF_CORRECTED_SUMMARY,
                    "display_json": json.dumps({"summary": PROOF_CORRECTED_SUMMARY}),
                    "owner_present": True,
                },
            )

    def test_classify_sql_commit_error_accepts_only_known_conflicts(self):
        self.assertEqual(
            classify_sql_commit_error(RuntimeError("THROW 54023 The publication changed.")),
            "conflict",
        )
        with self.assertRaisesRegex(EngineProofError, "race_unexpected_error"):
            classify_sql_commit_error(RuntimeError("login failed"))

    def test_injected_rollback_rejects_ambient_transaction_as_proof(self):
        class AmbientConnection(_EngineConnection):
            def cursor(self):
                cursor = _EngineCursor(self)

                def execute(statement, params=None):
                    sql = statement if isinstance(statement, str) else str(statement)
                    if "usp_CommitResumePublicationCommandForOwner" in sql:
                        raise RuntimeError("Ambient transactions are not permitted.")
                    return _EngineCursor.execute(cursor, statement, params)

                cursor.execute = execute
                return cursor

        with self.assertRaisesRegex(
            EngineProofError, "ambient_transaction_rejection_is_not_rollback_proof"
        ):
            run_injected_rollback(
                "docker:ps-mvp1-ef-sql-proof-20260916-01-sql",
                "owner-a",
                {"request_id": "11111111-1111-4111-8111-111111111111", "json": '{"type":"publish"}'},
                connect=lambda _identity: AmbientConnection(_identity),
            )

    def test_injected_rollback_requires_in_transaction_failure_and_restored_state(self):
        result = run_injected_rollback(
            "docker:ps-mvp1-ef-sql-proof-20260916-01-sql",
            "owner-a",
            {"request_id": "11111111-1111-4111-8111-111111111111", "json": '{"type":"publish"}'},
            connect=lambda _identity: _EngineConnection(_identity),
        )
        self.assertTrue(result["rolled_back"])
        self.assertTrue(result["injected_after_writes"])
        self.assertEqual(result["before"], result["after"])

    def test_migration_closure_rejects_catalog_and_publication_only(self):
        order = []
        with self.assertRaisesRegex(EngineProofError, "incomplete_migration_closure"):
            run_migration_closure(
                lambda: order.append("forward"),
                lambda: order.append("rollback"),
                lambda: order.append("verify"),
                ordered_ids=["PS-RESUME-CATALOG-001", "PS-RESUME-PUBLICATION-001"],
            )
        self.assertEqual(order, [])

    def test_migration_closure_requires_complete_registry_order(self):
        order = []
        ids = [item["id"] for item in resolve_publication_migration_closure()]
        self.assertIn("PS-PLAT-000", ids)
        self.assertIn("PS-RESUME-MEDIA-001", ids)
        self.assertEqual(set(ids), set(REQUIRED_PUBLICATION_CLOSURE_IDS))
        result = run_migration_closure(
            lambda: order.append("forward"),
            lambda: order.append("rollback"),
            lambda: order.append("verify"),
            ordered_ids=ids,
        )
        self.assertEqual(order, ["forward", "verify", "rollback", "forward", "verify"])
        self.assertTrue(result["closed"])
        self.assertTrue(result["reapplied"])

    def test_codec_oracle_compares_sql_and_python_bytes(self):
        connection = _EngineConnection("docker:proof")
        result = run_codec_and_evidence(connection, connection.codec_fields)
        self.assertTrue(result["equal"])
        self.assertEqual(result["sha256"], hash_canonical_source(encode_canonical_source(connection.codec_fields)))

    def test_codec_oracle_compares_independently_produced_python_bytes(self):
        fields = _EngineConnection("docker:proof").codec_fields
        python_bytes = encode_canonical_source(fields)
        python_digest = hash_canonical_source(python_bytes)

        class IndependentCursor:
            def execute(self, statement, params=None):
                return None

            def fetchone(self):
                return (python_bytes, python_digest)

            def close(self):
                return None

        class IndependentConnection:
            def cursor(self):
                return IndependentCursor()

            def close(self):
                return None

        result = run_codec_and_evidence(IndependentConnection(), fields)
        self.assertTrue(result["equal"])
        self.assertEqual(result["sha256"], python_digest)

    def test_codec_oracle_rejects_mismatched_sql_bytes(self):
        fields = _EngineConnection("docker:proof").codec_fields

        class MismatchCursor:
            def execute(self, statement, params=None):
                return None

            def fetchone(self):
                return (b"not-the-python-codec", "0" * 64)

            def close(self):
                return None

        class MismatchConnection:
            def cursor(self):
                return MismatchCursor()

            def close(self):
                return None

        with self.assertRaisesRegex(EngineProofError, "codec_mismatch"):
            run_codec_and_evidence(MismatchConnection(), fields)

    def test_sequence_contract_oracle_checks_limits_and_rejects_faulty_observations(self):
        result = run_sql_sequence_contracts(_EngineConnection("docker:sequence-contracts"), "owner-a", "owner-b")
        self.assertTrue(result["duplicate_slug_rejected"])
        self.assertGreater(result["codec_vectors"]["over_4000_characters"]["bytes"], 8200)
        self.assertEqual(result["invalid_codec_vectors_rejected"], 4)
        for marker, row, error in (
            ("publication slug constraint proof", (1, 1, 1), "unpublished_owner_slug_constraint_failed"),
            ("publication slug constraint proof", (2, 0, 2), "unpublished_owner_slug_constraint_failed"),
            ("publication codec rejection proof", (0,), "sql_codec_invalid_field_accepted"),
        ):
            with self.subTest(marker=marker, row=row):
                class FaultyCursor(_EngineCursor):
                    def execute(self, sql, params=None):
                        result = super().execute(sql, params)
                        if marker in sql:
                            self._one = row
                        return result
                class FaultyConnection(_EngineConnection):
                    def cursor(self):
                        return FaultyCursor(self)
                with self.assertRaisesRegex(EngineProofError, error):
                    run_sql_sequence_contracts(FaultyConnection("docker:sequence-fault"), "owner-a", "owner-b")

    def test_token_probe_rejects_missing_or_changed_media_reader_result(self):
        for fault in ("missing_call", "changed_token", "missing_result"):
            with self.subTest(fault=fault):
                class FaultyCursor(_EngineCursor):
                    def execute(self, sql, params=None):
                        token_probe = "publication draft version token proof" in sql
                        if token_probe and fault == "missing_call":
                            sql = sql.replace("EXEC dbo.usp_GetResumeMediaDraftForOwner @UserKey = @Owner;", "")
                        result = super().execute(sql, params)
                        if token_probe and fault == "changed_token":
                            description, _ = self._pending_sets[0]
                            self._pending_sets[0] = (description, [(42, 0)])
                        if token_probe and fault == "missing_result":
                            self._pending_sets = []
                        return result

                class FaultyConnection(_EngineConnection):
                    def cursor(self):
                        return FaultyCursor(self)

                with self.assertRaisesRegex(EngineProofError, "media_publication_version_token_changed"):
                    run_sql_sequence_contracts(FaultyConnection("docker:token-fault"), "owner-a", "owner-b")

    def test_migration_batch_surfaces_late_statement_errors_before_commit(self):
        from services.resume_publication_adapters import apply_sql_script

        class Cursor:
            description = None
            closed = False

            def execute(self, sql):
                pass

            def nextset(self):
                raise RuntimeError("late migration statement failed")

            def close(self):
                self.closed = True

        class Connection:
            committed = False
            result = Cursor()

            def cursor(self):
                return self.result

            def commit(self):
                self.committed = True

        connection = Connection()
        with self.assertRaisesRegex(RuntimeError, "late migration statement failed"):
            apply_sql_script(connection, "SELECT 1; THROW 54998, 'late', 1;")
        self.assertFalse(connection.committed)
        self.assertTrue(connection.result.closed)

    def test_migration_failure_retains_file_phase_and_sanitized_native_diagnostics(self):
        from types import SimpleNamespace
        from services.resume_publication_adapters import apply_sql_file

        for phase in ("execute", "drain", "commit"):
            for diagnostics_available in (True, False):
                with self.subTest(phase=phase, diagnostics_available=diagnostics_available):
                    events = []
                    class Cursor:
                        description = None
                        hstmt = object()
                        messages = [("01000", "synthetic diagnostic password=fixture-secret")]

                        def execute(self, sql):
                            events.append(("execute", sql))
                            if phase == "execute":
                                raise RuntimeError("generic SQL error")

                        def nextset(self):
                            events.append(("drain",))
                            if phase == "drain":
                                raise RuntimeError("generic SQL error")
                            return False

                        def close(self):
                            events.append(("close",))

                    cursor = Cursor()
                    class Connection:
                        def cursor(self):
                            return cursor

                        def commit(self):
                            events.append(("commit",))
                            raise RuntimeError("generic SQL error")

                    def native_diagnostics(handle):
                        self.assertIs(handle, cursor.hstmt)
                        self.assertNotIn(("close",), events)
                        events.append(("diagnostics",))
                        if not diagnostics_available:
                            raise RuntimeError("diagnostic lookup unavailable")
                        return [("42000", "SQL error 207 line 19: missing_column fixture-secret")]

                    driver = SimpleNamespace(ddbc_bindings=SimpleNamespace(DDBCSQLGetAllDiagRecords=native_diagnostics))
                    with TemporaryDirectory() as directory, patch.dict("sys.modules", {"mssql_python": driver}), patch.dict(os.environ, {"MSSQL_SA_PASSWORD": "fixture-secret"}):
                        path = Path(directory) / "synthetic_verify.sql"
                        path.write_text("SELECT 1;", encoding="utf-8")
                        with self.assertRaises(EngineProofError) as caught:
                            apply_sql_file(Connection(), path)
                    message = str(caught.exception)
                    self.assertIn("migration_file_synthetic_verify.sql_failed", message)
                    self.assertIn(f"sql_batch_{phase}_failed", message)
                    self.assertIn("generic SQL error", message)
                    self.assertNotIn("fixture-secret", message)
                    self.assertNotIn("diagnostic lookup unavailable", message)
                    if diagnostics_available:
                        self.assertIn("SQL error 207 line 19: missing_column", message)
                    self.assertEqual(events[0], ("execute", "SELECT 1;"))
                    self.assertEqual(events[-1], ("close",))
                    self.assertEqual(events.count(("commit",)), int(phase == "commit"))

    def test_execute_procedure_maps_mssql_python_result_sets(self):
        from db import fetch_all_result_sets
        from services.resume_publication_adapters import execute_procedure

        class MssqlShapedCursor:
            def __init__(self):
                self.description = [
                    ("committed", 0, None, None, None, None, None),
                    ("replayed", 0, None, None, None, None, None),
                ]
                self.executed = None

            def execute(self, statement, params=None):
                self.executed = (statement, params)
                return None

            def fetchall(self):
                return [(1, 0)]

            def nextset(self):
                return False

            def close(self):
                return None

        class MssqlShapedConnection:
            def __init__(self):
                self.cursor_obj = MssqlShapedCursor()

            def cursor(self):
                return self.cursor_obj

        mapped = fetch_all_result_sets(MssqlShapedConnection().cursor())
        self.assertEqual(mapped, [[{"committed": 1, "replayed": 0}]])
        rows = execute_procedure(
            MssqlShapedConnection(),
            "usp_CommitResumePublicationCommandForOwner",
            [("@UserKey", "owner-a"), ("@RequestId", "r"), ("@CommandJson", "{}")],
        )
        self.assertEqual(rows, [{"committed": 1, "replayed": 0}])

    def test_docker_cli_runtime_uses_docker_argv_without_contacting_daemon(self):
        import subprocess

        from services.resume_publication_adapters import IsolatedDockerCliRuntime, PROOF_ID

        calls = []

        def runner(args, **kwargs):
            calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        created = runtime.create_network("proof-net", internal=True, marker=PROOF_ID)
        self.assertEqual(created["id"], "abc123")
        self.assertEqual(calls[0][0], "docker")
        self.assertIn("network", calls[0])
        self.assertIn("--internal", calls[0])

    def test_docker_sql_start_uses_invocation_local_secret_outside_argv(self):
        import subprocess

        from services.resume_publication_adapters import IsolatedDockerCliRuntime, PROOF_ID

        calls = []
        envs = []

        def runner(args, **kwargs):
            calls.append(list(args))
            envs.append(kwargs.get("env"))
            return subprocess.CompletedProcess(args, 0, stdout="sql-id\n", stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        runtime.start_sql(
            "proof-sql",
            image="python:3.12-slim",
            network="proof-net",
            marker=PROOF_ID,
        )
        start = next(item for item in calls if "run" in item and "MSSQL_SA_PASSWORD" in item)
        self.assertIn("MSSQL_SA_PASSWORD", start)
        self.assertIn("--memory", start)
        self.assertIn("--cpus", start)
        self.assertIn("--pids-limit", start)
        self.assertIn("--hostname", start)
        self.assertNotIn("-p", start)
        self.assertNotIn("--publish", start)
        self.assertFalse(any(item.startswith("MSSQL_SA_PASSWORD=") for item in start))
        self.assertNotIn(runtime._sql_password, " ".join(start))
        start_env = next(item for item in envs if item and "MSSQL_SA_PASSWORD" in item)
        self.assertEqual(start_env["MSSQL_SA_PASSWORD"], runtime._sql_password)

    def test_docker_client_bakes_hashed_source_and_offline_wheels(self):
        from services.resume_publication_adapters import (
            IsolatedDockerCliRuntime,
            PROOF_CLIENT_LOCKFILE,
            source_manifest,
        )

        calls = []

        def runner(args, **kwargs):
            calls.append(list(args))
            if "build" in args:
                Path(args[args.index("--iidfile") + 1]).write_text("sha256:" + "a" * 64)
                dockerfile = Path(args[-1]) / "Dockerfile"
                text = dockerfile.read_text(encoding="utf-8")
                self.assertIn("--require-hashes --no-index", text)
                self.assertIn("COPY source/", text)
                self.assertIn("libltdl7 libkrb5-3 libgssapi-krb5-2", text)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        other = IsolatedDockerCliRuntime(runner=runner)
        self.assertNotEqual(runtime.invocation_marker, other.invocation_marker)
        with TemporaryDirectory() as directory:
            image = runtime.build_client_image(Path(__file__).resolve().parents[1], Path(directory), source_manifest())
        self.assertEqual(image["id"], "sha256:" + "a" * 64)
        self.assertEqual(image["marker"], runtime.invocation_marker)
        build = next(item for item in calls if "build" in item)
        self.assertIn("--tag", build)
        self.assertIn(f"peerslate.proof_id={runtime.invocation_marker}", build)
        lock = PROOF_CLIENT_LOCKFILE.read_text(encoding="utf-8")
        self.assertIn("azure-identity==1.25.3", lock)
        self.assertIn("d9ed6e3a3b4bbfb8acb18946de0919ca7b83e8456fa8cf78f668ef89f476f093", lock)
        self.assertNotIn("recorded at execute", lock.lower())
        self.assertIn("--no-index", lock)

    def test_isolation_inspects_both_containers_and_exact_network(self):
        import subprocess
        from services.resume_publication_adapters import PROOF_CLIENT_CONTAINER, PROOF_NETWORK

        def runner(args, **_kwargs):
            text = ""
            if args[1:3] == ["network", "inspect"]:
                text = "true"
            elif "PortBindings" in " ".join(args):
                text = "{}"
            elif "Binds" in " ".join(args):
                text = "null"
            elif "Mounts" in " ".join(args):
                text = "[]"
            elif "NetworkSettings.Networks" in " ".join(args):
                networks = {PROOF_NETWORK: {}}
                if args[-1] == PROOF_CLIENT_CONTAINER:
                    networks["bridge"] = {}
                text = json.dumps(networks)
            return subprocess.CompletedProcess(args, 0, stdout=text, stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        with self.assertRaisesRegex(EngineProofError, "prohibited_topology"):
            runtime.verify_isolation()

    def test_sql_image_identity_compares_config_id_and_pinned_repo_digest(self):
        import subprocess
        from services.resume_publication_adapters import SQL_IMAGE

        runtime = None
        config_id = "sha256:" + "f" * 64

        def runner(args, **_kwargs):
            joined = " ".join(args)
            if "RepoDigests" in joined:
                output = json.dumps([SQL_IMAGE])
            elif "{{.Image}}" in joined or "{{.Id}}" in joined and "image" in args:
                output = config_id
            elif "{{.Id}}" in joined:
                output = "sql-container-id"
            elif "peerslate.proof_id" in joined:
                output = runtime.invocation_marker
            elif "SERVERPROPERTY" in joined:
                output = "16.0.4265.3 Developer Edition"
            else:
                output = ""
            return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        result = runtime.verify_sql_identity({"id": "sql-container-id"})
        self.assertEqual(result["image"], SQL_IMAGE)
        self.assertEqual(result["image_id"], config_id)
        self.assertEqual(result["sql_build"], "16.0.4265.3")

    def test_docker_client_oracles_use_env_secret_and_in_client_flag(self):
        calls = []
        envs = []

        def runner(args, **kwargs):
            calls.append(list(args))
            envs.append(kwargs.get("env"))
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        runtime = IsolatedDockerCliRuntime(runner=runner)
        with self.assertRaisesRegex(EngineProofError, "client_evidence_copy_failed"):
            runtime.run_client_oracles(source_sha="abc")
        exec_call = next(
            item
            for item in calls
            if "exec" in item and any("run_resume_publication_sql_proof.py" in str(part) for part in item)
        )
        self.assertIn("--in-client-oracles", exec_call)
        self.assertIn("MSSQL_SA_PASSWORD", exec_call)
        self.assertFalse(any(item.startswith("MSSQL_SA_PASSWORD=") for item in exec_call))
        self.assertNotIn(runtime._sql_password, " ".join(exec_call))
        exec_env = next(item for item in envs if item and item.get("MSSQL_SA_PASSWORD") == runtime._sql_password)
        self.assertEqual(exec_env["PEERSLATE_RESUME_PUBLICATION_SQL_HOST"], "ps-mvp1-ef-sql-proof-20260916-01-sql")

    def test_client_crash_without_evidence_retains_sanitized_exit_diagnostics(self):
        runtime = None

        def runner(args, **_kwargs):
            if args[1] == "exec":
                return subprocess.CompletedProcess(args, 139, stdout="", stderr=f"client crash PWD={runtime._sql_password}")
            if args[1] == "cp":
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="No such file")
            raise AssertionError(args)

        runtime = IsolatedDockerCliRuntime(runner=runner)
        with self.assertRaisesRegex(EngineProofError, "client_oracles_failed:exit=139:copy_exit=1") as caught:
            runtime.run_client_oracles(source_sha="a" * 40)
        detail = str(caught.exception)
        self.assertNotIn(runtime._sql_password, detail)
        self.assertIn("[redacted]", detail)
        self.assertIn("No such file", detail)

    def test_nonzero_client_exit_overrides_written_pass_evidence(self):
        with TemporaryDirectory() as directory:
            def runner(args, **_kwargs):
                if args[1] == "exec":
                    return subprocess.CompletedProcess(args, 1, stdout="", stderr="client failed")
                if args[1] == "cp":
                    Path(args[-1]).write_text(json.dumps({"status": "pass", "oracles": {"claimed": True}}),
                                             encoding="utf-8")
                    return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
                raise AssertionError(args)

            runtime = IsolatedDockerCliRuntime(runner=runner)
            with patch("services.resume_publication_adapters.tempfile.mkdtemp", return_value=directory):
                result = runtime.run_client_oracles(source_sha="a" * 40)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["client_exit"], 1)
        self.assertEqual(result["oracles"], {"claimed": True})

    def test_prepare_hashed_wheelhouse_targets_linux_cp312_and_verifies_bytes(self):
        with TemporaryDirectory() as directory:
            dest = Path(directory) / "wheels"
            lockfile = Path(directory) / "lock.txt"
            payload = b"linux-cp312-wheel"
            digest = hashlib.sha256(payload).hexdigest()
            lockfile.write_text(f"demo==1.0.0 \\\n    --hash=sha256:{digest}\n", encoding="utf-8")

            def runner(args, **kwargs):
                self.assertIn("download", args)
                self.assertIn("--require-hashes", args)
                self.assertIn("--python-version", args)
                self.assertEqual(args[args.index("--python-version") + 1], "3.12")
                self.assertIn("manylinux_2_28_x86_64", args)
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "demo.whl").write_bytes(payload)
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

            prepared = prepare_hashed_wheelhouse(dest, lockfile, runner=runner)
            proof = verify_downloaded_wheelhouse(prepared, lockfile)
            self.assertTrue(proof["downloaded_bytes_independently_verified"])
            self.assertEqual(proof["source"], "downloaded_bytes")
            (dest / "extra.bin").write_bytes(b"not-in-lock")
            with self.assertRaisesRegex(EngineProofError, "wheelhouse_hash_mismatch"):
                verify_downloaded_wheelhouse(dest, lockfile)

    def test_sanitize_proof_error_redacts_password_and_connection_string(self):
        secret = "s3cret-token-value"
        error = RuntimeError(
            f"Login failed PWD={secret};MSSQL_SA_PASSWORD={secret} Server=x;UID=sa;PWD={secret}"
        )
        text = sanitize_proof_error(error, (secret,))
        self.assertNotIn(secret, text)
        self.assertIn("[redacted]", text)

    def test_seed_and_correction_oracles_change_wording(self):
        identity = "docker:proof-seed-correct"

        def connect(database_identity):
            return _EngineConnection(database_identity)

        ids = [item["id"] for item in resolve_publication_migration_closure()]
        payload = run_publication_sql_oracles(
            identity,
            connect,
            apply_forward=_simulated_capture_forward,
            apply_rollback=lambda identity: (_ for _ in ()).throw(RuntimeError("54120 Rollback refused"))
            if identity.endswith("PeerSlateMvp1EFPopulated_20260916_01") else None,
            verify=lambda _identity: None,
            ordered_ids=ids,
        )
        self.assertTrue(payload["oracles"]["correction_wording"]["changed"])
        self.assertEqual(payload["oracles"]["correction_wording"]["after"], PROOF_CORRECTED_SUMMARY)
        self.assertIn(
            payload["oracles"]["final_state"]["canonical_summary"],
            {PROOF_CORRECTED_SUMMARY, PROOF_RACE_SUMMARY, PROOF_SEED_SUMMARY},
        )
        self.assertEqual(payload["oracles"]["mandatory_case_count"], len(MANDATORY_ENGINE_CASES))
        self.assertEqual(set(payload["oracles"]["mandatory_cases"]), set(MANDATORY_ENGINE_CASES))
        commands = _EngineConnection._stores[f"{identity}:{PROOF_POPULATED_DATABASE}"]["policy_commands"]
        self.assertIn(("edit", "peerslate_app"), commands)
        self.assertIn(("change_permissions", "peerslate_app"), commands)

    def test_editor_allowlist_oracle_rejects_weakened_or_write_before_reject_engine(self):
        ids = [item["id"] for item in resolve_publication_migration_closure()]
        for mutation, expected in (
            ("enforce_editor_allowlist", "editor_field_allowlist_accepted"),
            ("editor_reject_with_write", "editor_field_allowlist_left_target_or_receipt"),
        ):
            with self.subTest(mutation=mutation):
                _EngineConnection.reset()

                class MutatedConnection(_EngineConnection):
                    enforce_editor_allowlist = mutation != "enforce_editor_allowlist"
                    editor_reject_with_write = mutation == "editor_reject_with_write"

                with self.assertRaisesRegex(EngineProofError, expected):
                    run_publication_sql_oracles(
                        f"docker:proof-editor-mutation-{mutation}",
                        MutatedConnection,
                        apply_forward=_simulated_capture_forward,
                        apply_rollback=lambda _identity: None,
                        verify=lambda _identity: None,
                        ordered_ids=ids,
                    )

    def test_seed_missing_owner_fails(self):
        class EmptyCursor:
            description = None

            def execute(self, statement, params=None):
                return None

            def fetchall(self):
                return []

            def nextset(self):
                return False

            def close(self):
                return None

        class EmptyConnection:
            def cursor(self):
                return EmptyCursor()

            def close(self):
                return None

        with self.assertRaisesRegex(EngineProofError, "seed_owner_missing"):
            seed_publication_owner(EmptyConnection())

    def test_correction_wording_unchanged_fails_race_assertion(self):
        with self.assertRaisesRegex(EngineProofError, "correction_wording_unchanged"):
            assert_race_pair_state(
                "publish_versus_correction",
                ("committed", "committed"),
                {"json": _publish_json()},
                {"json": _correct_json()},
                {
                    "sharing_enabled": True,
                    "publication_revision": 2,
                    "resume_display": True,
                    "canonical_summary": PROOF_SEED_SUMMARY,
                    "display_json": json.dumps({"summary": PROOF_SEED_SUMMARY}),
                    "owner_present": True,
                    "public_slug": PROOF_PUBLIC_SLUG,
                },
            )

    def test_revocation_winner_is_last_outbox_not_either_flag(self):
        publish = {"json": _publish_json()}
        revoke = {"json": '{"type":"sharing_off"}'}
        with self.assertRaisesRegex(EngineProofError, "race_invalid_final_state"):
            assert_race_pair_state(
                "publish_versus_revocation",
                ("committed", "committed"),
                publish,
                revoke,
                {
                    "sharing_enabled": True,
                    "publication_revision": 2,
                    "public_slug": PROOF_PUBLIC_SLUG,
                    "owner_present": True,
                    "resume_display": True,
                    "outbox": [(1, "publish", 1), (2, "sharing_off", 1)],
                },
            )
        with self.assertRaisesRegex(EngineProofError, "race_invalid_final_state"):
            assert_race_pair_state(
                "publish_versus_revocation",
                ("committed", "conflict"),
                publish,
                revoke,
                {"publication_revision": 3, "receipts": [(3,)], "owner_present": True},
            )
        assert_race_pair_state(
            "publish_versus_revocation",
            ("committed", "committed"),
            publish,
            revoke,
            {
                "sharing_enabled": False,
                "publication_revision": 1,
                "public_slug": PROOF_PUBLIC_SLUG,
                "owner_present": True,
                "resume_display": True,
                "outbox": [(1, "publish", 1), (2, "sharing_off", 1)],
            },
        )

    def test_connect_from_client_environment_requires_env_secret_and_internal_host(self):
        with self.assertRaisesRegex(EngineProofError, "sql_secret_missing"):
            connect_from_client_environment("docker:proof-sql")
        with patch.dict(
            os.environ,
            {
                "MSSQL_SA_PASSWORD": "local-secret",
                "PEERSLATE_RESUME_PUBLICATION_SQL_HOST": "localhost",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(EngineProofError, "sql_host_not_job_local"):
                connect_from_client_environment("docker:proof-sql")

    def test_acquire_runs_baked_content_id_after_source_digest_check(self):
        created = []
        with TemporaryDirectory() as directory:
            wheels = Path(directory) / "wheels"
            wheels.mkdir()

            class Recording:
                def exists(self, name):
                    return False

                def prepare_hashed_wheelhouse(self):
                    created.append("prepare")
                    return wheels

                def verify_downloaded_wheelhouse(self, path):
                    created.append(("verify", Path(path).name))
                    return {
                        "downloaded_bytes_independently_verified": True,
                        "artifact_count": 1,
                        "source": "downloaded_bytes",
                    }

                def build_client_image(self, root, wheelhouse, manifest):
                    created.append(("build", len(manifest)))
                    return {"id": "sha256:" + "a" * 64, "marker": PROOF_ID}

                def create_network(self, name, internal=True, marker=""):
                    created.append(("network", internal))
                    return {"id": "net-1", "marker": marker}

                def start_sql(self, name, **kwargs):
                    created.append(("sql", kwargs.get("publish_host_ports")))
                    return {"id": "sql-1", "marker": kwargs.get("marker")}

                def start_client(self, name, **kwargs):
                    created.append(("client", kwargs.get("image")))
                    return {"id": "client-1", "marker": kwargs.get("marker")}

                def verify_copied_client_source(self, container, manifest):
                    created.append(("source_digest", container))
                    return manifest

                def verify_sql_identity(self, sql):
                    return {"production_connection": False, "database": "PeerSlateMvp1EFEmpty_20260916_01", "sql_build": "16.0.4265.3"}

                def ensure_databases(self, names):
                    created.append(("databases", tuple(names)))

            acquired = acquire_isolated_sql_runtime(Recording())
        self.assertTrue(acquired["client_oracles"])
        self.assertNotIn("connect", acquired)
        self.assertEqual(
            [item[0] if isinstance(item, tuple) else item for item in created],
            [
                "prepare",
                "verify",
                "build",
                "network",
                "sql",
                "client",
                "source_digest",
                "databases",
            ],
        )
        self.assertIn(("client", "sha256:" + "a" * 64), created)

    def test_acquire_refuses_preexisting_and_cleanup_refuses_unowned(self):
        from services.resume_publication_adapters import (
            PROOF_ID,
            acquire_isolated_sql_runtime,
            cleanup_owned_resources,
        )

        class Existing:
            def exists(self, name):
                return True

        with self.assertRaisesRegex(EngineProofError, "preexisting_resource"):
            acquire_isolated_sql_runtime(Existing())

        class Foreign:
            def inspect(self, name):
                return {"id": "other", "marker": "not-owned"}

            def remove(self, name):
                raise AssertionError("must not remove unowned resources")

            def exists(self, name):
                return True

        result = cleanup_owned_resources(
            Foreign(),
            [{"name": "foreign", "id": "owned-id", "marker": PROOF_ID}],
        )
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["attempts"][0]["status"], "identity_mismatch")

    def test_application_principal_requires_internal_deny(self):
        result = assert_application_principal_permissions(_EngineConnection("docker:proof"), "peerslate_app")
        self.assertTrue(result["internal_denied_present"])
        self.assertIn("usp_ResumePublicationEncodeSourceInternal", result["internal_denied"])

    def test_mandatory_cases_missing_or_skipped_fail(self):
        with self.assertRaisesRegex(EngineProofError, "mandatory_cases_none_executed"):
            assert_executed_mandatory_cases({})
        with self.assertRaisesRegex(EngineProofError, "mandatory_cases_missing"):
            assert_executed_mandatory_cases({"empty_database_compile": "pass"})
        with self.assertRaisesRegex(EngineProofError, "mandatory_cases_skipped"):
            assert_executed_mandatory_cases({name: "skip" for name in MANDATORY_ENGINE_CASES})

    def test_wrong_source_sha_refuses_before_resources(self):
        with self.assertRaisesRegex(EngineProofError, "source_sha_mismatch"):
            with patch(
                "services.resume_publication_adapters.checkout_sha",
                return_value="a" * 40,
            ):
                assert_reviewed_source("b" * 40)

    def test_checkout_sha_uses_git_and_rejects_conflicting_build(self):
        completed = subprocess.CompletedProcess(["git"], 0, stdout="a" * 40 + "\n", stderr="")
        with patch("services.resume_publication_adapters.subprocess.run", return_value=completed):
            with patch.dict(os.environ, {"BUILD_SOURCEVERSION": "b" * 40}):
                with self.assertRaisesRegex(EngineProofError, "source_sha_mismatch"):
                    checkout_sha()
            with patch.dict(os.environ, {"BUILD_SOURCEVERSION": "a" * 40}):
                self.assertEqual(checkout_sha(), "a" * 40)

    def test_source_manifest_hashes_client_bytes(self):
        manifest = source_manifest()
        self.assertIn("services/resume_publication_repository.py", manifest)
        self.assertIn("services/resume_publication_service.py", manifest)
        self.assertTrue(all(len(digest) == 64 for digest in manifest.values()))

    def test_source_manifest_excludes_generated_bytecode(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "services" / "ai_foundation"
            source.mkdir(parents=True)
            (source / "contracts.py").write_text("SOURCE = True\n", encoding="utf-8")
            with patch("services.resume_publication_adapters.PROOF_CLIENT_SOURCE_PATHS", ("services/ai_foundation",)):
                expected = source_manifest(root)
                bytecode = source / "__pycache__"
                bytecode.mkdir()
                (bytecode / "contracts.cpython-312.pyc").write_bytes(b"generated-bytecode")
                (source / "contracts.pyc").write_bytes(b"generated-bytecode")
                self.assertEqual(source_manifest(root), expected)
                self.assertEqual(set(expected), {"services/ai_foundation/contracts.py"})

    def test_acquire_registers_created_ids_before_injected_failure(self):
        owned = []

        class Partial:
            fail_after = "sql"

            def exists(self, name):
                return False

            def prepare_hashed_wheelhouse(self):
                return Path(".")

            def verify_downloaded_wheelhouse(self, path):
                return {"downloaded_bytes_independently_verified": True, "artifact_count": 1, "source": "downloaded_bytes"}

            def build_client_image(self, root, wheelhouse, manifest):
                return {"id": "sha256:" + "a" * 64, "marker": PROOF_ID}

            def create_network(self, name, internal=True, marker=""):
                return {"id": "net-1", "marker": marker}

            def start_sql(self, name, **kwargs):
                return {"id": "sql-1", "marker": kwargs.get("marker")}

            def start_client(self, name, **kwargs):
                raise AssertionError("client must not start after injected sql failure")

        with TemporaryDirectory():
            with self.assertRaisesRegex(EngineProofError, "injected_failure:sql"):
                acquire_isolated_sql_runtime(Partial(), owned=owned)
        self.assertEqual([item["name"] for item in owned], [
            "peerslate-mvp1-e-sql-proof:20260916-01",
            "ps-mvp1-ef-sql-proof-20260916-01-net",
            "ps-mvp1-ef-sql-proof-20260916-01-sql",
        ])

    def test_cleanup_continues_after_error_and_cannot_report_success(self):
        removed = []

        class Mixed:
            def inspect(self, name):
                if name == "bad":
                    return {"id": "bad-id", "marker": PROOF_ID}
                return {"id": "good-id", "marker": PROOF_ID}

            def remove(self, name):
                if name == "bad":
                    raise RuntimeError("remove failed")
                removed.append(name)

            def exists(self, name):
                return False

        result = cleanup_owned_resources(
            Mixed(),
            [
                {"name": "good", "id": "good-id", "marker": PROOF_ID},
                {"name": "bad", "id": "bad-id", "marker": PROOF_ID},
            ],
        )
        self.assertEqual(result["status"], "fail")
        self.assertEqual(removed, ["good"])

    def test_partial_image_build_remains_in_cleanup_custody(self):
        from services.resume_publication_adapters import PROOF_CLIENT_IMAGE_NAME

        marker = "ps-mvp1-ef-sql-proof-20260916-01.unique"
        image_id = "sha256:" + "b" * 64
        owned = []

        class PartialBuild:
            invocation_marker = marker

            def exists(self, _name):
                return False

            def verify_downloaded_wheelhouse(self, _path):
                return {"downloaded_bytes_independently_verified": True}

            def build_client_image(self, _root, _wheelhouse, _manifest):
                raise EngineProofError("client_image_build_failed")

            def inspect(self, name):
                if name == PROOF_CLIENT_IMAGE_NAME:
                    return {"id": image_id, "marker": marker}
                return None

        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(EngineProofError, "client_image_build_failed"):
                acquire_isolated_sql_runtime(
                    PartialBuild(), wheelhouse=Path(directory), owned=owned,
                    expected_manifest={"proof": "a" * 64},
                )
        self.assertEqual(owned, [{"name": PROOF_CLIENT_IMAGE_NAME,
                                  "id": image_id, "marker": marker, "kind": "image"}])

    def test_docker_network_shape_survives_acquisition_and_cleanup(self):
        from services.resume_publication_adapters import PROOF_NETWORK

        runtime, resources, calls = self._protocol_runtime()
        owned = []
        acquired = acquire_isolated_sql_runtime(
            runtime, wheelhouse=Path("."), owned=owned,
            expected_manifest={"proof": "a" * 64},
        )
        self.assertEqual(acquired["client_runtime"]["status"], "verified")
        self.assertEqual(acquired["client_runtime"]["mssql_python"], "1.0.0")
        self.assertEqual(set(acquired["client_runtime"]["os_libraries"]),
                         {"libltdl7", "libkrb5-3", "libgssapi-krb5-2"})
        self.assertEqual(owned[1]["name"], PROOF_NETWORK)
        self.assertEqual(runtime.inspect(PROOF_NETWORK)["id"], "net-1")
        network_labels = [cmd for cmd in calls if cmd[:2] == ["network", "inspect"]
                          and "peerslate.proof_id" in " ".join(cmd)]
        self.assertTrue(network_labels)
        self.assertTrue(all(".Labels" in " ".join(cmd) and ".Config.Labels" not in " ".join(cmd)
                            for cmd in network_labels))
        cleanup = cleanup_owned_resources(runtime, owned)
        self.assertEqual(cleanup["status"], "pass")
        self.assertTrue(all(item["name_absent_verified"] and item["id_absent_verified"]
                            for item in cleanup["attempts"]))
        self.assertEqual({item["id"] for item in cleanup["attempts"]},
                         {item["id"] for item in owned})
        self.assertEqual(resources, {})

    def test_resource_id_absence_requires_missing_error_for_that_exact_id(self):
        cases = (
            ("No such container: client-1", False),
            ("No such container: client-1-other", True),
            ("No such container: other-id", True),
            ("Error response from daemon: plugin not found", True),
        )
        for stderr, must_fail in cases:
            with self.subTest(stderr=stderr):
                def runner(args, **_kwargs):
                    return subprocess.CompletedProcess(args, 1, stdout="", stderr=stderr)

                runtime = IsolatedDockerCliRuntime(runner=runner)
                if must_fail:
                    with self.assertRaisesRegex(EngineProofError, "resource_id_inspect_unverified"):
                        runtime.resource_id_present("container", "client-1")
                else:
                    self.assertFalse(runtime.resource_id_present("container", "client-1"))

    def test_unrelated_id_inspection_error_keeps_cleanup_unverified(self):
        runtime, resources, _calls = self._protocol_runtime(unrelated_id_error_after_remove=True)
        owned = []
        acquire_isolated_sql_runtime(
            runtime, wheelhouse=Path("."), owned=owned,
            expected_manifest={"proof": "a" * 64},
        )
        cleanup = cleanup_owned_resources(runtime, owned)
        self.assertEqual(resources, {})
        self.assertEqual(cleanup["status"], "fail")
        self.assertTrue(all(item["status"] == "error" and item["id_absent_verified"] is None
                            for item in cleanup["attempts"]))

    def test_timeout_after_daemon_create_reconciles_each_resource_by_marker(self):
        for stage in ("network", "sql", "client"):
            with self.subTest(stage=stage):
                runtime, resources, _calls = self._protocol_runtime(fail_create=stage)
                owned = []
                with self.assertRaisesRegex(EngineProofError, "command_timeout"):
                    acquire_isolated_sql_runtime(
                        runtime, wheelhouse=Path("."), owned=owned,
                        expected_manifest={"proof": "a" * 64},
                    )
                self.assertEqual(owned[-1]["kind"], "network" if stage == "network" else "container")
                self.assertEqual(owned[-1]["marker"], runtime.invocation_marker)
                self.assertIsNotNone(owned[-1]["id"])
                self.assertEqual(cleanup_owned_resources(runtime, owned)["status"], "pass")
                self.assertEqual(resources, {})

    def test_daemon_unavailable_after_remove_is_cleanup_unverified(self):
        runtime, _resources, _calls = self._protocol_runtime(unavailable_after_remove=True)
        owned = []
        acquire_isolated_sql_runtime(
            runtime, wheelhouse=Path("."), owned=owned,
            expected_manifest={"proof": "a" * 64},
        )
        cleanup = cleanup_owned_resources(runtime, owned)
        self.assertEqual(cleanup["status"], "fail")
        self.assertTrue(all(item["status"] == "error" for item in cleanup["attempts"]))

    def test_pinned_driver_uses_autocommit_and_bounded_login_and_query(self):
        from types import SimpleNamespace
        from services.resume_publication_adapters import (
            PROOF_EMPTY_DATABASE, production_mssql_python_connection,
        )

        seen = []

        class PinnedConnection:
            def __init__(self, connection_str="", autocommit=False, attrs_before=None, timeout=0, **kwargs):
                seen.append((connection_str, autocommit, attrs_before, timeout, kwargs))
                self.autocommit = autocommit
                self.timeout = timeout
                self.closed = False

            def close(self):
                self.closed = True

        with patch.dict("sys.modules", {"mssql_python": SimpleNamespace(
            Connection=PinnedConnection, SQL_ATTR_LOGIN_TIMEOUT=103,
        )}):
            connection = production_mssql_python_connection(
                host="proof-sql", database=PROOF_EMPTY_DATABASE,
                user="sa", password="synthetic", timeout_seconds=30,
            )
        self.assertTrue(connection.autocommit)
        self.assertEqual(connection.timeout, 30)
        self.assertEqual(seen[0][2], {103: 30})
        self.assertEqual(seen[0][3], 30)
        self.assertEqual(seen[0][4], {})

        class IgnoringConnection(PinnedConnection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.autocommit = False
                self.timeout = 0

        with patch.dict("sys.modules", {"mssql_python": SimpleNamespace(
            Connection=IgnoringConnection, SQL_ATTR_LOGIN_TIMEOUT=103,
        )}):
            with self.assertRaisesRegex(EngineProofError, "sql_connection_not_bounded"):
                production_mssql_python_connection(
                    host="proof-sql", database=PROOF_EMPTY_DATABASE,
                    user="sa", password="synthetic", timeout_seconds=30,
                )

    def test_uncertain_create_without_authoritative_identity_stays_unverified(self):
        class Missing:
            def inspect(self, name):
                raise EngineProofError(f"docker_resource_not_found:{name}")

            def remove(self, name):
                raise AssertionError("must not remove a resource without its marker")

        cleanup = cleanup_owned_resources(
            Missing(), [{"name": "unconfirmed-net", "id": None, "marker": PROOF_ID,
                         "kind": "network", "uncertain": True}],
        )
        self.assertEqual(cleanup["status"], "fail")
        self.assertEqual(cleanup["attempts"][0]["status"], "unverified_uncertain_create")

    def test_restored_entry_stays_private_without_global_sharing_change(self):
        from services.resume_publication_adapters import capture_publication_state

        connection = _EngineConnection("docker:proof-restore-private")
        owner = seed_publication_owner(connection)["user_key"]
        execute_procedure(
            connection, "usp_CommitResumePublicationCommandForOwner",
            _commit_parameters(owner, {"request_id": "00000000-0000-4000-8000-0000000000e1",
                                       "json": _publish_json()}),
        )
        execute_procedure(
            connection, "usp_CommitResumePublicationCommandForOwner",
            _commit_parameters(owner, {"request_id": "00000000-0000-4000-8000-0000000000e2",
                                       "json": json.dumps({"type": "delete", "entry_key": PROOF_ENTRY_KEY})}),
        )
        deleted = capture_publication_state(connection)
        with self.assertRaisesRegex(RuntimeError, "52105"):
            execute_procedure(
                connection, "usp_CommitResumePublicationCommandForOwner",
                _commit_parameters(owner, {"request_id": "00000000-0000-4000-8000-0000000000e3",
                                           "json": json.dumps({"type": "restore", "entry_key": PROOF_ENTRY_KEY})}),
            )
        execute_procedure(
            connection, "usp_CommitResumePublicationCommandForOwner",
            _commit_parameters(owner, {"request_id": "00000000-0000-4000-8000-0000000000e4",
                                       "json": json.dumps({"type": "restore", "entry_key": PROOF_ENTRY_KEY,
                                                           "expected_access_revision": deleted["access_revision"]})}),
        )
        restored = capture_publication_state(connection)
        self.assertTrue(restored["sharing_enabled"])
        self.assertEqual(restored["lifecycle"], "active")
        self.assertFalse(restored["resume_display"])
        self.assertFalse(restored["visitor_ai"])
        self.assertNotIn(PROOF_ENTRY_KEY, restored["display_json"] or "")
        self.assertNotIn(PROOF_ENTRY_KEY, restored["visitor_ai_json"] or "")

    def test_invalid_correction_targets_do_not_mutate(self):
        from services.resume_publication_repository import (
            PublicationConflictError,
            PublicationDenied,
            SqlResumePublicationRepository,
        )
        from services.resume_publication_adapters import ProofDatabaseAdapter, correct_publication_wording

        identity = "docker:proof-invalid-correct"
        connection = _EngineConnection(identity)
        seed_publication_owner(connection)
        execute_procedure(
            connection,
            "usp_CommitResumePublicationCommandForOwner",
            _commit_parameters(
                connection.store["user_key"],
                {"request_id": "00000000-0000-4000-8000-0000000000c1", "json": _publish_json()},
            ),
        )
        before = connection.store["canonical_summary"]
        repository = SqlResumePublicationRepository(ProofDatabaseAdapter(connection))
        with self.assertRaises(PublicationDenied):
            repository.commit_command(
                connection.store["user_key"],
                "00000000-0000-4000-8000-0000000000d1",
                {
                    "type": "correct",
                    "entry_key": "00000000-0000-4000-8000-0000000000de",
                    "expected_content_version": 1,
                    "expected_access_revision": 2,
                    "values": {"summary": "nope", "wording": "nope", "role_title": "Lead", "employer_name": "PeerSlate"},
                },
            )
        self.assertEqual(connection.store["canonical_summary"], before)
        connection.store["lifecycle"] = "deleted"
        with self.assertRaises(PublicationDenied):
            repository.commit_command(
                connection.store["user_key"],
                "00000000-0000-4000-8000-0000000000d2",
                {
                    "type": "correct",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_content_version": 1,
                    "expected_access_revision": 2,
                    "values": {"summary": "nope", "wording": "nope", "role_title": "Lead", "employer_name": "PeerSlate"},
                },
            )
        self.assertEqual(connection.store["canonical_summary"], before)
        connection.store["lifecycle"] = "active"
        with self.assertRaises(PublicationConflictError):
            repository.commit_command(
                connection.store["user_key"],
                "00000000-0000-4000-8000-0000000000d3",
                {
                    "type": "correct",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_content_version": 99,
                    "expected_access_revision": 2,
                    "values": {"summary": "nope", "wording": "nope", "role_title": "Lead", "employer_name": "PeerSlate"},
                },
            )
        self.assertEqual(connection.store["canonical_summary"], before)
        correct_publication_wording(
            connection,
            connection.store["user_key"],
            "00000000-0000-4000-8000-0000000000c2",
            PROOF_CORRECTED_SUMMARY,
            expected_content_version=1,
            expected_access_revision=2,
        )
        self.assertEqual(connection.store["canonical_summary"], PROOF_CORRECTED_SUMMARY)
        replay = repository.commit_command(
            connection.store["user_key"],
            "00000000-0000-4000-8000-0000000000c2",
            {
                "type": "correct",
                "entry_key": PROOF_ENTRY_KEY,
                "expected_content_version": 1,
                "expected_access_revision": 2,
                "values": {
                    "summary": PROOF_CORRECTED_SUMMARY,
                    "wording": PROOF_CORRECTED_SUMMARY,
                    "role_title": "Lead",
                    "employer_name": "PeerSlate",
                },
            },
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(connection.store["canonical_summary"], PROOF_CORRECTED_SUMMARY)

    def test_command_timeout_is_classified(self):
        from services.resume_publication_adapters import _timeout_docker, PROOF_COMMAND_TIMEOUT_SECONDS

        def runner(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="docker", timeout=PROOF_COMMAND_TIMEOUT_SECONDS)

        with self.assertRaisesRegex(EngineProofError, "command_timeout"):
            _timeout_docker(runner, ["ps"], None, 1)

    def test_cancelled_docker_cli_child_is_killed_and_reaped(self):
        from services.resume_publication_adapters import _run_interruptible_docker_command

        class Child:
            def __init__(self):
                self.communications = 0
                self.killed = False

            def communicate(self, timeout):
                self.communications += 1
                if self.communications == 1:
                    raise EngineProofError("proof_cancelled")
                return "", ""

            def kill(self):
                self.killed = True

        child = Child()
        with patch("services.resume_publication_adapters.subprocess.Popen", return_value=child):
            with self.assertRaisesRegex(EngineProofError, "proof_cancelled"):
                _run_interruptible_docker_command(
                    ["docker", "network", "create"], capture_output=True,
                    text=True, check=False, env=None, timeout=30,
                )
        self.assertTrue(child.killed)
        self.assertEqual(child.communications, 2)


@unittest.skipUnless(
    AUTHORIZED,
    "Protected SQL resource run is not authorized; static adapter tests do not contact it.",
)
class ResumePublicationSqlEngineLiveTests(unittest.TestCase):
    def test_complete_migration_race_rollback_and_reader_oracles(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from scripts.run_resume_publication_sql_proof import execute_proof

        with TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence.json"
            status = execute_proof("authorized-local-oracle", evidence)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertIn(payload["status"], {"pass", "prepared_not_executed"})
        self.assertNotEqual(payload.get("client_dsn_accepted"), True)


if __name__ == "__main__":
    unittest.main()
