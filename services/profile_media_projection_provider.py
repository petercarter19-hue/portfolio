"""Dark, injected provider for authorized Profile photo projections.

The module deliberately has no runtime registration and no SQL or Blob client.
Its ports are the seam for later, separately governed bindings.  Callers must
pass an already trusted, server-derived viewer key (or ``None`` for an
anonymous public request).  Every grant, audience decision, and source
snapshot is re-read after the private preview is opened, so a concurrent
withdrawal, block, source advance, or deletion prevents the bytes from being
returned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import re
from typing import Protocol

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_media_projection_service import (
    ProfileMediaProjection,
    validate_media_projection,
)


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_VERSION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_PHOTO_CONTENT_TYPES = frozenset({"image/jpeg", "image/png"})
_MAX_PREVIEW_BYTES = 10 * 1024 * 1024
_NOT_FOUND = "Media projection unavailable."
_UNAVAILABLE = "Media projection dependency unavailable."


@dataclass(frozen=True)
class MediaProjectionGrant:
    """Canonical publication binding; no storage locator is admitted."""

    projection_key: str = field(repr=False)
    owner_key: str = field(repr=False)
    projection_version: str
    audience: str
    source_key: str = field(repr=False)
    source_version: str
    derivative_sha256_digest: bytes = field(repr=False)
    published: bool
    revoked: bool
    where_used: bool
    kind: str
    title: str
    description: str | None
    derivative_path: str
    alt_text: str


@dataclass(frozen=True)
class MediaAudienceDecision:
    """Exact result from the relationship/block authorization boundary."""

    owner_key: str = field(repr=False)
    viewer_key: str | None = field(repr=False)
    audience: str
    authorization_epoch: str
    authorized: bool
    owner_blocked_viewer: bool
    viewer_blocked_owner: bool


@dataclass(frozen=True)
class PhotoSourceSnapshot:
    """Owner-scoped, current derivative lifecycle truth."""

    owner_key: str = field(repr=False)
    source_key: str = field(repr=False)
    source_version: str
    derivative_sha256_digest: bytes = field(repr=False)
    lifecycle_state: str
    current: bool
    deleted: bool
    scan_state: str
    media_kind: str
    metadata_stripped: bool
    content_type: str
    byte_length: int


@dataclass(frozen=True)
class PrivatePhotoPreview:
    """Locator-free result from the private preview-byte boundary."""

    body: bytes = field(repr=False)
    content_type: str
    byte_length: int
    sha256_digest: bytes = field(repr=False)


@dataclass(frozen=True)
class AuthorizedMediaProjection:
    """Internal delivery value; routes must not serialize domain identifiers."""

    projection: ProfileMediaProjection = field(repr=False)
    body: bytes = field(repr=False)
    content_type: str
    byte_length: int
    derivative_sha256_digest: bytes = field(repr=False)


class MediaProjectionGrantPort(Protocol):
    def get_exact_grant(
        self,
        *,
        owner_key: str,
        projection_key: str,
        projection_version: str,
        audience: str,
    ) -> MediaProjectionGrant | None: ...


class MediaAudienceAuthorizationPort(Protocol):
    def authorize(
        self, *, owner_key: str, viewer_key: str | None, audience: str
    ) -> MediaAudienceDecision | None: ...


class PhotoSourceLifecyclePort(Protocol):
    def get_exact_source(
        self, *, owner_key: str, source_key: str, source_version: str
    ) -> PhotoSourceSnapshot | None: ...


class PrivatePhotoPreviewPort(Protocol):
    def open_preview(
        self,
        *,
        owner_key: str,
        source_key: str,
        source_version: str,
        expected_sha256_digest: bytes,
        expected_byte_length: int,
    ) -> PrivatePhotoPreview | None: ...


@dataclass(frozen=True)
class _AuthorizedState:
    grant: MediaProjectionGrant
    audience: MediaAudienceDecision
    source: PhotoSourceSnapshot


def _not_found() -> ProfileNotFound:
    return ProfileNotFound(_NOT_FOUND)


def _valid_key(value: object) -> bool:
    return isinstance(value, str) and bool(_KEY.fullmatch(value))


def _valid_version(value: object) -> bool:
    return isinstance(value, str) and bool(_VERSION.fullmatch(value))


def _valid_digest(value: object) -> bool:
    return isinstance(value, bytes) and len(value) == 32


def _same(left: object, right: object) -> bool:
    return (
        isinstance(left, str)
        and isinstance(right, str)
        and hmac.compare_digest(left, right)
    )


def _same_optional(left: object, right: object) -> bool:
    return left is None and right is None or _same(left, right)


class ProfileMediaProjectionProvider:
    """Authorize and open one exact metadata-stripped photo preview."""

    def __init__(
        self,
        *,
        grants: MediaProjectionGrantPort,
        audiences: MediaAudienceAuthorizationPort,
        sources: PhotoSourceLifecyclePort,
        previews: PrivatePhotoPreviewPort,
    ):
        self._grants = grants
        self._audiences = audiences
        self._sources = sources
        self._previews = previews

    @staticmethod
    def _dependency(call):
        try:
            return call()
        except Exception:
            raise ProfileUnavailableError(_UNAVAILABLE) from None

    @staticmethod
    def _validate_request(
        *,
        owner_key: object,
        viewer_key: object,
        projection_key: object,
        projection_version: object,
        audience: object,
    ) -> None:
        if not (
            _valid_key(owner_key)
            and (viewer_key is None or _valid_key(viewer_key))
            and _valid_key(projection_key)
            and _valid_version(projection_version)
            and isinstance(audience, str)
            and audience in {"public", "connections"}
            and (audience == "public" or viewer_key is not None)
        ):
            raise _not_found()

    @staticmethod
    def _validate_grant(
        value: object,
        *,
        owner_key: str,
        projection_key: str,
        projection_version: str,
        audience: str,
    ) -> MediaProjectionGrant:
        if not isinstance(value, MediaProjectionGrant):
            raise _not_found()
        if not (
            _valid_key(value.owner_key)
            and _valid_key(value.projection_key)
            and _valid_version(value.projection_version)
            and _valid_key(value.source_key)
            and _valid_version(value.source_version)
            and _valid_digest(value.derivative_sha256_digest)
            and _same(value.owner_key, owner_key)
            and _same(value.projection_key, projection_key)
            and _same(value.projection_version, projection_version)
            and _same(value.audience, audience)
            and value.audience in {"public", "connections"}
            and type(value.published) is bool
            and value.published
            and type(value.revoked) is bool
            and not value.revoked
            and type(value.where_used) is bool
            and value.where_used
            and value.kind == "photo"
            and isinstance(value.title, str)
            and 0 < len(value.title.strip()) <= 240
            and (
                value.description is None
                or isinstance(value.description, str)
                and len(value.description) <= 2000
            )
            and isinstance(value.derivative_path, str)
            and isinstance(value.alt_text, str)
            and 0 < len(value.alt_text.strip()) <= 1000
        ):
            raise _not_found()
        validate_media_projection(
            ProfileMediaProjection(
                projection_key=value.projection_key,
                owner_key=value.owner_key,
                projection_version=value.projection_version,
                audience=value.audience,
                kind=value.kind,
                title=value.title,
                description=value.description,
                derivative_path=value.derivative_path,
                alt_text=value.alt_text,
            ),
            owner_key=owner_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        return value

    @staticmethod
    def _validate_audience(
        value: object,
        *,
        owner_key: str,
        viewer_key: str | None,
        audience: str,
    ) -> MediaAudienceDecision:
        if not isinstance(value, MediaAudienceDecision):
            raise _not_found()
        if not (
            _valid_key(value.owner_key)
            and (value.viewer_key is None or _valid_key(value.viewer_key))
            and _valid_version(value.authorization_epoch)
            and _same(value.owner_key, owner_key)
            and _same_optional(value.viewer_key, viewer_key)
            and _same(value.audience, audience)
            and type(value.authorized) is bool
            and value.authorized
            and type(value.owner_blocked_viewer) is bool
            and not value.owner_blocked_viewer
            and type(value.viewer_blocked_owner) is bool
            and not value.viewer_blocked_owner
        ):
            raise _not_found()
        return value

    @staticmethod
    def _validate_source(
        value: object, *, owner_key: str, grant: MediaProjectionGrant
    ) -> PhotoSourceSnapshot:
        if not isinstance(value, PhotoSourceSnapshot):
            raise _not_found()
        if not (
            _valid_key(value.owner_key)
            and _valid_key(value.source_key)
            and _valid_version(value.source_version)
            and _valid_digest(value.derivative_sha256_digest)
            and _same(value.owner_key, owner_key)
            and _same(value.source_key, grant.source_key)
            and _same(value.source_version, grant.source_version)
            and hmac.compare_digest(
                value.derivative_sha256_digest, grant.derivative_sha256_digest
            )
            and value.lifecycle_state == "confirmed"
            and type(value.current) is bool
            and value.current
            and type(value.deleted) is bool
            and not value.deleted
            and value.scan_state == "clean"
            and value.media_kind == "preview"
            and type(value.metadata_stripped) is bool
            and value.metadata_stripped
            and isinstance(value.content_type, str)
            and value.content_type in _PHOTO_CONTENT_TYPES
            and isinstance(value.byte_length, int)
            and not isinstance(value.byte_length, bool)
            and 0 < value.byte_length <= _MAX_PREVIEW_BYTES
        ):
            raise _not_found()
        return value

    def _authorized_state(
        self,
        *,
        owner_key: str,
        viewer_key: str | None,
        projection_key: str,
        projection_version: str,
        audience: str,
    ) -> _AuthorizedState:
        grant = self._validate_grant(
            self._dependency(
                lambda: self._grants.get_exact_grant(
                    owner_key=owner_key,
                    projection_key=projection_key,
                    projection_version=projection_version,
                    audience=audience,
                )
            ),
            owner_key=owner_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        decision = self._validate_audience(
            self._dependency(
                lambda: self._audiences.authorize(
                    owner_key=owner_key,
                    viewer_key=viewer_key,
                    audience=audience,
                )
            ),
            owner_key=owner_key,
            viewer_key=viewer_key,
            audience=audience,
        )
        source = self._validate_source(
            self._dependency(
                lambda: self._sources.get_exact_source(
                    owner_key=owner_key,
                    source_key=grant.source_key,
                    source_version=grant.source_version,
                )
            ),
            owner_key=owner_key,
            grant=grant,
        )
        return _AuthorizedState(grant=grant, audience=decision, source=source)

    @staticmethod
    def _validate_preview(
        value: object, *, source: PhotoSourceSnapshot
    ) -> PrivatePhotoPreview:
        if not isinstance(value, PrivatePhotoPreview):
            raise _not_found()
        if not (
            isinstance(value.body, bytes)
            and value.content_type == source.content_type
            and isinstance(value.byte_length, int)
            and not isinstance(value.byte_length, bool)
            and value.byte_length == source.byte_length
            and len(value.body) == source.byte_length
            and _valid_digest(value.sha256_digest)
            and hmac.compare_digest(
                value.sha256_digest, source.derivative_sha256_digest
            )
            and hmac.compare_digest(
                hashlib.sha256(value.body).digest(), source.derivative_sha256_digest
            )
        ):
            raise _not_found()
        return value

    def resolve(
        self,
        *,
        owner_key: str,
        viewer_key: str | None,
        projection_key: str,
        projection_version: str,
        audience: str,
    ) -> AuthorizedMediaProjection:
        self._validate_request(
            owner_key=owner_key,
            viewer_key=viewer_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        before = self._authorized_state(
            owner_key=owner_key,
            viewer_key=viewer_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        opened = self._dependency(
            lambda: self._previews.open_preview(
                owner_key=owner_key,
                source_key=before.grant.source_key,
                source_version=before.grant.source_version,
                expected_sha256_digest=before.source.derivative_sha256_digest,
                expected_byte_length=before.source.byte_length,
            )
        )
        after = self._authorized_state(
            owner_key=owner_key,
            viewer_key=viewer_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        if before != after:
            raise _not_found()
        preview = self._validate_preview(opened, source=after.source)
        projection = validate_media_projection(
            ProfileMediaProjection(
                projection_key=after.grant.projection_key,
                owner_key=after.grant.owner_key,
                projection_version=after.grant.projection_version,
                audience=after.grant.audience,
                kind=after.grant.kind,
                title=after.grant.title,
                description=after.grant.description,
                derivative_path=after.grant.derivative_path,
                alt_text=after.grant.alt_text,
            ),
            owner_key=owner_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        return AuthorizedMediaProjection(
            projection=projection,
            body=preview.body,
            content_type=preview.content_type,
            byte_length=preview.byte_length,
            derivative_sha256_digest=after.source.derivative_sha256_digest,
        )
