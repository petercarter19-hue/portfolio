"""Narrow MVP1 consumption of Profile's approved immutable identity.

Profile remains canonical. A Resume stores only a versioned reference, and a
later Profile publication can suppress that reference but never replace it.
This service validates the existing Profile records; SQL publication also
checks the selected reference within the Resume transaction.
"""

from services.profile_core_service import (
    ProfileCoreService, ProfilePublicationRevision, ProfileUnavailableError,
    PROFILE_PUBLICATION_ACTION_PUBLISH,
)
from services.resume_publication_contracts import (
    ContractError, ProfileIdentityReference, ReadState, TrustedUseContext, UseAudience, UsePurpose,
)


class Mvp1ProfileBinding:
    def __init__(self, store):
        self.store = store
        self.core = ProfileCoreService(store)

    def _approved(self, owner):
        raw = self.store.current_publication(owner)
        if raw is None:
            return None
        if type(raw) is not ProfilePublicationRevision:
            raise ProfileUnavailableError("Profile identity is unavailable.")
        current = self.core._valid_current_publication(raw, owner_key=owner, slug=raw.slug)
        if current is None or self.store.profile_for_slug(current.slug) != owner:
            raise ProfileUnavailableError("Profile identity is unavailable.")
        if current.action != PROFILE_PUBLICATION_ACTION_PUBLISH or current.identity is None:
            return None
        return current

    @staticmethod
    def _reference(current):
        return ProfileIdentityReference(
            current.owner_key, current.slug, current.revision_key,
            current.revision_number, current.digest,
        )

    def select_for_owner(self, owner):
        """Owner review may select the current approval; no implicit publication."""
        current = self._approved(owner)
        return self._reference(current) if current is not None else None

    def resolve(self, owner, reference):
        """Disclosure is neutral on absence, change, foreign data or failure."""
        if type(reference) is not ProfileIdentityReference or reference.owner_key != owner:
            return None
        try:
            current = self._approved(owner)
            if current is None or self._reference(current) != reference:
                return None
            return current.identity
        except Exception:
            # No authentication or slug-derived identity fallback.
            return None

    def recheck(self, owner, reference):
        return ReadState.CURRENT if self.resolve(owner, reference) is not None else ReadState.DENIED


def identity_reference(value):
    """Parse durable or HTTP data without accepting open identity dictionaries."""
    if value is None:
        return None
    try:
        return ProfileIdentityReference.from_payload(value)
    except (TypeError, ValueError, ContractError):
        raise ContractError("Invalid Profile identity selection.") from None


class PinnedResumeNamePort:
    """Name consumption for the exact guest Resume subject and current pin."""

    def __init__(self, binding, publication_repository):
        self.binding = binding
        self.publications = publication_repository

    def read_approved(self, context):
        from services.member_visitor_ai_service import ApprovedMemberName
        import hashlib
        import json

        if (type(context) is not TrustedUseContext
                or context.audience is not UseAudience.GUEST
                or context.purpose is not UsePurpose.VISITOR_AI
                or context.resume_key != "resume:" + context.subject_key):
            return None
        try:
            snapshot = self.publications.load_owner(context.subject_key)
            if snapshot.get("sharing_enabled") is not True or snapshot.get("current_revision") is None:
                return None
            current = snapshot["publications"].get(snapshot["current_revision"])
            reference = identity_reference(current.get("profile_identity")) if current else None
            identity = self.binding.resolve(context.subject_key, reference)
            if identity is None:
                return None
            version = hashlib.sha256(json.dumps({
                "resume_revision": snapshot["current_revision"],
                "sharing_epoch": snapshot["sharing_epoch"],
                "reference": reference.to_payload(),
            }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            return ApprovedMemberName(context.subject_key, UsePurpose.VISITOR_AI, identity.display_name, version)
        except Exception:
            return None

    def recheck(self, context, name):
        current = self.read_approved(context)
        return ReadState.CURRENT if current is not None and current == name else ReadState.DENIED
