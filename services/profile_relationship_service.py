"""Profile-local relationship authorization state model.

The canonical relationship lifecycle remains owned by PS-CONNECT-002.  This
adapter can consume that future service without recreating connections in
Profile.  Until injected and healthy, Connections reads fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from typing import Protocol

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


@dataclass(frozen=True)
class ProfileRelationshipSnapshot:
    actor_key: str
    subject_owner_key: str
    state: str
    relationship_version: str
    block_epoch: str
    blocked_either_direction: bool


class ProfileRelationshipReader(Protocol):
    def current_snapshot(self, *, actor_key: str, subject_owner_key: str) -> ProfileRelationshipSnapshot | None: ...


class ProfileRelationshipService:
    def __init__(self, reader: ProfileRelationshipReader | None):
        self._reader = reader

    def require_connection(self, *, actor_key: str, subject_owner_key: str) -> ProfileRelationshipSnapshot:
        if not (
            isinstance(actor_key, str)
            and isinstance(subject_owner_key, str)
            and _KEY.fullmatch(actor_key)
            and _KEY.fullmatch(subject_owner_key)
        ):
            raise ProfileNotFound("Profile unavailable.")
        if self._reader is None:
            raise ProfileUnavailableError("Connections dependency unavailable.")
        try:
            value = self._reader.current_snapshot(actor_key=actor_key, subject_owner_key=subject_owner_key)
        except Exception as error:
            raise ProfileUnavailableError("Connections dependency unavailable.") from error
        if not isinstance(value, ProfileRelationshipSnapshot) or not all(
            isinstance(item, str)
            for item in (
                value.actor_key,
                value.subject_owner_key,
                value.state,
                value.relationship_version,
                value.block_epoch,
            )
        ) or not isinstance(value.blocked_either_direction, bool) or not (
            _KEY.fullmatch(value.actor_key)
            and _KEY.fullmatch(value.subject_owner_key)
            and _KEY.fullmatch(value.relationship_version)
            and _KEY.fullmatch(value.block_epoch)
            and hmac.compare_digest(value.actor_key, actor_key)
            and hmac.compare_digest(value.subject_owner_key, subject_owner_key)
            and value.state == "connected"
            and value.blocked_either_direction is False
        ):
            raise ProfileNotFound("Profile unavailable.")
        return value
