"""Exact, audience-safe Media projection adapter for Profile."""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from typing import Protocol

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_VERSION = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_PATH = re.compile(r"^/[A-Za-z0-9][A-Za-z0-9._~-]*(?:/[A-Za-z0-9][A-Za-z0-9._~-]*)*$")
MEDIA_KINDS = frozenset({"photo", "album", "video"})


@dataclass(frozen=True)
class ProfileMediaProjection:
    projection_key: str
    owner_key: str
    projection_version: str
    audience: str
    kind: str
    title: str
    description: str | None
    derivative_path: str
    alt_text: str
    poster_path: str | None = None
    item_count: int | None = None
    duration_seconds: int | None = None


class ProfileMediaProjectionReader(Protocol):
    def get_exact_projection(
        self, *, owner_key: str, projection_key: str, projection_version: str, audience: str
    ) -> ProfileMediaProjection | None: ...


def _safe_path(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 512 and "\\" not in value and bool(_PATH.fullmatch(value))


def validate_media_projection(
    value: object, *, owner_key: str, projection_key: str, projection_version: str, audience: str
) -> ProfileMediaProjection:
    if not isinstance(value, ProfileMediaProjection):
        raise ProfileNotFound("Media projection unavailable.")
    if not all(
        isinstance(item, str)
        for item in (owner_key, projection_key, projection_version, audience)
    ):
        raise ProfileNotFound("Media projection unavailable.")
    if not all(
        isinstance(item, str)
        for item in (
            value.owner_key,
            value.projection_key,
            value.projection_version,
            value.audience,
            value.kind,
            value.title,
            value.alt_text,
        )
    ):
        raise ProfileNotFound("Media projection unavailable.")
    if not (
        _KEY.fullmatch(value.owner_key)
        and _KEY.fullmatch(value.projection_key)
        and _VERSION.fullmatch(value.projection_version)
        and hmac.compare_digest(value.owner_key, owner_key)
        and hmac.compare_digest(value.projection_key, projection_key)
        and hmac.compare_digest(value.projection_version, projection_version)
        and hmac.compare_digest(value.audience, audience)
        and value.audience in {"public", "connections"}
        and value.kind in MEDIA_KINDS
        and isinstance(value.title, str) and 0 < len(value.title.strip()) <= 240
        and (value.description is None or isinstance(value.description, str) and len(value.description) <= 2000)
        and _safe_path(value.derivative_path)
        and isinstance(value.alt_text, str) and len(value.alt_text.strip()) <= 1000
        and (value.poster_path is None or _safe_path(value.poster_path))
        and (
            value.item_count is None
            or isinstance(value.item_count, int)
            and not isinstance(value.item_count, bool)
            and 0 <= value.item_count <= 100000
        )
        and (
            value.duration_seconds is None
            or isinstance(value.duration_seconds, int)
            and not isinstance(value.duration_seconds, bool)
            and 0 <= value.duration_seconds <= 86400
        )
    ):
        raise ProfileNotFound("Media projection unavailable.")
    return value


class ProfileMediaProjectionService:
    def __init__(self, reader: ProfileMediaProjectionReader):
        self._reader = reader

    def resolve(self, *, owner_key: str, projection_key: str, projection_version: str, audience: str) -> ProfileMediaProjection:
        try:
            value = self._reader.get_exact_projection(
                owner_key=owner_key, projection_key=projection_key,
                projection_version=projection_version, audience=audience,
            )
        except Exception as error:
            raise ProfileUnavailableError("Media projection dependency unavailable.") from error
        return validate_media_projection(
            value, owner_key=owner_key, projection_key=projection_key,
            projection_version=projection_version, audience=audience,
        )
