"""Owner-scoped persistence ports for MVP1 increment C.

Three contracts live here:

* **The store** (``load_owner`` / ``save_owner``) that both adapters satisfy.
* **The unit of work** an explicit Add or an accepted proposal commits through.
  A loop of independently committing commands is not atomic, so the service
  stages every affected canonical write and then commits the intake rows and
  the receipt once. The SQL adapter maps that to one procedure and one database
  transaction; the in-memory adapter (test-only) restores the participating
  stores on rollback.
* **The procedure dispatch**, keyed by the closed command type, so the guide,
  decision and purge operations reach their own declared procedure instead of
  every operation naming the submission procedure.

The in-memory store is process-local and test-only. The SQL adapter names
proposed procedures; schema application remains separately withheld, and every
SQL path fails closed until a reviewed, applied schema exists. Allowlisting a
procedure name is not engine proof and does not apply SQL.
"""

from __future__ import annotations

import copy
import json
import threading
import weakref
from contextlib import ExitStack, contextmanager
from functools import wraps
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from services.database_service import DatabaseServiceError, database_service


class _OwnerCompositionLocks:
    def __init__(self):
        self.intake = threading.RLock()
        self.publication = threading.RLock()
        self.draft = threading.RLock()


_OWNER_LOCKS_GUARD = threading.Lock()
_OWNER_LOCKS = weakref.WeakValueDictionary()
_REQUEST_LOCKS = weakref.WeakValueDictionary()


class _RequestLock:
    def __init__(self):
        self.lock = threading.Lock()


# How long an identical in-flight request may wait for the first one. The
# local private sites serve from a fixed pool of worker threads, so a waiter
# must give its worker back instead of holding it for a whole provider call.
REQUEST_GUARD_WAIT_SECONDS = 2.0


class ResumeRequestInProgress(Exception):
    """The same request is still being processed; the caller may replay it later."""


@contextmanager
def resume_request_guard(owner, request_id, *, wait_seconds=None):
    """Serialize one provider request across service instances, without stores.

    A duplicate waits at most ``wait_seconds`` and then raises
    ``ResumeRequestInProgress``; it never holds a worker for the whole call.
    """
    key = (type(owner), str(owner), str(request_id))
    with _OWNER_LOCKS_GUARD:
        lock = _REQUEST_LOCKS.get(key)
        if lock is None:
            lock = _RequestLock()
            _REQUEST_LOCKS[key] = lock
    wait = REQUEST_GUARD_WAIT_SECONDS if wait_seconds is None else wait_seconds
    if not lock.lock.acquire(timeout=wait):
        raise ResumeRequestInProgress()
    try:
        yield
    finally:
        lock.lock.release()


@contextmanager
def resume_owner_guard(owner):
    """One process-local composition order: intake → publication → draft.

    Only same-owner operations serialize. Store dictionary locks remain short
    internal copy/replace guards. Never hold this context across a provider
    call: snapshot first, dispatch unlocked, then re-enter and fence the result.
    This is not a database transaction or cross-process SQL qualification.
    """
    key = (type(owner), str(owner))
    with _OWNER_LOCKS_GUARD:
        locks = _OWNER_LOCKS.get(key)
        if locks is None:
            locks = _OwnerCompositionLocks()
            _OWNER_LOCKS[key] = locks
    with locks.intake, locks.publication, locks.draft:
        yield


def owner_composed(method):
    """Use the shared order at a provider-free owner service boundary."""
    @wraps(method)
    def composed(self, owner, *args, **kwargs):
        with resume_owner_guard(owner):
            return method(self, owner, *args, **kwargs)
    return composed


# Every browser procedure has the same closed three-parameter shape:
# (@UserKey, @RequestId, @CommandJson). Uniformity is what lets one dispatcher
# bind the right procedure without inventing per-operation parameter lists.
RESUME_INTAKE_BROWSER_PROCEDURES = frozenset(
    {
        "usp_GetResumeIntakeWorkspaceForOwner",
        "usp_GetResumeIntakeDurableWorkspaceForOwner",
        "usp_ReplaceResumeIntakeDraftsForOwner",
        "usp_CommitResumeIntakeExtractedSourceForOwner",
        "usp_CommitResumeIntakeSubmissionForOwner",
        "usp_CommitResumeIntakeRecordingForOwner",
        "usp_ClaimResumeIntakeRecordingForOwner",
        "usp_CommitResumeIntakeProposalDecisionForOwner",
        "usp_SetResumeGuideStatusForOwner",
        "usp_PurgeResumeIntakeSourceForOwner",
    }
)
RESUME_INTAKE_WORKER_PROCEDURES = frozenset(
    {
        "usp_ClaimResumeIntakeJobsForOwner",
        "usp_CompleteResumeIntakeJobForOwner",
        "usp_SweepExpiredResumeIntakeSources",
    }
)

# The closed command type -> declared procedure contract.
COMMAND_PROCEDURES = {
    "add_submission": "usp_CommitResumeIntakeSubmissionForOwner",
    "transcribe_recording": "usp_CommitResumeIntakeRecordingForOwner",
    "claim_recording": "usp_ClaimResumeIntakeRecordingForOwner",
    "decide_proposal": "usp_CommitResumeIntakeProposalDecisionForOwner",
    "set_guide_status": "usp_SetResumeGuideStatusForOwner",
    "purge_source": "usp_PurgeResumeIntakeSourceForOwner",
    "keep_extracted_separate": "usp_CommitResumeIntakeExtractedSourceForOwner",
}

DRAFT_COMMAND_KEYS = frozenset({"expected_revision", "expected_lifecycle_epoch", "drafts"})
EXTRACTED_SOURCE_COMMAND_KEYS = frozenset({"type", "source_binding", "submission"})

# The exact keys each declared command JSON must carry. The agreement tests
# assert the service emits precisely these, and the SQL reads precisely these.
SUBMISSION_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "submission_key",
        "submission_version",
        "entrance",
        "policy_version",
        "lifecycle_epoch",
        "request_digest",
        "sources",
        "jobs",
        "proposals",
        "results",
        "summary",
        "receipt",
        "last_receipt",
        "canonical_intents",
    }
)
RECORDING_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "client_key",
        "entrance",
        "policy_version",
        "audio_sha256",
        "byte_length",
        "content_type",
        "outcome",
        "transcript",
        "source_key",
        "source_version",
        "receipt",
        "request_digest",
        "lease_id",
        "lifecycle_epoch",
        "duration_seconds",
    }
)
RECORDING_CLAIM_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "request_digest",
        "client_key",
        "entrance",
        "policy_version",
        "lifecycle_epoch",
        "audio_sha256",
        "byte_length",
        "content_type",
        "duration_seconds",
    }
)
DECISION_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "request_digest",
        "proposal_key",
        "decision",
        "confirmed_values",
        "target_key",
        "target_content_token",
        "target_access_revision",
        "outcome",
        "receipt",
        "canonical_intents",
    }
)
PURGE_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "request_digest",
        "source_key",
        "receipt",
    }
)
GUIDE_COMMAND_KEYS = frozenset(
    {
        "type",
        "request_id",
        "request_digest",
        "status",
        "status_source",
        "receipt",
    }
)
COMMAND_KEY_SETS = {
    "add_submission": SUBMISSION_COMMAND_KEYS,
    "transcribe_recording": RECORDING_COMMAND_KEYS,
    "claim_recording": RECORDING_CLAIM_COMMAND_KEYS,
    "decide_proposal": DECISION_COMMAND_KEYS,
    "purge_source": PURGE_COMMAND_KEYS,
    "set_guide_status": GUIDE_COMMAND_KEYS,
    "keep_extracted_separate": EXTRACTED_SOURCE_COMMAND_KEYS,
}

# The two canonical boundaries an intake intent may be staged against, with the
# exact JSON contract each declared callee enforces (extracted from
# PS-RESUME-EDIT-002 and PS-RESUME-DRAFT-001 by the agreement tests).
CANONICAL_BOUNDARIES = frozenset({"living_resume", "resume_draft"})
CALLEE_PROCEDURES = {
    "living_resume": "usp_CommitLivingResumeCommandForOwner",
    "resume_draft": "usp_CommitResumeDraftCommandForOwner",
}
CALLEE_COMMAND_KEYS = {
    # PS-RESUME-EDIT-002: rejects any key outside this closed set.
    "living_resume": frozenset(
        {"command_id", "type", "record_key", "parent_key", "expected_version", "values"}
    ),
    # PS-RESUME-DRAFT-001: the drafted-values overlay command. The callee
    # replays on its canonical semantic digest and fences the shared draft
    # version, so the staged intent carries both explicitly.
    "resume_draft": frozenset(
        {
            "type",
            "record_key",
            "record_type",
            "expected_content_token",
            "expected_access_revision",
            "expected_draft_version",
            "request_digest",
            "values",
            "intended_permission_expansions",
        }
    ),
}
CALLEE_TYPE_VOCABULARY = {
    "living_resume": frozenset(
        f"{operation}_{record_type}"
        for operation in ("create", "update", "remove")
        for record_type in ("role", "accomplishment", "skill", "credential", "education")
    ),
    "resume_draft": frozenset(
        {"save_item", "discard_item", "create_private_item", "review_candidate"}
    ),
}


class ResumeIntakeStoreUnavailable(RuntimeError):
    """The intake store cannot run (unapplied schema, allowlist, or connection)."""


def empty_intake_snapshot() -> dict[str, Any]:
    return {
        "version": 0,
        "lifecycle_epoch": 0,
        "policy_version": 0,
        "submissions": {},
        "sources": {},
        "jobs": {},
        "proposals": {},
        "receipts": {},
        "guide": {},
        # Unsubmitted composer drafts live here, never in submissions,
        # sources, proposals, or canonical entries. Draft rows are private,
        # unmatched, and version-checked; the SQL read maps them only when
        # its declared procedure returns draft rows.
        "drafts": {},
    }


# ``version`` is internal bookkeeping and optional; the declared read contract
# is the state the service actually reads.
_SNAPSHOT_KEYS = frozenset(empty_intake_snapshot()) - {"version"}


def validate_snapshot(payload: object) -> dict[str, Any]:
    """Fail closed unless a read produced the full declared snapshot shape."""

    if not isinstance(payload, dict):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    if _SNAPSHOT_KEYS - set(payload):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    for name in ("lifecycle_epoch", "policy_version"):
        if not isinstance(payload[name], int) or isinstance(payload[name], bool):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    for name in ("submissions", "sources", "jobs", "proposals", "receipts", "guide", "drafts"):
        if not isinstance(payload[name], dict):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    snapshot = {key: payload[key] for key in _SNAPSHOT_KEYS}
    if "last_receipt" in payload:
        snapshot["last_receipt"] = payload["last_receipt"]
    return snapshot


def _rows(value: object) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    return value


def _json_or_none(value: object):
    if value in (None, ""):
        return None
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    try:
        return json.loads(value)
    except ValueError as error:
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.") from error


def _declared_uuid(value: object, *, nullable: bool = False) -> str | None:
    """Normalize SQL UUID representations without accepting an invalid identity."""
    if value is None and nullable:
        return None
    if not isinstance(value, (str, UUID)):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as error:
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.") from error


def map_declared_workspace(payload: object) -> dict[str, Any]:
    """Map the declared read rows onto the internal owner snapshot.

    The proposed ``usp_GetResumeIntakeWorkspaceForOwner`` returns one column,
    ``workspace_json``, holding row arrays with the column names the procedure
    declares. This is the adapter that makes the two contracts agree: the
    tests drive the real service through this exact mapping instead of a
    friendlier JSON shape the procedure never emits.
    """

    if not isinstance(payload, dict):
        raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    for name in ("lifecycle_epoch", "policy_version"):
        if not isinstance(payload.get(name), int) or isinstance(payload.get(name), bool):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
    snapshot = empty_intake_snapshot()
    snapshot["lifecycle_epoch"] = payload["lifecycle_epoch"]
    snapshot["policy_version"] = payload["policy_version"]

    guide = payload.get("guide")
    if guide is not None:
        if not isinstance(guide, dict):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        snapshot["guide"] = {
            "status": guide.get("status") or "not_started",
            "status_source": guide.get("status_source") or "default_unstarted",
        }

    for row in _rows(payload.get("submissions")):
        if not isinstance(row, dict) or not row.get("submission_key"):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        key = _declared_uuid(row["submission_key"])
        snapshot["submissions"][key] = {
            "submission_key": key,
            "version": int(row.get("version") or 1),
            "state": row.get("state") or "active",
            "entrance": row.get("entrance"),
            "policy_version": int(row.get("policy_version") or 0),
            "request_id": _declared_uuid(row.get("request_id"), nullable=True) or "",
            "request_digest": row.get("request_digest"),
            "created_at": row.get("created_at_utc"),
            "source_keys": [_declared_uuid(value) for value in _rows(row.get("source_keys"))],
            "proposal_keys": [_declared_uuid(value) for value in _rows(row.get("proposal_keys"))],
            "item_count": int(row.get("item_count") or 0),
        }

    for row in _rows(payload.get("sources")):
        if not isinstance(row, dict) or not row.get("source_key"):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        key = _declared_uuid(row["source_key"])
        snapshot["sources"][key] = {
            "source_key": key,
            "kind": row.get("kind"),
            "state": row.get("state") or "active",
            "version": int(row.get("version") or 1),
            "text": row.get("text"),
            "structured_values": _json_or_none(
                row.get("structured_values_json")
                if "structured_values_json" in row
                else row.get("structured_values")
            ),
            "content_type": row.get("content_type"),
            "byte_length": row.get("byte_length"),
            "sha256": row.get("sha256"),
            "submission_key": _declared_uuid(row.get("submission_key"), nullable=True),
            "created_at": row.get("created_at_utc"),
        }

    for row in _rows(payload.get("jobs")):
        if not isinstance(row, dict) or not row.get("job_key"):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        key = _declared_uuid(row["job_key"])
        fence = {
            "source_key": _declared_uuid(row.get("source_key"), nullable=True),
            "source_version": int(row.get("source_version") or 0),
            "submission_key": _declared_uuid(row.get("submission_key"), nullable=True),
            "submission_version": int(row.get("submission_version") or 0),
            "policy_version": int(row.get("policy_version") or 0),
            "lifecycle_epoch": int(row.get("lifecycle_epoch") or 0),
        }
        snapshot["jobs"][key] = {
            "job_key": key,
            "kind": row.get("kind"),
            "state": row.get("state") or "queued",
            "fence": fence,
            "lease_id": None,
            "attempts": int(row.get("attempts") or 0),
            "result": row.get("result"),
            "outcome": row.get("outcome"),
            "created_at": row.get("created_at_utc"),
            "updated_at": row.get("updated_at_utc"),
        }

    for row in _rows(payload.get("proposals")):
        if not isinstance(row, dict) or not row.get("proposal_key"):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        key = _declared_uuid(row["proposal_key"])
        proposed = _json_or_none(row.get("proposed_values_json")) or {}
        provided = _json_or_none(row.get("provided_fields_json"))
        clears = _json_or_none(row.get("explicit_clears_json"))
        binding = {
            "source_key": _declared_uuid(row.get("source_key"), nullable=True),
            "source_version": int(row.get("source_version") or 0),
            "submission_key": _declared_uuid(row.get("submission_key"), nullable=True),
            "submission_version": int(row.get("submission_version") or 0),
            "lifecycle_epoch": int(row.get("lifecycle_epoch") or 0),
            "policy_version": int(row.get("policy_version") or 0),
        }
        snapshot["proposals"][key] = {
            "proposal_key": key,
            "state": row.get("state") or "pending",
            "kind": row.get("kind"),
            "record_type": row.get("record_type"),
            "target_key": _declared_uuid(row.get("target_key"), nullable=True),
            "target_content_token": row.get("target_content_token"),
            "target_access_revision": row.get("target_access_revision"),
            "quote": row.get("quote"),
            "span_start": int(row.get("span_start") or 0),
            "span_end": int(row.get("span_end") or 0),
            "proposed_values": proposed,
            "provided_fields": list(provided or []),
            "explicit_clears": list(clears or []),
            "confirmed_values": _json_or_none(row.get("confirmed_values_json")),
            "requires_member_wording": bool(row.get("requires_member_wording")),
            "confidence": row.get("confidence"),
            "command_digest": row.get("command_digest"),
            "binding": binding,
            "provenance": {
                "source_key": binding["source_key"],
                "source_version": binding["source_version"],
                "span_start": int(row.get("span_start") or 0),
                "span_end": int(row.get("span_end") or 0),
            },
            "source_purged": bool(row.get("source_purged")),
            "decision": row.get("decision"),
            "decided_at": row.get("decided_at_utc"),
            "created_at": row.get("created_at_utc"),
        }

    receipts = {}
    for row in _rows(payload.get("receipts")):
        if not isinstance(row, dict) or not row.get("request_id"):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        key = _declared_uuid(row["request_id"])
        result = _json_or_none(row.get("result_json"))
        if not isinstance(result, dict):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        result = copy.deepcopy(result)
        result["request_id"] = _declared_uuid(result.get("request_id"))
        if result["request_id"] != key:
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        if isinstance(result.get("submission"), dict) and "submission_key" in result["submission"]:
            result["submission"]["submission_key"] = _declared_uuid(result["submission"]["submission_key"])
        # The row digest is the database's own command hash. The service's own
        # payload digest travels inside the stored structural result and is
        # what replay/conflict compares, so prefer it when present.
        digest = result.get("request_digest") or row.get("request_digest")
        receipts[key] = {
            "request_digest": digest,
            "submission_key": _declared_uuid(row.get("submission_key"), nullable=True),
            "result": result,
        }
    snapshot["receipts"] = receipts
    last_receipt = _json_or_none(payload.get("last_receipt_json"))
    if isinstance(last_receipt, dict):
        snapshot["last_receipt"] = last_receipt
    return snapshot


class ResumeIntakeRepository(Protocol):
    supports_atomic_source_actions: bool

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        """Return a mutable owner-scoped snapshot."""

    def save_owner(self, owner_user_key, snapshot, command=None):
        """Replace that owner's snapshot, optionally through a closed command."""

    def owner_guard(self, owner_user_key):
        """Serialize one source-bound owner mutation from read through commit."""

    def claim_recording(self, owner_user_key, request_id, payload, *, now=None):
        """Reserve one durable provider lease or return pending/replay/conflict."""

    def unit_of_work(self, draft_service=None, *, owner=None):
        """Return the transaction/unit-of-work the service commits through."""

    def with_drafts(self, owner_user_key: str, mutator, *, create: bool = False):
        """Run ``mutator`` on the live owner snapshot under the owner lock.

        The mutator may change only the drafts map. A missing owner is passed
        as ``None`` unless ``create`` is true.
        """


class InMemoryResumeIntakeRepository:
    """Process-local store. Never a live database; owners stay isolated."""

    persistence_label = "in_memory_not_live_db"
    is_live_database = False
    # Draft rows live in the snapshot section, so the in-memory store keeps
    # them with the same owner isolation as every other intake record.
    supports_drafts = True
    supports_atomic_source_actions = True
    # This snapshot adapter persists turn reservations, dependent source
    # bindings and proposal revisions together. The SQL adapter has no
    # equivalent reviewed procedure and must not inherit this capability.
    supports_resume_conversation = True
    # This snapshot store retains the first-arrival marker and its receipt
    # atomically. The closed SQL mapper/procedure does not carry that metadata.
    supports_guide_first_arrival = True

    def __init__(self) -> None:
        self._owners: dict[str, dict[str, Any]] = {}
        self._recording_claims: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.RLock()

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        with self._lock:
            existing = self._owners.get(owner_user_key)
            if existing is None:
                return empty_intake_snapshot()
            return copy.deepcopy(existing)

    def owner_guard(self, owner_user_key):
        return resume_owner_guard(owner_user_key)

    def save_owner(self, owner_user_key, snapshot, command=None):
        with self._lock:
            # Drafts use their own owner-scoped CAS path. A non-draft command
            # works from a detached snapshot that may have been loaded before a
            # newer draft save completed, so carrying that stale draft section
            # into a whole-owner replacement would acknowledge v2 and then
            # silently restore v1. Preserve the live draft map at the same lock
            # boundary as every whole-owner replacement.
            current = self._owners.get(owner_user_key)
            replacement = copy.deepcopy(snapshot)
            # Unrelated commands may have loaded their snapshot before a
            # welcome was acknowledged. Never erase that once-only frontier.
            prior_guide = (current or {}).get("guide") or {}
            if isinstance(prior_guide, dict) and "first_arrival" in prior_guide:
                guide = replacement.setdefault("guide", {})
                prior = prior_guide["first_arrival"]
                incoming = guide.get("first_arrival", {})
                if isinstance(prior, dict) and isinstance(incoming, dict):
                    merged = copy.deepcopy(prior)
                    merged.update(incoming)
                    for key, value in prior.items():
                        if value is True:
                            merged[key] = True
                    guide["first_arrival"] = merged
                else:
                    guide["first_arrival"] = copy.deepcopy(prior)
            for key, entry in ((current or {}).get("receipts") or {}).items():
                result = entry.get("result") if isinstance(entry, dict) else None
                if isinstance(result, dict) and result.get("type") == "acknowledge_guide_first_arrival":
                    receipts = replacement.setdefault("receipts", {})
                    if key in receipts and receipts[key] != entry:
                        raise ResumeIntakeStoreUnavailable("An acknowledgment request key changed.")
                    receipts[key] = copy.deepcopy(entry)
            from services.resume_guide_contract import bind_item_identities
            try:
                bind_item_identities(owner_user_key,replacement,
                    privacy_repair=bool(command and command.get('procedure') == COMMAND_PROCEDURES['purge_source']))
            except (ValueError,TypeError,KeyError) as error:
                raise ResumeIntakeStoreUnavailable("Guide item identity could not be preserved") from error
            if command is not None:
                replacement["drafts"] = copy.deepcopy(
                    (current or {}).get("drafts") or {}
                )
                if 'draft_revision' in (current or {}):
                    replacement['draft_revision'] = current['draft_revision']
                if command.get('procedure') == COMMAND_PROCEDURES['purge_source']:
                    # Redact the current acknowledged draft at commit, rather
                    # than restoring a detached older draft. This does not
                    # repeat the source/proposal lifecycle mutations.
                    from services.resume_intake_proposals import redact_source_drafts
                    redact_source_drafts(replacement, command['payload']['source_key'])
            if (
                isinstance(command, dict)
                and command.get("procedure") == COMMAND_PROCEDURES["transcribe_recording"]
            ):
                payload = command.get("payload") or {}
                key = (str(owner_user_key), str(command.get("request_id")))
                claim = self._recording_claims.get(key)
                current = current or empty_intake_snapshot()
                bindings = {
                    "request_digest": payload.get("request_digest"),
                    "lease_id": payload.get("lease_id"),
                    "source_key": payload.get("source_key"),
                    "entrance": payload.get("entrance"),
                    "policy_version": payload.get("policy_version"),
                    "lifecycle_epoch": payload.get("lifecycle_epoch"),
                    "audio_sha256": payload.get("audio_sha256"),
                    "byte_length": payload.get("byte_length"),
                    "content_type": payload.get("content_type"),
                    "duration_seconds": payload.get("duration_seconds"),
                }
                if (
                    not claim
                    or claim.get("state") != "leased"
                    or any(claim.get(name) != value for name, value in bindings.items())
                    or int(current.get("lifecycle_epoch") or 0)
                    != int(claim.get("lifecycle_epoch") or 0)
                    or int(current.get("policy_version") or 0)
                    != int(claim.get("policy_version") or 0)
                    or datetime.now(timezone.utc)
                    >= datetime.fromisoformat(claim["lease_expires_at"])
                ):
                    raise ResumeIntakeStoreUnavailable(
                        "The recording claim changed before finalization."
                    )
                self._owners[owner_user_key] = replacement
                claim["state"] = "completed"
                claim["completed_at"] = datetime.now(timezone.utc).isoformat()
                return None
            self._owners[owner_user_key] = replacement
            return None

    def with_drafts(self, owner_user_key: str, mutator, *, create: bool = False):
        """Owner-scoped draft CAS against current owner state."""

        with resume_owner_guard(owner_user_key), self._lock:
            existing = self._owners.get(owner_user_key)
            if existing is None:
                if not create:
                    return mutator(None)
                existing = empty_intake_snapshot()
                self._owners[owner_user_key] = existing
            existing.setdefault("drafts", {})
            # Capture legacy row versions BEFORE expiry/discard can remove the
            # only evidence of their high-water mark. Reads do not advance it.
            revision = max(int(existing.get('draft_revision') or 0),
                max((int(row.get('version') or 0) for row in existing['drafts'].values()), default=0))
            if revision:
                existing['draft_revision'] = revision
            result = mutator(existing)
            revision = max(int(existing.get('draft_revision') or 0),
                max((int(row.get('version') or 0) for row in existing['drafts'].values()),default=0))
            if revision:
                existing['draft_revision'] = revision
            return result

    def claim_recording(self, owner_user_key, request_id, payload, *, now=None):
        moment = now or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        moment = moment.astimezone(timezone.utc)
        key = (str(owner_user_key), str(request_id))
        digest = payload.get("request_digest")
        with resume_owner_guard(owner_user_key), self._lock:
            snapshot = self._owners.get(owner_user_key) or empty_intake_snapshot()
            receipt = (snapshot.get("receipts") or {}).get(str(request_id))
            if receipt is not None:
                if receipt.get("request_digest") != digest:
                    return {"outcome": "conflict", "request_digest": digest}
                return {
                    "outcome": "replay",
                    "request_digest": digest,
                    "result": copy.deepcopy(receipt.get("result")),
                }
            existing = self._recording_claims.get(key)
            binding_names = (
                "request_digest", "client_key", "entrance", "policy_version",
                "lifecycle_epoch", "audio_sha256", "byte_length", "content_type",
                "duration_seconds",
            )
            if existing is not None:
                if any(existing.get(name) != payload.get(name) for name in binding_names):
                    return {"outcome": "conflict", "request_digest": digest}
                expires = datetime.fromisoformat(existing["lease_expires_at"])
                if existing.get("state") == "leased" and moment >= expires:
                    existing["state"] = "recovery_required"
                return {
                    "outcome": "pending",
                    "request_digest": digest,
                    "recovery_required": existing.get("state") != "leased",
                    "lease_expires_at": existing["lease_expires_at"],
                }
            if int(snapshot.get("lifecycle_epoch") or 0) != int(payload["lifecycle_epoch"]):
                return {"outcome": "conflict", "request_digest": digest}
            claim = {name: payload.get(name) for name in binding_names}
            claim.update(
                {
                    "state": "leased",
                    "lease_id": str(uuid4()),
                    "source_key": str(uuid4()),
                    "lease_expires_at": (moment + timedelta(minutes=5)).isoformat(),
                }
            )
            self._recording_claims[key] = claim
            claimed_snapshot = copy.deepcopy(snapshot)
            claimed_snapshot["policy_version"] = int(payload["policy_version"])
            self._owners[owner_user_key] = claimed_snapshot
            return {
                "outcome": "claimed",
                "request_digest": digest,
                "lease_id": claim["lease_id"],
                "source_key": claim["source_key"],
                "lease_expires_at": claim["lease_expires_at"],
            }

    def unit_of_work(self, draft_service=None, *, owner=None):
        return InMemoryIntakeUnitOfWork(self, draft_service, owner=owner)

    def _restore(
        self, owners: dict[str, dict[str, Any]], *, preserve_live_drafts: bool = False
    ) -> None:
        with self._lock:
            restored = copy.deepcopy(owners)
            if preserve_live_drafts:
                for owner_user_key, current in self._owners.items():
                    target = restored.setdefault(owner_user_key, empty_intake_snapshot())
                    target["drafts"] = copy.deepcopy(current.get("drafts") or {})
            self._owners = restored


class InMemoryIntakeUnitOfWork:
    """Test-only unit of work over the participating in-memory stores.

    Every store the member action touches is snapshotted when the block opens
    and restored on rollback, so an injected failure at any point leaves no
    canonical fact, no source, no job, no proposal and no receipt behind.
    """

    def __init__(self, repository: InMemoryResumeIntakeRepository, draft_service, *, owner=None) -> None:
        self.repository = repository
        self.draft_service = draft_service
        self.owner = owner
        self._intake_state = None
        self._draft_state = None
        self._catalog_state = None
        self._catalog_store = None
        self._publication_state = None
        self._publication_store = None
        self._touched_owners = set()
        self.supports_atomic_composition = False
        self._draft_lock = None
        self._locks = ExitStack()

    def __enter__(self):
        try:
            return self._enter()
        except BaseException:
            self._locks.close()
            raise

    def _enter(self):
        if not isinstance(self.owner, str) or not self.owner.strip():
            raise ResumeIntakeStoreUnavailable("An owner-bound transaction is required.")
        self._locks.enter_context(resume_owner_guard(self.owner))
        if self.draft_service is not None:
            draft_repository = getattr(self.draft_service, "repository", None)
            catalog = getattr(self.draft_service, "catalog", None)
            publication = getattr(getattr(catalog, "policy", None), "publication_service", None)
            if publication is not None:
                from services.resume_publication_repository import InMemoryResumePublicationRepository
                publication_store = getattr(publication, "repository", None)
                if type(publication_store) is not InMemoryResumePublicationRepository:
                    raise ResumeIntakeStoreUnavailable("Atomic publication storage is unavailable. Your input is kept.")
                self._publication_store = publication_store
                self._publication_state = self._owner_state(publication_store)
                # Media lifecycle and bound-media locks precede the draft store,
                # matching Publish and every media command (no cross-owner ABBA).
                try:
                    self._locks.enter_context(publication._memory_media_locks())
                except Exception as error:
                    raise ResumeIntakeStoreUnavailable(
                        "Atomic media storage is unavailable. Your input is kept.") from error
            if draft_repository is not None:
                from services.resume_draft_repository import InMemoryResumeDraftRepository
                if isinstance(draft_repository, InMemoryResumeDraftRepository):
                    self._draft_lock = True
                    # The pure apply/rollback phase also coordinates with
                    # incumbent media writers using this store's short lock.
                    self._locks.enter_context(draft_repository._lock)
                self._draft_state = self._owner_state(draft_repository)
            if catalog is not None:
                from services.resume_draft_repository import InMemoryCanonicalCatalog
                if isinstance(catalog, InMemoryCanonicalCatalog):
                    self._catalog_store = catalog
                else:
                    from services.entry_policy_repository import InMemoryEntryPolicyRepository
                    policy_store = getattr(getattr(catalog, 'policy', None), 'repository', None)
                    if isinstance(policy_store, InMemoryEntryPolicyRepository):
                        self._catalog_store = policy_store
                if self._catalog_store is not None:
                    self._catalog_state = self._owner_state(self._catalog_store)
                    self.supports_atomic_composition = self._draft_lock is not None
        with self.repository._lock:
            self._intake_state = self._owner_state(self.repository)
        return self

    def _owner_state(self, store):
        owners = getattr(store, "_owners", {})
        return {self.owner: copy.deepcopy(owners[self.owner])} if self.owner in owners else {}

    def _touch_owner(self, owner):
        if owner != self.owner:
            raise ResumeIntakeStoreUnavailable("A transaction cannot cross owners.")
        self._touched_owners.add(owner)

    def apply_canonical(self, owner, payload, projected):
        if self.draft_service is None:
            raise ResumeIntakeStoreUnavailable("Resume drafts are unavailable.")
        self._touch_owner(owner)
        result = self.draft_service.commit(owner, payload)
        return result.get("item") or projected

    def stamp_resume_choice(self, owner, request_id, request_digest):
        if not self.supports_atomic_composition:
            raise ResumeIntakeStoreUnavailable("Private Resume choices are unavailable.")
        self._touch_owner(owner)
        self.draft_service.stamp_private_resume_choice(owner, request_id, request_digest)

    def save_guide_references(self, owner, **command):
        if not self.supports_atomic_composition:
            raise ResumeIntakeStoreUnavailable("Private Resume references are unavailable.")
        self._touch_owner(owner)
        self.draft_service.save_private_guide_references(owner,**command)

    def apply_canonical_command(self, owner, payload, projected, *, boundary, request_id,
                                callee_command):
        """The in-memory path really runs B's Python service orchestration."""

        return {
            "item": self.apply_canonical(owner, payload, projected),
            "values_source": "canonical_read",
        }

    def commit(self, owner, snapshot, *, procedure=None, request_id=None, payload=None):
        self._touch_owner(owner)
        command = None
        if procedure is not None:
            command = {
                "procedure": procedure,
                "request_id": request_id,
                "payload": payload,
            }
        self.repository.save_owner(owner, snapshot, command)
        return None

    def rollback(self) -> None:
        if self._intake_state is not None:
            with self.repository._lock:
                for owner in self._touched_owners:
                    live_drafts = copy.deepcopy((self.repository._owners.get(owner) or {}).get('drafts') or {})
                    live_revision = int((self.repository._owners.get(owner) or {}).get('draft_revision') or 0)
                    if owner in self._intake_state:
                        self.repository._owners[owner] = copy.deepcopy(self._intake_state[owner])
                        self.repository._owners[owner]['drafts'] = live_drafts
                        if live_revision:
                            self.repository._owners[owner]['draft_revision'] = live_revision
                    else:
                        self.repository._owners.pop(owner, None)
        if self.draft_service is not None:
            draft_repository = getattr(self.draft_service, "repository", None)
            catalog = getattr(self.draft_service, "catalog", None)
            if draft_repository is not None and self._draft_state is not None:
                self._restore_owners(draft_repository, self._draft_state)
            if self._catalog_store is not None and self._catalog_state is not None:
                self._restore_owners(self._catalog_store, self._catalog_state)
            if self._publication_store is not None and self._publication_state is not None:
                self._restore_owners(self._publication_store, self._publication_state)

    def _restore_owners(self, store, before):
        for owner in self._touched_owners:
            if owner in before:
                store._owners[owner] = copy.deepcopy(before[owner])
            else:
                store._owners.pop(owner, None)

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is not None:
                self.rollback()
        finally:
            self._locks.close()
        return False


class SqlResumeIntakeRepository:
    """Owner procedures including the separately governed Intake002 boundary."""

    persistence_label = "sql_proposed_unapplied"
    is_live_database = True
    # Capabilities describe the closed adapter contract, not an applied schema.
    # Missing procedures or malformed results still fail closed on every call.
    supports_drafts = True
    supports_atomic_source_actions = True

    def __init__(self, database=None) -> None:
        self.database = database or database_service
        # This process lock avoids redundant local work. SQL owner/source locks
        # and revision/lifecycle CAS enforce correctness across workers; the
        # adapter still fails closed until the separately governed schema exists.
        self._owner_mutation_lock = threading.RLock()

    def owner_guard(self, owner_user_key):
        return resume_owner_guard(owner_user_key)

    def load_owner(self, owner_user_key: str) -> dict[str, Any]:
        try:
            rows = self.database.first_result(
                "usp_GetResumeIntakeDurableWorkspaceForOwner",
                [("@UserKey", owner_user_key)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake storage is unavailable."
            ) from error
        # The declared read returns exactly one row with one nvarchar(max)
        # column. Zero rows, a wrong shape, or unparseable JSON is a read
        # failure -- never an empty member.
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        raw = rows[0].get("workspace_json")
        if not isinstance(raw, str) or not raw:
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        try:
            parsed = json.loads(raw)
        except ValueError as error:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake storage is unavailable."
            ) from error
        if (not isinstance(parsed, dict) or type(parsed.get("draft_revision")) is not int
                or parsed["draft_revision"] < 0 or not isinstance(parsed.get("drafts"), dict)):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        drafts = parsed["drafts"]
        if set(drafts) - {"composer"}:
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        if drafts:
            row = drafts["composer"]
            if (not isinstance(row, dict) or row.get("draft_key") != "composer"
                    or set(row) != {"draft_key", "version", "state", "text", "items", "attachments",
                                    "created_at", "updated_at", "expires_at", "last_request_id"}
                    or type(row.get("version")) is not int
                    or not 1 <= row["version"] <= parsed["draft_revision"]
                    or row.get("state") != "active"
                    or (row.get("text") is not None and not isinstance(row.get("text"), str))
                    or not isinstance(row.get("items"), list)
                    or not isinstance(row.get("attachments"), list)
                    or not isinstance(row.get("last_request_id"), str)):
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        if drafts:
            try:
                UUID(row["last_request_id"])
                for key in ("created_at", "updated_at", "expires_at"):
                    if row[key] is not None:
                        timestamp = datetime.fromisoformat(row[key].replace("Z", "+00:00"))
                        if timestamp.tzinfo is None:
                            raise ValueError("missing timezone")
                    elif key != "expires_at":
                        raise ValueError("missing timestamp")
            except (ValueError, TypeError, AttributeError) as error:
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.") from error
        snapshot = map_declared_workspace(parsed)
        snapshot["drafts"] = copy.deepcopy(drafts)
        snapshot["draft_revision"] = parsed["draft_revision"]
        return snapshot

    def save_owner(self, owner_user_key, snapshot, command=None):
        if not isinstance(command, dict):
            raise ResumeIntakeStoreUnavailable(
                "Resume intake writes use the closed owner-scoped command procedures."
            )
        procedure = command.get("procedure")
        request_id = command.get("request_id")
        payload = command.get("payload")
        if procedure not in RESUME_INTAKE_BROWSER_PROCEDURES or not request_id:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake writes use the closed owner-scoped command procedures."
            )
        return self.commit_command(owner_user_key, procedure, request_id, payload)

    def with_drafts(self, owner_user_key: str, mutator, *, create: bool = False):
        # Only an explicit CAS conflict is retried. A failed/lost reply is
        # uncertain and returns unavailable; the member's request-id retry
        # recovers the stored draft without blindly repeating a side effect.
        for _attempt in range(2):
            snapshot = self.load_owner(owner_user_key)
            before = copy.deepcopy(snapshot)
            result = mutator(snapshot)
            if {k: v for k, v in snapshot.items() if k != "drafts"} != {
                    k: v for k, v in before.items() if k != "drafts"}:
                raise ResumeIntakeStoreUnavailable("A draft command may change only drafts.")
            if snapshot["drafts"] == before["drafts"]:
                return result
            request_id = str(uuid4())
            payload = {"expected_revision": before["draft_revision"],
                       "expected_lifecycle_epoch": before["lifecycle_epoch"],
                       "drafts": snapshot["drafts"]}
            try:
                sets = self.database.execute_procedure(
                    "usp_ReplaceResumeIntakeDraftsForOwner",
                    [("@UserKey", owner_user_key), ("@RequestId", request_id),
                     ("@CommandJson", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
                )
            except (DatabaseServiceError, ValueError) as error:
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.") from error
            non_empty = [rows for rows in sets if rows] if isinstance(sets, list) else []
            if (not non_empty or not isinstance(non_empty[-1], list) or len(non_empty[-1]) != 1
                    or not isinstance(non_empty[-1][0], dict)):
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
            row = non_empty[-1][0]
            # SQL uniqueidentifier text casing is not an identity change.
            # Normalize the response UUID while retaining the exact request fence.
            returned_request_id = _declared_uuid(row.get("request_id"))
            if returned_request_id != request_id or row.get("outcome") not in {"applied", "conflict"}:
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
            if row["outcome"] == "applied":
                if type(row.get("revision")) is not int or row["revision"] != before["draft_revision"] + 1:
                    raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
                return result
        raise ResumeIntakeStoreUnavailable("The draft changed while saving. Your input is retained.")

    def claim_recording(self, owner_user_key, request_id, payload, *, now=None):
        command_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        try:
            result_sets = self.database.execute_procedure(
                COMMAND_PROCEDURES["claim_recording"],
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", command_json),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake storage is unavailable."
            ) from error
        if not isinstance(result_sets, list):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        non_empty = [rows for rows in result_sets if rows]
        if not non_empty or len(non_empty[-1]) != 1 or not isinstance(non_empty[-1][0], dict):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        row = non_empty[-1][0]
        outcome = row.get("outcome")
        digest = row.get("request_digest")
        if outcome not in {"claimed", "pending", "replay", "conflict"} or digest != payload.get(
            "request_digest"
        ):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        result = {"outcome": outcome, "request_digest": digest}
        if outcome == "claimed":
            if not row.get("lease_id") or not row.get("source_key"):
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
            try:
                lease_id = str(UUID(str(row["lease_id"])))
                source_key = str(UUID(str(row["source_key"])))
            except (TypeError, ValueError, AttributeError) as error:
                raise ResumeIntakeStoreUnavailable(
                    "Resume intake storage is unavailable."
                ) from error
            result.update(
                lease_id=lease_id, source_key=source_key,
                lease_expires_at=row.get("lease_expires_at_utc"),
            )
        elif outcome == "pending":
            result.update(
                recovery_required=bool(row.get("recovery_required")),
                lease_expires_at=row.get("lease_expires_at_utc"),
            )
        elif outcome == "replay":
            stored = _json_or_none(row.get("result_json"))
            if (
                not isinstance(stored, dict)
                or stored.get("request_id") != str(request_id)
                or stored.get("request_digest") != digest
            ):
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
            result["result"] = stored
        return result

    def commit_command(self, owner_user_key, procedure, request_id, payload):
        if procedure not in RESUME_INTAKE_BROWSER_PROCEDURES:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake writes use the closed owner-scoped command procedures."
            )
        command_json = payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )
        try:
            result_sets = self.database.execute_procedure(
                procedure,
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", command_json),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake storage is unavailable."
            ) from error
        # Every declared write ends with one closed commit result. Nested
        # canonical procedures may emit earlier result sets, so inspect the
        # final non-empty set rather than assuming the first belongs to C.
        if not isinstance(result_sets, list):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        non_empty = [rows for rows in result_sets if rows]
        if not non_empty or not isinstance(non_empty[-1], list) or len(non_empty[-1]) != 1:
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        row = non_empty[-1][0]
        if not isinstance(row, dict) or row.get("committed") not in (True, 1):
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        replayed = row.get("replayed")
        digest = row.get("request_digest")
        if replayed not in (False, True, 0, 1) or not isinstance(digest, str) or len(digest) != 64:
            raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        result = None
        receipt_request_id = _declared_uuid(request_id)
        if bool(replayed):
            result = _json_or_none(row.get("result_json"))
            if isinstance(result, dict):
                result = copy.deepcopy(result)
            if procedure == COMMAND_PROCEDURES["keep_extracted_separate"]:
                receipt_request_id = _declared_uuid(row.get("receipt_request_id"))
                body = json.loads(payload) if isinstance(payload, str) else payload
                override_key = _declared_uuid((body.get("source_binding") or {}).get("override_key"))
                if not isinstance(result, dict) or not isinstance(result.get("submission"), dict):
                    raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
                result["submission"]["submission_key"] = _declared_uuid(result["submission"].get("submission_key"))
                if result["submission"]["submission_key"] != override_key:
                    raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
            if isinstance(result, dict):
                result["request_id"] = _declared_uuid(result.get("request_id"))
            if (
                not isinstance(result, dict)
                or result.get("request_id") != receipt_request_id
                or result.get("request_digest") != digest
            ):
                raise ResumeIntakeStoreUnavailable("Resume intake storage is unavailable.")
        return {
            "committed": True,
            "replayed": bool(replayed),
            "request_digest": digest,
            "result": result,
            "receipt_request_id": receipt_request_id,
        }

    def unit_of_work(self, draft_service=None, *, owner=None):
        return SqlIntakeUnitOfWork(self)


class SqlIntakeUnitOfWork:
    """One database transaction, expressed as staged canonical intents.

    The canonical writes cannot be applied one at a time from the application:
    that is the split the assignment names. Instead the intents travel inside
    the single closed command the declared procedure commits, so the database
    applies canonical rows, sources, jobs, proposals and the receipt in one
    transaction (``SET XACT_ABORT ON`` plus nested procedure calls).
    """

    def __init__(self, repository: SqlResumeIntakeRepository) -> None:
        self.repository = repository
        self.intents: list[dict[str, Any]] = []

    def __enter__(self):
        self.intents = []
        return self

    def apply_canonical(self, owner, payload, projected):
        # The SQL path never runs Python canonical code: the staged intent
        # carries the *callee's own* declared command for the right boundary,
        # and the declared procedure executes it inside the same transaction.
        raise ResumeIntakeStoreUnavailable(
            "SQL canonical intents are staged through apply_canonical_command."
        )

    def apply_canonical_command(self, owner, payload, projected, *, boundary, request_id,
                                callee_command):
        if boundary not in CANONICAL_BOUNDARIES:
            raise ResumeIntakeStoreUnavailable("Unknown canonical boundary.")
        if not isinstance(callee_command, dict):
            raise ResumeIntakeStoreUnavailable("A canonical command is required.")
        self.intents.append(
            {
                "boundary": boundary,
                "request_id": request_id,
                "procedure": CALLEE_PROCEDURES[boundary],
                "command": callee_command,
            }
        )
        return {"item": projected, "values_source": "member_supplied"}

    def commit(self, owner, snapshot, *, procedure=None, request_id=None, payload=None):
        if procedure not in RESUME_INTAKE_BROWSER_PROCEDURES or not request_id:
            raise ResumeIntakeStoreUnavailable(
                "Resume intake writes use the closed owner-scoped command procedures."
            )
        body = dict(payload or {})
        # Only the two procedures that stage canonical writes receive the
        # intents array; the recording, purge and guide commands declare their
        # own exact key sets.
        if procedure in {
            COMMAND_PROCEDURES["add_submission"],
            COMMAND_PROCEDURES["decide_proposal"],
        }:
            body["canonical_intents"] = list(self.intents)
        elif procedure == COMMAND_PROCEDURES["keep_extracted_separate"]:
            submission = dict(body.get("submission") or {})
            submission["canonical_intents"] = list(self.intents)
            body["submission"] = submission
        return self.repository.commit_command(owner, procedure, request_id, body)

    def rollback(self) -> None:
        self.intents = []

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            self.rollback()
        return False
