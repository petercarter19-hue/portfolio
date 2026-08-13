"""Read-only exact Project projection contract for the Profile destination."""

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
class ProfileProjectProjection:
    projection_key: str
    owner_key: str
    projection_version: str
    audience: str
    title: str
    summary: str
    role: str | None
    period: str | None
    outcome: str | None
    canonical_path: str


class ProfileProjectProjectionReader(Protocol):
    def get_exact_projection(
        self, *, owner_key: str, projection_key: str, projection_version: str, audience: str
    ) -> ProfileProjectProjection | None: ...


def validate_project_projection(
    value: object, *, owner_key: str, projection_key: str, projection_version: str, audience: str
) -> ProfileProjectProjection:
    if not isinstance(value, ProfileProjectProjection):
        raise ProfileNotFound("Project projection unavailable.")
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
            value.summary,
            value.canonical_path,
        )
    ):
        raise ProfileNotFound("Project projection unavailable.")
    bounded = (value.title, value.summary, value.role, value.period, value.outcome)
    if not (
        _KEY.fullmatch(value.owner_key)
        and _KEY.fullmatch(value.projection_key)
        and _VERSION.fullmatch(value.projection_version)
        and hmac.compare_digest(value.owner_key, owner_key)
        and hmac.compare_digest(value.projection_key, projection_key)
        and hmac.compare_digest(value.projection_version, projection_version)
        and hmac.compare_digest(value.audience, audience)
        and value.audience in {"public", "connections"}
        and all(item is None or isinstance(item, str) for item in bounded)
        and 0 < len(value.title.strip()) <= 240 and 0 < len(value.summary.strip()) <= 4000
        and all(item is None or len(item) <= 1000 for item in (value.role, value.period, value.outcome))
        and len(value.canonical_path) <= 512
        and "\\" not in value.canonical_path and bool(_PATH.fullmatch(value.canonical_path))
    ):
        raise ProfileNotFound("Project projection unavailable.")
    return value


class ProfileProjectProjectionService:
    def __init__(self, reader: ProfileProjectProjectionReader):
        self._reader = reader

    def resolve(self, *, owner_key: str, projection_key: str, projection_version: str, audience: str) -> ProfileProjectProjection:
        try:
            value = self._reader.get_exact_projection(
                owner_key=owner_key, projection_key=projection_key,
                projection_version=projection_version, audience=audience,
            )
        except Exception as error:
            raise ProfileUnavailableError("Project projection dependency unavailable.") from error
        return validate_project_projection(
            value, owner_key=owner_key, projection_key=projection_key,
            projection_version=projection_version, audience=audience,
        )
