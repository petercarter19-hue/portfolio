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
    _normalize_draft_values,
)
from services.resume_intake_document_adapter import (
    DocumentIntakeError,
    ResumeDocumentAdapter,
    resume_document_adapter,
)
from services.my_data_extraction_adapter import (
    ExtractionError,
    MyDataExtractionAdapter,
    ResumeOrganization,
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
    binding_is_current,
    decide as decide_proposal_record,
    invalidate as invalidate_proposal,
    invalidate_for_source as invalidate_proposals_for_source,
    invalidate_for_target as invalidate_proposals_for_target,
    present as present_proposal,
    redact_source_text,
)
from services.resume_intake_repository import (
    COMMAND_PROCEDURES,
    InMemoryResumeIntakeRepository,
    SqlIntakeUnitOfWork,
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
            "issue_date_precision",
            "expiration_date_precision",
            "verification_url",
            "completion_status",
        }
    ),
    "skill": frozenset({"name", "summary"}),
    "accomplishment": frozenset({"wording", "metric_value", "metric_label"}),
}
BOOLEAN_FIELDS = frozenset({"current_role"})
# Conversation-only fields do not widen the manual editor's field contract.
# This same closed set drives validation and the model's control/schema catalog.
CONVERSATION_FIELDS = {
    **EDITOR_FIELDS,
    "credential": EDITOR_FIELDS["credential"] | {"resume_credential_wording"},
    "knowledge": frozenset({"title", "wording", "classification"}),
}
CONVERSATION_BULLET_FIELDS = frozenset({"summary", "wording", "resume_credential_wording"})


def conversation_field_contract():
    """Fresh server-owned control metadata, never member/source evidence."""
    return {"schema_version": 1, "record_types": {
        record_type: {
            "value_fields": sorted(fields),
            "explicit_clear_fields": sorted(fields),
            "bullet_edit_fields": sorted(fields & CONVERSATION_BULLET_FIELDS),
            "boolean_fields": sorted(fields & BOOLEAN_FIELDS),
        }
        for record_type, fields in sorted(CONVERSATION_FIELDS.items())
    }}


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
        original_files=None,
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
        self.original_files = original_files
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
        history = self._resume_history(snapshot)
        policy = self.policy()
        guide = snapshot.get("guide") or {}
        pending = [
            present_proposal(row)
            for row in snapshot["proposals"].values()
            if row["state"] == "pending"
        ]
        pending.sort(key=lambda row: row["created_at"] or "")
        recovery = self._recovery_inventory(owner, snapshot)
        for row in pending:
            undo = recovery.get('undo:' + row['proposal_key'])
            if undo:
                row['undo_exclusion_token'] = undo['token']
        return {
            "entrance": policy.entrance,
            "policy": policy.as_document(),
            "lifecycle_epoch": snapshot["lifecycle_epoch"],
            "guide": {
                "status": guide.get("status") or "not_started",
                "status_source": guide.get("status_source") or "default_unstarted",
            },
            "pending_proposals": pending,
            "review_overview": self._review_overview(snapshot),
            "resume_section_bindings": history['section'],
            "resume_excluded_records": list(history['inclusion'].items()),
            "resume_recoverable_details": [
                {'recovery_key': key, 'recovery_token': value['token'],
                 'label': value['label'], 'text': value['text']}
                for key, value in recovery.items() if not key.startswith('undo:')],
            "resume_credential_bindings": list(history['credential'].values()),
            "resume_decision_conflicts": history['conflicts'],
            "conversation_turns": [self._conversation_response(snapshot, source)
                for source in snapshot['sources'].values() if source.get('state') == 'active'
                and ((source.get('structured_values') or {}).get('resume_conversation_v1') or {}).get('turn_state') == 'completed'],
            "source_accounting": [
                {"source_key": source["source_key"], "source_version": source["version"],
                 "kind": source["kind"], "text": source.get("text"),
                 **copy.deepcopy((source.get("structured_values") or {})["resume_conversation_v1"])}
                for source in snapshot["sources"].values()
                if source.get("state") == "active" and isinstance(source.get("structured_values"), dict)
                and "resume_conversation_v1" in source["structured_values"]
            ],
            "last_receipt": snapshot.get("last_receipt"),
            "receipts_count": len(snapshot["receipts"]),
            "capabilities": {
                "commands": sorted(COMMAND_TYPES),
                "structured_record_types": sorted(STRUCTURED_RECORD_TYPES),
                "editor_fields": {name: sorted(fields) for name, fields in EDITOR_FIELDS.items()},
                "supports_explicit_clear": True,
                "supports_resume_conversation": bool(getattr(self.repository, "supports_resume_conversation", False)),
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

    # -- durable conversational ingress --------------------------------

    @staticmethod
    def _latest_resume_decision(snapshot, rows, value):
        """Choose accepted chronology, never object order or creation order.

        Sequenced decisions are authoritative. Legacy decision timestamps and
        explicit accepted revision chains can establish chronology; source
        creation/dependencies cannot prove which pending choice was approved
        first. An unknowable conflicting legacy history requires owner review.
        """
        def sequence(row):
            n = (row.get('resume_conversation_v1') or {}).get('decision_order')
            return n if type(n) is int and n > 0 else 0

        def ancestor(older, newer):
            key, seen = newer.get('proposal_key'), set()
            while key and key not in seen:
                seen.add(key)
                row = snapshot['proposals'].get(key) or {}
                key = (row.get('resume_conversation_v1') or {}).get('revision_of')
                if key == older.get('proposal_key'):
                    return True
            return False

        def timestamp(row):
            try:
                stamp = datetime.fromisoformat(row.get('decided_at') or '')
                return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
            except (TypeError, ValueError):
                return None

        def later(newer, older):
            a, b = sequence(newer), sequence(older)
            if a or b:
                return a > b
            if ancestor(older, newer):
                return True
            if ancestor(newer, older):
                return False
            a, b = timestamp(newer), timestamp(older)
            return a is not None and b is not None and a > b

        maximum = max([0] + [sequence(row) for row in rows])
        if maximum:
            rows = [row for row in rows if sequence(row) == maximum]
        latest = [row for row in rows if not any(later(other, row) for other in rows)]
        if latest and len({_json_digest(value(row)) for row in latest}) == 1:
            # Identical effects need no chronological guess. A stable key is
            # used only after proving that every surviving choice is identical.
            return min(latest, key=lambda row: row['proposal_key'])
        return None

    @classmethod
    def _resume_history(cls, snapshot):
        groups = {name: {} for name in ('section', 'inclusion', 'credential', 'bullets')}
        result = {**{name: {} for name in groups}, 'conflicts': []}
        for row in snapshot['proposals'].values():
            if row.get('state') != 'accepted':
                continue
            meta = row.get('resume_conversation_v1') or {}
            key = row.get('saved_record_key') or row.get('target_key')
            if not key:
                continue
            effects = {}
            if meta.get('presentation_section'):
                effects['section'] = meta['presentation_section']
            if meta.get('resume_exclusion') or meta.get('resume_restoration'):
                effects['inclusion'] = bool(meta.get('resume_exclusion'))
            if isinstance(meta.get('approved_credential_binding'), dict):
                effects['credential'] = meta['approved_credential_binding']
            if 'excluded_bullets' in meta:
                effects['bullets'] = meta['excluded_bullets']
            for effect, value in effects.items():
                groups[effect].setdefault(key, []).append((row, value))
        for effect, records in groups.items():
            for key, pairs in records.items():
                values = {row['proposal_key']: value for row, value in pairs}
                latest = cls._latest_resume_decision(snapshot, [row for row, _ in pairs],
                    lambda row: values[row['proposal_key']])
                if latest:
                    result[effect][key] = copy.deepcopy(values[latest['proposal_key']])
                    continue
                # No raw source/proposal wording is added. Retained approved
                # effects are owner-only and purge already redacts bullet text.
                result['conflicts'].append({'record_key': key, 'effect': effect,
                    'history_token': _json_digest(sorted([
                        {'proposal_key': row['proposal_key'], 'value': value,
                         'decided_at': row.get('decided_at'),
                         'decision_order': (row.get('resume_conversation_v1') or {}).get('decision_order')}
                        for row, value in pairs], key=lambda row: row['proposal_key'])),
                    'choices': [{'proposal_key': row['proposal_key'], 'value': copy.deepcopy(value)}
                        for row, value in sorted(pairs, key=lambda pair: pair[0]['proposal_key'])]})
        result['conflicts'].sort(key=lambda row: (row['record_key'], row['effect']))
        return result

    @classmethod
    def _credential_bindings(cls, snapshot):
        history = cls._resume_history(snapshot)
        if any(row['effect'] == 'credential' for row in history['conflicts']):
            raise ResumeIntakeConflictError('history_review_required', history['conflicts'],
                'Review the saved Resume choices in the guide. Your approved information is kept.')
        return list(history['credential'].values())

    @staticmethod
    def _source_unit_proposals(snapshot, source_key, unit):
        keys = set(unit.get('proposal_keys') or [])
        if unit.get('proposal_key'):
            keys.add(unit['proposal_key'])
        for proposal in snapshot['proposals'].values():
            metadata = proposal.get('resume_conversation_v1') or {}
            if ({'source_key': source_key, 'unit_id': unit['unit_id']} in (metadata.get('source_refs') or [])
                    or (proposal.get('binding') or {}).get('source_key') == source_key
                    and unit['unit_id'] in (metadata.get('unit_ids') or [])):
                keys.add(proposal['proposal_key'])
        # Earlier source units remain bound through revisions, independently
        # of dictionary order or a legacy scalar's last assignment.
        latest = {}
        for key in keys:
            seen = set()
            row = snapshot['proposals'].get(key)
            while row and row.get('superseded_by') and row['proposal_key'] not in seen:
                seen.add(row['proposal_key'])
                row = snapshot['proposals'].get(row['superseded_by'])
            if row:
                latest[row['proposal_key']] = row
        return list(latest.values())

    def _conversation_view(self, snapshot, canonical, *, exclude_source=None):
        """Full authorized context; client-provided facts never enter this read."""
        from services.resume_onboarding_document_reader import inventory_source
        history = self._resume_history(snapshot)
        if history['conflicts']:
            raise ResumeIntakeConflictError('history_review_required', history['conflicts'],
                'Review the saved Resume choices in the guide before continuing. Your approved information is kept.')
        eligible = {row['source_id']: row for row in canonical['sources']}
        links = {b['credential_key']: b for b in history['credential'].values()}
        note_keys = {b['supplement_key'] for b in links.values()}
        restricted_parents = {key for key, b in links.items() if b['supplement_key'] not in eligible}
        resume_exclusions = history['inclusion']
        targets, materials, turns = [], [], []
        authorized_records = set(eligible) - restricted_parents
        def unit_records(source_key, unit):
            # Scalar legacy accounting was last-writer-wins. Reconstruct its
            # complete cohort from the retained source references as well as
            # the explicit multi-record bindings used by new decisions.
            records = set(unit.get('record_keys') or [])
            if unit.get('record_key'):
                records.add(unit['record_key'])
            for proposal in self._source_unit_proposals(snapshot, source_key, unit):
                records.update(filter(None, (proposal.get('target_key'), proposal.get('saved_record_key'))))
            return records
        for row in canonical['sources']:
            # A credential cannot be revised without its authorized complete
            # limitations. The attached note remains excluded from private AI.
            if row['source_id'] in note_keys or row['source_id'] in restricted_parents:
                continue
            values = copy.deepcopy(row['values'])
            link = links.get(row['source_id'])
            note = eligible.get((link or {}).get('supplement_key'))
            if note is not None and row['record_type'] == 'credential':
                values['resume_credential_wording'] = note['values']['wording']
            targets.append({'target_ref': 'record:' + row['source_id'],
                'record_type': row['record_type'], 'values': values,
                'content_token': row['content_token'], 'access_revision': row['access_revision'],
                'resume_excluded': resume_exclusions.get(row['source_id'], False)})
        for row in snapshot['proposals'].values():
            excluded_pending = (row['state'] == 'accepted' and not row.get('saved_record_key')
                and (row.get('resume_conversation_v1') or {}).get('resume_exclusion'))
            if (row['state'] != 'pending' and not excluded_pending) or row.get('source_purged') or row.get('superseded_by'):
                continue
            if row.get('target_key') and row['target_key'] not in eligible:
                continue
            if row.get('target_key') in restricted_parents:
                continue
            source = snapshot['sources'].get((row.get('binding') or {}).get('source_key'))
            if not source or source.get('state') != 'active':
                continue
            base = next((target for target in targets if target['target_ref'] == 'record:' + str(row.get('target_key'))), None)
            values = {**copy.deepcopy((base or {}).get('values') or {}), **copy.deepcopy(row['proposed_values'])}
            for name in row.get('explicit_clears') or []:
                values[name] = _empty_value(name)
            targets.append({'target_ref': 'proposal:' + row['proposal_key'],
                'record_type': row['record_type'], 'values': values,
                'source_refs': copy.deepcopy((row.get('resume_conversation_v1') or {}).get('source_refs') or []),
                'binding': copy.deepcopy(row['binding']),
                'resume_excluded': bool(excluded_pending),
                'presentation_section': (row.get('resume_conversation_v1') or {}).get('presentation_section')})
        for source in snapshot['sources'].values():
            if source.get('state') != 'active' or source['source_key'] == exclude_source:
                continue
            meta = (source.get('structured_values') or {}).get('resume_conversation_v1') or {}
            if meta.get('turn_state') in {'reserved', 'failed', 'changed'}:
                continue
            units = copy.deepcopy(meta.get('source_units') or inventory_source(source.get('text') or ''))
            # A previously approved unit may now be excluded from private AI.
            # Do not reintroduce it via its original uploaded document.
            units = [u for u in units if unit_records(source['source_key'], u) <= authorized_records]
            if units:
                materials.append({'source_key': source['source_key'], 'version': source['version'],
                    'kind': source['kind'], 'units': units})
            if meta.get('turn_state') == 'completed' and units:
                turn = {'source_key': source['source_key'], 'statement': '\n'.join(u['text'] for u in units),
                    'proposal_keys': [key for key in meta.get('proposal_keys') or []
                        if 'proposal:' + key in {target['target_ref'] for target in targets}],
                    'turn_order': meta.get('turn_order'), 'created_at': source.get('created_at')}
                controls = meta.get('control_bindings')
                # Assistant wording is conversational control, never a source
                # unit. Old unbound replies remain withheld; new replies carry
                # every record and source that the provider could have used.
                if (isinstance(controls, dict) and set(controls.get('record_keys') or []) <= authorized_records
                        and all(snapshot['sources'].get(binding['source_key'], {}).get('state') == 'active'
                            and snapshot['sources'][binding['source_key']]['version'] == binding['version']
                            for binding in controls.get('sources') or [])
                        and all(unit_records(binding['source_key'], unit) <= authorized_records
                            for binding in controls.get('sources') or []
                            for unit in ((snapshot['sources'][binding['source_key']].get('structured_values') or {})
                                .get('resume_conversation_v1') or {}).get('source_units') or [])):
                    turn['assistant_control'] = {'response': meta.get('response') or '',
                        'question': meta.get('next_question') or ''}
                turns.append(turn)
        for target in targets:
            target['bullets'] = {name: [{'index': index, 'text': line} for index, line in enumerate(value.splitlines())]
                for name, value in target['values'].items() if name in {'summary', 'wording', 'text', 'resume_credential_wording'} and isinstance(value, str)}
            # Removed bullets remain visible as evidence for an explicit undo.
            target['excluded_bullets'] = []
            if target['target_ref'].startswith('proposal:'):
                raw = snapshot['proposals'][target['target_ref'].split(':', 1)[1]]
                target['excluded_bullets'] = copy.deepcopy((raw.get('resume_conversation_v1') or {}).get('excluded_bullets') or [])
            else:
                target['excluded_bullets'] = copy.deepcopy(history['bullets'].get(target['target_ref'].split(':', 1)[1], []))
        turns.sort(key=lambda turn: (turn.get('turn_order') or 0, turn.get('created_at') or '', turn['source_key']))
        guide = (snapshot.get('drafts', {}).get(DRAFT_KEY) or {}).get('guide_state') or {}
        intent = guide.get('conversation_intent')
        guide_control = {'intent': intent if intent in {'story', 'project'} else 'resume',
            'screen': guide.get('screen'),
            'section': {'story': 'My Story', 'project': 'Projects'}.get(intent),
            'purpose': {'story': 'Optional personal story: a hobby, turning point, or something the member cares about.',
                'project': 'Optional project: what the member did and what changed.'}.get(intent,
                'Organize or refine supplied Resume content; ask only optional contextual questions.')}
        selected = snapshot['proposals'].get(guide.get('selected_proposal_key')) or {}
        selected_ref = 'proposal:' + str(selected.get('proposal_key'))
        if selected.get('state') == 'accepted':
            selected_ref = 'record:' + str(selected.get('saved_record_key') or selected.get('target_key'))
        selected_target = next((target for target in targets if target['target_ref'] == selected_ref), None)
        if selected_target:
            guide_control['selected_target'] = selected_ref
            if intent not in {'story','project'}:
                guide_control['section'] = (selected.get('resume_conversation_v1') or {}).get('presentation_section')
        return {'canonical': copy.deepcopy(canonical), 'targets': targets,
                'materials': materials, 'prior_turns': turns,
                'guide_control': guide_control, 'field_contract': conversation_field_contract(),
                'lifecycle_epoch': snapshot['lifecycle_epoch'], 'policy_version': snapshot['policy_version']}

    def _conversation_response(self, snapshot, source, *, replayed=False):
        meta = (source.get('structured_values') or {}).get('resume_conversation_v1') or {}
        rows = [present_proposal(snapshot['proposals'][key]) for key in meta.get('proposal_keys') or []
                if key in snapshot['proposals'] and snapshot['proposals'][key]['state'] == 'pending']
        return {'state': 'proposal' if rows else 'conversation', 'source_key': source['source_key'],
            'request_id': meta.get('request_id'), 'base_revision': meta.get('base_revision'),
            'response': meta.get('response') or 'This turn is no longer available.',
            'next_question': meta.get('next_question') or '', 'proposals': rows,
            'topic_skipped': meta.get('topic_skipped') is True,
            'saved': False, 'publishes': False, 'confirmation_required': bool(rows), 'replayed': replayed}

    @staticmethod
    def _recovery_row_token(row):
        # Supersession is retained separately: one pending recovery may be the
        # row's successor, but changes to the original decision are not allowed.
        return _json_digest({key: value for key, value in row.items() if key != 'superseded_by'})

    def _bullet_recovery_positions(self, rows, field, current, excluded):
        """Reconstruct literal ordinals; equal wording never identifies a bullet.

        Replay retained, sequenced edits over individual line identities. A
        later free-form field rewrite or unknowable legacy order refuses this
        route rather than inventing an insertion position.
        """
        relevant = [row for row in rows if field in (row.get('confirmed_values') or {})
            or any(edit['field'] == field for edit in (row.get('resume_conversation_v1') or {}).get('bullet_edits') or [])]
        if not relevant:
            return []
        nodes, ledger = None, []
        for row in relevant:
            meta = row['resume_conversation_v1']
            edits = [(i, edit) for i, edit in enumerate(meta.get('bullet_edits') or []) if edit['field'] == field]
            after = (row.get('confirmed_values') or {}).get(field)
            if not isinstance(after, str):
                return []
            lines = after.splitlines()
            if nodes is None:
                before = list(lines)
                for _, edit in reversed(edits):
                    index = edit['index']
                    if edit['action'] == 'exclude':
                        if index > len(before): return []
                        before.insert(index, edit['expected_text'])
                    else:
                        expected = edit['replacement'] if edit['action'] == 'revise' else edit['expected_text']
                        if index >= len(before) or before[index] != expected: return []
                        if edit['action'] == 'include': before.pop(index)
                        else: before[index] = edit['expected_text']
                nodes = [{'text': text, 'hidden': False, 'identity': None} for text in before]
            if not edits:
                visible = [node['text'] for node in nodes if not node['hidden']]
                if visible != lines:
                    if ledger: return []
                    nodes = [{'text': text, 'hidden': False, 'identity': None} for text in lines]
            for ordinal, edit in edits:
                visible = [node for node in nodes if not node['hidden']]
                index = edit['index']
                if edit['action'] == 'include':
                    identity = meta.get('recovery_bullet_identity')
                    node = next((node for node in ledger if node['text'] == edit['expected_text']
                        and (not identity or node['identity'] == identity)), None)
                    if node is None or sum(not n['hidden'] for n in nodes[:nodes.index(node)]) != index: return []
                    node['hidden'] = False; ledger.remove(node)
                else:
                    if index >= len(visible) or visible[index]['text'] != edit['expected_text']: return []
                    node = visible[index]
                    if edit['action'] == 'revise': node['text'] = edit['replacement']
                    else:
                        node.update(hidden=True, identity=[row['proposal_key'], ordinal],
                            retained={'field': field, 'index': index, 'text': edit['expected_text']})
                        ledger.append(node)
            if [node['text'] for node in nodes if not node['hidden']] != lines:
                return []
            expected = [bullet for bullet in meta.get('excluded_bullets') or [] if bullet['field'] == field]
            if [node['retained'] for node in ledger] != expected:
                return []
        if [node['text'] for node in nodes if not node['hidden']] != current.splitlines(): return []
        if [node['retained'] for node in ledger] != excluded: return []
        return [{'identity': node['identity'], 'index': sum(not n['hidden'] for n in nodes[:nodes.index(node)])}
            for node in ledger]

    def _recovery_inventory(self, owner, snapshot, *, allow_child=None):
        if not getattr(self.repository, 'supports_resume_conversation', False):
            return {}
        history, result = self._resume_history(snapshot), {}
        conflicted = {row['record_key'] for row in history['conflicts']}
        def current(row):
            if row.get('source_purged') or not binding_is_current(snapshot, row): return False
            linked = (row.get('resume_conversation_v1') or {}).get('credential_binding')
            if linked:
                note = self._find_item(owner, linked.get('supplement_key'))
                if (not note or linked.get('owner_user_key') != owner
                        or note['content_token'] != linked.get('supplement_content_token')
                        or note['access_revision'] != linked.get('supplement_access_revision')
                        or _json_digest({**note['values'], **(note.get('proposed_values') or {})}) != linked.get('supplement_values_digest')):
                    return False
            return True
        def leaf(row):
            return not row.get('superseded_by') or row.get('superseded_by') == allow_child
        def target_for(row):
            target = self._find_item(owner, row['target_key']) if row.get('target_key') else None
            if (target and target['content_token'] == row.get('target_content_token')
                    and target['access_revision'] == row.get('target_access_revision')
                    and (row.get('resume_conversation_v1') or {}).get('target_values_digest') ==
                        _json_digest({**target['values'], **(target.get('proposed_values') or {})})):
                return target
            return None
        def add(key, original, values, metadata, target=None, *, label, text, proof=None, template=None):
            if not current(original): return
            if target and any(row['state'] == 'pending' and row.get('target_key') == target['record_key']
                    and row['proposal_key'] not in {original['proposal_key'], allow_child}
                    for row in snapshot['proposals'].values()): return
            descriptor = {'original_key': original['proposal_key'], 'values': copy.deepcopy(values),
                'metadata': copy.deepcopy(metadata), 'target': copy.deepcopy(target),
                'label': label, 'text': text, 'template_key': (template or original)['proposal_key']}
            descriptor['token'] = _json_digest({'owner': owner, 'key': key,
                'original': self._recovery_row_token(original), 'lifecycle_epoch': snapshot['lifecycle_epoch'],
                'source': snapshot['sources'][original['binding']['source_key']]['version'],
                'values': values, 'metadata': metadata, 'target': target, 'proof': proof})
            result[key] = descriptor
        for row in snapshot['proposals'].values():
            meta = row.get('resume_conversation_v1') or {}
            if not leaf(row) or not current(row): continue
            exclusion = meta.get('resume_exclusion') or any(
                edit.get('action') == 'exclude' for edit in meta.get('bullet_edits') or [])
            prior = snapshot['proposals'].get(meta.get('revision_of')) if exclusion else None
            pending_lineage = bool(prior and prior['state'] == 'invalidated' and current(prior)
                and prior.get('superseded_by') == row['proposal_key']
                and prior.get('target_key') == row.get('target_key'))
            target = target_for(row)
            if row.get('target_key') and not target: continue
            if pending_lineage and prior.get('target_key') and target_for(prior) != target: continue
            if exclusion and row['state'] == 'pending':
                if pending_lineage:
                    add('undo:' + row['proposal_key'], row, prior['proposed_values'],
                        prior.get('resume_conversation_v1') or {}, target, label='Undo exclusion',
                        text='Return the original suggestion to review.', proof=self._recovery_row_token(prior), template=prior)
                elif target:
                    add('undo:' + row['proposal_key'], row, {}, {}, target,
                        label='Undo exclusion', text='Keep the current saved entry.')
            if row['state'] not in {'accepted', 'rejected'}: continue
            if pending_lineage:
                # Accepted saved exclusions are recovered through their saved
                # history below, rather than replaying the earlier revision.
                if target and row['state'] != 'rejected': continue
            elif row['state'] == 'rejected' and not row.get('target_key') and not row.get('saved_record_key') and not exclusion:
                prior = row
            else: continue
            values = prior['proposed_values']
            title = values.get('role_title') or values.get('name') or values.get('title') or 'Imported suggestion'
            add('proposal:' + row['proposal_key'], row, values, prior.get('resume_conversation_v1') or {}, target,
                label='Review original details: ' + str(title), text=prior.get('quote') or '',
                proof=self._recovery_row_token(prior), template=prior)
        for record_key in set(history['inclusion']) | set(history['bullets']):
            if record_key in conflicted: continue
            target = self._find_item(owner, record_key)
            if not target: continue
            values = {**target['values'], **(target.get('proposed_values') or {})}
            title = values.get('role_title') or values.get('name') or values.get('title') or 'Saved entry'
            rows = [row for row in snapshot['proposals'].values() if row['state'] == 'accepted'
                and (row.get('saved_record_key') or row.get('target_key')) == record_key]
            if history['inclusion'].get(record_key):
                choices = [row for row in rows if (row.get('resume_conversation_v1') or {}).get('resume_exclusion')
                    or (row.get('resume_conversation_v1') or {}).get('resume_restoration')]
                latest = self._latest_resume_decision(snapshot, choices,
                    lambda row: bool(row['resume_conversation_v1'].get('resume_exclusion')))
                if latest and current(latest):
                    meta = copy.deepcopy(latest['resume_conversation_v1'])
                    meta.update(resume_exclusion=False, resume_restoration=True, operation='restore_content',
                        target_values_digest=_json_digest(values))
                    add('record:' + latest['proposal_key'], latest, values, meta, target,
                        label='Review restoration: ' + str(title), text='Restore this same entry to your private Resume.')
            excluded = history['bullets'].get(record_key) or []
            choices = [row for row in rows if 'excluded_bullets' in (row.get('resume_conversation_v1') or {})]
            if not excluded or not choices or any(not current(row) for row in choices): continue
            orders = [(row['resume_conversation_v1'].get('decision_order'), row) for row in choices]
            if any(type(n) is not int or n < 1 for n, _ in orders) or len({n for n, _ in orders}) != len(orders): continue
            choices = [row for _, row in sorted(orders, key=lambda pair: pair[0])]
            latest = choices[-1]
            proof = [self._recovery_row_token(row) for row in choices]
            for field in {bullet['field'] for bullet in excluded}:
                retained = [bullet for bullet in excluded if bullet['field'] == field]
                positions = self._bullet_recovery_positions(choices, field, values.get(field) or '', retained)
                if not positions: continue
                ordinals = [i for i, bullet in enumerate(excluded) if bullet['field'] == field]
                for ordinal, bullet, position in zip(ordinals, retained, positions):
                    lines = (values.get(field) or '').splitlines()
                    lines.insert(position['index'], bullet['text'])
                    restored = {field: '\n'.join(lines)}
                    meta = copy.deepcopy(latest['resume_conversation_v1'])
                    meta.update(resume_exclusion=False, resume_restoration=False, operation='revise_content',
                        recovery_bullet_identity=position['identity'],
                        excluded_bullets=[b for i, b in enumerate(excluded) if i != ordinal],
                        bullet_edits=[{'action': 'include', 'field': field, 'index': position['index'],
                            'expected_text': bullet['text'], 'replacement': None}], target_values_digest=_json_digest(values))
                    add('bullet:' + latest['proposal_key'] + ':' + str(ordinal), latest, restored, meta, target,
                        label='Review excluded detail: ' + str(title), text=bullet['text'], proof=[proof, position['identity']])
        return result

    def _stage_recovery(self, snapshot, descriptor, key, digest):
        original = snapshot['proposals'][descriptor['original_key']]
        restores_pending = descriptor['template_key'] != descriptor['original_key']
        proposal = copy.deepcopy(snapshot['proposals'][descriptor['template_key']])
        proposal.update(proposal_key=str(uuid4()), state='pending', decision=None, decided_at=None,
            confirmed_values=None, created_at=_utc(None).isoformat(), command_digest=digest,
            proposed_values=copy.deepcopy(descriptor['values']))
        for field in ('superseded_by', 'request_digest', 'saved_record_key'):
            proposal.pop(field, None)
        target = descriptor['target']
        if target:
            proposal.update(target_key=target['record_key'], target_content_token=target['content_token'],
                target_access_revision=target['access_revision'])
            if not restores_pending:
                proposal.update(provided_fields=list(descriptor['values']), explicit_clears=[], requires_member_wording=False)
        proposal['resume_conversation_v1'] = copy.deepcopy(descriptor['metadata'])
        proposal['resume_conversation_v1'].pop('decision_order', None)
        proposal['resume_conversation_v1'].update(revision_of=original['proposal_key'],
            recovery_review={'key': key, 'token': descriptor['token'], 'as_shown': bool(target) and not restores_pending})
        dependencies = proposal['resume_conversation_v1'].setdefault('source_bindings', [])
        dependency = {'source_key': original['binding']['source_key'], 'version': original['binding']['source_version']}
        if dependency not in dependencies: dependencies.append(dependency)
        snapshot['proposals'][proposal['proposal_key']] = proposal
        if not target or restores_pending: original['superseded_by'] = proposal['proposal_key']
        return proposal

    @staticmethod
    def _refresh_source_accounting(snapshot):
        for source in snapshot['sources'].values():
            for unit in ((source.get('structured_values') or {}).get('resume_conversation_v1') or {}).get('source_units') or []:
                cohort = ResumeIntakeService._source_unit_proposals(snapshot, source['source_key'], unit)
                if not cohort: continue
                unit['proposal_keys'] = sorted(row['proposal_key'] for row in cohort)
                approved = [row for row in cohort if row['state'] == 'accepted'
                    and not (row.get('resume_conversation_v1') or {}).get('resume_exclusion')]
                unit['disposition'] = 'pending' if any(row['state'] == 'pending' for row in cohort) else (
                    'approved' if len(approved) == len(cohort) else 'partially approved' if approved else 'excluded')
                records = sorted({row.get('saved_record_key') or row.get('target_key') for row in cohort
                    if row.get('saved_record_key') or row.get('target_key')})
                unit['record_keys'] = records
                unit['record_key'] = records[0] if len(records) == 1 else None

    def review_excluded_details(self, owner, payload, *, allow_fixture_policy=False):
        if (not isinstance(payload, dict) or set(payload) != {'request_id', 'recovery_key', 'recovery_token'}
                or not isinstance(payload.get('recovery_key'), str) or len(payload['recovery_key']) > 128
                or not isinstance(payload.get('recovery_token'), str) or len(payload['recovery_token']) != 64
                or payload['recovery_key'].startswith('undo:')):
            raise ResumeIntakeValidationError('Invalid excluded-detail review.')
        command = {**payload, 'request_id': _as_uuid(payload['request_id'], field='request_id')}
        digest = _json_digest({'type': 'review_excluded_details', **command})
        if not getattr(self.repository, 'supports_resume_conversation', False):
            raise ResumeIntakeUnavailableError()
        self._require_usable_policy(allow_fixture=allow_fixture_policy)
        with self.repository.owner_guard(owner), self._unit_of_work() as unit:
            if not getattr(unit, 'supports_atomic_composition', False):
                raise ResumeIntakeUnavailableError()
            snapshot = self._load(owner)
            receipt = snapshot['receipts'].get(command['request_id'])
            if receipt:
                if receipt['request_digest'] != digest:
                    raise ResumeIntakeConflictError('idempotency_conflict', [], 'That request key was used for another review.')
                keys = [row['proposal_key'] for row in receipt['result'].get('proposals') or []]
                if any(key not in snapshot['proposals'] or snapshot['proposals'][key].get('source_purged')
                        or not binding_is_current(snapshot, snapshot['proposals'][key]) for key in keys):
                    return {**receipt['result'], 'proposals': [], 'replayed': True,
                        'message': 'Those original details are no longer available. Your current content is kept.'}
                return {**self._hydrate_replay(owner, snapshot, receipt['result']), 'replayed': True}
            key, token = command['recovery_key'], command['recovery_token']
            existing = next((row for row in snapshot['proposals'].values() if row['state'] == 'pending'
                and (row.get('resume_conversation_v1') or {}).get('recovery_review', {}).get('key') == key
                and row['resume_conversation_v1']['recovery_review']['token'] == token), None)
            descriptor = self._recovery_inventory(owner, snapshot, allow_child=(existing or {}).get('proposal_key')).get(key)
            if not descriptor or descriptor['token'] != token:
                raise ResumeIntakeConflictError('changed', [], 'Those excluded details changed or are no longer retained. Review the current list.')
            proposal = existing or self._stage_recovery(snapshot, descriptor, key, digest)
            self._refresh_source_accounting(snapshot)
            result = {'success': True, 'request_id': command['request_id'], 'proposals': [present_proposal(proposal)],
                'saved': False, 'publishes': False, 'replayed': bool(existing),
                'message': 'Review the original details before confirming. Nothing was saved.'}
            snapshot['receipts'][command['request_id']] = {'request_digest': digest, 'submission_key': None,
                'result': receipt_for_storage(result)}
            try:
                unit.commit(owner, snapshot)
            except ResumeIntakeStoreUnavailable as error:
                raise ResumeIntakeUnavailableError() from error
            return result

    def review_resume_history(self, owner, payload, *, allow_fixture_policy=False):
        """Propose an explicit current choice when legacy chronology is absent."""
        from services.resume_onboarding_document_reader import inventory_source
        if (not isinstance(payload, dict) or set(payload) != {
                'request_id', 'record_key', 'effect', 'history_token', 'proposal_key'}
                or payload.get('effect') not in {'section', 'inclusion', 'credential', 'bullets'}
                or not isinstance(payload.get('history_token'), str) or len(payload['history_token']) != 64):
            raise ResumeIntakeValidationError('Invalid saved-choice review.')
        command = copy.deepcopy(payload)
        for name in ('request_id', 'record_key', 'proposal_key'):
            command[name] = _as_uuid(command[name], field=name)
        digest = _json_digest(command)
        if not getattr(self.repository, 'supports_resume_conversation', False):
            raise ResumeIntakeUnavailableError()
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        with self.repository.owner_guard(owner):
            snapshot = self._load(owner)
            for source in snapshot['sources'].values():
                meta = (source.get('structured_values') or {}).get('resume_conversation_v1') or {}
                if meta.get('request_id') == command['request_id']:
                    if meta.get('request_digest') != digest or source.get('state') != 'active':
                        raise ResumeIntakeConflictError('changed', [], 'That review changed. Choose the saved entry again.')
                    return self._conversation_response(snapshot, source, replayed=True)
            conflict = next((row for row in self._resume_history(snapshot)['conflicts']
                if row['record_key'] == command['record_key'] and row['effect'] == command['effect']), None)
            choice = next((row for row in (conflict or {}).get('choices', [])
                if row['proposal_key'] == command['proposal_key']), None)
            if not choice or conflict['history_token'] != command['history_token']:
                raise ResumeIntakeConflictError('changed', [], 'That review changed. Choose the saved entry again.')
            for pending in snapshot['proposals'].values():
                review = (pending.get('resume_conversation_v1') or {}).get('history_review') or {}
                if pending.get('state') == 'pending' and all(review.get(name) == command[name]
                        for name in ('record_key', 'effect', 'history_token', 'proposal_key')):
                    source = snapshot['sources'].get((pending.get('binding') or {}).get('source_key'))
                    if source and source.get('state') == 'active':
                        return self._conversation_response(snapshot, source, replayed=True)
            target = self._find_item(owner, command['record_key'])
            if target is None:
                raise ResumeIntakeNotFoundError()
            values = {**target['values'], **(target.get('proposed_values') or {})}
            metadata = {'history_review': {**command}, 'target_values_digest': _json_digest(values)}
            effect, value = command['effect'], copy.deepcopy(choice['value'])
            if effect == 'section':
                if target['record_type'] == 'knowledge' and (
                        (value == 'My Story') != (values.get('classification') == 'personal')):
                    raise ResumeIntakeValidationError('Review this entry in the manual editor first; its classification changed.')
                metadata['presentation_section'] = value
            elif effect == 'inclusion':
                metadata.update(resume_exclusion=bool(value), resume_restoration=not bool(value))
            elif effect == 'bullets':
                if any(bullet['text'] in (values.get(bullet['field']) or '').splitlines() for bullet in value):
                    raise ResumeIntakeValidationError('A removed bullet is currently in your approved entry. '
                        'Review the other saved choice, or edit the entry manually.')
                metadata['excluded_bullets'] = value
            else:
                if (target['record_type'] != 'credential' or value.get('owner_user_key') != owner
                        or value.get('credential_key') != target['record_key']):
                    raise ResumeIntakeNotFoundError()
                note = self._find_item(owner, value.get('supplement_key'))
                note_values = {**(note or {}).get('values', {}), **((note or {}).get('proposed_values') or {})}
                if not note or note['record_type'] != 'knowledge' or note_values.get('classification') != 'work':
                    raise ResumeIntakeValidationError('Review this credential with its complete private details first.')
                metadata['approved_credential_binding'] = {**value,
                    'credential_content_token': target['content_token'],
                    'credential_access_revision': target['access_revision'],
                    'supplement_content_token': note['content_token'],
                    'supplement_access_revision': note['access_revision']}
                metadata['credential_binding'] = {**metadata['approved_credential_binding'],
                    'supplement_values_digest': _json_digest(note_values)}
                values['resume_credential_wording'] = note_values['wording']
            moment, submission_key = _utc(None), str(uuid4())
            wording = 'Review the saved Resume ' + effect + ' choice for this entry.'
            plan = _ItemPlan(client_key='history-review', kind='text', record_type=target['record_type'],
                source_text=wording, quote=wording, provided_values=values)
            snapshot['policy_version'] = policy.version
            snapshot['submissions'][submission_key] = {'submission_key': submission_key, 'version': 1,
                'state': 'active', 'created_at': moment.isoformat(), 'source_keys': []}
            source = self._store_source(snapshot, submission_key, 1, plan, moment, owner=owner)
            snapshot['submissions'][submission_key]['source_keys'] = [source['source_key']]
            proposal = self._make_proposal(snapshot, plan, source, submission_key, 1, policy,
                {'request_digest': digest}, kind='change_existing', target=target, confidence='certain')
            proposal['requires_member_wording'] = False
            proposal['resume_conversation_v1'] = metadata
            units = inventory_source(wording)
            for unit in units:
                unit.update(proposal_key=proposal['proposal_key'], disposition='pending')
            source['structured_values'] = {'resume_conversation_v1': {'schema_version': 1,
                'request_id': command['request_id'], 'request_digest': digest, 'turn_state': 'completed',
                'source_units': units, 'proposal_keys': [proposal['proposal_key']],
                'response': 'Review this current choice before confirming. Your approved content stays unchanged.'}}
            self.repository.save_owner(owner, snapshot)
            return self._conversation_response(snapshot, source)

    def converse(self, owner, payload, *, assistance, allow_fixture_policy=False):
        from services.resume_intake_runtime import SynthesisError
        from services.resume_onboarding_document_reader import inventory_source
        if not getattr(self.repository, 'supports_resume_conversation', False):
            raise SynthesisError('unavailable')
        if assistance.providers.get('interview') is None:
            raise SynthesisError('unavailable')
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        if (not isinstance(payload, dict) or set(payload) != {
                'request_id', 'expected_draft_version', 'statement', 'selected_target', 'source_keys'}
                or type(payload['expected_draft_version']) is not int or payload['expected_draft_version'] < 0
                or not isinstance(payload['statement'], str) or not payload['statement'].strip()
                or payload['selected_target'] is not None and not isinstance(payload['selected_target'], str)
                or len(payload['statement'].encode('utf-8')) > assistance.limits['maximum_task_bytes']
                or not isinstance(payload['source_keys'], list) or len(payload['source_keys']) > 12):
            raise SynthesisError('invalid')
        command = copy.deepcopy(payload)
        command['request_id'] = _as_uuid(payload['request_id'], field='request id')
        command['source_keys'] = [_as_uuid(key, field='source key') for key in payload['source_keys']]
        if command['selected_target'] is not None:
            parts = command['selected_target'].split(':')
            if len(parts) != 2 or parts[0] not in {'record', 'proposal'}:
                raise SynthesisError('invalid')
            _as_uuid(parts[1], field='selected target')
        if len(set(command['source_keys'])) != len(command['source_keys']):
            raise SynthesisError('invalid')
        request_digest = _json_digest(command)
        # Reserve before dispatch, release the owner lock during the paid call,
        # then reload and compare every source/proposal/canonical binding.
        with self.repository.owner_guard(owner):
            snapshot = self._load(owner)
            for old_source in snapshot['sources'].values():
                old_meta = (old_source.get('structured_values') or {}).get('resume_conversation_v1') or {}
                if old_meta.get('request_id') != command['request_id']:
                    continue
                if old_meta.get('request_digest') != request_digest:
                    raise SynthesisError('changed')
                if old_source.get('state') != 'active':
                    raise SynthesisError('changed')
                if old_meta.get('turn_state') == 'completed':
                    return self._conversation_response(snapshot, old_source, replayed=True)
                # An uncertain/reserved/failed dispatch never silently repeats.
                raise SynthesisError('unavailable')
            canonical = assistance._context(owner, [], allow_empty=True)
            if canonical['draft_version'] != command['expected_draft_version']:
                raise SynthesisError('changed')
            snapshot['policy_version'] = policy.version
            context = self._conversation_view(snapshot, canonical)
            refs = {row['target_ref'] for row in context['targets']}
            if command['selected_target'] is not None and command['selected_target'] not in refs:
                raise SynthesisError('not_found')
            for key in command['source_keys']:
                source = snapshot['sources'].get(key)
                if not source or source.get('state') != 'active' or source.get('kind') != 'recording':
                    raise SynthesisError('not_found')
            submission_key, source_key = str(uuid4()), str(uuid4())
            snapshot['submissions'][submission_key] = {'submission_key': submission_key, 'version': 1,
                'state': 'active', 'source_keys': [source_key], 'created_at': _utc(None).isoformat()}
            source = self._store_source(snapshot, submission_key, 1,
                _ItemPlan(client_key='conversation', kind='text', record_type='unspecified',
                          source_text=command['statement']), _utc(None), owner=owner)
            source_key = source['source_key']
            snapshot['submissions'][submission_key]['source_keys'] = [source_key]
            source['structured_values'] = {'resume_conversation_v1': {
                'schema_version': 1, 'request_id': command['request_id'], 'request_digest': request_digest,
                'base_revision': canonical['draft_version'], 'turn_state': 'reserved',
                'turn_order': 1 + max([0] + [((row.get('structured_values') or {}).get('resume_conversation_v1') or {}).get('turn_order', 0)
                    for row in snapshot['sources'].values()]),
                'source_units': inventory_source(command['statement']),
                'dependencies': [{'source_key': row['source_key'], 'version': row['version']} for row in context['materials']]}}
            context['current_turn'] = {'source_key': source_key, 'units': copy.deepcopy(source['structured_values']['resume_conversation_v1']['source_units'])}
            context['selected_target'] = command['selected_target']
            if len(json.dumps(context, ensure_ascii=False).encode('utf-8')) > assistance.limits['maximum_input_bytes']:
                raise SynthesisError('input_too_large')
            original_view_digest = _json_digest(self._conversation_view(snapshot, canonical, exclude_source=source_key))
            self.repository.save_owner(owner, snapshot)
        try:
            result = assistance.conversation(owner, command, context=context)
            with self.repository.owner_guard(owner):
                fresh = self._load(owner)
                current = fresh['sources'].get(source_key)
                new_canonical = assistance._context(owner, [], allow_empty=True)
                if (not current or current.get('state') != 'active'
                        or _json_digest(self._conversation_view(fresh, new_canonical, exclude_source=source_key)) != original_view_digest):
                    from services.resume_intake_runtime import conversation_rejection
                    raise conversation_rejection('changed', 'context_revalidation', 'authorized_context_changed')
                proposals = self._conversation_proposals(owner, fresh, current, command, context, result, policy)
                topic_skipped = any(operation['operation'] == 'skip_topic' for operation in result['operations'])
                meta = current['structured_values']['resume_conversation_v1']
                meta.update({'turn_state': 'completed', 'response': result['response'],
                    'next_question': '' if topic_skipped else result['next_question'],
                    'topic_skipped': topic_skipped, 'proposal_keys': [p['proposal_key'] for p in proposals],
                    'control_bindings': {'record_keys': sorted({target['target_ref'].split(':', 1)[1]
                        for target in context['targets'] if target['target_ref'].startswith('record:')}),
                        'sources': [{'source_key': row['source_key'], 'version': row['version']} for row in context['materials']]}})
                self.repository.save_owner(owner, fresh)
                return self._conversation_response(fresh, current)
        except Exception as error:
            from services.resume_intake_runtime import conversation_failure_diagnostic
            diagnostic = conversation_failure_diagnostic(error) or {
                'schema_version': 1, 'stage': 'turn_execution', 'reason': 'unclassified'}
            if isinstance(error, SynthesisError):
                error.conversation_diagnostic = diagnostic
            with self.repository.owner_guard(owner):
                fresh = self._load(owner)
                current = fresh['sources'].get(source_key)
                if current and current.get('state') == 'active':
                    meta = (current.get('structured_values') or {}).get('resume_conversation_v1') or {}
                    if meta.get('turn_state') == 'reserved':
                        meta['turn_state'] = 'failed'
                        meta['failure_diagnostic'] = diagnostic
                        self.repository.save_owner(owner, fresh)
            raise

    def _conversation_proposals(self, owner, snapshot, source, command, context, result, policy):
        from services.resume_intake_runtime import (
            SynthesisError, CONVERSATION_OPERATION_FIELDS, CONVERSATION_OPERATIONS,
            conversation_rejection,
        )
        from services.my_data_extraction_adapter import RESUME_SECTIONS
        target_map = {row['target_ref']: row for row in context['targets']}
        unit_map = {(row['source_key'], u['unit_id']): u for row in context['materials'] for u in row['units']}
        unit_map.update({(source['source_key'], u['unit_id']): u for u in context['current_turn']['units']})
        proposals, changed_targets = [], set()
        for operation in result['operations']:
            if not isinstance(operation, dict) or set(operation) != CONVERSATION_OPERATION_FIELDS:
                raise conversation_rejection('invalid_output', 'operation_contract', 'operation_shape')
            if operation['operation'] not in CONVERSATION_OPERATIONS:
                raise conversation_rejection('invalid_output', 'operation_contract', 'operation_name')
            op, ref, record_type = operation['operation'], operation['target_ref'], operation['record_type']
            if not all(isinstance(operation[name], list) for name in ('values', 'explicit_clears', 'bullet_edits', 'source_refs')):
                raise conversation_rejection('invalid_output', 'operation_contract', 'list_field_type')
            if op in {'clarify', 'answer_question', 'skip_topic'}:
                if ref is not None or any(operation[name] for name in ('values', 'explicit_clears', 'bullet_edits', 'source_refs')):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'control_operation_payload')
                continue
            target = target_map.get(ref) if ref is not None else None
            if (op != 'add_content' and target is None) or (op == 'add_content' and ref is not None):
                raise conversation_rejection('invalid_output', 'operation_contract', 'target_binding')
            if ref and (ref in changed_targets or target['record_type'] != record_type):
                raise conversation_rejection('invalid_output', 'operation_contract', 'record_type_or_duplicate_target')
            fields = CONVERSATION_FIELDS.get(record_type)
            if fields is None:
                raise conversation_rejection('invalid_output', 'operation_contract', 'unsupported_record_type')
            patch = {}
            for pair in operation['values']:
                if not isinstance(pair, dict) or set(pair) != {'field', 'value'}:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_pair_shape')
                if pair['field'] not in fields:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_field')
                if pair['field'] in patch:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_duplicate')
                if pair['value'] is None:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_null')
                if not isinstance(pair['value'], (str, int, float, bool)):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_type')
                if isinstance(pair['value'], str) and len(pair['value'].encode('utf-8')) > 8000:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'value_size')
                patch[pair['field']] = pair['value']
            clears = operation['explicit_clears']
            if (any(not isinstance(name, str) or name not in fields for name in clears)
                    or len(set(clears)) != len(clears) or set(clears) & set(patch)):
                raise conversation_rejection('invalid_output', 'operation_contract', 'clear_fields')
            source_refs = operation['source_refs']
            if not source_refs or len(source_refs) > 100:
                raise conversation_rejection('invalid_output', 'operation_contract', 'source_refs_required')
            for binding in source_refs:
                if (not isinstance(binding, dict) or set(binding) != {'source_key', 'unit_id'}
                        or (binding['source_key'], binding['unit_id']) not in unit_map):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'source_ref_binding')
            old = None
            values = copy.deepcopy(target['values']) if target else {}
            if ref and ref.startswith('proposal:'):
                old = snapshot['proposals'][ref.split(':', 1)[1]]
                clears = sorted((set(old.get('explicit_clears') or []) - set(patch)) | set(clears))
            excluded = copy.deepcopy((old or {}).get('resume_conversation_v1', {}).get('excluded_bullets')
                or (target or {}).get('excluded_bullets') or [])
            # Literal source-bound edits, rather than a model rewrite of every
            # bullet, preserve untouched wording, negations and qualifiers.
            edited_fields = set()
            for edit in operation['bullet_edits']:
                if (not isinstance(edit, dict) or set(edit) != {'action', 'field', 'index', 'expected_text', 'replacement'}
                        or edit['action'] not in {'include', 'exclude', 'revise'} or edit['field'] not in CONVERSATION_BULLET_FIELDS
                        or edit['field'] not in fields or edit['field'] in patch or edit['field'] in clears
                        or type(edit['index']) is not int or edit['index'] < 0):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'bullet_edit_shape')
                name, index = edit['field'], edit['index']
                lines = (values.get(name) or '').splitlines()
                if edit['action'] == 'include':
                    match = next((b for b in excluded if b['field'] == name and b['text'] == edit['expected_text']), None)
                    if match is None or edit['replacement'] is not None or index > len(lines):
                        raise conversation_rejection('invalid_output', 'operation_contract', 'bullet_include')
                    lines.insert(index, match['text']); excluded.remove(match)
                else:
                    if index >= len(lines) or lines[index] != edit['expected_text']:
                        raise conversation_rejection('invalid_output', 'operation_contract', 'bullet_expected_text')
                    if edit['action'] == 'exclude':
                        if edit['replacement'] is not None:
                            raise conversation_rejection('invalid_output', 'operation_contract', 'bullet_exclude_replacement')
                        excluded.append({'field': name, 'index': index, 'text': lines.pop(index)})
                    else:
                        if not isinstance(edit['replacement'], str) or not edit['replacement'].strip() or len(edit['replacement'].encode('utf-8')) > 8000:
                            raise conversation_rejection('invalid_output', 'operation_contract', 'bullet_revision_replacement')
                        lines[index] = edit['replacement']
                values[name] = '\n'.join(lines); edited_fields.add(name)
            values.update(patch)
            for name in clears:
                values[name] = _empty_value(name)
            if op == 'add_content':
                # New biography stays literal and complete; extracted identity
                # fields organize it but never substitute a shorter summary.
                literal = '\n'.join(unit_map[(b['source_key'], b['unit_id'])]['text'] for b in source_refs)
                if any(unit_map[(b['source_key'], b['unit_id'])]['kind'] != 'content' for b in source_refs):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'source_unit_kind')
                import re
                if (any(b['source_key'] == source['source_key'] for b in source_refs)
                        and re.match(r'^\s*(?:stop|skip|remove|exclude|delete|undo|restore|include|change|revise|update|correct|replace|ask|what|which|how|why|when|where|can you|could you|help me)\b', command['statement'], re.I)):
                    raise conversation_rejection('invalid_output', 'operation_contract', 'command_as_new_content')
                if command['statement'].strip().lower().rstrip('.!') in {
                        'remove that', 'stop', 'stop here', 'skip', 'skip this', 'undo that', 'never mind'}:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'control_as_new_content')
                identities = {'role': ('role_title', 'employer_name'), 'education': ('degree_name', 'institution_name'),
                              'credential': ('name', 'issuer'), 'skill': ('name',)}.get(record_type, ())
                normalized_literal = ' '.join(literal.lower().split())
                for name in identities:
                    if values.get(name) and ' '.join(str(values[name]).lower().split()) not in normalized_literal:
                        raise conversation_rejection('invalid_output', 'operation_contract', 'identity_not_literal')
                body_field = {'role': 'summary', 'education': 'summary', 'skill': 'summary',
                              'knowledge': 'wording', 'accomplishment': 'wording',
                              'credential': 'resume_credential_wording'}.get(record_type)
                if body_field:
                    values[body_field] = literal
                if len(literal.encode('utf-8')) > 8000:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'literal_size')
            section = operation['presentation_section'] or (target or {}).get('presentation_section')
            if section not in RESUME_SECTIONS:
                raise conversation_rejection('invalid_output', 'operation_contract', 'presentation_section')
            if record_type == 'knowledge':
                expected_class = 'personal' if section == 'My Story' else 'work'
                if values.get('classification', expected_class) != expected_class:
                    raise conversation_rejection('invalid_output', 'operation_contract', 'knowledge_classification')
                values['classification'] = expected_class
            if op != 'add_content' and values == target['values'] and op not in {'exclude_content', 'restore_content'}:
                continue
            canonical_target = None
            if ref and ref.startswith('record:'):
                canonical_target = self._find_item(owner, ref.split(':', 1)[1])
            elif old and old.get('target_key'):
                canonical_target = self._find_item(owner, old['target_key'])
                baseline = (old.get('resume_conversation_v1') or {}).get('target_values_digest')
                if (canonical_target is None or canonical_target['content_token'] != old.get('target_content_token')
                        or canonical_target['access_revision'] != old.get('target_access_revision')
                        or baseline and baseline != _json_digest({**canonical_target['values'],
                            **(canonical_target.get('proposed_values') or {})})):
                    raise conversation_rejection('changed', 'context_revalidation', 'canonical_target_changed')
                previous_note = (old.get('resume_conversation_v1') or {}).get('credential_binding')
                if previous_note:
                    note = self._find_item(owner, previous_note['supplement_key'])
                    if (note is None or previous_note.get('owner_user_key') != owner
                            or note['content_token'] != previous_note['supplement_content_token']
                            or note['access_revision'] != previous_note['supplement_access_revision']
                            or _json_digest({**note['values'], **(note.get('proposed_values') or {})}) != previous_note['supplement_values_digest']):
                        raise conversation_rejection('changed', 'context_revalidation', 'credential_supplement_changed')
            new_values = values if old or op == 'add_content' else {name: values[name] for name in set(patch) | edited_fields}
            new_values = {name: value for name, value in new_values.items() if name not in clears}
            plan = _ItemPlan(client_key='conversation', kind='text', record_type=record_type,
                source_text=command['statement'], quote=command['statement'], provided_values=new_values,
                explicit_clears=tuple(clears))
            proposal = self._make_proposal(snapshot, plan, source, source['submission_key'], 1, policy,
                {'request_digest': _json_digest(command)}, kind='new_fact' if not canonical_target else 'change_existing',
                target=canonical_target, confidence='certain', proposed_values=new_values)
            dependencies = [{'source_key': b['source_key'], 'version': snapshot['sources'][b['source_key']]['version']}
                            for b in source_refs]
            if old:
                dependencies.extend(copy.deepcopy((old.get('resume_conversation_v1') or {}).get('source_bindings') or []))
                dependencies.append({'source_key': old['binding']['source_key'], 'version': old['binding']['source_version']})
                if old['state'] == 'pending':
                    old['state'] = 'invalidated'
                old['superseded_by'] = proposal['proposal_key']
                for original in snapshot['sources'].values():
                    for source_unit in ((original.get('structured_values') or {}).get('resume_conversation_v1') or {}).get('source_units') or []:
                        if source_unit.get('proposal_key') == old['proposal_key']:
                            source_unit['proposal_key'] = proposal['proposal_key']
                        if old['proposal_key'] in (source_unit.get('proposal_keys') or []):
                            source_unit['proposal_keys'] = sorted((set(source_unit['proposal_keys']) - {old['proposal_key']}) | {proposal['proposal_key']})
            proposal['requires_member_wording'] = False
            proposal['resume_conversation_v1'] = {'unit_ids': [b['unit_id'] for b in source_refs],
                'source_refs': copy.deepcopy(source_refs), 'source_bindings': dependencies,
                'presentation_section': section, 'operation': op, 'revision_of': (old or {}).get('proposal_key'),
                'excluded_bullets': excluded, 'bullet_edits': copy.deepcopy(operation['bullet_edits']),
                'target_values_digest': _json_digest({k: v for k, v in (target or {}).get('values', {}).items()
                    if k != 'resume_credential_wording'}) if canonical_target and not old else
                    ((old or {}).get('resume_conversation_v1', {}).get('target_values_digest') or
                        (_json_digest({**canonical_target['values'], **(canonical_target.get('proposed_values') or {})}) if canonical_target else None)),
                'resume_exclusion': op == 'exclude_content' and not operation['bullet_edits'],
                'resume_restoration': bool(canonical_target) and op == 'restore_content' and not operation['bullet_edits']}
            if record_type == 'credential' and canonical_target:
                linked = next((b for b in self._credential_bindings(snapshot)
                    if b['credential_key'] == canonical_target['record_key']), None)
                if linked:
                    note = self._find_item(owner, linked['supplement_key'])
                    if note is None:
                        raise SynthesisError('changed')
                    proposal['resume_conversation_v1']['credential_binding'] = {
                        **linked, 'supplement_content_token': note['content_token'],
                        'supplement_access_revision': note['access_revision'],
                        'supplement_values_digest': _json_digest({**note['values'], **(note.get('proposed_values') or {})})}
            for binding in source_refs:
                for source_unit in ((snapshot['sources'][binding['source_key']].get('structured_values') or {}).get('resume_conversation_v1') or {}).get('source_units') or []:
                    if source_unit['unit_id'] == binding['unit_id'] and source_unit.get('kind') == 'content':
                        source_unit['proposal_key'] = proposal['proposal_key']
                        source_unit['proposal_keys'] = sorted(set(source_unit.get('proposal_keys') or []) | {proposal['proposal_key']})
                        source_unit['disposition'] = 'pending'
            proposals.append(proposal)
            if ref:
                changed_targets.add(ref)
        return proposals

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
                    duplicate = self._duplicate_document(snapshot, plan)
                    if duplicate is not None:
                        # The same file is already here with work still open: continue with it
                        # instead of storing it again and doubling the review.
                        results.append({
                            "client_key": plan.client_key, "kind": "document", "outcome": "duplicate",
                            "code": "duplicate_document", "existing_source_key": duplicate["source_key"],
                            "saved": False,
                            "message": "You've already uploaded this file. Let's continue with it."})
                        continue
                    source = self._store_source(snapshot, submission_key, submission_version, plan, moment, owner=owner)
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
        with self.repository.owner_guard(owner):
            return self._decide_guarded(owner, payload, allow_fixture_policy=allow_fixture_policy)

    def _decide_guarded(self, owner, payload, *, allow_fixture_policy=False):
        if not isinstance(payload, dict):
            raise ResumeIntakeValidationError("Invalid request.")
        if set(payload) & FORBIDDEN_CLIENT_FIELDS:
            raise ResumeIntakeValidationError("Owner fields cannot be client-supplied.")
        request_id = _as_uuid(payload.get("request_id"), field="request id")
        proposal_key = _as_uuid(payload.get("proposal_key"), field="proposal key")
        decision = payload.get("decision")
        if decision not in {"accept", "reject", "edit"}:
            raise ResumeIntakeValidationError("Invalid decision.")
        undo_token = payload.get('undo_exclusion_token')
        if undo_token is not None and (decision != 'reject' or not isinstance(undo_token, str) or len(undo_token) != 64):
            raise ResumeIntakeValidationError('Invalid exclusion Undo.')
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
             "decision": decision, "confirmed_values": confirmed,
             **({'undo_exclusion_token': undo_token} if undo_token is not None else {})}
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
        recovery = (proposal.get('resume_conversation_v1') or {}).get('recovery_review')
        if decision in {'accept', 'edit'} and recovery:
            if recovery.get('as_shown') and (decision != 'accept' or confirmed is not None and confirmed != proposal['proposed_values']):
                raise ResumeIntakeValidationError('Confirm this restoration as shown, or dismiss it and review again.')
            descriptor = self._recovery_inventory(owner, snapshot, allow_child=proposal_key).get(recovery['key'])
            if not descriptor or descriptor['token'] != recovery['token']:
                raise ResumeIntakeConflictError('changed', [], 'Those retained details changed. Review the current list again.')
        if undo_token is not None:
            descriptor = self._recovery_inventory(owner, snapshot).get('undo:' + proposal_key)
            if not descriptor or descriptor['token'] != undo_token:
                raise ResumeIntakeConflictError('changed', [], 'That exclusion changed. Your current content is kept.')
        if decision in {'accept', 'edit'} and (proposal.get('resume_conversation_v1') or {}).get('history_review'):
            if decision != 'accept' or confirmed is not None and confirmed != proposal['proposed_values']:
                raise ResumeIntakeValidationError('Confirm this saved choice as shown, or dismiss it and review again.')
        if decision in {'accept', 'edit'} and proposal.get('target_key') and proposal.get('resume_conversation_v1'):
            current_target = self._find_item(owner, proposal['target_key'])
            if (current_target is None or current_target.get('content_token') != proposal.get('target_content_token')
                    or current_target.get('access_revision') != proposal.get('target_access_revision')):
                raise ResumeIntakeConflictError('changed', [], 'That record changed. Your wording is still here. Review it again.',
                    proposed=proposal.get('proposed_values'))
        target_digest = (proposal.get('resume_conversation_v1') or {}).get('target_values_digest')
        linked = (proposal.get('resume_conversation_v1') or {}).get('credential_binding')
        if decision in {'accept', 'edit'} and linked:
            note = self._find_item(owner, linked.get('supplement_key'))
            if (note is None or linked.get('owner_user_key') != owner
                    or note.get('content_token') != linked.get('supplement_content_token')
                    or note.get('access_revision') != linked.get('supplement_access_revision')
                    or _json_digest({**note['values'], **(note.get('proposed_values') or {})}) != linked.get('supplement_values_digest')):
                raise ResumeIntakeConflictError('changed', [], 'The credential details changed. Review both records again.')
        if decision in {'accept', 'edit'} and target_digest and proposal.get('target_key'):
            target = self._find_item(owner, proposal['target_key'])
            effective = {**((target or {}).get('values') or {}), **((target or {}).get('proposed_values') or {})}
            if target is None or _json_digest(effective) != target_digest:
                raise ResumeIntakeConflictError('changed', [], 'That record changed. Review it again.')
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
        restored_proposal = None
        try:
            with self._unit_of_work() as unit:
                if recovery and decision in {'accept', 'edit'} or undo_token is not None:
                    if not getattr(unit, 'supports_atomic_composition', False):
                        raise ResumeIntakeUnavailableError()
                    fresh = self._load(owner)
                    key = recovery['key'] if recovery and decision in {'accept', 'edit'} else 'undo:' + proposal_key
                    token = recovery['token'] if recovery and decision in {'accept', 'edit'} else undo_token
                    descriptor = self._recovery_inventory(owner, fresh, allow_child=proposal_key if recovery else None).get(key)
                    if not descriptor or descriptor['token'] != token:
                        raise ResumeIntakeConflictError('changed', [], 'Those retained details changed. Your current content is kept.')
                if undo_token is not None and descriptor['template_key'] != descriptor['original_key']:
                    key = 'proposal:' + proposal_key
                    descriptor = self._recovery_inventory(owner, snapshot).get(key)
                    if not descriptor:
                        raise ResumeIntakeConflictError('changed', [], 'The original suggestion is no longer available. Nothing changed.')
                    restored_proposal = self._stage_recovery(snapshot, descriptor, key, digest)
                if decided["state"] == "accepted":
                    metadata = decided.get('resume_conversation_v1') or {}
                    if metadata:
                        metadata['decision_order'] = 1 + max([0] + [
                            value for row in snapshot['proposals'].values()
                            if row.get('state') == 'accepted'
                            for value in [(row.get('resume_conversation_v1') or {}).get('decision_order')]
                            if type(value) is int and value > 0])
                    if decided.get('target_key') and metadata:
                        # Recheck under the participating draft-store lock,
                        # including projection-only exclusion/restoration.
                        target = self._find_item(owner, decided['target_key'])
                        if (target is None or target['content_token'] != decided.get('target_content_token')
                                or target['access_revision'] != decided.get('target_access_revision')
                                or metadata.get('target_values_digest') and _json_digest({**target['values'],
                                    **(target.get('proposed_values') or {})}) != metadata['target_values_digest']):
                            raise ResumeIntakeConflictError('changed', [], 'That record changed. Your wording is still here.')
                        note_binding = metadata.get('credential_binding')
                        if note_binding:
                            note = self._find_item(owner,note_binding['supplement_key'])
                            if (note is None or note_binding['owner_user_key'] != owner
                                    or note['content_token'] != note_binding['supplement_content_token']
                                    or note['access_revision'] != note_binding['supplement_access_revision']
                                    or _json_digest({**note['values'],**(note.get('proposed_values') or {})}) != note_binding['supplement_values_digest']):
                                raise ResumeIntakeConflictError('changed', [], 'The credential details changed. Review both records again.')
                    review = metadata.get('history_review')
                    if review:
                        if review['effect'] == 'credential':
                            from services.resume_intake_repository import InMemoryIntakeUnitOfWork
                            if not isinstance(unit, InMemoryIntakeUnitOfWork) or not unit.supports_atomic_composition:
                                raise ResumeIntakeValidationError('This storage cannot confirm the complete credential binding atomically.')
                        prior = copy.deepcopy(snapshot)
                        prior['proposals'][proposal_key]['state'] = 'pending'
                        conflict = next((row for row in self._resume_history(prior)['conflicts']
                            if row['record_key'] == review['record_key'] and row['effect'] == review['effect']), None)
                        if not conflict or conflict['history_token'] != review['history_token']:
                            raise ResumeIntakeConflictError('changed', [], 'That saved choice changed. Review it again.')
                        item = self._find_item(owner, decided['target_key'])
                        outcome = 'reviewed'
                    elif metadata.get('resume_exclusion') or metadata.get('resume_restoration'):
                        # Inclusion is a private Resume projection choice, not
                        # permission to delete canonical member evidence.
                        item = self._find_item(owner, decided['target_key']) if decided.get('target_key') else None
                        outcome = 'excluded' if metadata.get('resume_exclusion') else 'restored'
                    else:
                        item = self._apply_decision(owner, snapshot, unit, decided, confirmed)
                        outcome = "saved"
                    decided["saved_record_key"] = (item or {}).get("record_key") or decided.get("target_key")
                self._refresh_source_accounting(snapshot)
                result = {
                    "success": True,
                    "outcome": outcome,
                    "request_id": request_id,
                    "request_digest": digest,
                    "replayed": False,
                    "proposal_key": proposal_key,
                    "proposal": present_proposal(snapshot["proposals"][proposal_key]),
                    **({'restored_proposal': present_proposal(restored_proposal)} if restored_proposal else {}),
                    "item": item,
                    "publishes": False,
                    "message": {
                        "saved": "Saved privately. Display and visitor AI stay off.",
                        "unresolved": "Proposal dismissed. Nothing was saved.",
                        'excluded': 'Excluded from your private Resume. Original evidence is kept.',
                        'restored': 'Restored to your private Resume. Nothing was published.',
                        'reviewed': 'Saved your current Resume choice. Approved content stays unchanged; nothing was published.',
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
                candidate.pop("canonical_values", None)
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
                "That parsed input was removed. Accepted history keeps its "
                "provenance, never the deleted text. Retained original files "
                "remain private until you delete them separately."
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
        result = winner if winner is not None else result
        # Purging parsed input invalidates proposals, never original ownership.
        # Only the member's separate original-file deletion creates cleanup intent.
        result["original_files_retained"] = self.original_files is not None
        return result

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
            if row is not None:
                # Reads refresh availability without refreshing inactivity.
                # The draft CAS fences purge and never restores source words.
                row["attachments"] = self._draft_attachments(snapshot, row.get("attachments") or [])
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
                # SQL retains a revision after discard/expiry. Reusing version
                # one would let an old device overwrite a recreated draft.
                version = int(snapshot.get("draft_revision") or 0) + 1
            elif expected != int(existing.get("version") or 0):
                held["outcome"] = "conflict"
                held["reason"] = "version_changed"
                held["existing"] = copy.deepcopy(existing)
                return
            else:
                version = int(existing.get("version") or 0) + 1
            state = normalized.get('guide_state') or {}
            keys = set(state.get('proposal_drafts') or {}) | set(state.get('correction_inputs') or {})
            keys.update(filter(None,(state.get('selected_proposal_key'),state.get('correction_target_key'))))
            keys.update(frame['selected_proposal_key'] for frame in state.get('navigation_history') or [] if frame['selected_proposal_key'])
            pending = state.get('pending_conversation') or {}
            if pending.get('selected_target','') and pending['selected_target'].startswith('proposal:'):
                keys.add(pending['selected_target'].split(':',1)[1])
            if (any((snapshot['proposals'].get(key) or {}).get('source_purged') for key in keys)
                    or any(snapshot['sources'].get(key,{}).get('state') == 'purged' for key in pending.get('source_keys',[]))
                    or any(source.get('state') == 'purged' and pending.get('request_id')
                        and ((source.get('structured_values') or {}).get('resume_conversation_v1') or {}).get('request_id') == pending['request_id']
                        for source in snapshot['sources'].values())):
                raise ResumeIntakeValidationError('That source was removed. Review your current input before saving another draft.')
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
            if 'guide_state' in normalized:
                record['guide_state'] = normalized['guide_state']
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
        # As in Add, the staged job and submission share the selected policy.
        # An older owner snapshot must not make the new local job stale before
        # its SQL transaction can validate the source and lifecycle fences.
        snapshot["policy_version"] = policy.version
        source_binding = {
            "source_key": keep["source_key"], "source_version": keep["source_version"],
            "override_key": override_key, "record_type": record_type,
        }
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
                keep.pop("canonical_values", None)
                commit_result = unit.commit(
                    owner,
                    snapshot,
                    procedure=COMMAND_PROCEDURES["keep_extracted_separate"],
                    request_id=request_id,
                    payload={"type": "keep_extracted_separate", "source_binding": source_binding,
                             "submission": _submission_payload(command, snapshot, stored_receipt)},
                )
        except ResumeIntakeStoreUnavailable as error:
            raise ResumeIntakeUnavailableError() from error
        receipt_request_id = request_id
        if commit_result and commit_result.get("replayed"):
            returned = commit_result.get("result")
            if (not isinstance(returned, dict)
                    or (returned.get("submission") or {}).get("submission_key") != override_key):
                raise ResumeIntakeUnavailableError()
            receipt_request_id = commit_result.get("receipt_request_id") or request_id
        winner = self._winner_after_commit(owner, receipt_request_id, digest, commit_result)
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
                    candidate.pop("canonical_values", None)
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
        if "canonical_values" in keep:
            try:
                normalized = normalize_editor_values(record_type, values)
            except LivingResumeEditorValidationError as error:
                raise ResumeIntakeValidationError(str(error)) from error
            if keep["canonical_values"] != normalized:
                raise ResumeIntakeUnavailableError()
            values = normalized
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
                **({'parent_key': _as_uuid(raw['parent_key'], field='parent key')} if raw.get('parent_key') else {}),
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
        result = {"text": text, "items": items, "attachments": attachments}
        if 'guide_state' in payload:
            if not getattr(self.repository, 'supports_resume_conversation', False):
                raise ResumeIntakeUnavailableError('Guide recovery is unavailable here. Your input is kept on this page.')
            state = payload['guide_state']
            fields = {'screen', 'selected_proposal_key', 'correction_target_key', 'correction_draft',
                'correction_inputs', 'proposal_drafts', 'question', 'context', 'guide_hidden',
                'conversation_intent', 'manual_type', 'manual_fields', 'pending_conversation'}
            if (not isinstance(state, dict) or set(state) - fields - {'seen_questions', 'navigation_history'} or not fields <= set(state)
                    or len(json.dumps(state).encode('utf-8')) > 90000):
                raise ResumeIntakeValidationError('Invalid guide state.')
            frames = state.get('navigation_history', [])
            if not isinstance(frames, list) or len(frames) > 12 or len(json.dumps(frames).encode('utf-8')) > 40000:
                raise ResumeIntakeValidationError('Invalid guide history.')
            for frame in frames:
                if (not isinstance(frame, dict) or set(frame) != {'screen','text','question','context','conversation_intent','selected_proposal_key'}
                        or frame['screen'] not in {'welcome','input','review','correction','next','optional','sharing','finish'}
                        or frame['conversation_intent'] not in {None,'story','project'}
                        or any(not isinstance(frame[name],str) or len(frame[name].encode('utf-8')) > 20000 for name in ('text','question','context'))):
                    raise ResumeIntakeValidationError('Invalid guide history.')
                if frame['selected_proposal_key'] is not None:
                    _as_uuid(frame['selected_proposal_key'],field='proposal key')
            seen = state.get('seen_questions', [])
            if (not isinstance(seen, list) or len(seen) > 50
                    or any(not isinstance(q, str) or len(q.encode('utf-8')) > 2000 for q in seen)):
                raise ResumeIntakeValidationError('Invalid guide questions.')
            if state['screen'] not in {'welcome', 'input', 'review', 'correction', 'next', 'optional', 'sharing', 'finish'}:
                raise ResumeIntakeValidationError('Invalid guide screen.')
            if type(state['guide_hidden']) is not bool or state['conversation_intent'] not in {None, 'story', 'project'}:
                raise ResumeIntakeValidationError('Invalid guide state.')
            for name in ('selected_proposal_key', 'correction_target_key'):
                if state[name] is not None:
                    _as_uuid(state[name], field='proposal key')
            for name in ('correction_draft', 'question', 'context'):
                if state[name] is not None and (not isinstance(state[name], str) or len(state[name].encode('utf-8')) > 20000):
                    raise ResumeIntakeValidationError('Invalid guide wording.')
            for name in ('correction_inputs', 'proposal_drafts', 'manual_fields'):
                if not isinstance(state[name], dict) or len(state[name]) > 50:
                    raise ResumeIntakeValidationError('Invalid guide fields.')
            for key, value in state['correction_inputs'].items():
                _as_uuid(key, field='proposal key')
                if not isinstance(value, str) or len(value.encode('utf-8')) > 20000:
                    raise ResumeIntakeValidationError('Invalid correction input.')
            for key, draft in state['proposal_drafts'].items():
                _as_uuid(key, field='proposal key')
                if not isinstance(draft, dict) or set(draft) - (set(EDITOR_FIELDS) | {'knowledge', 'type', 'destination', 'parent_key'}):
                    raise ResumeIntakeValidationError('Invalid correction fields.')
                for record_type, values in draft.items():
                    if record_type in {'type', 'destination', 'parent_key'}:
                        if values is not None and (not isinstance(values, str) or len(values) > 100):
                            raise ResumeIntakeValidationError('Invalid correction target.')
                        continue
                    allowed = {'title', 'wording', 'classification'} if record_type == 'knowledge' else EDITOR_FIELDS[record_type]
                    if record_type == 'credential':
                        allowed = allowed | {'resume_credential_wording'}
                    if (not isinstance(values, dict) or set(values) - allowed
                            or any(not isinstance(v, str) or len(v.encode('utf-8')) > 20000 for v in values.values())):
                        raise ResumeIntakeValidationError('Invalid correction fields.')
            for key, value in state['manual_fields'].items():
                if not key.startswith('resume-intake-') or not isinstance(value, (str, bool)) or len(str(value).encode('utf-8')) > 20000:
                    raise ResumeIntakeValidationError('Invalid manual fields.')
            if state['manual_type'] not in {None, ''} | STRUCTURED_RECORD_TYPES:
                raise ResumeIntakeValidationError('Invalid guide fields.')
            pending = state['pending_conversation']
            if pending is not None and (not isinstance(pending, dict) or set(pending) != {
                    'request_id', 'expected_draft_version', 'statement', 'selected_target', 'source_keys'}):
                raise ResumeIntakeValidationError('Invalid pending turn.')
            if pending is not None:
                _as_uuid(pending['request_id'], field='request id')
                if (type(pending['expected_draft_version']) is not int or pending['expected_draft_version'] < 0
                        or not isinstance(pending['statement'], str) or not pending['statement'].strip()
                        or len(pending['statement'].encode('utf-8')) > 20000
                        or not isinstance(pending['source_keys'], list) or len(pending['source_keys']) > 12
                        or pending['selected_target'] is not None and not isinstance(pending['selected_target'], str)):
                    raise ResumeIntakeValidationError('Invalid pending turn.')
                for key in pending['source_keys']:
                    _as_uuid(key, field='source key')
            result['guide_state'] = copy.deepcopy(state)
        return result

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
        restored = (result.get('restored_proposal') or {}).get('proposal_key')
        if restored:
            if restored in rows and not rows[restored].get('source_purged') and binding_is_current(snapshot, rows[restored]):
                result['restored_proposal'] = present_proposal(rows[restored])
            else:
                result.pop('restored_proposal', None)

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
                    "byte_length": len(data),
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

    def _store_source(self, snapshot, submission_key, submission_version, plan, moment, *, owner=None):
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
        if plan.kind == "document" and self.original_files is not None:
            from services.resume_original_file_repository import OriginalFileUnavailable
            try:
                self.original_files.retain(owner, source, plan.prepared["data"])
            except OriginalFileUnavailable:
                # The member-owned SQL reservation survives; the intake
                # transaction rolls back and preserves the member's Add input.
                raise ResumeIntakeStoreUnavailable() from None
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
            from services.resume_onboarding_document_reader import inventory_source
            source["structured_values"] = {"resume_conversation_v1": {
                "schema_version": 1, "source_units": list(parsed.source_units) or inventory_source(parsed.text or "", document=True),
                "pages": list(parsed.pages), "complete": parsed.complete,
                "ocr_configuration_sha256": parsed.ocr_configuration_sha256,
            }}
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
        organization = None
        resume_document = (plan.kind == "document" and self._extraction_adapter is not None
                           and hasattr(self._extraction_adapter, "organize_resume"))
        if self._extraction_adapter is not None and plan.kind in {"text", "document", "recording"}:
            drafts, provider_issue, organization = self._extract_with_adapter(owner, plan)
        else:
            drafts = self._interpreter(plan.source_text or "", plan.kind) or []
        if resume_document:
            # The document is kept either way. When it could not be organized there are no
            # fragment items: the member can try again, sort it by hand, or edit directly.
            if organization is None:
                organization = ResumeOrganization("unavailable", [], [], [])
            drafts = [] if organization.state == "unavailable" else organization.drafts
        elif not drafts and plan.kind == "document":
            from services.my_data_extraction_adapter import validate_resume_extraction_payload
            from services.resume_onboarding_document_reader import inventory_source
            drafts = validate_resume_extraction_payload({"candidates": []}, text=plan.source_text or "",
                source_units=inventory_source(plan.source_text or "", document=True), allowed_fields=EDITOR_FIELDS)
            for draft in drafts:
                draft["kind"] = "inferred_wording"
        elif not drafts:
            # The deterministic manual path always survives: a provider
            # failure leaves editable uncertain wording, never lost input.
            drafts = [{
                "kind": "inferred_wording", "record_type": "unspecified",
                "values": {"text": (plan.source_text or "")[:MAX_TEXT_UNITS]},
                "confidence": "uncertain",
            }]
        created, duplicates = self._proposals_from_drafts(
            owner, snapshot, source, plan, submission_key, submission_version, policy, command,
            drafts, proposals)
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
        if organization is not None:
            summary = organization.summary()
            if organization.state == "unavailable":
                reason = provider_issue or (organization.rejections[0]["code"] if organization.rejections else "unusable_output")
                summary["reason"] = reason
                result["provider_issue"] = {"code": reason, "retryable": True}
                result["message"] = "I read your résumé but couldn't organize it right now. Nothing is lost."
            context = (source.get("structured_values") or {}).get("resume_conversation_v1")
            if isinstance(context, dict):
                context["organization"] = summary
            result["organization"] = summary
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

    # -- document organization: retry, recovery and the batch-scoped review ----

    @staticmethod
    def _source_meta(source):
        return ((source or {}).get("structured_values") or {}).get("resume_conversation_v1") or {}

    @staticmethod
    def _bound_proposals(snapshot, source_key):
        return [row for row in snapshot["proposals"].values()
                if (row.get("binding") or {}).get("source_key") == source_key]

    def _organize_eligibility(self, snapshot, source):
        """Why a document may be organized again: 'unavailable', 'legacy' or None.

        Eligibility is re-derived from stored state on every request, so a repeat
        under a new request id on an already-organized source is refused before any
        dispatch. A legacy source was organized before per-candidate organization
        existed: every proposal it produced is still an untouched unplaced item.
        """
        if (not source or source.get("state") != "active" or source.get("kind") != "document"
                or not source.get("text")):
            return None
        organization = self._source_meta(source).get("organization")
        bound = self._bound_proposals(snapshot, source["source_key"])
        if isinstance(organization, dict):
            if organization.get("state") not in {"unavailable", "member_sorted"}:
                return None
        elif not bound:
            return None
        if all(row["state"] == "pending" and row["record_type"] == "unspecified" for row in bound):
            return "unavailable" if isinstance(organization, dict) else "legacy"
        return None

    def _duplicate_document(self, snapshot, plan):
        """An earlier active copy of this exact file that still has open work."""
        digest = (plan.prepared or {}).get("sha256")
        if plan.kind != "document" or not digest:
            return None
        for source in snapshot["sources"].values():
            if (source.get("state") == "active" and source.get("kind") == "document"
                    and source.get("sha256") == digest):
                meta = self._source_meta(source)
                organization = meta.get("organization")
                unorganized = isinstance(organization, dict) and organization.get("state") == "unavailable"
                if unorganized or any(row["state"] == "pending"
                                      for row in self._bound_proposals(snapshot, source["source_key"])):
                    return source
        return None

    def _reread_original(self, owner, source, policy):
        """Read the member's retained original again with the current reader.

        Returns the fresh ``(text, source_units, pages, complete, ocr_sha256)`` only when it
        differs from what this source stored at upload, so a reader improvement reaches an
        old upload without the member sending the file again. Any gap (no retained original,
        unreadable, unchanged) returns None and the stored reading is used as before.
        """
        files = self.original_files
        if files is None:
            return None
        try:
            rows = [row for row in files.list(owner)
                    if row.get("source_key") == source["source_key"] and row.get("state") == "uploaded"
                    and row.get("downloadable")]
            if not rows:
                return None
            data, content_type = files.download(owner, rows[-1]["original_key"])
            parsed = self.document_adapter.parse(content_type, data, policy, pipeline=self._document_pipeline)
        except Exception:
            return None
        if not parsed.ok or not parsed.text or parsed.text == source.get("text"):
            return None
        from services.resume_onboarding_document_reader import inventory_source
        units = list(parsed.source_units) or inventory_source(parsed.text, document=True)
        return parsed.text, units, list(parsed.pages), parsed.complete, parsed.ocr_configuration_sha256

    def organize_source(self, owner, payload, *, allow_fixture_policy=False):
        """Organize an uploaded résumé again, or let the member sort it by hand.

        ``retry`` makes one provider dispatch for a document whose organization
        failed or predates per-candidate organization; ``sort_myself`` makes none.
        Nothing is deleted: replaced unplaced items become ``invalidated``.
        """
        from services.my_data_extraction_adapter import organize_resume_extraction
        if not getattr(self.repository, "supports_resume_conversation", False):
            raise ResumeIntakeUnavailableError()
        adapter = self._extraction_adapter
        if adapter is None or not hasattr(adapter, "organize_resume"):
            raise ResumeIntakeUnavailableError()
        policy = self._require_usable_policy(allow_fixture=allow_fixture_policy)
        if (not isinstance(payload, dict) or set(payload) != {"request_id", "source_key", "mode"}
                or payload["mode"] not in {"retry", "sort_myself"}):
            raise ResumeIntakeValidationError("Invalid request.")
        request_id = _as_uuid(payload["request_id"], field="request id")
        source_key = _as_uuid(payload["source_key"], field="source key")
        mode = payload["mode"]
        digest = _json_digest({"type": "organize_source", "source_key": source_key, "mode": mode})
        moment = _utc(None)
        with self.repository.owner_guard(owner):
            snapshot = self._load(owner)
            existing = snapshot["receipts"].get(request_id)
            if existing is not None:
                if existing["request_digest"] != digest:
                    raise ResumeIntakeConflictError(
                        "idempotency_conflict", [{"request_id": request_id}],
                        "That request key was already used for different content.")
                return {**existing["result"], "replayed": True, "request_digest": digest}
            source = snapshot["sources"].get(source_key)
            if source is None or source.get("state") != "active" or source.get("kind") != "document":
                raise ResumeIntakeNotFoundError()
            reason = self._organize_eligibility(snapshot, source)
            bound = self._bound_proposals(snapshot, source_key)
            pending = [row for row in bound if row["state"] == "pending"]
            if reason is None or (mode == "sort_myself" and pending):
                # Checked before any budget is reserved: a repeat dispatches nothing and writes nothing.
                return {"success": True, "outcome": "already_organized", "source_key": source_key,
                        "request_id": request_id, "replayed": False, "saved": False, "publishes": False,
                        "message": "This résumé is already organized."}
            meta = self._source_meta(source)
            units = list(meta.get("source_units") or [])
            text = source["text"]
            refreshed = self._reread_original(owner, source, policy) if mode == "retry" else None
            if refreshed:
                text, units = refreshed[0], refreshed[1]
            if mode == "retry":
                from uuid import uuid5
                try:
                    organization = adapter.organize_resume(
                        text, allowed_fields={name: EDITOR_FIELDS[name] for name in EDITOR_FIELDS},
                        source_units=units, shortlist=self._matching_shortlist(owner),
                        request_id=str(uuid5(UUID(request_id), "organize_source")))
                except ExtractionError as error:
                    # Nothing changed: the member's words and this source stay exactly as they were.
                    return {"success": True, "outcome": "unavailable", "source_key": source_key,
                            "request_id": request_id, "replayed": False, "saved": False, "publishes": False,
                            "provider_issue": {"code": error.code, "retryable": True},
                            "message": "The organizer is unavailable right now. Nothing was changed."}
            else:
                organization = organize_resume_extraction(
                    {"candidates": []}, text=text, source_units=units,
                    allowed_fields={name: EDITOR_FIELDS[name] for name in EDITOR_FIELDS})
            snapshot["policy_version"] = policy.version
            summary = organization.summary()
            created, matched, replaced = [], [], 0
            if refreshed and not (organization.state == "unavailable" and mode == "retry"):
                # A fresh reading replaces the stored one under a new source version, so nothing
                # created from the old reading can be mistaken for it.
                source["text"], source["version"] = text, int(source.get("version") or 1) + 1
                meta.update(source_units=units, pages=refreshed[2], complete=refreshed[3],
                            ocr_configuration_sha256=refreshed[4])
            if organization.state == "unavailable" and mode == "retry":
                meta["organization"] = {**summary, "reason": "unusable_output"}
            else:
                for row in pending:
                    invalidate_proposal(snapshot, row["proposal_key"], now=moment)
                submission = snapshot["submissions"].get(source.get("submission_key")) or {}
                plan = _ItemPlan(client_key="organize-" + source_key, kind="document", record_type="unspecified",
                                 source_text=text, quote=text[:300], confidence="uncertain")
                proposals = []
                # The same outcome-to-kind rule as an upload, so a role the model matched to a saved
                # record still amends it instead of creating a second one.
                drafts = [{**draft, "kind": _resume_draft_kind(draft)} for draft in organization.drafts]
                created, matched = self._proposals_from_drafts(
                    owner, snapshot, source, plan, source["submission_key"], int(submission.get("version") or 1),
                    policy, {"request_digest": digest}, drafts, proposals)
                replaced = len(pending)
                meta["organization"] = {**summary, "state": "member_sorted" if mode == "sort_myself" else summary["state"]}
            if created:
                message = "Organized. Nothing is saved until you review it."
            elif matched:
                message = "Everything in this résumé is already in your saved résumé, so there is nothing new to review."
            else:
                message = "I still couldn't organize it. Nothing was changed."
            if matched and created:
                message += (" %d %s already in your résumé and %s left as %s."
                            % (len(matched), "item was" if len(matched) == 1 else "items were",
                               "was" if len(matched) == 1 else "were", "it is" if len(matched) == 1 else "they are"))
            if replaced and (created or matched):
                message += " %d loose %s from the earlier reading %s set aside, not deleted." % (
                    replaced, "item" if replaced == 1 else "items", "was" if replaced == 1 else "were")
            result = {"success": True, "request_id": request_id, "request_digest": digest, "replayed": False,
                      "outcome": "organized" if (created or matched) else "unavailable", "source_key": source_key,
                      "mode": mode, "organization": meta["organization"], "saved": False, "publishes": False,
                      "proposal_keys": [row["proposal_key"] for row in created],
                      "already_saved_count": len(matched), "replaced": replaced, "message": message}
            snapshot["receipts"][request_id] = {"request_digest": digest, "submission_key": None,
                                                "result": receipt_for_storage(result)}
            self.repository.save_owner(owner, snapshot)
            return result

    def _review_overview(self, snapshot):
        """The batch-scoped grouped review: derived, read-only, never a second store."""
        pending = [row for row in snapshot["proposals"].values() if row["state"] == "pending"]
        documents = [row for row in snapshot["sources"].values()
                     if row.get("state") == "active" and row.get("kind") == "document" and row.get("text")]
        documents.sort(key=lambda row: row.get("created_at") or "")

        def open_work(source):
            return (self._organize_eligibility(snapshot, source) is not None
                    or any((row.get("binding") or {}).get("source_key") == source["source_key"] for row in pending))

        batch_source = next((row for row in reversed(documents) if open_work(row)), None)
        overview = {"schema_version": 1, "batch": None,
                    "counts": {"experience": 0, "education": 0, "credentials": 0, "skills": 0, "other": 0, "unplaced": 0},
                    "groups": [], "unplaced": {"count": 0, "proposal_keys": []}, "earlier": {"count": 0},
                    "duplicate_source_keys": []}
        if batch_source is None:
            overview["earlier"]["count"] = len(pending)
            return overview
        key = batch_source["source_key"]
        meta = self._source_meta(batch_source)
        eligibility = self._organize_eligibility(snapshot, batch_source)
        organization = meta.get("organization") if isinstance(meta.get("organization"), dict) else {
            "state": "legacy_unorganized" if eligibility == "legacy" else "organized"}
        overview["batch"] = {
            "source_key": key, "created_at": batch_source.get("created_at"),
            "document": {"pages": len({u.get("page") for u in meta.get("source_units") or [] if u.get("page")}) or None,
                         "complete": meta.get("complete")},
            "organization": {"state": organization.get("state"),
                             "rejected": len([r for r in organization.get("rejections") or []
                                              if r.get("action") != "field_cleared"])},
            "retry_available": eligibility is not None, "retry_reason": eligibility}
        overview["duplicate_source_keys"] = [row["source_key"] for row in documents
                                             if row["source_key"] != key and row.get("sha256") == batch_source.get("sha256")]
        units = {u["unit_id"]: u for u in meta.get("source_units") or []}
        bucket = {"Experience": "experience", "Education": "education", "Credentials": "credentials", "Skills": "skills"}
        groups = []
        # Creation order is the structural clock: wall-clock ties can occur within one tick.
        position = {name: index for index, name in enumerate(snapshot["proposals"])}
        submission = batch_source.get("submission_key")
        # Everything added in the same Add as the document (typed words, a recording) is one batch.
        bound = [position[name] for name, row in snapshot["proposals"].items()
                 if (row.get("binding") or {}).get("submission_key") == submission]
        started = batch_source.get("created_at") or ""

        def newer(row):
            if bound:
                return position[row["proposal_key"]] >= min(bound)
            return (row.get("created_at") or "") >= started

        for row in pending:
            conversation = row.get("resume_conversation_v1") or {}
            from_batch = (row.get("binding") or {}).get("submission_key") == submission
            if (row.get("binding") or {}).get("source_key") == key and row["record_type"] == "unspecified" and conversation.get("presentation_section") == "Unsorted":
                overview["counts"]["unplaced"] += 1
                overview["unplaced"]["count"] += 1
                overview["unplaced"]["proposal_keys"].append(row["proposal_key"])
                continue
            # Work created after this upload (corrections, additions) belongs to it; older pending
            # work stays reachable behind its own deliberate navigation.
            if not from_batch and not newer(row):
                overview["earlier"]["count"] += 1
                continue
            section = conversation.get("presentation_section") or "Other"
            overview["counts"][bucket.get(section, "other")] += 1
            groups.append(self._overview_group(row, conversation, section, units))
        order = ["Experience", "Education", "Credentials", "Skills"]
        groups.sort(key=lambda g: g["heading"]["start_date"] or "", reverse=True)
        groups.sort(key=lambda g: (order.index(g["section"]) if g["section"] in order else len(order),
                                   not g["heading"]["current"], g["heading"]["start_date"] is None))
        overview["groups"] = groups
        return overview

    @staticmethod
    def _overview_group(row, conversation, section, units):
        values = dict(row.get("proposed_values") or {})
        record_type = row["record_type"]
        description = ("wording" if record_type == "knowledge"
                       else "resume_credential_wording" if record_type == "credential" else "summary")
        effective = values.get(description) or values.get("text") or ""
        ids = list(conversation.get("unit_ids") or [])
        selected = sorted((units[i] for i in ids if i in units), key=lambda u: u["span_start"])
        # Lines come from the effective wording. A unit id is attached only while that wording
        # is still exactly the joined source text, so an edited or amended item never shows stale source lines.
        if selected and "\n".join(u["text"] for u in selected) == effective:
            lines = [{"text": u["text"], "unit_id": u["unit_id"],
                      "role": "header" if u["unit_id"] == conversation.get("record_anchor") else "line"}
                     for u in selected]
        else:
            lines = [{"text": part, "unit_id": None, "role": "line"}
                     for part in effective.split("\n") if part.strip()]
        title = (values.get("role_title") or values.get("degree_name") or values.get("title")
                 or values.get("name") or None)
        return {
            "record_ref": "proposal:" + row["proposal_key"], "proposal_key": row["proposal_key"],
            "section": section, "record_type": record_type, "state": row["state"],
            "heading": {"title": title,
                        "organization": (values.get("employer_name") or values.get("institution_name")
                                         or values.get("issuer") or None),
                        "location": values.get("location_text"),
                        "start_date": values.get("start_date"), "end_date": values.get("end_date"),
                        "date_precision": values.get("date_precision"),
                        "current": values.get("current_role") is True},
            "uncertain_fields": list(conversation.get("uncertain_fields") or []),
            "requires_member_wording": bool(row.get("requires_member_wording")),
            "lines": lines,
            "source": {"source_key": (row.get("provenance") or {}).get("source_key"), "unit_ids": ids,
                       "pages": sorted({units[i].get("page") for i in ids if i in units and units[i].get("page")})},
            "version_token": _json_digest({"proposal_key": row["proposal_key"], "state": row["state"],
                                           "proposed_values": values, "binding": row.get("binding"),
                                           "uncertain_fields": conversation.get("uncertain_fields")}),
        }

    def _proposals_from_drafts(self, owner, snapshot, source, plan, submission_key, submission_version,
                               policy, command, drafts, proposals):
        """Create pending proposals for extracted drafts; returns ``(created, duplicates)``."""
        duplicates: list[dict] = []
        created = []
        for draft in drafts or []:
            if draft.get("outcome") == "equivalent":
                # A true restatement keeps the existing entry and permissions:
                # no proposal, no write, just a quiet truthful receipt entry.
                # A reference that no longer resolves stays visible as an
                # uncertain proposal instead of silently vanishing.
                duplicate = self._resolve_equivalent(owner, draft)
                if duplicate is not None:
                    source_context = (source.get("structured_values") or {}).get("resume_conversation_v1") or {}
                    for source_unit in source_context.get("source_units") or []:
                        if source_unit["unit_id"] in (draft.get("unit_ids") or []):
                            source_unit["disposition"] = "equivalent"
                            source_unit["record_key"] = duplicate["record_key"]
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
                elif kind == "additional_detail":
                    # Present the combined amendment for member review. A
                    # confirmed append must not silently replace prior meaning.
                    values = dict(draft.get('values') or {})
                    for name in ('summary', 'wording'):
                        existing_values = (target.get('proposed_values') if target.get('has_draft')
                                           else target.get('values')) or {}
                        existing = existing_values.get(name)
                        addition = values.get(name)
                        if existing and addition and addition not in existing:
                            values[name] = existing.rstrip() + '\n' + addition
                    draft = {**draft, 'values': values}
            proposal = self._make_proposal(
                snapshot, plan, source, submission_key, submission_version, policy, command,
                kind=kind,
                target=target,
                confidence=draft.get("confidence") or "uncertain",
                record_type=draft.get("record_type") or "unspecified",
                proposed_values={**(draft.get("values") or {}),
                    **({"suggested_category": draft["suggested_category"]}
                       if draft.get("suggested_category") else {}),
                    **({"suggested_parent_key": draft["parent_reference"]}
                       if draft.get("parent_reference") else {})},
                provided_fields=draft.get("provided_fields"),
                quote=draft.get("quote"),
                span_start=draft.get("span_start"),
                span_end=draft.get("span_end"),
            )
            if draft.get("unit_ids"):
                proposal["resume_conversation_v1"] = {
                    "unit_ids": list(draft["unit_ids"]), "record_anchor": draft.get("record_anchor"),
                    "presentation_section": draft.get("presentation_section"),
                }
                if draft.get("uncertain_fields"):
                    proposal["resume_conversation_v1"]["uncertain_fields"] = list(draft["uncertain_fields"])
                if draft.get("placement"):
                    proposal["resume_conversation_v1"]["placement"] = draft["placement"]
                if target and proposal['record_type'] == 'credential':
                    self._capture_credential_binding(owner, snapshot, proposal, target['record_key'])
                source_context = (source.get("structured_values") or {}).get("resume_conversation_v1") or {}
                for source_unit in source_context.get("source_units") or []:
                    if source_unit["unit_id"] in draft["unit_ids"]:
                        source_unit["disposition"] = "pending" if proposal["record_type"] != "unspecified" else "unresolved"
                        source_unit["proposal_key"] = proposal["proposal_key"]
            created.append(proposal)
            proposals.append(proposal)
        return created, duplicates

    def _extract_with_adapter(self, owner, plan):
        """Run strict Luna extraction, or report the provider failure.

        Returns ``(drafts, provider_issue)``. A failure keeps the member's
        input for the deterministic manual path and marks the result
        retryable: there is no fallback model, effort, or free-form mode.
        """

        text = plan.source_text or ""
        shortlist = self._matching_shortlist(owner)
        try:
            # The older private-provider seam carries source_text alone. Only
            # an explicitly declared document uses the resume inventory path.
            if getattr(plan, 'kind', None) == "document" and hasattr(self._extraction_adapter, "organize_resume"):
                from services.resume_onboarding_document_reader import inventory_source
                organization = self._extraction_adapter.organize_resume(text,
                    allowed_fields={name: EDITOR_FIELDS[name] for name in EDITOR_FIELDS},
                    source_units=inventory_source(text, document=True), shortlist=shortlist)
                for draft in organization.drafts:
                    draft["kind"] = _resume_draft_kind(draft)
                return organization.drafts, None, organization
            candidates = self._extraction_adapter.extract(
                text,
                allowed_fields={name: EDITOR_FIELDS[name] for name in EDITOR_FIELDS},
                shortlist=shortlist,
            )
        except ExtractionError as error:
            return None, error.code, None
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
                "suggested_category": candidate.suggested_category,
                "parent_reference": candidate.parent_reference,
            })
        return drafts, None, None

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

    def _canonical_view(self, owner):
        """Read the owner's existing facts and draft version in one read.

        Treating an unreadable catalog as empty would let the composer save a
        duplicate and mis-route a change to an existing fact as a new one. The
        same read supplies the authoritative draft version an overlay command
        fences against, so no caller ever guesses it.
        """

        try:
            workspace = self.draft_service.get_workspace(owner)
        except (ResumeDraftUnavailableError, CanonicalReadUnavailable,
                ResumeDraftStoreUnavailable) as error:
            raise ResumeIntakeUnavailableError() from error
        items = workspace.get("items")
        if not isinstance(items, list):
            raise ResumeIntakeUnavailableError()
        draft_version = workspace.get("draft_version")
        if (
            isinstance(draft_version, bool)
            or not isinstance(draft_version, int)
            or draft_version < 0
        ):
            raise ResumeIntakeUnavailableError()
        return [item for item in items if not item.get("orphaned")], draft_version

    def _canonical_items(self, owner):
        items, _draft_version = self._canonical_view(owner)
        return items

    def _save_new_fact(self, owner, snapshot, unit, plan, submission_key):
        record_key = _stable_key(submission_key, f"fact:{plan.client_key}")
        try:
            normalized = (_normalize_draft_values("knowledge", plan.provided_values)
                          if plan.record_type == "knowledge"
                          else normalize_editor_values(plan.record_type, plan.provided_values))
        except LivingResumeEditorValidationError as error:
            raise ResumeIntakeValidationError(str(error)) from error
        if plan.record_type == 'knowledge' and isinstance(unit, SqlIntakeUnitOfWork):
            raise ResumeIntakeValidationError('Guided personal stories are not supported by this storage yet. '
                'Your input is kept. Use the existing entry editor or the private local workspace.')
        if (plan.record_type == 'credential' and isinstance(unit, SqlIntakeUnitOfWork)
                and {'issue_date_precision', 'expiration_date_precision'} & set(normalized)):
            from services.living_resume_editor_service import CREDENTIAL_PRECISION_UNAVAILABLE
            raise ResumeIntakeValidationError(CREDENTIAL_PRECISION_UNAVAILABLE)
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
        boundary = "living_resume"
        if plan.record_type == "knowledge":
            boundary = "resume_draft"
            callee_command = {k: v for k, v in payload.items() if k != "request_id"}
            callee_command["request_digest"] = self.draft_service.command_digest(payload)
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
                boundary=boundary, request_id=item_request_id,
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

    def _capture_credential_binding(self, owner, snapshot, proposal, credential_key):
        linked = next((b for b in self._credential_bindings(snapshot)
            if b['credential_key'] == credential_key), None)
        if linked is None:
            return
        note = self._find_item(owner, linked['supplement_key'])
        if note is None or note['record_type'] != 'knowledge':
            raise ResumeIntakeConflictError('changed', [], 'The credential details changed. Review both records again.')
        proposal['resume_conversation_v1']['credential_binding'] = {
            **linked, 'supplement_content_token': note['content_token'],
            'supplement_access_revision': note['access_revision'],
            'supplement_values_digest': _json_digest({**note['values'], **(note.get('proposed_values') or {})})}

    def _apply_decision(self, owner, snapshot, unit, proposal, confirmed):
        values = dict((confirmed if confirmed is not None else proposal.get('confirmed_values')) or {})
        meta = proposal.get('resume_conversation_v1') or {}
        linked = meta.get('credential_binding')
        wording = values.pop('resume_credential_wording', (proposal.get('proposed_values') or {}).get('resume_credential_wording'))
        if proposal.get('record_type') != 'credential' or (wording is None and linked is None):
            return self._apply_record_decision(owner, snapshot, unit, proposal, confirmed)
        from services.resume_intake_repository import InMemoryIntakeUnitOfWork
        if (not isinstance(unit, InMemoryIntakeUnitOfWork) or not unit.supports_atomic_composition or not meta.get('unit_ids')
                or meta.get('presentation_section') != 'Credentials'):
            raise ResumeIntakeValidationError('This storage cannot save complete credential details atomically. '
                'Your proposal is kept; nothing was saved.')
        note = None
        if linked:
            if linked.get('owner_user_key') != owner or linked.get('credential_key') != proposal.get('target_key'):
                raise ResumeIntakeConflictError('changed', [], 'The credential details changed.')
            note = self._find_item(owner, linked['supplement_key'])
            if (note is None or note.get('record_type') != 'knowledge'
                    or note.get('content_token') != linked.get('supplement_content_token')
                    or note.get('access_revision') != linked.get('supplement_access_revision')
                    or _json_digest({**note['values'], **(note.get('proposed_values') or {})}) != linked.get('supplement_values_digest')):
                raise ResumeIntakeConflictError('changed', [], 'The credential details changed. Review both records again.')
            if wording is None:
                wording = {**note['values'], **(note.get('proposed_values') or {})}.get('wording')
        wording = _text(wording, field='complete credential wording', maximum=8000, required=True)
        parent = self._apply_record_decision(owner, snapshot, unit, proposal, values)
        note_values = {'title': 'Credential details', 'wording': wording, 'classification': 'work'}
        if note:
            note_proposal = {**proposal, 'record_type': 'knowledge', 'target_key': note['record_key'],
                'target_content_token': note['content_token'], 'target_access_revision': note['access_revision'],
                'explicit_clears': [], 'resume_conversation_v1': {**meta, 'credential_supplement': True}}
            saved_note = self._apply_record_decision(owner, snapshot, unit, note_proposal, note_values)
        else:
            plan = _ItemPlan(client_key='credential-supplement', kind='structured', record_type='knowledge',
                provided_values=note_values)
            saved_note = self._save_new_fact(owner, snapshot, unit, plan, proposal['proposal_key'])
        # No name/order relationship, duplicate text in receipts, or fabricated
        # canonical parent column. This private approved binding travels in the
        # same owner transaction as both records and source accounting.
        meta['approved_credential_binding'] = {
            'owner_user_key': owner, 'credential_key': parent['record_key'], 'supplement_key': saved_note['record_key'],
            'proposal_key': proposal['proposal_key'], 'source_key': proposal['binding']['source_key'],
            'source_version': proposal['binding']['source_version'],
            'source_refs': copy.deepcopy(meta.get('source_refs') or [
                {'source_key': proposal['binding']['source_key'], 'unit_id': key} for key in meta['unit_ids']]),
            'source_bindings': copy.deepcopy(meta.get('source_bindings') or []),
            'credential_content_token': parent.get('content_token'), 'credential_access_revision': parent.get('access_revision'),
            'supplement_content_token': saved_note.get('content_token'), 'supplement_access_revision': saved_note.get('access_revision')}
        return parent

    def _apply_record_decision(self, owner, snapshot, unit, proposal, confirmed):
        target_key = proposal.get("target_key")
        record_type = proposal.get("record_type")
        values = dict((confirmed if confirmed is not None else proposal.get("confirmed_values")) or {})
        if record_type in {None, "unspecified"}:
            record_type = values.pop("record_type", None)
        resume_binding = proposal.get("resume_conversation_v1") or {}
        source_knowledge = (record_type == "knowledge" and bool(resume_binding.get("unit_ids"))
                            and resume_binding.get("presentation_section") in {
                                "My Story", "Awards", "Professional summary", "Contact details", "Independent Project"}
                            or record_type == 'knowledge' and resume_binding.get('credential_supplement') is True)
        if record_type not in STRUCTURED_RECORD_TYPES and not (
                source_knowledge or record_type == "knowledge" and proposal.get("record_type") == "unspecified"
                and not target_key):
            raise ResumeIntakeConflictError(
                "reconciliation_required",
                [{"proposal_key": proposal["proposal_key"], "reason": "record_type_required"}],
                "Choose what this should become before saving it.",
                proposed=proposal.get("proposed_values"),
            )
        if record_type == "knowledge":
            expected_class = ("personal" if not source_knowledge or resume_binding.get("presentation_section") == "My Story" else "work")
            if values.get("classification", expected_class) != expected_class:
                raise ResumeIntakeValidationError("Choose a personal entry for My Story." if expected_class == "personal" else
                    "Keep this resume supplement separate from My Story.")
            values["classification"] = expected_class
        # ``parent_key`` is relationship metadata, not an editor field. It is
        # only meaningful when creating a child; an overlay change keeps the
        # existing parent.
        supplied_parent = values.pop("parent_key", None)
        fields = (frozenset({"title", "wording", "classification"})
                  if record_type == "knowledge" else EDITOR_FIELDS[record_type])
        unknown = set(values) - fields
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
        # against the versions captured when the proposal was made. The same
        # read supplies the authoritative draft version fenced below.
        items, expected_draft_version = self._canonical_view(owner)
        existing = next(
            (item for item in items if item.get("record_key") == target_key), None
        )
        if existing is None:
            raise ResumeIntakeNotFoundError()
        clears = list(proposal.get("explicit_clears") or [])
        merged = {**(existing.get("values") or {}), **(existing.get('proposed_values') or {})}
        merged.update(values)
        for name in clears:
            merged[name] = _empty_value(name)
        try:
            normalized = (_normalize_draft_values(record_type, merged) if record_type == "knowledge"
                          else normalize_editor_values(record_type, merged))
        except LivingResumeEditorValidationError as error:
            raise ResumeIntakeValidationError(str(error)) from error
        partial = {name: normalized.get(name) for name in values}
        for name in clears:
            partial[name] = _empty_value(name)
        if (record_type == 'credential' and isinstance(unit, SqlIntakeUnitOfWork)
                and {'issue_date_precision', 'expiration_date_precision'} & set(partial)):
            from services.living_resume_editor_service import CREDENTIAL_PRECISION_UNAVAILABLE
            raise ResumeIntakeValidationError(CREDENTIAL_PRECISION_UNAVAILABLE)
        overlay_request_id = _stable_key(proposal["proposal_key"],
            "credential-supplement-overlay" if resume_binding.get('credential_supplement') else "overlay")
        payload = {
            "request_id": overlay_request_id,
            "type": "save_item",
            "record_key": target_key,
            "record_type": existing.get("record_type") or record_type,
            "expected_content_token": proposal.get("target_content_token"),
            "expected_access_revision": proposal.get("target_access_revision"),
            "expected_draft_version": expected_draft_version,
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
        # The draft procedure takes @RequestId as its own parameter and reads
        # only its declared JSON keys, so the request id must not appear inside
        # the command body. The digest is the canonical semantic digest of the
        # same normalized command the in-memory path commits, so a retried
        # intent replays and a changed one conflicts.
        try:
            callee_command = {k: v for k, v in payload.items() if k != "request_id"}
            callee_command["request_digest"] = self.draft_service.command_digest(payload)
            applied = unit.apply_canonical_command(
                owner, payload, projected,
                boundary="resume_draft", request_id=overlay_request_id,
                callee_command=callee_command,
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


def _resume_draft_kind(draft):
    """One outcome-to-kind rule for an organized resume, shared by upload and retry."""
    if draft["outcome"] == "new" and draft["record_type"] != "unspecified":
        return "new_fact"
    if draft["outcome"] in {"additional_detail", "contradiction"}:
        return draft["outcome"]
    return "inferred_wording"


_RECEIPT_WORD_FIELDS = frozenset({
    "quote", "proposed_values", "confirmed_values", "values", "transcript",
    "extracted_fields",
    "canonical_values",
    "resume_conversation_v1",
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
        # Mutable source evidence holds the existing editor's deterministic
        # normalized copy. SQL compares staged values to it without inventing
        # a second set of normalization/default rules or accepting client values.
        raw = candidate["values"]
        if record_type in EDITOR_FIELDS and not (set(raw) & FORBIDDEN_CLIENT_FIELDS):
            filtered = {name: value for name, value in raw.items()
                        if name in EDITOR_FIELDS[record_type] and value is not None}
            try:
                candidate["canonical_values"] = normalize_editor_values(record_type, filtered)
            except LivingResumeEditorValidationError:
                pass  # Incomplete candidates retain the existing validation path.
        candidates.append(candidate)
        actions.append({
            "override_key": override_key,
            "record_type": record_type,
            "record_key": duplicate.get("record_key"),
        })
    source["structured_values"] = {**(source.get("structured_values") or {}), _EXTRACTED_CANDIDATES_FIELD: candidates}
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

    result = {
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
    if 'guide_state' in row:
        result['guide_state'] = copy.deepcopy(row['guide_state'])
    return result


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
