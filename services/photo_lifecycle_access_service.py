"""Fail-closed server policy for bounded Photo lifecycle proof access.

The policy never accepts browser identity, email, source keys, or UI state as
authorization. It evaluates only server configuration and the internal
``PeerSlateIdentity.user_key`` resolved by the existing authentication layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import os
import re
import threading

from flask import current_app


PHOTO_ACCESS_OFF = "off"
PHOTO_ACCESS_ORDINARY = "ordinary"
PHOTO_ACCESS_PROOF = "proof"
PHOTO_ACCESS_INVALID = "invalid"
MAX_PROOF_WINDOW = timedelta(hours=2)
PROOF_USER_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
PROOF_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_VALUES = frozenset({"", "0", "false", "no", "off"})

# The only two fields that may ever reach a log record. The format string is a
# module constant so the audit evidence and its tests cannot drift apart.
PROOF_ADMISSION_LOG_FORMAT = (
    "PeerSlate Photo lifecycle proof admission. access_mode=%s run_id=%s"
)
PROOF_ADMISSION_UNSET_RUN_ID = "unset"


@dataclass(frozen=True)
class PhotoLifecycleConfiguration:
    """A privacy-safe access decision input.

    Values remain server-side and this object must never be serialized into a
    response, log record, screenshot, or evidence artifact.

    One narrow exception exists and is enumerated here so it cannot widen by
    accident: ``PhotoLifecycleAccessService._announce_proof_window`` writes
    ``mode`` and ``run_id`` to the application log. ``cohort_user_keys``,
    ``expires_at_utc``, the admitted user key, and the object itself are never
    written anywhere.
    """

    mode: str
    cohort_user_keys: frozenset[str] = field(default_factory=frozenset)
    expires_at_utc: datetime | None = None
    run_id: str | None = None


class PhotoLifecycleAccessService:
    """Resolve ordinary release or an expiring two-owner proof cohort."""

    def __init__(self):
        # Windows already announced by this process. The fingerprint holds the
        # mode, the nonsecret run label, and the expiry instant so a second
        # approved window can never be silently attributed to the first. It
        # deliberately excludes the cohort keys, so no identity material is
        # retained by the audit path.
        self._announced_proof_windows = set()
        self._announcement_lock = threading.Lock()

    def reset_audit_state(self):
        """Forget which proof windows this process has already announced."""

        with self._announcement_lock:
            self._announced_proof_windows.clear()

    @staticmethod
    def _setting(name, default=""):
        configured = current_app.config.get(name)
        if configured is not None:
            return configured
        return os.getenv(name, default)

    @staticmethod
    def _boolean(value):
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().casefold()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        return None

    @staticmethod
    def _cohort(value):
        if not isinstance(value, str):
            return None
        keys = [item for item in re.split(r"[\s,]+", value.strip()) if item]
        if len(keys) != 2 or len(set(keys)) != 2:
            return None
        if any(not PROOF_USER_KEY.fullmatch(key) or "@" in key for key in keys):
            return None
        return frozenset(keys)

    @staticmethod
    def _expiry(value):
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            return None
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _now_utc(now):
        if now is None:
            return datetime.now(timezone.utc)
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)

    def configuration(self, now=None):
        """Return one fail-closed mode without exposing configured values."""

        ordinary_enabled = self._boolean(
            self._setting("CAPTURE_PHOTO_ENABLED", "false")
        )
        proof_enabled = self._boolean(
            self._setting("CAPTURE_PHOTO_LIFECYCLE_PROOF_ENABLED", "false")
        )
        if ordinary_enabled is None or proof_enabled is None:
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_INVALID)
        if ordinary_enabled and proof_enabled:
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_INVALID)
        if ordinary_enabled:
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_ORDINARY)
        if not proof_enabled:
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_OFF)

        cohort = self._cohort(
            self._setting("CAPTURE_PHOTO_LIFECYCLE_PROOF_USER_KEYS", "")
        )
        expiry = self._expiry(
            self._setting("CAPTURE_PHOTO_LIFECYCLE_PROOF_EXPIRES_AT_UTC", "")
        )
        raw_run_id = self._setting("CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID", "")
        run_id = str(raw_run_id or "").strip()
        if run_id and not PROOF_RUN_ID.fullmatch(run_id):
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_INVALID)

        now_utc = self._now_utc(now)
        if (
            cohort is None
            or expiry is None
            or expiry <= now_utc
            or expiry > now_utc + MAX_PROOF_WINDOW
        ):
            return PhotoLifecycleConfiguration(PHOTO_ACCESS_INVALID)

        return PhotoLifecycleConfiguration(
            PHOTO_ACCESS_PROOF,
            cohort_user_keys=cohort,
            expires_at_utc=expiry,
            run_id=run_id or None,
        )

    def _announce_proof_window(self, configuration):
        """Record once that a proof window actually admitted a cohort request.

        Only ``mode`` and the nonsecret ``run_id`` are written. The admitted
        user key, the cohort, the expiry, and the configuration object itself
        are never serialized into the log record.

        The record is emitted at warning level because proof mode is a
        deliberate, temporary bypass of the ordinary release flag in
        production, and because this application configures no logging
        handlers or levels of its own; an info-level record would be dropped
        by the default level and would leave exactly the silent evidence gap
        this audit closes.
        """

        fingerprint = (
            configuration.mode,
            configuration.run_id,
            configuration.expires_at_utc,
        )
        with self._announcement_lock:
            if fingerprint in self._announced_proof_windows:
                return False
            self._announced_proof_windows.add(fingerprint)
        current_app.logger.warning(
            PROOF_ADMISSION_LOG_FORMAT,
            configuration.mode,
            configuration.run_id or PROOF_ADMISSION_UNSET_RUN_ID,
        )
        return True

    def allows_identity(self, identity, configuration):
        """Authorize only the trusted server-resolved identity for this mode."""

        if configuration.mode not in {PHOTO_ACCESS_ORDINARY, PHOTO_ACCESS_PROOF}:
            return False
        user_key = getattr(identity, "user_key", None)
        if not isinstance(user_key, str) or not user_key.strip():
            return False
        if configuration.mode == PHOTO_ACCESS_ORDINARY:
            return True
        if user_key not in configuration.cohort_user_keys:
            return False
        self._announce_proof_window(configuration)
        return True


photo_lifecycle_access_service = PhotoLifecycleAccessService()


__all__ = [
    "MAX_PROOF_WINDOW",
    "PHOTO_ACCESS_INVALID",
    "PHOTO_ACCESS_OFF",
    "PHOTO_ACCESS_ORDINARY",
    "PHOTO_ACCESS_PROOF",
    "PROOF_ADMISSION_LOG_FORMAT",
    "PROOF_ADMISSION_UNSET_RUN_ID",
    "PhotoLifecycleAccessService",
    "PhotoLifecycleConfiguration",
    "photo_lifecycle_access_service",
]
