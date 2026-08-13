"""Durable Profile-core repository behind an injected procedure executor.

The adapter is intentionally unregistered.  It issues only the six named
PS-PROFILE-002 operations and converts one owner-scoped manifest row into the
already reviewed domain records.  ``ProfileCoreService`` revalidates every
nested value before use, so a malformed or cross-owner database row fails
closed at both repository and service boundaries.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Mapping, Protocol, Sequence

from services.profile_core_service import (
    ProfileAboutDraft,
    ProfileConflictError,
    ProfileCurrentChapterDraft,
    ProfileDraft,
    ProfileIdentityDraft,
    ProfilePlacementDraft,
    ProfilePrincipleDraft,
    ProfilePublicationCommand,
    ProfilePublicationItem,
    ProfilePublicationRevision,
    PROFILE_PUBLICATION_ACTIONS,
    ProfileUnavailableError,
)
from services.profile_posts_adapter import CommunityPostReference


PROFILE_PROCEDURES = frozenset(
    {
        "usp_GetProfileOwnerBySlug",
        "usp_GetProfileDraftForOwner",
        "usp_SaveProfileDraftForOwner",
        "usp_GetCurrentProfilePublicationForOwner",
        "usp_CommitProfilePublicationForOwner",
        "usp_GetProfilePublicationCommandForOwner",
    }
)


class ProfileProcedureExecutor(Protocol):
    def execute_procedure(
        self, procedure_name: str, parameters: Sequence[tuple[str, object]] | None = None
    ) -> list[list[Mapping[str, object]]]: ...


def _json_object(value: object) -> Mapping[str, Any]:
    if not isinstance(value, str) or len(value) > 1_000_000:
        raise ProfileUnavailableError("Profile persistence returned invalid data.")
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        raise ProfileUnavailableError("Profile persistence returned invalid data.") from None
    if not isinstance(parsed, dict):
        raise ProfileUnavailableError("Profile persistence returned invalid data.")
    return parsed


def _first_row(result_sets: object) -> Mapping[str, object] | None:
    if not isinstance(result_sets, list) or not result_sets:
        return None
    first = result_sets[0]
    if not isinstance(first, list) or not first:
        return None
    row = first[0]
    return row if isinstance(row, Mapping) else None


def _reference(value: object) -> CommunityPostReference | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ProfileUnavailableError("Profile persistence returned invalid data.")
    try:
        return CommunityPostReference(
            source_key=value["source_key"],
            source_revision=value["source_revision"],
            canonical_path=value["canonical_path"],
            published_at=datetime.fromisoformat(value["published_at"]),
        )
    except (KeyError, TypeError, ValueError):
        raise ProfileUnavailableError("Profile persistence returned invalid data.") from None


def _native(payload: Mapping[str, Any]):
    try:
        raw_identity = payload.get("identity")
        identity = None if raw_identity is None else ProfileIdentityDraft(**raw_identity)
        raw_chapter = payload.get("current_chapter")
        chapter = None if raw_chapter is None else ProfileCurrentChapterDraft(**raw_chapter)
        raw_about = payload.get("about")
        about = None
        if raw_about is not None:
            values = dict(raw_about)
            values["principles"] = tuple(
                ProfilePrincipleDraft(**item) for item in values.get("principles", ())
            )
            about = ProfileAboutDraft(**values)
        return identity, chapter, about
    except (TypeError, ValueError):
        raise ProfileUnavailableError("Profile persistence returned invalid data.") from None


def decode_draft(value: object) -> ProfileDraft:
    payload = _json_object(value)
    identity, chapter, about = _native(payload)
    try:
        placements = tuple(
            ProfilePlacementDraft(
                placement_key=item["placement_key"],
                content_kind=item["content_kind"],
                destination=item["destination"],
                region=item["region"],
                rank=item["rank"],
                featured=item["featured"],
                source_reference=_reference(item.get("source_reference")),
            )
            for item in payload.get("placements", ())
        )
        return ProfileDraft(
            draft_key=payload["draft_key"], owner_key=payload["owner_key"],
            slug=payload["slug"], version=payload["version"], identity=identity,
            current_chapter=chapter, about=about, placements=placements,
        )
    except (KeyError, TypeError, ValueError):
        raise ProfileUnavailableError("Profile persistence returned invalid data.") from None


def decode_revision(value: object) -> ProfilePublicationRevision:
    payload = _json_object(value)
    identity, chapter, about = _native(payload)
    try:
        items = tuple(
            ProfilePublicationItem(
                placement_key=item["placement_key"], content_kind=item["content_kind"],
                destination=item["destination"], region=item["region"], rank=item["rank"],
                featured=item["featured"], source_reference=_reference(item.get("source_reference")),
            )
            for item in payload.get("items", ())
        )
        return ProfilePublicationRevision(
            revision_key=payload["revision_key"], owner_key=payload["owner_key"],
            slug=payload["slug"], audience=payload["audience"],
            action=payload["action"],
            revision_number=payload["revision_number"],
            created_at=datetime.fromisoformat(payload["created_at"]), digest=payload["digest"],
            identity=identity, current_chapter=chapter, about=about, items=items,
        )
    except (KeyError, TypeError, ValueError):
        raise ProfileUnavailableError("Profile persistence returned invalid data.") from None


def _manifest_native(identity, chapter, about) -> dict[str, Any]:
    return {
        "identity": None if identity is None else {
            "display_name": identity.display_name, "headline": identity.headline,
            "location": identity.location, "summary": identity.summary,
        },
        "current_chapter": None if chapter is None else {"label": chapter.label, "body": chapter.body},
        "about": None if about is None else {
            "heading": about.heading, "body": about.body, "resume_path": about.resume_path,
            "story_path": about.story_path, "ask_path": about.ask_path,
            "principles": [{"title": item.title, "body": item.body} for item in about.principles],
        },
    }


def _reference_payload(value):
    return None if value is None else {
        "source_key": value.source_key, "source_revision": value.source_revision,
        "canonical_path": value.canonical_path, "published_at": value.published_at.isoformat(),
    }


def encode_draft(value: ProfileDraft) -> str:
    payload = {
        "draft_key": value.draft_key, "owner_key": value.owner_key,
        "slug": value.slug, "version": value.version,
        **_manifest_native(value.identity, value.current_chapter, value.about),
        "placements": [
            {"placement_key": item.placement_key, "content_kind": item.content_kind,
             "destination": item.destination, "region": item.region, "rank": item.rank,
             "featured": item.featured, "source_reference": _reference_payload(item.source_reference)}
            for item in value.placements
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def encode_revision(value: ProfilePublicationRevision) -> str:
    payload = {
        "revision_key": value.revision_key, "owner_key": value.owner_key, "slug": value.slug,
        "audience": value.audience, "action": value.action,
        "revision_number": value.revision_number,
        "created_at": value.created_at.isoformat(), "digest": value.digest,
        **_manifest_native(value.identity, value.current_chapter, value.about),
        "items": [
            {"placement_key": item.placement_key, "content_kind": item.content_kind,
             "destination": item.destination, "region": item.region, "rank": item.rank,
             "featured": item.featured, "source_reference": _reference_payload(item.source_reference)}
            for item in value.items
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class SqlProfileCoreRepository:
    """ProfileCoreStore implementation; registration is a later shared slice."""

    def __init__(self, executor: ProfileProcedureExecutor):
        self._executor = executor

    def _execute(self, name: str, parameters=()):
        if name not in PROFILE_PROCEDURES:
            raise ProfileUnavailableError("Profile persistence operation unavailable.")
        try:
            return self._executor.execute_procedure(name, parameters)
        except Exception as error:
            raise ProfileUnavailableError("Profile persistence unavailable.") from error

    def profile_for_slug(self, slug: str) -> str | None:
        row = _first_row(self._execute("usp_GetProfileOwnerBySlug", [("@ProfileSlug", slug)]))
        return None if row is None else row.get("owner_key")

    def draft_for_owner(self, owner_key: str) -> ProfileDraft | None:
        row = _first_row(self._execute("usp_GetProfileDraftForOwner", [("@OwnerKey", owner_key)]))
        return None if row is None else decode_draft(row.get("manifest_json"))

    def put_draft(self, draft: ProfileDraft, *, expected_version: str | None) -> None:
        rows = self._execute("usp_SaveProfileDraftForOwner", [
            ("@OwnerKey", draft.owner_key), ("@ProfileSlug", draft.slug),
            ("@ExpectedDraftVersion", expected_version),
            ("@DraftVersion", draft.version), ("@ManifestJson", encode_draft(draft)),
        ])
        row = _first_row(rows)
        if row is None or row.get("saved") != 1:
            raise ProfileConflictError("Profile draft changed. Refresh before saving.")

    def current_publication(self, owner_key: str) -> ProfilePublicationRevision | None:
        row = _first_row(self._execute("usp_GetCurrentProfilePublicationForOwner", [("@OwnerKey", owner_key), ("@Audience", "public")]))
        return None if row is None else decode_revision(row.get("manifest_json"))

    def append_publication(
        self,
        revision: ProfilePublicationRevision,
        command: ProfilePublicationCommand,
        *,
        action: str,
        expected_public_revision: str | None,
        expected_draft: ProfileDraft,
    ) -> ProfilePublicationCommand:
        if action not in PROFILE_PUBLICATION_ACTIONS or revision.action != action:
            raise ProfileUnavailableError("Profile persistence returned invalid data.")
        row = _first_row(self._execute("usp_CommitProfilePublicationForOwner", [
            ("@OwnerKey", revision.owner_key), ("@Audience", revision.audience),
            ("@PublicationAction", action),
            ("@ExpectedPublicRevision", expected_public_revision),
            ("@ExpectedDraftKey", expected_draft.draft_key),
            ("@ExpectedDraftVersion", expected_draft.version),
            ("@ExpectedDraftManifestJson", encode_draft(expected_draft)),
            ("@RevisionKey", revision.revision_key), ("@RevisionNumber", revision.revision_number),
            ("@RevisionDigest", revision.digest), ("@ManifestJson", encode_revision(revision)),
            ("@CommandKey", command.command_key), ("@IdempotencyKey", command.idempotency_key),
            ("@RequestDigest", command.request_digest),
        ]))
        if row is None or row.get("committed") != 1:
            raise ProfileConflictError("Profile publication changed. Refresh before publishing.")
        try:
            committed_revision = decode_revision(row["manifest_json"])
            if committed_revision.action != action:
                raise ProfileUnavailableError("Profile persistence returned invalid data.")
            return ProfilePublicationCommand(
                command_key=row["command_key"], owner_key=row["owner_key"],
                idempotency_key=row["idempotency_key"], request_digest=row["request_digest"],
                revision=committed_revision,
            )
        except KeyError:
            raise ProfileUnavailableError("Profile persistence returned invalid data.") from None

    def command_for(self, owner_key: str, idempotency_key: str) -> ProfilePublicationCommand | None:
        row = _first_row(self._execute("usp_GetProfilePublicationCommandForOwner", [
            ("@OwnerKey", owner_key), ("@IdempotencyKey", idempotency_key),
        ]))
        if row is None:
            return None
        try:
            return ProfilePublicationCommand(
                command_key=row["command_key"], owner_key=row["owner_key"],
                idempotency_key=row["idempotency_key"], request_digest=row["request_digest"],
                revision=decode_revision(row["manifest_json"]),
            )
        except KeyError:
            raise ProfileUnavailableError("Profile persistence returned invalid data.") from None
