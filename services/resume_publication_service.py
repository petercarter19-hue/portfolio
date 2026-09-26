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
from uuid import uuid4

from services.resume_media_catalog_repository import (
    CatalogFenceDenied,
    InMemoryResumeCatalogRepository,
    SqlResumeCatalogRepository,
)
from services.resume_publication_adapters import (
    OwnerMediaPort,
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

    def review_for_owner(self, owner: str, payload: dict | None = None, *, candidate=None):
        """Review current durable policy/draft/media. Does not write."""

        payload = payload if isinstance(payload, dict) else {}
        snapshot = self._load(owner)
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
            candidate, policy, media = build_owner_review_candidate(
                owner=owner,
                resume_key=str(payload.get("resume_key") or f"resume:{owner}"),
                draft_revision=int(payload.get("draft_revision") or 0),
                publication_revision=int(snapshot.get("publication_revision") or 0),
                sharing_epoch=int(snapshot.get("sharing_epoch") or 0),
                sharing_enabled=bool(snapshot.get("sharing_enabled")),
                entries=entries,
                payload=payload,
            )
            policy_port = OwnerPolicyPort(
                self.policy_service,
                resume_key=candidate.prior.resume_key,
                draft_revision=candidate.prior.draft_revision,
                publication_revision=candidate.prior.publication_revision,
                sharing_epoch=candidate.prior.sharing_epoch,
                sharing_enabled=policy.sharing_enabled,
                sources=policy.sources,
            )
            media_port = OwnerMediaPort(media)
        else:
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
                    if key in {"entries", "selections", "resume_key", "draft_revision"}
                },
            }
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
        if if_none_match and if_none_match.strip('"') == etag:
            return {"read_state": "not_modified", "etag": etag, "cache_control": "private,no-store"}
        media = {
            key: copy.deepcopy(item)
            for key, item in (current.get("media") or {}).items()
            if item.get("active")
        }
        return {
            "read_state": ReadState.CURRENT.value,
            "etag": etag,
            "cache_control": "private,no-store",
            "sharing_enabled": True,
            "publication_revision": current["revision"],
            "display": copy.deepcopy(current["display"]),
            "media": media,
        }

    def _guest_read_sql(self, *, slug: str, if_none_match: str | None = None) -> dict:
        try:
            row = self.sql_repository.get_public_by_slug(slug)
        except PublicationStoreUnavailable as error:
            raise PublicationUnavailableError("Publication is unavailable.") from error
        if not row:
            raise PublicationDenied("denied", "Publication is unavailable.")
        etag = str(row.get("reviewed_digest") or "")
        if if_none_match and etag and if_none_match.strip('"') == etag:
            return {"read_state": "not_modified", "etag": etag, "cache_control": "private,no-store"}
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
        return {
            "read_state": ReadState.CURRENT.value,
            "etag": etag,
            "cache_control": "private,no-store",
            "sharing_enabled": True,
            "publication_revision": row.get("publication_revision"),
            "display": display or {},
            "media": media,
        }

    def authorize_media(self, *, slug: str, slot: str, publication_revision: int | None = None) -> dict:
        if self.sql_repository is not None:
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
        return {"authorized": True, "slot": slot, "rechecked": True, **item}

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
            return {
                "status": 304,
                "etag": etag,
                "cache_control": "private,no-store",
                "body": b"",
                "content_type": "application/octet-stream",
            }
        blob = b""
        if self.media_bytes_port is not None:
            blob = self.media_bytes_port.read(first) or b""
        second = self.authorize_media(
            slug=slug, slot=slot, publication_revision=publication_revision
        )
        if second.get("content_sha256") != first.get("content_sha256") or not second.get("authorized"):
            raise PublicationDenied("denied", "Media is unavailable.")
        body = b"" if str(method).upper() == "HEAD" else blob
        return {
            "status": 200,
            "etag": etag,
            "cache_control": "private,no-store",
            "body": body,
            "content_type": "application/octet-stream",
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
        request_id = str(payload.get("request_id") or "")
        if not request_id:
            raise PublicationValidationError("request id is required.")
        command = dict(payload)
        body = {key: value for key, value in command.items() if key != "request_id"}
        digest = _digest(body)
        if self.sql_repository is None:
            with self._lock:
                before = self._load(owner)
                existing = before["receipts"].get(request_id)
                if existing is not None:
                    if existing["request_digest"] != digest:
                        raise PublicationConflictError("request_conflict", "That request already used a different payload.")
                    return {"receipt": dict(existing["receipt"]), "replayed": True, "read_state": ReadState.CURRENT.value}
                if command_type == "publish":
                    pending = self._pending_reviews.get(owner) or {}
                    review_payload = dict(pending.get("payload") or {})
                    review_payload.update(payload)
                    candidate = reviewed.candidate if reviewed is not None else None
                    result = self.review_for_owner(owner, review_payload, candidate=candidate)
                    if result.reviewed is None:
                        raise PublicationDenied(result.reason, "The reviewed candidate is no longer current.")
                    reviewed = result.reviewed
                    expected_digest = payload.get("reviewed_digest")
                    if expected_digest and expected_digest != reviewed.digest:
                        raise PublicationConflictError("stale_publish", "The reviewed candidate is no longer current.")
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
            pending = self._pending_reviews.get(owner) or {}
            review_payload = dict(pending.get("payload") or {})
            review_payload.update(payload)
            candidate = reviewed.candidate if reviewed is not None else None
            result = self.review_for_owner(owner, review_payload, candidate=candidate)
            if result.reviewed is None:
                raise PublicationDenied(result.reason, "The reviewed candidate is no longer current.")
            reviewed = result.reviewed
            expected_digest = payload.get("reviewed_digest")
            if expected_digest and expected_digest != reviewed.digest:
                raise PublicationConflictError("stale_publish", "The reviewed candidate is no longer current.")
            command["reviewed_digest"] = reviewed.digest
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
            self._delete(snapshot, {"entry_key": command["entry_key"]})
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
        display = {}
        visitor_ai = {}
        evidence = {}
        for item in reviewed.display.entries:
            values = _wording_map(item.wording)
            evidence_key = f"evidence:{item.ref.entry_key}"
            versioned = publication_evidence_version(
                owner_key=owner,
                entry_key=item.ref.entry_key,
                evidence_key=evidence_key,
                evidence_version_key=f"{evidence_key}:{new_revision}",
                version=new_revision,
                canonical_token=item.ref.content_revision,
                policy_content_version=max(item.ref.access_revision, 1),
                access_revision=item.ref.access_revision,
                canonical_type=payload.get("canonical_types", {}).get(item.ref.entry_key, "role"),
                values=_codec_values(values, payload.get("canonical_types", {}).get(item.ref.entry_key, "role")),
                display_eligible=True,
                visitor_ai_eligible=False,
            )
            evidence[item.ref.entry_key] = versioned
            display[item.ref.entry_key] = {
                "wording": values,
                "evidence_sha256": versioned.content_sha256,
                "canonical_token": versioned.canonical_token,
            }
        for item in reviewed.visitor_ai.entries:
            values = _wording_map(item.wording)
            current_type = payload.get("canonical_types", {}).get(item.ref.entry_key, "role")
            evidence_key = f"evidence:{item.ref.entry_key}"
            versioned = publication_evidence_version(
                owner_key=owner,
                entry_key=item.ref.entry_key,
                evidence_key=evidence_key,
                evidence_version_key=f"{evidence_key}:{new_revision}:ai",
                version=new_revision,
                canonical_token=item.ref.content_revision,
                policy_content_version=max(item.ref.access_revision, 1),
                access_revision=item.ref.access_revision,
                canonical_type=current_type,
                values=_codec_values(values, current_type),
                display_eligible=item.ref.entry_key in display,
                visitor_ai_eligible=True,
            )
            evidence[item.ref.entry_key] = versioned
            visitor_ai[item.ref.entry_key] = {
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
                "active": True,
            }
        publication = {
            "revision": new_revision,
            "digest": reviewed.digest,
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
        new_revision = int(snapshot["publication_revision"]) + 1
        updated["revision"] = new_revision
        snapshot["publications"][new_revision] = updated
        snapshot["publication_revision"] = new_revision
        snapshot["current_revision"] = new_revision
        return {"outcome": "restricted", "publication_revision": new_revision}

    def _delete(self, snapshot, payload):
        current = self._current(snapshot)
        if current is None:
            return {"outcome": "deleted"}
        entry_key = payload["entry_key"]
        updated = copy.deepcopy(current)
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
    if canonical_type == "role":
        if "summary" in mapped and "role_title" not in mapped:
            mapped.setdefault("role_title", mapped.get("title") or mapped.get("role_title"))
    return mapped


def owner_review_context(subject_key: str, resume_key: str) -> TrustedUseContext:
    return _context_from_authorized_server(
        subject_key=subject_key,
        resume_key=resume_key,
        audience=UseAudience.OWNER_PREVIEW,
        purpose=UsePurpose.PUBLICATION_REVIEW,
        authenticated_owner_key=subject_key,
    )


resume_publication_service = ResumePublicationService()
