"""Pure E review. Separate reads are not an atomic publication transaction.

The later transaction owner must compare digest AND every dependency again
under its consistency boundary. A successful result cannot authorize a read,
write, permission expansion, publication, or citation by itself.
"""

import hashlib
import json

from services.ai_foundation.contracts import Audience, Purpose
from services.resume_media_repository import (
    CatalogAssetRecord, MAX_PROVENANCE_LABEL_LENGTH, assert_no_catalog_claim,
    normalize_alt_text, normalize_caption, provenance_label_for, validate_crop_geometry,
)
from services.resume_publication_contracts import (
    CandidateInput, ContractError, DisplayManifest, EntryState, ManifestEntry,
    MediaReadPort, MediaSnapshot, MediaState, MediaVersion, PolicyReadPort, PolicySnapshot,
    ReadState, ReviewedCandidate, SourceState, UseAudience, UsePurpose,
    ValidationResult, VersionTuple, VisitorAIManifest, Wording, members, unique,
)


def _entry(ref):
    return {"subject_key": ref.subject_key, "entry_key": ref.entry_key,
            "content_revision": ref.content_revision, "access_revision": ref.access_revision}


def _source(ref):
    return {"entry": _entry(ref.entry), "source_key": ref.source_key,
            "source_version_key": ref.source_version_key, "version": ref.version,
            "content_sha256": ref.content_sha256}


def _media(ref):
    return {"subject_key": ref.subject_key, "slot": ref.slot,
            "placement_version": ref.placement_version, "source_kind": ref.source_kind,
            "source_key": ref.source_key, "source_revision": ref.source_revision,
            "asset_version": ref.asset_version, "catalog_revision": ref.catalog_revision,
            "content_sha256": ref.content_sha256, "readiness_sha256": ref.readiness_sha256}


def _placement(item):
    # Numeric crop equivalents serialize equally; negative zero is zero.
    def number(value):
        return float(value) if value else 0.0
    return {"slot": item.slot, "source_kind": item.source_kind, "asset_id": item.asset_id,
            "asset_version": item.asset_version, "asset_digest": item.asset_digest,
            "presentation_version": item.presentation_version,
            "crop": {"x": number(item.crop.x), "y": number(item.crop.y),
                     "width": number(item.crop.width), "height": number(item.crop.height)},
            "alt_text": item.alt_text, "decorative": item.decorative,
            "provenance_label": item.provenance_label, "caption": item.caption}


def _wording(values):
    return [{"field": item.field, "value": item.value} for item in values]


def _canonical_payload(candidate, policy, media):
    """Fixed schema, explicit nulls; no generic object/reflection serializer."""
    versions = candidate.prior
    context = candidate.context
    return {
        "schema": "resume-publication-review.v1",
        "context": {"subject_key": context.subject_key, "resume_key": context.resume_key,
                    "audience": context.audience.value, "purpose": context.purpose.value,
                    "authenticated_owner_key": context.authenticated_owner_key},
        "versions": {
            "schema_version": versions.schema_version,
            "subject_key": versions.subject_key, "resume_key": versions.resume_key,
            "draft_revision": versions.draft_revision,
            "publication_revision": versions.publication_revision,
            "sharing_epoch": versions.sharing_epoch,
            "entries": [_entry(x) for x in versions.entries],
            "sources": [_source(x) for x in versions.sources],
            "media": [_media(x) for x in versions.media],
        },
        "selections": [{
            "entry": _entry(x.entry), "display": x.display, "visitor_ai": x.visitor_ai,
            "expand_display": x.expand_display, "expand_visitor_ai": x.expand_visitor_ai,
            "deltas": [{"field": d.field, "before": d.before, "after": d.after}
                       for d in x.deltas],
        } for x in candidate.selections],
        "placements": [_placement(x) for x in candidate.placements],
        "policy": {
            "state": policy.state.value, "sharing_enabled": policy.sharing_enabled,
            "entries": [{"ref": _entry(x.ref), "wording": _wording(x.wording),
                         "display_allowed": x.display_allowed,
                         "visitor_ai_allowed": x.visitor_ai_allowed,
                         "active": x.active, "identity_resolved": x.identity_resolved}
                        for x in sorted(policy.entries, key=lambda x: x.ref)],
            "sources": [{"ref": _source(x.ref), "title": x.source.title,
                         "content": x.source.content,
                         "audiences": sorted(a.value for a in x.source.allowed_audiences),
                         "purposes": sorted(p.value for p in x.source.allowed_purposes),
                         "saved": x.saved, "approved": x.approved,
                         "active": x.active, "canonical_evidence": x.canonical_evidence}
                        for x in sorted(policy.sources, key=lambda x: x.ref)],
        },
        "media_read": {"state": media.state.value,
                       "media": [{"ref": _media(x.ref), "width": x.width, "height": x.height,
                                  "ready": x.ready, "active": x.active,
                                  "presentation_evidence": _presentation_evidence(x)}
                                 for x in sorted(media.media, key=lambda x: x.ref)]},
    }


def _presentation_evidence(current):
    record = current.catalog
    return {
        "provenance_label": provenance_label_for(source_kind=current.ref.source_kind, record=record),
        "catalog_label": record.label if record is not None else None,
        "catalog_tags": sorted(record.tags) if record is not None else None,
    }


def _check_presentation(placement, current):
    """Preserve media producer semantics without changing reviewed wording."""
    record = current.catalog
    if placement.source_kind == "generated_illustration":
        if type(record) is not CatalogAssetRecord:
            return "missing_catalog_evidence"
        if (record.asset_id != current.ref.source_key or record.version != current.ref.asset_version
                or record.digest != current.ref.content_sha256 or record.width != current.width
                or record.height != current.height or record.origin != placement.source_kind
                or record.lifecycle != "active"):
            return "catalog_evidence_changed"
        if (type(record.tags) is not tuple or any(type(x) is not str for x in record.tags)
                or type(record.label) is not str or type(record.provenance) is not tuple):
            return "malformed_catalog_evidence"
        # Existing catalog records freeze metadata. Reject mutable/ambiguous
        # pairs before deriving a label; only the existing allowlist is used.
        keys = []
        for pair in record.provenance:
            if (type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str
                    or type(pair[1]) not in (str, int, float, bool)):
                return "malformed_catalog_evidence"
            keys.append(pair[0])
        if len(keys) != len(set(keys)):
            return "malformed_catalog_evidence"
    elif record is not None:
        return "unexpected_catalog_evidence"
    if (normalize_alt_text(placement.alt_text) != placement.alt_text
            or normalize_caption(placement.caption) != placement.caption):
        return "unnormalized_presentation_text"
    label = provenance_label_for(source_kind=placement.source_kind, record=record)
    if (placement.provenance_label != label or len(label) > MAX_PROVENANCE_LABEL_LENGTH
            or not label or any(ord(ch) < 32 and ch != "\t" for ch in label)):
        return "invalid_provenance"
    if record is not None:
        assert_no_catalog_claim(alt_text=placement.alt_text, caption=placement.caption, record=record)
    return None


def _failure(state, reason):
    return ValidationResult(state, reason)


def validate_candidate(candidate: CandidateInput, policy_port: PolicyReadPort,
                       media_port: MediaReadPort) -> ValidationResult:
    """Read-only validation, fail closed on malformed/unavailable authorities.

    Ports must supply authoritative complete version dependencies. No default
    adapters and no fallback to the private editor catalog are provided.
    """
    if type(candidate) is not CandidateInput:
        return _failure(ReadState.DENIED, "malformed_candidate")
    context, prior = candidate.context, candidate.prior
    if (context.subject_key, context.resume_key) != (prior.subject_key, prior.resume_key):
        return _failure(ReadState.DENIED, "foreign_context")
    if context.audience is not UseAudience.OWNER_PREVIEW or context.purpose not in {
        UsePurpose.PUBLICATION_REVIEW, UsePurpose.OWNER_PREVIEW,
    }:
        return _failure(ReadState.DENIED, "owner_review_required")
    if prior.draft_revision is None:
        return _failure(ReadState.UNAVAILABLE, "missing_draft_revision")
    if any(x.entry not in prior.entries for x in candidate.selections):
        return _failure(ReadState.STALE, "selection_version_mismatch")
    try:
        policy = policy_port.read_current(context, prior.entries)
        media = media_port.read_current(context, candidate.placements)
    except Exception:
        # Do not expose adapter messages (which may contain member material).
        return _failure(ReadState.UNAVAILABLE, "authority_read_failed")
    try:
        return _validate_snapshots(candidate, policy, media)
    except (ValueError, TypeError, AttributeError, KeyError):
        return _failure(ReadState.UNAVAILABLE, "malformed_authority")


def _validate_snapshots(candidate, policy, media):
    prior = candidate.prior
    if type(policy) is not PolicySnapshot or type(media) is not MediaSnapshot:
        raise ContractError("typed snapshots required")
    for snapshot in (policy, media):
        if type(snapshot.state) is not ReadState:
            raise ContractError("typed read state required")
        if snapshot.state is not ReadState.CURRENT:
            return _failure(snapshot.state, "authority_" + snapshot.state.value)
        if type(snapshot.versions) is not VersionTuple:
            return _failure(ReadState.UNAVAILABLE, "missing_versions")
        if snapshot.versions != prior:
            return _failure(ReadState.STALE, "dependency_changed")
    if type(policy.sharing_enabled) is not bool:
        raise ContractError("sharing authority unavailable")
    members(policy.entries, EntryState)
    members(policy.sources, SourceState)
    members(media.media, MediaState)
    if any(type(x.ref) is not MediaVersion for x in media.media):
        raise ContractError("typed media dependencies required")
    unique(policy.entries, lambda x: x.ref.identity)
    unique(policy.sources, lambda x: x.ref.source_version_key)
    unique(media.media, lambda x: x.ref.slot)
    if (set(x.ref for x in policy.entries) != set(prior.entries)
            or set(x.ref for x in policy.sources) != set(prior.sources)
            or set(x.ref for x in media.media) != set(prior.media)):
        return _failure(ReadState.UNAVAILABLE, "incomplete_dependencies")
    for source in policy.sources:
        ref, value = source.ref, source.source
        if not all((source.saved, source.approved, source.active, source.canonical_evidence)):
            return _failure(ReadState.DENIED, "ineligible_source")
        if (value.subject_key != prior.subject_key or value.source_key != ref.source_key
                or value.source_version_key != ref.source_version_key
                or value.version != ref.version or value.content_sha256 != ref.content_sha256
                or not value.digest_is_current()):
            return _failure(ReadState.STALE, "source_changed")
    by_entry = {x.ref: x for x in policy.entries}
    display, visitor_ai = [], []
    for selection in candidate.selections:
        current = by_entry[selection.entry]
        if not current.active or not current.identity_resolved:
            return _failure(ReadState.DENIED, "ineligible_entry")
        # Expansions must describe exactly the reviewed permission increase.
        if (selection.expand_display != (selection.display and not current.display_allowed)
                or selection.expand_visitor_ai != (selection.visitor_ai and not current.visitor_ai_allowed)):
            return _failure(ReadState.DENIED, "invalid_permission_expansion")
        values = {x.field: x.value for x in current.wording}
        for delta in selection.deltas:
            if delta.field not in values or values[delta.field] != delta.before:
                return _failure(ReadState.STALE, "editorial_base_changed")
            values[delta.field] = delta.after
        sources = tuple(x for x in prior.sources if x.entry == selection.entry)
        entry = ManifestEntry(selection.entry, tuple(Wording(k, v) for k, v in sorted(values.items())), sources)
        if selection.display:
            display.append(entry)
        if selection.visitor_ai:
            if not sources:
                return _failure(ReadState.UNAVAILABLE, "missing_ai_source")
            for source in policy.sources:
                if source.ref in sources and (
                    Audience.PUBLIC not in source.source.allowed_audiences
                    or Purpose.PUBLIC_PROFILE_ANSWER not in source.source.allowed_purposes
                ):
                    return _failure(ReadState.DENIED, "ai_source_scope")
            visitor_ai.append(entry)
    media_by_slot = {x.ref.slot: x for x in media.media}
    for placement in candidate.placements:
        current = media_by_slot.get(placement.slot)
        if current is None:
            return _failure(ReadState.UNAVAILABLE, "missing_media_dependency")
        if type(current.ready) is not bool or type(current.active) is not bool:
            raise ContractError("typed media status required")
        if not current.ready or not current.active:
            return _failure(ReadState.DENIED, "media_not_ready")
        ref = current.ref
        if (placement.source_kind != ref.source_kind or placement.asset_id != ref.source_key
                or placement.asset_version != ref.asset_version
                or placement.asset_digest != ref.content_sha256
                or placement.presentation_version != ref.placement_version):
            return _failure(ReadState.STALE, "media_changed")
        if type(current.width) is not int or type(current.height) is not int:
            raise ContractError("typed dimensions required")
        try:
            normalized = validate_crop_geometry(placement.crop.as_dict(), slot=placement.slot,
                                                width=current.width, height=current.height)
        except Exception:
            return _failure(ReadState.DENIED, "invalid_crop")
        if normalized != placement.crop:
            return _failure(ReadState.DENIED, "unnormalized_crop")
        if not placement.decorative and not placement.alt_text.strip():
            return _failure(ReadState.DENIED, "missing_alt_text")
        try:
            presentation_error = _check_presentation(placement, current)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            return _failure(ReadState.DENIED, "invalid_presentation")
        if presentation_error:
            return _failure(ReadState.DENIED, presentation_error)
    payload = _canonical_payload(candidate, policy, media)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    reviewed = ReviewedCandidate(candidate, prior, DisplayManifest(tuple(display), candidate.placements),
                                 VisitorAIManifest(tuple(visitor_ai)), hashlib.sha256(encoded).hexdigest())
    return ValidationResult(ReadState.CURRENT, "reviewed_not_published", reviewed)
