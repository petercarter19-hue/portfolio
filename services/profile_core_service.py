"""Profile-native D0 contracts, deliberately unregistered and in-memory.

The finished Profile will need a governed SQL-backed publication system.  D0
does *not* fake that system.  It provides the dependency-free domain contract
that later migration, identity, and application-registration work can adopt:

* profile-native identity/current-chapter/About and Home curation drafts;
* owner-scoped immutable publication revisions for the Public audience;
* an exact public serializer that is also used by owner preview; and
* a narrow Community-reference placement that never copies Community content.

``InMemoryProfileCoreStore`` is an explicit test/local adapter.  It is never
instantiated by application startup and therefore cannot alter production
routes, data, or sign-in behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import re
from secrets import token_urlsafe
from threading import RLock
from typing import Any, Iterable, Mapping, Protocol, Sequence

from services.profile_posts_adapter import (
    CommunityPostReferenceAdapter,
    ProfilePostReferenceNotFound,
    ProfilePostReferenceValidationError,
    ProfilePostsAdapterError,
    validate_community_post_reference,
)


PROFILE_AUDIENCE_PUBLIC = "public"
PROFILE_PUBLICATION_ACTION_PUBLISH = "publish"
PROFILE_PUBLICATION_ACTION_WITHDRAW = "withdraw"
PROFILE_PUBLICATION_ACTIONS = frozenset(
    {PROFILE_PUBLICATION_ACTION_PUBLISH, PROFILE_PUBLICATION_ACTION_WITHDRAW}
)
PROFILE_DESTINATIONS = frozenset({"home", "posts", "projects", "media", "voice", "about"})
PROFILE_NATIVE_KINDS = frozenset({"identity", "current_chapter", "about"})
PROFILE_OWNED_KIND = "profile_native"
COMMUNITY_POST_KIND = "community_post_reference"
PROFILE_SCHEMA_VERSION = "profile-core-d0-v1"

_OPAQUE_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
_REQUEST_KEY = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_VERSION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_REGION = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_PROFILE_INTERNAL_PATH = re.compile(
    r"^/(?:[A-Za-z0-9][A-Za-z0-9._~-]*)(?:/[A-Za-z0-9][A-Za-z0-9._~-]*)*$"
)
_TEXT_LIMITS = {
    "display_name": 160,
    "headline": 240,
    "location": 160,
    "summary": 2_000,
    "current_chapter_label": 120,
    "current_chapter_body": 2_000,
    "about_heading": 160,
    "about_body": 4_000,
}


class ProfileCoreError(Exception):
    """Base error for Profile-core contract failures."""


class ProfileValidationError(ProfileCoreError):
    """The request fails local, non-sensitive contract validation."""


class ProfileNotFound(ProfileCoreError):
    """Neutral absence for a profile, draft, or publication."""


class ProfileAuthorizationError(ProfileCoreError):
    """Actor/subject ownership is absent; routes convert this to neutral absence."""


class ProfileConflictError(ProfileCoreError):
    """Optimistic version, digest, or idempotency conflict."""


class ProfileUnavailableError(ProfileCoreError):
    """The later durable dependency is unavailable."""


class ProfilePersistenceConflictError(ProfileConflictError):
    """A durable adapter rejected the expected version/idempotency contract."""


@dataclass(frozen=True)
class ProfileViewerContext:
    """Server-derived identity context.

    It intentionally has no user-controlled ``mode`` or ``audience`` field.
    The unregistered D0 service supports only owner working mode and exact
    Public projection/preview.  Connections is a later dependency.
    """

    actor_key: str | None
    subject_owner_key: str
    profile_slug: str
    request_purpose: str

    @property
    def is_owner(self) -> bool:
        return self.actor_key is not None and hmac.compare_digest(
            self.actor_key, self.subject_owner_key
        )


@dataclass(frozen=True)
class ProfileIdentityDraft:
    display_name: str
    headline: str
    location: str | None
    summary: str


@dataclass(frozen=True)
class ProfileCurrentChapterDraft:
    label: str
    body: str


@dataclass(frozen=True)
class ProfilePrincipleDraft:
    """A small Profile-native value; never a copied Story or Resume record."""

    title: str
    body: str


@dataclass(frozen=True)
class ProfileAboutDraft:
    heading: str
    body: str
    resume_path: str | None = None
    story_path: str | None = None
    ask_path: str | None = None
    principles: tuple[ProfilePrincipleDraft, ...] = ()


@dataclass(frozen=True)
class ProfilePlacementDraft:
    placement_key: str
    content_kind: str
    destination: str
    region: str
    rank: int
    featured: bool
    source_reference: CommunityPostReference | None = None


@dataclass(frozen=True)
class ProfileDraft:
    draft_key: str
    owner_key: str
    slug: str
    version: str
    identity: ProfileIdentityDraft | None = None
    current_chapter: ProfileCurrentChapterDraft | None = None
    about: ProfileAboutDraft | None = None
    placements: tuple[ProfilePlacementDraft, ...] = ()


@dataclass(frozen=True)
class ProfilePublicationItem:
    """Immutable audience-safe placement in one publication revision."""

    placement_key: str
    content_kind: str
    destination: str
    region: str
    rank: int
    featured: bool
    source_reference: CommunityPostReference | None = None


@dataclass(frozen=True)
class ProfilePublicationRevision:
    revision_key: str
    owner_key: str
    slug: str
    audience: str
    action: str
    revision_number: int
    created_at: datetime
    digest: str
    identity: ProfileIdentityDraft | None
    current_chapter: ProfileCurrentChapterDraft | None
    about: ProfileAboutDraft | None
    items: tuple[ProfilePublicationItem, ...]


@dataclass(frozen=True)
class ProfilePublicationCommand:
    command_key: str
    owner_key: str
    idempotency_key: str
    request_digest: str
    revision: ProfilePublicationRevision


@dataclass(frozen=True)
class ProfilePublicReadModel:
    """The only model returned by public reader/owner preview in D0."""

    schema_version: str
    profile_slug: str
    mode: str
    publication_revision: str
    identity: Mapping[str, str | None]
    current_chapter: Mapping[str, str] | None
    about: Mapping[str, str | None] | None
    home: tuple[Mapping[str, Any], ...]
    posts: tuple[Mapping[str, Any], ...]
    projects: tuple[Mapping[str, Any], ...] = ()
    media: tuple[Mapping[str, Any], ...] = ()
    voice: tuple[Mapping[str, Any], ...] = ()
    available_destinations: tuple[str, ...] = ("home", "posts", "about")
    destination_state: str = "ready"


@dataclass(frozen=True)
class ProfileOwnerReadModel:
    """Owner-only working state, intentionally separate from public payloads."""

    schema_version: str
    profile_slug: str
    draft_version: str
    public_revision: str | None
    public_digest: str | None
    source_status: tuple[Mapping[str, str | None], ...]


class ProfileCoreStore(Protocol):
    """Minimal persistence port; later SQL work supplies the durable adapter."""

    def profile_for_slug(self, slug: str) -> str | None:
        """Return one owner key for normalized slug, or no result."""

    def draft_for_owner(self, owner_key: str) -> ProfileDraft | None:
        """Return only the exact owner's private draft."""

    def put_draft(self, draft: ProfileDraft, *, expected_version: str | None) -> None:
        """Replace one owner-scoped mutable draft after a verified command."""

    def current_publication(self, owner_key: str) -> ProfilePublicationRevision | None:
        """Return the exact current Public revision for one owner."""

    def append_publication(
        self,
        revision: ProfilePublicationRevision,
        command: ProfilePublicationCommand,
        *,
        action: str,
        expected_public_revision: str | None,
        expected_draft: ProfileDraft,
    ) -> ProfilePublicationCommand:
        """Atomically advance one Public branch in a durable implementation."""

    def command_for(self, owner_key: str, idempotency_key: str) -> ProfilePublicationCommand | None:
        """Return only the owning actor's prior idempotent command."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _opaque(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_KEY.fullmatch(value):
        raise ProfileValidationError(f"Invalid {field_name}.")
    return value


def _slug(value: object) -> str:
    if not isinstance(value, str) or not _SLUG.fullmatch(value):
        raise ProfileValidationError("Invalid profile slug.")
    return value


def _publication_action(value: object) -> str:
    if value not in PROFILE_PUBLICATION_ACTIONS:
        raise ProfileValidationError("Invalid Profile publication action.")
    return value


def _request_key(value: object) -> str:
    if not isinstance(value, str) or not _REQUEST_KEY.fullmatch(value):
        raise ProfileValidationError("Invalid idempotency key.")
    return value


def _version(value: object, field_name: str = "version") -> str:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise ProfileValidationError(f"Invalid {field_name}.")
    return value


def _text(value: object, field_name: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ProfileValidationError(f"Invalid {field_name}.")
    normalized = " ".join(value.strip().split())
    if not normalized or len(normalized) > _TEXT_LIMITS[field_name]:
        raise ProfileValidationError(f"Invalid {field_name}.")
    return normalized


def _safe_path(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    # These are same-origin Profile links, never arbitrary URLs.  The narrow
    # canonical shape excludes authorities, schemes, queries/fragments,
    # literal/encoded traversal, encoded separators, backslashes, controls,
    # whitespace, duplicate separators, and trailing-slash aliases.
    if (
        not isinstance(value, str)
        or len(value) > 512
        or "\\" in value
        or not _PROFILE_INTERNAL_PATH.fullmatch(value)
    ):
        raise ProfileValidationError(f"Invalid {field_name}.")
    return value


def _rank(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 100_000:
        raise ProfileValidationError("Invalid placement rank.")
    return value


def _region(value: object) -> str:
    if not isinstance(value, str) or not _REGION.fullmatch(value):
        raise ProfileValidationError("Invalid placement region.")
    return value


def _digest(value: Any) -> str:
    normalized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(normalized.encode("utf-8")).hexdigest()


def _token(prefix: str) -> str:
    return f"{prefix}_{token_urlsafe(18).replace('-', 'a').replace('_', 'b')}"


def _revision_token(number: int) -> str:
    return f"v{number}:{token_urlsafe(12)}"


def _public_identity(identity: ProfileIdentityDraft) -> dict[str, str | None]:
    return {
        "display_name": identity.display_name,
        "headline": identity.headline,
        "location": identity.location,
        "summary": identity.summary,
    }


class InMemoryProfileCoreStore:
    """Explicit process-local adapter used in contract tests and local previews only."""

    def __init__(self, drafts: Iterable[ProfileDraft] = ()):
        self._lock = RLock()
        self._owners_by_slug: dict[str, str] = {}
        self._drafts: dict[str, ProfileDraft] = {}
        self._publications: dict[str, ProfilePublicationRevision] = {}
        self._commands: dict[tuple[str, str], ProfilePublicationCommand] = {}
        for draft in drafts:
            self.put_draft(draft, expected_version=None)

    def profile_for_slug(self, slug: str) -> str | None:
        with self._lock:
            return self._owners_by_slug.get(slug)

    def draft_for_owner(self, owner_key: str) -> ProfileDraft | None:
        with self._lock:
            return self._drafts.get(owner_key)

    def put_draft(self, draft: ProfileDraft, *, expected_version: str | None) -> None:
        with self._lock:
            existing_owner = self._owners_by_slug.get(draft.slug)
            if existing_owner is not None and not hmac.compare_digest(existing_owner, draft.owner_key):
                raise ProfileConflictError("Profile slug is unavailable.")
            current = self._drafts.get(draft.owner_key)
            current_version = current.version if current is not None else None
            if current_version != expected_version:
                raise ProfilePersistenceConflictError("Profile draft changed.")
            self._owners_by_slug[draft.slug] = draft.owner_key
            self._drafts[draft.owner_key] = draft

    def current_publication(self, owner_key: str) -> ProfilePublicationRevision | None:
        with self._lock:
            return self._publications.get(owner_key)

    def append_publication(
        self,
        revision: ProfilePublicationRevision,
        command: ProfilePublicationCommand,
        *,
        action: str,
        expected_public_revision: str | None,
        expected_draft: ProfileDraft,
    ) -> ProfilePublicationCommand:
        with self._lock:
            action = _publication_action(action)
            if revision.action != action:
                raise ProfilePersistenceConflictError("Profile publication action changed.")
            existing = self._commands.get((command.owner_key, command.idempotency_key))
            if existing is not None:
                if not hmac.compare_digest(existing.request_digest, command.request_digest):
                    raise ProfilePersistenceConflictError("Profile idempotency conflict.")
                return existing
            if self._drafts.get(revision.owner_key) != expected_draft:
                raise ProfilePersistenceConflictError("Profile draft changed.")
            current = self._publications.get(revision.owner_key)
            current_key = current.revision_key if current is not None else None
            if current_key != expected_public_revision:
                raise ProfilePersistenceConflictError("Profile publication changed.")
            if action == PROFILE_PUBLICATION_ACTION_PUBLISH:
                expected_items = tuple(
                    ProfilePublicationItem(
                        placement_key=item.placement_key,
                        content_kind=item.content_kind,
                        destination=item.destination,
                        region=item.region,
                        rank=item.rank,
                        featured=item.featured,
                        source_reference=item.source_reference,
                    )
                    for item in sorted(
                        expected_draft.placements,
                        key=lambda candidate: (
                            candidate.destination,
                            candidate.region,
                            candidate.rank,
                            candidate.placement_key,
                        ),
                    )
                )
                if (
                    revision.identity != expected_draft.identity
                    or revision.current_chapter != expected_draft.current_chapter
                    or revision.about != expected_draft.about
                    or revision.items != expected_items
                ):
                    raise ProfilePersistenceConflictError(
                        "Profile reviewed manifest changed."
                    )
            elif (
                revision.identity is not None
                or revision.current_chapter is not None
                or revision.about is not None
                or revision.items
            ):
                raise ProfilePersistenceConflictError(
                    "Profile withdrawal manifest must be empty."
                )
            self._publications[revision.owner_key] = revision
            self._commands[(command.owner_key, command.idempotency_key)] = command
            return command

    def command_for(self, owner_key: str, idempotency_key: str) -> ProfilePublicationCommand | None:
        with self._lock:
            return self._commands.get((owner_key, idempotency_key))


class ProfileCoreService:
    """D0 service layer: all owner checks occur before draft/publication reads."""

    def __init__(
        self,
        store: ProfileCoreStore,
        *,
        community_post_references: CommunityPostReferenceAdapter | None = None,
    ):
        self._store = store
        # The service accepts only an adapter-backed source key/revision.  A
        # direct ``CommunityPostReference`` is a storage-shaped object, not a
        # caller capability, and must never be accepted from a composition
        # command.
        self._community_post_references = community_post_references

    @staticmethod
    def owner_context(*, actor_key: str, subject_owner_key: str, slug: str, purpose: str) -> ProfileViewerContext:
        return ProfileViewerContext(
            actor_key=_opaque(actor_key, "actor key"),
            subject_owner_key=_opaque(subject_owner_key, "subject owner key"),
            profile_slug=_slug(slug),
            request_purpose=purpose,
        )

    @staticmethod
    def anonymous_context(*, subject_owner_key: str, slug: str, purpose: str = "html") -> ProfileViewerContext:
        return ProfileViewerContext(
            actor_key=None,
            subject_owner_key=_opaque(subject_owner_key, "subject owner key"),
            profile_slug=_slug(slug),
            request_purpose=purpose,
        )

    def _require_owner_context(self, context: ProfileViewerContext) -> None:
        # Compare the server-derived context before touching private draft or
        # command state.  Routes must never construct this from browser input.
        if not context.is_owner:
            raise ProfileAuthorizationError("Profile action unavailable.")

    def _owner_for_slug(self, slug: str) -> str:
        owner_key = self._store.profile_for_slug(_slug(slug))
        if owner_key is None:
            raise ProfileNotFound("Profile unavailable.")
        try:
            return _opaque(owner_key, "profile owner key")
        except ProfileValidationError:
            raise ProfileNotFound("Profile unavailable.") from None

    @staticmethod
    def _valid_owner_draft(
        draft: ProfileDraft | None,
        *,
        owner_key: str,
        slug: str,
    ) -> ProfileDraft | None:
        """Validate a private store result before exposing it to an owner flow."""

        if not isinstance(draft, ProfileDraft):
            return None
        try:
            draft_owner_key = _opaque(draft.owner_key, "draft owner key")
            draft_slug = _slug(draft.slug)
            _opaque(draft.draft_key, "profile draft")
            _version(draft.version, "draft version")
        except ProfileValidationError:
            return None
        if not (
            hmac.compare_digest(draft_owner_key, owner_key)
            and hmac.compare_digest(draft_slug, slug)
        ):
            return None
        return draft

    def _owner_draft(self, context: ProfileViewerContext) -> ProfileDraft:
        self._require_owner_context(context)
        owner_key = self._owner_for_slug(context.profile_slug)
        if not hmac.compare_digest(owner_key, context.subject_owner_key):
            raise ProfileAuthorizationError("Profile action unavailable.")
        draft = self._valid_owner_draft(
            self._store.draft_for_owner(owner_key),
            owner_key=owner_key,
            slug=context.profile_slug,
        )
        # A persistence adapter is a trust boundary.  It must not be possible
        # for a malformed/cross-owner record returned under A's lookup to
        # become A's private draft.  Compare both fields in constant time and
        # return the same neutral failure used for a missing record.
        if draft is None:
            raise ProfileNotFound("Profile unavailable.")
        return draft

    @staticmethod
    def _valid_native_manifest(
        identity: ProfileIdentityDraft | None,
        current_chapter: ProfileCurrentChapterDraft | None,
        about: ProfileAboutDraft | None,
        *,
        require_identity: bool,
    ) -> bool:
        """Validate stored Profile-native fields without silently normalizing them."""

        if identity is None:
            return not require_identity and current_chapter is None and about is None
        if not isinstance(identity, ProfileIdentityDraft):
            return False
        try:
            if (
                _text(identity.display_name, "display_name") != identity.display_name
                or _text(identity.headline, "headline") != identity.headline
                or _text(identity.location, "location", required=False) != identity.location
                or _text(identity.summary, "summary") != identity.summary
            ):
                return False
            if current_chapter is not None:
                if not isinstance(current_chapter, ProfileCurrentChapterDraft) or (
                    _text(current_chapter.label, "current_chapter_label") != current_chapter.label
                    or _text(current_chapter.body, "current_chapter_body") != current_chapter.body
                ):
                    return False
            if about is not None:
                if not isinstance(about, ProfileAboutDraft) or (
                    _text(about.heading, "about_heading") != about.heading
                    or _text(about.body, "about_body") != about.body
                    or _safe_path(about.resume_path, "resume path") != about.resume_path
                    or _safe_path(about.story_path, "story path") != about.story_path
                    or _safe_path(about.ask_path, "Ask path") != about.ask_path
                    or not isinstance(about.principles, tuple)
                    or len(about.principles) > 4
                ):
                    return False
                for principle in about.principles:
                    if not isinstance(principle, ProfilePrincipleDraft) or (
                        _text(principle.title, "about_heading") != principle.title
                        or _text(principle.body, "current_chapter_body") != principle.body
                    ):
                        return False
        except ProfileValidationError:
            return False
        return True

    def _valid_manifest(
        self,
        *,
        owner_key: str,
        slug: str,
        identity: ProfileIdentityDraft | None,
        current_chapter: ProfileCurrentChapterDraft | None,
        about: ProfileAboutDraft | None,
        entries: object,
        entry_type: type[ProfilePlacementDraft] | type[ProfilePublicationItem],
        require_identity: bool,
        require_current_sources: bool,
    ) -> bool:
        """Fail closed on every nested stored Profile manifest shape.

        Persistence adapters are an untrusted boundary.  Both mutable drafts
        and immutable publication revisions therefore pass through this one
        validator before a review, publish, idempotent return, or public
        serialization may use their nested placements.  It intentionally
        validates rather than repairs values: replacing malformed stored data
        would turn an attacker-controlled store response into publication.
        """

        try:
            _opaque(owner_key, "profile owner key")
            _slug(slug)
        except ProfileValidationError:
            return False
        if not self._valid_native_manifest(
            identity, current_chapter, about, require_identity=require_identity
        ):
            return False
        if not isinstance(entries, tuple):
            return False

        placement_keys: set[str] = set()
        occupied_slots: set[tuple[str, str, int]] = set()
        for entry in entries:
            if not isinstance(entry, entry_type):
                return False
            try:
                placement_key = _opaque(entry.placement_key, "profile placement")
                if entry.content_kind != COMMUNITY_POST_KIND:
                    return False
                if entry.destination not in {"home", "posts"}:
                    return False
                region = _region(entry.region)
                rank = _rank(entry.rank)
                if not isinstance(entry.featured, bool):
                    return False
                reference = validate_community_post_reference(entry.source_reference)
            except (ProfileValidationError, ProfilePostReferenceValidationError):
                return False

            if reference != entry.source_reference:
                return False
            if placement_key in placement_keys:
                return False
            placement_keys.add(placement_key)
            slot = (entry.destination, region, rank)
            if slot in occupied_slots:
                return False
            occupied_slots.add(slot)

            if require_current_sources:
                if self._community_post_references is None:
                    return False
                try:
                    resolved = self._community_post_references.verify_current_exact_reference(
                        owner_key=owner_key,
                        reference=reference,
                    )
                except ProfilePostsAdapterError:
                    return False
                if resolved != reference:
                    return False
        return True

    def _valid_draft_manifest(
        self, draft: ProfileDraft, *, require_current_sources: bool
    ) -> bool:
        return self._valid_manifest(
            owner_key=draft.owner_key,
            slug=draft.slug,
            identity=draft.identity,
            current_chapter=draft.current_chapter,
            about=draft.about,
            entries=draft.placements,
            entry_type=ProfilePlacementDraft,
            require_identity=True,
            require_current_sources=require_current_sources,
        )

    def _valid_current_publication(
        self,
        publication: ProfilePublicationRevision | None,
        *,
        owner_key: str,
        slug: str,
    ) -> ProfilePublicationRevision | None:
        """Return only a structurally consistent current Public revision.

        Store results are validated before any owner state, public projection,
        or serializer sees them.  A malformed/cross-owner result is neutral
        absence, not an exception that leaks state or an opportunity to render
        another member's immutable publication.
        """

        if publication is None:
            return None
        if not isinstance(publication, ProfilePublicationRevision):
            return None
        try:
            publication_owner_key = _opaque(publication.owner_key, "publication owner key")
            publication_slug = _slug(publication.slug)
            publication_revision = _version(publication.revision_key, "public revision")
            publication_action = _publication_action(publication.action)
            if not isinstance(publication.audience, str):
                return None
            if (
                isinstance(publication.revision_number, bool)
                or not isinstance(publication.revision_number, int)
                or publication.revision_number < 1
            ):
                return None
            if (
                not isinstance(publication.digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", publication.digest)
            ):
                return None
            if (
                not isinstance(publication.created_at, datetime)
                or publication.created_at.tzinfo is None
            ):
                return None
        except ProfileValidationError:
            return None
        if not (
            hmac.compare_digest(publication_owner_key, owner_key)
            and hmac.compare_digest(publication_slug, slug)
            and hmac.compare_digest(publication.audience, PROFILE_AUDIENCE_PUBLIC)
            and hmac.compare_digest(publication_revision, publication.revision_key)
        ):
            return None
        if not self._valid_manifest(
            owner_key=owner_key,
            slug=slug,
            identity=publication.identity,
            current_chapter=publication.current_chapter,
            about=publication.about,
            entries=publication.items,
            entry_type=ProfilePublicationItem,
            require_identity=publication_action == PROFILE_PUBLICATION_ACTION_PUBLISH,
            require_current_sources=False,
        ):
            return None
        if (
            publication_action == PROFILE_PUBLICATION_ACTION_WITHDRAW
            and publication.items
        ):
            return None
        expected_digest = _digest(
            {
                "audience": PROFILE_AUDIENCE_PUBLIC,
                "action": publication_action,
                "slug": slug,
                "identity": _identity_payload(publication.identity),
                "current_chapter": _chapter_payload(publication.current_chapter),
                "about": _about_payload(publication.about),
                "items": [_item_payload(item) for item in publication.items],
            }
        )
        if not hmac.compare_digest(publication.digest, expected_digest):
            return None
        return publication

    def _current_publication_for_owner(
        self,
        draft: ProfileDraft,
        *,
        fail_closed: bool,
    ) -> ProfilePublicationRevision | None:
        """Read and validate the current branch without trusting the store.

        Owner mutation/review flows must not mistake a malformed returned row
        for an empty branch.  Public rendering may instead map the same bad
        record to neutral absence so it cannot disclose operational detail.
        """

        raw_publication = self._store.current_publication(draft.owner_key)
        publication = self._valid_current_publication(
            raw_publication,
            owner_key=draft.owner_key,
            slug=draft.slug,
        )
        if raw_publication is not None and publication is None and fail_closed:
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        return publication

    def _valid_prior_command(
        self,
        command: ProfilePublicationCommand | None,
        *,
        owner_key: str,
        slug: str,
        idempotency_key: str,
        request_digest: str,
        expected_action: str,
    ) -> ProfilePublicationCommand | None:
        """Validate an idempotent replay before returning any stored revision."""

        if command is None:
            return None
        if not isinstance(command, ProfilePublicationCommand):
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        try:
            _opaque(command.command_key, "publication command")
            command_owner_key = _opaque(command.owner_key, "publication command owner")
            _request_key(command.idempotency_key)
            _version(command.revision.revision_key, "public revision")
        except (ProfileValidationError, AttributeError):
            raise ProfileUnavailableError("Profile publication dependency unavailable.") from None
        revision = self._valid_current_publication(
            command.revision,
            owner_key=owner_key,
            slug=slug,
        )
        if revision is None or not (
            hmac.compare_digest(command_owner_key, owner_key)
            and hmac.compare_digest(command.idempotency_key, idempotency_key)
            and hmac.compare_digest(
                revision.action, _publication_action(expected_action)
            )
        ):
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        if (
            not isinstance(command.request_digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", command.request_digest)
        ):
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        if not hmac.compare_digest(command.request_digest, request_digest):
            raise ProfileConflictError("This idempotency key belongs to a different request.")
        return command

    def owner_state(self, context: ProfileViewerContext) -> ProfileOwnerReadModel:
        draft = self._owner_draft(context)
        if not self._valid_draft_manifest(draft, require_current_sources=False):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        publication = self._current_publication_for_owner(draft, fail_closed=True)
        source_status: list[Mapping[str, str | None]] = []
        for placement in draft.placements:
            if placement.source_reference is not None:
                source_status.append(
                    {
                        "placement_key": placement.placement_key,
                        "state": "pinned",
                        "source_revision": placement.source_reference.source_revision,
                    }
                )
        return ProfileOwnerReadModel(
            schema_version=PROFILE_SCHEMA_VERSION,
            profile_slug=draft.slug,
            draft_version=draft.version,
            public_revision=publication.revision_key if publication else None,
            public_digest=publication.digest if publication else None,
            source_status=tuple(source_status),
        )

    def update_native_draft(
        self,
        context: ProfileViewerContext,
        *,
        expected_version: str,
        identity: Mapping[str, object] | None = None,
        current_chapter: Mapping[str, object] | None = None,
        about: Mapping[str, object] | None = None,
    ) -> ProfileDraft:
        """Update only Profile-native working content after an owner check."""

        draft = self._owner_draft(context)
        if not self._valid_draft_manifest(draft, require_current_sources=False):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        if not hmac.compare_digest(_version(expected_version, "expected draft version"), draft.version):
            raise ProfileConflictError("Profile draft changed. Refresh before saving.")
        if identity is current_chapter is about is None:
            raise ProfileValidationError("Choose Profile content to update.")

        next_identity = draft.identity
        if identity is not None:
            if not isinstance(identity, Mapping):
                raise ProfileValidationError("Invalid identity draft.")
            next_identity = ProfileIdentityDraft(
                display_name=_text(identity.get("display_name"), "display_name") or "",
                headline=_text(identity.get("headline"), "headline") or "",
                location=_text(identity.get("location"), "location", required=False),
                summary=_text(identity.get("summary"), "summary") or "",
            )

        next_chapter = draft.current_chapter
        if current_chapter is not None:
            if not isinstance(current_chapter, Mapping):
                raise ProfileValidationError("Invalid current chapter draft.")
            next_chapter = ProfileCurrentChapterDraft(
                label=_text(current_chapter.get("label"), "current_chapter_label") or "",
                body=_text(current_chapter.get("body"), "current_chapter_body") or "",
            )

        next_about = draft.about
        if about is not None:
            if not isinstance(about, Mapping):
                raise ProfileValidationError("Invalid About draft.")
            principles = _principles(about.get("principles"))
            next_about = ProfileAboutDraft(
                heading=_text(about.get("heading"), "about_heading") or "",
                body=_text(about.get("body"), "about_body") or "",
                resume_path=_safe_path(about.get("resume_path"), "resume path"),
                story_path=_safe_path(about.get("story_path"), "story path"),
                ask_path=_safe_path(about.get("ask_path"), "Ask path"),
                principles=principles,
            )

        next_draft = replace(
            draft,
            version=_revision_token(_draft_version_number(draft.version) + 1),
            identity=next_identity,
            current_chapter=next_chapter,
            about=next_about,
        )
        self._store.put_draft(next_draft, expected_version=draft.version)
        return next_draft

    def add_community_post_reference(
        self,
        context: ProfileViewerContext,
        *,
        expected_version: str,
        source_key: str,
        source_revision: str,
        destination: str = "posts",
        region: str = "stream",
        rank: int = 0,
        featured: bool = False,
    ) -> ProfileDraft:
        """Add a narrow exact source reference, never raw post content."""

        draft = self._owner_draft(context)
        if not self._valid_draft_manifest(draft, require_current_sources=False):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        if not hmac.compare_digest(_version(expected_version, "expected draft version"), draft.version):
            raise ProfileConflictError("Profile draft changed. Refresh before saving.")
        if destination not in {"home", "posts"}:
            raise ProfileValidationError("Posts may appear only on Home or Posts.")
        region = _region(region)
        rank = _rank(rank)
        if not isinstance(featured, bool):
            raise ProfileValidationError("Invalid featured state.")
        if self._community_post_references is None:
            raise ProfileUnavailableError("Community reference dependency unavailable.")
        try:
            reference = self._community_post_references.reference_for(
                owner_key=draft.owner_key,
                source_key=source_key,
                source_revision=source_revision,
            )
        except (ProfilePostReferenceNotFound, ProfilePostReferenceValidationError):
            # Do not distinguish a cross-owner/missing/ineligible source from
            # an ordinary unavailable reference at the Profile boundary.
            raise ProfileNotFound("Community reference unavailable.") from None
        except ProfilePostsAdapterError as error:
            raise ProfileUnavailableError("Community reference dependency unavailable.") from error
        try:
            reference = validate_community_post_reference(reference)
        except ProfilePostReferenceValidationError:
            raise ProfileUnavailableError("Community reference dependency unavailable.") from None

        for existing in draft.placements:
            if existing.source_reference == reference and existing.destination == destination:
                raise ProfileConflictError("That Community reference is already placed here.")
            if existing.destination == destination and existing.region == region and existing.rank == rank:
                raise ProfileConflictError("That Profile placement position is already used.")

        placement = ProfilePlacementDraft(
            placement_key=_token("pp"),
            content_kind=COMMUNITY_POST_KIND,
            destination=destination,
            region=region,
            rank=rank,
            featured=featured,
            source_reference=reference,
        )
        next_draft = replace(
            draft,
            version=_revision_token(_draft_version_number(draft.version) + 1),
            placements=(*draft.placements, placement),
        )
        self._store.put_draft(next_draft, expected_version=draft.version)
        return next_draft

    def review_publication(
        self,
        context: ProfileViewerContext,
        *,
        expected_draft_version: str,
        expected_public_revision: str | None,
    ) -> Mapping[str, Any]:
        """Compare a private draft to one current Public revision without publishing."""

        draft = self._owner_draft(context)
        if not hmac.compare_digest(_version(expected_draft_version, "expected draft version"), draft.version):
            raise ProfileConflictError("Profile draft changed. Refresh before reviewing.")
        if not self._valid_draft_manifest(draft, require_current_sources=True):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        current = self._current_publication_for_owner(draft, fail_closed=True)
        if expected_public_revision is None:
            if current is not None:
                raise ProfileConflictError("Public publication changed. Refresh before reviewing.")
        elif current is None or not hmac.compare_digest(
            _version(expected_public_revision, "expected public revision"), current.revision_key
        ):
            raise ProfileConflictError("Public publication changed. Refresh before reviewing.")

        candidate = self._new_publication_revision(
            draft, current, action=PROFILE_PUBLICATION_ACTION_PUBLISH
        )
        return {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "audience": PROFILE_AUDIENCE_PUBLIC,
            "draft_version": draft.version,
            "current_public_revision": current.revision_key if current else None,
            "candidate_revision": candidate.revision_key,
            "candidate_digest": candidate.digest,
            "changes": _publication_changes(current, candidate),
        }

    def publish_publication(
        self,
        context: ProfileViewerContext,
        *,
        expected_draft_version: str,
        expected_public_revision: str | None,
        candidate_digest: str,
        idempotency_key: str,
        confirmed: bool,
    ) -> ProfilePublicationCommand:
        """Explicitly advance the immutable Public branch or preserve the old one."""

        draft = self._owner_draft(context)
        if not confirmed:
            raise ProfileValidationError("Confirm the Public publication before publishing.")
        expected_draft_version = _version(expected_draft_version, "expected draft version")
        idempotency_key = _request_key(idempotency_key)
        if not isinstance(candidate_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", candidate_digest):
            raise ProfileValidationError("Invalid candidate digest.")
        request_digest = _digest(
            {
                "draft_version": expected_draft_version,
                "expected_public_revision": expected_public_revision,
                "candidate_digest": candidate_digest,
                "audience": PROFILE_AUDIENCE_PUBLIC,
                "action": PROFILE_PUBLICATION_ACTION_PUBLISH,
            }
        )
        prior = self._valid_prior_command(
            self._store.command_for(draft.owner_key, idempotency_key),
            owner_key=draft.owner_key,
            slug=draft.slug,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            expected_action=PROFILE_PUBLICATION_ACTION_PUBLISH,
        )
        if prior is not None:
            return prior
        # An exact, fully validated idempotent replay above returns the already
        # committed immutable result.  Only a fresh publication requires the
        # draft's Community sources to remain exact, current, and eligible.
        if not self._valid_draft_manifest(draft, require_current_sources=True):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        if not hmac.compare_digest(expected_draft_version, draft.version):
            raise ProfileConflictError("Profile draft changed. Refresh before publishing.")

        current = self._current_publication_for_owner(draft, fail_closed=True)
        if expected_public_revision is None:
            if current is not None:
                raise ProfileConflictError("Public publication changed. Refresh before publishing.")
        elif current is None or not hmac.compare_digest(
            _version(expected_public_revision, "expected public revision"), current.revision_key
        ):
            raise ProfileConflictError("Public publication changed. Refresh before publishing.")

        candidate = self._new_publication_revision(
            draft, current, action=PROFILE_PUBLICATION_ACTION_PUBLISH
        )
        if not hmac.compare_digest(candidate_digest, candidate.digest):
            raise ProfileConflictError("Profile candidate changed. Review again before publishing.")

        command = ProfilePublicationCommand(
            command_key=_token("pc"),
            owner_key=draft.owner_key,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            revision=candidate,
        )
        committed = self._store.append_publication(
            candidate,
            command,
            action=PROFILE_PUBLICATION_ACTION_PUBLISH,
            expected_public_revision=current.revision_key if current else None,
            expected_draft=draft,
        )
        validated = self._valid_prior_command(
            committed,
            owner_key=draft.owner_key,
            slug=draft.slug,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            expected_action=PROFILE_PUBLICATION_ACTION_PUBLISH,
        )
        if validated is None:
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        return validated

    def withdraw_publication(
        self,
        context: ProfileViewerContext,
        *,
        expected_public_revision: str,
        idempotency_key: str,
        confirmed: bool,
    ) -> ProfilePublicationCommand:
        """Advance to a new empty Public revision; prior revisions remain immutable."""

        draft = self._owner_draft(context)
        if not confirmed:
            raise ProfileValidationError("Confirm Public withdrawal before continuing.")
        expected_public_revision = _version(expected_public_revision, "expected public revision")
        idempotency_key = _request_key(idempotency_key)
        request_digest = _digest(
            {
                "expected_public_revision": expected_public_revision,
                "audience": PROFILE_AUDIENCE_PUBLIC,
                "action": PROFILE_PUBLICATION_ACTION_WITHDRAW,
            }
        )
        prior = self._valid_prior_command(
            self._store.command_for(draft.owner_key, idempotency_key),
            owner_key=draft.owner_key,
            slug=draft.slug,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            expected_action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
        )
        if prior is not None:
            return prior
        current = self._current_publication_for_owner(draft, fail_closed=True)
        if current is None or not hmac.compare_digest(expected_public_revision, current.revision_key):
            raise ProfileConflictError("Public publication changed. Refresh before withdrawing.")
        revision = self._new_publication_revision(
            draft,
            current,
            action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            identity=None,
            current_chapter=None,
            about=None,
            items=(),
        )
        command = ProfilePublicationCommand(
            command_key=_token("pc"),
            owner_key=draft.owner_key,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            revision=revision,
        )
        committed = self._store.append_publication(
            revision,
            command,
            action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
            expected_public_revision=current.revision_key,
            expected_draft=draft,
        )
        validated = self._valid_prior_command(
            committed,
            owner_key=draft.owner_key,
            slug=draft.slug,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            expected_action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
        )
        if validated is None:
            raise ProfileUnavailableError("Profile publication dependency unavailable.")
        return validated

    def public_read(self, *, slug: str, destination: str) -> ProfilePublicReadModel:
        """Read only the exact current Public revision after slug lookup.

        D0 deliberately does not use a broad per-owner content query then
        filter it for the browser; all fields derive from the single immutable
        publication revision returned here.
        """

        if destination not in PROFILE_DESTINATIONS:
            raise ProfileNotFound("Profile destination unavailable.")
        owner_key = self._owner_for_slug(slug)
        revision = self._valid_current_publication(
            self._store.current_publication(owner_key),
            owner_key=owner_key,
            slug=slug,
        )
        if revision is None or revision.identity is None:
            raise ProfileNotFound("Profile unavailable.")
        return self._serialize_public(revision, destination=destination)

    def owner_preview_public(self, context: ProfileViewerContext, *, destination: str) -> ProfilePublicReadModel:
        """Owner preview intentionally calls the same exact public serializer."""

        self._owner_draft(context)
        return self.public_read(slug=context.profile_slug, destination=destination)

    def _new_publication_revision(
        self,
        draft: ProfileDraft,
        current: ProfilePublicationRevision | None,
        *,
        action: str,
        identity: ProfileIdentityDraft | None | object = ...,
        current_chapter: ProfileCurrentChapterDraft | None | object = ...,
        about: ProfileAboutDraft | None | object = ...,
        items: Sequence[ProfilePublicationItem] | object = ...,
    ) -> ProfilePublicationRevision:
        action = _publication_action(action)
        # Withdrawal deliberately passes explicit empty items.  It may remove
        # an old draft placement whose source has since been revoked, while a
        # normal draft-to-publication projection must re-resolve every source.
        if not self._valid_draft_manifest(
            draft, require_current_sources=items is ...
        ):
            raise ProfileUnavailableError("Profile draft dependency unavailable.")
        public_items = (
            tuple(items)
            if items is not ...
            else tuple(
                ProfilePublicationItem(
                    placement_key=item.placement_key,
                    content_kind=item.content_kind,
                    destination=item.destination,
                    region=item.region,
                    rank=item.rank,
                    featured=item.featured,
                    source_reference=item.source_reference,
                )
                for item in sorted(draft.placements, key=lambda candidate: (candidate.destination, candidate.region, candidate.rank, candidate.placement_key))
            )
        )
        selected_identity = draft.identity if identity is ... else identity
        selected_chapter = draft.current_chapter if current_chapter is ... else current_chapter
        selected_about = draft.about if about is ... else about
        if action == PROFILE_PUBLICATION_ACTION_PUBLISH and selected_identity is None:
            raise ProfileValidationError("A Profile publication requires identity.")
        if action == PROFILE_PUBLICATION_ACTION_WITHDRAW and (
            selected_identity is not None
            or selected_chapter is not None
            or selected_about is not None
            or public_items
        ):
            raise ProfileValidationError("A Profile withdrawal manifest must be empty.")
        number = (current.revision_number if current else 0) + 1
        digest = _digest(
            {
                "audience": PROFILE_AUDIENCE_PUBLIC,
                "action": action,
                "slug": draft.slug,
                "identity": _identity_payload(selected_identity),
                "current_chapter": _chapter_payload(selected_chapter),
                "about": _about_payload(selected_about),
                "items": [_item_payload(item) for item in public_items],
            }
        )
        return ProfilePublicationRevision(
            revision_key=_revision_token(number),
            owner_key=draft.owner_key,
            slug=draft.slug,
            audience=PROFILE_AUDIENCE_PUBLIC,
            action=action,
            revision_number=number,
            created_at=_now(),
            digest=digest,
            identity=selected_identity,
            current_chapter=selected_chapter,
            about=selected_about,
            items=public_items,
        )

    def _serialize_public(self, revision: ProfilePublicationRevision, *, destination: str) -> ProfilePublicReadModel:
        assert revision.identity is not None
        post_items = tuple(
            _public_item(item)
            for item in revision.items
            if item.content_kind == COMMUNITY_POST_KIND and item.destination in ({"posts"} if destination == "posts" else {"home"})
        )
        home_items = tuple(_public_item(item) for item in revision.items if item.destination == "home")
        projects = tuple(_public_item(item) for item in revision.items if item.destination == "projects")
        media = tuple(_public_item(item) for item in revision.items if item.destination == "media")
        voice = tuple(_public_item(item) for item in revision.items if item.destination == "voice")
        available = ["home"]
        if any(item.destination == "posts" for item in revision.items):
            available.append("posts")
        if projects:
            available.append("projects")
        if media:
            available.append("media")
        if voice:
            available.append("voice")
        if revision.about is not None:
            available.append("about")
        # Project, Media, and Voice are not decorative empty pages.  Until an
        # exact canonical projection is part of this immutable publication,
        # those optional destinations are absent and resolve neutrally.
        if destination in {"projects", "media", "voice"} and destination not in available:
            raise ProfileNotFound("Profile destination unavailable.")
        about = _about_payload(revision.about) if destination in {"home", "about"} else None
        chapter = _chapter_payload(revision.current_chapter) if destination == "home" else None
        return ProfilePublicReadModel(
            schema_version=PROFILE_SCHEMA_VERSION,
            profile_slug=revision.slug,
            mode="public",
            publication_revision=revision.revision_key,
            identity=_public_identity(revision.identity),
            current_chapter=chapter,
            about=about,
            home=home_items if destination == "home" else (),
            posts=post_items,
            projects=projects if destination == "projects" else (),
            media=media if destination == "media" else (),
            voice=voice if destination == "voice" else (),
            available_destinations=tuple(available),
            destination_state=(
                "ready"
                if destination == "home"
                or destination == "about" and about is not None
                or destination == "posts" and post_items
                or destination == "projects" and projects
                or destination == "media" and media
                or destination == "voice" and voice
                else "empty"
            ),
        )


def _draft_version_number(value: str) -> int:
    match = re.match(r"^v([0-9]+):", value)
    if not match:
        return 0
    return int(match.group(1))


def _identity_payload(value: ProfileIdentityDraft | None) -> Mapping[str, str | None] | None:
    return _public_identity(value) if value is not None else None


def _chapter_payload(value: ProfileCurrentChapterDraft | None) -> Mapping[str, str] | None:
    if value is None:
        return None
    return {"label": value.label, "body": value.body}


def _principles(value: object) -> tuple[ProfilePrincipleDraft, ...]:
    """Validate a small bounded Profile-native principle list.

    Principles are optional and use the existing bounded text fields rather
    than opening a general rich-content store in the foundation.
    """

    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > 4:
        raise ProfileValidationError("Invalid About principles.")
    principles: list[ProfilePrincipleDraft] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ProfileValidationError("Invalid About principles.")
        principles.append(
            ProfilePrincipleDraft(
                title=_text(item.get("title"), "about_heading") or "",
                body=_text(item.get("body"), "current_chapter_body") or "",
            )
        )
    return tuple(principles)


def _about_payload(value: ProfileAboutDraft | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return {
        "heading": value.heading,
        "body": value.body,
        "resume_path": value.resume_path,
        "story_path": value.story_path,
        "ask_path": value.ask_path,
        "principles": [
            {"title": principle.title, "body": principle.body}
            for principle in value.principles
        ],
    }


def _item_payload(item: ProfilePublicationItem) -> Mapping[str, Any]:
    reference = item.source_reference
    return {
        "placement_key": item.placement_key,
        "content_kind": item.content_kind,
        "destination": item.destination,
        "region": item.region,
        "rank": item.rank,
        "featured": item.featured,
        "source_reference": (
            {
                "source_key": reference.source_key,
                "source_revision": reference.source_revision,
                "canonical_path": reference.canonical_path,
                "published_at": reference.published_at.isoformat(),
            }
            if reference
            else None
        ),
    }


def _public_item(item: ProfilePublicationItem) -> Mapping[str, Any]:
    """Public shape intentionally excludes source keys/revisions/owner metadata."""

    reference = item.source_reference
    payload: dict[str, Any] = {
        "projection_key": item.placement_key,
        "kind": item.content_kind,
        "featured": item.featured,
    }
    if reference is not None:
        payload["canonical_path"] = reference.canonical_path
        payload["published_at"] = reference.published_at.isoformat()
    return payload


def _publication_changes(
    current: ProfilePublicationRevision | None, candidate: ProfilePublicationRevision
) -> Mapping[str, Any]:
    current_keys = {item.placement_key for item in current.items} if current else set()
    candidate_keys = {item.placement_key for item in candidate.items}
    return {
        "added_placement_keys": sorted(candidate_keys - current_keys),
        "removed_placement_keys": sorted(current_keys - candidate_keys),
        "identity_changed": (current is None or _identity_payload(current.identity) != _identity_payload(candidate.identity)),
        "current_chapter_changed": (current is None or _chapter_payload(current.current_chapter) != _chapter_payload(candidate.current_chapter)),
        "about_changed": (current is None or _about_payload(current.about) != _about_payload(candidate.about)),
    }


def make_profile_draft(
    *,
    owner_key: str,
    slug: str,
    identity: ProfileIdentityDraft | None = None,
    current_chapter: ProfileCurrentChapterDraft | None = None,
    about: ProfileAboutDraft | None = None,
    placements: Sequence[ProfilePlacementDraft] = (),
) -> ProfileDraft:
    """Build a valid explicit test/local draft without production defaults."""

    return ProfileDraft(
        draft_key=_token("pd"),
        owner_key=_opaque(owner_key, "owner key"),
        slug=_slug(slug),
        version=_revision_token(1),
        identity=identity,
        current_chapter=current_chapter,
        about=about,
        placements=tuple(placements),
    )
