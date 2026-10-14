"""Complete Resume publication consistency boundary.

In-memory execution is one snapshot replace. The SQL path invokes one closed
command procedure and never holds a transaction across network/storage calls.
Review does not write. Restore stays private.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import replace
from contextlib import ExitStack, contextmanager, nullcontext
from uuid import uuid4

from services.mvp1_profile_binding import identity_reference
from services.resume_intake_repository import owner_composed, resume_owner_guard

from services.resume_media_catalog_repository import (
    CatalogFenceDenied,
    InMemoryResumeCatalogRepository,
    SqlResumeCatalogRepository,
)
from services.resume_publication_adapters import (
    OwnerMediaPort,
    DraftMediaPublicationPort,
    OwnerPolicyPort,
    SnapshotMediaPort,
    SnapshotPolicyPort,
    build_owner_review_candidate,
)
from services.resume_publication_contracts import (
    CandidateInput,
    ContractError,
    PublicationEvidenceVersion,
    ValidationResult,
    ReadState,
    TrustedUseContext,
    UseAudience,
    UsePurpose,
    _context_from_authorized_server,
)
from services.resume_publication_projection import publication_evidence_version, ordered_resume_display, resume_section_for
from services.resume_publication_repository import (
    InMemoryResumePublicationRepository,
    PublicationConflictError,
    PublicationDenied,
    PublicationStoreUnavailable,
    SqlResumePublicationRepository,
    empty_publication_snapshot,
)
from services.resume_publication_validation import validate_candidate


COMMAND_TYPES = frozenset(
    {
        "publish",
        "correct",
        "change_permissions",
        "delete",
        "restore",
        "sharing_off",
        "catalog_withdraw",
        "media_restrict",
    }
)


class PublicationValidationError(ValueError):
    pass


class PublicationUnavailableError(RuntimeError):
    pass


def _digest(payload: dict) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _wording_map(wording) -> dict[str, str | None]:
    if isinstance(wording, dict):
        return dict(wording)
    return {item.field: item.value for item in wording}


def memory_resume_publication_service(**kwargs):
    """Explicit in-memory stores for tests. Production construction never calls this."""

    kwargs.setdefault("repository", InMemoryResumePublicationRepository())
    kwargs.setdefault("catalog", InMemoryResumeCatalogRepository())
    kwargs.setdefault("sql_repository", None)
    return ResumePublicationService(**kwargs)


class _ReadOnlyPolicyReview:
    """Keep every validation reread on the same explicit read-only authority."""

    def __init__(self, policy_service):
        self.policy_service = policy_service

    def _read(self, owner, method):
        reader = getattr(self.policy_service, method, None)
        if not callable(reader):
            raise PublicationUnavailableError("Read-only publication review authority is unavailable.")
        try:
            listed = reader(owner)
            if type(listed) is not dict or type(listed.get("entries")) is not list:
                raise PublicationUnavailableError("Publication review authority is unavailable.")
            return listed
        except Exception as error:
            raise PublicationUnavailableError("Publication review authority is unavailable.") from error

    def list_entries(self, owner):
        return self._read(owner, "read_entries")

    def list_publication_entries(self, owner):
        return self._read(owner, "read_publication_entries")


class ResumePublicationService:
    def __init__(
        self,
        repository=None,
        catalog=None,
        sql_repository=None,
        policy_port=None,
        media_port=None,
        reserved_public_slugs=(),
        profile_binding=None,
        draft_service=None,
        media_application=None,
    ) -> None:
        if repository is None and sql_repository is None:
            sql_repository = SqlResumePublicationRepository()
            repository = sql_repository
            if catalog is None:
                catalog = SqlResumeCatalogRepository()
        elif repository is None:
            repository = sql_repository
            if catalog is None:
                catalog = SqlResumeCatalogRepository()
        elif catalog is None:
            if isinstance(repository, InMemoryResumePublicationRepository) and sql_repository is None:
                catalog = InMemoryResumeCatalogRepository()
            else:
                catalog = SqlResumeCatalogRepository()
        if sql_repository is None and isinstance(repository, SqlResumePublicationRepository):
            sql_repository = repository
        self.repository = repository
        self.catalog = catalog
        self.sql_repository = sql_repository
        self.policy_port = policy_port
        self.media_port = media_port
        self.reserved_public_slugs = frozenset(reserved_public_slugs)
        self.profile_binding = profile_binding
        self.draft_service = draft_service
        self.media_application = media_application
        self.policy_service = None
        self.media_bytes_port = None
        self._lock = threading.RLock()
        self._pending_reviews = {}

    def _load(self, owner: str) -> dict:
        try:
            return self.repository.load_owner(owner)
        except PublicationStoreUnavailable as error:
            raise PublicationUnavailableError("Publication is unavailable.") from error

    def _save(self, owner: str, snapshot: dict) -> None:
        try:
            self.repository.save_owner(owner, snapshot)
        except PublicationStoreUnavailable as error:
            raise PublicationUnavailableError("Publication is unavailable.") from error

    def read_display_selection_provenance(self, owner, entry_keys):
        """Qualified memory-only choice history; permission flags remain authority.

        Missing historical metadata is unknown. Reading never initializes it.
        SQL has no provenance contract and must not be probed or guessed.
        """
        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        if (type(self.repository) is not InMemoryResumePublicationRepository or
                type(getattr(self.policy_service, "repository", None)) is not InMemoryEntryPolicyRepository):
            return None
        with resume_owner_guard(owner):
            choices = self._load(owner).get("guide_display_choices")
            return {key: choices.get(key, "unknown") if type(choices) is dict and
                type(choices.get(key)) is str and choices.get(key) in {"never_selected", "explicitly_chosen"}
                else "unknown" for key in entry_keys}

    @owner_composed
    def has_current(self, owner: str) -> bool:
        snapshot = self._load(owner)
        return snapshot.get("current_revision") is not None

    def review(self, candidate: CandidateInput):
        policy_port = self.policy_port
        media_port = self.media_port
        if policy_port is None or media_port is None:
            raise PublicationUnavailableError("Publication review authority is unavailable.")
        return validate_candidate(candidate, policy_port, media_port)

    @staticmethod
    def publish_candidate(reviewed) -> dict:
        """Serializable review input, echoed unchanged; never a grant of authority.

        A fresh publish rebuilds this from current owner authorities. Receipts
        classify retries before rebuilding, so changed state cannot change the
        command bytes for a successful request whose response was lost.
        """
        candidate = reviewed.candidate
        versions = candidate.prior
        bases = {base.entry.entry_key: base.canonical_token for base in candidate.draft_bases}
        from services.resume_publication_validation import _placement
        return {
            "schema_version": 1,
            "story_entry_key": candidate.story_entry_key,
            "reviewed_digest": reviewed.digest,
            "resume_key": versions.resume_key,
            "draft_revision": versions.draft_revision,
            "publication_revision": versions.publication_revision,
            "sharing_epoch": versions.sharing_epoch,
            "profile_identity": candidate.profile_identity.to_payload() if candidate.profile_identity else None,
            "entries": [{
                "entry_key": item.entry.entry_key,
                "content_revision": item.entry.content_revision,
                "access_revision": item.entry.access_revision,
                "canonical_token": bases.get(item.entry.entry_key),
                "resume_display": item.display,
                "visitor_ai": item.visitor_ai,
                "deltas": [{"field": delta.field, "before": delta.before, "after": delta.after}
                           for delta in item.deltas],
            } for item in candidate.selections],
            "placements": [_placement(item) for item in candidate.placements],
        }

    def _review_publish(self, owner, payload, reviewed=None):
        envelope = payload.get("candidate")
        if envelope is not None:
            if type(envelope) is not dict or type(envelope.get("entries")) is not list:
                raise PublicationValidationError("A complete reviewed candidate is required.")
            review_payload = {
                "entries": envelope["entries"],
                "resume_key": envelope.get("resume_key"),
                "draft_revision": envelope.get("draft_revision"),
                "profile_identity": envelope.get("profile_identity"),
            }
        elif self.draft_service is not None:
            raise PublicationValidationError("Review and submit the complete Resume candidate.")
        else:
            # Compatibility for pre-integration callers. Integrated publishing
            # never depends on process-local review memory.
            review_payload = dict((self._pending_reviews.get(owner) or {}).get("payload") or {})
            review_payload.update(payload)
        result = self.review_for_owner(owner, review_payload,
            candidate=reviewed.candidate if reviewed is not None else None)
        if result.reviewed is None:
            raise PublicationDenied(result.reason, "The reviewed candidate is no longer current.")
        current = result.reviewed
        if payload.get("reviewed_digest") != current.digest:
            raise PublicationConflictError("stale_publish", "The reviewed candidate is no longer current.")
        if envelope is not None and _digest(envelope) != _digest(self.publish_candidate(current)):
            raise PublicationConflictError("stale_publish", "The reviewed candidate changed. Review it again.")
        if envelope is not None and payload.get("profile_identity") != envelope.get("profile_identity"):
            raise PublicationValidationError("Profile identity must match the reviewed candidate.")
        return current

    @staticmethod
    def review_details(reviewed):
        choices = {choice.entry: choice for choice in reviewed.candidate.selections}
        rows = []
        for item in reviewed.owner_entries:
            choice = choices[item.ref]
            after = _wording_map(item.wording)
            before = dict(after)
            for delta in choice.deltas:
                before[delta.field] = delta.before
            rows.append({"entry_key": item.ref.entry_key,
                "title": after.get("role_title") or after.get("title") or after.get("name")
                    or after.get("skill_name") or after.get("credential_name") or "Saved information",
                "before": before, "after": after, "resume_display": choice.display,
                "visitor_ai": choice.visitor_ai,
                "changes": [{"field": delta.field, "before": delta.before, "after": delta.after}
                            for delta in choice.deltas]})
        return rows

    @owner_composed
    def draft_preview(self, owner, payload=None):
        if payload is not None:
            if type(payload) is not dict or type(payload.get("candidate")) is not dict:
                raise PublicationValidationError("Review and submit the complete Resume candidate.")
            # This existing seam only rebuilds/validates; it never commits.
            reviewed = self._review_publish(owner, payload)
        else:
            result = self.review_for_owner(owner)
            if result.reviewed is None:
                raise PublicationConflictError("stale_preview", "The private preview changed. Review again.")
            reviewed = result.reviewed
        from services.resume_publication_validation import _placement
        sharing = self._load(owner)
        list_for_review = getattr(self.policy_service, "list_publication_entries", self.policy_service.list_entries)
        types = {row["entry_key"]: row["canonical_type"] for row in list_for_review(owner)["entries"]}
        display = {}
        for item in reviewed.display.entries:
            if item.ref.entry_key not in types:
                raise PublicationConflictError("stale_preview", "The private preview changed. Review again.")
            display[item.ref.entry_key] = {
                "canonical_type": types[item.ref.entry_key],
                "presentation_section": "story" if item.ref.entry_key == reviewed.candidate.story_entry_key else "entry",
                "wording": _wording_map(item.wording)}
        media = {item.slot: _placement(item) for item in reviewed.display.placements}
        media = self._visible_media(display, media) if self.media_application is not None else {}
        for placement in media.values():
            placement["preview_digest"] = _digest(placement)
        presented = {"published": False, "preview_only": True, "read_state": "current",
            "sharing_enabled": bool(sharing["sharing_enabled"]),
            "publication_revision": sharing["publication_revision"],
            "digest": reviewed.digest,
            "display": ordered_resume_display(display),
            "media": media,
            "public_identity": self._public_identity(owner,
                reviewed.candidate.profile_identity.to_payload() if reviewed.candidate.profile_identity else None)}
        # Recheck the pinned candidate after constructing presentation metadata.
        # Authority never comes from process-local pending-review memory.
        if payload is not None:
            self._review_publish(owner, payload)
        return presented

    def open_private_preview_media(self, owner: str, slot: str, expected: str):
        """Owner draft bytes pinned to the reviewed placement, never latest fallback."""
        if slot not in {"story_banner", "experience_support"} or not isinstance(expected, str) or len(expected) != 64:
            raise PublicationDenied("denied", "Private preview media is unavailable.")
        if self.media_application is None or self.draft_service is None:
            raise PublicationUnavailableError("Private preview media is unavailable.")
        from services.resume_publication_validation import _placement
        try:
            workspace = self.draft_service.get_workspace(owner)
            if workspace.get("capabilities", {}).get("canonical_read") != "ok":
                raise PublicationUnavailableError("Private preview media is unavailable.")
            draft_version = workspace["draft_version"]
        except Exception as error:
            raise PublicationUnavailableError("Private preview media is unavailable.") from error
        port = DraftMediaPublicationPort(self.media_application)
        def check():
            try:
                placements, _ = port.read_draft(owner, draft_version)
                selected = next((item for item in placements if item.slot == slot), None)
                if selected is None or _digest(_placement(selected)) != expected:
                    raise PublicationDenied("stale_preview", "Private preview media changed.")
            except PublicationDenied:
                raise
            except Exception as error:
                raise PublicationDenied("stale_preview", "Private preview media changed.") from error
        check()
        opened = self.media_application.open_draft_placement_media(owner_id=owner, slot=slot)
        try:
            check()
        except Exception:
            if isinstance(opened, dict) and opened.get("stream"):
                opened["stream"].close()
            raise
        return opened

    @owner_composed
    def read_review_for_owner(self, owner: str, payload: dict | None = None, *, candidate=None):
        """Read/validate the shared candidate without creating a pending review."""

        if getattr(self, "require_media_application", False) and self.media_application is None:
            raise PublicationUnavailableError("Resume media is unavailable. Your saved draft is unchanged.")
        payload = payload if isinstance(payload, dict) else {}
        snapshot = self._load(owner)
        selected_identity = None
        if self.profile_binding is not None:
            try:
                selected_identity = (
                    identity_reference(payload["profile_identity"])
                    if "profile_identity" in payload
                    else self.profile_binding.select_for_owner(owner)
                )
            except ContractError as error:
                raise PublicationValidationError("Invalid Profile identity selection.") from error
            except Exception as error:
                raise PublicationUnavailableError("Profile identity is unavailable.") from error
            if selected_identity is not None and self.profile_binding.recheck(owner, selected_identity) is not ReadState.CURRENT:
                raise PublicationConflictError("stale_identity", "Profile identity changed. Review it again.")
        elif payload.get("profile_identity") is not None:
            raise PublicationUnavailableError("Profile identity is unavailable.")
        if candidate is None:
            if self.policy_service is None:
                raise PublicationUnavailableError("Publication review authority is unavailable.")
            read_policy = _ReadOnlyPolicyReview(self.policy_service)
            listed = read_policy.list_publication_entries(owner)
            entries = [
                item
                for item in listed.get("entries") or []
                if item.get("lifecycle") == "active"
                and item.get("access_revision") is not None
                and item.get("content_version") is not None
            ]
            workspace = None
            if self.draft_service is not None:
                try:
                    workspace = self.draft_service.get_workspace(owner)
                except Exception as error:
                    raise PublicationUnavailableError("Resume draft is unavailable.") from error
                if workspace.get("capabilities", {}).get("canonical_read") != "ok":
                    raise PublicationUnavailableError("Resume draft is unavailable.")
                if any(item.get("has_draft") and (item.get("draft_is_stale") or item.get("orphaned"))
                       for item in workspace.get("items", ())):
                    raise PublicationConflictError("stale_draft", "Saved information changed. Review your Resume edits again.")
            draft_items = workspace.get("items", ()) if workspace else ()
            if self.draft_service is not None and self.media_application is None:
                try:
                    stored_draft = self.draft_service.repository.load_owner(owner)
                    if (stored_draft.get("media") or {}).get("placements"):
                        raise PublicationUnavailableError("Resume media is unavailable. Your saved draft is unchanged.")
                except PublicationUnavailableError:
                    raise
                except Exception as error:
                    raise PublicationUnavailableError("Resume draft is unavailable.") from error
            placements, media_states = (), ()
            durable_media_port = None
            if self.media_application is not None:
                if workspace is None:
                    raise PublicationUnavailableError("Resume draft is unavailable.")
                durable_media_port = DraftMediaPublicationPort(self.media_application)
                try:
                    placements, media_states = durable_media_port.read_draft(owner, workspace["draft_version"])
                except Exception as error:
                    raise PublicationUnavailableError("Resume media is unavailable.") from error
            codec_blockers = self._publication_format_blockers(entries, workspace, payload)
            if codec_blockers:
                return ValidationResult(ReadState.UNAVAILABLE, "publication_codec_unavailable",
                    blocked_items=tuple((item["item_ref"], item["reason"]) for item in codec_blockers))
            candidate, policy, media = build_owner_review_candidate(
                owner=owner,
                resume_key=str(payload.get("resume_key") or f"resume:{owner}"),
                draft_revision=int(workspace["draft_version"] if workspace else payload.get("draft_revision") or 0),
                publication_revision=int(snapshot.get("publication_revision") or 0),
                sharing_epoch=int(snapshot.get("sharing_epoch") or 0),
                sharing_enabled=bool(snapshot.get("sharing_enabled")),
                entries=entries,
                payload=payload,
                profile_identity=selected_identity,
                draft_items=draft_items,
                story_entry_key=workspace.get("story_entry_key") if workspace else None,
                placements=placements,
                media_versions=tuple(item.ref for item in media_states),
                media_states=media_states,
            )
            policy_port = OwnerPolicyPort(
                read_policy,
                resume_key=candidate.prior.resume_key,
                draft_revision=candidate.prior.draft_revision,
                publication_revision=candidate.prior.publication_revision,
                sharing_epoch=candidate.prior.sharing_epoch,
                sharing_enabled=policy.sharing_enabled,
                sources=policy.sources,
                wording_fields={item["record_key"]: tuple((item.get("proposed_values") or {}).keys())
                                for item in draft_items if item.get("has_draft")},
                draft_service=self.draft_service,
                draft_bases=candidate.draft_bases,
                media_versions=candidate.prior.media,
            )
            if durable_media_port is not None:
                durable_media_port.versions = candidate.prior
            media_port = durable_media_port or OwnerMediaPort(media)
        else:
            if candidate.profile_identity is not None and (
                self.profile_binding is None
                or self.profile_binding.recheck(owner, candidate.profile_identity) is not ReadState.CURRENT
            ):
                raise PublicationConflictError("stale_identity", "Profile identity changed. Review it again.")
            policy_port = self.policy_port
            media_port = self.media_port
            if policy_port is None or media_port is None:
                raise PublicationUnavailableError("Publication review authority is unavailable.")
        return validate_candidate(candidate, policy_port, media_port)

    @owner_composed
    def review_for_owner(self, owner: str, payload: dict | None = None, *, candidate=None):
        """Explicit review keeps its pending-review behavior; content stays private."""
        payload = payload if isinstance(payload, dict) else {}
        result = self.read_review_for_owner(owner, payload, candidate=candidate)
        if result.reviewed is not None:
            self._pending_reviews[owner] = {
                "digest": result.reviewed.digest,
                "payload": {
                    key: value
                    for key, value in payload.items()
                    if key in {"entries", "selections", "resume_key", "draft_revision", "profile_identity"}
                },
            }
            if self.profile_binding is not None:
                ref = result.reviewed.candidate.profile_identity
                self._pending_reviews[owner]["payload"]["profile_identity"] = ref.to_payload() if ref else None
        return result

    @staticmethod
    def _unavailable_basis(*, blocked=(), ineligible=()):
        return {"read_state": "blocked" if blocked else "unavailable", "publication_state": "unknown",
            "basis_revision": None, "publication_revision": None, "sharing_enabled": None,
            "change_count": None, "membership": None, "items": None, "proposed": None,
            "story": None, "contact": None, "profile": None, "candidate": None, "reviewed_digest": None,
            "blocked_items": list(blocked), "ineligible_items": list(ineligible)}

    def _basis_authorities(self, owner):
        if self.policy_service is None or self.draft_service is None:
            raise PublicationUnavailableError("Complete publication review authority is unavailable.")
        rows = _ReadOnlyPolicyReview(self.policy_service).list_publication_entries(owner)["entries"]
        keys = set()
        for row in rows:
            if (type(row) is not dict or type(row.get("entry_key")) is not str or not row["entry_key"]
                    or row["entry_key"] in keys or row.get("lifecycle") not in {"active", "deleted"}
                    or type(row.get("canonical_type")) is not str
                    or type(row.get("content_version")) is not int or row["content_version"] < 1
                    or type(row.get("access_revision")) is not int or row["access_revision"] < 1):
                raise PublicationUnavailableError("Publication review authority is unavailable.")
            keys.add(row["entry_key"])
        workspace = self.draft_service.get_workspace(owner)
        if (type(workspace) is not dict or workspace.get("capabilities", {}).get("canonical_read") != "ok"
                or type(workspace.get("items")) is not list or type(workspace.get("draft_version")) is not int):
            raise PublicationUnavailableError("Resume draft is unavailable.")
        snapshot = self._load(owner)
        if (type(snapshot.get("sharing_enabled")) is not bool
                or any(type(snapshot.get(name)) is not int or snapshot[name] < 0
                       for name in ("publication_revision", "sharing_epoch"))):
            raise PublicationUnavailableError("Publication is unavailable.")
        current = self._current(snapshot)
        if snapshot.get("current_revision") is not None and current is None:
            raise PublicationUnavailableError("Publication is unavailable.")
        if snapshot["sharing_enabled"] and current is None:
            raise PublicationUnavailableError("Publication is unavailable.")
        if current is not None and (type(current) is not dict
                or any(type(current.get(name)) is not dict for name in ("display", "visitor_ai", "evidence", "media"))):
            raise PublicationUnavailableError("Publication is unavailable.")
        return rows, workspace, snapshot, current

    @staticmethod
    def _publication_format_blockers(rows, workspace, payload=None, *, selected_only=True):
        """Fail closed for ruled local fields that codec v1 cannot preserve.

        List-valued project data also exceeds v1's complete-candidate scalar
        contract, so it blocks that complete review even while unselected.
        Nothing is removed or coerced into a different qualification type.
        """
        payload = payload or {}
        choices = payload.get("entries") or payload.get("selections") or []
        if type(choices) is not list or any(type(item) is not dict for item in choices):
            raise PublicationValidationError("Invalid entry selections.")
        selected = {item.get("entry_key"): item for item in choices}
        items = {item["record_key"]: item for item in (workspace or {}).get("items", [])}
        blocked = []
        if "highlight_refs" in (workspace or {}):
            blocked.append({"item_ref":"resume","reason":"publication_codec_highlight_references"})
        blocked.extend({"item_ref":item["record_key"],"reason":"publication_codec_skill_references"}
            for item in (workspace or {}).get("items",[]) if "evidence_refs" in item)
        for row in rows:
            if row.get("lifecycle") != "active":
                continue
            key = row["entry_key"]
            item = items.get(key) or {}
            values = {**(row.get("values") or {}), **(item.get("values") or {}), **(item.get("proposed_values") or {})}
            choice = selected.get(key) or {}
            publishing = bool(choice.get("resume_display", choice.get("display", row.get("resume_display")))
                              or choice.get("visitor_ai", row.get("visitor_ai")))
            reasons = []
            if row["canonical_type"] == "knowledge":
                from services.living_resume_editor_service import validate_guide_text_limits, GuideTextLimitError
                try:
                    validate_guide_text_limits(values)
                except GuideTextLimitError as error:
                    reasons.append(error.code)
            if row["canonical_type"] == "credential":
                if values.get("qualification_kind") in {"publication", "membership"}:
                    reasons.append("publication_codec_qualification_kind")
                if values.get("verification_url"):
                    reasons.append("publication_codec_verification_url")
            elif row["canonical_type"] == "project":
                structured_links = isinstance(values.get("additional_project_urls"), list)
                if values.get("project_url") or structured_links:
                    reasons.append("publication_codec_project_links")
                for field, reason in (("project_category", "category"), ("organization_name", "organization"),
                                      ("project_role", "role"), ("project_status", "status"), ("location_text", "location")):
                    if values.get(field):
                        reasons.append("publication_codec_project_" + reason)
                if (values.get("start_date") or values.get("end_date")) and values.get("date_precision") not in {None, "day"}:
                    reasons.append("publication_codec_project_date_precision")
                if structured_links:
                    publishing = True  # v1 cannot construct a scalar Wording from this field.
            if publishing or not selected_only:
                blocked.extend({"item_ref": key, "reason": reason} for reason in reasons)
        return blocked

    @staticmethod
    def _basis_diagnostics(rows, workspace, payload=None):
        blocked, ineligible = [], []
        for item in workspace["items"]:
            if item.get("orphaned") is True:
                blocked.append({"item_ref": item["record_key"], "reason": "orphaned"})
            elif item.get("draft_is_stale") is True:
                blocked.append({"item_ref": item["record_key"], "reason": "stale_draft"})
            if item.get("publication_eligible") is False:
                ineligible.append({"item_ref": item["record_key"], "reason": "publication_ineligible"})
        ineligible.extend({"item_ref": row["entry_key"], "reason": "deleted"}
                          for row in rows if row["lifecycle"] != "active")
        blocked.extend(ResumePublicationService._publication_format_blockers(rows, workspace, payload))
        ineligible.extend(ResumePublicationService._publication_format_blockers(rows, workspace, payload, selected_only=False))
        return blocked, ineligible

    @owner_composed
    def read_publication_basis_for_owner(self, owner, payload=None):
        """Describe the existing validated publish candidate; never review-cache or save.

        Extra authority reads recheck the same candidate's versions. They do not
        build another candidate, predict opaque tokens or create committed evidence.
        """
        try:
            result = self.read_review_for_owner(owner, payload)
        except Exception:
            try:
                rows, workspace, _, _ = self._basis_authorities(owner)
                blocked, ineligible = self._basis_diagnostics(rows, workspace, payload)
                return self._unavailable_basis(blocked=blocked, ineligible=ineligible)
            except Exception:
                return self._unavailable_basis()
        try:
            rows, workspace, snapshot, current = self._basis_authorities(owner)
            blocked, ineligible = self._basis_diagnostics(rows, workspace, payload)
            if result.state is not ReadState.CURRENT or result.reviewed is None or blocked:
                return self._unavailable_basis(blocked=blocked, ineligible=ineligible)
            reviewed = result.reviewed
            versions = reviewed.versions
            if (versions.subject_key != owner or versions.draft_revision != workspace["draft_version"]
                    or versions.publication_revision != snapshot["publication_revision"]
                    or versions.sharing_epoch != snapshot["sharing_epoch"]):
                return self._unavailable_basis()
            active = {row["entry_key"]: row for row in rows if row["lifecycle"] == "active"}
            choices = {choice.entry.entry_key: choice for choice in reviewed.candidate.selections}
            if set(active) != set(choices) or any(
                    choice.entry.subject_key != owner or choice.entry.content_revision != str(active[key]["content_version"])
                    or choice.entry.access_revision != active[key]["access_revision"]
                    for key, choice in choices.items()):
                return self._unavailable_basis()
            from services.resume_publication_projection import TYPE_FIELD_MAP
            unsupported = [{"item_ref": key, "reason": "unsupported_canonical_type"} for key, row in active.items()
                           if row["canonical_type"] not in TYPE_FIELD_MAP]
            if any(choices[item["item_ref"]].display or choices[item["item_ref"]].visitor_ai for item in unsupported):
                return self._unavailable_basis(blocked=unsupported, ineligible=[*ineligible, *unsupported])
            ineligible.extend(unsupported)
            display = {item.ref.entry_key: {"canonical_type": active[item.ref.entry_key]["canonical_type"],
                "presentation_section": "story" if item.ref.entry_key == reviewed.candidate.story_entry_key else "entry",
                "wording": _wording_map(item.wording)} for item in reviewed.display.entries}
            visitor_ai = {item.ref.entry_key: {"canonical_type": active[item.ref.entry_key]["canonical_type"],
                "wording": _wording_map(item.wording)} for item in reviewed.visitor_ai.entries}
            media = self._basis_media(self._visible_media(display, self._reviewed_media(reviewed)))
            visible = bool(snapshot["sharing_enabled"] and current is not None)
            before_display = current["display"] if visible else {}
            before_ai = current["visitor_ai"] if visible else {}
            before_media = self._basis_media(self._visible_media(before_display, current["media"])) if visible else {}
            items = []
            for key in sorted(set(active) | set(before_display) | set(before_ai)):
                published_display, published_ai = key in before_display, key in before_ai
                selected_display, selected_ai = key in display, key in visitor_ai
                changed = (published_display, published_ai) != (selected_display, selected_ai)
                for before, after, fields in ((before_display, display, ("canonical_type", "presentation_section", "wording")),
                                               (before_ai, visitor_ai, ("canonical_type", "wording"))):
                    if key in before and key in after:
                        for field in fields:
                            left, right = before[key].get(field), after[key].get(field)
                            if field == "wording":
                                if type(left) is not dict or type(right) is not dict:
                                    return self._unavailable_basis()
                                # Old published snapshots can retain explicit optional
                                # nulls after the consumed draft's field list disappears.
                                # Missing/null has the same visible value, not a new edit.
                                changed = changed or any(left.get(name) != right.get(name) for name in set(left) | set(right))
                            else:
                                changed = changed or left != right
                if published_display or published_ai:
                    evidence = current["evidence"].get(key)
                    if (not isinstance(evidence, PublicationEvidenceVersion)
                            or evidence.owner_key != owner or evidence.entry_key != key):
                        return self._unavailable_basis()
                    if (selected_display or selected_ai) and key in choices:
                        ref = choices[key].entry
                        changed = changed or str(evidence.policy_content_version) != ref.content_revision or evidence.access_revision != ref.access_revision
                items.append({"item_ref": key, "canonical_type": (active.get(key) or before_display.get(key) or before_ai.get(key))["canonical_type"],
                    "published_display": published_display, "published_visitor_ai": published_ai,
                    "proposed_display": selected_display, "proposed_visitor_ai": selected_ai, "changed": bool(changed)})
            before_story = [key for key, row in before_display.items() if row.get("presentation_section") == "story"]
            after_story = [key for key, row in display.items() if row.get("presentation_section") == "story"]
            if len(before_story) > 1 or len(after_story) > 1:
                return self._unavailable_basis()
            def contact_keys(entries):
                return sorted(key for key, row in entries.items() if resume_section_for(row.get("canonical_type"),
                    row.get("wording") or {}, presentation_section=row.get("presentation_section"),
                    story_bound=row.get("presentation_section") == "story") == "contact")
            before_contact, after_contact = contact_keys(before_display), contact_keys(display)
            contact_changed = before_contact != after_contact or any(row["changed"] and
                row["item_ref"] in set(before_contact) | set(after_contact) for row in items)
            profile = reviewed.candidate.profile_identity.to_payload() if reviewed.candidate.profile_identity else None
            before_profile = current.get("profile_identity") if visible else None
            profile_changed = before_profile != profile
            media_changes = sorted(slot for slot in set(before_media) | set(media) if before_media.get(slot) != media.get(slot))
            count = sum(row["changed"] for row in items) + int(profile_changed) + len(media_changes)
            return {"read_state": "current", "publication_state": "unpublished" if not visible else "changes_waiting" if count else "published",
                "basis_revision": _digest({"reviewed_digest": reviewed.digest, "publication_revision": snapshot["publication_revision"],
                                           "sharing_epoch": snapshot["sharing_epoch"]}),
                "publication_revision": snapshot["publication_revision"], "sharing_enabled": snapshot["sharing_enabled"],
                "change_count": count, "membership": {"display": sorted(display), "visitor_ai": sorted(visitor_ai)}, "items": items,
                "proposed": {"display": ordered_resume_display(display), "visitor_ai": visitor_ai, "media": media},
                "story": {"private_entry_key": reviewed.candidate.story_entry_key,
                          "published_entry_key": before_story[0] if before_story else None,
                          "proposed_published_entry_key": after_story[0] if after_story else None,
                          "changed": before_story != after_story},
                "contact": {"published_entry_keys": before_contact, "proposed_entry_keys": after_contact,
                            "changed": contact_changed},
                "profile": {"published_reference": before_profile, "proposed_reference": profile, "changed": profile_changed},
                "media_changed_slots": media_changes, "candidate": self.publish_candidate(reviewed),
                "reviewed_digest": reviewed.digest, "blocked_items": [], "ineligible_items": ineligible}
        except Exception:
            return self._unavailable_basis()

    @staticmethod
    def _basis_media(media):
        result = copy.deepcopy(media)
        for item in result.values():
            version = item.get("asset_version")
            if (type(version) not in {int, str} or not str(version).isascii()
                    or not str(version).isdigit() or int(version) < 1):
                raise PublicationUnavailableError("Publication media version is unavailable.")
            # Preserve exact rowversions across JSON and JavaScript; SQL-shaped
            # decimal strings and snapshot integers mean the same version.
            item["asset_version"] = str(int(version))
            if item.get("catalog_revision") is not None:
                item["catalog_revision"] = str(item["catalog_revision"])
        return result

    @staticmethod
    def _reviewed_media(reviewed):
        versions = {item.slot: item for item in reviewed.versions.media}
        return {placement.slot: {"slot": placement.slot, "source_kind": placement.source_kind,
            "source_key": placement.asset_id, "asset_version": placement.asset_version,
            "content_sha256": placement.asset_digest,
            "catalog_revision": None if placement.source_kind != "generated_illustration" else str(placement.asset_version),
            "source_revision": versions[placement.slot].source_revision,
            "presentation_version": placement.presentation_version, "crop": placement.crop.as_dict(),
            "alt_text": placement.alt_text, "decorative": placement.decorative, "caption": placement.caption,
            "provenance_label": placement.provenance_label, "active": True} for placement in reviewed.display.placements}

    @owner_composed
    def owner_preview(self, owner: str) -> dict:
        snapshot = self._load(owner)
        current = self._current(snapshot)
        presented = None
        if current:
            presented = {
                "revision": current["revision"],
                "digest": current["digest"],
                "display": copy.deepcopy(current["display"]),
                "visitor_ai": copy.deepcopy(current["visitor_ai"]),
                "media": copy.deepcopy(current["media"]),
                "profile_identity": copy.deepcopy(current.get("profile_identity")),
                "evidence": {
                    key: {
                        "content_sha256": item.content_sha256,
                        "canonical_token": item.canonical_token,
                        "policy_content_version": item.policy_content_version,
                        "version": item.version,
                    }
                    for key, item in current["evidence"].items()
                },
            }
        return {
            "sharing_enabled": bool(snapshot["sharing_enabled"]),
            "publication_revision": snapshot["publication_revision"],
            "current": presented,
            "read_state": ReadState.CURRENT.value,
        }

    def guest_read(self, *, slug: str, if_none_match: str | None = None) -> dict:
        if slug in self.reserved_public_slugs:
            raise PublicationDenied("fixture_classified", "Example profile stays separately classified.")
        if self.sql_repository is not None:
            return self._guest_read_sql(slug=slug, if_none_match=if_none_match)
        owner = self._owner_for_slug(slug)
        if owner is None:
            raise PublicationDenied("denied", "Publication is unavailable.")
        snapshot = self._load(owner)
        if not snapshot.get("sharing_enabled"):
            raise PublicationDenied("denied", "Publication is unavailable.")
        current = self._current(snapshot)
        if current is None:
            raise PublicationDenied("denied", "Publication is unavailable.")
        etag = current["digest"]
        if self.profile_binding is None and self.media_application is None and if_none_match and if_none_match.strip('"') == etag:
            return {"read_state": "not_modified", "etag": etag, "cache_control": "private,no-store"}
        media = {
            key: copy.deepcopy(item)
            for key, item in (current.get("media") or {}).items()
            if item.get("active") and self._current_media_source(owner, item)
        }
        media = self._visible_media(current["display"], media)
        return {
            "read_state": ReadState.CURRENT.value,
            "etag": etag,
            "cache_control": "private,no-store",
            "sharing_enabled": True,
            "publication_revision": current["revision"],
            "display": copy.deepcopy(current["display"]),
            "media": media,
            "public_identity": self._public_identity(owner, current.get("profile_identity")),
        }

    def _public_identity(self, owner, raw_reference):
        if self.profile_binding is None or type(owner) is not str:
            return None
        try:
            selected = identity_reference(raw_reference)
            identity = self.profile_binding.resolve(owner, selected)
            if identity is None:
                return None
            return {"display_name": identity.display_name, "headline": identity.headline,
                    "location": identity.location}
        except Exception:
            return None

    def _guest_read_sql(self, *, slug: str, if_none_match: str | None = None) -> dict:
        try:
            row = self.sql_repository.get_public_by_slug(slug)
        except PublicationStoreUnavailable as error:
            raise PublicationUnavailableError("Publication is unavailable.") from error
        if not row:
            raise PublicationDenied("denied", "Publication is unavailable.")
        etag = str(row.get("reviewed_digest") or "")
        display = row.get("display_json", row.get("display")) or {}
        media = row.get("media_json", row.get("media")) or {}
        if isinstance(display, str):
            display = json.loads(display)
        if isinstance(media, str):
            media = json.loads(media)
        media = {
            key: copy.deepcopy(item)
            for key, item in (media or {}).items()
            if isinstance(item, dict) and item.get("active")
        }
        for slot in tuple(media):
            try:
                self.sql_repository.authorize_media(slug, slot, row.get("publication_revision"))
            except PublicationDenied:
                del media[slot]
            except PublicationStoreUnavailable as error:
                raise PublicationUnavailableError("Resume media is unavailable.") from error
        media = self._visible_media(display, media)
        return {
            "read_state": ReadState.CURRENT.value,
            "etag": etag,
            "cache_control": "private,no-store",
            "sharing_enabled": True,
            "publication_revision": row.get("publication_revision"),
            "display": copy.deepcopy(display or {}),
            "media": media,
            "public_identity": self._public_identity(
                row.get("owner_user_key"),
                SqlResumePublicationRepository._identity_reference(row.get("profile_identity_json")),
            ),
        }

    def authorize_media(self, *, slug: str, slot: str, publication_revision: int | None = None) -> dict:
        if self.sql_repository is not None:
            if slot == "story_banner" and slot not in self.guest_read(slug=slug)["media"]:
                raise PublicationDenied("denied", "Media is unavailable.")
            try:
                return self.sql_repository.authorize_media(slug, slot, publication_revision)
            except PublicationStoreUnavailable as error:
                raise PublicationUnavailableError("Publication is unavailable.") from error
        payload = self.guest_read(slug=slug)
        media = payload.get("media") or {}
        item = media.get(slot)
        if not item or not item.get("active"):
            raise PublicationDenied("denied", "Media is unavailable.")
        if publication_revision is not None and publication_revision != payload["publication_revision"]:
            raise PublicationDenied("stale", "Media is unavailable.")
        if item.get("source_kind") == "generated_illustration":
            catalog_revision = item.get("catalog_revision")
            try:
                record = self.catalog.get_active(item["source_key"], int(item["asset_version"]))
            except CatalogFenceDenied as error:
                raise PublicationDenied("denied", "Media is unavailable.") from error
            if catalog_revision and str(record.version) != str(catalog_revision) and record.digest != item.get("content_sha256"):
                raise PublicationDenied("denied", "Media is unavailable.")
            if record.lifecycle != "active":
                raise PublicationDenied("denied", "Media is unavailable.")
        return {"authorized": True, "slot": slot, "rechecked": True,
                "owner_user_key": self._owner_for_slug(slug),
                "publication_revision": payload["publication_revision"], **item}

    @staticmethod
    def _visible_media(display, media):
        # A saved Story image is presentation of an explicitly displayed My
        # Story entry. Its private draft can remain selected while Story is off.
        if not any(item.get("canonical_type") == "knowledge" and item.get("presentation_section") == "story"
                   for item in (display or {}).values()):
            media.pop("story_banner", None)
        return media

    def _current_media_source(self, owner, item):
        if self.media_application is None:
            return True  # Legacy test-only memory publications have no source port.
        try:
            sources = self.media_application.media_repository
            if item.get("source_kind") == "owner_photo":
                record = sources.get_owner_photo(owner_id=owner, source_id=item["source_key"])
                if record is None or record.state != "ready":
                    return False
                if record.version_token != item.get("source_revision"):
                    return False
            else:
                record = sources.get_catalog_asset(asset_id=item["source_key"], version=item["asset_version"])
            return (record is not None and record.lifecycle == "active"
                    and record.version == item["asset_version"] and record.digest == item["content_sha256"])
        except Exception:
            return False

    def deliver_guest_media(
        self,
        *,
        slug: str,
        slot: str,
        publication_revision: int | None = None,
        if_none_match: str | None = None,
        method: str = "GET",
    ) -> dict:
        """Authorize, then access storage, then re-authorize immediately before bytes."""

        first = self.authorize_media(
            slug=slug, slot=slot, publication_revision=publication_revision
        )
        etag = str(first.get("content_sha256") or "")
        if if_none_match and etag and if_none_match.strip('"') == etag:
            if self.authorize_media(slug=slug, slot=slot, publication_revision=publication_revision) != first:
                raise PublicationDenied("stale", "Media is unavailable.")
            return {
                "status": 304,
                "etag": etag,
                "cache_control": "private,no-store",
                "body": b"",
                "content_type": "application/octet-stream",
            }
        if self.media_bytes_port is None:
            raise PublicationUnavailableError("Resume media storage is unavailable.")
        blob = self.media_bytes_port.read(first)
        content_type = "application/octet-stream"
        if isinstance(blob, dict):
            content_type = blob.get("content_type") or content_type
            blob = blob.get("data")
        if type(blob) is not bytes or not blob:
            raise PublicationUnavailableError("Resume media storage is unavailable.")
        second = self.authorize_media(
            slug=slug, slot=slot, publication_revision=publication_revision
        )
        if second != first or not second.get("authorized"):
            raise PublicationDenied("denied", "Media is unavailable.")
        body = b"" if str(method).upper() == "HEAD" else blob
        return {
            "status": 200,
            "etag": etag,
            "cache_control": "private,no-store",
            "body": body,
            "content_type": content_type,
            "authorized": True,
            "rechecked": True,
        }

    def commit(self, owner: str, payload: dict, *, reviewed=None, policy_snapshot=None) -> dict:
        if not isinstance(payload, dict):
            raise PublicationValidationError("Invalid command.")
        forbidden = {"owner_user_key", "user_key", "owner_profile_id", "table", "bypass", "session_role"}
        if set(payload) & forbidden:
            raise PublicationValidationError("Owner or table fields cannot be client-supplied.")
        command_type = payload.get("type")
        if command_type not in COMMAND_TYPES:
            raise PublicationValidationError("Unknown command.")
        if command_type == "publish" and self.profile_binding is not None and "profile_identity" not in payload:
            raise PublicationValidationError("Review and submit the selected Profile identity.")
        request_id = str(payload.get("request_id") or "")
        if not request_id:
            raise PublicationValidationError("request id is required.")
        command = dict(payload)
        body = {key: value for key, value in command.items() if key != "request_id"}
        digest = _digest(body)
        if self.sql_repository is None:
            with resume_owner_guard(owner), self._memory_media_locks(), self._memory_draft_lock():
                before = self._load(owner)
                existing = before["receipts"].get(request_id)
                if existing is not None:
                    if existing["request_digest"] != digest:
                        raise PublicationConflictError("request_conflict", "That request already used a different payload.")
                    return {"receipt": dict(existing["receipt"]), "replayed": True, "read_state": ReadState.CURRENT.value}
                if command_type == "publish":
                    reviewed = self._review_publish(owner, payload, reviewed)
                snapshot = copy.deepcopy(before)
                presented = self._apply(snapshot, owner, command_type, payload, reviewed, policy_snapshot)
                receipt = {
                    "request_id": request_id,
                    "request_digest": digest,
                    "type": command_type,
                    "outcome": presented.get("outcome"),
                    "publication_revision": snapshot["publication_revision"],
                }
                snapshot["receipts"][request_id] = {"request_digest": digest, "receipt": receipt}
                if command_type == "publish" and self.draft_service is not None:
                    self._save_integrated_memory(owner, snapshot, reviewed, before)
                else:
                    self._save(owner, snapshot)
                return {"receipt": receipt, "replayed": False, "read_state": ReadState.CURRENT.value, **presented}
        existing = self._sql_receipt(owner, request_id)
        if existing is not None:
            try:
                return self.sql_repository.commit_command(owner, request_id, command)
            except PublicationConflictError:
                raise
            except PublicationStoreUnavailable as error:
                raise PublicationUnavailableError("Publication is unavailable.") from error
        if command_type == "publish":
            reviewed = self._review_publish(owner, payload, reviewed)
        try:
            return self.sql_repository.commit_command(owner, request_id, command)
        except PublicationConflictError:
            raise
        except PublicationStoreUnavailable as error:
            raise PublicationUnavailableError("Publication is unavailable.") from error

    def _sql_receipt(self, owner: str, request_id: str):
        getter = getattr(self.sql_repository, "get_receipt", None)
        if callable(getter):
            return getter(owner, request_id)
        snapshot = self._load(owner)
        return (snapshot.get("receipts") or {}).get(request_id)

    def _memory_draft_lock(self):
        if self.draft_service is None:
            return nullcontext()
        from services.resume_draft_repository import InMemoryResumeDraftRepository
        repository = self.draft_service.repository
        if type(repository) is not InMemoryResumeDraftRepository:
            raise PublicationUnavailableError("Atomic publication storage is unavailable.")
        return repository._lock

    def _memory_media_lock(self):
        if self.media_application is None:
            return nullcontext()
        guard = getattr(self.media_application.media_repository, "_source_guard", None)
        if not callable(getattr(guard, "__enter__", None)):
            raise PublicationUnavailableError("Atomic media storage is unavailable.")
        return guard

    @contextmanager
    def _memory_media_locks(self):
        """The in-memory store order: media lifecycle, then bound media, then draft.

        Publish and the Guide unit of work both read draft media while holding
        the draft store lock, and media reads/commands take the bound-media and
        lifecycle locks before the draft store. Taking both media locks first
        keeps one global order, so two owners can never wait on each other.
        """
        with ExitStack() as stack:
            stack.enter_context(self._memory_media_lock())
            if self.media_application is not None:
                bound = getattr(self.media_application.media_repository, "_lock", None)
                if bound is not None:
                    if not callable(getattr(bound, "__enter__", None)):
                        raise PublicationUnavailableError("Atomic media storage is unavailable.")
                    stack.enter_context(bound)
            yield

    def _save_integrated_memory(self, owner, snapshot, reviewed, before):
        """Process-local fixture transaction; SQL uses the single command proc."""
        from services.entry_policy_repository import InMemoryEntryPolicyRepository
        repository = getattr(self.policy_service, "repository", None)
        if type(repository) is not InMemoryEntryPolicyRepository:
            raise PublicationUnavailableError("Atomic canonical storage is unavailable.")
        policy_before = repository.load_owner(owner)
        policy_after = copy.deepcopy(policy_before)
        draft_before = self.draft_service.repository.load_owner(owner)
        draft_after = copy.deepcopy(draft_before)
        if draft_before["draft_version"] != reviewed.versions.draft_revision:
            raise PublicationConflictError("stale_draft", "The draft changed.")
        display_choices = snapshot.setdefault("guide_display_choices", {})
        if type(display_choices) is not dict:
            raise PublicationUnavailableError("Display choice history is unavailable. Your input is kept.")
        for choice in reviewed.candidate.selections:
            entry = policy_after["entries"].get(choice.entry.entry_key)
            if (entry is None or entry["lifecycle"] != "active"
                    or str(entry["content_version"]) != choice.entry.content_revision
                    or entry["access_revision"] != choice.entry.access_revision):
                raise PublicationConflictError("stale_publish", "Saved information changed.")
            for delta in choice.deltas:
                field = _canonical_field(entry["canonical_type"], delta.field)
                if entry["values"].get(field) != delta.before:
                    raise PublicationConflictError("stale_publish", "Saved information changed.")
                entry["values"][field] = delta.after
            if choice.deltas:
                entry["content_version"] += 1
            if (entry["resume_display"], entry["visitor_ai"]) != (choice.display, choice.visitor_ai):
                entry["resume_display"], entry["visitor_ai"] = choice.display, choice.visitor_ai
                entry["access_revision"] += 1
            # Publish explicitly confirms the complete reviewed list, including
            # false/false choices whose canonical flags need no revision bump.
            display_choices[choice.entry.entry_key] = "explicitly_chosen"
            draft_after["items"].pop(choice.entry.entry_key, None)
        draft_after["draft_version"] += 1
        draft_after["base_publication_version"] = snapshot["publication_revision"]
        # Save only once per store, restoring every snapshot on injected failure.
        # This is not multi-process/durable transaction evidence.
        try:
            repository.save_owner(owner, policy_after)
            self.draft_service.repository.save_owner(owner, draft_after)
            self._save(owner, snapshot)
        except Exception:
            repository.save_owner(owner, policy_before)
            self.draft_service.repository.save_owner(owner, draft_before)
            self._save(owner, before)
            raise

    def apply_policy_command(self, owner: str, command: dict, entries: dict) -> dict | None:
        """In-memory publication side effects for a My Data / entry-policy write.

        The caller owns the policy snapshot. This method mutates and saves only
        the publication store. Use commit_linked_write for the atomic pair.
        """

        snapshot = self._load(owner)
        if self._current(snapshot) is None:
            return None
        self._apply_policy_effects(snapshot, owner, command, entries)
        self._save(owner, snapshot)
        return {"outcome": "applied", "publication_revision": snapshot["publication_revision"]}

    def commit_linked_write(self, owner: str, policy_repository, policy_before: dict, policy_after: dict, command: dict) -> None:
        """Save linked policy/publication and any private-link deletion atomically."""

        from services.resume_draft_repository import InMemoryResumeDraftRepository
        draft_repository = getattr(self.draft_service,"repository",None)
        qualified_draft = type(draft_repository) is InMemoryResumeDraftRepository
        deleting_links = qualified_draft and command.get("type") in {"delete","permanently_delete"}
        with resume_owner_guard(owner), draft_repository._lock if deleting_links else nullcontext():
            if policy_repository.load_owner(owner) != policy_before:
                raise PublicationConflictError("stale_publish", "Saved information changed.")
            pub_before = self._load(owner)
            pub_after = copy.deepcopy(pub_before)
            self._apply_policy_effects(pub_after, owner, command, policy_after.get("entries") or {})
            draft_before = draft_after = None
            if deleting_links:
                removed = {key for key, row in policy_after.get("entries",{}).items() if row.get("lifecycle") != "active"}
                removed.update(set(policy_before.get("entries",{})) - set(policy_after.get("entries",{})))
                draft_before = draft_repository.load_owner(owner)
                draft_after = self.draft_service.prune_deleted_private_references(draft_before,removed)
            try:
                policy_repository.save_owner(owner, policy_after)
                if draft_after is not None:
                    draft_repository.save_owner(owner,draft_after)
                self._save(owner, pub_after)
            except Exception:
                try:
                    policy_repository.save_owner(owner, policy_before)
                except Exception:
                    pass
                try:
                    self._save(owner, pub_before)
                except Exception:
                    pass
                if draft_after is not None:
                    draft_repository.save_owner(owner,draft_before)
                raise

    def _apply_policy_effects(self, snapshot: dict, owner: str, command: dict, entries: dict) -> None:
        # This snapshot is saved with the canonical mutation by the existing
        # linked transaction, even before the first public copy exists.
        if type(self.repository) is InMemoryResumePublicationRepository:
            choices = snapshot.setdefault("guide_display_choices", {})
            if type(choices) is not dict:
                raise PublicationUnavailableError("Display choice history is unavailable. Your input is kept.")
            if command.get("type") == "create":
                choices.setdefault(command["entry_key"], "never_selected")
            elif command.get("type") == "change_permissions":
                for target in command.get("targets") or []:
                    if "resume_display" in (target.get("permissions") or {}):
                        choices[target["entry_key"]] = "explicitly_chosen"
        current = self._current(snapshot)
        if current is None:
            return
        command_type = command.get("type")
        if command_type == "edit":
            # The policy command already validates and corrects canonical state.
            # A private/restored entry has no outward projection to refresh.
            # Its correction must neither fail nor acquire publication membership.
            key = command["entry_key"]
            if key not in current["display"] and key not in current["visitor_ai"]:
                return
            self._correct(
                snapshot,
                owner,
                {
                    "entry_key": command["entry_key"],
                    "values": command.get("values") or (entries.get(command["entry_key"]) or {}).get("values") or {},
                    "expected_content_version": command.get("expected_content_version"),
                    "expected_access_revision": command.get("expected_access_revision"),
                    "canonical_type": command.get("canonical_type")
                    or (entries.get(command["entry_key"]) or {}).get("canonical_type")
                    or "role",
                },
                {"entries": entries, "expected": command},
            )
            return
        if command_type == "change_permissions":
            targets = command.get("targets") or [
                {
                    "entry_key": command.get("entry_key"),
                    "permissions": command.get("permissions")
                    or {
                        key: command[key]
                        for key in ("resume_display", "visitor_ai")
                        if key in command
                    },
                }
            ]
            for item in targets:
                payload = {"entry_key": item.get("entry_key") or command.get("entry_key")}
                payload["policy_entry"] = entries.get(payload["entry_key"])
                perms = item.get("permissions") or {}
                if "resume_display" in perms:
                    payload["resume_display"] = perms["resume_display"]
                elif "resume_display" in command:
                    payload["resume_display"] = command["resume_display"]
                if "visitor_ai" in perms:
                    payload["visitor_ai"] = perms["visitor_ai"]
                elif "visitor_ai" in command:
                    payload["visitor_ai"] = command["visitor_ai"]
                self._change_permissions(snapshot, payload)
            return
        if command_type == "delete":
            # The policy transaction has already validated and deleted the
            # counted group. Rebuild the projection from that authoritative
            # result, including linked achievements, in this same commit.
            removed = [key for key, entry in entries.items() if entry.get("lifecycle") != "active"]
            self._delete(snapshot, {"entry_key": command["entry_key"]}, entry_keys=removed)
            return
        if command_type == "restore":
            self._restore(snapshot, {"entry_key": command["entry_key"]})
            return
        if command_type in {"recategorize", "permanently_delete", "resolve_match"}:
            entry_key = command.get("entry_key")
            if entry_key:
                if command_type == "permanently_delete":
                    self._delete(snapshot, {"entry_key": entry_key})
                elif command_type == "resolve_match" and entry_key in (
                    current.get("display") or {}
                ) | (current.get("visitor_ai") or {}):
                    values = (entries.get(entry_key) or {}).get("values") or command.get("values") or {}
                    self._correct(
                        snapshot,
                        owner,
                        {
                            "entry_key": entry_key,
                            "values": values,
                            "canonical_type": (entries.get(entry_key) or {}).get("canonical_type") or "role",
                        },
                        {"entries": entries, "expected": command},
                    )
        return

    @owner_composed
    def bind_slug(self, owner: str, slug: str) -> None:
        if slug in self.reserved_public_slugs:
            raise PublicationValidationError("Example profile stays separately classified.")
        snapshot = self._load(owner)
        snapshot["slug"] = slug
        self._save(owner, snapshot)

    def _owner_for_slug(self, slug: str) -> str | None:
        if hasattr(self.repository, "_owners"):
            for owner, snapshot in self.repository._owners.items():
                if snapshot.get("slug") == slug:
                    return owner
        return None

    def _current(self, snapshot: dict) -> dict | None:
        revision = snapshot.get("current_revision")
        if revision is None:
            return None
        return snapshot["publications"].get(revision)

    def _apply(self, snapshot, owner, command_type, payload, reviewed, policy_snapshot):
        if command_type == "publish":
            return self._publish(snapshot, owner, payload, reviewed)
        if command_type == "correct":
            return self._correct(snapshot, owner, payload, policy_snapshot)
        if command_type == "change_permissions":
            return self._change_permissions(snapshot, payload)
        if command_type == "delete":
            return self._delete(snapshot, payload)
        if command_type == "restore":
            return self._restore(snapshot, payload)
        if command_type == "sharing_off":
            snapshot["sharing_enabled"] = False
            snapshot["sharing_epoch"] = int(snapshot["sharing_epoch"]) + 1
            return {"outcome": "restricted"}
        if command_type == "catalog_withdraw":
            self.catalog.withdraw(payload["asset_id"], int(payload["version"]))
            current = self._current(snapshot)
            if current:
                for slot, media in list(current["media"].items()):
                    if media.get("source_key") == payload["asset_id"]:
                        media["active"] = False
            return {"outcome": "withdrawn"}
        if command_type == "media_restrict":
            current = self._current(snapshot)
            if current is None:
                raise PublicationDenied("denied", "Publication is unavailable.")
            slot = payload["slot"]
            if slot in current["media"]:
                current["media"][slot]["active"] = False
            snapshot["revoked_media"].add(slot)
            return {"outcome": "restricted"}
        raise PublicationValidationError("Unknown command.")

    def _publish(self, snapshot, owner, payload, reviewed):
        if reviewed is None:
            raise PublicationValidationError("Reviewed candidate is required.")
        if reviewed.validation is not ReadState.CURRENT:
            raise PublicationDenied("stale", "The reviewed candidate is no longer current.")
        expected = payload.get("expected_publication_revision")
        if expected is not None and int(expected) != int(snapshot["publication_revision"]):
            raise PublicationConflictError("stale_publish", "The publication changed.")
        expected_digest = payload.get("reviewed_digest")
        if expected_digest and expected_digest != reviewed.digest:
            raise PublicationConflictError("stale_publish", "The reviewed candidate is no longer current.")
        new_revision = int(snapshot["publication_revision"]) + 1
        resulting = {}
        if self.draft_service is not None:
            rows = {row["entry_key"]: row for row in self.policy_service.list_entries(owner)["entries"]}
            for selection in reviewed.candidate.selections:
                row = rows[selection.entry.entry_key]
                resulting[selection.entry.entry_key] = (
                    row["content_version"] + int(bool(selection.deltas)),
                    row["access_revision"] + int((row["resume_display"], row["visitor_ai"]) !=
                                                (selection.display, selection.visitor_ai)),
                    row["canonical_type"],
                )
        def evidence_versions(item):
            if item.ref.entry_key in resulting:
                return resulting[item.ref.entry_key]
            return (int(item.ref.content_revision) if item.ref.content_revision.isdigit() else 1,
                    item.ref.access_revision,
                    payload.get("canonical_types", {}).get(item.ref.entry_key, "role"))
        display = {}
        visitor_ai = {}
        evidence = {}
        for item in reviewed.display.entries:
            values = _wording_map(item.wording)
            content_version, access_revision, current_type = evidence_versions(item)
            evidence_key = f"evidence:{item.ref.entry_key}"
            versioned = publication_evidence_version(
                owner_key=owner,
                entry_key=item.ref.entry_key,
                evidence_key=evidence_key,
                evidence_version_key=f"{evidence_key}:{new_revision}",
                version=new_revision,
                canonical_token=str(content_version) if resulting else item.ref.content_revision,
                policy_content_version=content_version,
                access_revision=access_revision,
                canonical_type=current_type,
                values=_codec_values(values, current_type),
                display_eligible=True,
                visitor_ai_eligible=False,
            )
            evidence[item.ref.entry_key] = versioned
            display[item.ref.entry_key] = {
                "canonical_type": current_type,
                "presentation_section": "story" if item.ref.entry_key == reviewed.candidate.story_entry_key else "entry",
                "wording": values,
                "evidence_sha256": versioned.content_sha256,
                "canonical_token": versioned.canonical_token,
            }
        for item in reviewed.visitor_ai.entries:
            values = _wording_map(item.wording)
            content_version, access_revision, current_type = evidence_versions(item)
            evidence_key = f"evidence:{item.ref.entry_key}"
            versioned = publication_evidence_version(
                owner_key=owner,
                entry_key=item.ref.entry_key,
                evidence_key=evidence_key,
                evidence_version_key=f"{evidence_key}:{new_revision}:ai",
                version=new_revision,
                canonical_token=str(content_version) if resulting else item.ref.content_revision,
                policy_content_version=content_version,
                access_revision=access_revision,
                canonical_type=current_type,
                values=_codec_values(values, current_type),
                display_eligible=item.ref.entry_key in display,
                visitor_ai_eligible=True,
            )
            evidence[item.ref.entry_key] = versioned
            visitor_ai[item.ref.entry_key] = {
                "canonical_type": current_type,
                "wording": values,
                "evidence_sha256": versioned.content_sha256,
                "canonical_token": versioned.canonical_token,
            }
            if item.ref.entry_key in display:
                display[item.ref.entry_key]["evidence_sha256"] = versioned.content_sha256
        for placement in reviewed.display.placements:
            if placement.source_kind == "generated_illustration":
                record = self.catalog.get_active(placement.asset_id, placement.asset_version)
                if record.digest != placement.asset_digest:
                    raise PublicationDenied("denied", "Media is unavailable.")
        media = self._reviewed_media(reviewed)
        publication = {
            "revision": new_revision,
            "digest": reviewed.digest,
            "profile_identity": (reviewed.candidate.profile_identity.to_payload()
                                 if reviewed.candidate.profile_identity is not None else None),
            "display": ordered_resume_display(display),
            "visitor_ai": visitor_ai,
            "evidence": evidence,
            "media": media,
        }
        snapshot["publications"][new_revision] = publication
        snapshot["publication_revision"] = new_revision
        snapshot["current_revision"] = new_revision
        snapshot["sharing_enabled"] = True
        snapshot["sharing_epoch"] = int(snapshot["sharing_epoch"]) + 1
        snapshot["slug"] = payload.get("slug") or snapshot.get("slug")
        return {"outcome": "published", "publication_revision": new_revision}

    def _correct(self, snapshot, owner, payload, policy_snapshot):
        current = self._current(snapshot)
        if current is None:
            raise PublicationDenied("denied", "Publication is unavailable.")
        expected = payload.get("expected_publication_revision")
        if expected is not None and int(expected) != int(current["revision"]):
            raise PublicationConflictError("stale_publish", "The publication changed.")
        entry_key = payload["entry_key"]
        if entry_key not in current["display"] and entry_key not in current["visitor_ai"]:
            raise PublicationDenied("denied", "Correction cannot expand membership.")
        values = payload.get("values") or {}
        canonical_type = payload.get("canonical_type") or "role"
        new_revision = int(snapshot["publication_revision"]) + 1
        versioned = publication_evidence_version(
            owner_key=owner,
            entry_key=entry_key,
            evidence_key=f"evidence:{entry_key}",
            evidence_version_key=f"evidence:{entry_key}:{new_revision}",
            version=new_revision,
            canonical_token=str(payload.get("canonical_token") or new_revision),
            policy_content_version=int(payload.get("expected_content_version") or new_revision),
            access_revision=int(payload.get("expected_access_revision") or 1),
            canonical_type=canonical_type,
            values=_codec_values(values, canonical_type),
            display_eligible=entry_key in current["display"],
            visitor_ai_eligible=entry_key in current["visitor_ai"],
        )
        updated = copy.deepcopy(current)
        updated["revision"] = new_revision
        updated["evidence"][entry_key] = versioned
        for bucket in ("display", "visitor_ai"):
            if entry_key in updated[bucket]:
                updated[bucket][entry_key]["wording"] = dict(values)
                updated[bucket][entry_key]["evidence_sha256"] = versioned.content_sha256
                updated[bucket][entry_key]["canonical_token"] = versioned.canonical_token
        snapshot["publications"][new_revision] = updated
        snapshot["publication_revision"] = new_revision
        snapshot["current_revision"] = new_revision
        updated["digest"] = versioned.content_sha256
        return {"outcome": "corrected", "publication_revision": new_revision}

    def _change_permissions(self, snapshot, payload):
        current = self._current(snapshot)
        if current is None:
            raise PublicationDenied("denied", "Publication is unavailable.")
        entry_key = payload["entry_key"]
        updated = copy.deepcopy(current)
        if payload.get("resume_display") is False:
            updated["display"].pop(entry_key, None)
        if payload.get("visitor_ai") is False:
            updated["visitor_ai"].pop(entry_key, None)
        policy_entry = payload.get("policy_entry")
        evidence = updated["evidence"].get(entry_key)
        if policy_entry is not None and evidence is not None:
            # The policy commit advances access even when only private
            # assistance changes. Refresh existing evidence authority without
            # adding an entry to either published manifest.
            if evidence.policy_content_version != policy_entry["content_version"]:
                raise PublicationConflictError("stale_publish", "Saved information changed.")
            updated["evidence"][entry_key] = replace(evidence,
                access_revision=policy_entry["access_revision"],
                display_eligible=policy_entry["resume_display"],
                visitor_ai_eligible=policy_entry["visitor_ai"],
                evidence_version_key=evidence.evidence_version_key + ':access:' + str(policy_entry["access_revision"]))
        new_revision = int(snapshot["publication_revision"]) + 1
        updated["revision"] = new_revision
        snapshot["publications"][new_revision] = updated
        snapshot["publication_revision"] = new_revision
        snapshot["current_revision"] = new_revision
        return {"outcome": "restricted", "publication_revision": new_revision}

    def _delete(self, snapshot, payload, *, entry_keys=None):
        current = self._current(snapshot)
        if current is None:
            return {"outcome": "deleted"}
        updated = copy.deepcopy(current)
        for entry_key in entry_keys if entry_keys is not None else (payload["entry_key"],):
            updated["display"].pop(entry_key, None)
            updated["visitor_ai"].pop(entry_key, None)
            updated["evidence"].pop(entry_key, None)
        new_revision = int(snapshot["publication_revision"]) + 1
        updated["revision"] = new_revision
        snapshot["publications"][new_revision] = updated
        snapshot["publication_revision"] = new_revision
        snapshot["current_revision"] = new_revision
        return {"outcome": "deleted", "publication_revision": new_revision}

    def _restore(self, snapshot, payload):
        """Restore stays private and cannot regrant publication membership."""
        return {"outcome": "restored_private"}


def _codec_values(values: dict, canonical_type: str) -> dict:
    mapped = dict(values)
    if canonical_type == "credential":
        for name in ("name", "issuer", "identifier"):
            if name in mapped:
                mapped[_canonical_field(canonical_type, name)] = mapped[name]
    if canonical_type == "skill" and "skill_name" in mapped:
        mapped.setdefault("name", mapped["skill_name"])
    if canonical_type == "knowledge" and "wording" in mapped:
        mapped.setdefault("summary", mapped["wording"])
    if canonical_type == "role":
        if "summary" in mapped and "role_title" not in mapped:
            mapped.setdefault("role_title", mapped.get("title") or mapped.get("role_title"))
    return mapped


def _canonical_field(canonical_type, editor_field):
    return {"skill": {"name": "skill_name", "summary": "skill_summary"},
            "credential": {"name": "credential_name", "issuer": "issuer_name", "identifier": "credential_identifier"}
            }.get(canonical_type, {}).get(editor_field, editor_field)


def owner_review_context(subject_key: str, resume_key: str) -> TrustedUseContext:
    return _context_from_authorized_server(
        subject_key=subject_key,
        resume_key=resume_key,
        audience=UseAudience.OWNER_PREVIEW,
        purpose=UsePurpose.PUBLICATION_REVIEW,
        authenticated_owner_key=subject_key,
    )


resume_publication_service = ResumePublicationService()
