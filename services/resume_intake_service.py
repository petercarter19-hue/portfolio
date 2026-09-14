"""Composer intake: explicit Add, provenance, versions, idempotency, receipts.

MVP1 increment C. One owner-scoped composer accepts typed text, an in-field
microphone recording and document attachments together. Nothing is processed
until the member presses Add, and Add produces an immutable submission with
truthful per-item receipts: unambiguous member-supplied facts are saved
privately, extraction or inferred wording becomes a pending proposal that
needs the member's own decision, and a refused document or recording is a
*validation* result -- distinct from a persistence failure, which aborts the
whole member action.

Atomicity: every member action runs inside a unit of work
(``repository.unit_of_work``). Canonical draft commands are staged through that
unit, and the intake rows, sources, jobs, proposals and receipt commit once. If
anything fails, the unit rolls back, so no canonical fact can survive without
its receipt and no retry can turn a committed write into a spurious proposal.
The in-memory unit of work is test-only; the SQL unit of work is one database
transaction.

Field intent: a partial member change carries only the fields the member
actually supplied, plus an explicit ``explicit_clears`` list. Unspecified
fields stay absent so an overlay merge cannot blank values the member never
touched, while an explicit clear still works.

In-memory persistence is test-only. No schema is applied and no production
flag is enabled here.
"""

from __future__ import annotations

import hashlib
import json
import copy
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from services.living_resume_editor_service import (
    LivingResumeEditorValidationError,
    normalize_editor_intent,
    normalize_editor_values,
    utf16_length,
)
from services.resume_draft_repository import (
    CanonicalReadUnavailable,
    ResumeDraftStoreUnavailable,
)
from services.resume_draft_service import (
    ResumeDraftConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftService,
    ResumeDraftUnavailableError,
    ResumeDraftValidationError,
    resume_draft_service,
)
from services.resume_intake_document_adapter import (
    DocumentIntakeError,
    ResumeDocumentAdapter,
    resume_document_adapter,
)
from services.my_data_extraction_adapter import (
    ExtractionError,
    MyDataExtractionAdapter,
)
from services.resume_intake_jobs import (
    JobFence,
    complete as complete_job,
    enqueue,
    fail as fail_job,
    invalidate_for_source as invalidate_jobs_for_source,
    lease as lease_job,
    present as present_job,
)
from services.resume_intake_policy import (
    ENTRANCE_RESUME_ONBOARDING,
    IntakePolicy,
    resolve_policy,
)
from services.resume_intake_proposals import (
    ProposalError,
    ProposalSpec,
    create as create_proposal,
    decide as decide_proposal_record,
    invalidate_for_source as invalidate_proposals_for_source,
    invalidate_for_target as invalidate_proposals_for_target,
    present as present_proposal,
    redact_source_text,
)
from services.resume_intake_repository import (
    COMMAND_PROCEDURES,
    InMemoryResumeIntakeRepository,
    ResumeIntakeStoreUnavailable,
    empty_intake_snapshot,
    validate_snapshot,
)
from services.resume_intake_transcription_adapter import (
    RecordingIntakeError,
    ResumeTranscriptionAdapter,
    resume_transcription_adapter,
)


COMMAND_TYPES = frozenset(
    {"add_submission", "decide_proposal", "purge_source", "transcribe_recording"}
)
STRUCTURED_RECORD_TYPES = frozenset(
    {"role", "education", "credential", "skill", "accomplishment"}
)
FORBIDDEN_CLIENT_FIELDS = frozenset(
    {
        "owner_user_key",
        "owner_profile_id",
        "user_key",
        "table",
        "bypass",
        "visibility",
        "approval_status",
        "publication_status",
        "resume_display",
        "visitor_ai",
    }
)
MAX_TEXT_UNITS = 20_000

# One unsubmitted composer draft per owner. Draft rows are private input
# evidence: never matched, never shared, never canonical until Add.
DRAFT_KEY = "composer"
DRAFT_MAX_ITEMS = 25
DRAFT_MAX_ATTACHMENTS = 25

# The closed editable field set per record type. Client-supplied keys must be
# inside it; an explicit clear must name one of them, never a fabricated key.
EDITOR_FIELDS = {
    "role": frozenset(
        {
            "role_title",
            "employer_name",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
            "employment_type",
            "current_role",
        }
    ),
    "education": frozenset(
        {
            "title",
            "institution_name",
            "degree_name",
            "field_of_study",
            "education_status",
            "grade_text",
            "location_text",
            "summary",
            "start_date",
            "end_date",
            "date_precision",
        }
    ),
    "credential": frozenset(
        {
            "name",
            "issuer",
            "identifier",
            "issue_date",
            "expiration_date",
            "verification_url",
            "completion_status",
        }
    ),
    "skill": frozenset({"name", "summary"}),
    "accomplishment": frozenset({"wording", "metric_value", "metric_label"}),
}
BOOLEAN_FIELDS = frozenset({"current_role"})
_SUBJECT_FIELDS = {
    "role": "role_title",
    "education": "title",
    "credential": "name",
    "skill": "name",
    "accomplishment": "wording",
}
def _eligible_accomplishment_parent(item):
    """Mirror EDIT-002's owner-scoped private draft role predicate.

    The canonical reader exposes that complete SQL predicate as ``editable``;
    ``save_mode=canonical`` is its service translation. Reader rows are already
    owner-qualified and exclude inactive or deleted entities.
    """

    return bool(
        isinstance(item, dict)
        and item.get("record_type") == "role"
        and item.get("editable") is True
        and item.get("save_mode") == "canonical"
        and not item.get("orphaned")
    )


class ResumeIntakeValidationError(ValueError):
    code = "invalid"


class ResumeIntakePolicyError(RuntimeError):
    code = "policy_not_selected"


class ResumeIntakeConflictError(Exception):
    def __init__(self, error_code, conflicts=None, message="That request conflicts.", proposed=None):
        super().__init__(message)
        self.error_code = error_code
        self.code = error_code
        self.conflicts = list(conflicts or [])
        self.proposed = proposed


class ResumeIntakeNotFoundError(Exception):
    """Neutral missing-or-foreign result. Never distinguishes another member."""

    code = "not_found"


class ResumeIntakeUnavailableError(Exception):
    def __init__(self, message="The composer is unavailable.", proposed=None):
        super().__init__(message)
        self.code = "unavailable"
        self.proposed = proposed


def _utc(now):
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_digest(payload) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _as_uuid(value, *, field):
    if not isinstance(value, str):
        raise ResumeIntakeValidationError(f"Invalid {field}.")
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as error:
        raise ResumeIntakeValidationError(f"Invalid {field}.") from error
    return str(parsed)


def _text(value, *, field, maximum=MAX_TEXT_UNITS, required=False):
    if value is None:
        if required:
            raise ResumeIntakeValidationError(f"Invalid {field}.")
        return None
    if not isinstance(value, str):
        raise ResumeIntakeValidationError(f"Invalid {field}.")
    cleaned = value.strip()
    if required and not cleaned:
        raise ResumeIntakeValidationError(f"Invalid {field}.")
    if utf16_length(cleaned) > maximum:
        raise ResumeIntakeValidationError(f"Invalid {field}.")
    return cleaned or None


def _normalized_subject(value):
    if not isinstance(value, str):
        return ""
    keep = [c.lower() for c in value if c.isalnum() or c.isspace()]
    return "".join(keep).split() and " ".join("".join(keep).split()) or ""


def _subject(record_type, values):
    name = _SUBJECT_FIELDS.get(record_type)
    raw = values.get(name) if name else None
    return raw.strip() if isinstance(raw, str) and raw.strip() else ""


def _empty_value(field_name):
    """The closed empty representation for one field."""

    return False if field_name in BOOLEAN_FIELDS else None


def _meaningful(value) -> bool:
    """True when a value actually carries member-supplied content."""

    return value not in (None, "", False)


def _stable_key(*parts) -> str:
    """Derive a stable UUID from stable inputs (retry-safe key derivation)."""

    digest = hashlib.sha256(":".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return str(UUID(digest[:32]))


@dataclass
class _ItemPlan:
    client_key: str
    kind: str
    record_type: str
    provided_values: dict = dataclass_field(default_factory=dict)
    explicit_clears: list = dataclass_field(default_factory=list)
    source_text: str | None = None
    quote: str | None = None
    confidence: str = "certain"
    document: dict | None = None
    prepared: dict | None = None
    reuse_source_key: str | None = None
    parent_key: str | None = None
    # Explicit member override: save as a separate fact without matching.
    # Only ever set from the member's own Keep-as-separate decision on a
    # duplicate receipt, never inferred.
    as_separate: bool = False


class ResumeIntakeService:
    def __init__(
        self,
        repository=None,
        draft_service: ResumeDraftService | None = None,
        document_adapter: ResumeDocumentAdapter | None = None,
        transcription_adapter: ResumeTranscriptionAdapter | None = None,
        policy: IntakePolicy | None = None,
        interpreter=None,
        document_pipeline=None,
        extraction_adapter: MyDataExtractionAdapter | None = None,
        matching_exclusions=None,
    ) -> None:
        self.repository = repository or InMemoryResumeIntakeRepository()
        self.draft_service = draft_service or resume_draft_service
        self.document_adapter = document_adapter or resume_document_adapter
        self.transcription_adapter = transcription_adapter or resume_transcription_adapter
        self._policy = policy
        self._interpreter = interpreter or self._default_interpreter
        # Strict Luna extraction for free-text kinds. None keeps the
        # deterministic uncertain default, so manual entry works with no
        # provider at all. A configured adapter that fails never falls back
        # to another model or effort: the failure stays visible and retryable.
        self._extraction_adapter = extraction_adapter
        # Callable(owner) -> container of canonical record keys excluded from
        # private matching. None means the exclusion source is unwired, so a
        # configured adapter compares against an empty shortlist rather than
        # risk comparing member material the member excluded from private AI.
        self._matching_exclusions = matching_exclusions
        # Deterministic parser seam. Tests inject a recorder that asserts the
        # exact bytes it received; production leaves it None (the shared seam).
        self._document_pipeline = document_pipeline
        # A same-process duplicate recording request must not reach a paid or
        # privacy-sensitive provider twice while its first receipt is still
        # being committed. SQL remains the durable winner across processes;
        # this keyed guard closes the source-level race inside one app process.
        self._recording_locks_guard = threading.Lock()
        self._recording_locks = {}

    # -- policy ---------------------------------------------------------

    def policy(self) -> IntakePolicy:
        return self._policy or resolve_policy(ENTRANCE_RESUME_ONBOARDING)

    def _require_usable_policy(self, *, allow_fixture):
        policy = self.policy()
        if policy.fixture_only and not allow_fixture:
            raise ResumeIntakePolicyError(
                "Resume onboarding limits and retention are not selected yet."
            )
        return policy

    # -- store ----------------------------------------------------------

    def _load(self, owner):
        try:
            snapshot = self.repository.load_owner(owner)
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error
        if not snapshot:
            snapshot = empty_intake_snapshot()
        try:
            return validate_snapshot(snapshot)
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error

    def _unit_of_work(self):
        return self.repository.unit_of_work(self.draft_service)

    @contextmanager
    def _recording_request_lock(self, owner, request_id):
        key = (str(owner), str(request_id))
        with self._recording_locks_guard:
            state = self._recording_locks.get(key)
            if state is None:
                state = {"lock": threading.Lock(), "users": 0}
                self._recording_locks[key] = state
            state["users"] += 1
        try:
            with state["lock"]:
                yield
        finally:
            with self._recording_locks_guard:
                state["users"] -= 1
                if state["users"] == 0 and self._recording_locks.get(key) is state:
                    self._recording_locks.pop(key, None)

    def _winner_after_commit(self, owner, request_id, request_digest, commit_result):
        """Return the durable SQL winner when this caller lost a receipt race."""

        if not commit_result or not commit_result.get("replayed"):
            return None
        returned = commit_result.get("result")
        if (
            commit_result.get("request_digest") != request_digest
            or not isinstance(returned, dict)
            or returned.get("request_id") != request_id
            or returned.get("request_digest") != request_digest
        ):
            raise ResumeIntakeUnavailableError()
        # Reload through the owner-qualified read. This both hydrates mutable
        # source/canonical state and proves that the procedure's returned
        # receipt is the receipt visible for this owner and request.
        snapshot = self._load(owner)
        existing = snapshot.get("receipts", {}).get(request_id)
        if (
            not isinstance(existing, dict)
            or existing.get("request_digest") != request_digest
            or existing.get("result") != returned
        ):
            raise ResumeIntakeUnavailableError()
        return {
            **self._hydrate_replay(owner, snapshot, existing["result"]),
            "replayed": True,
            "request_digest": request_digest,
        }

    def persistence_label(self):
        return getattr(self.repository, "persistence_label", "unknown")

    # -- reads ----------------------------------------------------------

    def get_workspace(self, owner):
        snapshot = self._load(owner)
        policy = self.policy()
        guide = snapshot.get("guide") or {}
        pending = [
            present_proposal(row)
            for row in snapshot["proposals"].values()
            if row["state"] == "pending"
        ]
        pending.sort(key=lambda row: row["created_at"] or "")
        return {
            "entrance": policy.entrance,
            "policy": policy.as_document(),
            "lifecycle_epoch": snapshot["lifecycle_epoch"],
            "guide": {
                "status": guide.get("status") or "not_started",
                "status_source": guide.get("status_source") or "default_unstarted",
            },
            "pending_proposals": pending,
            "last_receipt": snapshot.get("last_receipt"),
            "receipts_count": len(snapshot["receipts"]),
            "capabilities": {
                "commands": sorted(COMMAND_TYPES),
                "structured_record_types": sorted(STRUCTURED_RECORD_TYPES),
                "editor_fields": {name: sorted(fields) for name, fields in EDITOR_FIELDS.items()},
                "supports_explicit_clear": True,
                "preserves_unspecified_fields": True,
                "publishes": False,
                "starts_processing_on_read": False,
                "persistence": self.persistence_label(),
                "persistence_is_live_database": bool(
                    getattr(self.repository, "is_live_database", False)
                    and policy.durable_persistence_allowed
                ),
                "schema_applied": False,
            },
        }

    # -- explicit Add ---------------------------------------------------

    def submit(self, owner, payload, *, files=None, allow_fixture_policy=False, now=None):
        if isinstance(payload, dict) and payload.get("type") == "keep_extracted_separate":
            return self.keep_extracted_separate(
                owner, payload, allow_fixture_policy=allow_fixture_policy, now=now,
            )
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        moment = _utc(now)
        files = files or {}
        raw = self._normalize_add(payload)
        # A read failure must still hand the member's unsent input back, so the
        # hint travels with the error even though the command digest needs the
        # snapshot (for the referenced recordings' hashes).
        proposed_hint = {
            "text": raw["text"],
            "items": [
                {"client_key": item["client_key"], "record_type": item["record_type"],
                 "values": item["values"], "explicit_clears": item["explicit_clears"]}
                for item in raw["items"]
            ],
            "attachments": raw["attachments"],
        }
        try:
            snapshot = self._load(owner)
        except ResumeIntakeUnavailableError as error:
            raise ResumeIntakeUnavailableError(
                proposed=error.proposed or proposed_hint
            ) from error
        snapshot["policy_version"] = policy.version
        prepared, results = self._prepare_inputs(raw, files, policy, snapshot)
        command = self._finalize_command(raw, prepared, snapshot)

        existing = snapshot["receipts"].get(command["request_id"])
        if existing is not None:
            if existing["request_digest"] != command["request_digest"]:
                raise ResumeIntakeConflictError(
                    "idempotency_conflict",
                    [{"request_id": command["request_id"]}],
                    "That request key was already used for different content.",
                    proposed=command["proposed"],
                )
            return {**self._hydrate_replay(owner, snapshot, existing["result"]), "replayed": True,
                    "request_digest": existing["request_digest"]}

        submission_key = str(uuid4())
        submission_version = 1
        submission = {
            "submission_key": submission_key,
            "version": submission_version,
            "state": "active",
            "entrance": policy.entrance,
            "policy_version": policy.version,
            "request_id": command["request_id"],
            "request_digest": command["request_digest"],
            "created_at": moment.isoformat(),
            "source_keys": [],
            "proposal_keys": [],
            "item_count": 0,
        }
        plans = self._plan_items(command, prepared)
        commit_result = None
        try:
            with self._unit_of_work() as unit:
                # The submission row exists before any job is fenced, so a
                # job's submission-version proof is meaningful from the start.
                snapshot["submissions"][submission_key] = submission
                canonical_view: list[dict] = []
                jobs: list[dict] = []
                proposals: list[dict] = []
                source_keys: list[str] = []
                for plan in plans:
                    source = self._store_source(snapshot, submission_key, submission_version, plan, moment)
                    source_keys.append(source["source_key"])
                    fence = JobFence(
                        source_key=source["source_key"],
                        source_version=int(source["version"]),
                        submission_key=submission_key,
                        submission_version=submission_version,
                        policy_version=policy.version,
                        lifecycle_epoch=snapshot["lifecycle_epoch"],
                    )
                    job = enqueue(snapshot, fence, _job_kind(plan.kind), now=moment)
                    lease = lease_job(snapshot, job["job_key"], now=moment)
                    outcome, result = self._process_plan(
                        owner, snapshot, unit, plan, source, submission_key,
                        submission_version, policy, command, moment, canonical_view, proposals,
                    )
                    if outcome == "failed":
                        fail_job(snapshot, job["job_key"], lease["lease_id"],
                                 result.get("code") or "failed", now=moment)
                    else:
                        # A quiet duplicate processed fully but saved nothing:
                        # it is skipped, never unresolved and never saved.
                        job_result = (
                            "saved" if outcome == "saved"
                            else "skipped" if outcome == "duplicate"
                            else "unresolved"
                        )
                        complete_job(snapshot, job["job_key"], lease["lease_id"],
                                     result=job_result,
                                     outcome=result.get("code") or outcome, now=moment)
                    jobs.append(present_job(snapshot["jobs"][job["job_key"]]))
                    result = dict(result)
                    result.setdefault("client_key", plan.client_key)
                    result.setdefault("kind", plan.kind)
                    results.append(result)

                submission["source_keys"] = source_keys
                submission["proposal_keys"] = [row["proposal_key"] for row in proposals]
                submission["item_count"] = len(results)
                summary = _summarize(results)
                receipt = {
                    "success": True,
                    "outcome": summary["outcome"],
                    "replayed": False,
                    "request_digest": command["request_digest"],
                    "request_id": command["request_id"],
                    "submission": submission,
                    "results": results,
                    "summary": summary,
                    "jobs": jobs,
                    "proposals": [present_proposal(row) for row in proposals],
                    "saved_items": canonical_view,
                    "publishes": False,
                    "message": _receipt_message(summary),
                }
                # The immutable stored receipt never carries the member's words:
                # the mutable source and proposal rows hold them and are the
                # only copies purge has to redact. What is stored is the
                # structural outcome, replayed verbatim on a same-key retry.
                stored_receipt = receipt_for_storage(receipt)
                stored_receipt["persisted"] = True
                for entry in stored_receipt.get("saved_items") or []:
                    entry["persisted"] = True
                snapshot["receipts"][command["request_id"]] = {
                    "request_digest": command["request_digest"],
                    "submission_key": submission_key,
                    "result": stored_receipt,
                }
                snapshot["last_receipt"] = {
                    "outcome": receipt["outcome"],
                    "summary": summary,
                    "created_at": moment.isoformat(),
                    "request_id": command["request_id"],
                }
                commit_result = unit.commit(
                    owner,
                    snapshot,
                    procedure=COMMAND_PROCEDURES["add_submission"],
                    request_id=command["request_id"],
                    payload=_submission_payload(command, snapshot, stored_receipt),
                )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError(proposed=command["proposed"]) from error
        winner = self._winner_after_commit(
            owner, command["request_id"], command["request_digest"], commit_result
        )
        if winner is not None:
            return winner
        receipt["persisted"] = True
        for entry in receipt.get("saved_items") or []:
            entry["persisted"] = True
        return _present_intake_receipt(receipt)

    # -- in-field microphone transcription ------------------------------

    def transcribe_recording(
        self, owner, upload, payload, *, allow_fixture_policy=False, now=None
    ):
        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        client_key = _text(payload.get("client_key"), field="client key", maximum=200) or "recording"
        duration = payload.get("duration_seconds")
        moment = _utc(now)
        # Read the audio once, bounded, before hashing: the digest binds to the
        # admitted bytes, not to a filename or duration.
        try:
            data = self.transcription_adapter.read_bounded(upload, policy)
        except RecordingIntakeError as error:
            raise ResumeIntakeValidationError(error.member_message) from error
        audio_sha256 = hashlib.sha256(data).hexdigest()
        content_type = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0].strip()
        digest = _json_digest(
            {"type": "transcribe_recording", "client_key": client_key,
             "duration_seconds": duration, "audio_sha256": audio_sha256}
        )
        with self._recording_request_lock(owner, request_id):
            return self._transcribe_recording_once(
                owner=owner,
                request_id=request_id,
                client_key=client_key,
                duration=duration,
                moment=moment,
                data=data,
                audio_sha256=audio_sha256,
                content_type=content_type,
                digest=digest,
                policy=policy,
            )

    def _transcribe_recording_once(
        self, *, owner, request_id, client_key, duration, moment, data,
        audio_sha256, content_type, digest, policy
    ):
        try:
            validated = self.transcription_adapter.admit_bytes(content_type, data, duration, policy)
        except RecordingIntakeError as error:
            raise ResumeIntakeValidationError(error.member_message) from error

        snapshot = self._load(owner)
        lifecycle_epoch = int(snapshot["lifecycle_epoch"])
        claim_payload = {
            "type": "claim_recording",
            "request_id": request_id,
            "request_digest": digest,
            "client_key": client_key,
            "entrance": policy.entrance,
            "policy_version": policy.version,
            "lifecycle_epoch": lifecycle_epoch,
            "audio_sha256": audio_sha256,
            "byte_length": validated.byte_length,
            "content_type": validated.content_type,
            "duration_seconds": validated.duration_seconds,
        }
        try:
            claim = self.repository.claim_recording(
                owner, request_id, claim_payload, now=moment
            )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError(proposed={"client_key": client_key}) from error
        if claim.get("outcome") == "conflict":
            raise ResumeIntakeConflictError(
                "idempotency_conflict", [{"request_id": request_id}],
                "That request key was already used for a different recording.",
            )
        if claim.get("outcome") == "replay":
            return self._winner_after_commit(
                owner,
                request_id,
                digest,
                {
                    "replayed": True,
                    "request_digest": digest,
                    "result": claim.get("result"),
                },
            )
        if claim.get("outcome") == "pending":
            recovery_required = bool(claim.get("recovery_required"))
            return {
                "success": False,
                "outcome": "pending",
                "code": (
                    "recording_recovery_required"
                    if recovery_required else "recording_pending"
                ),
                "request_id": request_id,
                "request_digest": digest,
                "replayed": False,
                "client_key": client_key,
                "input_preserved": True,
                "provider_called_by_this_attempt": False,
                "recovery_required": recovery_required,
                "lease_expires_at": claim.get("lease_expires_at"),
                "publishes": False,
                "message": (
                    "This recording has an unfinished processing claim. "
                    "It was not sent to the provider again."
                    if recovery_required else
                    "This recording already has a processing claim. "
                    "It was not sent to the provider again."
                ),
            }
        if claim.get("outcome") != "claimed":
            raise ResumeIntakeUnavailableError(proposed={"client_key": client_key})

        # Provider contact occurs only after the durable owner/request/digest
        # claim has returned this lease and preallocated source key.
        outcome = self.transcription_adapter.transcribe(validated, policy)

        # Reload after provider work so finalization never replaces newer owner
        # state with the snapshot observed before the lease was acquired.
        snapshot = self._load(owner)
        if (
            int(snapshot["lifecycle_epoch"]) != lifecycle_epoch
            or int(snapshot["policy_version"]) != int(policy.version)
        ):
            raise ResumeIntakeConflictError(
                "recording_claim_changed", [{"request_id": request_id}],
                "This recording finished after your intake state changed. "
                "It was not saved, and it will not be sent to the provider again.",
                proposed={"client_key": client_key},
            )
        snapshot["policy_version"] = policy.version
        result = {
            "success": outcome.ok,
            "outcome": "transcribed" if outcome.ok else "failed",
            "request_id": request_id,
            "request_digest": digest,
            "replayed": False,
            "client_key": client_key,
            "transcript": outcome.transcript,
            "receipt": outcome.as_receipt(),
            "input_preserved": not outcome.ok,
            "publishes": False,
            "source_version": 1 if outcome.ok else None,
            "lifecycle_epoch": lifecycle_epoch,
        }
        source_key = claim["source_key"]
        if outcome.ok:
            snapshot["sources"][source_key] = {
                "source_key": source_key,
                "kind": "recording",
                "state": "active",
                "version": 1,
                "text": outcome.transcript,
                "content_type": outcome.content_type,
                "byte_length": outcome.byte_length,
                "sha256": outcome.sha256,
                "duration_seconds": outcome.duration_seconds,
                "created_at": moment.isoformat(),
                "origin_client_key": client_key,
            }
            result["source_key"] = source_key
        stored_result = receipt_for_storage(result)
        stored_result["persisted"] = bool(outcome.ok)
        snapshot["receipts"][request_id] = {
            "request_digest": digest, "submission_key": None, "result": stored_result,
        }
        try:
            commit_result = self.repository.save_owner(
                owner,
                snapshot,
                {
                    "procedure": COMMAND_PROCEDURES["transcribe_recording"],
                    "request_id": request_id,
                    "payload": {
                        "type": "transcribe_recording",
                        "request_id": request_id,
                        "client_key": client_key,
                        "entrance": policy.entrance,
                        "policy_version": policy.version,
                        "lifecycle_epoch": lifecycle_epoch,
                        "audio_sha256": audio_sha256,
                        "byte_length": validated.byte_length,
                        "content_type": validated.content_type,
                        "duration_seconds": validated.duration_seconds,
                        "outcome": result["outcome"],
                        "transcript": outcome.transcript,
                        "source_key": source_key,
                        "source_version": 1 if outcome.ok else None,
                        "receipt": stored_result,
                        "request_digest": digest,
                        "lease_id": claim["lease_id"],
                    },
                },
            )
        except ResumeIntakeStoreUnavailable as error:
            # The durable claim deliberately remains pending. A retry checks
            # for a completed receipt but never starts a second provider call
            # merely because this final response or finalization was ambiguous.
            raise ResumeIntakeUnavailableError(proposed={"client_key": client_key}) from error
        winner = self._winner_after_commit(owner, request_id, digest, commit_result)
        return winner if winner is not None else result

    # -- member decision on a pending proposal ---------------------------

    def decide(self, owner, payload, *, allow_fixture_policy=False):
        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        proposal_key = _as_uuid(payload.get("proposal_key"), field="proposal key")
        decision = payload.get("decision")
        if decision not in {"accept", "reject", "edit"}:
            raise ResumeIntakeValidationError("Invalid decision.")
        confirmed = payload.get("confirmed_values")
        if confirmed is not None and not isinstance(confirmed, dict):
            raise ResumeIntakeValidationError("Invalid confirmed values.")
        # Privacy cleanup never depends on AI/provider availability, but a
        # decision that writes canonical truth does need a usable policy.
        policy = None
        if decision in {"accept", "edit"}:
            policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        digest = _json_digest(
            {"type": "decide_proposal", "proposal_key": proposal_key,
             "decision": decision, "confirmed_values": confirmed}
        )
        snapshot = self._load(owner)
        if policy is not None:
            snapshot["policy_version"] = policy.version
        existing = snapshot["receipts"].get(request_id)
        if existing is not None:
            if existing["request_digest"] != digest:
                raise ResumeIntakeConflictError(
                    "idempotency_conflict", [{"request_id": request_id}],
                    "That request key was already used for a different decision.",
                )
            return {**self._hydrate_replay(owner, snapshot, existing["result"]), "replayed": True}
        proposal = snapshot["proposals"].get(proposal_key)
        if proposal is None:
            raise ResumeIntakeNotFoundError()
        if decision in {"accept", "edit"} and confirmed is None:
            if decision == "edit":
                raise ResumeIntakeValidationError("Provide your wording to save this.")
            if proposal.get("requires_member_wording"):
                raise ResumeIntakeConflictError(
                    "reconciliation_required",
                    [{"proposal_key": proposal_key, "reason": "member_wording_required"}],
                    "Choose what this should become before saving it.",
                    proposed=proposal.get("proposed_values"),
                )
        try:
            decided = decide_proposal_record(
                snapshot, proposal_key, decision=decision,
                confirmed_values=confirmed, request_digest=digest,
            )
        except ProposalError as error:
            raise ResumeIntakeConflictError(
                error.code, error.conflicts, "That proposal changed.", proposed=error.proposed
            ) from error

        outcome = "unresolved"
        item = None
        procedure = COMMAND_PROCEDURES["decide_proposal"]
        commit_result = None
        try:
            with self._unit_of_work() as unit:
                if decided["state"] == "accepted":
                    item = self._apply_decision(owner, snapshot, unit, decided, confirmed)
                    outcome = "saved"
                result = {
                    "success": True,
                    "outcome": outcome,
                    "request_id": request_id,
                    "request_digest": digest,
                    "replayed": False,
                    "proposal_key": proposal_key,
                    "proposal": present_proposal(snapshot["proposals"][proposal_key]),
                    "item": item,
                    "publishes": False,
                    "message": {
                        "saved": "Saved privately. Display and visitor AI stay off.",
                        "unresolved": "Proposal dismissed. Nothing was saved.",
                    }.get(outcome, "Nothing was published."),
                }
                snapshot["receipts"][request_id] = {
                    "request_digest": digest, "submission_key": None,
                    "result": receipt_for_storage(result),
                }
                commit_result = unit.commit(
                    owner,
                    snapshot,
                    procedure=procedure,
                    request_id=request_id,
                    payload={
                        "type": "decide_proposal",
                        "request_id": request_id,
                        "proposal_key": proposal_key,
                        "decision": decision,
                        "confirmed_values": decided.get("confirmed_values"),
                        "request_digest": digest,
                        "target_key": decided.get("target_key"),
                        "target_content_token": decided.get("target_content_token"),
                        "target_access_revision": decided.get("target_access_revision"),
                        "outcome": outcome,
                        "receipt": receipt_for_storage(result),
                    },
                )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError(proposed=confirmed) from error
        winner = self._winner_after_commit(owner, request_id, digest, commit_result)
        return winner if winner is not None else result

    # -- purge / delete a source ----------------------------------------

    def purge_source(self, owner, payload, *, now=None):
        with self.repository.owner_guard(owner):
            return self._purge_source_guarded(owner, payload, now=now)

    def _purge_source_guarded(self, owner, payload, *, now=None):
        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        # Deleting a member's own input is privacy cleanup: it never waits on a
        # provider, a feature flag, or a selected onboarding policy.
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        source_key = _as_uuid(payload.get("source_key"), field="source key")
        moment = _utc(now)
        snapshot = self._load(owner)
        source = snapshot["sources"].get(source_key)
        if source is None:
            raise ResumeIntakeNotFoundError()
        digest = _json_digest({"type": "purge_source", "source_key": source_key})
        existing = snapshot["receipts"].get(request_id)
        if existing is not None:
            if existing["request_digest"] != digest:
                raise ResumeIntakeConflictError(
                    "idempotency_conflict", [{"request_id": request_id}],
                    "That request key was already used for a different source.",
                )
            return {**self._hydrate_replay(owner, snapshot, existing["result"]), "replayed": True}
        already = source["state"] == "purged"
        invalidated_candidates = 0
        if not already:
            for candidate in _source_extracted_candidates(source):
                if candidate.get("state") != "invalidated":
                    invalidated_candidates += 1
                candidate["state"] = "invalidated"
                candidate.pop("values", None)
                candidate.pop("consumed_request_id", None)
            source["state"] = "purged"
            source["text"] = None  # purged source text is never resurrected
            # Structured values are member words too. The redaction pass below
            # clears ordinary values and reduces extracted candidates to
            # identifier-only invalidated tombstones.
            source["version"] = int(source["version"]) + 1
            source["purged_at"] = moment.isoformat()
            snapshot["lifecycle_epoch"] = int(snapshot["lifecycle_epoch"]) + 1
        stale_jobs = invalidate_jobs_for_source(snapshot, source_key, now=moment)
        invalidated = invalidate_proposals_for_source(snapshot, source_key, now=moment)
        # Retained provenance keeps keys/versions/spans only: no purged text
        # survives in the proposal row or in a stored receipt copy.
        redacted = redact_source_text(snapshot, source_key)
        result = {
            "success": True,
            "outcome": "already_purged" if already else "purged",
            "request_id": request_id,
            "request_digest": digest,
            "replayed": False,
            "source_key": source_key,
            "stale_jobs": stale_jobs,
            "invalidated_proposals": invalidated,
            "invalidated_extracted_candidates": invalidated_candidates,
            "redacted_proposals": redacted,
            "provenance_retained": True,
            "source_resurrected": False,
            "message": (
                "That input was removed. Accepted history keeps its provenance, "
                "never the deleted text."
            ),
        }
        snapshot["receipts"][request_id] = {
            "request_digest": digest, "submission_key": None,
            "result": receipt_for_storage(result),
        }
        try:
            commit_result = self.repository.save_owner(
                owner,
                snapshot,
                {
                    "procedure": COMMAND_PROCEDURES["purge_source"],
                    "request_id": request_id,
                    "payload": {
                        "type": "purge_source",
                        "request_id": request_id,
                        "source_key": source_key,
                        "request_digest": digest,
                        "receipt": receipt_for_storage(result),
                    },
                },
            )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError(proposed={"source_key": source_key}) from error
        winner = self._winner_after_commit(owner, request_id, digest, commit_result)
        return winner if winner is not None else result

    # -- unsubmitted composer drafts ------------------------------------

    def _require_draft_store(self):
        if not getattr(self.repository, "supports_drafts", False):
            raise ResumeIntakeUnavailableError(
                "Draft saving is unavailable here. Your words stay in this browser."
            )

    def _drop_expired_drafts(self, snapshot, policy, moment):
        days = policy.draft_inactivity_days
        if days is None:
            return 0
        drafts = snapshot.get("drafts") or {}
        expired = [
            key for key, row in drafts.items()
            if _draft_expires_at(row, days) is not None
            and _utc(moment) >= _draft_expires_at(row, days)
        ]
        for key in expired:
            del drafts[key]
        return len(expired)

    def get_draft(self, owner, *, now=None):
        """Return the owner's unsubmitted composer draft, if one survives."""

        self._require_draft_store()
        policy = self.policy()
        moment = _utc(now)

        def read(snapshot):
            if snapshot is None:
                return None
            self._drop_expired_drafts(snapshot, policy, moment)
            row = (snapshot.get("drafts") or {}).get(DRAFT_KEY)
            return copy.deepcopy(row) if row is not None else None

        try:
            row = self.repository.with_drafts(owner, read, create=False)
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error
        return {
            "success": True,
            "draft": present_draft(row) if row is not None else None,
            "drafts_supported": True,
            "expires_after_days": policy.draft_inactivity_days,
        }

    def save_draft(self, owner, payload, *, allow_fixture_policy=False, now=None):
        """Version-checked draft save. Conflicts keep the member's input."""

        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        self._require_draft_store()
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        expected = payload.get("expected_version")
        if expected is not None and (
            isinstance(expected, bool) or not isinstance(expected, int) or expected < 1
        ):
            raise ResumeIntakeValidationError("Invalid draft version.")
        moment = _utc(now)
        normalized = self._normalize_draft(payload)
        held = {}

        def apply(snapshot):
            drafts = snapshot.setdefault("drafts", {})
            self._drop_expired_drafts(snapshot, policy, moment)
            existing = drafts.get(DRAFT_KEY)
            if existing is not None and existing.get("last_request_id") == request_id:
                held["outcome"] = "replay"
                held["record"] = copy.deepcopy(existing)
                return
            if existing is None:
                if expected is not None:
                    held["outcome"] = "conflict"
                    held["reason"] = "draft_missing"
                    held["existing"] = None
                    return
                version = 1
            elif expected != int(existing.get("version") or 0):
                held["outcome"] = "conflict"
                held["reason"] = "version_changed"
                held["existing"] = copy.deepcopy(existing)
                return
            else:
                version = int(existing.get("version") or 0) + 1
            attachments = self._draft_attachments(snapshot, normalized["attachments"])
            record = {
                "draft_key": DRAFT_KEY,
                "version": version,
                "state": "active",
                "text": normalized["text"],
                "items": normalized["items"],
                "attachments": attachments,
                "created_at": (existing or {}).get("created_at") or moment.isoformat(),
                "updated_at": moment.isoformat(),
                "expires_at": _draft_expiry_iso(moment, policy.draft_inactivity_days),
                "last_request_id": request_id,
            }
            drafts[DRAFT_KEY] = record
            held["outcome"] = "saved"
            held["record"] = copy.deepcopy(record)

        try:
            self.repository.with_drafts(owner, apply, create=True)
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError(proposed=normalized) from error
        if held.get("outcome") == "replay":
            return {
                "success": True, "draft": present_draft(held["record"]),
                "replayed": True, "request_id": request_id,
            }
        if held.get("outcome") == "conflict":
            existing = held.get("existing")
            if held.get("reason") == "draft_missing":
                raise ResumeIntakeConflictError(
                    "draft_conflict", [{"draft_key": DRAFT_KEY, "reason": "draft_missing"}],
                    "That draft is gone. Your unsaved words are kept here.",
                    proposed=normalized,
                )
            raise ResumeIntakeConflictError(
                "draft_conflict",
                [{
                    "draft_key": DRAFT_KEY,
                    "reason": "version_changed",
                    "server_version": int((existing or {}).get("version") or 0),
                    "server_updated_at": (existing or {}).get("updated_at"),
                    "server_draft": present_draft(existing) if existing else None,
                }],
                "That draft changed on another device. "
                "Your unsaved words are kept here. Choose which copy to keep.",
                proposed=normalized,
            )
        return {
            "success": True, "draft": present_draft(held["record"]),
            "replayed": False, "request_id": request_id,
        }

    def discard_draft(self, owner, payload, *, allow_fixture_policy=False, now=None):
        """Discard the unsubmitted draft. Idempotent and never a canonical write."""

        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        self._require_draft_store()
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        request_id = payload.get("request_id")
        if request_id is not None:
            _as_uuid(request_id, field="request id")
        moment = _utc(now)
        held = {"had_draft": False}

        def apply(snapshot):
            if snapshot is None:
                held["had_draft"] = False
                return
            self._drop_expired_drafts(snapshot, policy, moment)
            drafts = snapshot.setdefault("drafts", {})
            held["had_draft"] = drafts.pop(DRAFT_KEY, None) is not None

        try:
            self.repository.with_drafts(owner, apply, create=False)
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error
        return {"success": True, "discarded": True, "had_draft": held["had_draft"]}

    def keep_extracted_separate(self, owner, payload, *, allow_fixture_policy=False, now=None):
        """Save a server-held extracted equivalent as a new private fact."""

        if not getattr(self.repository, "supports_atomic_source_actions", False):
            raise ResumeIntakeUnavailableError(
                "Keep as separate is unavailable until source validation and saving share one transaction."
            )
        with self.repository.owner_guard(owner):
            return self._keep_extracted_separate_guarded(
                owner,
                payload,
                allow_fixture_policy=allow_fixture_policy,
                now=now,
            )

    def _keep_extracted_separate_guarded(
        self, owner, payload, *, allow_fixture_policy=False, now=None
    ):

        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        extra = set(payload) - {"type", "request_id", "override_key"}
        if extra:
            raise ResumeIntakeValidationError("Unknown keep-separate fields.")
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        override_key = payload.get("override_key")
        if not isinstance(override_key, str) or not override_key.strip():
            raise ResumeIntakeValidationError("Invalid keep-separate command.")
        override_key = override_key.strip()
        moment = _utc(now)
        digest = _json_digest({
            "type": "keep_extracted_separate",
            "override_key": override_key,
        })
        snapshot = self._load(owner)
        existing = snapshot["receipts"].get(request_id)
        if existing is not None:
            if existing["request_digest"] != digest:
                raise ResumeIntakeConflictError(
                    "idempotency_conflict",
                    [{"request_id": request_id}],
                    "That request key was already used for different content.",
                )
            return {
                **self._hydrate_replay(owner, snapshot, existing["result"]),
                "replayed": True,
                "request_digest": existing["request_digest"],
            }
        keep = self._find_extracted_override(snapshot, override_key)
        if keep is None:
            raise ResumeIntakeNotFoundError()
        if keep.get("state") == "invalidated":
            raise ResumeIntakeConflictError(
                "source_purged",
                [{"override_key": override_key, "reason": "source_purged"}],
                "That source was removed, so this keep-separate action is no longer available.",
            )
        consumed = keep.get("consumed_request_id")
        if consumed:
            stored = snapshot["receipts"].get(consumed)
            if not isinstance(stored, dict) or not isinstance(stored.get("result"), dict):
                raise ResumeIntakeConflictError(
                    "idempotency_conflict",
                    [{"override_key": override_key}],
                    "That keep-separate action was already used.",
                )
            return {
                **self._hydrate_replay(owner, snapshot, stored["result"]),
                "replayed": True,
                "request_digest": stored.get("request_digest"),
            }
        # The proposed SQL adapter persists the accepted override as its own
        # structural submission receipt, while its source JSON remains the
        # mutable candidate store. Recover that identifier-only consumption
        # marker after a reload so a new request cannot create the same
        # canonical fact twice. A purge removes/invalidates the source first,
        # so it never reaches this replay path.
        _consumed_request_id, stored = self._find_consumed_extracted_override(
            snapshot, override_key
        )
        if stored is not None:
            return {
                **self._hydrate_replay(owner, snapshot, stored["result"]),
                "replayed": True,
                "request_digest": stored.get("request_digest"),
            }
        record_type, values = self._server_held_extracted_values(keep)
        plan = _ItemPlan(
            client_key=f"keep-extracted:{override_key}",
            kind="structured",
            record_type=record_type,
            provided_values=values,
            as_separate=True,
            quote=_subject(record_type, values)[:300],
            confidence="certain",
        )
        command = {
            "request_id": request_id,
            "request_digest": digest,
            "proposed": None,
        }
        commit_result = None
        try:
            with self._unit_of_work() as unit:
                submission_key = override_key
                submission_version = 1
                submission = {
                    "submission_key": submission_key,
                    "version": submission_version,
                    "state": "active",
                    "entrance": policy.entrance,
                    "policy_version": policy.version,
                    "request_id": request_id,
                    "request_digest": digest,
                    "created_at": moment.isoformat(),
                    "source_keys": [],
                    "proposal_keys": [],
                    "item_count": 0,
                }
                snapshot["submissions"][submission_key] = submission
                canonical_view: list[dict] = []
                jobs: list[dict] = []
                proposals: list[dict] = []
                source = self._store_source(
                    snapshot, submission_key, submission_version, plan, moment
                )
                fence = JobFence(
                    source_key=source["source_key"],
                    source_version=int(source["version"]),
                    submission_key=submission_key,
                    submission_version=submission_version,
                    policy_version=policy.version,
                    lifecycle_epoch=snapshot["lifecycle_epoch"],
                )
                job = enqueue(snapshot, fence, _job_kind(plan.kind), now=moment)
                lease = lease_job(snapshot, job["job_key"], now=moment)
                outcome, result = self._process_plan(
                    owner, snapshot, unit, plan, source, submission_key,
                    submission_version, policy, command, moment, canonical_view,
                    proposals,
                )
                if outcome == "failed":
                    fail_job(
                        snapshot, job["job_key"], lease["lease_id"],
                        result.get("code") or "failed", now=moment,
                    )
                else:
                    job_result = (
                        "saved" if outcome == "saved"
                        else "skipped" if outcome == "duplicate"
                        else "unresolved"
                    )
                    complete_job(
                        snapshot, job["job_key"], lease["lease_id"],
                        result=job_result,
                        outcome=result.get("code") or outcome, now=moment,
                    )
                jobs.append(present_job(snapshot["jobs"][job["job_key"]]))
                result = dict(result)
                result.setdefault("client_key", plan.client_key)
                result.setdefault("kind", plan.kind)
                results = [result]
                submission["source_keys"] = [source["source_key"]]
                submission["proposal_keys"] = [row["proposal_key"] for row in proposals]
                submission["item_count"] = len(results)
                summary = _summarize(results)
                receipt = {
                    "success": True,
                    "outcome": summary["outcome"],
                    "replayed": False,
                    "request_digest": digest,
                    "request_id": request_id,
                    "submission": submission,
                    "results": results,
                    "summary": summary,
                    "jobs": jobs,
                    "proposals": [present_proposal(row) for row in proposals],
                    "saved_items": canonical_view,
                    "publishes": False,
                    "message": _receipt_message(summary),
                }
                stored_receipt = receipt_for_storage(receipt)
                stored_receipt["persisted"] = True
                for entry in stored_receipt.get("saved_items") or []:
                    entry["persisted"] = True
                snapshot["receipts"][request_id] = {
                    "request_digest": digest,
                    "submission_key": submission_key,
                    "result": stored_receipt,
                }
                snapshot["last_receipt"] = {
                    "outcome": receipt["outcome"],
                    "summary": summary,
                    "created_at": moment.isoformat(),
                    "request_id": request_id,
                }
                keep["state"] = "consumed"
                keep["consumed_request_id"] = request_id
                keep.pop("values", None)
                commit_result = unit.commit(
                    owner,
                    snapshot,
                    procedure=COMMAND_PROCEDURES["add_submission"],
                    request_id=request_id,
                    payload=_submission_payload(command, snapshot, stored_receipt),
                )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error
        winner = self._winner_after_commit(owner, request_id, digest, commit_result)
        if winner is not None:
            return winner
        receipt["persisted"] = True
        for entry in receipt.get("saved_items") or []:
            entry["persisted"] = True
        return _present_intake_receipt(receipt)

    def _find_extracted_override(self, snapshot, override_key):
        for source in (snapshot.get("sources") or {}).values():
            for candidate in _source_extracted_candidates(source):
                if candidate.get("override_key") != override_key:
                    continue
                if (
                    candidate.get("source_key") != source.get("source_key")
                    or int(candidate.get("source_version") or 0)
                    != int(source.get("version") or 0)
                    or source.get("state") != "active"
                ):
                    candidate["state"] = "invalidated"
                    candidate.pop("values", None)
                    candidate.pop("consumed_request_id", None)
                return candidate
        return None

    def _find_consumed_extracted_override(self, snapshot, override_key):
        for request_id, stored in (snapshot.get("receipts") or {}).items():
            if (
                isinstance(stored, dict)
                and stored.get("submission_key") == override_key
                and isinstance(stored.get("result"), dict)
            ):
                return request_id, stored
        return None, None

    def _server_held_extracted_values(self, keep):
        record_type = keep.get("record_type")
        if record_type not in STRUCTURED_RECORD_TYPES:
            raise ResumeIntakeConflictError(
                "reconciliation_required",
                [{"reason": "record_type_required"}],
                "Choose what this should become before saving it.",
            )
        if keep.get("state") != "pending":
            raise ResumeIntakeConflictError(
                "reconciliation_required",
                [{"override_key": keep.get("override_key"), "reason": "candidate_unavailable"}],
                "That keep-separate action is no longer available.",
            )
        raw = keep.get("values")
        if not isinstance(raw, dict):
            raise ResumeIntakeValidationError("Invalid keep-separate command.")
        values = {}
        for name, value in raw.items():
            if name in FORBIDDEN_CLIENT_FIELDS:
                raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
            if name not in EDITOR_FIELDS[record_type] or value is None:
                continue
            values[name] = value
        if not values:
            raise ResumeIntakeValidationError("Invalid keep-separate command.")
        return record_type, values

    def _normalize_draft(self, payload):
        text = _text(payload.get("text"), field="text")
        raw_items = payload.get("items") or []
        if not isinstance(raw_items, list) or len(raw_items) > DRAFT_MAX_ITEMS:
            raise ResumeIntakeValidationError("Invalid items.")
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ResumeIntakeValidationError("Invalid items.")
            record_type = raw.get("record_type")
            if record_type not in STRUCTURED_RECORD_TYPES:
                raise ResumeIntakeValidationError("Invalid record type.")
            values = raw.get("values")
            if values is None:
                values = {}
            if not isinstance(values, dict):
                raise ResumeIntakeValidationError("Invalid values.")
            unknown = set(values) - EDITOR_FIELDS[record_type]
            if unknown or (set(values) & FORBIDDEN_CLIENT_FIELDS):
                raise ResumeIntakeValidationError("Unknown value fields are not allowed.")
            clears = raw.get("explicit_clears") or []
            if not isinstance(clears, list):
                raise ResumeIntakeValidationError("Invalid explicit clears.")
            clear_set = set()
            for name in clears:
                if not isinstance(name, str) or name not in EDITOR_FIELDS[record_type]:
                    raise ResumeIntakeValidationError("Invalid explicit clears.")
                clear_set.add(name)
            if clear_set & set(values):
                raise ResumeIntakeValidationError("A field cannot be set and cleared at once.")
            items.append({
                "client_key": _text(raw.get("client_key"), field="client key", maximum=200)
                or str(uuid4()),
                "record_type": record_type,
                "values": dict(values),
                "explicit_clears": sorted(clear_set),
            })
        raw_attachments = payload.get("attachments") or []
        if not isinstance(raw_attachments, list) or len(raw_attachments) > DRAFT_MAX_ATTACHMENTS:
            raise ResumeIntakeValidationError("Invalid attachments.")
        attachments = []
        for raw in raw_attachments:
            if not isinstance(raw, dict):
                raise ResumeIntakeValidationError("Invalid attachments.")
            kind = raw.get("kind")
            if kind not in {"document", "recording"}:
                raise ResumeIntakeValidationError("Invalid attachment kind.")
            client_key = _text(raw.get("client_key"), field="client key", maximum=200, required=True)
            entry = {"client_key": client_key, "kind": kind}
            if kind == "document":
                entry["declared_content_type"] = _text(
                    raw.get("declared_content_type"), field="content type", maximum=200
                )
                entry["filename"] = _text(raw.get("filename"), field="filename", maximum=300)
            else:
                entry["duration_seconds"] = raw.get("duration_seconds")
                source_key = raw.get("source_key")
                entry["source_key"] = (
                    _as_uuid(source_key, field="source key") if source_key else None
                )
            attachments.append(entry)
        return {"text": text, "items": items, "attachments": attachments}

    def _draft_attachments(self, snapshot, attachments):
        """Resolve draft attachment descriptors against live sources.

        A descriptor that names a missing, purged, or unreadable source stays
        in the draft with ``needs_reattach`` instead of failing the save: an
        incomplete upload is a truthful reattachment state, never lost input.
        """

        resolved = []
        sources = snapshot.get("sources") or {}
        for entry in attachments:
            row = dict(entry)
            source_key = entry.get("source_key")
            if source_key:
                source = sources.get(source_key)
                if (
                    source is None
                    or source.get("state") != "active"
                    or not source.get("text")
                ):
                    row["needs_reattach"] = True
                else:
                    row["needs_reattach"] = False
            else:
                # No server source stands behind this descriptor, so Add
                # cannot use it yet: documents wait for their bytes and
                # recordings wait for a transcript.
                row["needs_reattach"] = True
            resolved.append(row)
        return resolved

    # -- internals ------------------------------------------------------

    def _hydrate_replay(self, owner, snapshot, stored_result):
        """Restore member-visible content on replay from still-active sources.

        The immutable receipt keeps only structure. Recovery stays useful by
        re-reading the *mutable* source and proposal rows, qualified by owner,
        source key, source version and the current lifecycle epoch. A purged or
        superseded source yields no content, so replay can never resurrect what
        purge removed.
        """

        if not isinstance(stored_result, dict):
            return stored_result
        result = copy.deepcopy(stored_result)
        epoch = int(snapshot.get("lifecycle_epoch") or 0)

        source_key = result.get("source_key")
        if source_key:
            source = (snapshot.get("sources") or {}).get(source_key)
            version = result.get("source_version")
            epoch_ok = result.get("lifecycle_epoch") is None or int(
                result.get("lifecycle_epoch") or 0
            ) == epoch
            if (
                source is not None
                and source.get("state") == "active"
                and source.get("text")
                and (version is None or int(source.get("version") or 0) == int(version))
                and epoch_ok
            ):
                result["transcript"] = source.get("text")
                result["content_recovered"] = True
                if isinstance(result.get("receipt"), dict):
                    result["receipt"]["transcript"] = source.get("text")
            else:
                result["transcript"] = None
                result["content_recovered"] = False
                if source is None:
                    result["source_unavailable_reason"] = "missing"
                elif source.get("state") == "purged":
                    result["source_purged"] = True
                    result["source_unavailable_reason"] = "purged"
                elif version is not None and int(source.get("version") or 0) != int(version):
                    result["source_unavailable_reason"] = "version_changed"
                elif not epoch_ok:
                    result["source_unavailable_reason"] = "lifecycle_changed"
                else:
                    result["source_unavailable_reason"] = "inactive"

        rows = snapshot.get("proposals") or {}
        proposal_keys = [
            row.get("proposal_key") for row in result.get("proposals") or []
            if isinstance(row, dict)
        ]
        if proposal_keys:
            live = [present_proposal(rows[key]) for key in proposal_keys if key in rows]
            if live:
                result["proposals"] = live
        single = result.get("proposal_key")
        if single and single in rows:
            result["proposal"] = present_proposal(rows[single])

        # Saved member values never live in the immutable receipt. Re-read them
        # through the owner-qualified canonical catalog. An unchanged version is
        # content-equivalent to the first response. A changed version is labeled
        # as current state so replay never claims it is the original wording.
        saved_items = result.get("saved_items") or []
        if saved_items:
            canonical_available = True
            try:
                current_items = self._canonical_items(owner)
            except ResumeIntakeUnavailableError:
                current_items = []
                canonical_available = False
            current_by_key = {item.get("record_key"): item for item in current_items}
            hydrated = []
            for stored in saved_items:
                if not isinstance(stored, dict):
                    hydrated.append(stored)
                    continue
                entry = dict(stored)
                current = current_by_key.get(entry.get("record_key"))
                if current is None:
                    entry["content_recovered"] = False
                    entry["content_unavailable_reason"] = (
                        "canonical_unavailable" if not canonical_available else "missing"
                    )
                else:
                    source = (snapshot.get("sources") or {}).get(entry.get("intake_source_key"))
                    source_values = (
                        source.get("structured_values")
                        if source is not None
                        and source.get("state") == "active"
                        and int(source.get("version") or 0)
                        == int(entry.get("intake_source_version") or 0)
                        else None
                    )
                    same_content = isinstance(source_values, dict) and (
                        current.get("values") or {}
                    ) == source_values
                    entry["values"] = copy.deepcopy(current.get("values") or {})
                    entry["content_recovered"] = True
                    entry["content_equivalent_to_first_response"] = same_content
                    entry["values_source"] = (
                        "saved_version" if same_content else "current_canonical_at_replay"
                    )
                    if source_values is None:
                        entry["first_response_comparison"] = "source_unavailable"
                    elif not same_content:
                        entry["content_changed_since_first_response"] = True
                hydrated.append(entry)
            result["saved_items"] = hydrated
        # A duplicate receipt replays its keep-as-separate wording from the
        # still-active purgeable source row, so immutable history never
        # carries member words yet replay stays fully usable. A purged or
        # changed source yields no wording, never resurrected text.
        for row in result.get("results") or []:
            if not isinstance(row, dict) or row.get("outcome") != "duplicate":
                continue
            keep = row.get("keep_separate")
            if not isinstance(keep, dict) or keep.get("values"):
                continue
            if keep.get("override_key"):
                continue
            source = (snapshot.get("sources") or {}).get(row.get("intake_source_key"))
            if (
                source is not None
                and source.get("state") == "active"
                and int(source.get("version") or 0)
                == int(row.get("intake_source_version") or 0)
                and isinstance(source.get("structured_values"), dict)
            ):
                keep["values"] = copy.deepcopy(source["structured_values"])
        return _present_intake_receipt(result)

    def _normalize_add(self, payload):
        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid command.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner or authority fields cannot be client-supplied.")
        if payload.get("type", "add_submission") != "add_submission":
            raise ResumeIntakeValidationError("Unknown command.")
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        text = _text(payload.get("text"), field="text")
        raw_items = payload.get("items") or []
        if not isinstance(raw_items, list) or len(raw_items) > 25:
            raise ResumeIntakeValidationError("Invalid items.")
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ResumeIntakeValidationError("Invalid items.")
            record_type = raw.get("record_type")
            if record_type not in STRUCTURED_RECORD_TYPES:
                raise ResumeIntakeValidationError("Invalid record type.")
            values = raw.get("values")
            if values is None:
                values = {}
            if not isinstance(values, dict):
                raise ResumeIntakeValidationError("Invalid values.")
            unknown = set(values) - EDITOR_FIELDS[record_type]
            if unknown or (set(values) & FORBIDDEN_CLIENT_FIELDS):
                raise ResumeIntakeValidationError("Unknown value fields are not allowed.")
            clears = raw.get("explicit_clears") or []
            if not isinstance(clears, list):
                raise ResumeIntakeValidationError("Invalid explicit clears.")
            clear_set = set()
            for name in clears:
                if not isinstance(name, str) or name not in EDITOR_FIELDS[record_type]:
                    raise ResumeIntakeValidationError("Invalid explicit clears.")
                clear_set.add(name)
            if clear_set & set(values):
                raise ResumeIntakeValidationError("A field cannot be set and cleared at once.")
            # Keep-as-separate is an explicit member decision from a
            # duplicate receipt. Only a real boolean True skips matching;
            # anything else malformed is refused rather than guessed.
            as_separate = raw.get("as_separate", False)
            if as_separate is not True and as_separate is not False:
                raise ResumeIntakeValidationError("Invalid request to save separately.")
            items.append({
                "client_key": _text(raw.get("client_key"), field="client key", maximum=200)
                or str(uuid4()),
                "record_type": record_type,
                "values": dict(values),
                "explicit_clears": sorted(clear_set),
                "parent_key": (
                    _as_uuid(raw.get("parent_key"), field="parent key")
                    if raw.get("parent_key") else None
                ),
                "as_separate": as_separate,
            })
        raw_attachments = payload.get("attachments") or []
        if not isinstance(raw_attachments, list) or len(raw_attachments) > 25:
            raise ResumeIntakeValidationError("Invalid attachments.")
        attachments = []
        for raw in raw_attachments:
            if not isinstance(raw, dict):
                raise ResumeIntakeValidationError("Invalid attachments.")
            kind = raw.get("kind")
            if kind not in {"document", "recording"}:
                raise ResumeIntakeValidationError("Invalid attachment kind.")
            client_key = _text(raw.get("client_key"), field="client key", maximum=200, required=True)
            entry = {"client_key": client_key, "kind": kind}
            if kind == "document":
                entry["declared_content_type"] = _text(
                    raw.get("declared_content_type"), field="content type", maximum=200
                )
                entry["filename"] = _text(raw.get("filename"), field="filename", maximum=300)
            else:
                entry["duration_seconds"] = raw.get("duration_seconds")
                entry["source_key"] = (
                    _as_uuid(raw.get("source_key"), field="source key")
                    if raw.get("source_key") else None
                )
            attachments.append(entry)
        if not items and not attachments and not text:
            raise ResumeIntakeValidationError("Add something before saving.")
        return {
            "request_id": request_id,
            "text": text,
            "items": items,
            "attachments": attachments,
        }

    def _prepare_inputs(self, raw, files, policy, snapshot):
        """Read each document once, bounded, and hash the admitted bytes."""

        prepared = {}
        results = []
        documents = 0
        for attachment in raw["attachments"]:
            if attachment["kind"] == "document":
                documents += 1
                upload = files.get(attachment["client_key"])
                if documents > policy.max_documents_per_submission:
                    results.append({
                        "client_key": attachment["client_key"], "kind": "document",
                        "outcome": "failed", "code": "too_many_documents",
                        "message": "Too many documents were attached to one Add.", "saved": False,
                    })
                    continue
                if upload is None:
                    results.append({
                        "client_key": attachment["client_key"], "kind": "document",
                        "outcome": "failed", "code": "upload_required",
                        "message": "That file did not arrive. Attach it again.", "saved": False,
                    })
                    continue
                try:
                    content_type, data = self.document_adapter.admit(upload, policy)
                except DocumentIntakeError as error:
                    results.append({
                        "client_key": attachment["client_key"], "kind": "document",
                        "outcome": "failed", "code": error.code,
                        "message": error.member_message, "saved": False,
                    })
                    continue
                prepared[attachment["client_key"]] = {
                    "content_type": content_type,
                    "data": data,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            else:
                source = (snapshot.get("sources") or {}).get(attachment.get("source_key"))
                if source is None or source.get("state") != "active" or not source.get("text"):
                    results.append({
                        "client_key": attachment["client_key"], "kind": "recording",
                        "outcome": "failed", "code": "recording_not_transcribed",
                        "message": "That recording was not transcribed. Try again, or keep typing.",
                        "saved": False,
                    })
                    continue
                prepared[attachment["client_key"]] = {
                    "source_key": source["source_key"],
                    "sha256": source.get("sha256"),
                    "content_type": source.get("content_type"),
                    "byte_length": source.get("byte_length"),
                    "duration_seconds": source.get("duration_seconds"),
                    "text": source.get("text"),
                }
        return prepared, results

    def _finalize_command(self, raw, prepared, snapshot):
        items = []
        for item in raw["items"]:
            # The member may supply only the fields they actually changed. The
            # closed validator runs on the provided keys; a create needs its
            # required subject, a change is validated against the target later.
            try:
                normalized = normalize_editor_intent(item["record_type"], item["values"])
            except LivingResumeEditorValidationError as error:
                raise ResumeIntakeValidationError(str(error)) from error
            provided = {name: normalized[name] for name in item["values"] if name in normalized}
            items.append({**item, "provided_values": provided})
        digest_items = [
            {
                "client_key": item["client_key"],
                "record_type": item["record_type"],
                "values": item["provided_values"],
                "explicit_clears": item["explicit_clears"],
                "parent_key": item.get("parent_key"),
                "as_separate": bool(item.get("as_separate")),
            }
            for item in items
        ]
        digest_attachments = []
        for attachment in raw["attachments"]:
            entry = dict(attachment)
            payload = prepared.get(attachment["client_key"])
            entry["sha256"] = payload.get("sha256") if payload else None
            digest_attachments.append(entry)
        digest = _json_digest({
            "type": "add_submission",
            "text": raw["text"],
            "items": digest_items,
            "attachments": digest_attachments,
        })
        proposed = {
            "text": raw["text"],
            "items": [
                {"client_key": item["client_key"], "record_type": item["record_type"],
                 "values": item["provided_values"], "explicit_clears": item["explicit_clears"],
                 "parent_key": item.get("parent_key"),
                 "as_separate": bool(item.get("as_separate"))}
                for item in items
            ],
            "attachments": digest_attachments,
        }
        return {
            "request_id": raw["request_id"],
            "text": raw["text"],
            "items": items,
            "attachments": raw["attachments"],
            "prepared": prepared,
            "request_digest": digest,
            "proposed": proposed,
        }

    def _plan_items(self, command, prepared):
        plans = []
        if command["text"]:
            plans.append(_ItemPlan(
                client_key="typed-text", kind="text", record_type="unspecified",
                source_text=command["text"], quote=command["text"][:300], confidence="uncertain",
            ))
        for item in command["items"]:
            plans.append(_ItemPlan(
                client_key=item["client_key"], kind="structured",
                record_type=item["record_type"],
                provided_values=item["provided_values"],
                explicit_clears=item["explicit_clears"],
                parent_key=item.get("parent_key"),
                as_separate=bool(item.get("as_separate")),
                quote=_subject(item["record_type"], item["provided_values"])[:300],
                confidence="certain",
            ))
        for attachment in command["attachments"]:
            payload = prepared.get(attachment["client_key"])
            if payload is None:
                continue  # its validation failure already became a failed result
            if attachment["kind"] == "document":
                plans.append(_ItemPlan(
                    client_key=attachment["client_key"], kind="document",
                    record_type="unspecified", prepared=payload,
                    source_text=None, confidence="uncertain",
                ))
            else:
                plans.append(_ItemPlan(
                    client_key=attachment["client_key"], kind="recording",
                    record_type="unspecified", prepared=payload,
                    reuse_source_key=payload["source_key"],
                    source_text=payload.get("text"),
                    quote=(payload.get("text") or "")[:300], confidence="uncertain",
                ))
        return plans

    def _store_source(self, snapshot, submission_key, submission_version, plan, moment):
        if plan.reuse_source_key:
            existing = snapshot["sources"].get(plan.reuse_source_key)
            if existing is not None and existing.get("state") == "active":
                return existing
        source_key = str(uuid4())
        source = {
            "source_key": source_key,
            "kind": plan.kind,
            "state": "active",
            "version": 1,
            "text": plan.source_text if plan.kind != "structured" else None,
            "structured_values": plan.provided_values if plan.kind == "structured" else None,
            "record_type": plan.record_type,
            "content_type": (plan.prepared or {}).get("content_type"),
            "byte_length": (plan.prepared or {}).get("byte_length"),
            "sha256": (plan.prepared or {}).get("sha256"),
            "submission_key": submission_key,
            "submission_version": submission_version,
            "created_at": moment.isoformat(),
            "origin_client_key": plan.client_key,
        }
        snapshot["sources"][source_key] = source
        return source

    def _process_plan(
        self, owner, snapshot, unit, plan, source, submission_key,
        submission_version, policy, command, moment, canonical_view, proposals,
    ):
        if plan.kind == "structured" and plan.record_type == "accomplishment":
            # PS-RESUME-EDIT-002 rejects create_accomplishment with a NULL
            # parent. Never invent one: an unresolved parent stays an
            # actionable proposal instead of an invalid canonical intent.
            _parent, parent_reason = self._accomplishment_parent(owner, plan.parent_key)
            if parent_reason is not None:
                proposal = self._make_proposal(
                    snapshot, plan, source, submission_key, submission_version, policy,
                    command, kind="ambiguous_match", target=None,
                    confidence="parent_required", record_type="accomplishment",
                    proposed_values=_partial_values(plan),
                )
                proposals.append(proposal)
                return "unresolved", {
                    "outcome": "unresolved",
                    "record_type": "accomplishment",
                    "proposal_key": proposal["proposal_key"],
                    "code": parent_reason,
                    "message": "Choose an eligible private draft role for this Impact, then save it.",
                    "saved": False,
                }
        if plan.kind == "document" and plan.source_text is None:
            parsed = self.document_adapter.parse(
                plan.prepared["content_type"], plan.prepared["data"], policy,
                pipeline=self._document_pipeline,
            )
            if not parsed.ok:
                return "failed", {
                    "outcome": "failed", "code": parsed.reason or parsed.outcome,
                    "message": parsed.member_message, "saved": False,
                    "document": parsed.as_receipt(),
                }
            plan.source_text = parsed.text
            plan.quote = (parsed.text or "")[:300]
            plan.document = parsed.as_receipt()
            snapshot["sources"][source["source_key"]]["text"] = parsed.text

        if plan.kind == "structured":
            match = None
            if not plan.as_separate:
                match = self._match_existing(owner, plan)
            if match is None:
                item = self._save_new_fact(owner, snapshot, unit, plan, submission_key)
                # Keep the exact first-response values in the mutable, purgeable
                # source row. The immutable receipt retains only the source key
                # and version needed for owner-qualified replay comparison.
                snapshot["sources"][source["source_key"]]["structured_values"] = copy.deepcopy(
                    item.get("values") or {}
                )
                item["intake_source_key"] = source["source_key"]
                item["intake_source_version"] = int(source.get("version") or 1)
                canonical_view.append(item)
                return "saved", {
                    "outcome": "saved",
                    "record_type": plan.record_type,
                    "record_key": item.get("record_key"),
                    "message": "Saved privately. Display and visitor AI stay off.",
                    "display": "off",
                    "visitor_ai": "off",
                    "saved": True,
                }
            kind, target, confidence = match
            if kind == "equivalent":
                # Identical restatement: keep the existing entry, permissions
                # and versions untouched, with a quiet truthful receipt. The
                # member can still keep it as a separate fact explicitly.
                # Only keys travel in the receipt: member wording stays in
                # the purgeable source row, never in immutable history.
                snapshot["sources"][source["source_key"]]["structured_values"] = copy.deepcopy(
                    dict(plan.provided_values)
                )
                return "duplicate", {
                    "outcome": "duplicate",
                    "record_type": plan.record_type,
                    "record_key": (target or {}).get("record_key"),
                    "intake_source_key": source["source_key"],
                    "intake_source_version": int(source.get("version") or 1),
                    "already_saved": [{
                        "record_key": (target or {}).get("record_key"),
                        "record_type": plan.record_type,
                    }],
                    "keep_separate": {
                        "client_key": plan.client_key,
                        "record_type": plan.record_type,
                        "values": dict(plan.provided_values),
                        "explicit_clears": list(plan.explicit_clears),
                    },
                    "message": "Already saved. Nothing new was added.",
                    "saved": False,
                }
            proposal = self._make_proposal(
                snapshot, plan, source, submission_key, submission_version, policy,
                command, kind=kind, target=target, confidence=confidence,
            )
            proposals.append(proposal)
            return "unresolved", {
                "outcome": "unresolved",
                "record_type": plan.record_type,
                "proposal_key": proposal["proposal_key"],
                "message": "This may change something you already have. Review it to decide.",
                "saved": False,
            }
        # Text, documents and recordings are extraction: never silently saved.
        provider_issue = None
        duplicates: list[dict] = []
        if self._extraction_adapter is not None and plan.kind in {"text", "document", "recording"}:
            drafts, provider_issue = self._extract_with_adapter(owner, plan)
        else:
            drafts = self._interpreter(plan.source_text or "", plan.kind) or []
        if not drafts:
            # The deterministic manual path always survives: a provider
            # failure leaves editable uncertain wording, never lost input.
            drafts = [{
                "kind": "inferred_wording", "record_type": "unspecified",
                "values": {"text": (plan.source_text or "")[:MAX_TEXT_UNITS]},
                "confidence": "uncertain",
            }]
        created = []
        for draft in drafts or []:
            if draft.get("outcome") == "equivalent":
                # A true restatement keeps the existing entry and permissions:
                # no proposal, no write, just a quiet truthful receipt entry.
                # A reference that no longer resolves stays visible as an
                # uncertain proposal instead of silently vanishing.
                duplicate = self._resolve_equivalent(owner, draft)
                if duplicate is not None:
                    duplicates.append({
                        **duplicate,
                        "extracted_fields": dict(draft.get("values") or {}),
                    })
                    continue
                draft = {**draft, "kind": "inferred_wording", "confidence": "uncertain"}
            kind = draft.get("kind") or "inferred_wording"
            target = None
            if kind in {"additional_detail", "contradiction"}:
                # Overlay the listed member-owned fact. A missing, excluded,
                # unreadable, stale, or unlisted reference fails closed to
                # uncertain manual review instead of creating a second row.
                target = self._resolve_matched_target(owner, draft)
                if target is None:
                    kind = "inferred_wording"
                    draft = {**draft, "kind": kind, "confidence": "uncertain"}
            proposal = self._make_proposal(
                snapshot, plan, source, submission_key, submission_version, policy, command,
                kind=kind,
                target=target,
                confidence=draft.get("confidence") or "uncertain",
                record_type=draft.get("record_type") or "unspecified",
                proposed_values=draft.get("values"),
                provided_fields=draft.get("provided_fields"),
                quote=draft.get("quote"),
                span_start=draft.get("span_start"),
                span_end=draft.get("span_end"),
            )
            created.append(proposal)
            proposals.append(proposal)
        if duplicates and not created:
            actions = _bind_extracted_candidates(
                source, duplicates, submission_key, plan.client_key
            )
            return "duplicate", {
                "outcome": "duplicate",
                "record_type": plan.record_type,
                "already_saved": [
                    {
                        "record_key": row.get("record_key"),
                        "record_type": row.get("record_type"),
                    }
                    for row in duplicates
                ],
                "keep_separate_actions": actions,
                "message": "Already saved. Nothing new was added.",
                "saved": False,
            }
        result = {
            "outcome": "unresolved",
            "record_type": plan.record_type,
            "proposal_keys": [row["proposal_key"] for row in created],
            "message": "Captured as a proposal. Nothing is saved until you review it.",
            "saved": False,
        }
        if duplicates:
            result["keep_separate_actions"] = _bind_extracted_candidates(
                source, duplicates, submission_key, plan.client_key
            )
            result["already_saved"] = [
                {
                    "record_key": row.get("record_key"),
                    "record_type": row.get("record_type"),
                }
                for row in duplicates
            ]
            result["message"] += (
                f" {len(duplicates)}"
                f" {'item was' if len(duplicates) == 1 else 'items were'} already saved."
            )
        if provider_issue is not None:
            result["provider_issue"] = {"code": provider_issue, "retryable": True}
            result["message"] += (
                " The organizer is unavailable right now. Your words are kept "
                "for review, and you can retry or type them directly."
            )
        if plan.document:
            # A truncated or partial document is visible, never implied complete.
            result["document"] = plan.document
        return "unresolved", result

    def _make_proposal(
        self, snapshot, plan, source, submission_key, submission_version, policy, command,
        *, kind, target=None, confidence="uncertain", record_type=None, proposed_values=None,
        provided_fields=None, quote=None, span_start=None, span_end=None,
    ):
        quote = quote or plan.quote or (plan.source_text or "")[:300]
        if span_start is None or span_end is None:
            span_start, span_end = 0, len(quote)
        spec = ProposalSpec(
            source_key=source["source_key"],
            source_version=int(source["version"]),
            submission_key=submission_key,
            submission_version=submission_version,
            kind=kind,
            record_type=record_type or plan.record_type,
            quote=quote,
            span_start=span_start,
            span_end=span_end,
            proposed_values=(
                proposed_values if proposed_values is not None else _partial_values(plan)
            ),
            target_key=(target or {}).get("record_key"),
            target_content_token=(target or {}).get("content_token"),
            target_access_revision=(target or {}).get("access_revision"),
            provided_fields=(
                tuple(provided_fields)
                if provided_fields is not None
                else tuple(plan.provided_values.keys())
            ),
            explicit_clears=tuple(plan.explicit_clears),
            confidence=confidence,
            command_digest=command["request_digest"],
            lifecycle_epoch=snapshot["lifecycle_epoch"],
            policy_version=policy.version,
        )
        return create_proposal(snapshot, spec)

    def _match_existing(self, owner, plan):
        """Return ``(kind, target_item, confidence)`` or None for a new fact."""

        provided = plan.provided_values
        subject_field = _SUBJECT_FIELDS[plan.record_type]
        if subject_field not in provided or not _subject(plan.record_type, provided):
            raise ResumeIntakeValidationError(
                f"Add the {subject_field.replace('_', ' ')} for this entry."
            )
        subject = _normalized_subject(_subject(plan.record_type, provided))
        for item in self._canonical_items(owner):
            if item.get("record_type") != plan.record_type:
                continue
            existing_values = item.get("values") or {}
            existing_subject = _normalized_subject(_subject(plan.record_type, existing_values))
            if not existing_subject or existing_subject != subject:
                continue
            if _subject(plan.record_type, existing_values) != _subject(plan.record_type, provided):
                return "ambiguous_match", item, "similar"
            # A conflict is a *changed* existing value, not a newly supplied
            # detail: filling a previously empty field is an addition, while
            # rewriting or clearing a filled one contradicts the record. A
            # restatement that adds no new meaning is equivalent: the existing
            # entry and its permissions stay exactly as they are.
            conflict = False
            addition = False
            for name in EDITOR_FIELDS[plan.record_type]:
                if name in provided:
                    new = provided.get(name)
                    old = existing_values.get(name)
                    if _meaningful(new) and _meaningful(old) and new != old:
                        conflict = True
                        break
                    if _meaningful(new) and not _meaningful(old):
                        addition = True
                if name in plan.explicit_clears and _meaningful(existing_values.get(name)):
                    conflict = True
                    break
            if conflict:
                return "contradiction", item, "certain"
            if addition:
                return "additional_detail", item, "certain"
            return "equivalent", item, "certain"
        return None

    def _matching_shortlist(self, owner):
        """Member-scoped comparison candidates, minus private-AI exclusions.

        Only facts the member may use for private processing are comparable.
        When the exclusion source is unwired or unreadable the shortlist is
        empty on purpose: the adapter then reports new or uncertain and the
        member decides, instead of comparing material the member excluded.
        """

        try:
            items = self._canonical_items(owner)
        except ResumeIntakeUnavailableError:
            return []
        excluded: set = set()
        if self._matching_exclusions is None:
            return []
        try:
            excluded = set(self._matching_exclusions(owner) or ())
        except Exception:
            return []
        shortlist = []
        for item in items:
            key = item.get("record_key")
            if not key or key in excluded:
                continue
            shortlist.append({
                "record_key": key,
                "record_type": item.get("record_type"),
                "values": item.get("values") or {},
            })
        return shortlist

    def _extract_with_adapter(self, owner, plan):
        """Run strict Luna extraction, or report the provider failure.

        Returns ``(drafts, provider_issue)``. A failure keeps the member's
        input for the deterministic manual path and marks the result
        retryable: there is no fallback model, effort, or free-form mode.
        """

        text = plan.source_text or ""
        shortlist = self._matching_shortlist(owner)
        try:
            candidates = self._extraction_adapter.extract(
                text,
                allowed_fields={name: EDITOR_FIELDS[name] for name in EDITOR_FIELDS},
                shortlist=shortlist,
            )
        except ExtractionError as error:
            return None, error.code
        drafts = []
        for candidate in candidates:
            record_type = candidate.record_type
            if record_type == "unspecified" or candidate.outcome == "uncertain":
                kind = "inferred_wording"
            elif candidate.outcome == "new":
                kind = "new_fact"
            elif candidate.outcome == "additional_detail":
                kind = "additional_detail"
            elif candidate.outcome == "contradiction":
                kind = "contradiction"
            else:
                kind = "inferred_wording"
            drafts.append({
                "kind": kind,
                "record_type": record_type,
                "values": dict(candidate.values),
                "confidence": candidate.confidence,
                "outcome": candidate.outcome,
                "match_reference": candidate.match_reference,
                "provided_fields": list(candidate.provided_fields),
                "quote": candidate.quote,
                "span_start": candidate.span_start,
                "span_end": candidate.span_end,
            })
        return drafts, None

    def _resolve_equivalent(self, owner, draft):
        """Confirm an equivalent reference still exists, or return None."""

        reference = draft.get("match_reference")
        if not reference:
            return None
        try:
            item = self._find_item(owner, reference)
        except ResumeIntakeUnavailableError:
            return None
        if item is None:
            return None
        return {
            "record_key": item.get("record_key"),
            "record_type": item.get("record_type"),
        }

    def _resolve_matched_target(self, owner, draft):
        """Bind a matched outcome to the current owner-scoped fact, or None.

        Additional-detail and contradiction proposals overlay the listed
        member-owned item, carrying its content token and access revision so
        only the member's later accept can apply the change. A missing,
        excluded, unreadable, stale, or unlisted reference fails closed.
        """

        reference = draft.get("match_reference")
        if not isinstance(reference, str) or not reference:
            return None
        try:
            shortlist_keys = {
                entry.get("record_key")
                for entry in self._matching_shortlist(owner)
                if entry.get("record_key")
            }
            if reference not in shortlist_keys:
                return None
            item = self._find_item(owner, reference)
        except ResumeIntakeUnavailableError:
            return None
        if item is None:
            return None
        token = item.get("content_token")
        if not isinstance(token, str) or not token:
            return None
        if item.get("access_revision") is None:
            return None
        return item

    def _canonical_items(self, owner):
        """Read the owner's existing facts. Fail closed when unreadable.

        Treating an unreadable catalog as empty would let the composer save a
        duplicate and mis-route a change to an existing fact as a new one.
        """

        try:
            workspace = self.draft_service.get_workspace(owner)
        except (ResumeDraftUnavailableError, CanonicalReadUnavailable,
                ResumeDraftStoreUnavailable) as error:
            raise ResumeIntakeUnavailableError() from error
        items = workspace.get("items")
        if not isinstance(items, list):
            raise ResumeIntakeUnavailableError()
        return [item for item in items if not item.get("orphaned")]

    def _save_new_fact(self, owner, snapshot, unit, plan, submission_key):
        record_key = _stable_key(submission_key, f"fact:{plan.client_key}")
        try:
            normalized = normalize_editor_values(plan.record_type, plan.provided_values)
        except LivingResumeEditorValidationError as error:
            raise ResumeIntakeValidationError(str(error)) from error
        item_request_id = _stable_key(submission_key, f"request:{plan.client_key}")
        payload = {
            "request_id": item_request_id,
            "type": "create_private_item",
            "record_key": record_key,
            "record_type": plan.record_type,
            "parent_key": plan.parent_key,
            "values": normalized,
            "intended_permission_expansions": {"resume_display": False, "visitor_ai": False},
        }
        # A brand-new private fact is created by the EXISTING canonical editor
        # command (usp_CommitLivingResumeCommandForOwner), whose closed key set
        # and type vocabulary are extracted from PS-RESUME-EDIT-002. Calling the
        # draft procedure here would only write a receipt and create nothing.
        callee_command = {
            "command_id": item_request_id,
            "type": f"create_{plan.record_type}",
            "record_key": record_key,
            "parent_key": plan.parent_key,
            "expected_version": None,
            "values": normalized,
        }
        projected = {
            "record_key": record_key,
            "record_type": plan.record_type,
            "values": normalized,
            "proposed_values": None,
            "resume_display": False,
            "visitor_ai": False,
            "draft_overlay": False,
            "values_source": "member_supplied",
            "persisted": False,
        }
        try:
            applied = unit.apply_canonical_command(
                owner, payload, projected,
                boundary="living_resume", request_id=item_request_id,
                callee_command=callee_command,
            )
        except ResumeDraftConflictError as error:
            raise ResumeIntakeConflictError(
                error.error_code, error.conflicts,
                "That item already exists with different details.",
            ) from error
        except ResumeDraftValidationError as error:
            # A closed-value refusal from the canonical command boundary is a
            # safe 400, never an unhandled 500.
            raise ResumeIntakeValidationError(str(error)) from error
        except ResumeDraftNotFoundError as error:
            raise ResumeIntakeNotFoundError() from error
        except (ResumeDraftUnavailableError, ResumeDraftStoreUnavailable) as error:
            raise ResumeIntakeUnavailableError() from error
        applied = applied if isinstance(applied, dict) else {"item": applied}
        item = dict(applied.get("item") or projected)
        item["values_source"] = applied.get("values_source") or item.get("values_source")
        item["persisted"] = False
        item["resume_display"] = False
        item["visitor_ai"] = False
        item.setdefault("record_type", plan.record_type)
        return item

    def _apply_decision(self, owner, snapshot, unit, proposal, confirmed):
        target_key = proposal.get("target_key")
        record_type = proposal.get("record_type")
        values = dict((confirmed if confirmed is not None else proposal.get("confirmed_values")) or {})
        if record_type in {None, "unspecified"}:
            record_type = values.pop("record_type", None)
        if record_type not in STRUCTURED_RECORD_TYPES:
            raise ResumeIntakeConflictError(
                "reconciliation_required",
                [{"proposal_key": proposal["proposal_key"], "reason": "record_type_required"}],
                "Choose what this should become before saving it.",
                proposed=proposal.get("proposed_values"),
            )
        # ``parent_key`` is relationship metadata, not an editor field. It is
        # only meaningful when creating a child; an overlay change keeps the
        # existing parent.
        supplied_parent = values.pop("parent_key", None)
        unknown = set(values) - EDITOR_FIELDS[record_type]
        if unknown or (set(values) & FORBIDDEN_CLIENT_FIELDS):
            raise ResumeIntakeValidationError("Unknown value fields are not allowed.")
        if not target_key:
            resolved_parent = None
            if record_type == "accomplishment":
                resolved_parent = supplied_parent or proposal.get("parent_key")
                _parent, parent_reason = self._accomplishment_parent(owner, resolved_parent)
                if parent_reason is not None:
                    raise ResumeIntakeConflictError(
                        "reconciliation_required",
                        [{"proposal_key": proposal["proposal_key"], "reason": parent_reason}],
                        "Choose an eligible private draft role before saving it.",
                        proposed=proposal.get("proposed_values"),
                    )
            plan = _ItemPlan(
                client_key="proposal", kind="structured", record_type=record_type,
                provided_values=dict(values),
                parent_key=resolved_parent,
            )
            return self._save_new_fact(owner, snapshot, unit, plan, proposal["proposal_key"])
        # A change to an existing fact goes through B's private draft overlay,
        # against the versions captured when the proposal was made.
        existing = self._find_item(owner, target_key)
        if existing is None:
            raise ResumeIntakeNotFoundError()
        clears = list(proposal.get("explicit_clears") or [])
        merged = dict(existing.get("values") or {})
        merged.update(values)
        for name in clears:
            merged[name] = _empty_value(name)
        try:
            normalized = normalize_editor_values(record_type, merged)
        except LivingResumeEditorValidationError as error:
            raise ResumeIntakeValidationError(str(error)) from error
        partial = {name: normalized[name] for name in values}
        for name in clears:
            partial[name] = _empty_value(name)
        overlay_request_id = _stable_key(proposal["proposal_key"], "overlay")
        payload = {
            "request_id": overlay_request_id,
            "type": "save_item",
            "record_key": target_key,
            "record_type": existing.get("record_type") or record_type,
            "expected_content_token": proposal.get("target_content_token"),
            "expected_access_revision": proposal.get("target_access_revision"),
            "values": partial,
            "intended_permission_expansions": {"resume_display": False, "visitor_ai": False},
        }
        projected = {
            "record_key": target_key,
            "record_type": existing.get("record_type") or record_type,
            "proposed_values": partial,
            "draft_overlay": True,
            "resume_display": False,
            "visitor_ai": False,
            "values_source": "member_supplied",
            "persisted": False,
        }
        try:
            applied = unit.apply_canonical_command(
                owner, payload, projected,
                boundary="resume_draft", request_id=overlay_request_id,
                # The draft procedure takes @RequestId as its own parameter and
                # reads only its declared JSON keys, so the request id must not
                # appear inside the command body.
                callee_command={k: v for k, v in payload.items() if k != "request_id"},
            )
        except ResumeDraftConflictError as error:
            raise ResumeIntakeConflictError(
                error.error_code, error.conflicts,
                "That record changed. Your wording is still here.",
                proposed=partial,
            ) from error
        except ResumeDraftValidationError as error:
            raise ResumeIntakeValidationError(str(error)) from error
        except ResumeDraftNotFoundError as error:
            raise ResumeIntakeNotFoundError() from error
        except (ResumeDraftUnavailableError, ResumeDraftStoreUnavailable) as error:
            raise ResumeIntakeUnavailableError(proposed=partial) from error
        applied = applied if isinstance(applied, dict) else {"item": applied}
        item = dict(applied.get("item") or projected)
        item["values_source"] = applied.get("values_source") or item.get("values_source")
        item["persisted"] = False
        item["draft_overlay"] = True
        item["resume_display"] = False
        item["visitor_ai"] = False
        return item

    def _find_item(self, owner, record_key):
        for item in self._canonical_items(owner):
            if item.get("record_key") == record_key:
                return item
        return None

    def _accomplishment_parent(self, owner, record_key):
        if not record_key:
            return None, "parent_required"
        parent = self._find_item(owner, record_key)
        if parent is None:
            return None, "parent_not_found"
        if parent.get("record_type") != "role":
            return None, "parent_type_ineligible"
        if not _eligible_accomplishment_parent(parent):
            return None, "parent_ineligible"
        return parent, None

    @staticmethod
    def _default_interpreter(text, kind):
        """Deterministic default: report the member's own words as uncertain."""

        if not (text or "").strip():
            return []
        return [{
            "kind": "inferred_wording",
            "record_type": "unspecified",
            "values": {"text": text[:MAX_TEXT_UNITS]},
            "confidence": "uncertain",
        }]


def _partial_values(plan):
    values = dict(plan.provided_values)
    for name in plan.explicit_clears:
        values[name] = _empty_value(name)
    return values


_RECEIPT_WORD_FIELDS = frozenset({
    "quote", "proposed_values", "confirmed_values", "values", "transcript",
    "extracted_fields",
})

_EXTRACTED_CANDIDATES_FIELD = "_extracted_candidates"


def _source_extracted_candidates(source):
    raw = source.get("structured_values") if isinstance(source, dict) else None
    candidates = raw.get(_EXTRACTED_CANDIDATES_FIELD) if isinstance(raw, dict) else None
    return candidates if isinstance(candidates, list) else []


def _bind_extracted_candidates(source, duplicates, submission_key, client_key):
    """Bind each equivalent to mutable source state; return identifier actions."""

    candidates = list(_source_extracted_candidates(source))
    actions = []
    for index, duplicate in enumerate(duplicates):
        override_key = _stable_key(
            submission_key, f"keep-separate:{client_key}:{index}"
        )
        record_type = duplicate.get("record_type")
        candidate = {
            "override_key": override_key,
            "record_type": record_type,
            "record_key": duplicate.get("record_key"),
            "source_key": source["source_key"],
            "source_version": int(source.get("version") or 1),
            "state": "pending",
            "values": copy.deepcopy(duplicate.get("extracted_fields") or {}),
        }
        candidates.append(candidate)
        actions.append({
            "override_key": override_key,
            "record_type": record_type,
            "record_key": duplicate.get("record_key"),
        })
    source["structured_values"] = {_EXTRACTED_CANDIDATES_FIELD: candidates}
    return actions


def receipt_for_storage(receipt):
    """Strip member wording from a receipt before it is stored immutably.

    The immutable receipt keeps the structural outcome (ids, outcomes, counts,
    codes, messages) and is what a same-key retry replays. The member's own
    words live only in the mutable source and proposal rows, which is what
    source purge can redact -- so no receipt copy can resurrect purged text.
    Extracted keep-separate candidates live only in mutable source-bound state;
    immutable receipts retain their identifier-only actions.
    """

    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items() if key not in _RECEIPT_WORD_FIELDS}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(dict(receipt))


def _public_keep_separate(keep):
    """Member-visible keep-separate action. Never returns extracted fields."""

    if not isinstance(keep, dict):
        return keep
    if keep.get("override_key"):
        return {
            "override_key": keep["override_key"],
            "record_type": keep.get("record_type"),
            "record_key": keep.get("record_key"),
        }
    return keep


def _present_intake_receipt(receipt):
    if not isinstance(receipt, dict):
        return receipt
    presented = copy.deepcopy(receipt)
    for row in presented.get("results") or []:
        if isinstance(row, dict) and "keep_separate" in row:
            row["keep_separate"] = _public_keep_separate(row.get("keep_separate"))
        if isinstance(row, dict) and "keep_separate_actions" in row:
            row["keep_separate_actions"] = [
                _public_keep_separate(keep)
                for keep in (row.get("keep_separate_actions") or [])
            ]
    return presented


def _job_kind(kind):
    return {
        "structured": "text_interpretation",
        "text": "text_interpretation",
        "document": "document_parse",
        "recording": "voice_transcription",
    }[kind]


def _submission_payload(command, snapshot, receipt):
    """The exact command JSON the declared submission procedure consumes."""

    submission_key = receipt["submission"]["submission_key"]
    return {
        "type": "add_submission",
        "request_id": command["request_id"],
        "submission_key": submission_key,
        "submission_version": receipt["submission"]["version"],
        "entrance": receipt["submission"]["entrance"],
        "policy_version": receipt["submission"]["policy_version"],
        "lifecycle_epoch": snapshot["lifecycle_epoch"],
        "request_digest": command["request_digest"],
        "sources": [
            {
                "source_key": source["source_key"],
                "kind": source["kind"],
                "state": source["state"],
                "version": source["version"],
                "text": source.get("text"),
                "structured_values": source.get("structured_values"),
                "content_type": source.get("content_type"),
                "byte_length": source.get("byte_length"),
                "sha256": source.get("sha256"),
                "created_at_utc": source.get("created_at"),
            }
            for source in snapshot["sources"].values()
            if source.get("submission_key") == submission_key
        ],
        "jobs": [
            {
                "job_key": job["job_key"],
                "kind": job["kind"],
                "state": job["state"],
                "result": job.get("result"),
                "outcome": job.get("outcome"),
                "source_key": job["fence"]["source_key"],
                "source_version": job["fence"]["source_version"],
                "submission_key": job["fence"]["submission_key"],
                "submission_version": job["fence"]["submission_version"],
                "policy_version": job["fence"]["policy_version"],
                "lifecycle_epoch": job["fence"]["lifecycle_epoch"],
            }
            for job in snapshot["jobs"].values()
            if job["fence"]["submission_key"] == submission_key
        ],
        "proposals": [
            {
                "proposal_key": row["proposal_key"],
                "kind": row["kind"],
                "record_type": row["record_type"],
                "target_key": row.get("target_key"),
                "target_content_token": row.get("target_content_token"),
                "target_access_revision": row.get("target_access_revision"),
                "quote": row.get("quote"),
                "span_start": row.get("span_start"),
                "span_end": row.get("span_end"),
                "proposed_values": row.get("proposed_values"),
                "provided_fields": row.get("provided_fields"),
                "explicit_clears": row.get("explicit_clears"),
                "requires_member_wording": row.get("requires_member_wording"),
                "confidence": row.get("confidence"),
                "command_digest": row.get("command_digest"),
                "binding": row.get("binding"),
            }
            for row in snapshot["proposals"].values()
            if row["proposal_key"] in receipt["submission"]["proposal_keys"]
        ],
        "results": receipt["results"],
        "summary": receipt["summary"],
        # Durable last receipt, so a refresh after reload shows the confirmed
        # outcome instead of "nothing added yet".
        "last_receipt": snapshot["last_receipt"],
        # The immutable structural result, replayed verbatim on a same-key retry.
        "receipt": receipt,
    }


def _summarize(results):
    saved = sum(1 for row in results if row.get("outcome") == "saved")
    unresolved = sum(1 for row in results if row.get("outcome") == "unresolved")
    failed = sum(1 for row in results if row.get("outcome") == "failed")
    duplicates = sum(1 for row in results if row.get("outcome") == "duplicate")
    counted = saved + unresolved + failed + duplicates
    if failed and counted == failed:
        outcome = "failed"
    elif duplicates and counted == duplicates:
        outcome = "duplicate"
    elif unresolved and not saved and not failed and not duplicates:
        outcome = "unresolved"
    elif saved and not failed and not unresolved and not duplicates:
        outcome = "saved"
    else:
        outcome = "partial"
    return {
        "outcome": outcome,
        "saved": saved,
        "unresolved": unresolved,
        "failed": failed,
        "duplicates": duplicates,
        "total": len(results),
        "all_saved": bool(results) and saved == len(results),
    }


def _receipt_message(summary):
    if summary["all_saved"]:
        return "Saved privately. Display and visitor AI stay off."
    if summary.get("duplicates") and summary["total"] == summary["duplicates"]:
        return "Already saved. Nothing new was added."
    parts = []
    if summary["saved"]:
        parts.append(f"{summary['saved']} saved privately")
    if summary["unresolved"]:
        parts.append(f"{summary['unresolved']} needs your review")
    if summary["failed"]:
        parts.append(f"{summary['failed']} could not be saved")
    if summary.get("duplicates"):
        parts.append(f"{summary['duplicates']} already saved")
    return "Some of that Add was not saved: " + "; ".join(parts) + "."


def _draft_expires_at(row, inactivity_days):
    """Parse one draft row's expiry moment, or None when it never expires."""

    if inactivity_days is None:
        return None
    raw = (row or {}).get("expires_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _draft_expiry_iso(moment, inactivity_days):
    if inactivity_days is None:
        return None
    return (moment + timedelta(days=int(inactivity_days))).isoformat()


def present_draft(row):
    """Member-visible draft view. Never exposes another owner's rows."""

    return {
        "draft_key": row.get("draft_key") or DRAFT_KEY,
        "version": int(row.get("version") or 0),
        "state": row.get("state") or "active",
        "text": row.get("text"),
        "items": [dict(item) for item in (row.get("items") or [])],
        "attachments": [dict(item) for item in (row.get("attachments") or [])],
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "expires_at": row.get("expires_at"),
    }


def sweep_drafts(snapshot, *, now=None, inactivity_days=30):
    """Drop expired composer drafts. Pure helper for the future expiry worker.

    Reads already enforce expiry, so behavior holds with no worker running;
    the worker only reclaims storage. Returns the expired draft count.
    """

    if inactivity_days is None:
        return 0
    moment = _utc(now)
    drafts = snapshot.get("drafts") or {}
    expired = [
        key for key, row in drafts.items()
        if _draft_expires_at(row, inactivity_days) is not None
        and moment >= _draft_expires_at(row, inactivity_days)
    ]
    for key in expired:
        del drafts[key]
    return len(expired)


def _current_intake_service():
    """Resolve the live service, preferring an injected app-configured one."""

    try:
        from flask import current_app

        injected = current_app.config.get("RESUME_INTAKE_SERVICE")
        if isinstance(injected, ResumeIntakeService):
            return injected
    except Exception:  # noqa: BLE001 - no request/app context, or no Flask
        pass
    return resume_intake_service


def observe_manual_edit(owner, command_type, record_key, result) -> None:
    """A committed manual editor command fences pending intake references.

    Best-effort across the two stores for the in-memory adapter: the proposed
    SQL commits the manual edit and this invalidation in one transaction, while
    the test-only adapter can only do it after the editor commit. Either way a
    pending proposal can never be accepted against a record the member has
    since edited, and no proposed wording is lost.
    """

    if command_type not in {"save_item", "discard_item"} or not record_key:
        return
    service = _current_intake_service()
    if not isinstance(service, ResumeIntakeService):
        return
    try:
        snapshot = service.repository.load_owner(owner)
    except ResumeIntakeStoreUnavailable:
        return
    if not snapshot:
        return
    snapshot.setdefault("proposals", {})
    affected = invalidate_proposals_for_target(snapshot, str(record_key))
    if not affected:
        return
    try:
        service.repository.save_owner(owner, snapshot)
    except ResumeIntakeStoreUnavailable:
        return


def register_manual_edit_observer() -> None:
    from services.resume_draft_service import register_commit_observer

    register_commit_observer(observe_manual_edit)


resume_intake_service = ResumeIntakeService()
