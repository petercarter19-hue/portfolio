"""Trusted adapters from current policy/media authorities into E ports.

These adapters never invent versions. Missing or unavailable authority fails
closed. Review itself performs no writes.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Callable
from uuid import uuid4

from services.resume_publication_contracts import (
    CandidateInput,
    ContractError,
    EditorialDelta,
    DraftEntryBase,
    EntryRef,
    EntrySelection,
    EntryState,
    MediaSnapshot,
    MediaState,
    MediaVersion,
    NeutralReviewEvidence,
    PolicySnapshot,
    ReadState,
    SourceRef,
    SourceState,
    UseAudience,
    UsePurpose,
    VersionTuple,
    Wording,
    _context_from_authorized_server,
)
from services.resume_media_repository import MediaPlacement


class SnapshotPolicyPort:
    def __init__(self, snapshot: PolicySnapshot) -> None:
        self.snapshot = snapshot

    def read_current(self, context, refs: tuple[EntryRef, ...]) -> PolicySnapshot:
        if self.snapshot.versions is None:
            return PolicySnapshot(ReadState.UNAVAILABLE)
        if tuple(item.identity for item in refs) != tuple(item.identity for item in self.snapshot.versions.entries):
            return PolicySnapshot(ReadState.STALE, self.snapshot.versions)
        return self.snapshot


class SnapshotMediaPort:
    def __init__(self, snapshot: MediaSnapshot) -> None:
        self.snapshot = snapshot

    def read_current(self, context, placements: tuple[MediaPlacement, ...]) -> MediaSnapshot:
        return self.snapshot


class CatalogGuardedMediaPort:
    def __init__(self, inner, catalog) -> None:
        self.inner = inner
        self.catalog = catalog

    def read_current(self, context, placements: tuple[MediaPlacement, ...]) -> MediaSnapshot:
        snapshot = self.inner.read_current(context, placements)
        if snapshot.state is not ReadState.CURRENT:
            return snapshot
        media = []
        for item in snapshot.media:
            if item.ref.source_kind == "generated_illustration":
                try:
                    record = self.catalog.get_active(item.ref.source_key, item.ref.asset_version)
                except Exception as error:
                    from services.resume_media_catalog_repository import CatalogFenceDenied

                    if not isinstance(error, CatalogFenceDenied):
                        raise
                    return MediaSnapshot(ReadState.DENIED, snapshot.versions)
                if record.lifecycle != "active" or record.digest != item.ref.content_sha256:
                    return MediaSnapshot(ReadState.DENIED, snapshot.versions)
                media.append(
                    MediaState(item.ref, item.width, item.height, item.ready, item.active, record)
                )
            else:
                media.append(item)
        return MediaSnapshot(ReadState.CURRENT, snapshot.versions, tuple(media))


def policy_snapshot_from_entries(
    *,
    subject_key: str,
    resume_key: str,
    draft_revision: int,
    publication_revision: int,
    sharing_epoch: int,
    sharing_enabled: bool,
    entries: list[dict],
    sources: tuple[SourceState, ...] = (),
    wording_fields=None,
    wording_values=None,
) -> PolicySnapshot:
    refs = []
    states = []
    for item in entries:
        ref = EntryRef(
            subject_key,
            str(item["entry_key"]),
            str(item.get("content_token") or item.get("content_version")),
            int(item["access_revision"]),
        )
        values = dict((wording_values or {}).get(str(item["entry_key"]), item.get("values") or {}))
        for name in (wording_fields or {}).get(str(item["entry_key"]), ()):
            values.setdefault(name, None)
        wording = tuple(
            Wording(str(key), value)
            for key, value in sorted(values.items())
            if type(value) in (str, bool, type(None))
        )
        refs.append(ref)
        states.append(
            EntryState(
                ref,
                wording,
                bool(item.get("resume_display")),
                bool(item.get("visitor_ai")),
                item.get("lifecycle", "active") == "active",
                True,
                bool(item.get("private_assistance_excluded")),
            )
        )
    versions = VersionTuple(
        subject_key,
        resume_key,
        draft_revision,
        publication_revision,
        sharing_epoch,
        tuple(refs),
        tuple(source.ref for source in sources),
        (),
    )
    return PolicySnapshot(ReadState.CURRENT, versions, sharing_enabled, tuple(states), sources)


class OwnerPolicyPort:
    """Durable owner policy reads through list/get. Missing versions fail closed."""

    def __init__(
        self,
        policy_service,
        *,
        resume_key: str,
        draft_revision: int,
        publication_revision: int,
        sharing_epoch: int,
        sharing_enabled: bool,
        sources: tuple[SourceState, ...] = (),
        wording_fields=None,
        draft_service=None,
        draft_bases=(),
        media_versions=(),
        wording_values=None,
    ) -> None:
        self.policy_service = policy_service
        self.resume_key = resume_key
        self.draft_revision = draft_revision
        self.publication_revision = publication_revision
        self.sharing_epoch = sharing_epoch
        self.sharing_enabled = sharing_enabled
        self.sources = sources
        self.wording_fields = wording_fields
        self.draft_service = draft_service
        self.draft_bases = draft_bases
        self.media_versions = media_versions
        self.wording_values = wording_values

    def read_current(self, context, refs: tuple[EntryRef, ...]) -> PolicySnapshot:
        try:
            if self.draft_service is not None:
                workspace = self.draft_service.get_workspace(context.subject_key)
                if (workspace.get("draft_version") != self.draft_revision
                        or workspace.get("capabilities", {}).get("canonical_read") != "ok"):
                    return PolicySnapshot(ReadState.STALE)
                current_items = {item["record_key"]: item for item in workspace.get("items", ())}
                self.wording_values = {key: item.get("values") or {} for key, item in current_items.items()}
                for base in self.draft_bases:
                    item = current_items.get(base.entry.entry_key)
                    if (item is None or item.get("orphaned") or item.get("draft_is_stale")
                            or item.get("content_token") != base.canonical_token
                            or item.get("access_revision") != base.entry.access_revision):
                        return PolicySnapshot(ReadState.STALE)
            list_for_review = getattr(
                self.policy_service, "list_publication_entries", self.policy_service.list_entries
            )
            listed = list_for_review(context.subject_key)
        except Exception:
            return PolicySnapshot(ReadState.UNAVAILABLE)
        entries = []
        for item in listed.get("entries") or []:
            if item.get("lifecycle") != "active":
                continue
            if item.get("access_revision") is None or item.get("content_version") is None:
                return PolicySnapshot(ReadState.UNAVAILABLE)
            entries.append(item)
        snapshot = policy_snapshot_from_entries(
            subject_key=context.subject_key,
            resume_key=self.resume_key,
            draft_revision=self.draft_revision,
            publication_revision=self.publication_revision,
            sharing_epoch=self.sharing_epoch,
            sharing_enabled=self.sharing_enabled,
            entries=entries,
            sources=self.sources,
            wording_fields=self.wording_fields,
            wording_values=self.wording_values,
        )
        if tuple(item.identity for item in refs) != tuple(
            item.identity for item in snapshot.versions.entries
        ):
            return PolicySnapshot(ReadState.STALE, snapshot.versions)
        return replace(snapshot, versions=replace(snapshot.versions, media=self.media_versions))


class DraftMediaPublicationPort:
    """Read the existing draft and source authorities; never trust client media."""

    def __init__(self, application, versions=None):
        self.application = application
        self.versions = versions

    def read_draft(self, owner, draft_revision):
        repository = self.application.media_repository
        draft = repository.get_draft(owner_id=owner)
        if draft.version != draft_revision:
            raise ContractError("media draft changed")
        states = []
        for placement in draft.placements:
            catalog = None
            if placement.source_kind == "owner_photo":
                record = repository.get_owner_photo(owner_id=owner, source_id=placement.asset_id)
                ready = record is not None and record.state == "ready"
            else:
                record = repository.get_catalog_asset(asset_id=placement.asset_id, version=placement.asset_version)
                catalog = record
                ready = record is not None
            if record is None or record.lifecycle != "active" or not ready:
                raise ContractError("media source is unavailable")
            readiness = hashlib.sha256(json.dumps({
                "version": record.version, "digest": record.digest, "state": getattr(record, "state", "ready"),
                "lifecycle": record.lifecycle, "width": record.width, "height": record.height,
                "source_revision": getattr(record, "version_token", str(record.version)),
            }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            ref = MediaVersion(owner, placement.slot, placement.presentation_version, placement.source_kind,
                placement.asset_id, getattr(record, "version_token", str(record.version)), record.version,
                str(record.version) if catalog else None, record.digest, readiness)
            states.append(MediaState(ref, record.width, record.height, True, True, catalog))
        return draft.placements, tuple(sorted(states, key=lambda item: item.ref))

    def read_current(self, context, placements):
        try:
            current, states = self.read_draft(context.subject_key, self.versions.draft_revision)
            if tuple(sorted(current, key=lambda item: item.slot)) != placements:
                return MediaSnapshot(ReadState.STALE)
            return MediaSnapshot(ReadState.CURRENT, self.versions, states)
        except Exception:
            return MediaSnapshot(ReadState.UNAVAILABLE)


class PublishedMediaBytesPort:
    """Storage adapter called only after the publication authorizes a source.

    Owner identity here comes from that server authorization, never the guest
    request. Existing media readers enforce source ownership, byte integrity
    and a second source check. The caller then rechecks publication eligibility.
    """

    def __init__(self, application):
        self.application = application

    def read(self, authorization):
        from services.resume_publication_service import PublicationUnavailableError
        try:
            owner = authorization["owner_user_key"]
            if authorization.get("authorized") is not True or type(owner) is not str or not owner:
                raise ValueError("publication authority required")
            if authorization["source_kind"] == "owner_photo":
                opened = self.application.open_photo_preview(owner_id=owner, source_id=authorization["source_key"])
            elif authorization["source_kind"] == "generated_illustration":
                opened = self.application.open_library_thumbnail(owner_id=owner,
                    asset_id=authorization["source_key"], asset_version=authorization["asset_version"],
                    slot=authorization["slot"])
            else:
                raise ValueError("invalid media kind")
            if not opened:
                raise ValueError("media changed")
            data = opened["stream"].read()
            if len(data) != opened["byte_length"]:
                raise ValueError("media changed")
            return {"data": data, "content_type": opened["content_type"]}
        except Exception as error:
            raise PublicationUnavailableError("Resume media storage is unavailable.") from error


class OwnerMediaPort:
    """Durable owner media reads. Empty placements remain current."""

    def __init__(self, snapshot: MediaSnapshot) -> None:
        self.snapshot = snapshot

    def read_current(self, context, placements: tuple[MediaPlacement, ...]) -> MediaSnapshot:
        if self.snapshot.state is not ReadState.CURRENT:
            return self.snapshot
        if tuple(item.slot for item in placements) != tuple(
            item.ref.slot for item in self.snapshot.media
        ):
            return MediaSnapshot(ReadState.STALE, self.snapshot.versions)
        return self.snapshot


def _neutral_evidence(owner: str, ref: EntryRef, wording: tuple[Wording, ...]) -> NeutralReviewEvidence:
    content = "\n".join(
        f"{item.field}={item.value if item.value is not None else ''}"
        for item in sorted(wording)
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    token = ref.content_revision
    policy_version = int(token) if str(token).isdigit() else 1
    if policy_version < 1:
        policy_version = 1
    return NeutralReviewEvidence(
        entry=ref,
        evidence_key=f"ev:{ref.entry_key}",
        evidence_version_key=f"ev:{ref.entry_key}:{ref.access_revision}",
        version=max(ref.access_revision, 1),
        content_sha256=digest,
        codec="resume-canonical-source.v1",
        canonical_token=token,
        policy_content_version=policy_version,
        access_revision=ref.access_revision,
        lifecycle="active",
        owner_key=owner,
        saved=True,
        approved=True,
        active=True,
        canonical_evidence=True,
        ai_use_count=0,
        content=content,
    )


def build_owner_review_candidate(
    *,
    owner: str,
    resume_key: str,
    draft_revision: int,
    publication_revision: int,
    sharing_epoch: int,
    sharing_enabled: bool,
    entries: list[dict],
    payload: dict | None = None,
    placements: tuple[MediaPlacement, ...] = (),
    media_versions: tuple[MediaVersion, ...] = (),
    media_states=None,
    sources: tuple[SourceState, ...] = (),
    profile_identity=None,
    draft_items=(),
    story_entry_key=None,
):
    """Build an owner review candidate from durable list/get rows. Review does not write."""

    payload = payload or {}
    choices = payload.get("entries") or payload.get("selections") or []
    choice_map = {}
    if type(choices) is not list:
        raise ContractError("entry selections must be a list")
    for item in choices:
        if type(item) is not dict or type(item.get("entry_key")) is not str:
            raise ContractError("invalid entry selection")
        if item["entry_key"] in choice_map:
            raise ContractError("duplicate entry selection")
        for flag in ("resume_display", "display", "visitor_ai"):
            if flag in item and type(item[flag]) is not bool:
                raise ContractError("permissions must be explicit booleans")
        choice_map[item["entry_key"]] = item
    if set(choice_map) - {row["entry_key"] for row in entries}:
        raise ContractError("entry selection is unavailable")
    overlays = {item["record_key"]: item for item in draft_items if item.get("has_draft")}
    workspace_items = {item["record_key"]: item for item in draft_items}
    if story_entry_key is not None and not any(row["entry_key"] == story_entry_key
            and row["canonical_type"] == "knowledge" for row in entries):
        raise ContractError("Story reference is unavailable")
    if any(item.get("orphaned") or item.get("draft_is_stale") for item in overlays.values()):
        raise ContractError("stale Resume draft")
    wording_fields = {key: tuple((item.get("proposed_values") or {}).keys()) for key, item in overlays.items()}
    snapshot = policy_snapshot_from_entries(
        subject_key=owner,
        resume_key=resume_key,
        draft_revision=draft_revision,
        publication_revision=publication_revision,
        sharing_epoch=sharing_epoch,
        sharing_enabled=sharing_enabled,
        entries=entries,
        sources=sources,
        wording_fields=wording_fields,
        wording_values={key: item.get("values") or {} for key, item in workspace_items.items()},
    )
    context = _context_from_authorized_server(
        subject_key=owner,
        resume_key=resume_key,
        audience=UseAudience.OWNER_PREVIEW,
        purpose=UsePurpose.PUBLICATION_REVIEW,
        authenticated_owner_key=owner,
    )
    versions = VersionTuple(
        owner,
        resume_key,
        draft_revision,
        publication_revision,
        sharing_epoch,
        snapshot.versions.entries,
        tuple(source.ref for source in sources),
        media_versions,
    )
    selections = []
    evidence = []
    draft_bases = []
    for state in snapshot.entries:
        overlay = overlays.get(state.ref.entry_key)
        deltas = []
        canonical = workspace_items.get(state.ref.entry_key)
        if canonical is not None:
            draft_bases.append(DraftEntryBase(state.ref, canonical["content_token"]))
        if overlay:
            if (overlay.get("draft_base_content_token") != overlay.get("content_token")
                    or overlay.get("draft_base_access_revision") != state.ref.access_revision):
                raise ContractError("stale Resume draft")
            before = {item.field: item.value for item in state.wording}
            for name, value in (overlay.get("proposed_values") or {}).items():
                if value != before.get(name):
                    deltas.append(EditorialDelta(name, before.get(name), value))
        choice = choice_map.get(state.ref.entry_key)
        if choice:
            display = bool(choice.get("resume_display", choice.get("display", state.display_allowed)))
            visitor_ai = bool(choice.get("visitor_ai", state.visitor_ai_allowed))
        else:
            display = state.display_allowed
            visitor_ai = state.visitor_ai_allowed
        expand_display = display and not state.display_allowed
        expand_visitor_ai = visitor_ai and not state.visitor_ai_allowed
        selections.append(
            EntrySelection(state.ref, display, visitor_ai, expand_display, expand_visitor_ai, tuple(deltas))
        )
        if visitor_ai:
            evidence.append(_neutral_evidence(owner, state.ref, state.wording))
    candidate = CandidateInput(
        context,
        versions,
        tuple(selections),
        placements,
        review_evidence=tuple(evidence),
        profile_identity=profile_identity,
        draft_bases=tuple(draft_bases),
        story_entry_key=story_entry_key,
    )
    if media_states is None:
        media_states = tuple(MediaState(item, 1800, 600, True, True) for item in media_versions)
    media = MediaSnapshot(ReadState.CURRENT, versions, media_states)
    policy = PolicySnapshot(
        ReadState.CURRENT, versions, sharing_enabled, snapshot.entries, sources
    )
    return candidate, policy, media


PROOF_ID = "ps-mvp1-ef-sql-proof-20260916-01"
CLIENT_LOCK_INTENT = hashlib.sha256(
    b"SERIALIZABLE|UPDLOCK,HOLDLOCK|resume-canonical-source.v1"
).hexdigest()
FORBIDDEN_PRODUCTION_DATABASES = frozenset({"peerslate-database", "peerslate-staging"})
REQUIRED_PUBLICATION_CLOSURE_IDS = (
    "PS-PLAT-000",
    "PS-PLAT-001",
    "PS-PLAT-002",
    "PS-PLAT-003",
    "PS-PLAT-004",
    "PS-PLAT-005",
    "PS-PLAT-006",
    "PS-PLAT-007",
    "PS-RESUME-EDIT-001",
    "PS-RESUME-EDIT-002",
    "PS-ENTRY-POLICY-001",
    "PS-RESUME-DRAFT-001",
    "PS-RESUME-INTAKE-001",
    "PS-AUTH-001",
    "PS-CAPTURE-001",
    "PS-CAPTURE-002",
    "PS-MOMENT-001",
    "PS-PLACEMENT-001",
    "PS-VOICE-001",
    "PS-CAPTURE-MEDIA-001",
    "PS-RESUME-MEDIA-001",
    "PS-RESUME-CATALOG-001",
    "PS-RESUME-PUBLICATION-001",
)
PROOF_NETWORK = f"{PROOF_ID}-net"
PROOF_SQL_CONTAINER = f"{PROOF_ID}-sql"
PROOF_CLIENT_CONTAINER = f"{PROOF_ID}-client"
PROOF_EMPTY_DATABASE = "PeerSlateMvp1EFEmpty_20260916_01"
PROOF_POPULATED_DATABASE = "PeerSlateMvp1EFPopulated_20260916_01"
SQL_IMAGE = (
    "mcr.microsoft.com/mssql/server:2022-CU26-ubuntu-22.04"
    "@sha256:ba4c8329f48fb8f02e1416be6a930ebfd71268caee78aa985f3af4315e457c89"
)
CLIENT_IMAGE = (
    "python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464"
)
PROOF_CLIENT_LOCKFILE = (
    Path(__file__).resolve().parents[1] / "requirements-resume-publication-sql-proof.txt"
)
PROOF_CLIENT_REMOTE_ROOT = "/opt/peerslate/src"
PROOF_CLIENT_REMOTE_WHEELS = "/opt/peerslate/wheels"
PROOF_CLIENT_REMOTE_LOCK = f"{PROOF_CLIENT_REMOTE_ROOT}/requirements-resume-publication-sql-proof.txt"
PROOF_CLIENT_REMOTE_EVIDENCE = "/tmp/resume-publication-sql-proof.json"
PROOF_SQL_MEMORY = "3g"
PROOF_CLIENT_MEMORY = "1g"
PROOF_SQL_CPUS = "2"
PROOF_CLIENT_CPUS = "1"
PROOF_SQL_PIDS = "512"
PROOF_CLIENT_PIDS = "256"
PROOF_JOB_TIMEOUT_SECONDS = 45 * 60
PROOF_CLIENT_ORACLE_TIMEOUT_SECONDS = 30 * 60
PROOF_CLEANUP_COMMAND_TIMEOUT_SECONDS = 30
PROOF_CLEANUP_RETRY = 1
PROOF_CLEANUP_WINDOW_SECONDS = 5 * 60
PROOF_SQL_READY_TIMEOUT_SECONDS = 120
PROOF_COMMAND_TIMEOUT_SECONDS = 30
PROOF_SQL_BUILD = "16.0.4265.3"
PROOF_SQL_EDITION_TOKEN = "Developer"
PROOF_ENTRY_KEY = "00000000-0000-4000-8000-000000000001"
PROOF_BATCH_ENTRY_KEY = "00000000-0000-4000-8000-000000000002"
PROOF_EDITOR_CONTROL_COMMAND = "00000000-0000-4000-8000-0000000000e4"
PROOF_EDITOR_CONTROL_KEY = "00000000-0000-4000-8000-0000000000e5"
PROOF_EDITOR_INVALID_FIELDS = (
    ("00000000-0000-4000-8000-0000000000e7",
     "00000000-0000-4000-8000-0000000000e9", "Role_Title"),
    ("00000000-0000-4000-8000-0000000000e8",
     "00000000-0000-4000-8000-0000000000ea", "unknown_field"),
    ("00000000-0000-4000-8000-0000000000eb",
     "00000000-0000-4000-8000-0000000000ec", "summary "),
)
PROOF_FOREIGN_ENTRY_KEY = "00000000-0000-4000-8000-0000000000fe"
PROOF_FOREIGN_EXTRA_ENTRY_KEYS = (
    "00000000-0000-4000-8000-0000000000fc",
    "00000000-0000-4000-8000-0000000000fd",
)
PROOF_CATALOG_ASSET_ID = "00000000-0000-4000-8000-0000000000ca"
PROOF_MISSING_ENTRY_KEY = "00000000-0000-4000-8000-0000000000de"
PROOF_SEED_SUMMARY = "Led team 0."
PROOF_CORRECTED_SUMMARY = "Led team 1."
PROOF_RACE_SUMMARY = "Led team 2."
PROOF_PUBLIC_SLUG = "alice"
PROOF_CLIENT_SOURCE_PATHS = (
    "scripts/run_resume_publication_sql_proof.py",
    "scripts/configure_resume_publication_sql_authority.py",
    "requirements-resume-publication-sql-proof.txt",
    "services/resume_publication_adapters.py",
    "services/resume_publication_contracts.py",
    "services/resume_publication_repository.py",
    "services/resume_publication_service.py",
    "services/entry_policy_repository.py",
    "services/entry_policy_service.py",
    "services/living_resume_editor_service.py",
    "services/database_service.py",
    "db.py",
    "services/resume_publication_projection.py",
    "services/resume_publication_validation.py",
    "services/resume_media_repository.py",
    "services/resume_media_catalog_repository.py",
    "services/resume_media_application.py",
    "services/my_data_service.py",
    "services/response_policy.py",
    "services/ai_foundation",
    "templates/resume_publication.html",
    "SQL FIles",
)
PROOF_CLIENT_PACKAGING = "baked_reviewed_source_on_pinned_base"
PROOF_CLIENT_IMAGE_NAME = "peerslate-mvp1-e-sql-proof:20260916-01"
MANDATORY_ENGINE_CASES = (
    "empty_forward_verify_rollback_reapply_verify",
    "capture_rollback_dependency_guards",
    "empty_rollback_restores_predecessor_execute",
    "verifier_mutation_rejections",
    "empty_forward_idempotency",
    "sql_sequence_contracts",
    "compile_complete_closure",
    "schema_permissions_constraints",
    "production_repository_commit_and_read",
    "production_service_publish_correct_restrict",
    "my_data_bulk_permissions_atomic",
    "guest_html_json_media_readers",
    "receipt_replay",
    "receipt_conflict_changed_body",
    "correction_rejects_missing_foreign_deleted_stale",
    "publish_versus_correction",
    "publish_versus_policy_restriction",
    "publish_versus_sharing_off",
    "publish_versus_delete",
    "publish_versus_restore",
    "publish_versus_draft_change",
    "publish_versus_media_restrict",
    "publish_versus_catalog_withdraw",
    "revoke_before_response_commit",
    "injected_rollback_after_evidence",
    "application_principal_effective_denial",
    "restricted_principal_direct_denial",
    "cross_owner_denial",
    "populated_database_seed_and_oracles",
    "empty_database_compile",
)
PERMITTED_RACE_PAIRS = frozenset(
    {
        "publish_versus_correction",
        "publish_versus_revocation",
        "publish_versus_policy_restriction",
        "publish_versus_delete",
        "publish_versus_restore",
        "publish_versus_draft_change",
        "publish_versus_media_restrict",
        "publish_versus_catalog_withdraw",
    }
)
PERMITTED_RACE_OUTCOMES = frozenset({"committed", "conflict"})
_SECRET_IN_TEXT = re.compile(
    r"(?i)(PWD=|Password=|MSSQL_SA_PASSWORD=|SQLCMDPASSWORD=)[^\s;\"']+"
)


class EngineProofError(RuntimeError):
    """Disposable engine proof failed. Never a production apply."""


@contextmanager
def _expect_publication_error(expected_type: type[Exception], missing_code: str):
    try:
        yield
    except expected_type:
        return
    raise EngineProofError(missing_code)


def refuse_client_supplied_dsn(dsn: str | None) -> None:
    if dsn:
        raise EngineProofError("client_dsn_forbidden")


def checkout_sha(root: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root or Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=PROOF_COMMAND_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0 or not (completed.stdout or "").strip():
        raise EngineProofError("source_sha_unavailable")
    actual = (completed.stdout or "").strip().lower()
    for env_name in ("BUILD_SOURCEVERSION", "PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA"):
        supplied = os.environ.get(env_name, "").strip().lower()
        if supplied and supplied != actual:
            raise EngineProofError("source_sha_mismatch")
    return actual


def assert_reviewed_source(requested_sha: str, root: Path | None = None) -> str:
    if not requested_sha or not re.fullmatch(r"[0-9a-f]{40}", requested_sha.lower()):
        raise EngineProofError("source_sha_required")
    actual = checkout_sha(root)
    if actual != requested_sha.lower():
        raise EngineProofError("source_sha_mismatch")
    return actual


def source_manifest(root: Path | None = None) -> dict[str, str]:
    base = root or Path(__file__).resolve().parents[1]
    digest = {}
    for relative in PROOF_CLIENT_SOURCE_PATHS:
        path = base / relative
        if not path.exists():
            raise EngineProofError(f"client_source_missing:{relative}")
        if path.is_file():
            digest[relative.replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
            continue
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file() or "__pycache__" in file_path.parts:
                continue
            if file_path.suffix in {".pyc", ".pyo"}:
                continue
            key = file_path.relative_to(base).as_posix()
            digest[key] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if not digest:
        raise EngineProofError("client_source_manifest_empty")
    return digest


def manifest_digest(manifest: dict[str, str]) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sanitize_proof_error(error: BaseException, secrets: tuple[str, ...] | list[str] = ()) -> str:
    """Keep failure evidence free of invocation-local secrets and DSN passwords."""

    text = f"{type(error).__name__}: {error}"
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return _SECRET_IN_TEXT.sub(r"\1[redacted]", text)


def is_expected_populated_publication_rollback_refusal(error: BaseException) -> bool:
    """Recognize the exact populated guard when the SQL driver omits its number."""

    current = error
    seen = set()
    while current is not None and id(current) not in seen:
        if "54120" in str(current):
            return True
        seen.add(id(current))
        current = current.__cause__ or getattr(current, "__context__", None)
    text = str(error)
    return all(marker in text for marker in (
        "migration_phase_rollback_migration_PS-RESUME-PUBLICATION-001_batch_1_failed",
        "migration_file_PS-RESUME-PUBLICATION-001_publication_rollback.sql_failed",
        "Rollback refused: publication state is populated.",
    ))


def parse_lockfile_sha256_digests(lockfile: Path) -> set[str]:
    digests = set()
    for match in re.finditer(r"--hash=sha256:([0-9a-f]{64})", lockfile.read_text(encoding="utf-8")):
        digests.add(match.group(1))
    if not digests:
        raise EngineProofError("lockfile_hashes_missing")
    return digests


def verify_downloaded_wheelhouse(wheelhouse: Path, lockfile: Path | None = None) -> dict[str, Any]:
    """Independently hash downloaded bytes. Distinct from PyPI published metadata."""

    lockfile = lockfile or PROOF_CLIENT_LOCKFILE
    expected = parse_lockfile_sha256_digests(lockfile)
    files = [path for path in wheelhouse.iterdir() if path.is_file()]
    if not files:
        raise EngineProofError("wheelhouse_empty")
    found = {hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    if found != expected:
        raise EngineProofError("wheelhouse_hash_mismatch")
    return {
        "downloaded_bytes_independently_verified": True,
        "artifact_count": len(files),
        "source": "downloaded_bytes",
    }


def prepare_hashed_wheelhouse(
    dest: Path,
    lockfile: Path | None = None,
    runner=None,
) -> Path:
    """Network-capable hashed pip download for Linux CPython 3.12 wheels."""

    lockfile = lockfile or PROOF_CLIENT_LOCKFILE
    dest.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--require-hashes",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--python-version",
        "3.12",
        "--implementation",
        "cp",
        "--platform",
        "manylinux_2_28_x86_64",
        "--platform",
        "manylinux_2_17_x86_64",
        "--platform",
        "manylinux2014_x86_64",
        "--only-binary",
        ":all:",
        "--dest",
        str(dest),
        "-r",
        str(lockfile),
    ]
    completed = (runner or subprocess.run)(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=PROOF_COMMAND_TIMEOUT_SECONDS,
    )
    if getattr(completed, "returncode", 1) != 0:
        raise EngineProofError("wheelhouse_download_failed")
    verify_downloaded_wheelhouse(dest, lockfile)
    return dest


def _json_command(**fields: Any) -> str:
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def seed_publication_owner(
    connection,
    *,
    auth_subject: str = "proof-owner-a",
    entry_key: str = PROOF_ENTRY_KEY,
) -> dict[str, Any]:
    """Insert the synthetic owner, profile, canonical role, policy, and permissions."""

    created = execute_procedure(
        connection,
        "usp_UpsertAppUserFromAuth",
        [
            ("@AuthProvider", "test"),
            ("@AuthIssuer", "https://proof.peerslate.example"),
            ("@AuthSubject", auth_subject),
            ("@Email", None),
            ("@DisplayName", "Proof Owner A"),
            ("@ProfileImageUrl", None),
            ("@TimezoneName", None),
        ],
    )
    if not created or not created[0].get("user_key"):
        raise EngineProofError("seed_owner_missing")
    user_key = str(created[0]["user_key"])
    command_id = "00000000-0000-4000-8000-0000000000aa"
    execute_procedure(
        connection,
        "usp_CommitLivingResumeCommandForOwner",
        [
            ("@UserKey", user_key),
            ("@CommandId", command_id),
            (
                "@CommandJson",
                _json_command(
                    command_id=command_id,
                    type="create_role",
                    record_key=entry_key,
                    parent_key=None,
                    expected_version=None,
                    values={
                        "role_title": "Lead",
                        "employer_name": "PeerSlate",
                        "location_text": None,
                        "summary": PROOF_SEED_SUMMARY,
                        "start_date": None,
                        "end_date": None,
                        "date_precision": "month",
                        "employment_type": "full_time",
                        "current_role": False,
                    },
                ),
            ),
        ],
    )
    execute_procedure(
        connection,
        "usp_CommitEntryPolicyCommandForOwner",
        _commit_parameters(
            user_key,
            {
                "request_id": "00000000-0000-4000-8000-0000000000b1",
                "json": _json_command(
                    type="create",
                    entry_key=entry_key,
                    canonical_type="role",
                    values={"role_title": "Lead", "employer_name": "PeerSlate"},
                ),
            },
        ),
    )
    execute_procedure(
        connection,
        "usp_CommitEntryPolicyCommandForOwner",
        _commit_parameters(
            user_key,
            {
                "request_id": "00000000-0000-4000-8000-0000000000b2",
                "json": _json_command(
                    type="change_permissions",
                    entry_key=entry_key,
                    expected_access_revision=1,
                    permissions={"resume_display": True, "visitor_ai": False},
                ),
            },
        ),
    )
    state = capture_publication_state(connection)
    if not state.get("owner_present") or not state.get("canonical_summary"):
        raise EngineProofError("missing_seed_rows")
    if state.get("canonical_summary") != PROOF_SEED_SUMMARY:
        raise EngineProofError("missing_seed_rows")
    if not state.get("resume_display") or state.get("visitor_ai"):
        raise EngineProofError("missing_seed_rows")
    return {"user_key": user_key, "entry_key": entry_key, "state": state}


def seed_second_proof_owner(connection) -> str:
    created = execute_procedure(
        connection,
        "usp_UpsertAppUserFromAuth",
        [
            ("@AuthProvider", "test"),
            ("@AuthIssuer", "https://proof.peerslate.example"),
            ("@AuthSubject", "proof-owner-b"),
            ("@Email", None),
            ("@DisplayName", "Proof Owner B"),
            ("@ProfileImageUrl", None),
            ("@TimezoneName", None),
        ],
    )
    if not created or not created[0].get("user_key"):
        raise EngineProofError("second_owner_missing")
    user_key = str(created[0]["user_key"])
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM dbo.app_users AS u JOIN dbo.member_profiles AS p ON p.user_id = u.id WHERE u.user_key = ? AND u.active = 1 AND p.active = 1",
            (user_key,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if not row or int(row[0] or 0) != 1:
        raise EngineProofError("second_owner_profile_missing")
    execute_procedure(
        connection,
        "usp_CommitLivingResumeCommandForOwner",
        [
            ("@UserKey", user_key),
            ("@CommandId", "00000000-0000-4000-8000-0000000000f1"),
            ("@CommandJson", _json_command(
                command_id="00000000-0000-4000-8000-0000000000f1",
                type="create_role", record_key=PROOF_FOREIGN_ENTRY_KEY,
                parent_key=None, expected_version=None,
                values={"role_title": "Private", "employer_name": "Proof B",
                        "summary": "Owner B only.", "date_precision": "month",
                        "employment_type": "full_time", "current_role": False},
            )),
        ],
    )
    execute_procedure(
        connection, "usp_CommitEntryPolicyCommandForOwner",
        _commit_parameters(user_key, {
            "request_id": "00000000-0000-4000-8000-0000000000f2",
            "json": _json_command(type="create", entry_key=PROOF_FOREIGN_ENTRY_KEY,
                                  canonical_type="role", values={"role_title": "Private"}),
        }),
    )
    for index, entry_key in enumerate(PROOF_FOREIGN_EXTRA_ENTRY_KEYS, start=3):
        command_id = f"00000000-0000-4000-8000-0000000000f{index}"
        policy_request_id = f"00000000-0000-4000-8000-0000000000f{index + 2}"
        execute_procedure(
            connection, "usp_CommitLivingResumeCommandForOwner",
            [("@UserKey", user_key), ("@CommandId", command_id),
             ("@CommandJson", _json_command(
                 command_id=command_id, type="create_role", record_key=entry_key,
                 parent_key=None, expected_version=None,
                 values={"role_title": f"Private {index}", "employer_name": "Proof B",
                         "summary": f"Owner B private {index}.", "date_precision": "month",
                         "employment_type": "full_time", "current_role": False},
             ))],
        )
        execute_procedure(
            connection, "usp_CommitEntryPolicyCommandForOwner",
            _commit_parameters(user_key, {
                "request_id": policy_request_id,
                "json": _json_command(type="create", entry_key=entry_key,
                                      canonical_type="role", values={"role_title": f"Private {index}"}),
            }),
        )
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM dbo.entry_policy_records AS policy JOIN dbo.member_profiles AS p ON p.profile_id = policy.owner_profile_id JOIN dbo.app_users AS u ON u.id = p.user_id WHERE u.user_key = ? AND policy.entry_key = ? AND policy.lifecycle = N'active'",
            (user_key, PROOF_FOREIGN_ENTRY_KEY),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if not row or int(row[0] or 0) != 1:
        raise EngineProofError("foreign_entry_seed_missing")
    return user_key


def seed_proof_catalog_asset(connection) -> None:
    """Insert one synthetic catalog asset into the disposable proof database."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT dbo.resume_catalog_assets (asset_id, asset_version, content_sha256, label, category, tags, width, height, origin, lifecycle) VALUES (?, 1, ?, N'Proof illustration', N'proof', N'', 1, 1, N'generated_illustration', N'active')",
            (PROOF_CATALOG_ASSET_ID, "c" * 64),
        )
        connection.commit()
        cursor.execute(
            "SELECT lifecycle FROM dbo.resume_catalog_assets WHERE asset_id = ? AND asset_version = 1",
            (PROOF_CATALOG_ASSET_ID,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if not row or row[0] != "active":
        raise EngineProofError("catalog_seed_missing")


def proof_entry_count(connection, user_key: str | None = None) -> int:
    cursor = connection.cursor()
    try:
        if user_key is None:
            cursor.execute("SELECT COUNT(*) FROM dbo.entry_policy_records")
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.entry_policy_records AS policy JOIN dbo.member_profiles AS p ON p.profile_id = policy.owner_profile_id JOIN dbo.app_users AS u ON u.id = p.user_id WHERE u.user_key = ?",
                (user_key,),
            )
        row = cursor.fetchone()
    finally:
        cursor.close()
    return int(row[0] or 0) if row else -1


def publish_reviewed(connection, user_key: str, request_id: str, digest: str) -> None:
    execute_procedure(
        connection,
        "usp_CommitResumePublicationCommandForOwner",
        _commit_parameters(
            user_key,
            {
                "request_id": request_id,
                "json": _json_command(
                    type="publish",
                    reviewed_digest=digest,
                    slug=PROOF_PUBLIC_SLUG,
                    media={
                        "portrait": {
                            "active": True,
                            "source_kind": "upload",
                            "source_key": "synthetic-portrait",
                            "asset_version": 1,
                            "content_sha256": "e" * 64,
                        },
                        "illustration": {
                            "active": True,
                            "source_kind": "generated_illustration",
                            "source_key": PROOF_CATALOG_ASSET_ID,
                            "asset_version": 1,
                            "content_sha256": "c" * 64,
                        },
                    },
                ),
            },
        ),
    )


def correct_publication_wording(
    connection,
    user_key: str,
    request_id: str,
    summary: str,
    *,
    expected_content_version: int,
    expected_access_revision: int,
) -> None:
    """Publication correct path: ApplyCanonicalInternal, never Core's unknown command."""

    execute_procedure(
        connection,
        "usp_CommitResumePublicationCommandForOwner",
        _commit_parameters(
            user_key,
            {
                "request_id": request_id,
                "json": _json_command(
                    type="correct",
                    entry_key=PROOF_ENTRY_KEY,
                    expected_content_version=expected_content_version,
                    expected_access_revision=expected_access_revision,
                    values={
                        "summary": summary,
                        "wording": summary,
                        "role_title": "Lead",
                        "employer_name": "PeerSlate",
                    },
                ),
            },
        ),
    )


def capture_publication_state(connection) -> dict[str, Any]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT sharing_enabled, sharing_epoch, publication_revision, current_revision, public_slug
              FROM dbo.resume_sharing_state
             WHERE owner_profile_id IN (SELECT owner_profile_id FROM dbo.entry_policy_records WHERE entry_key = ?)
            """,
            (PROOF_ENTRY_KEY,),
        )
        sharing = cursor.fetchall()
        cursor.execute(
            """
            SELECT chapter.summary, chapter.approved_wording, policy.resume_display, policy.visitor_ai,
                   policy.content_version, policy.access_revision, policy.lifecycle
              FROM dbo.career_chapters AS chapter
              JOIN dbo.entry_policy_records AS policy
                ON policy.canonical_key = chapter.chapter_key
               AND policy.owner_profile_id = chapter.owner_profile_id
             WHERE policy.entry_key = ?
            """,
            (PROOF_ENTRY_KEY,),
        )
        canonical = cursor.fetchall()
        cursor.execute(
            """
            SELECT r.display_json, r.visitor_ai_json, r.publication_revision, r.media_json
              FROM dbo.resume_publication_revisions AS r
              JOIN dbo.resume_sharing_state AS s
                ON s.owner_profile_id = r.owner_profile_id
               AND s.current_revision = r.publication_revision
             WHERE s.owner_profile_id IN (SELECT owner_profile_id FROM dbo.entry_policy_records WHERE entry_key = ?)
            """,
            (PROOF_ENTRY_KEY,),
        )
        publication = cursor.fetchall()
        cursor.execute(
            """
            SELECT command_receipt_id, request_id, command_type, outcome
              FROM dbo.resume_publication_receipts
             WHERE owner_profile_id IN (SELECT owner_profile_id FROM dbo.entry_policy_records WHERE entry_key = ?)
             ORDER BY command_receipt_id
            """,
            (PROOF_ENTRY_KEY,),
        )
        receipts = cursor.fetchall()
        cursor.execute(
            """
            SELECT outbox_id, event_type, publication_revision
              FROM dbo.resume_publication_outbox
             WHERE owner_profile_id IN (SELECT owner_profile_id FROM dbo.entry_policy_records WHERE entry_key = ?)
             ORDER BY outbox_id
            """,
            (PROOF_ENTRY_KEY,),
        )
        outbox = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM dbo.app_users")
        users = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) FROM dbo.member_profiles")
        profiles = cursor.fetchall()
        cursor.execute(
            "SELECT lifecycle FROM dbo.resume_catalog_assets WHERE asset_id = ? AND asset_version = 1",
            (PROOF_CATALOG_ASSET_ID,),
        )
        catalog = cursor.fetchall()
        cursor.execute(
            "SELECT d.draft_version FROM dbo.resume_drafts AS d JOIN dbo.entry_policy_records AS p ON p.owner_profile_id = d.owner_profile_id WHERE p.entry_key = ?",
            (PROOF_ENTRY_KEY,),
        )
        draft = cursor.fetchall()
    finally:
        cursor.close()

    sharing_row = _first_row(sharing)
    canonical_row = _first_row(canonical)
    publication_row = _first_row(publication)
    return {
        "sharing": [tuple(row) for row in sharing or []],
        "sharing_enabled": _truthy(None if sharing_row is None else sharing_row[0]),
        "sharing_epoch": None if sharing_row is None else sharing_row[1],
        "publication_revision": None if sharing_row is None else sharing_row[2],
        "current_revision": None if sharing_row is None else sharing_row[3],
        "public_slug": None if sharing_row is None else sharing_row[4],
        "canonical_summary": None if canonical_row is None else canonical_row[0],
        "approved_wording": None if canonical_row is None else canonical_row[1],
        "resume_display": _truthy(None if canonical_row is None else canonical_row[2]),
        "visitor_ai": _truthy(None if canonical_row is None else canonical_row[3]),
        "content_version": None if canonical_row is None else canonical_row[4],
        "access_revision": None if canonical_row is None else canonical_row[5],
        "lifecycle": None if canonical_row is None else canonical_row[6],
        "display_json": None if publication_row is None else publication_row[0],
        "visitor_ai_json": None if publication_row is None else publication_row[1],
        "media_json": None if publication_row is None else publication_row[3],
        "catalog_lifecycle": None if not catalog else catalog[0][0],
        "draft_version": None if not draft else draft[0][0],
        "receipts": [tuple(row) for row in receipts or []],
        "outbox": [tuple(row) for row in outbox or []],
        "owner_present": _count(users) >= 1 and _count(profiles) >= 1,
    }


def capture_foreign_policy_state(connection) -> list[tuple[Any, ...]]:
    """Privileged observer for the synthetic second owner's entry."""

    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT entry_key, lifecycle, access_revision FROM dbo.entry_policy_records WHERE entry_key = ?",
            (PROOF_FOREIGN_ENTRY_KEY,),
        )
        return [tuple(row) for row in cursor.fetchall()]
    finally:
        cursor.close()


def _first_row(rows):
    if not rows:
        return None
    return rows[0]


def _count(rows) -> int:
    if not rows:
        return 0
    value = rows[0][0] if not isinstance(rows[0], dict) else list(rows[0].values())[0]
    return int(value or 0)


def _truthy(value) -> bool:
    return value not in (0, "0", False, None)


def _capture_owner_state(connection) -> dict[str, Any]:
    return capture_publication_state(connection)


def production_mssql_python_connection(
    *,
    host: str,
    database: str,
    user: str,
    password: str,
    timeout_seconds: int = 30,
):
    """Open mssql_python against a verified job-local disposable database.

    A client-supplied DSN is never the resource identity.
    """

    if not host or host in {"localhost", "127.0.0.1", "::1"}:
        raise EngineProofError("sql_host_not_job_local")
    if database in FORBIDDEN_PRODUCTION_DATABASES:
        raise EngineProofError("production_sql_forbidden")
    if database not in {PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE}:
        raise EngineProofError("sql_database_not_proof_owned")
    from mssql_python import Connection, SQL_ATTR_LOGIN_TIMEOUT

    if (type(timeout_seconds) is not int or timeout_seconds <= 0
            or timeout_seconds > PROOF_COMMAND_TIMEOUT_SECONDS):
        raise EngineProofError("sql_timeout_unbounded")
    connection = Connection(
        f"Server={host};Database={database};UID={user};PWD={password};Encrypt=yes;"
        "TrustServerCertificate=yes;",
        autocommit=True,
        timeout=timeout_seconds,
        attrs_before={SQL_ATTR_LOGIN_TIMEOUT: timeout_seconds},
    )
    try:
        if connection.autocommit is not True or connection.timeout != timeout_seconds:
            raise EngineProofError("sql_connection_not_bounded")
    except Exception:
        connection.close()
        raise
    return connection


def connect_from_client_environment(identity: str):
    """Open SQL from inside the isolated client using env-delivered secrets."""

    password = os.environ.get("MSSQL_SA_PASSWORD", "")
    host = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_HOST", "").strip()
    database = os.environ.get(
        "PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE", PROOF_EMPTY_DATABASE
    ).strip() or PROOF_EMPTY_DATABASE
    suffix = str(identity).rsplit(":", 1)[-1]
    if suffix in {PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE}:
        database = suffix
    if not password:
        raise EngineProofError("sql_secret_missing")
    refuse_client_supplied_dsn(
        identity if identity.startswith(("Driver=", "Server=", "DSN=")) else None
    )
    return production_mssql_python_connection(
        host=host,
        database=database,
        user="sa",
        password=password,
    )


def apply_sql_script(connection, sql_text: str) -> None:
    cursor = connection.cursor()
    phase = "execute"
    try:
        cursor.execute(sql_text)
        # A migration is a batch. Surface errors from later statements before
        # reporting success or committing a driver-owned transaction.
        phase = "drain"
        _fetch_procedure_result_sets(cursor)
        if hasattr(connection, "commit"):
            phase = "commit"
            connection.commit()
    except Exception as error:
        # Capture diagnostics before close clears the statement handle. The
        # pinned driver's nextset error can contain only a generic SQLSTATE.
        diagnostics = [str(error)]
        diagnostics.extend(str(item) for item in (getattr(cursor, "messages", None) or [])[:16])
        if getattr(cursor, "hstmt", None):
            try:
                from mssql_python import ddbc_bindings
                diagnostics.extend(str(item) for item in ddbc_bindings.DDBCSQLGetAllDiagRecords(cursor.hstmt)[:16])
            except Exception:
                # Diagnostic availability must never replace the actual failure.
                pass
        secret = os.environ.get("MSSQL_SA_PASSWORD", "")
        detail = sanitize_proof_error(RuntimeError(" | ".join(diagnostics)), (secret,) if secret else ())
        raise EngineProofError(f"sql_batch_{phase}_failed: {detail[:8192]}") from error
    finally:
        cursor.close()


def apply_sql_file(connection, path: Path) -> None:
    try:
        apply_sql_script(connection, path.read_text(encoding="utf-8"))
    except Exception as error:
        raise EngineProofError(f"migration_file_{path.name}_failed: {error}") from error


def execute_procedure(connection, procedure_name: str, parameters: list[tuple[str, Any]]):
    assignments = ", ".join(f"{name} = ?" for name, _value in parameters)
    statement = f"EXEC dbo.{procedure_name}"
    if assignments:
        statement = f"{statement} {assignments}"
    cursor = connection.cursor()
    try:
        cursor.execute(statement, tuple(value for _name, value in parameters))
        sets = _fetch_procedure_result_sets(cursor)
    finally:
        cursor.close()
    if not sets:
        return []
    return sets[-1]


def _fetch_procedure_result_sets(cursor) -> list[list[dict[str, Any]]]:
    result_sets: list[list[dict[str, Any]]] = []
    while True:
        description = getattr(cursor, "description", None)
        if description is not None:
            names = [column[0] for column in description]
            rows = []
            for row in cursor.fetchall() or []:
                if isinstance(row, dict):
                    rows.append(row)
                else:
                    rows.append(dict(zip(names, row)))
            result_sets.append(rows)
        if not cursor.nextset():
            break
    return result_sets


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_publication_migration_closure(root: Path | None = None) -> list[dict[str, Any]]:
    """Topological registry closure required by the accepted SQL resource plan."""

    root = root or Path(__file__).resolve().parents[1]
    registry_path = root / "SQL FIles" / "Migrations" / "registry.json"
    document = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = document.get("migrations") or []
    by_id = {item["id"]: item for item in entries}
    missing = [item for item in REQUIRED_PUBLICATION_CLOSURE_IDS if item not in by_id]
    if missing:
        raise EngineProofError(f"incomplete_migration_closure:{','.join(missing)}")
    ordered = [item for item in entries if item["id"] in REQUIRED_PUBLICATION_CLOSURE_IDS]
    if {item["id"] for item in ordered} != set(REQUIRED_PUBLICATION_CLOSURE_IDS):
        raise EngineProofError("incomplete_migration_closure")
    files = []
    for item in ordered:
        forward = root / item["forward"]
        rollback = root / item["rollback"]
        verify_name = Path(item["forward"]).name.replace(".sql", "_verify.sql")
        verify = root / "SQL FIles" / "Verification" / verify_name
        record = {
            "id": item["id"],
            "forward": item["forward"],
            "forward_sha256": _sha256_file(forward),
            "rollback": item["rollback"],
            "rollback_sha256": _sha256_file(rollback),
        }
        if verify.exists():
            record["verify"] = verify.relative_to(root).as_posix()
            record["verify_sha256"] = _sha256_file(verify)
        files.append(record)
    return files


def run_migration_closure(
    apply_forward,
    apply_rollback,
    verify,
    ordered_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    expected = [item["id"] for item in resolve_publication_migration_closure()]
    if list(ordered_ids or []) != expected:
        raise EngineProofError("incomplete_migration_closure")
    forward_evidence = apply_forward()
    verify()
    apply_rollback()
    apply_forward()
    verify()
    return {
        "closed": True,
        "reapplied": True,
        "ids": list(ordered_ids),
        "lock_intent": CLIENT_LOCK_INTENT,
        "order": ["forward", "verify", "rollback", "forward", "verify"],
        "capture_rollback": (forward_evidence or {}).get("capture_rollback"),
    }


def assert_executed_mandatory_cases(executed: dict[str, str]) -> None:
    if not executed:
        raise EngineProofError("mandatory_cases_none_executed")
    missing = [case for case in MANDATORY_ENGINE_CASES if case not in executed]
    skipped = [case for case, status in executed.items() if status == "skip"]
    failed = [case for case, status in executed.items() if status != "pass"]
    if missing:
        raise EngineProofError("mandatory_cases_missing:" + ",".join(missing))
    if skipped:
        raise EngineProofError("mandatory_cases_skipped:" + ",".join(skipped))
    if failed:
        raise EngineProofError("mandatory_cases_failed:" + ",".join(failed))
    if len(executed) < len(MANDATORY_ENGINE_CASES):
        raise EngineProofError("mandatory_cases_none_executed")


class ProofDatabaseAdapter:
    """Production repository adapter over the proof connection/procedure helper."""

    def __init__(self, connection) -> None:
        self.connection = connection

    def _rows(self, procedure: str, parameters: list[tuple[str, Any]]):
        bound = []
        for name, value in parameters:
            if name == "@CommandJson" and isinstance(value, dict):
                bound.append((name, json.dumps(value, ensure_ascii=False, separators=(",", ":"))))
            else:
                bound.append((name, value))
        try:
            return execute_procedure(self.connection, procedure, bound)
        except EngineProofError:
            raise
        except Exception as error:
            raise ValueError(str(error)) from error

    def first_row(self, procedure: str, parameters: list[tuple[str, Any]]):
        rows = self._rows(procedure, parameters)
        if not rows:
            return None
        return rows[0]

    def first_result(self, procedure: str, parameters: list[tuple[str, Any]]):
        return self._rows(procedure, parameters)

    def last_row(self, procedure: str, parameters: list[tuple[str, Any]]):
        rows = self._rows(procedure, parameters)
        if not rows:
            return None
        return rows[-1]


def _database_connect(connect: Callable[[str], Any], resource_identity: str, database: str):
    def opener(identity: str | None = None):
        target = identity or f"{resource_identity}:{database}"
        if ":" not in str(target).split("docker:", 1)[-1] and database:
            target = f"{resource_identity}:{database}"
        previous = os.environ.get("PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE")
        os.environ["PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE"] = database
        try:
            return connect(target)
        finally:
            if previous is None:
                os.environ.pop("PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE", None)
            else:
                os.environ["PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE"] = previous

    return opener


def _fail_after(runtime, step: str) -> None:
    target = getattr(runtime, "fail_after", None) or os.environ.get(
        "PEERSLATE_RESUME_PUBLICATION_FAIL_AFTER", ""
    )
    if target == step:
        raise EngineProofError(f"injected_failure:{step}")


def _resource_present(runtime, name: str) -> bool:
    exists = getattr(runtime, "exists", None)
    if callable(exists):
        return bool(exists(name))
    try:
        runtime.inspect(name)
        return True
    except EngineProofError as error:
        if str(error).startswith("docker_resource_not_found:"):
            return False
        raise


def _timeout_docker(runner, args: list[str], extra_env: dict[str, str] | None, timeout: int):
    env = None
    if extra_env is not None:
        env = os.environ.copy()
        env.update(extra_env)
    try:
        completed = runner(
            ["docker", *args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise EngineProofError("command_timeout") from error
    if not isinstance(completed, subprocess.CompletedProcess):
        raise EngineProofError("docker_cli_failed")
    return completed


def _run_interruptible_docker_command(args, *, capture_output, text, check, env, timeout):
    """Reap the CLI child promptly when normal cancellation interrupts Python."""

    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, env=env,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise
    return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)


def production_publication_stack(connection):
    from services.entry_policy_repository import SqlEntryPolicyRepository
    from services.entry_policy_service import EntryPolicyService
    from services.resume_publication_repository import SqlResumePublicationRepository
    from services.resume_publication_service import ResumePublicationService

    repository = SqlResumePublicationRepository(ProofDatabaseAdapter(connection))
    service = ResumePublicationService(sql_repository=repository, repository=repository)
    service.policy_service = EntryPolicyService(
        repository=SqlEntryPolicyRepository(ProofDatabaseAdapter(connection))
    )
    return repository, service


def provision_proof_principals(connection) -> None:
    """Create only contained users in the named disposable proof database."""

    statements = [
        "IF DATABASE_PRINCIPAL_ID(N'peerslate_app') IS NULL CREATE USER [peerslate_app] WITHOUT LOGIN",
        "IF DATABASE_PRINCIPAL_ID(N'peerslate_restricted') IS NULL CREATE USER [peerslate_restricted] WITHOUT LOGIN",
    ]
    from scripts.configure_resume_publication_sql_authority import DENIED_INTERNAL, PROPOSED_PROCEDURES

    for name in PROPOSED_PROCEDURES:
        statements.append(f"GRANT EXECUTE ON dbo.[{name}] TO [peerslate_app]")
    for name in DENIED_INTERNAL:
        statements.append(f"DENY EXECUTE ON dbo.[{name}] TO [peerslate_app]")
    statements.append("DENY EXECUTE ON dbo.[usp_CommitResumePublicationCommandForOwner] TO [peerslate_restricted]")
    for statement in statements:
        apply_sql_script(connection, statement)


def _effective_principal(connection, principal: str, action: Callable[[], None]) -> None:
    if principal not in {"peerslate_app", "peerslate_restricted"}:
        raise EngineProofError("proof_principal_unknown")
    cursor = connection.cursor()
    impersonated = False
    try:
        cursor.execute(f"EXECUTE AS USER = '{principal}'")
        impersonated = True
        cursor.execute("SELECT USER_NAME()")
        row = cursor.fetchone()
        if not row or str(row[0]) != principal:
            raise EngineProofError("proof_principal_not_effective")
        action()
    finally:
        if impersonated:
            cursor.execute("REVERT")
        cursor.close()


def _expect_sql_permission_denial(action: Callable[[], None]) -> None:
    try:
        action()
    except Exception as error:
        text = str(error).lower()
        if "permission denied" in text or "permission was denied" in text or "(229)" in text:
            return
        raise EngineProofError(
            "proof_unexpected_principal_error:" + sanitize_proof_error(error)[:1024]
        ) from error
    raise EngineProofError("proof_principal_allowed")


def assert_application_principal_permissions(connection, principal: str) -> dict[str, Any]:
    """Effective EXECUTE grants and DENY on internal helpers for the proof principal."""

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT permission_name, state_desc, OBJECT_NAME(major_id) AS object_name
          FROM sys.database_permissions
         WHERE USER_NAME(grantee_principal_id) = ?
        """,
        (principal,),
    )
    rows = cursor.fetchall()
    cursor.close()
    granted = {}
    denied_internal = []
    for row in rows or []:
        if not row:
            continue
        perm = str(row[0] or "")
        state = str(row[1] or "")
        name = str(row[2] or "")
        if not name:
            continue
        granted[name] = {"permission": perm, "state": state}
        internal = name.startswith("usp_ResumePublication") and name.endswith("Internal")
        core = name.endswith("Core")
        if (internal or core) and state.upper() == "DENY":
            denied_internal.append(name)
    if not denied_internal:
        raise EngineProofError("application_principal_missing_internal_deny")
    from scripts.configure_resume_publication_sql_authority import PROPOSED_PROCEDURES

    missing_grants = [name for name in PROPOSED_PROCEDURES
                      if granted.get(name, {}).get("state", "").upper() != "GRANT"]
    if missing_grants:
        raise EngineProofError("application_principal_missing_grants")
    return {
        "granted": granted,
        "internal_denied_present": True,
        "internal_denied": sorted(set(denied_internal)),
        "principal": principal,
        "lock_intent": CLIENT_LOCK_INTENT,
    }


def _commit_parameters(owner: str, command: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("@UserKey", owner),
        ("@RequestId", command["request_id"]),
        ("@CommandJson", command["json"]),
    ]


def _command_type(command: dict[str, Any]) -> str:
    raw = command.get("json") or "{}"
    if isinstance(raw, dict):
        return str(raw.get("type") or "")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("type") or "")


def classify_sql_commit_error(error: BaseException) -> str:
    """Map known SQL publication conflicts. Unexpected errors do not pass."""

    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts = [str(current)]
        parts.extend(str(item) for item in getattr(current, "args", ()) if item is not None)
        text = " ".join(parts).lower()
        if (
            "54022" in text
            or "52205" in text
            or "1205" in text
            or "1222" in text
            or "54023" in text
            or "54026" in text
            or "54027" in text
            or "54028" in text
            or "54029" in text
            or "already used a different payload" in text
            or "the publication changed" in text
            or "permission denied" in text
        ):
            return "conflict"
        current = current.__cause__ or getattr(current, "__context__", None)
    raise EngineProofError("race_unexpected_error")


def _sharing_enabled(state: dict[str, Any]) -> bool:
    if "sharing_enabled" in state:
        if not state.get("owner_present", True) and not state.get("sharing"):
            raise EngineProofError("race_invalid_final_state")
        return bool(state.get("sharing_enabled"))
    rows = state.get("sharing") or []
    if not rows:
        raise EngineProofError("race_invalid_final_state")
    return _truthy(rows[0][0])


def _publication_revision(state: dict[str, Any]) -> int:
    if state.get("publication_revision") is not None:
        return int(state["publication_revision"])
    rows = state.get("sharing") or []
    if not rows or len(rows[0]) < 3:
        raise EngineProofError("race_invalid_final_state")
    try:
        return int(rows[0][2] or 0)
    except (TypeError, ValueError) as error:
        raise EngineProofError("race_invalid_final_state") from error


def _serializable_winner(state: dict[str, Any], candidates: set[str]) -> str | None:
    for row in reversed(state.get("outbox") or []):
        event = row[1] if len(row) > 1 else row[0]
        if event in candidates:
            return str(event)
    return None


def _json_contains(payload, needle: str) -> bool:
    if payload is None:
        return False
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", "replace")
    return needle in str(payload)


def render_guest_publication_html(publication: dict[str, Any]) -> str:
    """Render the public block of the shipped Resume template from a SQL guest read."""

    from jinja2 import Environment, FileSystemLoader, select_autoescape

    root = Path(__file__).resolve().parents[1]
    environment = Environment(
        loader=FileSystemLoader(root / "templates"),
        autoescape=select_autoescape(("html",)),
    )
    template = environment.get_template("resume_publication.html")
    context = template.new_context(
        {"is_public_reader": True, "public_publication": publication}
    )
    return "".join(template.blocks["content"](context))


def assert_race_pair_state(
    pair: str,
    outcomes: tuple[str, ...],
    command_a: dict[str, Any],
    command_b: dict[str, Any],
    state: dict[str, Any],
) -> None:
    if pair not in PERMITTED_RACE_PAIRS:
        raise EngineProofError("race_unknown_pair")
    if any(item not in PERMITTED_RACE_OUTCOMES for item in outcomes):
        raise EngineProofError("race_unexpected_error")
    if "committed" not in outcomes:
        raise EngineProofError("race_both_failed")
    enabled = _sharing_enabled(state)
    revision = _publication_revision(state)
    types = (_command_type(command_a), _command_type(command_b))
    if pair == "publish_versus_correction":
        if "publish" not in types or "correct" not in types:
            raise EngineProofError("race_invalid_setup")
        if not enabled or revision < 1:
            raise EngineProofError("race_invalid_final_state")
        if not state.get("resume_display"):
            raise EngineProofError("race_invalid_final_state")
        correct_index = types.index("correct")
        if outcomes[correct_index] == "committed":
            if state.get("canonical_summary") != PROOF_RACE_SUMMARY:
                raise EngineProofError("correction_wording_unchanged")
            if not _json_contains(state.get("display_json"), PROOF_RACE_SUMMARY):
                raise EngineProofError("correction_wording_unchanged")
        else:
            if state.get("canonical_summary") == PROOF_RACE_SUMMARY:
                raise EngineProofError("race_invalid_final_state")
            if state.get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
                raise EngineProofError("race_invalid_final_state")
        return
    if pair == "publish_versus_policy_restriction":
        if "publish" not in types or "change_permissions" not in types:
            raise EngineProofError("race_invalid_setup")
        restrict_index = types.index("change_permissions")
        restricted = outcomes[restrict_index] == "committed"
        if bool(state.get("resume_display")) == restricted:
            raise EngineProofError("race_invalid_final_state")
        if restricted and _json_contains(state.get("display_json"), state.get("canonical_summary") or PROOF_CORRECTED_SUMMARY):
            raise EngineProofError("race_policy_leaked_wording")
        if not restricted and (not enabled or not _json_contains(state.get("display_json"), state.get("canonical_summary") or PROOF_CORRECTED_SUMMARY)):
            raise EngineProofError("race_invalid_final_state")
        return
    if pair in {
        "publish_versus_delete",
        "publish_versus_restore",
        "publish_versus_draft_change",
        "publish_versus_media_restrict",
        "publish_versus_catalog_withdraw",
    }:
        if "publish" not in types:
            raise EngineProofError("race_invalid_setup")
        if "committed" not in outcomes:
            raise EngineProofError("race_both_failed")
        if pair == "publish_versus_delete":
            deleted = outcomes[types.index("delete")] == "committed"
            if (state.get("lifecycle") == "deleted") != deleted:
                raise EngineProofError("race_invalid_final_state")
            if deleted and (state.get("resume_display") or _json_contains(state.get("display_json"), state.get("canonical_summary") or PROOF_CORRECTED_SUMMARY)):
                raise EngineProofError("race_deleted_wording_visible")
        if pair == "publish_versus_restore":
            restored = outcomes[types.index("restore")] == "committed"
            if (state.get("lifecycle") == "active") != restored:
                raise EngineProofError("race_invalid_final_state")
            if restored and (state.get("resume_display") or state.get("visitor_ai")
                             or _json_contains(state.get("display_json"), PROOF_ENTRY_KEY)
                             or _json_contains(state.get("visitor_ai_json"), PROOF_ENTRY_KEY)):
                raise EngineProofError("race_restore_not_private")
        if pair == "publish_versus_draft_change":
            if "save_item" not in types or not state.get("canonical_summary"):
                raise EngineProofError("race_invalid_final_state")
            if outcomes[types.index("save_item")] == "committed" and state.get("draft_version") is None:
                raise EngineProofError("race_draft_not_saved")
        if pair == "publish_versus_media_restrict":
            if "media_restrict" not in types:
                raise EngineProofError("race_invalid_setup")
            media = json.loads(state.get("media_json") or "{}")
            active = bool((media.get("portrait") or {}).get("active"))
            if active == (outcomes[types.index("media_restrict")] == "committed"):
                raise EngineProofError("race_media_final_state")
        if pair == "publish_versus_catalog_withdraw":
            if "catalog_withdraw" not in types:
                raise EngineProofError("race_invalid_setup")
            withdrawn = outcomes[types.index("catalog_withdraw")] == "committed"
            if (state.get("catalog_lifecycle") == "withdrawn") != withdrawn:
                raise EngineProofError("race_catalog_final_state")
        return
    if "publish" not in types or "sharing_off" not in types:
        raise EngineProofError("race_invalid_setup")
    publish_index = types.index("publish")
    revoke_index = types.index("sharing_off")
    publish_committed = outcomes[publish_index] == "committed"
    revoke_committed = outcomes[revoke_index] == "committed"
    if publish_committed and not revoke_committed:
        if not enabled or revision < 1 or state.get("public_slug") != PROOF_PUBLIC_SLUG:
            raise EngineProofError("race_invalid_final_state")
        return
    if revoke_committed and not publish_committed:
        if enabled:
            raise EngineProofError("race_invalid_final_state")
        return
    winner = _serializable_winner(state, {"publish", "sharing_off"})
    if winner == "publish":
        if not enabled or state.get("public_slug") != PROOF_PUBLIC_SLUG:
            raise EngineProofError("race_invalid_final_state")
        return
    if winner == "sharing_off":
        if enabled:
            raise EngineProofError("race_invalid_final_state")
        return
    raise EngineProofError("race_invalid_final_state")


def run_two_connection_race(
    resource_identity: str,
    owner_a: str,
    owner_b: str,
    command_a: dict[str, Any],
    command_b: dict[str, Any],
    connect: Callable[[str], Any] | None = None,
    barrier: threading.Barrier | None = None,
    pair: str | None = None,
    observe: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Two connections, deterministic barrier, asserted permitted outcomes."""

    if connect is None:
        raise EngineProofError("job_local_connect_required")
    if resource_identity.startswith(("Driver=", "Server=", "DSN=")):
        raise EngineProofError("client_dsn_forbidden")
    if pair is not None and pair not in PERMITTED_RACE_PAIRS:
        raise EngineProofError("race_unknown_pair")
    gate = barrier or threading.Barrier(2, timeout=5)
    outcomes: list[str | None] = [None, None]
    errors: list[str | None] = [None, None]
    unexpected: list[BaseException] = []
    waits = {"count": 0}
    lock = threading.Lock()

    def worker(index: int, owner: str, command: dict[str, Any]) -> None:
        connection = None
        try:
            try:
                connection = connect(resource_identity)
                timeout_cursor = connection.cursor()
                try:
                    timeout_cursor.execute("SET LOCK_TIMEOUT 5000")
                finally:
                    timeout_cursor.close()
            except Exception as error:
                with lock:
                    unexpected.append(EngineProofError("race_connection_setup_failed"))
                    errors[index] = type(error).__name__
                    outcomes[index] = "unexpected"
                gate.abort()
                return
            with lock:
                waits["count"] += 1
            try:
                gate.wait()
            except threading.BrokenBarrierError:
                with lock:
                    unexpected.append(EngineProofError("race_barrier_timeout"))
                    outcomes[index] = "unexpected"
                return
            try:
                procedure = (
                    "usp_CommitResumeDraftCommandForOwner"
                    if _command_type(command) == "save_item"
                    else "usp_CommitResumePublicationCommandForOwner"
                )
                result = execute_procedure(
                    connection,
                    procedure,
                    _commit_parameters(owner, command),
                )
                if procedure == "usp_CommitResumeDraftCommandForOwner" and (
                    not result or not result[0].get("committed")
                ):
                    if result and result[0].get("outcome") in {"stale_draft", "idempotency_conflict"}:
                        outcomes[index] = "conflict"
                    else:
                        raise EngineProofError("race_draft_not_committed")
                else:
                    outcomes[index] = "committed"
            except Exception as error:
                try:
                    outcomes[index] = classify_sql_commit_error(error)
                    errors[index] = type(error).__name__
                except EngineProofError as classified:
                    unexpected.append(classified)
                    outcomes[index] = "unexpected"
                    errors[index] = type(error).__name__
        finally:
            try:
                if connection is not None:
                    connection.close()
            except Exception:
                pass

    threads = [
        threading.Thread(target=worker, args=(0, owner_a, command_a)),
        threading.Thread(target=worker, args=(1, owner_b, command_b)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=45)
        if thread.is_alive():
            raise EngineProofError("race_barrier_timeout")
    if waits["count"] < 2:
        raise EngineProofError("race_missing_interleaving")
    if unexpected:
        raise unexpected[0]
    if None in outcomes or "unexpected" in outcomes:
        raise EngineProofError("race_unexpected_error")
    finalized = (str(outcomes[0]), str(outcomes[1]))
    if any(item not in PERMITTED_RACE_OUTCOMES for item in finalized):
        raise EngineProofError("race_unexpected_error")
    if "committed" not in finalized:
        raise EngineProofError("race_both_failed")
    observer = observe or (_capture_owner_state if pair is not None else None)
    final_state = None
    if observer is not None:
        watcher = connect(resource_identity)
        try:
            final_state = observer(watcher)
        finally:
            try:
                watcher.close()
            except Exception:
                pass
        if pair is not None:
            assert_race_pair_state(pair, finalized, command_a, command_b, final_state)
    return {
        "owners": (owner_a, owner_b),
        "pair": pair,
        "interleaved": True,
        "barrier": True,
        "outcomes": finalized,
        "errors": tuple(errors),
        "final_state": final_state,
        "lock_intent": CLIENT_LOCK_INTENT,
    }


def run_injected_rollback(
    resource_identity: str,
    owner: str,
    command: dict[str, Any],
    connect: Callable[[str], Any] | None = None,
    capture_state: Callable[[Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Inject failure after evidence insert and before the publication pointer."""

    if connect is None:
        raise EngineProofError("job_local_connect_required")
    if resource_identity.startswith(("Driver=", "Server=", "DSN=")):
        raise EngineProofError("client_dsn_forbidden")
    connection = connect(resource_identity)
    observer = capture_state or _capture_owner_state
    try:
        before = observer(connection)
        cursor = connection.cursor()
        cursor.execute(
            "EXEC sys.sp_set_session_context @key = N'resume_publication_proof_fail_after_evidence', @value = N'1'"
        )
        cursor.close()
        try:
            execute_procedure(
                connection,
                "usp_CommitResumePublicationCommandForOwner",
                _commit_parameters(owner, command),
            )
            raise EngineProofError("injected_failure_did_not_occur")
        except EngineProofError:
            raise
        except Exception as error:
            reason = str(error)
            if "Ambient transactions are not permitted" in reason:
                raise EngineProofError(
                    "ambient_transaction_rejection_is_not_rollback_proof"
                ) from error
            if "PROOF_INJECTED_FAILURE" not in reason and "54999" not in reason:
                raise EngineProofError("injected_rollback_missing_in_transaction_failure") from error
        after = observer(connection)
        if after != before:
            raise EngineProofError("injected_rollback_left_writes")
        return {
            "rolled_back": True,
            "injected_after_writes": True,
            "before": before,
            "after": after,
            "lock_intent": CLIENT_LOCK_INTENT,
        }
    finally:
        try:
            connection.close()
        except Exception:
            pass


def run_codec_and_evidence(
    connection,
    fields: dict[str, Any],
    encode=None,
    digest=None,
) -> dict[str, Any]:
    """Compare SQL encode bytes/digest with the Python codec. Must execute both."""

    from services.resume_publication_contracts import encode_canonical_source, hash_canonical_source

    python_encode = encode or encode_canonical_source
    python_digest = digest or hash_canonical_source
    expected_bytes = python_encode(fields)
    expected_digest = python_digest(expected_bytes)
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            DECLARE @Bytes varbinary(max);
            DECLARE @Digest char(64);
            EXEC dbo.usp_ResumePublicationEncodeSourceInternal
                @FieldsJson = ?, @Bytes = @Bytes OUTPUT, @Digest = @Digest OUTPUT;
            SELECT @Bytes AS content_bytes, @Digest AS content_sha256;
            """,
            (payload,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if not row:
        raise EngineProofError("codec_sql_encode_missing")
    sql_bytes = bytes(row[0] or b"")
    sql_digest = str(row[1] or "")
    if sql_bytes != expected_bytes or sql_digest != expected_digest:
        raise EngineProofError("codec_mismatch")
    return {
        "equal": True,
        "sha256": expected_digest,
        "bytes": len(expected_bytes),
        "lock_intent": CLIENT_LOCK_INTENT,
    }


CAPTURE_ROLLBACK_GUARD_CASES = {
    "own_index": 0,
    "later_view": 52022,
    "later_trigger": 52022,
    "later_index": 52022,
    "later_stats": 52022,
    "later_fk": 52021,
    "member_data": 52020,
}


def run_capture_rollback_contracts(connection) -> dict[str, Any]:
    """Exercise Capture's real rollback immediately after its first installation."""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            -- capture rollback metadata proof
            SELECT i.object_id AS capture_object_id, i.index_id, i.name AS index_name,
                i.has_filter, i.filter_definition,
                CASE WHEN EXISTS (SELECT 1 FROM sys.sql_expression_dependencies AS d
                    WHERE d.referenced_id=i.object_id AND d.referencing_id=i.object_id)
                    THEN 1 ELSE 0 END AS self_dependency
            FROM sys.indexes AS i
            WHERE i.object_id=OBJECT_ID(N'dbo.captures') AND i.name=N'IX_captures_owner_created';
        """)
        metadata = [row for result in _fetch_procedure_result_sets(cursor) for row in result]
    finally:
        cursor.close()
    if len(metadata) != 1 or metadata[0].get("has_filter") != 1 or metadata[0].get("self_dependency") != 1:
        raise EngineProofError("capture_owned_filter_dependency_not_observed")
    normalized_filter = str(metadata[0].get("filter_definition") or "").lower()
    for char in "[]() \r\n\t":
        normalized_filter = normalized_filter.replace(char, "")
    if normalized_filter != "deleted_at_utcisnull":
        raise EngineProofError("capture_owned_filter_definition_changed")

    root = Path(__file__).resolve().parents[1]
    rollback = (root / "SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures_rollback.sql").read_text(encoding="utf-8")
    fixtures = {
        "own_index": ("", "1=1"),
        "later_view": (
            "EXEC(N'CREATE VIEW dbo.v_ProofCaptureLater AS SELECT capture_id FROM dbo.captures;');",
            "OBJECT_ID(N'dbo.v_ProofCaptureLater', N'V') IS NOT NULL"),
        "later_trigger": (
            "EXEC(N'CREATE TRIGGER dbo.tr_ProofCaptureLater ON dbo.captures AFTER INSERT AS BEGIN SET NOCOUNT ON; SELECT capture_id FROM dbo.captures; END;');",
            "OBJECT_ID(N'dbo.tr_ProofCaptureLater', N'TR') IS NOT NULL"),
        "later_index": (
            "CREATE INDEX IX_ProofCaptureLater ON dbo.captures(capture_id) WHERE active=1;",
            "EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.captures') AND name=N'IX_ProofCaptureLater')"),
        "later_stats": (
            "CREATE STATISTICS ST_ProofCaptureLater ON dbo.captures(capture_id) WHERE active=1;",
            "EXISTS (SELECT 1 FROM sys.stats WHERE object_id=OBJECT_ID(N'dbo.captures') AND name=N'ST_ProofCaptureLater' AND user_created=1 AND has_filter=1)"),
        "later_fk": (
            "CREATE TABLE dbo.ProofCaptureLaterRows(capture_id bigint REFERENCES dbo.captures(capture_id));",
            "OBJECT_ID(N'dbo.ProofCaptureLaterRows', N'U') IS NOT NULL"),
        "member_data": (
            """
            EXEC dbo.usp_UpsertAppUserFromAuth @AuthProvider=N'test',
                @AuthIssuer=N'https://proof.peerslate.example', @AuthSubject=N'proof-capture-rollback',
                @DisplayName=N'Proof rollback owner';
            DECLARE @UserKey nvarchar(300);
            SELECT @UserKey=user_key FROM dbo.app_users WHERE auth_subject=N'proof-capture-rollback';
            EXEC dbo.usp_CreateCapture @UserKey=@UserKey, @CaptureType=N'text', @Body=N'Proof rollback guard';
            """, "(SELECT COUNT(*) FROM dbo.captures)=1"),
    }
    cases = {}
    for name, expected in CAPTURE_ROLLBACK_GUARD_CASES.items():
        if name == "own_index":
            continue
        fixture, observe = fixtures[name]
        cursor = connection.cursor()
        try:
            # Embed the exact rollback file in this batch. Its own CATCH can
            # roll back the outer fixture transaction without crossing an EXEC
            # boundary with a changed transaction count. No driver commit here.
            cursor.execute(f"""
                -- capture rollback guard proof:{name}
                SET NOCOUNT ON; SET XACT_ABORT ON;
                IF @@TRANCOUNT<>0 THROW 54980, 'Capture proof has ambient transaction.', 1;
                IF EXISTS (SELECT 1 FROM dbo.captures)
                   OR EXISTS (SELECT 1 FROM dbo.app_users WHERE auth_subject=N'proof-capture-rollback')
                   OR OBJECT_ID(N'dbo.v_ProofCaptureLater') IS NOT NULL
                   OR OBJECT_ID(N'dbo.tr_ProofCaptureLater') IS NOT NULL
                   OR OBJECT_ID(N'dbo.ProofCaptureLaterRows') IS NOT NULL
                   OR EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.captures') AND name=N'IX_ProofCaptureLater')
                   OR EXISTS (SELECT 1 FROM sys.stats WHERE object_id=OBJECT_ID(N'dbo.captures') AND name=N'ST_ProofCaptureLater')
                    THROW 54981, 'Capture proof baseline is not pristine.', 1;
                DECLARE @CaptureBefore int=OBJECT_ID(N'dbo.captures');
                DECLARE @IndexBefore int=(SELECT index_id FROM sys.indexes WHERE object_id=@CaptureBefore AND name=N'IX_captures_owner_created');
                DECLARE @CreateBefore nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CreateCapture'));
                DECLARE @ListBefore nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListCapturesForOwner'));
                DECLARE @GuardError int=0, @FixtureApplied bit=0, @TableRemoved bit=0;
                BEGIN TRY
                    BEGIN TRANSACTION;
                    {fixture}
                    IF {observe} SET @FixtureApplied=1;
                    BEGIN TRY
                        {rollback}
                        IF OBJECT_ID(N'dbo.captures') IS NULL SET @TableRemoved=1;
                    END TRY
                    BEGIN CATCH
                        SET @GuardError=ERROR_NUMBER();
                    END CATCH;
                    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
                END TRY
                BEGIN CATCH
                    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
                    THROW;
                END CATCH;
                SELECT @GuardError AS capture_guard_error, @FixtureApplied AS fixture_applied,
                    @TableRemoved AS table_removed,
                    CASE WHEN @@TRANCOUNT=0 AND OBJECT_ID(N'dbo.captures')=@CaptureBefore
                        AND EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=@CaptureBefore AND index_id=@IndexBefore AND name=N'IX_captures_owner_created')
                        AND OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CreateCapture'))=@CreateBefore
                        AND OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListCapturesForOwner'))=@ListBefore
                        AND NOT EXISTS (SELECT 1 FROM dbo.captures)
                        AND NOT EXISTS (SELECT 1 FROM dbo.app_users WHERE auth_subject=N'proof-capture-rollback')
                        AND OBJECT_ID(N'dbo.v_ProofCaptureLater') IS NULL
                        AND OBJECT_ID(N'dbo.tr_ProofCaptureLater') IS NULL
                        AND OBJECT_ID(N'dbo.ProofCaptureLaterRows') IS NULL
                        AND NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=@CaptureBefore AND name=N'IX_ProofCaptureLater')
                        AND NOT EXISTS (SELECT 1 FROM sys.stats WHERE object_id=@CaptureBefore AND name=N'ST_ProofCaptureLater')
                        THEN 1 ELSE 0 END AS baseline_restored;
            """)
            rows = [row for result in _fetch_procedure_result_sets(cursor) for row in result
                    if "capture_guard_error" in row]
        finally:
            cursor.close()
        if (len(rows) != 1 or rows[0].get("capture_guard_error") != expected
                or rows[0].get("fixture_applied") != 1 or rows[0].get("baseline_restored") != 1
                or rows[0].get("table_removed") != (1 if expected == 0 else 0)):
            raise EngineProofError(f"capture_rollback_guard_failed:{name}:observed={rows!r}")
        cases[name] = "pass"

    # A successful DROP TABLE is a real migration boundary. Run it outside a
    # parent transaction, observe the absent objects, then reapply Capture-001.
    # The negative fixtures above still require complete transactional restore.
    def state(marker):
        cursor = connection.cursor()
        try:
            cursor.execute(f"""
                -- capture rollback standalone state proof:{marker}
                SELECT CASE WHEN OBJECT_ID(N'dbo.captures', N'U') IS NOT NULL THEN 1 ELSE 0 END AS capture_table,
                    CASE WHEN OBJECT_ID(N'dbo.usp_CreateCapture', N'P') IS NOT NULL THEN 1 ELSE 0 END AS create_proc,
                    CASE WHEN OBJECT_ID(N'dbo.usp_ListCapturesForOwner', N'P') IS NOT NULL THEN 1 ELSE 0 END AS list_proc,
                    CASE WHEN EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-CAPTURE-001')
                        THEN 1 ELSE 0 END AS migration_record,
                    CASE WHEN EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.captures')
                        AND name=N'IX_captures_owner_created') THEN 1 ELSE 0 END AS owned_index,
                    @@TRANCOUNT AS transaction_count;
            """)
            rows = [row for result in _fetch_procedure_result_sets(cursor) for row in result]
        finally:
            cursor.close()
        if len(rows) != 1:
            raise EngineProofError(f"capture_rollback_state_missing:{marker}:observed={rows!r}")
        return rows[0]

    present = {"capture_table": 1, "create_proc": 1, "list_proc": 1,
               "migration_record": 1, "owned_index": 1, "transaction_count": 0}
    before = state("before")
    if before != present:
        raise EngineProofError(f"capture_rollback_baseline_missing:observed={before!r}")

    def dependency_catalog() -> dict[str, Any]:
        # Only synthetic object identities and types; no member rows or SQL bodies.
        queries = {
            "dependencies": """
                SELECT TOP (17) dependency.referencing_id,
                    referencing_object.name AS referencing_name,
                    referencing_object.type AS referencing_type,
                    referencing_object.parent_object_id,
                    dependency.referencing_minor_id, dependency.referenced_minor_id
                FROM sys.sql_expression_dependencies AS dependency
                LEFT JOIN sys.objects AS referencing_object
                    ON referencing_object.object_id=dependency.referencing_id
                WHERE dependency.referenced_id=OBJECT_ID(N'dbo.captures')
                ORDER BY dependency.referencing_id, dependency.referencing_minor_id,
                    dependency.referenced_minor_id;
            """,
            "indexes": """
                SELECT TOP (17) index_id, name, is_primary_key, is_unique_constraint, has_filter
                FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.captures')
                ORDER BY index_id;
            """,
            "statistics": """
                SELECT TOP (17) statistic.stats_id, statistic.name, statistic.user_created,
                    statistic.auto_created, statistic.has_filter,
                    CASE WHEN EXISTS (SELECT 1 FROM sys.indexes AS capture_index
                        WHERE capture_index.object_id=statistic.object_id
                          AND capture_index.index_id=statistic.stats_id)
                        THEN 1 ELSE 0 END AS index_backed
                FROM sys.stats AS statistic
                WHERE statistic.object_id=OBJECT_ID(N'dbo.captures')
                ORDER BY statistic.stats_id;
            """,
        }
        observed = {}
        for kind, query in queries.items():
            cursor = connection.cursor()
            try:
                cursor.execute(query)
                rows = [row for result in _fetch_procedure_result_sets(cursor) for row in result]
            finally:
                cursor.close()
            observed[kind] = {"rows": rows[:16], "truncated": len(rows) > 16}
        return observed

    catalog_before = dependency_catalog()
    try:
        apply_sql_file(connection, root / "SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures_rollback.sql")
    except Exception as error:
        try:
            catalog_after = dependency_catalog()
        except Exception as observation_error:
            catalog_after = {"observation_error": sanitize_proof_error(observation_error)}
        raise EngineProofError(
            f"capture_rollback_standalone_failed:{error}:"
            f"catalog_before={catalog_before!r}:catalog_after={catalog_after!r}"
        ) from error
    removed = state("removed")
    try:
        if removed != {"capture_table": 0, "create_proc": 0, "list_proc": 0,
                       "migration_record": 0, "owned_index": 0, "transaction_count": 0}:
            raise EngineProofError(f"capture_rollback_owned_removal_failed:observed={removed!r}")
    finally:
        apply_sql_file(connection, root / "SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures.sql")
    restored = state("reapplied")
    if restored != present:
        raise EngineProofError(f"capture_rollback_reapply_failed:observed={restored!r}")
    cases["own_index"] = "pass"
    return {"owned_filter": metadata[0], "cases": cases,
            "dependency_catalog_before": catalog_before}


PREDECESSOR_VERIFIERS = (
    ("PS-RESUME-EDIT-001_private_commands_verify.sql", "usp_CommitLivingResumeCommandForOwner", 52010),
    ("PS-RESUME-EDIT-002_education_commands_verify.sql", "usp_CommitLivingResumeCommandForOwner", 52022),
    ("PS-ENTRY-POLICY-001_entry_metadata_verify.sql", "usp_CommitEntryPolicyCommandForOwner", 52110),
    ("PS-RESUME-DRAFT-001_resume_drafts_verify.sql", "usp_CommitResumeDraftCommandForOwner", 52210),
    ("PS-RESUME-MEDIA-001_resume_media_verify.sql", "usp_CommitResumeMediaCommandForOwner", 52310),
    ("PS-RESUME-INTAKE-001_resume_intake_verify.sql", "usp_CommitResumeIntakeCommandForOwner", 52320),
)


def run_verifier_mutation_contracts(connection) -> dict[str, Any]:
    """Require actual verifiers to reject damaged modules, rolling back every probe."""
    root = Path(__file__).resolve().parents[1] / "SQL FIles/Verification"

    def literal(value):
        return "N'" + value.replace("'", "''") + "'"

    def alter_existing_definition(declared_name, actual_name):
        # The hosted module did not match exact CREATE/ALTER header strings.
        # A renamed Core also keeps its old public name. Locate that name only
        # in a bounded declaration prefix, then preserve the body suffix.
        return (
            f"DECLARE @DeclaredName nvarchar(128)={literal(declared_name)}; "
            "DECLARE @NamePosition int=CHARINDEX(@DeclaredName, @D); "
            "DECLARE @Prefix nvarchar(256)=UPPER(LEFT(@D, @NamePosition)); "
            "IF @NamePosition=0 OR @NamePosition>256 OR CHARINDEX(N'PROC', @Prefix)=0 "
            "OR (CHARINDEX(N'CREATE', @Prefix)=0 AND CHARINDEX(N'ALTER', @Prefix)=0) "
            "BEGIN "
            "DECLARE @HeaderPreview nvarchar(100)=REPLACE(REPLACE(LEFT(@D, 100), CHAR(13), N' '), CHAR(10), N' '); "
            "DECLARE @Diagnostic nvarchar(2048)=CONCAT(N'Verifier probe declaration missing; name_pos=', "
            "COALESCE(CONVERT(nvarchar(12), @NamePosition), N'null'), N'; header=', "
            "COALESCE(@HeaderPreview, N'null')); "
            "THROW 54974, @Diagnostic, 1; "
            "END; "
            "DECLARE @SuffixStart int=@NamePosition+LEN(@DeclaredName); "
            "IF SUBSTRING(@D, @SuffixStart, 1)=N']' SET @SuffixStart=@SuffixStart+1; "
            f"SET @D={literal(f'ALTER PROCEDURE dbo.{actual_name}')} "
            "+SUBSTRING(@D, @SuffixStart, LEN(@D)); "
        )

    probes = []
    for filename, public, error in PREDECESSOR_VERIFIERS:
        core = public + "Core"
        guard = ("usp_ResumePublicationApplyAfterPolicyInternal" if "EntryPolicy" in public
                 else "usp_ResumePublicationGuardLegacyMutator")
        other_core = ("usp_CommitResumeDraftCommandForOwnerCore" if "LivingResume" in public
                      else "usp_CommitLivingResumeCommandForOwnerCore")
        probes.extend((
            (filename, "missing_core", core, f"DROP PROCEDURE dbo.{core};", error),
            (filename, "lost_predecessor_protection", core,
             f"EXEC sys.sp_executesql {literal(f'CREATE OR ALTER PROCEDURE dbo.{core} AS RETURN;')};", error),
            (filename, "misdirected_core", public,
             f"DECLARE @D nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.{public}')); "
             f"IF CHARINDEX(N'EXEC dbo.{core}', @D)=0 THROW 54975, 'Verifier probe call is missing.', 1; "
             f"SET @D=REPLACE(@D, N'EXEC dbo.{core}', N'EXEC dbo.{other_core}'); "
             + alter_existing_definition(public, public) + "EXEC sys.sp_executesql @D;", error),
            (filename, "missing_guard_call", public,
             f"DECLARE @D nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.{public}')); "
             f"IF CHARINDEX(N'EXEC dbo.{guard}', @D)=0 THROW 54975, 'Verifier probe call is missing.', 1; "
             f"SET @D=REPLACE(@D, N'EXEC dbo.{guard}', "
             "N'EXEC dbo.usp_ResumePublicationLockOwnerInternal'); "
             + alter_existing_definition(public, public) + "EXEC sys.sp_executesql @D;", error),
        ))
    for name, error in (("usp_ResumePublicationGuardLegacyMutator", 54113),
                        ("usp_ResumePublicationApplyAfterPolicyInternal", 54114)):
        probes.append(("PS-RESUME-PUBLICATION-001_publication_verify.sql", "weakened_guard", name,
                       f"EXEC sys.sp_executesql {literal(f'CREATE OR ALTER PROCEDURE dbo.{name} AS RETURN;')};", error))

    media = "usp_CommitResumeMediaCommandForOwner"
    for kind, old, new in (
        ("media_replay_type_comparison", "@ExistingType <> @IncomingType", "1 = 0"),
        ("media_replay_digest_comparison", "@ExistingDigest <> @IncomingDigest", "1 = 0"),
        ("media_replay_conflict_outcome", "N'idempotency_conflict' AS outcome", "N'replayed' AS outcome"),
    ):
        mutation = (
            f"DECLARE @D nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.{media}Core')); "
            f"IF CHARINDEX({literal(old)}, @D)=0 THROW 54975, 'Verifier probe target is missing.', 1; "
            f"SET @D=REPLACE(@D, {literal(old)}, {literal(new)}); "
            + alter_existing_definition(media, media + "Core") + "EXEC sys.sp_executesql @D;"
        )
        probes.append(("PS-RESUME-MEDIA-001_resume_media_verify.sql", kind, media + "Core", mutation, 52310))

    for kind, old, new in (
        ("media_conflict_publishes", "CONVERT(bit, 0) AS publishes", "CONVERT(bit, 1) AS publishes"),
        ("media_conflict_return", "RETURN;", ""),
    ):
        mutation = (
            f"DECLARE @D nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.{media}Core')); "
            "DECLARE @Start int=CHARINDEX(N'IF @ExistingType <> @IncomingType', @D); "
            "DECLARE @End int=CHARINDEX(N'END;', @D, @Start); "
            "IF @Start=0 OR @End<=@Start THROW 54973, 'Conflict probe branch missing.', 1; "
            "DECLARE @Branch nvarchar(max)=SUBSTRING(@D, @Start, @End+4-@Start); "
            f"IF CHARINDEX({literal(old)}, @Branch)=0 THROW 54975, 'Verifier probe target is missing.', 1; "
            f"SET @D=STUFF(@D, @Start, @End+4-@Start, REPLACE(@Branch, {literal(old)}, {literal(new)})); "
            + alter_existing_definition(media, media + "Core") + "EXEC sys.sp_executesql @D;"
        )
        probes.append(("PS-RESUME-MEDIA-001_resume_media_verify.sql", kind, media + "Core", mutation, 52310))

    passed = []
    for filename, kind, name, mutation, expected in probes:
        verifier = (root / filename).read_text(encoding="utf-8")
        cursor = connection.cursor()
        try:
            # Do not call apply_sql_file here: its commit would release the DDL
            # mutation. One batch owns execution, expected-error capture and rollback.
            cursor.execute(f"""
                -- publication verifier mutation proof
                SET NOCOUNT ON; SET XACT_ABORT ON;
                IF @@TRANCOUNT <> 0 THROW 54971, 'Verifier probe requires no ambient transaction.', 1;
                DECLARE @Before nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.{name}'));
                IF @Before IS NULL THROW 54972, 'Verifier probe module is missing.', 1;
                DECLARE @ProbeError int=0, @Changed bit=0;
                BEGIN TRY
                    BEGIN TRANSACTION;
                    EXEC sys.sp_executesql {literal(mutation)};
                    IF OBJECT_DEFINITION(OBJECT_ID(N'dbo.{name}')) IS NULL
                       OR OBJECT_DEFINITION(OBJECT_ID(N'dbo.{name}')) <> @Before SET @Changed=1;
                    BEGIN TRY
                        EXEC sys.sp_executesql {literal(verifier)};
                    END TRY
                    BEGIN CATCH
                        SET @ProbeError=ERROR_NUMBER();
                    END CATCH;
                    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                END TRY
                BEGIN CATCH
                    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                    THROW;
                END CATCH;
                SELECT @ProbeError AS probe_error, @Changed AS mutation_applied,
                    CASE WHEN OBJECT_DEFINITION(OBJECT_ID(N'dbo.{name}')) = @Before
                         AND @@TRANCOUNT=0 THEN 1 ELSE 0 END AS module_restored;
            """)
            rows = [row for result in _fetch_procedure_result_sets(cursor) for row in result
                    if "probe_error" in row]
        except Exception as exc:
            raise EngineProofError(
                f"verifier_mutation_execution_failed:{filename}:{kind}:{name}:"
                f"{sanitize_proof_error(exc)}"
            ) from exc
        finally:
            cursor.close()
        if (len(rows) != 1 or rows[0].get("probe_error") != expected
                or rows[0].get("mutation_applied") != 1 or rows[0].get("module_restored") != 1):
            raise EngineProofError(f"verifier_mutation_contract_failed:{filename}:{kind}")
        passed.append(f"{filename}:{kind}:{name}")
    return {"rejected_and_restored": passed, "count": len(passed)}


def run_sql_sequence_contracts(connection, owner_a: str, owner_b: str) -> dict[str, Any]:
    """Exercise SQL Server null uniqueness and codec limits on synthetic owners."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            -- publication slug constraint proof
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            DECLARE @OwnerA nvarchar(300) = ?, @OwnerB nvarchar(300) = ?;
            DECLARE @A bigint, @B bigint, @Rejected bit = 0;
            SELECT @A = p.profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id = p.user_id WHERE u.user_key = @OwnerA;
            SELECT @B = p.profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id = p.user_id WHERE u.user_key = @OwnerB;
            DECLARE @Before int = (SELECT COUNT(*) FROM dbo.resume_sharing_state
                WHERE owner_profile_id IN (@A, @B) AND public_slug IS NULL AND sharing_enabled = 0);
            IF @Before <> 2 OR @A = @B THROW 54970, 'Two unpublished owners are required.', 1;
            BEGIN TRY
                BEGIN TRANSACTION;
                UPDATE dbo.resume_sharing_state SET public_slug = N'proof-slug-uniqueness' WHERE owner_profile_id = @A;
                BEGIN TRY
                    UPDATE dbo.resume_sharing_state SET public_slug = N'proof-slug-uniqueness' WHERE owner_profile_id = @B;
                END TRY
                BEGIN CATCH
                    IF ERROR_NUMBER() NOT IN (2601, 2627) THROW;
                    SET @Rejected = 1;
                END CATCH;
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
            SELECT @Before, @Rejected, (SELECT COUNT(*) FROM dbo.resume_sharing_state
                WHERE owner_profile_id IN (@A, @B) AND public_slug IS NULL AND sharing_enabled = 0);
            """,
            (owner_a, owner_b),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if row is None or tuple(int(value) for value in row) != (2, 1, 2):
        raise EngineProofError("unpublished_owner_slug_constraint_failed")

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            -- publication draft version token proof
            SET NOCOUNT ON;
            DECLARE @Owner nvarchar(300) = ?, @Profile bigint;
            SELECT @Profile = p.profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id = p.user_id WHERE u.user_key = @Owner;
            BEGIN TRY
                BEGIN TRANSACTION;
                IF EXISTS (SELECT 1 FROM dbo.resume_drafts WHERE owner_profile_id = @Profile)
                    UPDATE dbo.resume_drafts SET base_publication_version = N'publication:proof-token' WHERE owner_profile_id = @Profile;
                ELSE
                    INSERT dbo.resume_drafts (owner_profile_id, draft_version, base_publication_version)
                    VALUES (@Profile, 0, N'publication:proof-token');
                EXEC dbo.usp_GetResumeDraftForOwner @UserKey = @Owner;
                EXEC dbo.usp_GetResumeMediaDraftForOwner @UserKey = @Owner;
                ROLLBACK TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
            """,
            (owner_a,),
        )
        results = _fetch_procedure_result_sets(cursor)
    finally:
        cursor.close()
    for reader, identifying_column in (("draft", "command_receipts_json"), ("media", "media_generation")):
        headers = [row for result_set in results for row in result_set if identifying_column in row]
        if len(headers) != 1 or headers[0].get("base_publication_version") != "publication:proof-token":
            raise EngineProofError(f"{reader}_publication_version_token_changed")

    vectors = {
        "unicode": {"summary": "Caf\u00e9 \u6f22\u5b57 \U0001f642 e\u0301  ", "current_role": True},
        "over_4000_characters": {"summary": "\u03a9" * 4100, "current_role": False},
    }
    codec = {name: run_codec_and_evidence(connection, fields) for name, fields in vectors.items()}
    invalid = (
        ('{"summary":7}', 54013),
        ('{"current_role":"true"}', 54013),
        ('{"summary ":"x"}', 54012),
        ('{"summary":"x","summary":"y"}', 54012),
    )
    for payload, expected in invalid:
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                -- publication codec rejection proof
                SET NOCOUNT ON;
                DECLARE @Error int = 0, @Bytes varbinary(max), @Digest char(64);
                BEGIN TRY
                    EXEC dbo.usp_ResumePublicationEncodeSourceInternal
                        @FieldsJson = ?, @Bytes = @Bytes OUTPUT, @Digest = @Digest OUTPUT;
                END TRY
                BEGIN CATCH
                    SET @Error = ERROR_NUMBER();
                END CATCH;
                SELECT @Error;
                """,
                (payload,),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()
        if row is None or int(row[0]) != expected:
            raise EngineProofError("sql_codec_invalid_field_accepted")
    return {"unpublished_owners": 2, "duplicate_slug_rejected": True,
            "slug_probe_rolled_back": True, "draft_version_token_preserved": True,
            "media_version_token_preserved": True, "codec_vectors": codec,
            "invalid_codec_vectors_rejected": len(invalid)}


def run_publication_sql_oracles(
    resource_identity: str,
    connect: Callable[[str], Any],
    *,
    apply_forward,
    apply_rollback,
    verify,
    ordered_ids: list[str],
    codec_fields: dict[str, Any] | None = None,
    principal: str = "peerslate_app",
) -> dict[str, Any]:
    """Empty rollback/reapply, then populated seed, production adapters, and races."""

    if connect is None:
        raise EngineProofError("job_local_connect_required")
    refuse_client_supplied_dsn(
        resource_identity if resource_identity.startswith(("Driver=", "Server=", "DSN=")) else None
    )
    executed: dict[str, str] = {}

    def observe_state() -> dict[str, Any]:
        observer = populated_connect(populated_identity)
        try:
            return capture_publication_state(observer)
        finally:
            observer.close()

    def observe_foreign_policy() -> list[tuple[Any, ...]]:
        observer = populated_connect(populated_identity)
        try:
            return capture_foreign_policy_state(observer)
        finally:
            observer.close()

    def run_case(name: str, fn):
        try:
            fn()
        except Exception as error:
            raise EngineProofError(f"oracle_case_{name}_failed: {error}") from error
        executed[name] = "pass"

    empty_identity = f"{resource_identity}:{PROOF_EMPTY_DATABASE}"
    populated_identity = f"{resource_identity}:{PROOF_POPULATED_DATABASE}"

    def empty_connect(identity=None):
        return connect(identity or empty_identity)

    def populated_connect(identity=None):
        return connect(identity or populated_identity)

    migration = None

    def _empty_closure():
        nonlocal migration
        migration = run_migration_closure(
            lambda: apply_forward(empty_identity),
            lambda: apply_rollback(empty_identity),
            lambda: verify(empty_identity),
            ordered_ids=ordered_ids,
        )
        if not migration.get("reapplied"):
            raise EngineProofError("empty_reapply_missing")
        capture = migration.get("capture_rollback") or {}
        if capture.get("cases") != {name: "pass" for name in CAPTURE_ROLLBACK_GUARD_CASES}:
            raise EngineProofError("capture_rollback_guard_evidence_missing")
        executed["capture_rollback_dependency_guards"] = "pass"

    run_case("empty_forward_verify_rollback_reapply_verify", _empty_closure)

    def _empty_idempotency():
        apply_forward(empty_identity)
        verify(empty_identity)

    run_case("empty_forward_idempotency", _empty_idempotency)
    def _compiled_closure():
        if set(ordered_ids) != set(REQUIRED_PUBLICATION_CLOSURE_IDS):
            raise EngineProofError("incomplete_migration_closure")
        verify(empty_identity)

    run_case("compile_complete_closure", _compiled_closure)
    run_case("empty_database_compile", lambda: verify(empty_identity))

    verifier_mutations = None

    def _verifier_mutations():
        nonlocal verifier_mutations
        connection = empty_connect()
        try:
            verifier_mutations = run_verifier_mutation_contracts(connection)
        finally:
            connection.close()
        verify(empty_identity)

    run_case("verifier_mutation_rejections", _verifier_mutations)

    def _empty_predecessor_permissions():
        predecessors = (
            "usp_CommitEntryPolicyCommandForOwner",
            "usp_ListEntryPolicyEntriesForOwner",
            "usp_GetEntryPolicyEntryForOwner",
            "usp_CommitResumeDraftCommandForOwner",
            "usp_CommitResumeMediaCommandForOwner",
            "usp_CommitResumeIntakeCommandForOwner",
            "usp_CommitLivingResumeCommandForOwner",
        )
        root = Path(__file__).resolve().parents[1]
        forward = root / "SQL FIles/Migrations/proposed/PS-RESUME-PUBLICATION-001_publication.sql"
        rollback = root / "SQL FIles/Migrations/proposed/PS-RESUME-PUBLICATION-001_publication_rollback.sql"
        connection = empty_connect()
        try:
            # The predecessor object keeps its explicit principal grant when
            # renamed Core. The migration's PUBLIC deny must override it only
            # while E is applied, then disappear on empty rollback.
            apply_sql_file(connection, forward)
            provision_proof_principals(connection)
            for name in predecessors:
                apply_sql_script(connection, f"GRANT EXECUTE ON dbo.[{name}Core] TO [peerslate_app]")

            def effective(names):
                values = []

                def read():
                    cursor = connection.cursor()
                    try:
                        for name in names:
                            cursor.execute("SELECT HAS_PERMS_BY_NAME(?, N'OBJECT', N'EXECUTE')",
                                           (f"dbo.{name}",))
                            row = cursor.fetchone()
                            values.append(None if row is None else row[0])
                    finally:
                        cursor.close()

                _effective_principal(connection, "peerslate_app", read)
                return values

            cores = [name + "Core" for name in predecessors]
            if effective(cores) != [0] * len(cores):
                raise EngineProofError("core_execute_deny_missing")
            apply_sql_file(connection, rollback)
            if effective(predecessors) != [1] * len(predecessors):
                raise EngineProofError("empty_rollback_predecessor_execute_not_restored")
            # The same structural contracts must accept their original public
            # implementations after Publication alone is removed.
            for filename, _, _ in PREDECESSOR_VERIFIERS:
                apply_sql_file(connection, root / "SQL FIles/Verification" / filename)
            apply_sql_file(connection, forward)
            if effective(cores) != [0] * len(cores):
                raise EngineProofError("core_execute_deny_not_reapplied")
            verify(empty_identity)
        finally:
            connection.close()

    run_case("empty_rollback_restores_predecessor_execute", _empty_predecessor_permissions)

    def _multi_target_permissions():
        connection = empty_connect()
        try:
            provision_proof_principals(connection)
            owner = seed_publication_owner(connection)["user_key"]
            def observe_editor_attempt(command_id: str, record_key: str) -> tuple[int, int, int]:
                cursor = connection.cursor()
                try:
                    counts = []
                    for table, column, key in (
                        ("slate_entities", "entity_key", record_key),
                        ("career_chapters", "chapter_key", record_key),
                        ("living_resume_command_receipts", "command_id", command_id),
                    ):
                        cursor.execute(f"SELECT COUNT_BIG(*) FROM dbo.{table} WHERE {column} = ?", (key,))
                        row = cursor.fetchone()
                        if row is None:
                            raise EngineProofError("editor_attempt_observation_missing")
                        counts.append(int(row[0]))
                    return tuple(counts)
                finally:
                    cursor.close()

            valid_values = {
                "role_title": "Allowlist control", "employer_name": "PeerSlate",
                "date_precision": "month", "current_role": False,
            }
            if observe_editor_attempt(PROOF_EDITOR_CONTROL_COMMAND, PROOF_EDITOR_CONTROL_KEY) != (0, 0, 0):
                raise EngineProofError("editor_allowlist_control_not_fresh")
            execute_procedure(connection, "usp_CommitLivingResumeCommandForOwner", [
                ("@UserKey", owner), ("@CommandId", PROOF_EDITOR_CONTROL_COMMAND),
                ("@CommandJson", _json_command(
                    command_id=PROOF_EDITOR_CONTROL_COMMAND, type="create_role",
                    record_key=PROOF_EDITOR_CONTROL_KEY, parent_key=None,
                    expected_version=None, values=valid_values,
                )),
            ])
            if observe_editor_attempt(PROOF_EDITOR_CONTROL_COMMAND, PROOF_EDITOR_CONTROL_KEY) != (1, 1, 1):
                raise EngineProofError("editor_allowlist_control_not_committed")
            before_invalid_fields = capture_publication_state(connection)
            for command_id, record_key, field_name in PROOF_EDITOR_INVALID_FIELDS:
                before_attempt = observe_editor_attempt(command_id, record_key)
                if before_attempt != (0, 0, 0):
                    raise EngineProofError("editor_invalid_attempt_not_fresh")
                try:
                    execute_procedure(connection, "usp_CommitLivingResumeCommandForOwner", [
                        ("@UserKey", owner), ("@CommandId", command_id),
                        ("@CommandJson", _json_command(
                            command_id=command_id, type="create_role",
                            record_key=record_key, parent_key=None,
                            expected_version=None,
                            values={**valid_values, field_name: "Rejected"},
                        )),
                    ])
                except Exception as error:
                    if "RESUME_EDITOR_VALIDATION" not in str(error):
                        raise EngineProofError("editor_field_allowlist_unexpected_error") from error
                else:
                    raise EngineProofError("editor_field_allowlist_accepted")
                if capture_publication_state(connection) != before_invalid_fields:
                    raise EngineProofError("editor_field_allowlist_mutated_state")
                if observe_editor_attempt(command_id, record_key) != before_attempt:
                    raise EngineProofError("editor_field_allowlist_left_target_or_receipt")
            second_command = "00000000-0000-4000-8000-0000000000a8"
            execute_procedure(connection, "usp_CommitLivingResumeCommandForOwner", [
                ("@UserKey", owner), ("@CommandId", second_command),
                ("@CommandJson", _json_command(
                    command_id=second_command, type="create_role",
                    record_key=PROOF_BATCH_ENTRY_KEY, parent_key=None,
                    expected_version=None,
                    values={"role_title": "Second role", "employer_name": "PeerSlate",
                            "summary": "Second public role.", "date_precision": "month",
                            "employment_type": "full_time", "current_role": False},
                )),
            ])
            execute_procedure(connection, "usp_CommitEntryPolicyCommandForOwner",
                              _commit_parameters(owner, {
                                  "request_id": "00000000-0000-4000-8000-0000000000a9",
                                  "json": _json_command(type="create", entry_key=PROOF_BATCH_ENTRY_KEY,
                                                        canonical_type="role", values={"role_title": "Second role"}),
                              }))
            execute_procedure(connection, "usp_CommitEntryPolicyCommandForOwner",
                              _commit_parameters(owner, {
                                  "request_id": "00000000-0000-4000-8000-0000000000ac",
                                  "json": _json_command(type="change_permissions", entry_key=PROOF_BATCH_ENTRY_KEY,
                                                        expected_access_revision=1,
                                                        permissions={"resume_display": True, "visitor_ai": False}),
                              }))
            seed_second_proof_owner(connection)
            publish_reviewed(connection, owner, "00000000-0000-4000-8000-0000000000ad", "b" * 64)

            def observe():
                observer = empty_connect()
                try:
                    cursor = observer.cursor()
                    try:
                        cursor.execute(
                            "SELECT policy.entry_key, policy.resume_display, policy.visitor_ai, policy.access_revision "
                            "FROM dbo.entry_policy_records AS policy "
                            "JOIN dbo.member_profiles AS profile ON profile.profile_id = policy.owner_profile_id "
                            "JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id "
                            "WHERE app_user.user_key = ? AND policy.entry_key IN (?, ?) ORDER BY policy.entry_key",
                            (owner, PROOF_ENTRY_KEY, PROOF_BATCH_ENTRY_KEY),
                        )
                        rows = cursor.fetchall()
                    finally:
                        cursor.close()
                    policies = {str(row[0]): (bool(row[1]), bool(row[2]), int(row[3])) for row in rows}
                    return policies, capture_publication_state(observer), capture_foreign_policy_state(observer)
                finally:
                    observer.close()

            before_policy, before_state, _ = observe()
            if (set(before_policy) != {PROOF_ENTRY_KEY, PROOF_BATCH_ENTRY_KEY}
                    or not all(row[0] for row in before_policy.values())
                    or not all(key in (before_state.get("display_json") or "")
                               for key in (PROOF_ENTRY_KEY, PROOF_BATCH_ENTRY_KEY))):
                raise EngineProofError("bulk_permission_seed_missing")
            _, service = production_publication_stack(connection)
            batch = {
                "request_id": "00000000-0000-4000-8000-0000000000ae",
                "type": "change_permissions", "entry_key": PROOF_ENTRY_KEY,
                "entries": [
                    {"entry_key": key, "expected_access_revision": before_policy[key][2],
                     "permissions": {"resume_display": False, "visitor_ai": False,
                                     "private_assistance_excluded": False}}
                    for key in (PROOF_ENTRY_KEY, PROOF_BATCH_ENTRY_KEY)
                ],
            }

            def commit_and_check():
                result = service.policy_service.commit(owner, batch)
                after_policy, after_state, _ = observe()
                if (result.get("replayed") or result.get("receipt", {}).get("type") != "change_permissions"
                        or set(after_policy) != set(before_policy)
                        or any(after_policy[key] != (False, False, before_policy[key][2] + 1)
                               for key in before_policy)
                        or int(after_state["publication_revision"]) != int(before_state["publication_revision"]) + 1
                        or len(after_state["receipts"]) != len(before_state["receipts"]) + 1
                        or any(key in (after_state.get("display_json") or "")
                               for key in before_policy)):
                    raise EngineProofError("bulk_permission_restriction_missing")
                replay = service.policy_service.commit(owner, batch)
                if not replay.get("replayed") or observe()[0:2] != (after_policy, after_state):
                    raise EngineProofError("bulk_permission_replay_changed_state")

                def expect_rejection(payload, code):
                    snapshot = observe()
                    try:
                        service.policy_service.commit(owner, payload)
                    except Exception as error:
                        current, seen = error, set()
                        while current is not None and id(current) not in seen:
                            if "54014" in str(current) or "ENTRY_POLICY_CHANGED" in str(current):
                                break
                            seen.add(id(current))
                            current = current.__cause__ or getattr(current, "__context__", None)
                        else:
                            raise EngineProofError(f"{code}_wrong_error") from error
                    else:
                        raise EngineProofError(f"{code}_accepted")
                    if observe() != snapshot:
                        raise EngineProofError(f"{code}_partial_change")

                stale = dict(batch, request_id="00000000-0000-4000-8000-0000000000af")
                stale["entries"] = [dict(item) for item in batch["entries"]]
                stale["entries"][0]["expected_access_revision"] = after_policy[PROOF_ENTRY_KEY][2]
                expect_rejection(stale, "bulk_permission_stale")
                foreign = dict(batch, request_id="00000000-0000-4000-8000-0000000000b0")
                foreign["entries"] = [
                    {"entry_key": PROOF_ENTRY_KEY,
                     "expected_access_revision": after_policy[PROOF_ENTRY_KEY][2],
                     "permissions": {"resume_display": True}},
                    {"entry_key": PROOF_FOREIGN_ENTRY_KEY,
                     "expected_access_revision": 1,
                     "permissions": {"resume_display": True}},
                ]
                expect_rejection(foreign, "bulk_permission_foreign")

            _effective_principal(connection, "peerslate_app", commit_and_check)
        finally:
            connection.close()

    run_case("my_data_bulk_permissions_atomic", _multi_target_permissions)

    apply_forward(populated_identity)
    verify(populated_identity)

    seed_connection = populated_connect(populated_identity)
    try:
        initial_entry_count = proof_entry_count(seed_connection)
        if initial_entry_count != 0:
            raise EngineProofError("populated_database_not_empty")
        provision_proof_principals(seed_connection)
        seed = seed_publication_owner(seed_connection)
        user_key = seed["user_key"]
        seed_proof_catalog_asset(seed_connection)
        second_user_key = seed_second_proof_owner(seed_connection)
        sequence_contracts = run_sql_sequence_contracts(seed_connection, user_key, second_user_key)
        executed["sql_sequence_contracts"] = "pass"
        owner_a_count = proof_entry_count(seed_connection, user_key)
        owner_b_count = proof_entry_count(seed_connection, second_user_key)
        if owner_a_count != 1 or owner_b_count != 3:
            raise EngineProofError("seed_cardinality_mismatch")
        digest = "a" * 64
        publish_reviewed(
            seed_connection,
            user_key,
            "00000000-0000-4000-8000-0000000000c1",
            digest,
        )
        before = capture_publication_state(seed_connection)
        if before.get("canonical_summary") != PROOF_SEED_SUMMARY:
            raise EngineProofError("missing_seed_rows")
        versions = {
            "content": int(before.get("content_version") or 1),
            "access": int(before.get("access_revision") or 2),
        }
        first_correct_versions = versions.copy()
        correct_publication_wording(
            seed_connection,
            user_key,
            "00000000-0000-4000-8000-0000000000c2",
            PROOF_CORRECTED_SUMMARY,
            expected_content_version=versions["content"],
            expected_access_revision=versions["access"],
        )
        after_correct = capture_publication_state(seed_connection)
        if after_correct.get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
            raise EngineProofError("correction_wording_unchanged")
        if not _json_contains(after_correct.get("display_json"), PROOF_CORRECTED_SUMMARY):
            raise EngineProofError("correction_wording_unchanged")
        if not after_correct.get("sharing_enabled") or not after_correct.get("resume_display"):
            raise EngineProofError("race_invalid_final_state")
        versions["content"] = int(after_correct.get("content_version") or (versions["content"] + 1))
        versions["access"] = int(after_correct.get("access_revision") or versions["access"])
        repository, service = production_publication_stack(seed_connection)

        def _invalid_targets():
            from services.resume_publication_repository import PublicationConflictError, PublicationDenied

            def commit_at(stage, request_id, command, expected_error=None):
                try:
                    return repository.commit_command(user_key, request_id, command)
                except Exception as error:
                    if expected_error is not None and isinstance(error, expected_error):
                        raise
                    cause = error
                    seen = set()
                    while cause.__cause__ is not None and id(cause) not in seen:
                        seen.add(id(cause))
                        cause = cause.__cause__
                    raise EngineProofError(
                        f"invalid_correction_{stage}_unexpected:{sanitize_proof_error(cause)}"
                    ) from error

            probes = (
                (PROOF_MISSING_ENTRY_KEY, False, PublicationDenied),
                (PROOF_FOREIGN_ENTRY_KEY, False, PublicationDenied),
                (PROOF_ENTRY_KEY, True, PublicationConflictError),
            )
            snapshot = capture_publication_state(seed_connection)
            for index, (entry_key, stale, expected_error) in enumerate(probes, start=1):
                before_state = capture_publication_state(seed_connection)
                payload = {
                    "type": "correct",
                    "entry_key": entry_key,
                    "expected_content_version": 99 if stale else versions["content"],
                    "expected_access_revision": versions["access"],
                    "values": {
                        "summary": f"Led team invalid {index}.",
                        "wording": f"Led team invalid {index}.",
                        "role_title": "Lead",
                        "employer_name": "PeerSlate",
                    },
                }
                with _expect_publication_error(expected_error, "invalid_correction_accepted"):
                    commit_at(
                        f"probe_{index}",
                        f"00000000-0000-4000-8000-0000000000d{index}",
                        payload,
                        expected_error,
                    )
                after_state = capture_publication_state(seed_connection)
                if after_state.get("canonical_summary") != before_state.get("canonical_summary"):
                    raise EngineProofError("invalid_correction_mutated")

            commit_at(
                "delete",
                "00000000-0000-4000-8000-0000000000d4",
                {"type": "delete", "entry_key": PROOF_ENTRY_KEY},
            )
            deleted = capture_publication_state(seed_connection)
            if deleted.get("lifecycle") == "active":
                raise EngineProofError("delete_lifecycle_missing")
            with _expect_publication_error(PublicationDenied, "deleted_correction_accepted"):
                commit_at(
                    "deleted",
                    "00000000-0000-4000-8000-0000000000d5",
                    {
                        "type": "correct",
                        "entry_key": PROOF_ENTRY_KEY,
                        "expected_content_version": versions["content"],
                        "expected_access_revision": versions["access"],
                        "values": {"summary": "Deleted entry must not change."},
                    },
                    PublicationDenied,
                )
            if capture_publication_state(seed_connection).get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
                raise EngineProofError("invalid_correction_mutated")
            commit_at(
                "restore",
                "00000000-0000-4000-8000-0000000000d6",
                {"type": "restore", "entry_key": PROOF_ENTRY_KEY,
                 "expected_access_revision": int(deleted["access_revision"])},
            )
            restored_private = capture_publication_state(seed_connection)
            if (restored_private.get("lifecycle") != "active"
                    or restored_private.get("resume_display")
                    or restored_private.get("visitor_ai")
                    or _json_contains(restored_private.get("display_json"), PROOF_ENTRY_KEY)
                    or _json_contains(restored_private.get("visitor_ai_json"), PROOF_ENTRY_KEY)):
                raise EngineProofError("restore_not_private")
            restored_guest = service.guest_read(slug=PROOF_PUBLIC_SLUG)
            if (restored_guest.get("read_state") != "current"
                    or _json_contains(restored_guest.get("display"), PROOF_ENTRY_KEY)):
                raise EngineProofError("restore_public_exclusion_missing")
            # Restore must stay private. Once that boundary is proven, the
            # owner explicitly grants display before later guest-edit oracles.
            regranted = service.policy_service.commit(
                user_key,
                {
                    "request_id": "00000000-0000-4000-8000-0000000000d8",
                    "type": "change_permissions",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_access_revision": int(restored_private["access_revision"]),
                    "permissions": {"resume_display": True, "visitor_ai": False},
                },
            )
            regranted_state = capture_publication_state(seed_connection)
            if (regranted.get("receipt", {}).get("type") != "change_permissions"
                    or not regranted_state.get("resume_display")
                    or regranted_state.get("visitor_ai")
                    or not _json_contains(regranted_state.get("display_json"), PROOF_CORRECTED_SUMMARY)):
                raise EngineProofError("restore_explicit_display_regrant_missing")
            publish_reviewed(
                seed_connection, user_key, "00000000-0000-4000-8000-0000000000d7", digest
            )
            restored = capture_publication_state(seed_connection)
            if restored.get("canonical_summary") != snapshot.get("canonical_summary") or not restored.get("sharing_enabled"):
                raise EngineProofError("invalid_correction_mutated")
            versions["content"] = int(restored.get("content_version") or versions["content"])
            versions["access"] = int(restored.get("access_revision") or versions["access"])

        run_case("correction_rejects_missing_foreign_deleted_stale", _invalid_targets)

        def _production_repository():
            row = repository.get_owner_publication(user_key)
            if row is None:
                raise EngineProofError("production_repository_read_missing")

        run_case("production_repository_commit_and_read", _production_repository)

        def _receipt_replay():
            replay = repository.commit_command(
                user_key,
                "00000000-0000-4000-8000-0000000000c2",
                {
                    "type": "correct",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_content_version": first_correct_versions["content"],
                    "expected_access_revision": first_correct_versions["access"],
                    "values": {
                        "summary": PROOF_CORRECTED_SUMMARY,
                        "wording": PROOF_CORRECTED_SUMMARY,
                        "role_title": "Lead",
                        "employer_name": "PeerSlate",
                    },
                },
            )
            if not replay.get("replayed"):
                raise EngineProofError("receipt_replay_missing")
            if capture_publication_state(seed_connection).get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
                raise EngineProofError("receipt_replay_mutated")

        run_case("receipt_replay", _receipt_replay)

        def _receipt_conflict():
            from services.resume_publication_repository import PublicationConflictError

            try:
                repository.commit_command(
                    user_key,
                    "00000000-0000-4000-8000-0000000000c2",
                    {
                        "type": "correct",
                        "entry_key": PROOF_ENTRY_KEY,
                        "expected_content_version": versions["content"],
                        "expected_access_revision": versions["access"],
                        "values": {
                            "summary": "Led team conflict.",
                            "wording": "Led team conflict.",
                            "role_title": "Lead",
                            "employer_name": "PeerSlate",
                        },
                    },
                )
                raise EngineProofError("receipt_conflict_missing")
            except PublicationConflictError as error:
                if getattr(error, "code", "") != "request_conflict":
                    raise EngineProofError("receipt_conflict_missing") from error
            if capture_publication_state(seed_connection).get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
                raise EngineProofError("receipt_conflict_mutated")

        run_case("receipt_conflict_changed_body", _receipt_conflict)

        def _production_service():
            from services.my_data_service import MyDataService

            reviewed = service.review_for_owner(user_key, {})
            if reviewed.reviewed is None:
                raise EngineProofError(f"production_service_review_missing:{reviewed.reason}")
            published = service.commit(
                user_key,
                {
                    "request_id": "00000000-0000-4000-8000-0000000000c3",
                    "type": "publish",
                    "reviewed_digest": reviewed.reviewed.digest,
                    "slug": PROOF_PUBLIC_SLUG,
                    "media": {
                        "portrait": {
                            "active": True,
                            "source_kind": "upload",
                            "source_key": "synthetic-portrait",
                            "asset_version": 1,
                            "content_sha256": "e" * 64,
                        }
                    },
                },
            )
            if published.get("outcome") != "published":
                raise EngineProofError("production_service_publish_missing")
            state = observe_state()
            corrected = service.commit(
                user_key,
                {
                    "request_id": "00000000-0000-4000-8000-0000000000c4",
                    "type": "correct",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_content_version": int(state["content_version"]),
                    "expected_access_revision": int(state["access_revision"]),
                    "values": {
                        "summary": "Service corrected wording.",
                        "wording": "Service corrected wording.",
                        "role_title": "Lead",
                        "employer_name": "PeerSlate",
                    },
                },
            )
            if (not corrected.get("committed")
                    or observe_state().get("canonical_summary") != "Service corrected wording."):
                raise EngineProofError("production_service_correct_missing")
            state = observe_state()
            if state.get("approved_wording") != "Service corrected wording.":
                raise EngineProofError("production_service_correct_approved_wording_missing")
            # The form can change Wording alone, including capitalization,
            # while it sends the unchanged Summary alias and both versions.
            wording_only_value = "Service corrected WORDING."
            wording_only_payload = {
                "request_id": "00000000-0000-4000-8000-0000000000c9",
                "type": "edit",
                "entry_key": PROOF_ENTRY_KEY,
                "expected_content_version": int(state["content_version"]),
                "expected_access_revision": int(state["access_revision"]),
                "values": {"summary": "Service corrected wording.",
                           "wording": wording_only_value,
                           "role_title": "Lead", "employer_name": "PeerSlate"},
            }
            wording_only = service.policy_service.commit(user_key, wording_only_payload)
            wording_state = observe_state()
            wording_failures = []
            if wording_only.get("receipt", {}).get("type") != "edit":
                wording_failures.append("receipt")
            if wording_state.get("canonical_summary") != wording_only_value:
                wording_failures.append("canonical_summary")
            if wording_state.get("approved_wording") != wording_only_value:
                wording_failures.append("approved_wording")
            if int(wording_state["content_version"]) != int(state["content_version"]) + 1:
                wording_failures.append("content_version")
            if not _json_contains(wording_state.get("display_json"), wording_only_value):
                wording_failures.append("display_json")
            if wording_failures:
                raise EngineProofError("my_data_wording_only_missing:" + ",".join(wording_failures))
            if not any(entry.get("entry_key") == PROOF_ENTRY_KEY
                       and (entry.get("values") or {}).get("summary") == wording_only_value
                       for entry in wording_only.get("entries") or []):
                raise EngineProofError("my_data_wording_only_reader_missing")
            wording_guest = service.guest_read(slug=PROOF_PUBLIC_SLUG)
            if (wording_guest.get("read_state") != "current"
                    or not _json_contains(wording_guest.get("display"), wording_only_value)):
                raise EngineProofError("my_data_wording_only_guest_missing")
            wording_replay = service.policy_service.commit(user_key, wording_only_payload)
            if not wording_replay.get("replayed") or observe_state() != wording_state:
                raise EngineProofError("my_data_wording_only_replay_changed_state")
            stale_wording = dict(wording_only_payload, request_id="00000000-0000-4000-8000-0000000000cb")
            try:
                service.policy_service.commit(user_key, stale_wording)
            except Exception:
                pass
            else:
                raise EngineProofError("my_data_wording_only_stale_edit_accepted")
            if observe_state() != wording_state:
                raise EngineProofError("my_data_wording_only_stale_edit_mutated")
            state = observe_state()
            # The real form submits every displayed field. The member edits
            # Summary alone, leaving the Wording alias at its prior value.
            my_data_payload = {
                "request_id": "00000000-0000-4000-8000-0000000000c5",
                "type": "edit",
                "entry_key": PROOF_ENTRY_KEY,
                "expected_content_version": int(state["content_version"]),
                "expected_access_revision": int(state["access_revision"]),
                "values": {"summary": PROOF_CORRECTED_SUMMARY,
                           "wording": wording_only_value,
                           "role_title": "Lead", "employer_name": "PeerSlate"},
            }
            my_data_corrected = service.policy_service.commit(user_key, my_data_payload)
            edited_state = observe_state()
            if (my_data_corrected.get("receipt", {}).get("type") != "edit"
                    or edited_state.get("canonical_summary") != PROOF_CORRECTED_SUMMARY
                    or edited_state.get("approved_wording") != PROOF_CORRECTED_SUMMARY
                    or int(edited_state["content_version"]) != int(state["content_version"]) + 1):
                raise EngineProofError("my_data_correction_missing")
            if not any(entry.get("entry_key") == PROOF_ENTRY_KEY
                       and (entry.get("values") or {}).get("summary") == PROOF_CORRECTED_SUMMARY
                       for entry in my_data_corrected.get("entries") or []):
                raise EngineProofError("my_data_reader_correction_missing")
            replay = service.policy_service.commit(user_key, my_data_payload)
            if not replay.get("replayed") or observe_state() != edited_state:
                raise EngineProofError("my_data_edit_replay_changed_state")
            stale_payload = dict(my_data_payload, request_id="00000000-0000-4000-8000-0000000000c8")
            try:
                service.policy_service.commit(user_key, stale_payload)
            except Exception:
                pass
            else:
                raise EngineProofError("my_data_stale_edit_accepted")
            if observe_state() != edited_state:
                raise EngineProofError("my_data_stale_edit_mutated")
            corrected_guest = service.guest_read(slug=PROOF_PUBLIC_SLUG)
            if (corrected_guest.get("read_state") != "current"
                    or not _json_contains(corrected_guest.get("display"), PROOF_CORRECTED_SUMMARY)):
                raise EngineProofError("my_data_guest_correction_missing")
            state = observe_state()
            my_data_restricted = service.policy_service.commit(
                user_key,
                {
                    "request_id": "00000000-0000-4000-8000-0000000000c6",
                    "type": "change_permissions",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_access_revision": int(state["access_revision"]),
                    "permissions": {"resume_display": False, "visitor_ai": False},
                },
            )
            restricted = observe_state()
            if (my_data_restricted.get("receipt", {}).get("type") != "change_permissions"
                    or restricted.get("resume_display") or restricted.get("visitor_ai")
                    or _json_contains(restricted.get("display_json"), PROOF_CORRECTED_SUMMARY)
                    or _json_contains(restricted.get("visitor_ai_json"), PROOF_CORRECTED_SUMMARY)):
                raise EngineProofError("my_data_restriction_missing")
            restricted_guest = service.guest_read(slug=PROOF_PUBLIC_SLUG)
            if (restricted_guest.get("read_state") != "current"
                    or _json_contains(restricted_guest.get("display"), PROOF_ENTRY_KEY)):
                raise EngineProofError("my_data_guest_restriction_missing")

            class EmptyIntake:
                def get_workspace(self, _owner):
                    return {"pending_proposals": []}

            my_data = MyDataService(entry_policy=service.policy_service, intake=EmptyIntake())
            inventory = my_data.overview(user_key, permission="private")
            if inventory.get("entries_state") != "ready" or inventory.get("visible_count") < 1:
                raise EngineProofError("my_data_restriction_missing")
            visible_entries = [entry for group in inventory.get("groups") or []
                               for entry in group.get("entries") or []]
            if not any(entry.get("entry_key") == PROOF_ENTRY_KEY
                       and (entry.get("values") or {}).get("summary") == PROOF_CORRECTED_SUMMARY
                       for entry in visible_entries):
                raise EngineProofError("my_data_corrected_inventory_missing")
            service.commit(
                user_key,
                {
                    "request_id": "00000000-0000-4000-8000-0000000000c7",
                    "type": "change_permissions",
                    "entry_key": PROOF_ENTRY_KEY,
                    "expected_access_revision": int(restricted["access_revision"]),
                    "permissions": {"resume_display": True, "visitor_ai": False},
                },
            )
            restored = observe_state()
            if not restored.get("resume_display") or restored.get("visitor_ai"):
                raise EngineProofError("production_service_restore_missing")
            versions["content"] = int(restored["content_version"])
            versions["access"] = int(restored["access_revision"])

        run_case("production_service_publish_correct_restrict", lambda: _effective_principal(seed_connection, "peerslate_app", _production_service))
        def _guest_readers():
            guest = service.guest_read(slug=PROOF_PUBLIC_SLUG)
            if guest.get("read_state") != "current" or not guest.get("sharing_enabled"):
                raise EngineProofError("guest_json_missing")
            if not _json_contains(guest.get("display"), PROOF_CORRECTED_SUMMARY):
                raise EngineProofError("guest_json_stale")
            html = render_guest_publication_html(guest)
            if "Published Resume" not in html or PROOF_CORRECTED_SUMMARY not in html:
                raise EngineProofError("guest_html_stale")
            media = service.authorize_media(slug=PROOF_PUBLIC_SLUG, slot="portrait")
            if not media.get("authorized") or not media.get("rechecked"):
                raise EngineProofError("guest_media_denied")

            class SyntheticBytesPort:
                def read(self, _authorization):
                    return b"synthetic-portrait-bytes"

            service.media_bytes_port = SyntheticBytesPort()
            delivered = service.deliver_guest_media(slug=PROOF_PUBLIC_SLUG, slot="portrait")
            if delivered.get("body") != b"synthetic-portrait-bytes" or not delivered.get("rechecked"):
                raise EngineProofError("guest_media_delivery_failed")

        run_case("guest_html_json_media_readers", lambda: _effective_principal(seed_connection, "peerslate_app", _guest_readers))
        def _populated_seed_present():
            state = capture_publication_state(seed_connection)
            if not state.get("owner_present") or state.get("canonical_summary") != PROOF_CORRECTED_SUMMARY:
                raise EngineProofError("populated_seed_missing")
            verify(populated_identity)
            try:
                apply_rollback(populated_identity)
            except Exception as error:
                if not is_expected_populated_publication_rollback_refusal(error):
                    raise EngineProofError(
                        "populated_rollback_wrong_refusal:"
                        + sanitize_proof_error(error)[:2048]
                    ) from error
            else:
                raise EngineProofError("populated_rollback_destroyed_schema")
            if capture_publication_state(seed_connection) != state:
                raise EngineProofError("populated_rollback_mutated_state")
            verify(populated_identity)

        run_case("populated_database_seed_and_oracles", _populated_seed_present)
        run_case(
            "schema_permissions_constraints",
            lambda: assert_application_principal_permissions(seed_connection, principal),
        )
    finally:
        seed_connection.close()

    publish = _json_command(
        type="publish", reviewed_digest="b" * 64, slug=PROOF_PUBLIC_SLUG,
        media={
            "portrait": {"active": True, "source_kind": "upload",
                         "source_key": "synthetic-portrait", "asset_version": 1,
                         "content_sha256": "e" * 64},
            "illustration": {"active": True, "source_kind": "generated_illustration",
                             "source_key": PROOF_CATALOG_ASSET_ID, "asset_version": 1,
                             "content_sha256": "c" * 64},
        },
    )
    race_correct = _json_command(
        type="correct",
        entry_key=PROOF_ENTRY_KEY,
        expected_content_version=versions["content"],
        expected_access_revision=versions["access"],
        values={
            "summary": PROOF_RACE_SUMMARY,
            "wording": PROOF_RACE_SUMMARY,
            "role_title": "Lead",
            "employer_name": "PeerSlate",
        },
    )
    sharing = _json_command(type="sharing_off")
    policy = _json_command(
        type="change_permissions",
        entry_key=PROOF_ENTRY_KEY,
        expected_access_revision=versions["access"],
        permissions={"resume_display": False, "visitor_ai": False},
    )
    delete_cmd = _json_command(type="delete", entry_key=PROOF_ENTRY_KEY)
    restore_cmd = _json_command(type="restore", entry_key=PROOF_ENTRY_KEY)
    draft_cmd = _json_command(
        type="save_item", expected_draft_version=0,
        request_digest="d" * 64, record_key=PROOF_ENTRY_KEY,
        record_type="role", expected_content_token=str(versions["content"]),
        expected_access_revision=versions["access"],
        values={"summary": "Draft only."},
    )
    media_cmd = _json_command(type="media_restrict", slot="portrait")
    catalog_cmd = _json_command(type="catalog_withdraw", asset_id=PROOF_CATALOG_ASSET_ID, version=1)

    def race_pair(case_name, pair, left, right, left_id, right_id):
        def body():
            preparation = populated_connect(populated_identity)
            try:
                state = capture_publication_state(preparation)
                if pair == "publish_versus_restore":
                    if state.get("lifecycle") == "active":
                        execute_procedure(preparation, "usp_CommitResumePublicationCommandForOwner",
                                          _commit_parameters(user_key, {"request_id": str(uuid4()),
                                              "json": _json_command(type="delete", entry_key=PROOF_ENTRY_KEY)}))
                else:
                    if state.get("lifecycle") == "deleted":
                        execute_procedure(preparation, "usp_CommitResumePublicationCommandForOwner",
                                          _commit_parameters(user_key, {"request_id": str(uuid4()),
                                              "json": _json_command(type="restore", entry_key=PROOF_ENTRY_KEY,
                                                                    expected_access_revision=int(state["access_revision"]))}))
                    state = capture_publication_state(preparation)
                    if not state.get("resume_display"):
                        execute_procedure(preparation, "usp_CommitResumePublicationCommandForOwner",
                                          _commit_parameters(user_key, {"request_id": str(uuid4()),
                                              "json": _json_command(type="change_permissions", entry_key=PROOF_ENTRY_KEY,
                                                  expected_access_revision=state["access_revision"],
                                                  permissions={"resume_display": True, "visitor_ai": False})}))
                    publish_reviewed(preparation, user_key, str(uuid4()), "b" * 64)
                state = capture_publication_state(preparation)
                if pair != "publish_versus_restore" and (state.get("lifecycle") != "active" or not state.get("resume_display")):
                    raise EngineProofError("race_setup_not_active")
                if pair == "publish_versus_restore" and state.get("lifecycle") != "deleted":
                    raise EngineProofError("race_setup_not_deleted")
                left_payload = json.loads(left)
                right_payload = json.loads(right)
                left_payload["expected_publication_revision"] = int(state["publication_revision"])
                if pair == "publish_versus_policy_restriction":
                    right_payload["expected_access_revision"] = int(state["access_revision"])
                if pair == "publish_versus_restore":
                    right_payload["expected_access_revision"] = int(state["access_revision"])
                if pair == "publish_versus_draft_change":
                    right_payload["expected_draft_version"] = int(state.get("draft_version") or 0)
                    right_payload["expected_content_token"] = str(state["content_version"])
                    right_payload["expected_access_revision"] = int(state["access_revision"])
                if pair == "publish_versus_catalog_withdraw" and state.get("catalog_lifecycle") != "active":
                    raise EngineProofError("race_catalog_not_active")
            finally:
                preparation.close()
            result = run_two_connection_race(
                populated_identity,
                user_key,
                user_key,
                {"request_id": left_id, "json": _json_command(**left_payload)},
                {"request_id": right_id, "json": _json_command(**right_payload)},
                connect=populated_connect,
                pair=pair,
                observe=capture_publication_state,
            )
            if pair == "publish_versus_draft_change" and result["final_state"].get("canonical_summary") != state.get("canonical_summary"):
                raise EngineProofError("race_draft_changed_canonical")
            if pair == "publish_versus_catalog_withdraw":
                from services.resume_publication_repository import PublicationDenied

                reader_connection = populated_connect(populated_identity)
                try:
                    _, reader = production_publication_stack(reader_connection)
                    if result["final_state"].get("catalog_lifecycle") == "withdrawn":
                        with _expect_publication_error(PublicationDenied, "withdrawn_catalog_media_allowed"):
                            reader.authorize_media(slug=PROOF_PUBLIC_SLUG, slot="illustration")
                    elif not reader.authorize_media(slug=PROOF_PUBLIC_SLUG, slot="illustration").get("authorized"):
                        raise EngineProofError("active_catalog_media_denied")
                finally:
                    reader_connection.close()

        run_case(case_name, body)

    race = None

    def _correction_race():
        nonlocal race
        race = run_two_connection_race(
            populated_identity,
            user_key,
            user_key,
            {"request_id": "11111111-1111-4111-8111-111111111111", "json": publish},
            {"request_id": "22222222-2222-4222-8222-222222222222", "json": race_correct},
            connect=populated_connect,
            pair="publish_versus_correction",
            observe=capture_publication_state,
        )

    run_case("publish_versus_correction", _correction_race)
    revoke_race = None

    def _revoke_race():
        nonlocal revoke_race
        revoke_race = run_two_connection_race(
            populated_identity,
            user_key,
            user_key,
            {"request_id": "44444444-4444-4444-8444-444444444444", "json": publish},
            {"request_id": "55555555-5555-4555-8555-555555555555", "json": sharing},
            connect=populated_connect,
            pair="publish_versus_revocation",
            observe=capture_publication_state,
        )

    run_case("publish_versus_sharing_off", _revoke_race)
    race_pair(
        "publish_versus_policy_restriction",
        "publish_versus_policy_restriction",
        publish,
        policy,
        "66666666-6666-4666-8666-666666666661",
        "66666666-6666-4666-8666-666666666662",
    )
    race_pair(
        "publish_versus_delete",
        "publish_versus_delete",
        publish,
        delete_cmd,
        "77777777-7777-4777-8777-777777777771",
        "77777777-7777-4777-8777-777777777772",
    )
    race_pair(
        "publish_versus_restore",
        "publish_versus_restore",
        publish,
        restore_cmd,
        "88888888-8888-4888-8888-888888888881",
        "88888888-8888-4888-8888-888888888882",
    )
    race_pair(
        "publish_versus_draft_change",
        "publish_versus_draft_change",
        publish,
        draft_cmd,
        "99999999-9999-4999-8999-999999999991",
        "99999999-9999-4999-8999-999999999992",
    )
    race_pair(
        "publish_versus_media_restrict",
        "publish_versus_media_restrict",
        publish,
        media_cmd,
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
    )
    race_pair(
        "publish_versus_catalog_withdraw",
        "publish_versus_catalog_withdraw",
        publish,
        catalog_cmd,
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1",
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2",
    )

    def _revoke_before_response():
        setup = populated_connect(populated_identity)
        try:
            publish_reviewed(setup, user_key, str(uuid4()), "b" * 64)
            if not capture_publication_state(setup).get("sharing_enabled"):
                raise EngineProofError("revoke_setup_not_shared")
        finally:
            setup.close()
        connection = populated_connect(populated_identity)
        try:
            _, guest_service = production_publication_stack(connection)
            from services.resume_publication_repository import PublicationDenied

            class RevokingBytesPort:
                read_count = 0

                def read(self, _authorization):
                    self.read_count += 1
                    revoker = populated_connect(populated_identity)
                    try:
                        execute_procedure(
                            revoker, "usp_CommitResumePublicationCommandForOwner",
                            _commit_parameters(user_key, {"request_id": str(uuid4()),
                                "json": _json_command(type="sharing_off")}),
                        )
                    finally:
                        revoker.close()
                    return b"bytes-must-not-escape"

            port = RevokingBytesPort()
            guest_service.media_bytes_port = port
            with _expect_publication_error(PublicationDenied, "revoke_delivered_bytes"):
                guest_service.deliver_guest_media(slug=PROOF_PUBLIC_SLUG, slot="portrait")
            if port.read_count != 1 or capture_publication_state(connection).get("sharing_enabled"):
                raise EngineProofError("revoke_final_state")
        finally:
            connection.close()

    run_case("revoke_before_response_commit", _revoke_before_response)

    injected = None

    def _injected_rollback():
        nonlocal injected
        injected = run_injected_rollback(
            populated_identity,
            user_key,
            {"request_id": "33333333-3333-4333-8333-333333333333", "json": publish},
            connect=populated_connect,
            capture_state=capture_publication_state,
        )
        if not injected.get("rolled_back"):
            raise EngineProofError("injected_rollback_missing")

    run_case("injected_rollback_after_evidence", _injected_rollback)

    connection = populated_connect(populated_identity)
    try:
        fields = codec_fields or {
            "canonical_type": "role",
            "role_title": "Lead",
            "employer_name": "PeerSlate",
            "location_text": None,
            "summary": PROOF_SEED_SUMMARY,
            "start_date": None,
            "end_date": None,
            "date_precision": None,
            "employment_type": None,
            "current_role": False,
            "title": None,
            "institution_name": None,
            "degree_name": None,
            "field_of_study": None,
            "education_status": None,
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
        codec = run_codec_and_evidence(connection, fields)
        permissions = assert_application_principal_permissions(connection, principal)

        def _effective_app():
            _effective_principal(
                connection,
                "peerslate_app",
                lambda: _expect_sql_permission_denial(
                    lambda: execute_procedure(
                        connection,
                        "usp_ResumePublicationApplyCanonicalInternal",
                        [("@ProfileId", 1), ("@CommandJson", "{}")],
                    )
                ),
            )

        run_case("application_principal_effective_denial", _effective_app)

        def _restricted():
            restricted = populated_connect(populated_identity)
            try:
                _effective_principal(
                    restricted,
                    "peerslate_restricted",
                    lambda: _expect_sql_permission_denial(
                        lambda: execute_procedure(
                            restricted,
                            "usp_CommitResumePublicationCommandForOwner",
                            _commit_parameters(
                                user_key,
                                {
                                    "request_id": "cccccccc-cccc-4ccc-8ccc-ccccccccccc1",
                                    "json": publish,
                                },
                            ),
                        )
                    ),
                )
            finally:
                restricted.close()

        run_case("restricted_principal_direct_denial", _restricted)

        def _cross_owner():
            from services.resume_publication_repository import PublicationDenied

            before_owner = observe_state()
            before_foreign = observe_foreign_policy()
            if len(before_foreign) != 1:
                raise EngineProofError("cross_owner_seed_missing")
            foreign_repo, _service = production_publication_stack(connection)
            with _expect_publication_error(PublicationDenied, "cross_owner_allowed"):
                foreign_repo.commit_command(
                    second_user_key,
                    "dddddddd-dddd-4ddd-8ddd-ddddddddddd1",
                    {
                        "type": "correct",
                        "entry_key": PROOF_ENTRY_KEY,
                        "expected_content_version": versions["content"],
                        "expected_access_revision": versions["access"],
                        "values": {
                            "summary": "Led team stolen.",
                            "wording": "Led team stolen.",
                            "role_title": "Lead",
                            "employer_name": "PeerSlate",
                        },
                    },
                )
            def direct_sql(statement):
                cursor = connection.cursor()
                try:
                    cursor.execute(statement, (PROOF_FOREIGN_ENTRY_KEY,))
                    cursor.fetchall()
                finally:
                    cursor.close()

            _expect_sql_permission_denial(
                lambda: direct_sql("SELECT entry_key FROM dbo.entry_policy_records WHERE entry_key = ?")
            )
            _expect_sql_permission_denial(
                lambda: direct_sql("UPDATE dbo.entry_policy_records SET resume_display = 1 WHERE entry_key = ?")
            )
            _expect_sql_permission_denial(
                lambda: direct_sql("DELETE FROM dbo.entry_policy_records WHERE entry_key = ?")
            )
            if observe_state() != before_owner or observe_foreign_policy() != before_foreign:
                raise EngineProofError("cross_owner_mutated")

        run_case("cross_owner_denial", lambda: _effective_principal(connection, "peerslate_app", _cross_owner))
        final_state = capture_publication_state(connection)
    finally:
        connection.close()
    assert_executed_mandatory_cases(executed)
    return {
        "status": "pass",
        "prepared_not_executed": False,
        "oracles": {
            "migration_closure": migration,
            "mandatory_cases": executed,
            "mandatory_case_count": len(executed),
            "seed": {"user_key_present": bool(user_key), "entry_key": PROOF_ENTRY_KEY,
                     "initial_entries": initial_entry_count,
                     "owner_a_entries": owner_a_count, "owner_b_entries": owner_b_count},
            "correction_wording": {
                "before": PROOF_SEED_SUMMARY,
                "after": PROOF_CORRECTED_SUMMARY,
                "changed": True,
            },
            "two_connection_race": race,
            "publish_versus_revocation_race": revoke_race,
            "injected_rollback": injected,
            "codec_and_evidence": codec,
            "sequence_contracts": sequence_contracts,
            "verifier_mutations": verifier_mutations,
            "permissions": {
                "internal_denied_present": permissions["internal_denied_present"],
                "internal_denied": permissions["internal_denied"],
                "principal": permissions["principal"],
            },
            "final_state": {
                "sharing_enabled": final_state.get("sharing_enabled"),
                "canonical_summary": final_state.get("canonical_summary"),
                "resume_display": final_state.get("resume_display"),
                "visitor_ai": final_state.get("visitor_ai"),
            },
            "database": PROOF_POPULATED_DATABASE,
            "empty_database": PROOF_EMPTY_DATABASE,
        },
    }


def cleanup_owned_resources(runtime, owned: list[dict[str, Any]]) -> dict[str, Any]:
    """Attempt every owned resource, preserve identity checks, verify absence."""

    attempts = []
    failed = False
    deadline = time.monotonic() + PROOF_CLEANUP_WINDOW_SECONDS
    if isinstance(runtime, IsolatedDockerCliRuntime):
        runtime.cleanup_deadline = deadline
    for resource in reversed(list(owned or [])):
        name = resource.get("name")
        attempt = {
            "name": name,
            "kind": resource.get("kind"),
            "id": resource.get("id"),
            "marker": resource.get("marker"),
            "uncertain": bool(resource.get("uncertain")),
            "observed_id": None,
            "observed_marker": None,
            "name_absent_verified": False,
            "id_absent_verified": None,
            "status": "error",
        }
        if time.monotonic() > deadline:
            failed = True
            attempt["status"] = "timeout"
            attempts.append(attempt)
            continue
        try:
            try:
                current = runtime.inspect(name)
            except EngineProofError as error:
                if resource.get("uncertain") and str(error).startswith("docker_resource_not_found:"):
                    # A timed-out create may still complete in the daemon.
                    # A single not-found observation cannot close its custody.
                    failed = True
                    attempt["status"] = "unverified_uncertain_create"
                    attempts.append(attempt)
                    continue
                raise
            attempt["observed_id"] = current.get("id")
            attempt["observed_marker"] = current.get("marker")
            if (current.get("marker") != resource.get("marker")
                    or not current.get("id")
                    or (resource.get("id") is not None and current.get("id") != resource.get("id"))):
                failed = True
                attempt["status"] = "identity_mismatch"
                attempts.append(attempt)
                continue
            last_error = None
            for retry in range(PROOF_CLEANUP_RETRY + 1):
                try:
                    remove = getattr(runtime, "remove")
                    kind = resource.get("kind") or "container"
                    if kind == "image" and hasattr(runtime, "remove_image"):
                        runtime.remove_image(name, resource.get("id"))
                    else:
                        remove(name)
                    last_error = None
                    break
                except Exception as error:
                    last_error = error
                    if retry >= PROOF_CLEANUP_RETRY:
                        raise
            if last_error is not None:
                raise last_error
            if _resource_present(runtime, name):
                failed = True
                attempt["status"] = "still_present"
            else:
                attempt["name_absent_verified"] = True
                probe_id = getattr(runtime, "resource_id_present", None)
                if callable(probe_id):
                    id_absent = not probe_id(resource.get("kind") or "container", current["id"])
                    attempt["id_absent_verified"] = id_absent
                    if not id_absent:
                        failed = True
                        attempt["status"] = "still_present"
                    else:
                        attempt["status"] = "removed"
                elif isinstance(runtime, IsolatedDockerCliRuntime):
                    failed = True
                    attempt["status"] = "id_absence_unverified"
                else:
                    attempt["status"] = "removed"
        except EngineProofError as error:
            failed = True
            attempt["status"] = "error"
            if "command_timeout" in str(error):
                attempt["status"] = "timeout"
        except Exception:
            failed = True
            attempt["status"] = "error"
        attempts.append(attempt)
    if isinstance(runtime, IsolatedDockerCliRuntime):
        runtime.cleanup_deadline = None
    return {
        "status": "fail" if failed else "pass",
        "attempts": attempts,
        "cleaned": [item["name"] for item in attempts if item.get("status") == "removed"],
    }


def acquire_isolated_sql_runtime(
    runtime,
    *,
    source_root: Path | None = None,
    wheelhouse: Path | None = None,
    owned: list[dict[str, Any]] | None = None,
    expected_manifest: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the hashed client image and register isolated runtime custody."""

    owned = owned if owned is not None else []
    root = source_root or Path(__file__).resolve().parents[1]
    names = (PROOF_CLIENT_IMAGE_NAME, PROOF_NETWORK, PROOF_SQL_CONTAINER, PROOF_CLIENT_CONTAINER)
    for name in names:
        if runtime.exists(name):
            raise EngineProofError(f"preexisting_resource:{name}")
    if wheelhouse is None:
        env_house = os.environ.get("PEERSLATE_RESUME_PUBLICATION_WHEELHOUSE", "").strip()
        if env_house:
            wheelhouse = Path(env_house)
        else:
            prepare = getattr(runtime, "prepare_hashed_wheelhouse", None)
            if not callable(prepare):
                raise EngineProofError("wheelhouse_required")
            wheelhouse = Path(prepare())
    verify = getattr(runtime, "verify_downloaded_wheelhouse", verify_downloaded_wheelhouse)
    wheel_proof = verify(Path(wheelhouse))
    manifest = expected_manifest or source_manifest(root)
    invocation_marker = str(getattr(runtime, "invocation_marker", PROOF_ID))

    def register(name: str, created: dict[str, Any], kind: str, step: str) -> None:
        owned.append(
            {
                "name": name,
                "id": created["id"],
                "marker": created.get("marker") or invocation_marker,
                "kind": kind,
            }
        )
        _fail_after(runtime, step)

    def create_with_custody(name: str, kind: str, step: str, create):
        try:
            created = create()
        except Exception:
            # A CLI timeout can follow a successful daemon-side create. Keep the
            # exact name and invocation marker in custody until cleanup proves
            # absence or verifies and removes this invocation's resource.
            partial = None
            inspect_partial = getattr(runtime, "inspect", None)
            if callable(inspect_partial):
                try:
                    partial = inspect_partial(name)
                except Exception:
                    pass
            if partial and partial.get("id") and partial.get("marker") == invocation_marker:
                owned.append({"name": name, "id": partial["id"],
                              "marker": invocation_marker, "kind": kind})
            else:
                owned.append({"name": name, "id": None, "marker": invocation_marker,
                              "kind": kind, "uncertain": True})
            raise
        register(name, created, kind, step)
        return created

    built = create_with_custody(
        PROOF_CLIENT_IMAGE_NAME, "image", "build",
        lambda: runtime.build_client_image(root, Path(wheelhouse), manifest),
    )
    client_image_id = built["id"]
    inspect = getattr(runtime, "inspect", None)
    if callable(inspect):
        inspected_image = inspect(PROOF_CLIENT_IMAGE_NAME)
        if inspected_image.get("id") != client_image_id or inspected_image.get("marker") != invocation_marker:
            raise EngineProofError("cleanup_identity_mismatch")

    network = create_with_custody(
        PROOF_NETWORK, "network", "network",
        lambda: runtime.create_network(PROOF_NETWORK, internal=True, marker=invocation_marker),
    )
    if callable(inspect):
        inspected_network = inspect(PROOF_NETWORK)
        if inspected_network.get("id") != network["id"] or inspected_network.get("marker") != invocation_marker:
            raise EngineProofError("cleanup_identity_mismatch")
    sql = create_with_custody(
        PROOF_SQL_CONTAINER, "container", "sql",
        lambda: runtime.start_sql(
            PROOF_SQL_CONTAINER, image=SQL_IMAGE, network=PROOF_NETWORK,
            marker=invocation_marker, publish_host_ports=False,
        ),
    )
    if callable(inspect):
        inspected_sql = inspect(PROOF_SQL_CONTAINER)
        if inspected_sql.get("id") != sql["id"] or inspected_sql.get("marker") != invocation_marker:
            raise EngineProofError("cleanup_identity_mismatch")
    wait_sql = getattr(runtime, "wait_for_sql", None)
    if callable(wait_sql):
        wait_sql(PROOF_SQL_CONTAINER)
    _fail_after(runtime, "sql_ready")
    client = create_with_custody(
        PROOF_CLIENT_CONTAINER, "container", "client",
        lambda: runtime.start_client(
            PROOF_CLIENT_CONTAINER, image=client_image_id, network=PROOF_NETWORK,
            marker=invocation_marker, publish_host_ports=False,
        ),
    )
    if callable(inspect):
        inspected_client = inspect(PROOF_CLIENT_CONTAINER)
        if inspected_client.get("id") != client["id"] or inspected_client.get("marker") != invocation_marker:
            raise EngineProofError("cleanup_identity_mismatch")
    copied = getattr(runtime, "verify_copied_client_source", None)
    if not callable(copied) or copied(PROOF_CLIENT_CONTAINER, manifest) != manifest:
        raise EngineProofError("client_source_digest_mismatch")
    _fail_after(runtime, "client_source_digest")
    inspect_client_runtime = getattr(runtime, "inspect_client_runtime", None)
    client_runtime = (inspect_client_runtime() if callable(inspect_client_runtime)
                      else {"status": "unavailable"})
    identity = runtime.verify_sql_identity(sql)
    isolation = getattr(runtime, "verify_isolation", None)
    if callable(isolation):
        topology = isolation()
        identity["isolation"] = topology
        if topology.get("host_ports") or topology.get("host_mounts") or not topology.get("internal"):
            raise EngineProofError("prohibited_topology")
    if identity.get("production_connection"):
        raise EngineProofError("production_sql_forbidden")
    build = str(identity.get("sql_build") or identity.get("product_version") or "")
    edition = str(identity.get("sql_edition") or identity.get("edition") or "")
    image_id = str(identity.get("image") or identity.get("image_id") or SQL_IMAGE)
    if not build or build != PROOF_SQL_BUILD:
        raise EngineProofError("sql_build_mismatch")
    if edition and PROOF_SQL_EDITION_TOKEN.lower() not in edition.lower():
        raise EngineProofError("sql_edition_mismatch")
    if image_id and SQL_IMAGE.split("@")[-1] not in image_id and image_id != SQL_IMAGE:
        raise EngineProofError("sql_image_mismatch")
    _fail_after(runtime, "identity")
    runtime.ensure_databases((PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE))
    _fail_after(runtime, "databases")
    return {
        "owned": owned,
        "identity": identity,
        "resource_identity": f"docker:{PROOF_SQL_CONTAINER}",
        "wheelhouse": wheel_proof,
        "client_oracles": True,
        "client_packaging": PROOF_CLIENT_PACKAGING,
        "client_image_id": client_image_id,
        "client_runtime": client_runtime,
        "invocation_marker": invocation_marker,
        "source_manifest_digest": manifest_digest(manifest),
    }


class IsolatedDockerCliRuntime:
    """Pinned Docker CLI adapter. Tests intercept process execution."""

    def __init__(self, runner=None) -> None:
        self._runner = runner or _run_interruptible_docker_command
        self._sql_password = secrets.token_urlsafe(32)
        self.invocation_marker = f"{PROOF_ID}.{secrets.token_hex(12)}"

    def _docker(
        self,
        args: list[str],
        extra_env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        self._reject_isolation(args)
        deadline = getattr(self, "cleanup_deadline", None)
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineProofError("cleanup_window_expired")
            timeout = min(timeout or PROOF_COMMAND_TIMEOUT_SECONDS, remaining)
        return _timeout_docker(
            self._runner,
            args,
            extra_env,
            timeout if timeout is not None else PROOF_COMMAND_TIMEOUT_SECONDS,
        )

    def _reject_isolation(self, args: list[str]) -> None:
        forbidden = {"-p", "--publish", "-v", "--volume", "--mount"}
        for item in args:
            if item in forbidden or item.startswith("--publish=") or item.startswith("--volume=") or item.startswith("--mount="):
                raise EngineProofError("host_port_or_mount_forbidden")
            if (
                item.startswith("MSSQL_SA_PASSWORD=")
                or item.startswith("SQLCMDPASSWORD=")
                or item.startswith("PWD=")
            ):
                raise EngineProofError("secret_in_argv")
        joined = " ".join(args)
        if self._sql_password and self._sql_password in joined:
            raise EngineProofError("secret_in_argv")

    def prepare_hashed_wheelhouse(self, dest: Path | None = None) -> Path:
        target = Path(dest or tempfile.mkdtemp(prefix="resume-publication-wheels-"))
        return prepare_hashed_wheelhouse(target)

    def verify_downloaded_wheelhouse(self, wheelhouse: Path) -> dict[str, Any]:
        return verify_downloaded_wheelhouse(Path(wheelhouse))

    def build_client_image(
        self, root: Path, wheelhouse: Path, manifest: dict[str, str]
    ) -> dict[str, Any]:
        """Bake only hashed proof files and offline wheels into a tagged image."""

        with tempfile.TemporaryDirectory(prefix="resume-publication-client-build-") as directory:
            context = Path(directory)
            source = context / "source"
            wheels = context / "wheelhouse"
            source.mkdir()
            wheels.mkdir()
            for relative, digest in manifest.items():
                original = root / relative
                if original.is_symlink() or not original.is_file():
                    raise EngineProofError("client_source_untrusted_path")
                if hashlib.sha256(original.read_bytes()).hexdigest() != digest:
                    raise EngineProofError("client_source_digest_mismatch")
                destination = source / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
            for original in wheelhouse.iterdir():
                if original.is_symlink() or not original.is_file():
                    raise EngineProofError("wheelhouse_untrusted_path")
                shutil.copy2(original, wheels / original.name)
            dockerfile = context / "Dockerfile"
            dockerfile.write_text(
                f"FROM {CLIENT_IMAGE}\n"
                f"LABEL peerslate.proof_id={self.invocation_marker}\n"
                "RUN apt-get update && apt-get install -y --no-install-recommends "
                "libltdl7 libkrb5-3 libgssapi-krb5-2 && rm -rf /var/lib/apt/lists/*\n"
                f"WORKDIR {PROOF_CLIENT_REMOTE_ROOT}\n"
                f"COPY wheelhouse/ {PROOF_CLIENT_REMOTE_WHEELS}/\n"
                f"COPY source/ {PROOF_CLIENT_REMOTE_ROOT}/\n"
                "RUN python -m pip install --require-hashes --no-index "
                f"--find-links={PROOF_CLIENT_REMOTE_WHEELS} --disable-pip-version-check "
                f"--no-cache-dir -r {PROOF_CLIENT_REMOTE_LOCK}\n",
                encoding="utf-8",
            )
            image_id_file = context / "image-id"
            built = self._docker(
                [
                    "build", "--pull", "--tag",
                    PROOF_CLIENT_IMAGE_NAME, "--label", f"peerslate.proof_id={self.invocation_marker}",
                    "--iidfile", str(image_id_file), str(context),
                ],
                timeout=10 * 60,
            )
            if built.returncode != 0 or not image_id_file.is_file():
                raise EngineProofError("client_image_build_failed")
            image_id = image_id_file.read_text(encoding="utf-8").strip()
            if not image_id.startswith("sha256:"):
                raise EngineProofError("client_image_id_missing")
            return {"id": image_id, "name": PROOF_CLIENT_IMAGE_NAME, "marker": self.invocation_marker}

    def exists(self, name: str) -> bool:
        try:
            self.inspect(name)
            return True
        except EngineProofError as error:
            if str(error).startswith("docker_resource_not_found:"):
                return False
            raise

    def create_network(self, name: str, internal: bool = True, marker: str = "") -> dict[str, Any]:
        args = ["network", "create"]
        if internal:
            args.append("--internal")
        args.extend(["--label", f"peerslate.proof_id={marker or PROOF_ID}", name])
        completed = self._docker(args)
        if completed.returncode != 0:
            raise EngineProofError(f"docker_cli_failed:{completed.stderr}")
        created_id = (completed.stdout or "").strip()
        if not created_id:
            raise EngineProofError("docker_cli_failed:network_create_id")
        return {"id": created_id, "marker": marker}

    def start_sql(
        self,
        name: str,
        *,
        image: str,
        network: str,
        marker: str,
        publish_host_ports: bool = False,
    ) -> dict[str, Any]:
        if publish_host_ports:
            raise EngineProofError("host_port_publish_forbidden")
        completed = self._docker(
            [
                "run",
                "-d",
                "--name",
                name,
                "--hostname",
                name,
                "--network",
                network,
                "--memory",
                PROOF_SQL_MEMORY,
                "--cpus",
                PROOF_SQL_CPUS,
                "--pids-limit",
                PROOF_SQL_PIDS,
                "--label",
                f"peerslate.proof_id={marker}",
                "-e",
                "ACCEPT_EULA=Y",
                "-e",
                "MSSQL_SA_PASSWORD",
                image,
            ],
            extra_env={"MSSQL_SA_PASSWORD": self._sql_password},
        )
        if completed.returncode != 0:
            raise EngineProofError("docker_cli_failed:sql_start")
        created_id = (completed.stdout or "").strip()
        if not created_id:
            raise EngineProofError("docker_cli_failed:sql_start_id")
        return {"id": created_id, "marker": marker}

    def start_client(
        self,
        name: str,
        *,
        image: str,
        network: str,
        marker: str,
        publish_host_ports: bool = False,
    ) -> dict[str, Any]:
        if publish_host_ports:
            raise EngineProofError("host_port_publish_forbidden")
        completed = self._docker(
            [
                "run",
                "-d",
                "--name",
                name,
                "--network",
                network,
                "--memory",
                PROOF_CLIENT_MEMORY,
                "--cpus",
                PROOF_CLIENT_CPUS,
                "--pids-limit",
                PROOF_CLIENT_PIDS,
                "--label",
                f"peerslate.proof_id={marker}",
                image,
                "sleep",
                str(PROOF_JOB_TIMEOUT_SECONDS),
            ]
        )
        if completed.returncode != 0:
            raise EngineProofError(f"docker_cli_failed:{completed.stderr}")
        created_id = (completed.stdout or "").strip()
        if not created_id:
            raise EngineProofError("docker_cli_failed:client_start_id")
        return {"id": created_id, "marker": marker}

    def remove(self, name: str) -> None:
        if name.endswith("-net") or name == PROOF_NETWORK:
            completed = self._docker(["network", "rm", name], timeout=PROOF_CLEANUP_COMMAND_TIMEOUT_SECONDS)
        else:
            completed = self._docker(["rm", "-f", name], timeout=PROOF_CLEANUP_COMMAND_TIMEOUT_SECONDS)
        if completed.returncode != 0:
            raise EngineProofError(f"docker_cli_failed:{completed.stderr}")

    def remove_image(self, name: str, image_id: str | None = None) -> None:
        completed = self._docker(
            ["rmi", "-f", image_id or name],
            timeout=PROOF_CLEANUP_COMMAND_TIMEOUT_SECONDS,
        )
        if completed.returncode != 0:
            raise EngineProofError(f"docker_cli_failed:{completed.stderr}")

    def wait_for_sql(self, name: str = PROOF_SQL_CONTAINER) -> None:
        deadline = time.monotonic() + PROOF_SQL_READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            completed = self._docker(
                [
                    "exec",
                    "-e",
                    "SQLCMDPASSWORD",
                    name,
                    "/opt/mssql-tools18/bin/sqlcmd",
                    "-S",
                    "localhost",
                    "-U",
                    "sa",
                    "-C",
                    "-Q",
                    "SELECT 1",
                ],
                extra_env={"SQLCMDPASSWORD": self._sql_password},
                timeout=PROOF_COMMAND_TIMEOUT_SECONDS,
            )
            if completed.returncode == 0:
                return
            time.sleep(2)
        raise EngineProofError("sql_ready_timeout")

    def verify_isolation(self) -> dict[str, Any]:
        internal = self._docker(
            ["network", "inspect", "--format", "{{.Internal}}", PROOF_NETWORK]
        )
        if internal.returncode != 0 or (internal.stdout or "").strip().lower() != "true":
            raise EngineProofError("prohibited_topology")
        for container in (PROOF_SQL_CONTAINER, PROOF_CLIENT_CONTAINER):
            outputs = [
                self._docker(["inspect", "--format", "{{json .HostConfig.PortBindings}}", container]),
                self._docker(["inspect", "--format", "{{json .HostConfig.Binds}}", container]),
                self._docker(["inspect", "--format", "{{json .Mounts}}", container]),
                self._docker(["inspect", "--format", "{{json .NetworkSettings.Networks}}", container]),
            ]
            if any(item.returncode != 0 for item in outputs):
                raise EngineProofError("prohibited_topology")
            try:
                ports, binds, mounts, networks = (
                    json.loads((item.stdout or "").strip()) for item in outputs
                )
            except (TypeError, ValueError) as error:
                raise EngineProofError("prohibited_topology") from error
            if ports or binds or mounts or not isinstance(networks, dict) or set(networks) != {PROOF_NETWORK}:
                raise EngineProofError("prohibited_topology")
        return {"internal": True, "host_ports": False, "host_mounts": False}

    def verify_copied_client_source(self, container: str, expected: dict[str, str]) -> dict[str, str]:
        actual = {}
        for relative, digest in expected.items():
            completed = self._docker(
                [
                    "exec",
                    container,
                    "python",
                    "-c",
                    (
                        "import hashlib,pathlib,sys;"
                        f"p=pathlib.Path({PROOF_CLIENT_REMOTE_ROOT!r})/sys.argv[1];"
                        "sys.stdout.write(hashlib.sha256(p.read_bytes()).hexdigest())"
                    ),
                    relative,
                ]
            )
            if completed.returncode != 0:
                raise EngineProofError(f"client_source_missing:{relative}")
            actual[relative] = (completed.stdout or "").strip()
            if actual[relative] != digest:
                raise EngineProofError("client_source_digest_mismatch")
        return actual

    def inspect(self, name: str) -> dict[str, Any]:
        if name == PROOF_NETWORK:
            prefix = ["network", "inspect"]
            label_path = ".Labels"
        elif name == PROOF_CLIENT_IMAGE_NAME:
            prefix = ["image", "inspect"]
            label_path = ".Config.Labels"
        else:
            prefix = ["container", "inspect"]
            label_path = ".Config.Labels"
        identity = self._docker([*prefix, "--format", "{{.Id}}", name])
        if identity.returncode != 0:
            error = (identity.stderr or "").lower()
            missing = (
                f"no such object: {name.lower()}" in error
                or f"no such container: {name.lower()}" in error
                or f"no such image: {name.lower()}" in error
                or f"no such network: {name.lower()}" in error
                or f"network {name.lower()} not found" in error
            )
            raise EngineProofError(
                f"docker_resource_not_found:{name}" if missing else f"docker_inspect_failed:{name}"
            )
        marker = self._docker(
            [*prefix, "--format", "{{index " + label_path + " \"peerslate.proof_id\"}}", name]
        )
        if marker.returncode != 0 or not (identity.stdout or "").strip():
            raise EngineProofError(f"docker_inspect_failed:{name}")
        return {
            "id": (identity.stdout or "").strip(),
            "marker": (marker.stdout or "").strip(),
        }

    def resource_id_present(self, kind: str, resource_id: str) -> bool:
        """Recheck the acquired immutable ID after its name disappears."""

        if kind not in {"network", "container", "image"} or not resource_id:
            raise EngineProofError("resource_id_unavailable")
        completed = self._docker([kind, "inspect", "--format", "{{.Id}}", resource_id])
        if completed.returncode == 0:
            return True
        error = (completed.stderr or "").lower()
        exact_id = re.escape(resource_id.lower())
        missing = (
            rf"no such (?:object|container|image|network):\s*['\"]?{exact_id}['\"]?(?=$|\s)",
            rf"network\s+['\"]?{exact_id}['\"]?\s+not found(?=$|\s)",
        )
        if any(re.search(pattern, error) for pattern in missing):
            return False
        raise EngineProofError("resource_id_inspect_unverified")

    def inspect_client_runtime(self) -> dict[str, Any]:
        """Record actual client/driver and resolved OS library versions."""

        python = self._docker([
            "exec", PROOF_CLIENT_CONTAINER, "python", "-B", "-c",
            "import importlib.metadata,json,platform;"
            "print(json.dumps({'python':platform.python_version(),"
            "'libc':platform.libc_ver(),"
            "'mssql_python':importlib.metadata.version('mssql-python')}))",
        ])
        packages = self._docker([
            "exec", PROOF_CLIENT_CONTAINER, "dpkg-query", "-W",
            "-f=${Package}=${Version}\\n", "libltdl7", "libkrb5-3", "libgssapi-krb5-2",
        ])
        if python.returncode != 0 or packages.returncode != 0:
            raise EngineProofError("client_runtime_version_unavailable")
        try:
            versions = json.loads((python.stdout or "").strip())
            libraries = dict(line.split("=", 1) for line in (packages.stdout or "").splitlines())
        except (TypeError, ValueError) as error:
            raise EngineProofError("client_runtime_version_invalid") from error
        if (not isinstance(versions, dict) or not versions.get("python")
                or not versions.get("mssql_python")
                or set(libraries) != {"libltdl7", "libkrb5-3", "libgssapi-krb5-2"}
                or not all(libraries.values())):
            raise EngineProofError("client_runtime_version_invalid")
        return {"status": "verified", "python": versions["python"],
                "libc": versions.get("libc"), "mssql_python": versions["mssql_python"],
                "os_libraries": libraries}

    def verify_sql_identity(self, sql: dict[str, Any]) -> dict[str, Any]:
        inspect = self.inspect(PROOF_SQL_CONTAINER)
        if inspect.get("id") != sql.get("id") or inspect.get("marker") != self.invocation_marker:
            raise EngineProofError("cleanup_identity_mismatch")
        image = self._docker(["inspect", "--format", "{{.Image}}", PROOF_SQL_CONTAINER])
        pinned = self._docker(["image", "inspect", "--format", "{{.Id}}", SQL_IMAGE])
        digests = self._docker(["image", "inspect", "--format", "{{json .RepoDigests}}", SQL_IMAGE])
        running_image_id = (image.stdout or "").strip()
        pinned_image_id = (pinned.stdout or "").strip()
        if (image.returncode != 0 or pinned.returncode != 0 or digests.returncode != 0
                or not running_image_id or running_image_id != pinned_image_id
                or SQL_IMAGE.split("@")[-1] not in (digests.stdout or "")):
            raise EngineProofError("sql_image_mismatch")
        version = self._docker(
            [
                "exec",
                "-e",
                "SQLCMDPASSWORD",
                PROOF_SQL_CONTAINER,
                "/opt/mssql-tools18/bin/sqlcmd",
                "-S",
                "localhost",
                "-U",
                "sa",
                "-C",
                "-h",
                "-1",
                "-W",
                "-Q",
                "SET NOCOUNT ON; SELECT CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(32)), CAST(SERVERPROPERTY('Edition') AS nvarchar(128));",
            ],
            extra_env={"SQLCMDPASSWORD": self._sql_password},
        )
        if version.returncode != 0:
            raise EngineProofError("sql_identity_query_failed")
        parts = [item.strip() for item in (version.stdout or "").split() if item.strip()]
        build = parts[0] if parts else ""
        edition = " ".join(parts[1:]) if len(parts) > 1 else ""
        return {
            "production_connection": False,
            "database": PROOF_EMPTY_DATABASE,
            "id": inspect["id"],
            "marker": inspect["marker"],
            "image": SQL_IMAGE,
            "image_id": running_image_id,
            "sql_build": build,
            "sql_edition": edition,
        }

    def ensure_databases(self, names: tuple[str, ...] | list[str]) -> None:
        for name in names:
            if name not in {PROOF_EMPTY_DATABASE, PROOF_POPULATED_DATABASE}:
                raise EngineProofError("sql_database_not_proof_owned")
            completed = self._docker(
                [
                    "exec",
                    "-e",
                    "SQLCMDPASSWORD",
                    PROOF_SQL_CONTAINER,
                    "/opt/mssql-tools18/bin/sqlcmd",
                    "-S",
                    "localhost",
                    "-U",
                    "sa",
                    "-C",
                    "-Q",
                    f"IF DB_ID('{name}') IS NULL CREATE DATABASE [{name}]",
                ],
                extra_env={"SQLCMDPASSWORD": self._sql_password},
            )
            if completed.returncode != 0:
                raise EngineProofError("sql_database_create_failed")

    def run_client_oracles(
        self,
        *,
        source_sha: str = "",
        extra_env: dict[str, str] | None = None,
        **_ignored,
    ) -> dict[str, Any]:
        env = {
            "MSSQL_SA_PASSWORD": self._sql_password,
            "PEERSLATE_RESUME_PUBLICATION_SQL_HOST": PROOF_SQL_CONTAINER,
            "PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE": PROOF_EMPTY_DATABASE,
            "PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA": source_sha,
            "PYTHONPATH": PROOF_CLIENT_REMOTE_ROOT,
        }
        if extra_env:
            env.update(extra_env)
        completed = self._docker(
            [
                "exec",
                "-e",
                "MSSQL_SA_PASSWORD",
                "-e",
                "PEERSLATE_RESUME_PUBLICATION_SQL_HOST",
                "-e",
                "PEERSLATE_RESUME_PUBLICATION_SQL_DATABASE",
                "-e",
                "PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA",
                "-e",
                "PYTHONPATH",
                "-w",
                PROOF_CLIENT_REMOTE_ROOT,
                PROOF_CLIENT_CONTAINER,
                "python",
                "-B",
                "scripts/run_resume_publication_sql_proof.py",
                "--in-client-oracles",
                "--source-sha",
                source_sha,
                "--evidence",
                PROOF_CLIENT_REMOTE_EVIDENCE,
            ],
            extra_env=env,
            timeout=PROOF_CLIENT_ORACLE_TIMEOUT_SECONDS,
        )
        host_dir = Path(tempfile.mkdtemp(prefix="resume-publication-evidence-"))
        evidence_host = host_dir / "evidence.json"
        copied = self._docker(
            [
                "cp",
                f"{PROOF_CLIENT_CONTAINER}:{PROOF_CLIENT_REMOTE_EVIDENCE}",
                str(evidence_host),
            ]
        )
        payload = None
        if copied.returncode == 0 and evidence_host.is_file():
            loaded = json.loads(evidence_host.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        if completed.returncode != 0:
            if payload is not None:
                payload["status"] = "fail"
                payload["client_exit"] = completed.returncode
                return payload
            # A client crash can precede its evidence write. Preserve a bounded,
            # sanitized process diagnostic so that this failure is actionable.
            client_detail = sanitize_proof_error(
                RuntimeError(str(completed.stderr or completed.stdout or "")),
                (self._sql_password,),
            )[:2048]
            copy_detail = sanitize_proof_error(
                RuntimeError(str(copied.stderr or "")), (self._sql_password,)
            )[:512]
            raise EngineProofError(
                f"client_oracles_failed:exit={completed.returncode}:"
                f"copy_exit={copied.returncode}:client={client_detail}:copy={copy_detail}"
            )
        if payload is None:
            raise EngineProofError("client_evidence_copy_failed")
        return payload
