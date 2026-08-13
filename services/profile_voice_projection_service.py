"""Exact retained-Voice projection contract; no capture, inference, or autoplay."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from typing import Protocol

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_VERSION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_PATH = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9._~-]*(?:/[A-Za-z0-9][A-Za-z0-9._~-]*)*$")


@dataclass(frozen=True)
class ProfileVoiceProjection:
    projection_key: str
    owner_key: str
    projection_version: str
    audience: str
    title: str
    context: str | None
    duration_seconds: int
    audio_path: str | None
    transcript: str | None
    transcript_approved: bool


class ProfileVoiceProjectionReader(Protocol):
    def get_exact_projection(
        self, *, owner_key: str, projection_key: str, projection_version: str, audience: str
    ) -> ProfileVoiceProjection | None: ...


def _path(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 512 and "\\" not in value and bool(_PATH.fullmatch(value))


def validate_voice_projection(
    value: object, *, owner_key: str, projection_key: str, projection_version: str, audience: str
) -> ProfileVoiceProjection:
    if not isinstance(value, ProfileVoiceProjection):
        raise ProfileNotFound("Voice projection unavailable.")
    if not all(
        isinstance(item, str)
        for item in (owner_key, projection_key, projection_version, audience)
    ) or not all(
        isinstance(item, str)
        for item in (
            value.owner_key,
            value.projection_key,
            value.projection_version,
            value.audience,
            value.title,
        )
    ):
        raise ProfileNotFound("Voice projection unavailable.")
    if not (
        _KEY.fullmatch(value.owner_key)
        and _KEY.fullmatch(value.projection_key)
        and _VERSION.fullmatch(value.projection_version)
        and hmac.compare_digest(value.owner_key, owner_key)
        and hmac.compare_digest(value.projection_key, projection_key)
        and hmac.compare_digest(value.projection_version, projection_version)
        and hmac.compare_digest(value.audience, audience)
        and value.audience in {"public", "connections"}
        and isinstance(value.title, str) and 0 < len(value.title.strip()) <= 240
        and (value.context is None or isinstance(value.context, str) and len(value.context) <= 2000)
        and isinstance(value.duration_seconds, int)
        and not isinstance(value.duration_seconds, bool)
        and 0 < value.duration_seconds <= 86400
        and (value.audio_path is None or _path(value.audio_path))
        and isinstance(value.transcript_approved, bool)
        and (
            value.transcript_approved
            and isinstance(value.transcript, str)
            and 0 < len(value.transcript) <= 100000
            or not value.transcript_approved
            and value.transcript is None
        )
        and (
            value.audio_path is not None
            or value.transcript_approved
            and value.transcript is not None
        )
    ):
        raise ProfileNotFound("Voice projection unavailable.")
    return value


class ProfileVoiceProjectionService:
    def __init__(self, reader: ProfileVoiceProjectionReader):
        self._reader = reader

    def resolve(self, *, owner_key: str, projection_key: str, projection_version: str, audience: str) -> ProfileVoiceProjection:
        try:
            value = self._reader.get_exact_projection(
                owner_key=owner_key, projection_key=projection_key,
                projection_version=projection_version, audience=audience,
            )
        except Exception as error:
            raise ProfileUnavailableError("Voice projection dependency unavailable.") from error
        return validate_voice_projection(
            value, owner_key=owner_key, projection_key=projection_key,
            projection_version=projection_version, audience=audience,
        )
