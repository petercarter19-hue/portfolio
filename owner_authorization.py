"""Server-side, fail-closed *site-owner* authorization for the Control Room.

PeerSlate already authenticates members (see ``identity.py``) and gives each one
private, self-owned surfaces under ``/app`` (settings, capture). That is
per-member ownership — every signed-in member is the owner of *their own* data.

The Control Room needs something different: a single **site owner** (Pete) may
view it, and no other authenticated member may. No such distinction existed in
the application before this module.

Design:

* Identity is resolved only from the trusted authentication boundary via
  ``identity.get_optional_identity()`` — never from a client-supplied id, email,
  role, or boolean.
* Ownership is decided by comparing that server-resolved identity against an
  allowlist the operator configures in the environment
  (``PEERSLATE_OWNER_EMAILS`` and/or ``PEERSLATE_OWNER_USER_KEYS``). This module
  reads only the configured *values*; it hardcodes no personal identifier, so it
  stays generic and multi-tenant-safe.
* It is **fail-closed**: if neither allowlist is configured, *nobody* is the
  owner and every protected route behaves as if it does not exist.
* A non-owner (unauthenticated or authenticated) receives a plain ``404`` so the
  route's very existence is never confirmed. Obscurity is not the control — the
  server-side check is — but not advertising the surface is good hygiene.
"""

from __future__ import annotations

import re

from flask import abort, current_app
from werkzeug.exceptions import HTTPException
from functools import wraps

from identity import get_optional_identity
from services.database_service import DatabaseServiceError


_SPLIT = re.compile(r"[,\s;]+")


def _allowlist(config_key):
    raw = current_app.config.get(config_key) or ""
    if not isinstance(raw, str):
        return frozenset()
    return frozenset(part for part in _SPLIT.split(raw.strip()) if part)


def owner_emails():
    """Configured owner emails, casefolded for case-insensitive comparison."""
    return frozenset(email.casefold() for email in _allowlist("PEERSLATE_OWNER_EMAILS"))


def owner_user_keys():
    """Configured owner user keys (opaque; compared case-sensitively)."""
    return _allowlist("PEERSLATE_OWNER_USER_KEYS")


def owner_allowlist_configured():
    """True only when at least one owner identifier is configured."""
    return bool(owner_emails() or owner_user_keys())


def is_owner(identity):
    """Return True only for an identity that matches a configured allowlist.

    Empty allowlists → always False (fail-closed). ``None`` identity → False.
    """
    if identity is None:
        return False

    keys = owner_user_keys()
    if keys:
        user_key = getattr(identity, "user_key", None)
        if user_key and user_key in keys:
            return True

    emails = owner_emails()
    if emails:
        email = getattr(identity, "email", None)
        if email and email.strip().casefold() in emails:
            return True

    return False


def resolve_owner():
    """The current identity if (and only if) it is the site owner, else None.

    Never raises: a storage failure while resolving identity fails closed.
    """
    try:
        identity = get_optional_identity()
    except DatabaseServiceError:
        current_app.logger.error(
            "Control Room owner resolution failed on identity storage; "
            "failing closed."
        )
        return None
    return identity if is_owner(identity) else None


def owner_required(view):
    """Guard a view so only the resolved site owner may reach it.

    Anyone else — unauthenticated, authenticated non-owner, or an identity that
    cannot be resolved because storage is down — receives a bare 404, which is
    indistinguishable from a route that does not exist. This must be applied to
    every Control Room route independently, including data endpoints; protecting
    the page alone is not sufficient.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            identity = get_optional_identity()
        except DatabaseServiceError:
            current_app.logger.error(
                "Control Room access check failed on identity storage; "
                "failing closed."
            )
            abort(404)

        if not is_owner(identity):
            abort(404)

        return view(*args, **kwargs)

    return wrapped


# ``HTTPException`` is imported so callers/tests can reason about the 404 the
# decorator raises without depending on Werkzeug internals directly.
__all__ = [
    "is_owner",
    "owner_required",
    "resolve_owner",
    "owner_allowlist_configured",
    "owner_emails",
    "owner_user_keys",
    "HTTPException",
]
