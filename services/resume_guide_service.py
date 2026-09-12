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
