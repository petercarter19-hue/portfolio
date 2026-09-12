"""Entrance-specific intake policy for MVP1 increment C.

The C composer, document parser seam and transcription adapter are shared
between Settings > My Data and Resume onboarding. Their *policies* are not
shared: My Data's accepted limits were selected by the owner, and Resume
onboarding's limits, retention and source-cleanup promises have NOT been
selected for onboarding.

This module therefore keeps the boundary explicit and parametric:

* :data:`MY_DATA_POLICY` is the already accepted My Data contract.
* :data:`FIXTURE_RESUME_ONBOARDING_POLICY` is clearly labelled synthetic fixture
  policy. It reuses My Data's numbers so code and tests have something
  concrete to run against, and it is ``selected=False`` so nothing may treat
  those numbers as an onboarding promise.
* :data:`SELECTED_RESUME_ONBOARDING_POLICY` is ``None`` until the owner decides.

Operational enablement is fail-closed and default-off. Two independent gates
exist: the feature flag (nothing runs at all when it is off) and the
fixture-policy flag (the unselected onboarding policy refuses to be silently
substituted by fixture numbers). Durable persistence additionally requires a
selected policy and a live store; the in-memory store is test-only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from services.my_opportunities.member_import_service import (
    MemberImportLimits,
    _DOCX_CONTENT_TYPE,
)


ENTRANCE_RESUME_ONBOARDING = "resume_onboarding"
ENTRANCE_MY_DATA = "my_data"
INTAKE_ENTRANCES = frozenset({ENTRANCE_RESUME_ONBOARDING, ENTRANCE_MY_DATA})

POLICY_VERSION = 1

# The owner-selected My Data Contract (accepted, unchanged by increment C).
MY_DATA_LIMITS = {
    "allowed_document_types": (
        "application/pdf",
        _DOCX_CONTENT_TYPE,
        "text/plain",
    ),
    "max_document_bytes": 10_000_000,
    # Audio has its own bound. Reusing the document ceiling silently coupled
    # two unrelated technical limits.
    "max_recording_bytes": 20 * 1024 * 1024,
    "max_documents_per_submission": 5,
    "max_text_units": 20_000,
    "max_recordings_per_draft": 3,
    "max_recording_seconds": 180.0,
    "cleanup_audio_after_transcription": True,
    "source_inspection": True,
    "source_deletion": True,
    "draft_inactivity_days": 30,
}

_UNSELECTED_ONBOARDING_DECISION = (
    "Resume onboarding file/voice limits and retention are not selected. "
    "Nothing here may be presented as an onboarding promise."
)


@dataclass(frozen=True)
class IntakePolicy:
    """One entrance's intake limits and retention promises."""

    entrance: str
    label: str
    version: int
    selected: bool
    fixture: bool
    allowed_document_types: tuple[str, ...]
    max_document_bytes: int
    max_recording_bytes: int
    max_documents_per_submission: int
    max_text_units: int
    max_recordings_per_draft: int
    max_recording_seconds: float
    cleanup_audio_after_transcription: bool
    source_inspection: bool
    source_deletion: bool
    draft_inactivity_days: int | None
    retention_statement: str
    pending_decision: str | None = None

    @property
    def fixture_only(self) -> bool:
        return self.fixture or not self.selected

    @property
    def durable_persistence_allowed(self) -> bool:
        """Durable persistence needs a *selected* policy. Fixtures never qualify."""

        return bool(self.selected and not self.fixture)

    def as_document(self) -> dict[str, Any]:
        """Serializable description for API consumers and tests."""

        return {
            "entrance": self.entrance,
            "label": self.label,
            "version": self.version,
            "selected": self.selected,
            "fixture": self.fixture,
            "durable_persistence_allowed": self.durable_persistence_allowed,
            "allowed_document_types": list(self.allowed_document_types),
            "max_document_bytes": self.max_document_bytes,
            "max_recording_bytes": self.max_recording_bytes,
            "max_documents_per_submission": self.max_documents_per_submission,
            "max_text_units": self.max_text_units,
            "max_recordings_per_draft": self.max_recordings_per_draft,
            "max_recording_seconds": self.max_recording_seconds,
            "cleanup_audio_after_transcription": self.cleanup_audio_after_transcription,
            "source_inspection": self.source_inspection,
            "source_deletion": self.source_deletion,
            "draft_inactivity_days": self.draft_inactivity_days,
            "retention_statement": self.retention_statement,
            "pending_decision": self.pending_decision,
        }

    def import_limits(self) -> MemberImportLimits:
        """Bounds for the shared document-only parse seam."""

        return MemberImportLimits(
            max_paste_units=self.max_text_units,
            max_extracted_units=self.max_text_units,
            max_upload_bytes=self.max_document_bytes,
        )


MY_DATA_POLICY = IntakePolicy(
    entrance=ENTRANCE_MY_DATA,
    label="My Data (selected)",
    version=POLICY_VERSION,
    selected=True,
    fixture=False,
    retention_statement=(
        "Drafts expire after 30 days of inactivity; originals are privately "
        "inspectable and deletable; audio is removed after transcription."
    ),
    **MY_DATA_LIMITS,
)

FIXTURE_RESUME_ONBOARDING_POLICY = IntakePolicy(
    entrance=ENTRANCE_RESUME_ONBOARDING,
    label="Resume onboarding (SYNTHETIC FIXTURE - NOT SELECTED)",
    version=POLICY_VERSION,
    selected=False,
    fixture=True,
    retention_statement=(
        "SYNTHETIC FIXTURE ONLY. These are not Resume onboarding promises; "
        "durable onboarding storage stays withheld until the owner selects "
        "the real limits and retention."
    ),
    pending_decision=_UNSELECTED_ONBOARDING_DECISION,
    **MY_DATA_LIMITS,
)

# The owner has not selected Resume onboarding policy. None means "unselected".
SELECTED_RESUME_ONBOARDING_POLICY: IntakePolicy | None = None

RECOMMENDED_ONBOARDING_DECISION = {
    "decision": "Select Resume onboarding file, voice and retention promises.",
    "recommendation": (
        "Adopt the same selectable-text PDF/DOCX/TXT ceiling (10,000,000 bytes "
        "each), English recordings up to three minutes with additional "
        "recordings in one draft, 30-day inactive-draft expiry, private source "
        "inspection and deletion, and post-transcription audio cleanup - the "
        "My Data contract - and state them in the onboarding UI before durable "
        "enablement."
    ),
    "why_it_matters": (
        "The composer must not promise recovery, retention or inspection it "
        "cannot honour. Until this is selected, onboarding persistence stays "
        "disabled and only the labelled synthetic fixture policy runs."
    ),
}


class IntakePolicyError(RuntimeError):
    """The requested entrance has no usable policy."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def resolve_policy(entrance: object) -> IntakePolicy:
    """Return the policy for one entrance, or fail closed."""

    if entrance == ENTRANCE_MY_DATA:
        return MY_DATA_POLICY
    if entrance == ENTRANCE_RESUME_ONBOARDING:
        if SELECTED_RESUME_ONBOARDING_POLICY is not None:
            return SELECTED_RESUME_ONBOARDING_POLICY
        return FIXTURE_RESUME_ONBOARDING_POLICY
    raise IntakePolicyError("unknown_entrance")


def policy_for_document(entrance: object) -> IntakePolicy:
    """Backwards-compatible alias used by the document adapter."""

    return resolve_policy(entrance)


def fixture_policy_for_tests(**overrides: Any) -> IntakePolicy:
    """A labelled fixture policy with deterministic overrides for tests."""

    return replace(FIXTURE_RESUME_ONBOARDING_POLICY, **overrides)


def sweep_parameters(policy: IntakePolicy) -> dict[str, Any]:
    """Entrance-specific retention sweep parameters, or an explicit refusal.

    Retention cleanup is scheduled only for an entrance whose policy the owner
    has actually selected. Resume onboarding's unselected (fixture) policy
    yields ``scheduled: False``, so no universal timed sweep can silently
    become an onboarding retention promise.
    """

    if not policy.durable_persistence_allowed or policy.draft_inactivity_days is None:
        return {
            "scheduled": False,
            "entrance": policy.entrance,
            "inactivity_days": None,
            "reason": "policy_not_selected",
        }
    return {
        "scheduled": True,
        "entrance": policy.entrance,
        "inactivity_days": policy.draft_inactivity_days,
        "reason": "policy_selected",
    }


def selected_policy_for_tests(**overrides: Any) -> IntakePolicy:
    """A *selected* policy for tests that need durable-eligible behaviour.

    This never mutates :data:`SELECTED_RESUME_ONBOARDING_POLICY`; callers must
    inject it explicitly, so a test cannot accidentally enable onboarding in
    the running application.
    """

    selected = replace(
        FIXTURE_RESUME_ONBOARDING_POLICY,
        label="Resume onboarding (test-selected)",
        selected=True,
        fixture=False,
        retention_statement="Test-selected policy. Not an owner decision.",
        pending_decision=None,
    )
    return replace(selected, **overrides) if overrides else selected
