"""Optional contextual guide for the private Resume composer (MVP1 C).

Completion is the member's own choice. It is never a content score, an elapsed
time, or an inference from existing content, and simply having Resume records
does not prove onboarding was completed. A read failure reports
``load_state="unavailable"`` -- it is never rendered as "new member" or
"nothing saved yet".

GET does not start ingestion or provider work: this service only reads and
writes member-chosen guide status.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import copy
from uuid import UUID, uuid4

from services.resume_intake_repository import COMMAND_PROCEDURES
from services.resume_intake_repository import (
    InMemoryResumeIntakeRepository,
    ResumeIntakeStoreUnavailable,
    empty_intake_snapshot,
    validate_snapshot,
)


GUIDE_STATUSES = ("not_started", "in_progress", "paused", "completed", "skipped")
MEMBER_SETTABLE_STATUSES = frozenset({"in_progress", "paused", "completed", "skipped"})


class GuideValidationError(ValueError):
    code = "invalid"


class GuideUnavailableError(RuntimeError):
    code = "unavailable"


class GuideConflictError(RuntimeError):
    code = "idempotency_conflict"


def _utc(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ResumeGuideService:
    def __init__(self, repository=None) -> None:
        self.repository = repository or InMemoryResumeIntakeRepository()

    def _load(self, owner: str) -> dict:
        try:
            snapshot = self.repository.load_owner(owner)
        except ResumeIntakeStoreUnavailable as error:
            raise GuideUnavailableError("The guide is unavailable.") from error
        if not snapshot:
            return empty_intake_snapshot()
        snapshot.setdefault("guide", {})
        return snapshot

    def get_state(self, owner: str, *, question: dict | None = None) -> dict:
        """Read-only. Never starts processing and never invents member state."""

        snapshot = self._load(owner)
        guide = snapshot.get("guide") or {}
        return {
            "load_state": "loaded",
            "status": guide.get("status") or "not_started",
            "status_source": guide.get("status_source") or "default_unstarted",
            "member_choice": guide.get("status_source") == "member",
            "question": self._question(question),
            "statuses": list(GUIDE_STATUSES),
            "completion_is_member_action": True,
            "read_does_not_start_processing": True,
            "read_error_is_not_new_member": True,
        }

    def unavailable_state(self, *, question: dict | None = None) -> dict:
        """Honest read-failure shape. Not 'not_started'; not an empty member."""

        return {
            "load_state": "unavailable",
            "status": None,
            "status_source": "unavailable",
            "member_choice": False,
            "question": self._question(question),
            "statuses": list(GUIDE_STATUSES),
            "completion_is_member_action": True,
            "read_does_not_start_processing": True,
            "read_error_is_not_new_member": True,
            "message": "The guide is unavailable right now. Your saved work is unchanged.",
        }

    @staticmethod
    def unavailable_first_arrival():
        return {"read_state": "unavailable", "eligible": None,
            "shown": None, "dismissed": None, "started": None}

    def _arrival_snapshot(self, owner):
        if not isinstance(owner, str) or not owner.strip():
            raise GuideValidationError("Invalid owner context.")
        if not getattr(self.repository, "supports_guide_first_arrival", False):
            raise GuideUnavailableError("First arrival is unavailable for this storage.")
        snapshot = self.repository.load_owner(owner)
        validate_snapshot(snapshot)  # Validate, retaining other legitimate snapshot metadata.
        return snapshot

    @staticmethod
    def _arrival_flags(snapshot):
        arrival = snapshot["guide"].get("first_arrival", {})
        if not isinstance(arrival, dict) or set(arrival) - {"shown", "dismissed", "started"}:
            raise GuideUnavailableError("First arrival state is unavailable.")
        if any(type(value) is not bool for value in arrival.values()):
            raise GuideUnavailableError("First arrival state is unavailable.")
        return {key: arrival.get(key, False) for key in ("shown", "dismissed", "started")}

    @staticmethod
    def _arrival_projection(owner, snapshot, read_content):
        def supplied(value):
            if isinstance(value, str):
                return bool(value.strip())
            if isinstance(value, dict):
                return any(supplied(item) for item in value.values())
            if isinstance(value, list):
                return any(supplied(item) for item in value)
            return value is not None and value is not False
        guide = snapshot["guide"]
        flags = ResumeGuideService._arrival_flags(snapshot)
        has_content = bool(guide) or any(snapshot[name] for name in ("sources", "proposals", "submissions", "jobs"))
        for draft in snapshot["drafts"].values():
            if not isinstance(draft, dict):
                raise GuideUnavailableError("Private draft content is unavailable.")
            words = draft.get("text")
            words = "" if words is None else words  # The existing composer stores absent text as null.
            if not isinstance(words, str):
                raise GuideUnavailableError("Private draft content is unavailable.")
            if any(not isinstance(draft.get(key, []), list) for key in ("items", "attachments")):
                raise GuideUnavailableError("Private draft content is unavailable.")
            state = draft.get("guide_state") or {}
            if not isinstance(state, dict):
                raise GuideUnavailableError("Private draft content is unavailable.")
            has_content = has_content or bool(words.strip() or draft.get("items") or draft.get("attachments"))
            for key in ("manual_fields", "correction_inputs", "proposal_drafts", "pending_conversation"):
                fields = state.get(key) or {}
                if not isinstance(fields, dict):
                    raise GuideUnavailableError("Private draft content is unavailable.")
                has_content = has_content or supplied(fields)
            history = state.get("navigation_history") or []
            if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
                raise GuideUnavailableError("Private draft content is unavailable.")
            has_content = has_content or any(supplied(row.get("text")) for row in history)
        if not has_content:
            try:
                content = read_content(owner)
            except Exception as error:
                raise GuideUnavailableError("Private resume content is unavailable.") from error
            if type(content) is not bool:
                raise GuideUnavailableError("Private resume content is unavailable.")
            has_content = content
        return {"read_state": "available", "eligible": not has_content, **flags}

    def get_first_arrival(self, owner, *, read_content):
        """A qualified negative-content read; never creates an owner or marker."""
        try:
            with self.repository.owner_guard(owner):
                snapshot = self._arrival_snapshot(owner)
                return self._arrival_projection(owner, snapshot, read_content)
        except (ResumeIntakeStoreUnavailable, GuideUnavailableError, TypeError, ValueError):
            return self.unavailable_first_arrival()

    def acknowledge_first_arrival(self, owner, payload, *, read_content):
        """Claim shown once, or record an explicit dismissal/start; no content save."""
        if not isinstance(payload, dict) or set(payload) != {"request_id", "first_arrival_action"}:
            raise GuideValidationError("Invalid first arrival acknowledgment.")
        action, request_id = payload["first_arrival_action"], payload["request_id"]
        if not isinstance(action, str) or action not in {"shown", "dismissed", "started"}:
            raise GuideValidationError("Invalid first arrival acknowledgment.")
        try:
            if str(UUID(request_id)) != request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError) as error:
            raise GuideValidationError("Invalid acknowledgment request id.") from error
        digest = hashlib.sha256(json.dumps({"type": "acknowledge_guide_first_arrival", "action": action},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        try:
            with self.repository.owner_guard(owner):
                snapshot = self._arrival_snapshot(owner)
                existing = snapshot["receipts"].get(request_id)
                if existing is not None:
                    if existing.get("request_digest") != digest:
                        raise GuideConflictError("That request key was already used for another action.")
                    receipt = existing.get("result")
                    if (not isinstance(receipt, dict) or receipt.get("type") != "acknowledge_guide_first_arrival"
                            or receipt.get("request_id") != request_id or receipt.get("request_digest") != digest
                            or receipt.get("action") != action or receipt.get("persisted") is not True
                            or receipt.get("canonical_write") is not False):
                        raise GuideUnavailableError("Acknowledgment receipt is unavailable.")
                    return {"success": True, "replayed": True, "show_now": False,
                        "receipt": copy.deepcopy(receipt),
                        "first_arrival": self._arrival_projection(owner, snapshot, read_content)}
                flags = self._arrival_flags(snapshot)
                if flags[action]:
                    return {"success": True, "replayed": False, "show_now": False,
                        "receipt": None, "first_arrival": self._arrival_projection(owner, snapshot, read_content)}
                # Only automatic showing requires proof of absent content.
                # Explicit member choices remain recordable during a catalog outage.
                if action == "shown":
                    before = self._arrival_projection(owner, snapshot, read_content)
                    if not before["eligible"]:
                        return {"success": True, "replayed": False, "show_now": False,
                            "receipt": None, "first_arrival": before}
                guide = snapshot["guide"]
                guide.setdefault("first_arrival", {})[action] = True
                receipt = {"success": True, "type": "acknowledge_guide_first_arrival",
                    "request_id": request_id, "request_digest": digest, "action": action,
                    "persisted": True, "canonical_write": False}
                snapshot["receipts"][request_id] = {"request_digest": digest,
                    "submission_key": None, "result": receipt}
                committed = self.repository.save_owner(owner, snapshot, {
                    "procedure": COMMAND_PROCEDURES["set_guide_status"], "request_id": request_id,
                    "payload": {"type": "set_guide_status", "request_id": request_id,
                        "request_digest": digest, "status": guide.get("status") or "not_started",
                        "status_source": guide.get("status_source") or "default_unstarted", "receipt": receipt}})
                current = self._arrival_snapshot(owner)
                stored = current["receipts"].get(request_id)
                if (not isinstance(stored, dict) or stored.get("request_digest") != digest
                        or stored.get("result") != receipt or current["guide"].get("first_arrival", {}).get(action) is not True):
                    raise GuideUnavailableError("The acknowledgment could not be verified.")
                replayed = bool(committed and committed.get("replayed"))
                return {"success": True, "replayed": replayed,
                    "show_now": action == "shown" and not replayed, "receipt": copy.deepcopy(receipt),
                    "first_arrival": self._arrival_projection(owner, current, read_content)}
        except ResumeIntakeStoreUnavailable as error:
            raise GuideUnavailableError("First arrival is unavailable.") from error

    def _status_response(self, owner, receipt, *, replayed, question=None):
        if not isinstance(receipt, dict):
            raise GuideUnavailableError("The guide is unavailable.")
        current = self.get_state(owner, question=question)
        original = copy.deepcopy(receipt)
        # ``status`` remains the acknowledged command's structural outcome.
        # A later member choice is available only under the explicit current
        # label, so replay never rewrites the meaning of the original digest.
        return {
            **current,
            **original,
            "receipt": original,
            "current_state": current,
            "replayed": bool(replayed),
        }

    def set_status(self, owner: str, payload: object, *, now: datetime | None = None) -> dict:
        with self.repository.owner_guard(owner):
            return self._set_status(owner, payload, now=now)

    def _set_status(self, owner: str, payload: object, *, now: datetime | None = None) -> dict:
        if not isinstance(payload, dict):
            raise GuideValidationError("Invalid guide status.")
        if set(payload) & {"owner_user_key", "user_key", "owner_profile_id"}:
            raise GuideValidationError("Owner fields cannot be client-supplied.")
        status = payload.get("status")
        if status not in MEMBER_SETTABLE_STATUSES:
            raise GuideValidationError("Invalid guide status.")
        supplied_request_id = payload.get("request_id")
        if supplied_request_id is None:
            request_id = str(uuid4())
        else:
            try:
                request_id = str(UUID(str(supplied_request_id)))
            except (TypeError, ValueError, AttributeError) as error:
                raise GuideValidationError("Invalid guide request id.") from error
            if request_id != supplied_request_id:
                raise GuideValidationError("Invalid guide request id.")
        digest_document = {"type": "set_guide_status", "status": status, "status_source": "member"}
        request_digest = hashlib.sha256(
            json.dumps(
                digest_document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        snapshot = self._load(owner)
        existing = snapshot.get("receipts", {}).get(request_id)
        if existing is not None:
            if existing.get("request_digest") != request_digest:
                raise GuideConflictError("That guide request key was already used for another status.")
            return self._status_response(
                owner, existing.get("result"), replayed=True,
                question=payload.get("question"),
            )
        guide = snapshot.setdefault("guide", {})
        guide["status"] = status
        guide["status_source"] = "member"
        guide["updated_at"] = _utc(now).isoformat()
        receipt = {
            "success": True,
            "type": "set_guide_status",
            "request_id": request_id,
            "request_digest": request_digest,
            "status": status,
            "status_source": "member",
            "persisted": True,
        }
        snapshot.setdefault("receipts", {})[request_id] = {
            "request_digest": request_digest,
            "submission_key": None,
            "result": receipt,
        }
        try:
            # The guide is its own closed owner-scoped command, so the SQL
            # adapter reaches usp_SetResumeGuideStatusForOwner instead of
            # refusing a command-less snapshot replace.
            commit_result = self.repository.save_owner(
                owner,
                snapshot,
                {
                    "procedure": COMMAND_PROCEDURES["set_guide_status"],
                    "request_id": request_id,
                    "payload": {
                        "type": "set_guide_status",
                        "request_id": request_id,
                        "request_digest": request_digest,
                        "status": status,
                        "status_source": "member",
                        "receipt": receipt,
                    },
                },
            )
        except ResumeIntakeStoreUnavailable as error:
            raise GuideUnavailableError("The guide is unavailable.") from error
        if commit_result and commit_result.get("replayed"):
            returned = commit_result.get("result")
            current_snapshot = self._load(owner)
            winner = current_snapshot.get("receipts", {}).get(request_id)
            if (
                commit_result.get("request_digest") != request_digest
                or not isinstance(returned, dict)
                or not isinstance(winner, dict)
                or winner.get("request_digest") != request_digest
                or winner.get("result") != returned
            ):
                raise GuideUnavailableError("The guide is unavailable.")
            return self._status_response(
                owner, winner["result"], replayed=True,
                question=payload.get("question"),
            )
        return self._status_response(
            owner, receipt, replayed=False, question=payload.get("question")
        )

    @staticmethod
    def _question(question: dict | None) -> dict:
        if isinstance(question, dict) and question.get("prompt"):
            return {
                "prompt": str(question["prompt"])[:300],
                "context": (str(question.get("context"))[:300] or None) if question.get("context") else None,
                "optional": True,
            }
        return {
            "prompt": "What would you like to add?",
            "context": None,
            "optional": True,
        }


resume_guide_service = ResumeGuideService()
