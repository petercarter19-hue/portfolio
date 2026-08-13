"""Unregistered PS-CONNECT-002 relationship-foundation contracts.

This module owns no route, request header, or application registration.  A
future caller must first resolve :class:`identity.PeerSlateIdentity` through
the existing trusted identity boundary, then pass that identity here.  The
foundation deliberately exposes only pair-scoped commands and one exact
audience snapshot; it never lists members, searches relationships, or accepts
a caller-provided actor key.

The SQL repository is injected.  That keeps this non-production provider
unregistered until a later, separately authorized integration can add its
stored procedures to the shared database allowlist and wire Profile's adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
import hmac
import re
from typing import Protocol

from identity import PeerSlateIdentity


_USER_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_REQUEST_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RELATIONSHIP_VERSION_TOKEN = re.compile(r"^rel_[0-9]{20}$")
_BLOCK_EPOCH_TOKEN = re.compile(r"^blk_[0-9]{20}$")

CONNECTION_COMMANDS = frozenset(
    {
        "request",
        "accept",
        "decline",
        "cancel",
        "expire",
        "disconnect",
        "block",
        "unblock",
        "reconnect",
    }
)

CONNECTION_SNAPSHOT_STATES = frozenset(
    {
        "none",
        "outbound_pending",
        "inbound_pending",
        "connected",
        "declined",
        "cancelled",
        "expired",
        "disconnected",
        "blocked",
    }
)


class ConnectionFoundationError(RuntimeError):
    """Stable, caller-safe failure for the unregistered foundation."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


class ConnectionFoundationUnavailableError(ConnectionFoundationError):
    def __init__(self) -> None:
        super().__init__("Connections are unavailable.", code="unavailable")


class ConnectionFoundationConflictError(ConnectionFoundationError):
    def __init__(self) -> None:
        super().__init__("The relationship changed. Refresh and try again.", code="changed")


class ConnectionFoundationNotFoundError(ConnectionFoundationError):
    def __init__(self) -> None:
        super().__init__("Connection unavailable.", code="not_found")


class ConnectionFoundationAuthorizationError(ConnectionFoundationError):
    def __init__(self) -> None:
        super().__init__("Connection action unavailable.", code="no_identity")


class ConnectionFoundationValidationError(ConnectionFoundationError):
    def __init__(self) -> None:
        super().__init__("Invalid connection command.", code="invalid")


@dataclass(frozen=True)
class ConnectionActor:
    """A narrow copy of a previously validated server identity.

    It is created only by :func:`actor_from_server_identity`; command callers
    receive no API that takes an actor key as an untrusted request value.
    """

    user_key: str
    auth_provider: str
    auth_issuer: str
    auth_subject: str


@dataclass(frozen=True)
class ConnectionCommand:
    """One explicit relationship mutation with deterministic replay fencing."""

    command: str
    idempotency_key: str
    request_digest: str
    expected_relationship_version: str | None


@dataclass(frozen=True)
class ConnectionAudienceSnapshot:
    """The exact pair-scoped value a later Profile adapter can consume.

    ``blocked_either_direction`` is redundant with ``state == 'blocked'`` on
    purpose.  The redundant flag makes it hard for a downstream adapter to
    accidentally treat a stale connected state as eligible after a block.
    """

    actor_key: str
    subject_owner_key: str
    state: str
    relationship_version: str
    block_epoch: str
    blocked_either_direction: bool


@dataclass(frozen=True)
class ConnectionCommandResult:
    """The immutable stored result for a command/idempotency-key pair."""

    command_key: str
    actor_key: str
    subject_owner_key: str
    command: str
    idempotency_key: str
    request_digest: str
    snapshot: ConnectionAudienceSnapshot


class ConnectionFoundationStore(Protocol):
    def commit(
        self,
        *,
        actor_user_key: str,
        subject_user_key: str,
        command: ConnectionCommand,
    ) -> ConnectionCommandResult: ...

    def current_audience_snapshot(
        self, *, actor_user_key: str, subject_user_key: str
    ) -> ConnectionAudienceSnapshot | None: ...

    def command_for(
        self, *, actor_user_key: str, idempotency_key: str
    ) -> ConnectionCommandResult | None: ...


def _valid_key(value: object) -> bool:
    return isinstance(value, str) and _USER_KEY.fullmatch(value) is not None


def _require_subject_key(value: object) -> str:
    if not _valid_key(value):
        raise ConnectionFoundationNotFoundError()
    return value


def validate_connection_actor_key(value: object) -> str:
    """Validate an already server-derived key at an injected provider boundary.

    This is deliberately separate from :func:`actor_from_server_identity` so a
    repository can fail closed when it is exercised directly in a unit test or
    later injected service. It is *not* a public request-identity API.
    """

    if not _valid_key(value):
        raise ConnectionFoundationNotFoundError()
    return value


def validate_connection_parties(
    actor_user_key: object, subject_user_key: object
) -> tuple[str, str]:
    """Require two distinct opaque member keys without revealing which failed."""

    actor = validate_connection_actor_key(actor_user_key)
    subject = _require_subject_key(subject_user_key)
    if hmac.compare_digest(actor, subject):
        raise ConnectionFoundationNotFoundError()
    return actor, subject


def validate_connection_idempotency_key(value: object) -> str:
    """Validate an opaque replay key without normalizing its exact bytes."""

    if not isinstance(value, str) or _IDEMPOTENCY_KEY.fullmatch(value) is None:
        raise ConnectionFoundationValidationError()
    return value


def actor_from_server_identity(identity: object) -> ConnectionActor:
    """Make an actor only from the repository's trusted identity type.

    A structurally similar object is deliberately not accepted.  That prevents
    a future route from accidentally treating browser-provided fields as a
    server-derived member identity.
    """

    if not isinstance(identity, PeerSlateIdentity) or not all(
        isinstance(value, str) and value.strip()
        for value in (
            identity.user_key,
            identity.auth_provider,
            identity.auth_issuer,
            identity.auth_subject,
        )
    ) or not _valid_key(identity.user_key):
        raise ConnectionFoundationAuthorizationError()
    return ConnectionActor(
        user_key=identity.user_key,
        auth_provider=identity.auth_provider,
        auth_issuer=identity.auth_issuer,
        auth_subject=identity.auth_subject,
    )


def validate_connection_command(command: object) -> ConnectionCommand:
    if not isinstance(command, ConnectionCommand):
        raise ConnectionFoundationValidationError()
    if (
        command.command not in CONNECTION_COMMANDS
        or not isinstance(command.idempotency_key, str)
        or _IDEMPOTENCY_KEY.fullmatch(command.idempotency_key) is None
        or not isinstance(command.request_digest, str)
        or _REQUEST_DIGEST.fullmatch(command.request_digest) is None
    ):
        raise ConnectionFoundationValidationError()
    expected = command.expected_relationship_version
    if expected is not None and (
        not isinstance(expected, str)
        or _RELATIONSHIP_VERSION_TOKEN.fullmatch(expected) is None
    ):
        raise ConnectionFoundationValidationError()
    # An initial block is intentional and may create a relationship fence
    # before the members have ever requested a connection. Every other
    # lifecycle transition is compare-and-swap fenced by relationship version.
    if command.command not in {"request", "block"} and expected is None:
        raise ConnectionFoundationValidationError()
    return command


def validate_connection_snapshot(
    snapshot: object, *, actor_key: str, subject_owner_key: str
) -> ConnectionAudienceSnapshot:
    if not isinstance(snapshot, ConnectionAudienceSnapshot) or not all(
        isinstance(value, str)
        for value in (
            snapshot.actor_key,
            snapshot.subject_owner_key,
            snapshot.state,
            snapshot.relationship_version,
            snapshot.block_epoch,
        )
    ) or not isinstance(snapshot.blocked_either_direction, bool):
        raise ConnectionFoundationUnavailableError()
    if not (
        _valid_key(snapshot.actor_key)
        and _valid_key(snapshot.subject_owner_key)
        and _RELATIONSHIP_VERSION_TOKEN.fullmatch(snapshot.relationship_version)
        and _BLOCK_EPOCH_TOKEN.fullmatch(snapshot.block_epoch)
        and snapshot.state in CONNECTION_SNAPSHOT_STATES
        and hmac.compare_digest(snapshot.actor_key, actor_key)
        and hmac.compare_digest(snapshot.subject_owner_key, subject_owner_key)
        and (snapshot.state == "blocked") == snapshot.blocked_either_direction
    ):
        raise ConnectionFoundationNotFoundError()
    return snapshot


def validate_connection_command_result(
    result: object,
    *,
    actor_key: str,
    subject_owner_key: str,
    command: ConnectionCommand | None = None,
) -> ConnectionCommandResult:
    if not isinstance(result, ConnectionCommandResult) or not all(
        isinstance(value, str)
        for value in (
            result.command_key,
            result.actor_key,
            result.subject_owner_key,
            result.command,
            result.idempotency_key,
            result.request_digest,
        )
    ):
        raise ConnectionFoundationUnavailableError()
    if not (
        _IDEMPOTENCY_KEY.fullmatch(result.command_key)
        and _valid_key(result.actor_key)
        and _valid_key(result.subject_owner_key)
        and result.command in CONNECTION_COMMANDS
        and _IDEMPOTENCY_KEY.fullmatch(result.idempotency_key)
        and _REQUEST_DIGEST.fullmatch(result.request_digest)
        and hmac.compare_digest(result.actor_key, actor_key)
        and hmac.compare_digest(result.subject_owner_key, subject_owner_key)
    ):
        raise ConnectionFoundationNotFoundError()
    if command is not None and not (
        result.command == command.command
        and hmac.compare_digest(result.idempotency_key, command.idempotency_key)
        and hmac.compare_digest(result.request_digest, command.request_digest)
    ):
        raise ConnectionFoundationConflictError()
    validate_connection_snapshot(
        result.snapshot, actor_key=actor_key,
        **{"subject_owner_key": subject_owner_key},
    )
    return result


class ConnectionFoundationService:
    """Server-identity-first, pair-scoped façade over the SQL provider."""

    def __init__(self, store: ConnectionFoundationStore) -> None:
        self._store = store

    def execute(
        self,
        *,
        identity: PeerSlateIdentity,
        subject_user_key: str,
        command: ConnectionCommand,
    ) -> ConnectionCommandResult:
        actor = actor_from_server_identity(identity)
        _, subject = validate_connection_parties(actor.user_key, subject_user_key)
        command = validate_connection_command(command)
        try:
            result = self._store.commit(
                actor_user_key=actor.user_key,
                subject_user_key=subject,
                command=command,
            )
        except ConnectionFoundationError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error
        return validate_connection_command_result(
            result, actor_key=actor.user_key, subject_owner_key=subject, command=command
        )

    def profile_audience_snapshot(
        self, *, identity: PeerSlateIdentity, subject_user_key: str
    ) -> ConnectionAudienceSnapshot:
        """Resolve one relationship after actor derivation and before retrieval.

        The method intentionally returns the same neutral absence for an unknown
        target, unrelated actor, and a repository that reports no pair snapshot.
        """

        actor = actor_from_server_identity(identity)
        _, subject = validate_connection_parties(actor.user_key, subject_user_key)
        try:
            snapshot = self._store.current_audience_snapshot(
                actor_user_key=actor.user_key, subject_user_key=subject
            )
        except ConnectionFoundationError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error
        if snapshot is None:
            raise ConnectionFoundationNotFoundError()
        return validate_connection_snapshot(
            snapshot, actor_key=actor.user_key,
            **{"subject_owner_key": subject},
        )

    def command_result(
        self, *, identity: PeerSlateIdentity, idempotency_key: str
    ) -> ConnectionCommandResult:
        """Return only this actor's exact stored command winner, or neutral absence."""

        actor = actor_from_server_identity(identity)
        idempotency_key = validate_connection_idempotency_key(idempotency_key)
        try:
            result = self._store.command_for(**{
                "actor_user_key": actor.user_key,
                "idempotency_key": idempotency_key,
            })
        except ConnectionFoundationError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error
        if result is None:
            raise ConnectionFoundationNotFoundError()
        # A provider result is untrusted until its binding field can be read
        # and validated. Do not dereference a malformed object outside the
        # fail-closed boundary: that could leak an AttributeError rather than
        # the stable unavailable outcome expected for a provider fault.
        try:
            subject_owner_key = result.subject_owner_key
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error
        if not isinstance(subject_owner_key, str):
            raise ConnectionFoundationUnavailableError()
        try:
            return validate_connection_command_result(
                result,
                actor_key=actor.user_key,
                subject_owner_key=subject_owner_key,
            )
        except ConnectionFoundationError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error


class ConnectionFoundationProfileReader:
    """Profile-reader adapter over the same injected relationship provider.

    Profile owns the caller-facing reader protocol and already derives its
    viewer key before invoking a reader. This adapter adds no route or Profile
    registration; it only makes a valid foundation snapshot an *exact*
    ``ProfileRelationshipSnapshot`` when a later authorized composition wires
    it. Invalid, self, absent, or cross-owner snapshots collapse to ``None``
    so Profile retains its neutral not-found behavior. Provider outages remain
    outages rather than being mistaken for relationship absence.
    """

    def __init__(self, store: ConnectionFoundationStore) -> None:
        self._store = store

    def current_snapshot(
        self, *, actor_key: str, subject_owner_key: str
    ) -> object | None:
        try:
            actor, subject = validate_connection_parties(actor_key, subject_owner_key)
            snapshot = self._store.current_audience_snapshot(
                actor_user_key=actor, subject_user_key=subject
            )
            if snapshot is None:
                return None
            snapshot = validate_connection_snapshot(
                snapshot, actor_key=actor, subject_owner_key=subject
            )
        except ConnectionFoundationNotFoundError:
            return None
        except ConnectionFoundationError:
            raise
        except Exception as error:
            raise ConnectionFoundationUnavailableError() from error

        # The import is local so this unregistered foundation does not make the
        # Profile module a startup dependency. No Profile surface is modified.
        from services.profile_relationship_service import ProfileRelationshipSnapshot

        return ProfileRelationshipSnapshot(
            actor_key=snapshot.actor_key,
            subject_owner_key=snapshot.subject_owner_key,
            state=snapshot.state,
            relationship_version=snapshot.relationship_version,
            block_epoch=snapshot.block_epoch,
            blocked_either_direction=snapshot.blocked_either_direction,
        )
