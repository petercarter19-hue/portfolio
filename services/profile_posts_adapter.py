"""Narrow Community-reference adapter for the Profile D0 foundation.

Profile may present a member-selected reference to an authored Community post,
but it never becomes a second Community store.  This module deliberately knows
only the minimum stable reference shape: the source owner's opaque key, one
exact source revision, a canonical conversation path, and publication time.
It neither accepts nor returns post/reply bodies, reactions, attachments, or
conversation data.

The concrete Community reader is injected by the later integration package.
The in-memory reader below exists solely for isolated service and route tests;
it is not wired into the application or a database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Mapping, Protocol


_OPAQUE_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_REVISION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Profile never treats a source-provided value as an arbitrary URL.  Community
# supplies an already-normalized internal path; this deliberately narrow shape
# excludes schemes, authorities, escaping, query/fragment syntax, traversal,
# and encoded host tricks rather than attempting to sanitize them later.
_CANONICAL_INTERNAL_PATH = re.compile(
    r"^/(?:[A-Za-z0-9][A-Za-z0-9._~-]*)(?:/[A-Za-z0-9][A-Za-z0-9._~-]*)*$"
)


class ProfilePostsAdapterError(Exception):
    """Base error for a Profile-to-Community reference failure."""


class ProfilePostReferenceNotFound(ProfilePostsAdapterError):
    """The source is absent, belongs to another owner, or is ineligible."""


class ProfilePostsDependencyUnavailable(ProfilePostsAdapterError):
    """The source-owning room cannot safely answer the adapter request."""


class ProfilePostReferenceValidationError(ProfilePostsAdapterError):
    """The caller supplied a malformed opaque source reference."""


@dataclass(frozen=True)
class EligibleCommunityPostSource:
    """An exact Community source revision that Profile may reference.

    ``source_key`` remains internal to Profile's owner service.  The public
    Profile serializer uses a Profile-owned opaque placement key instead.
    There is intentionally no content/body/comment/reply field here.
    """

    source_key: str
    owner_key: str
    source_revision: str
    canonical_path: str
    published_at: datetime
    profile_eligible: bool = True


@dataclass(frozen=True)
class CommunityPostReference:
    """Reference stored by Profile, not a copy of Community truth."""

    source_key: str
    source_revision: str
    canonical_path: str
    published_at: datetime


@dataclass(frozen=True)
class CommunityPostSourceStatus:
    """Owner-only freshness signal for an already pinned reference."""

    state: str
    current_revision: str | None


class CommunityPostSourceReader(Protocol):
    """Dependency-owned reader that exposes no broad Community feed."""

    def get_exact_profile_eligible_post(
        self, *, owner_key: str, source_key: str, source_revision: str
    ) -> EligibleCommunityPostSource | None:
        """Return only the requested exact eligible source revision."""

    def get_current_profile_eligible_revision(
        self, *, owner_key: str, source_key: str
    ) -> str | None:
        """Return the current eligible revision without returning post content."""


def validate_community_post_reference(
    reference: CommunityPostReference,
) -> CommunityPostReference:
    """Validate the body-free reference shape retained by Profile.

    A resolver normally creates this value, but Profile validates it again at
    its own boundary so an incorrectly implemented injected resolver cannot
    introduce an external URL, a cross-shaped identifier, or an unsafe time
    value into a publication draft.
    """

    if not isinstance(reference, CommunityPostReference):
        raise ProfilePostReferenceValidationError("Invalid Community post reference.")
    return CommunityPostReference(
        source_key=_opaque(reference.source_key, field="Community post reference"),
        source_revision=_revision(reference.source_revision),
        canonical_path=_canonical_path(reference.canonical_path),
        published_at=_published_at(reference.published_at),
    )


def _opaque(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_KEY.fullmatch(value):
        raise ProfilePostReferenceValidationError(f"Invalid {field}.")
    return value


def _revision(value: object) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise ProfilePostReferenceValidationError("Invalid source revision.")
    return value


def _canonical_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 512
        or "\\" in value
        or not _CANONICAL_INTERNAL_PATH.fullmatch(value)
    ):
        raise ProfilePostReferenceValidationError("Invalid canonical post path.")
    return value


def _published_at(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise ProfilePostReferenceValidationError("Invalid post publication time.")
    if value.tzinfo is None:
        raise ProfilePostReferenceValidationError("Post publication time must be timezone-aware.")
    return value.astimezone(timezone.utc)


class CommunityPostReferenceAdapter:
    """Validates exact Community references without importing Community truth."""

    def __init__(self, reader: CommunityPostSourceReader):
        self._reader = reader

    def reference_for(
        self, *, owner_key: str, source_key: str, source_revision: str
    ) -> CommunityPostReference:
        """Resolve the exact allowed source revision for one owner.

        The call names both owner and source revision.  A broad source query
        followed by Python-side filtering would violate the Profile boundary.
        """

        owner_key = _opaque(owner_key, field="owner key")
        source_key = _opaque(source_key, field="Community post reference")
        source_revision = _revision(source_revision)
        try:
            source = self._reader.get_exact_profile_eligible_post(
                owner_key=owner_key,
                source_key=source_key,
                source_revision=source_revision,
            )
        except ProfilePostsAdapterError:
            raise
        except Exception as error:  # pragma: no cover - defensive integration fence
            raise ProfilePostsDependencyUnavailable("Community reference unavailable.") from error

        if source is None:
            raise ProfilePostReferenceNotFound("Community reference unavailable.")
        if not isinstance(source, EligibleCommunityPostSource):
            raise ProfilePostReferenceNotFound("Community reference unavailable.")

        # Validate the injected dependency output before retaining any part of
        # it.  This catches an adapter that returns a cross-owner or stale row.
        if (
            _opaque(source.source_key, field="Community post reference") != source_key
            or _opaque(source.owner_key, field="owner key") != owner_key
            or _revision(source.source_revision) != source_revision
            or not source.profile_eligible
        ):
            raise ProfilePostReferenceNotFound("Community reference unavailable.")

        return validate_community_post_reference(CommunityPostReference(
            source_key=source_key,
            source_revision=source_revision,
            canonical_path=_canonical_path(source.canonical_path),
            published_at=_published_at(source.published_at),
        ))

    def source_status(
        self, *, owner_key: str, reference: CommunityPostReference
    ) -> CommunityPostSourceStatus:
        """Return an owner-only stale signal; never rewrite the reference."""

        owner_key = _opaque(owner_key, field="owner key")
        reference = validate_community_post_reference(reference)
        source_key = reference.source_key
        source_revision = reference.source_revision
        try:
            current_revision = self._reader.get_current_profile_eligible_revision(
                owner_key=owner_key,
                source_key=source_key,
            )
        except ProfilePostsAdapterError:
            raise
        except Exception as error:  # pragma: no cover - defensive integration fence
            raise ProfilePostsDependencyUnavailable("Community reference unavailable.") from error

        if current_revision is None:
            # A revoked/deleted source cannot be silently replaced.  The owner
            # must resolve it before a later publication command.
            return CommunityPostSourceStatus(state="unavailable", current_revision=None)
        current_revision = _revision(current_revision)
        if current_revision == source_revision:
            return CommunityPostSourceStatus(state="current", current_revision=current_revision)
        return CommunityPostSourceStatus(state="source_changed", current_revision=current_revision)

    def verify_current_exact_reference(
        self, *, owner_key: str, reference: CommunityPostReference
    ) -> CommunityPostReference:
        """Re-resolve a stored reference before Profile creates a new publication.

        A draft is not a capability to keep publishing a source forever.  This
        deliberately requires both the exact eligible revision and that it is
        still the source's current eligible revision.  It returns the exact
        normalized value only when the dependency agrees with every retained
        field, so a hostile or stale adapter response cannot be substituted.
        """

        owner_key = _opaque(owner_key, field="owner key")
        reference = validate_community_post_reference(reference)
        resolved = self.reference_for(
            owner_key=owner_key,
            source_key=reference.source_key,
            source_revision=reference.source_revision,
        )
        if resolved != reference:
            raise ProfilePostReferenceNotFound("Community reference unavailable.")
        status = self.source_status(owner_key=owner_key, reference=resolved)
        if status.state != "current":
            raise ProfilePostReferenceNotFound("Community reference unavailable.")
        return resolved


class InMemoryCommunityPostSourceReader:
    """Small deterministic test double; deliberately not an application service."""

    def __init__(
        self,
        records: Mapping[tuple[str, str, str], EligibleCommunityPostSource] | None = None,
        current_revisions: Mapping[tuple[str, str], str] | None = None,
    ):
        self._records = dict(records or {})
        self._current_revisions = dict(current_revisions or {})

    def get_exact_profile_eligible_post(
        self, *, owner_key: str, source_key: str, source_revision: str
    ) -> EligibleCommunityPostSource | None:
        return self._records.get((owner_key, source_key, source_revision))

    def get_current_profile_eligible_revision(
        self, *, owner_key: str, source_key: str
    ) -> str | None:
        return self._current_revisions.get((owner_key, source_key))
