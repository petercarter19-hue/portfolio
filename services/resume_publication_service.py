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
from contextlib import nullcontext
from uuid import uuid4

from services.mvp1_profile_binding import identity_reference

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
    ReadState,
    TrustedUseContext,
    UseAudience,
    UsePurpose,
    _context_from_authorized_server,
)
from services.resume_publication_projection import publication_evidence_version
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

    def draft_preview(self, owner, payload=None):
        result = self.review_for_owner(owner, payload)
        if result.reviewed is None:
            raise PublicationConflictError("stale_preview", "The private preview changed. Review again.")
        reviewed = result.reviewed
        from services.resume_publication_validation import _placement
        sharing = self._load(owner)
        return {"published": False, "preview_only": True, "read_state": "current",
            "sharing_enabled": bool(sharing["sharing_enabled"]),
            "publication_revision": sharing["publication_revision"],
            "digest": reviewed.digest,
            "display": {item.ref.entry_key: {"wording": _wording_map(item.wording)} for item in reviewed.display.entries},
            "media": {item.slot: _placement(item) for item in reviewed.display.placements},
            "public_identity": self._public_identity(owner,
                reviewed.candidate.profile_identity.to_payload() if reviewed.candidate.profile_identity else None)}

    def review_for_owner(self, owner: str, payload: dict | None = None, *, candidate=None):
        """Review current durable policy/draft/media. Does not write."""

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
            list_for_review = getattr(
                self.policy_service, "list_publication_entries", self.policy_service.list_entries
            )
            listed = list_for_review(owner)
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
                self.policy_service,
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
        result = validate_candidate(candidate, policy_port, media_port)
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
            "display": display or {},
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
            with self._lock, self._memory_media_lock(), self._memory_draft_lock():
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
        """Save policy and publication together, restoring both on failure."""

        with self._lock:
            if policy_repository.load_owner(owner) != policy_before:
                raise PublicationConflictError("stale_publish", "Saved information changed.")
            pub_before = self._load(owner)
            pub_after = copy.deepcopy(pub_before)
            self._apply_policy_effects(pub_after, owner, command, policy_after.get("entries") or {})
            try:
                policy_repository.save_owner(owner, policy_after)
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
                raise

    def _apply_policy_effects(self, snapshot: dict, owner: str, command: dict, entries: dict) -> None:
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
        media = {}
        for placement in reviewed.display.placements:
            if placement.source_kind == "generated_illustration":
                record = self.catalog.get_active(placement.asset_id, placement.asset_version)
                if record.digest != placement.asset_digest:
                    raise PublicationDenied("denied", "Media is unavailable.")
            media[placement.slot] = {
                "slot": placement.slot,
                "source_kind": placement.source_kind,
                "source_key": placement.asset_id,
                "asset_version": placement.asset_version,
                "content_sha256": placement.asset_digest,
                "catalog_revision": None if placement.source_kind != "generated_illustration" else str(placement.asset_version),
                "source_revision": next(item.source_revision for item in reviewed.versions.media if item.slot == placement.slot),
                "presentation_version": placement.presentation_version,
                "crop": placement.crop.as_dict(),
                "alt_text": placement.alt_text,
                "decorative": placement.decorative,
                "caption": placement.caption,
                "provenance_label": placement.provenance_label,
                "active": True,
            }
        publication = {
            "revision": new_revision,
            "digest": reviewed.digest,
            "profile_identity": (reviewed.candidate.profile_identity.to_payload()
                                 if reviewed.candidate.profile_identity is not None else None),
            "display": display,
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
