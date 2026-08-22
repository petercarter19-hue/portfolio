"""Process-boot Interview release state (consolidated correction B3).

Exactly one immutable resolution per process: the application boundary
calls :func:`initialize` once at import/boot time, the configured
release set is fully re-verified there, and the outcome — ``ready``
with the verified release, or ``service_not_configured`` — is frozen.

Requests read only the frozen state. A configuration change, registry
edit, bundle edit, guarded-file change, or evaluation-manifest change
after boot cannot alter the running process; making any of those
effective requires a process restart, which re-runs the full
verification. A process whose boot never ran answers exactly like a
failed boot: fail closed, zero provider dispatch.
"""

import logging
import threading

logger = logging.getLogger(__name__)

READY = "ready"
SERVICE_NOT_CONFIGURED = "service_not_configured"

_LOCK = threading.Lock()
_STATE = None


class BootState:
    """One frozen boot outcome. Instances never mutate after creation."""

    __slots__ = ("status", "release", "configured_id")

    def __init__(self, status, release, configured_id):
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "release", release)
        object.__setattr__(self, "configured_id", configured_id)

    def __setattr__(self, name, value):
        raise AttributeError("BootState is immutable")


def initialize(configured_id, root=None):
    """Resolve and freeze the boot state; idempotent after the first call.

    The first invocation wins. Later invocations — including ones with a
    DIFFERENT configured id — return the already-frozen state untouched,
    so nothing that happens after boot can swap the running release.
    """
    global _STATE
    with _LOCK:
        if _STATE is not None:
            if _STATE.configured_id != configured_id:
                # Content-free by design: ids are public identity hashes.
                logger.warning(
                    "interview boot state is frozen; ignoring a post-boot "
                    "configuration change"
                )
            return _STATE
        from services.interview_ai import release as release_module
        resolved = None
        if configured_id:
            resolved = release_module._resolve_uncached(
                configured_id, root or release_module.ROOT
            )
        _STATE = BootState(
            READY if resolved is not None else SERVICE_NOT_CONFIGURED,
            resolved,
            configured_id,
        )
        logger.info("interview boot state frozen: %s", _STATE.status)
        return _STATE


def state():
    """The frozen boot state, or None when boot never ran (fail closed)."""
    return _STATE


def reset_for_tests():
    """Test hook simulating a process restart. Never called at runtime."""
    global _STATE
    with _LOCK:
        _STATE = None
