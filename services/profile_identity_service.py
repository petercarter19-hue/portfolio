"""Server-derived Profile identity and viewer-context resolution.

This module has no Flask/request dependency.  A later registered integration
adapts the already trusted Easy Auth identity into ``TrustedActorIdentity``;
browser supplied owner, mode, or audience values never enter this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from typing import Protocol

from services.profile_core_service import (
    ProfileAuthorizationError,
    ProfileNotFound,
    ProfileUnavailableError,
    ProfileValidationError,
    ProfileViewerContext,
)


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


@dataclass(frozen=True)
class TrustedActorIdentity:
    issuer: str
    subject: str


@dataclass(frozen=True)
class ProfileIdentityRecord:
    owner_key: str
    slug: str
    active: bool
    auth_epoch: str


class ProfileIdentityDirectory(Protocol):
    def profile_for_actor(self, identity: TrustedActorIdentity) -> ProfileIdentityRecord | None: ...

    def profile_for_slug(self, slug: str) -> ProfileIdentityRecord | None: ...


def _valid_record(record: object) -> ProfileIdentityRecord | None:
    if not isinstance(record, ProfileIdentityRecord):
        return None
    if (
        not isinstance(record.active, bool)
        or not record.active
        or not isinstance(record.owner_key, str)
        or not isinstance(record.slug, str)
        or not isinstance(record.auth_epoch, str)
        or not _KEY.fullmatch(record.owner_key)
        or not _SLUG.fullmatch(record.slug)
        or not _KEY.fullmatch(record.auth_epoch)
    ):
        return None
    return record


class ProfileIdentityService:
    """Resolve subject and actor identities before any protected retrieval."""

    def __init__(self, directory: ProfileIdentityDirectory):
        self._directory = directory

    def owner_context(self, actor: TrustedActorIdentity, *, purpose: str) -> ProfileViewerContext:
        if not isinstance(actor, TrustedActorIdentity) or not actor.issuer or not actor.subject:
            raise ProfileAuthorizationError("Profile action unavailable.")
        try:
            record = _valid_record(self._directory.profile_for_actor(actor))
        except Exception as error:
            raise ProfileUnavailableError("Profile identity dependency unavailable.") from error
        if record is None:
            raise ProfileNotFound("Profile unavailable.")
        return ProfileViewerContext(
            actor_key=record.owner_key,
            subject_owner_key=record.owner_key,
            profile_slug=record.slug,
            request_purpose=purpose,
        )

    def public_context(self, *, slug: str, purpose: str = "html") -> ProfileViewerContext:
        if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
            raise ProfileNotFound("Profile unavailable.")
        try:
            record = _valid_record(self._directory.profile_for_slug(slug))
        except Exception as error:
            raise ProfileUnavailableError("Profile identity dependency unavailable.") from error
        if record is None or not hmac.compare_digest(record.slug, slug):
            raise ProfileNotFound("Profile unavailable.")
        return ProfileViewerContext(
            actor_key=None,
            subject_owner_key=record.owner_key,
            profile_slug=record.slug,
            request_purpose=purpose,
        )


class InMemoryProfileIdentityDirectory:
    """Explicit test adapter; never used by application startup."""

    def __init__(self, entries: dict[tuple[str, str], ProfileIdentityRecord]):
        self._by_actor = dict(entries)
        self._by_slug = {record.slug: record for record in entries.values()}

    def profile_for_actor(self, identity: TrustedActorIdentity) -> ProfileIdentityRecord | None:
        return self._by_actor.get((identity.issuer, identity.subject))

    def profile_for_slug(self, slug: str) -> ProfileIdentityRecord | None:
        return self._by_slug.get(slug)
