"""Dark, injected provider for authorized retained-Voice projections.

Only a member-approved transcript is admitted.  A provider transcription
attempt is deliberately absent from every port and return type.  The module has
no runtime registration and no SQL, Speech, identity, or storage client; later
bindings require their own governed delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import re
from typing import Protocol

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_voice_projection_service import (
    ProfileVoiceProjection,
    validate_voice_projection,
)


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_VERSION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_VOICE_CONTENT_TYPES = frozenset(
    {"audio/webm", "audio/ogg", "audio/wav", "audio/mp4", "audio/mpeg", "audio/aac"}
)
_MAX_AUDIO_BYTES = 20 * 1024 * 1024
_NOT_FOUND = "Voice projection unavailable."
_UNAVAILABLE = "Voice projection dependency unavailable."


@dataclass(frozen=True)
class VoiceProjectionGrant:
    """Canonical publication binding, including only approved transcript truth."""

    projection_key: str = field(repr=False)
    owner_key: str = field(repr=False)
    projection_version: str
    audience: str
    source_key: str = field(repr=False)
    source_version: str
    source_sha256_digest: bytes = field(repr=False)
    capture_revision: str
    published: bool
    revoked: bool
    where_used: bool
    title: str
    context: str | None
    duration_seconds: int
    audio_path: str | None
    approved_transcript: str | None = field(repr=False)
    transcript_approved: bool


@dataclass(frozen=True)
class VoiceAudienceDecision:
    owner_key: str = field(repr=False)
    viewer_key: str | None = field(repr=False)
    audience: str
    authorization_epoch: str
    authorized: bool
    owner_blocked_viewer: bool
    viewer_blocked_owner: bool


@dataclass(frozen=True)
class VoiceSourceSnapshot:
    """Owner-scoped retained source and exact approved-Capture lineage."""

    owner_key: str = field(repr=False)
    source_key: str = field(repr=False)
    source_version: str
    source_sha256_digest: bytes = field(repr=False)
    capture_revision: str
    lifecycle_state: str
    current: bool
    deleted: bool
    audio_available: bool
    content_type: str | None
    byte_length: int | None
    duration_seconds: int


@dataclass(frozen=True)
class PrivateVoiceAudio:
    """Locator-free result from the private retained-audio boundary."""

    body: bytes = field(repr=False)
    content_type: str
    byte_length: int
    sha256_digest: bytes = field(repr=False)


@dataclass(frozen=True)
class AuthorizedVoiceProjection:
    """Internal delivery value with explicit partial-state and playback truth."""

    projection: ProfileVoiceProjection = field(repr=False)
    audio_body: bytes | None = field(repr=False)
    content_type: str | None
    byte_length: int | None
    source_sha256_digest: bytes = field(repr=False)
    transcript_available: bool
    autoplay: bool = False


class VoiceProjectionGrantPort(Protocol):
    def get_exact_grant(
        self,
        *,
        owner_key: str,
        projection_key: str,
        projection_version: str,
        audience: str,
    ) -> VoiceProjectionGrant | None: ...


class VoiceAudienceAuthorizationPort(Protocol):
    def authorize(
        self, *, owner_key: str, viewer_key: str | None, audience: str
    ) -> VoiceAudienceDecision | None: ...


class VoiceSourceLifecyclePort(Protocol):
    def get_exact_source(
        self, *, owner_key: str, source_key: str, source_version: str
    ) -> VoiceSourceSnapshot | None: ...


class PrivateVoiceAudioPort(Protocol):
    def open_audio(
        self,
        *,
        owner_key: str,
        source_key: str,
        source_version: str,
        expected_sha256_digest: bytes,
        expected_byte_length: int,
    ) -> PrivateVoiceAudio | None: ...


@dataclass(frozen=True)
class _AuthorizedState:
    grant: VoiceProjectionGrant
    audience: VoiceAudienceDecision
    source: VoiceSourceSnapshot


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


class ProfileVoiceProjectionProvider:
    """Authorize one exact Voice projection and open audio only when included."""

    def __init__(
        self,
        *,
        grants: VoiceProjectionGrantPort,
        audiences: VoiceAudienceAuthorizationPort,
        sources: VoiceSourceLifecyclePort,
        audio: PrivateVoiceAudioPort,
    ):
        self._grants = grants
        self._audiences = audiences
        self._sources = sources
        self._audio = audio

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
    ) -> VoiceProjectionGrant:
        if not isinstance(value, VoiceProjectionGrant):
            raise _not_found()
        approved = (
            type(value.transcript_approved) is bool
            and value.transcript_approved
            and isinstance(value.approved_transcript, str)
            and 0 < len(value.approved_transcript.strip()) <= 100000
        )
        unapproved = (
            type(value.transcript_approved) is bool
            and not value.transcript_approved
            and value.approved_transcript is None
        )
        if not (
            _valid_key(value.owner_key)
            and _valid_key(value.projection_key)
            and _valid_version(value.projection_version)
            and _valid_key(value.source_key)
            and _valid_version(value.source_version)
            and _valid_digest(value.source_sha256_digest)
            and _valid_version(value.capture_revision)
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
            and isinstance(value.title, str)
            and 0 < len(value.title.strip()) <= 240
            and (
                value.context is None
                or isinstance(value.context, str)
                and len(value.context) <= 2000
            )
            and isinstance(value.duration_seconds, int)
            and not isinstance(value.duration_seconds, bool)
            and 0 < value.duration_seconds <= 86400
            and (value.audio_path is None or isinstance(value.audio_path, str))
            and (approved or unapproved)
            and (value.audio_path is not None or approved)
        ):
            raise _not_found()
        validate_voice_projection(
            ProfileVoiceProjection(
                projection_key=value.projection_key,
                owner_key=value.owner_key,
                projection_version=value.projection_version,
                audience=value.audience,
                title=value.title,
                context=value.context,
                duration_seconds=value.duration_seconds,
                audio_path=value.audio_path,
                transcript=value.approved_transcript,
                transcript_approved=value.transcript_approved,
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
    ) -> VoiceAudienceDecision:
        if not isinstance(value, VoiceAudienceDecision):
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
        value: object, *, owner_key: str, grant: VoiceProjectionGrant
    ) -> VoiceSourceSnapshot:
        if not isinstance(value, VoiceSourceSnapshot):
            raise _not_found()
        has_valid_audio = (
            type(value.audio_available) is bool
            and value.audio_available
            and isinstance(value.content_type, str)
            and value.content_type in _VOICE_CONTENT_TYPES
            and isinstance(value.byte_length, int)
            and not isinstance(value.byte_length, bool)
            and 0 < value.byte_length <= _MAX_AUDIO_BYTES
        )
        has_no_audio = (
            type(value.audio_available) is bool
            and not value.audio_available
            and value.content_type is None
            and value.byte_length is None
        )
        if not (
            _valid_key(value.owner_key)
            and _valid_key(value.source_key)
            and _valid_version(value.source_version)
            and _valid_digest(value.source_sha256_digest)
            and _valid_version(value.capture_revision)
            and _same(value.owner_key, owner_key)
            and _same(value.source_key, grant.source_key)
            and _same(value.source_version, grant.source_version)
            and _same(value.capture_revision, grant.capture_revision)
            and hmac.compare_digest(
                value.source_sha256_digest, grant.source_sha256_digest
            )
            and value.lifecycle_state == "confirmed"
            and type(value.current) is bool
            and value.current
            and type(value.deleted) is bool
            and not value.deleted
            and isinstance(value.duration_seconds, int)
            and not isinstance(value.duration_seconds, bool)
            and value.duration_seconds == grant.duration_seconds
            and (has_valid_audio or has_no_audio)
            and (grant.audio_path is None or has_valid_audio)
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
    def _validate_audio(
        value: object, *, source: VoiceSourceSnapshot
    ) -> PrivateVoiceAudio:
        if not isinstance(value, PrivateVoiceAudio):
            raise _not_found()
        if not (
            isinstance(value.body, bytes)
            and value.content_type == source.content_type
            and isinstance(value.byte_length, int)
            and not isinstance(value.byte_length, bool)
            and value.byte_length == source.byte_length
            and len(value.body) == source.byte_length
            and _valid_digest(value.sha256_digest)
            and hmac.compare_digest(value.sha256_digest, source.source_sha256_digest)
            and hmac.compare_digest(
                hashlib.sha256(value.body).digest(), source.source_sha256_digest
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
    ) -> AuthorizedVoiceProjection:
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
        opened = None
        if before.grant.audio_path is not None:
            opened = self._dependency(
                lambda: self._audio.open_audio(
                    owner_key=owner_key,
                    source_key=before.grant.source_key,
                    source_version=before.grant.source_version,
                    expected_sha256_digest=before.source.source_sha256_digest,
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
        audio = None
        if after.grant.audio_path is not None:
            audio = self._validate_audio(opened, source=after.source)
        projection = validate_voice_projection(
            ProfileVoiceProjection(
                projection_key=after.grant.projection_key,
                owner_key=after.grant.owner_key,
                projection_version=after.grant.projection_version,
                audience=after.grant.audience,
                title=after.grant.title,
                context=after.grant.context,
                duration_seconds=after.grant.duration_seconds,
                audio_path=after.grant.audio_path,
                transcript=after.grant.approved_transcript,
                transcript_approved=after.grant.transcript_approved,
            ),
            owner_key=owner_key,
            projection_key=projection_key,
            projection_version=projection_version,
            audience=audience,
        )
        return AuthorizedVoiceProjection(
            projection=projection,
            audio_body=None if audio is None else audio.body,
            content_type=None if audio is None else audio.content_type,
            byte_length=None if audio is None else audio.byte_length,
            source_sha256_digest=after.source.source_sha256_digest,
            transcript_available=after.grant.transcript_approved,
        )
