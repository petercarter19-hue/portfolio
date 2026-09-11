"""Owner-scoped entry-policy API for MVP1 increment A.

REGISTERED, AND OFF.
``app.py`` registers this blueprint unconditionally. The gate is
``PEERSLATE_ENTRY_POLICY_ENABLED``, read with ``is True``. Off means a
neutral 404. Schema is not applied by this package; command execution uses
the injected in-memory/test repository or fail-closed SQL.

Identity is server-derived. Client owner ids, table names, and permission
bypass flags are ignored or refused. Responses are private, no-store.
My Data overlay UI is out of scope; these routes are the direct-control API.
"""

from __future__ import annotations

from types import MappingProxyType

from flask import Blueprint, current_app, jsonify, request

from identity import AuthenticationRequired, get_current_identity
from services.entry_policy_service import (
    EntryPolicyConflictError,
    EntryPolicyNotFoundError,
    EntryPolicyService,
    EntryPolicyUnavailableError,
    EntryPolicyValidationError,
    entry_policy_service,
)


entry_policy = Blueprint("entry_policy", __name__, url_prefix="/api/entry-policy")

PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "entry_policy.commit_entry_policy_command": "30 per hour",
        "entry_policy.list_entry_policy_entries": "60 per minute",
        "entry_policy.get_entry_policy_entry": "60 per minute",
        "entry_policy.sweep_entry_policy_expiry": "10 per hour",
    }
)


def _enabled() -> bool:
    return current_app.config.get("PEERSLATE_ENTRY_POLICY_ENABLED", False) is True


def _service() -> EntryPolicyService:
    return current_app.config.get("ENTRY_POLICY_SERVICE") or entry_policy_service


@entry_policy.before_request
def gate_and_protect_writes():
    if not _enabled():
        return jsonify({"success": False, "message": "Not found."}), 404
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return None
    if request.headers.get("X-PeerSlate-Request") != "same-origin":
        return jsonify(
            {"success": False, "message": "A same-origin request header is required."}
        ), 403
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify(
            {"success": False, "message": "Cross-origin writes are not allowed."}
        ), 403
    return None


@entry_policy.after_request
def private_no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _identity_or_not_found():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None


@entry_policy.get("/me/entries")
def list_entry_policy_entries():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().list_entries(identity.user_key)
    except EntryPolicyUnavailableError:
        return jsonify({"success": False, "message": "Entry policy is unavailable."}), 503
    return jsonify({"success": True, **result})


@entry_policy.get("/me/entries/<entry_key>")
def get_entry_policy_entry(entry_key):
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().get_entry(identity.user_key, entry_key)
    except EntryPolicyValidationError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except EntryPolicyNotFoundError:
        return jsonify({"success": False, "message": "Not found."}), 404
    except EntryPolicyUnavailableError:
        return jsonify({"success": False, "message": "Entry policy is unavailable."}), 503
    return jsonify({"success": True, **result})


@entry_policy.post("/me/commands")
def commit_entry_policy_command():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if isinstance(payload, dict):
        payload = {
            key: value
            for key, value in payload.items()
            if key not in {"owner_user_key", "user_key", "owner_profile_id"}
        }
    try:
        result = _service().commit(identity.user_key, payload)
    except EntryPolicyValidationError as error:
        return jsonify({"success": False, "message": str(error)}), 400
    except EntryPolicyNotFoundError:
        return jsonify({"success": False, "message": "Not found."}), 404
    except EntryPolicyConflictError as error:
        return jsonify(
            {
                "success": False,
                "error_code": error.error_code,
                "conflicts": error.conflicts,
                "message": str(error),
            }
        ), 409
    except EntryPolicyUnavailableError:
        return jsonify({"success": False, "message": "Entry policy is unavailable."}), 503
    return jsonify({"success": True, **result})


@entry_policy.post("/me/expiry-sweep")
def sweep_entry_policy_expiry():
    """Owner-scoped recovery-window sweep. Not a production worker host."""

    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().sweep_expired(identity.user_key)
    except EntryPolicyUnavailableError:
        return jsonify({"success": False, "message": "Entry policy is unavailable."}), 503
    return jsonify({"success": True, **result})
