"""Synthetic E conformance; no SQL, routes, provider or publication proof."""

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from unittest.mock import Mock

import unittest
from functools import wraps


def parameterized(name, values):
    def decorate(fn):
        @wraps(fn)
        def run(self, **kwargs):
            for value in values:
                with self.subTest(**{name: value}):
                    fn(self, **kwargs, **{name: value})
        return run
    return decorate

from services.ai_foundation.contracts import Audience, Purpose, SourceVersion
from services.resume_media_repository import CatalogAssetRecord, CropRect, MediaPlacement
from services.resume_publication_contracts import (
    CandidateInput, ContractError, EditorialDelta, EntryRef, EntrySelection, EntryState,
    MediaSnapshot, MediaState, MediaVersion, NeutralReviewEvidence, PolicySnapshot, ReadState, SourceRef,
    SourceState, TrustedUseContext, UseAudience, UsePurpose, VersionTuple, Wording,
    _context_from_authorized_server,
)
from services.resume_publication_validation import validate_candidate


def fixture(*, media=False, second=False):
    context = _context_from_authorized_server(
        subject_key="member-a", resume_key="resume-a", audience=UseAudience.OWNER_PREVIEW,
        purpose=UsePurpose.PUBLICATION_REVIEW, authenticated_owner_key="member-a")
    entries, sources, states, selections = [], [], [], []
    for index in range(2 if second else 1):
        entry = EntryRef("member-a", f"role:{index}", "rowversion-4", 2)
        source = SourceVersion.approved(
            source_key=f"source-{index}", source_version_key=f"source-{index}:3", version=3,
            subject_key="member-a", title="Approved evidence", content=f"Led team {index}.",
            allowed_audiences=frozenset({Audience.PUBLIC}),
            allowed_purposes=frozenset({Purpose.PUBLIC_PROFILE_ANSWER}))
        ref = SourceRef(entry, source.source_key, source.source_version_key, 3, source.content_sha256)
        entries.append(entry)
        sources.append(SourceState(ref, source, True, True, True, True))
        states.append(EntryState(entry, (Wording("summary", source.content), Wording("note", None)),
                                 True, True, True, True))
        selections.append(EntrySelection(entry, True, True, False, False))
    placements, media_states = (), ()
    if media:
        checksum = sha256(b"synthetic-media").hexdigest()
        placement = MediaPlacement("story_banner", "owner_photo", "photo-1", 2, checksum,
                                   CropRect(0.0, 0.0, 1.0, 1.0), 3, "A mountain", False,
                                   "Member photo", "Exact caption")
        media_ref = MediaVersion("member-a", "story_banner", 3, "owner_photo", "photo-1",
                                 "rowversion-photo-8", 2, None, checksum, sha256(b"ready").hexdigest())
        placements = (placement,)
        media_states = (MediaState(media_ref, 1800, 600, True, True),)
    versions = VersionTuple("member-a", "resume-a", 4, 2, 8, tuple(entries),
                            tuple(x.ref for x in sources), tuple(x.ref for x in media_states))
    candidate = CandidateInput(context, versions, tuple(selections), placements)
    policy = PolicySnapshot(ReadState.CURRENT, versions, True, tuple(states), tuple(sources))
    media_snapshot = MediaSnapshot(ReadState.CURRENT, versions, media_states)
    return candidate, policy, media_snapshot


def review_evidence_for(entry, wording, owner="member-a"):
    content = "\n".join(
        f"{item.field}={item.value if item.value is not None else ''}"
        for item in sorted(wording)
    )
    return NeutralReviewEvidence(
        entry=entry,
        evidence_key=f"ev:{entry.entry_key}",
        evidence_version_key=f"ev:{entry.entry_key}:1",
        version=1,
        content_sha256=sha256(content.encode("utf-8")).hexdigest(),
        codec="resume-canonical-source.v1",
        canonical_token=entry.content_revision,
        policy_content_version=1,
        access_revision=entry.access_revision,
        lifecycle="active",
        owner_key=owner,
        saved=True,
        approved=True,
        active=True,
        canonical_evidence=True,
        ai_use_count=0,
        content=content,
    )


def review(candidate, policy, media):
    return validate_candidate(candidate, Mock(read_current=Mock(return_value=policy)),
                              Mock(read_current=Mock(return_value=media)))


class PublicationContractTests(unittest.TestCase):
    def test_review_returns_separate_manifests_without_writes(self):
        candidate, policy, media = fixture(media=True)
        p, m = Mock(), Mock()
        p.read_current.return_value, m.read_current.return_value = policy, media
        result = validate_candidate(candidate, p, m)
        assert result.state is ReadState.CURRENT
        assert result.reason == "reviewed_not_published"
        assert result.reviewed.display.placements == candidate.placements
        assert result.reviewed.visitor_ai.entries[0].sources == candidate.prior.sources
        assert not hasattr(result.reviewed.visitor_ai, "placements")
        assert [x[0] for x in p.mock_calls] == ["read_current"]
        assert [x[0] for x in m.mock_calls] == ["read_current"]
        with self.assertRaises(FrozenInstanceError):
            result.reviewed.digest = "changed"


    def test_context_cannot_be_client_dict_or_preview_boolean(self):
        candidate, policy, media = fixture()
        assert validate_candidate({"context": {"owner_preview": True}}, Mock(), Mock()).state is ReadState.DENIED
        with self.assertRaises(ContractError):
            TrustedUseContext("member-a", "resume-a", UseAudience.OWNER_PREVIEW,
                              UsePurpose.OWNER_PREVIEW, "member-a", True)
        with self.assertRaises(ContractError):
            replace(candidate.context, authenticated_owner_key="member-b")
        with self.assertRaises(ContractError):
            replace(candidate, context={"owner_preview": True})


    def test_guest_cannot_review_even_if_sharing_on(self):
        candidate, policy, media = fixture()
        context = _context_from_authorized_server(
            subject_key="member-a", resume_key="resume-a", audience=UseAudience.GUEST,
            purpose=UsePurpose.PUBLIC_DISPLAY, authenticated_owner_key=None)
        for enabled in (True, False):
            assert review(replace(candidate, context=context), replace(policy, sharing_enabled=enabled), media).state is ReadState.DENIED


    def test_sharing_off_owner_preview_remains_distinct_and_digest_bound(self):
        candidate, policy, media = fixture()
        on = review(candidate, policy, media)
        off = review(candidate, replace(policy, sharing_enabled=False), media)
        assert off.state is ReadState.CURRENT
        assert off.reviewed.digest != on.reviewed.digest
        assert not hasattr(off.reviewed, "public_token")


    @parameterized("case", [("draft_revision", True), ("publication_revision", None),
        ("sharing_epoch", "1"), ("sharing_epoch", -1), ("schema_version", 2), ("schema_version", True)])
    def test_missing_or_unsupported_revisions_never_default(self, case):
        field, value = case
        candidate, _, _ = fixture()
        with self.assertRaises(ContractError):
            replace(candidate.prior, **{field: value})


    def test_draft_none_is_unavailable_for_review(self):
        candidate, policy, media = fixture()
        assert review(replace(candidate, prior=replace(candidate.prior, draft_revision=None)), policy, media).state is ReadState.UNAVAILABLE


    @parameterized("state", [ReadState.DENIED, ReadState.STALE, ReadState.UNAVAILABLE])
    @parameterized("port", ["policy", "media"])
    def test_authority_failures_return_no_candidate(self, state, port):
        candidate, policy, media = fixture()
        if port == "policy":
            policy = PolicySnapshot(state)
        else:
            media = MediaSnapshot(state)
        result = review(candidate, policy, media)
        assert result.state is state and result.reviewed is None


    def test_adapter_error_is_neutral_and_has_no_private_exception(self):
        candidate, _, _ = fixture()
        result = validate_candidate(candidate, Mock(read_current=Mock(side_effect=RuntimeError("secret-path"))), Mock())
        assert result.reason == "authority_read_failed"
        assert "secret" not in repr(result)


    @parameterized("change", ["draft_revision", "publication_revision", "sharing_epoch"])
    def test_each_top_level_dependency_change_rejects(self, change):
        candidate, policy, media = fixture()
        altered = replace(candidate.prior, **{change: getattr(candidate.prior, change) + 1})
        assert review(candidate, replace(policy, versions=altered), media).state is ReadState.STALE
        assert review(candidate, policy, replace(media, versions=altered)).state is ReadState.STALE


    def test_content_access_source_and_media_dependencies_are_exact(self):
        candidate, policy, media = fixture(media=True)
        versions = candidate.prior
        variants = [replace(versions, media=(replace(versions.media[0], source_revision="new"),)),
                    replace(versions, media=(replace(versions.media[0], readiness_sha256="0" * 64),))]
        for field, value in (("content_revision", "new"), ("access_revision", 8)):
            entry = replace(versions.entries[0], **{field: value})
            variants.append(replace(versions, entries=(entry,), sources=(replace(versions.sources[0], entry=entry),)))
        variants.append(replace(versions, sources=(replace(versions.sources[0], version=8),)))
        for changed in variants:
            assert review(candidate, replace(policy, versions=changed), media).state is ReadState.STALE


    def test_foreign_context_and_foreign_references_fail(self):
        candidate, policy, media = fixture()
        foreign_context = _context_from_authorized_server(
            subject_key="member-b", resume_key="resume-a", audience=UseAudience.OWNER_PREVIEW,
            purpose=UsePurpose.PUBLICATION_REVIEW, authenticated_owner_key="member-b")
        assert review(replace(candidate, context=foreign_context), policy, media).reason == "foreign_context"
        with self.assertRaises(ContractError):
            replace(candidate.prior, entries=(replace(candidate.prior.entries[0], subject_key="member-b"),))


    @parameterized("field", ["saved", "approved", "active", "canonical_evidence"])
    def test_raw_pending_deleted_assistance_or_artwork_sources_denied(self, field):
        candidate, policy, media = fixture()
        source = replace(policy.sources[0], **{field: False})
        assert review(candidate, replace(policy, sources=(source,)), media).reason == "ineligible_source"


    @parameterized("field", ["active", "identity_resolved"])
    def test_deleted_or_ambiguous_entry_denied(self, field):
        candidate, policy, media = fixture()
        assert review(candidate, replace(policy, entries=(replace(policy.entries[0], **{field: False}),)), media).state is ReadState.DENIED


    def test_source_digest_and_scope_are_not_assumed(self):
        candidate, policy, media = fixture()
        state = policy.sources[0]
        bad = replace(state, source=replace(state.source, content="Changed source"))
        assert review(candidate, replace(policy, sources=(bad,)), media).reason == "source_changed"
        bad = replace(state, source=replace(state.source, allowed_audiences=frozenset({Audience.OWNER})))
        assert review(candidate, replace(policy, sources=(bad,)), media).reason == "ai_source_scope"


    def test_display_hidden_ai_allowed_is_separate(self):
        candidate, policy, media = fixture()
        candidate = replace(candidate, selections=(replace(candidate.selections[0], display=False),))
        reviewed = review(candidate, policy, media).reviewed
        assert not reviewed.display.entries
        assert reviewed.visitor_ai.entries


    def test_expansion_must_be_explicit_exact_and_does_not_mutate_policy(self):
        candidate, policy, media = fixture()
        private = replace(policy, entries=(replace(policy.entries[0], display_allowed=False, visitor_ai_allowed=False),))
        assert review(candidate, private, media).reason == "invalid_permission_expansion"
        evidence = review_evidence_for(candidate.prior.entries[0], policy.entries[0].wording)
        candidate = replace(
            candidate,
            selections=(replace(candidate.selections[0], expand_display=True, expand_visitor_ai=True),),
            review_evidence=(evidence,),
        )
        assert review(candidate, private, media).state is ReadState.CURRENT
        assert private.entries[0].display_allowed is False
        assert review(candidate, policy, media).reason == "invalid_permission_expansion"


    def test_first_ai_grant_uses_neutral_saved_evidence_and_does_not_write(self):
        candidate, policy, media = fixture()
        private = replace(policy, entries=(replace(policy.entries[0], display_allowed=True, visitor_ai_allowed=False),))
        ports = Mock()
        without_evidence = replace(
            candidate,
            selections=(replace(candidate.selections[0], expand_visitor_ai=True),),
        )
        assert review(without_evidence, private, media).reason == "missing_review_evidence"
        stale = review_evidence_for(
            replace(candidate.prior.entries[0], content_revision="old"),
            policy.entries[0].wording,
        )
        stale_candidate = replace(
            without_evidence,
            review_evidence=(replace(stale, entry=candidate.prior.entries[0], canonical_token="old"),),
        )
        assert review(stale_candidate, private, media).state is ReadState.STALE
        evidence = review_evidence_for(candidate.prior.entries[0], policy.entries[0].wording)
        ready = replace(without_evidence, review_evidence=(evidence,))
        p, m = Mock(), Mock()
        p.read_current.return_value, m.read_current.return_value = private, media
        result = validate_candidate(ready, p, m)
        assert result.state is ReadState.CURRENT
        assert result.reviewed.visitor_ai.entries
        assert [x[0] for x in p.mock_calls] == ["read_current"]
        assert [x[0] for x in m.mock_calls] == ["read_current"]
        assert private.entries[0].visitor_ai_allowed is False


    def test_review_evidence_does_not_invent_public_source_version(self):
        candidate, policy, media = fixture()
        evidence = review_evidence_for(candidate.prior.entries[0], policy.entries[0].wording)
        assert evidence.ai_use_count == 0
        assert "PUBLIC" not in repr(evidence)


    def test_exact_changed_fields_only_and_prose_unchanged(self):
        candidate, policy, media = fixture()
        delta = EditorialDelta("summary", "Led team 0.", "  Led a team.\n")
        candidate = replace(candidate, selections=(replace(candidate.selections[0], deltas=(delta,)),))
        result = review(candidate, policy, media)
        assert dict((x.field, x.value) for x in result.reviewed.display.entries[0].wording) == {
            "note": None, "summary": "  Led a team.\n"}
        assert policy.entries[0].wording[1].value == "Led team 0."
        stale = replace(delta, before="Not the base")
        assert review(replace(candidate, selections=(replace(candidate.selections[0], deltas=(stale,)),)), policy, media).reason == "editorial_base_changed"
        with self.assertRaises(ContractError):
            EditorialDelta("summary", "same", "same")


    def test_duplicates_and_mutable_collections_rejected(self):
        candidate, policy, _ = fixture()
        for values in ((candidate.selections[0],) * 2, list(candidate.selections)):
            with self.assertRaises(ContractError):
                replace(candidate, selections=values)
        with self.assertRaises(ContractError):
            replace(candidate.prior, sources=candidate.prior.sources * 2)
        with self.assertRaises(ContractError):
            replace(policy.entries[0], wording=(Wording("summary", "a"), Wording("summary", "b")))


    def test_digest_stable_for_set_order_and_changes_for_presentation_or_wording(self):
        candidate, policy, media = fixture(media=True, second=True)
        baseline = review(candidate, policy, media).reviewed.digest
        reordered = replace(candidate, selections=tuple(reversed(candidate.selections)),
                            prior=replace(candidate.prior, entries=tuple(reversed(candidate.prior.entries)),
                                          sources=tuple(reversed(candidate.prior.sources))))
        assert review(reordered, replace(policy, entries=tuple(reversed(policy.entries)),
                                        sources=tuple(reversed(policy.sources))), media).reviewed.digest == baseline
        for field, value in (("caption", "different"), ("alt_text", "other description")):
            changed = replace(candidate, placements=(replace(candidate.placements[0], **{field: value}),))
            assert review(changed, policy, media).reviewed.digest != baseline
        changed = replace(candidate, selections=(replace(candidate.selections[0], deltas=(EditorialDelta("note", None, ""),)), candidate.selections[1]))
        assert review(changed, policy, media).reviewed.digest != baseline
        purpose = replace(candidate.context, purpose=UsePurpose.OWNER_PREVIEW)
        assert review(replace(candidate, context=purpose), policy, media).reviewed.digest != baseline


    @parameterized("coordinate", [float("nan"), float("inf"), True])
    def test_nonfinite_or_boolean_crop_rejected(self, coordinate):
        candidate, _, _ = fixture(media=True)
        with self.assertRaises(ContractError):
            replace(candidate, placements=(replace(candidate.placements[0], crop=CropRect(coordinate, 0, 1, 1)),))


    def test_media_requires_ready_versioned_authority_and_valid_accessible_crop(self):
        candidate, policy, media = fixture(media=True)
        for field in ("ready", "active"):
            assert review(candidate, policy, replace(media, media=(replace(media.media[0], **{field: False}),))).reason == "media_not_ready"
        assert review(candidate, policy, replace(media, media=())).reason == "incomplete_dependencies"
        for crop in (CropRect(0, 0, 2, 1), CropRect(0, 0, .1, 1), CropRect(.000000001, 0, .999999999, 1)):
            changed = replace(candidate, placements=(replace(candidate.placements[0], crop=crop),))
            assert review(changed, policy, media).state is ReadState.DENIED
        changed = replace(candidate, placements=(replace(candidate.placements[0], alt_text=""),))
        assert review(changed, policy, media).reason == "missing_alt_text"


    def test_generated_media_pins_catalog_and_is_never_ai_evidence(self):
        candidate, policy, media = fixture(media=True)
        placement = replace(candidate.placements[0], source_kind="generated_illustration", provenance_label="Generated illustration")
        ref = replace(candidate.prior.media[0], source_kind="generated_illustration", catalog_revision="catalog-9")
        versions = replace(candidate.prior, media=(ref,))
        candidate = replace(candidate, prior=versions, placements=(placement,))
        policy = replace(policy, versions=versions)
        catalog = CatalogAssetRecord(ref.source_key, ref.asset_version, ref.content_sha256,
                                     "Leadership", "concept", ("Teamwork",), 1800, 600)
        media = replace(media, versions=versions, media=(replace(media.media[0], ref=ref, catalog=catalog),))
        result = review(candidate, policy, media)
        assert result.state is ReadState.CURRENT
        assert result.reviewed.visitor_ai.entries[0].sources == versions.sources
        with self.assertRaises(ContractError):
            replace(ref, catalog_revision=None)
        for field, value in (("caption", "leadership"), ("alt_text", "TEAMWORK")):
            changed = replace(candidate, placements=(replace(placement, **{field: value}),))
            assert review(changed, policy, media).state is ReadState.DENIED
        absent = replace(media, media=(replace(media.media[0], catalog=None),))
        assert review(candidate, policy, absent).reason == "missing_catalog_evidence"
        changed_catalog = replace(catalog, provenance=(("model", "Approved model"),))
        authoritative = replace(media, media=(replace(media.media[0], catalog=changed_catalog),))
        assert review(candidate, policy, authoritative).reason == "invalid_provenance"
        changed = replace(candidate, placements=(replace(placement, provenance_label="Generated illustration (Approved model)"),))
        revised = review(changed, policy, authoritative)
        assert revised.state is ReadState.CURRENT
        assert revised.reviewed.digest != result.reviewed.digest
        assert revised.reviewed.display.placements[0].provenance_label == "Generated illustration (Approved model)"

    def test_media_text_is_bounded_exact_and_provenance_is_server_derived(self):
        candidate, policy, media = fixture(media=True)
        for field, value in (
            ("provenance_label", ""), ("provenance_label", "private/blob/member/photo.jpg"),
            ("provenance_label", "Generated illustration"),
            ("alt_text", "a" * 10000), ("caption", "c" * 10000),
            ("caption", "NUL\x00caption"), ("alt_text", "NUL\x00alt"),
            ("alt_text", " leading space"), ("caption", "trailing space "),
        ):
            with self.subTest(field=field, value=value[:40]):
                changed = replace(candidate, placements=(replace(candidate.placements[0], **{field: value}),))
                result = review(changed, policy, media)
                assert result.state is ReadState.DENIED and result.reviewed is None
        result = review(candidate, policy, media)
        assert result.reviewed.display.placements == candidate.placements

    def test_placement_and_presentation_revisions_must_be_positive(self):
        candidate, _, _ = fixture(media=True)
        for invalid in (0, -1, True, None, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ContractError):
                    replace(candidate.prior.media[0], placement_version=invalid)
                with self.assertRaises(ContractError):
                    replace(candidate, placements=(replace(candidate.placements[0], presentation_version=invalid),))

    def test_valid_version_scope_permission_and_crop_changes_change_digest(self):
        candidate, policy, media = fixture(media=True)
        baseline = review(candidate, policy, media).reviewed.digest
        for field in ("draft_revision", "publication_revision", "sharing_epoch"):
            versions = replace(candidate.prior, **{field: getattr(candidate.prior, field) + 1})
            result = review(replace(candidate, prior=versions), replace(policy, versions=versions),
                            replace(media, versions=versions))
            assert result.reviewed.digest != baseline
        for field in ("display", "visitor_ai"):
            changed = replace(candidate, selections=(replace(candidate.selections[0], **{field: False}),))
            assert review(changed, policy, media).reviewed.digest != baseline
        source = replace(policy.sources[0], source=replace(policy.sources[0].source,
            allowed_purposes=frozenset({Purpose.PUBLIC_PROFILE_ANSWER, Purpose.EVIDENCE_FINDER})))
        assert review(candidate, replace(policy, sources=(source,)), media).reviewed.digest != baseline
        crop = CropRect(.1, .1, .8, .8)
        changed = replace(candidate, placements=(replace(candidate.placements[0], crop=crop),))
        assert review(changed, policy, media).reviewed.digest != baseline
        integral = replace(candidate, placements=(replace(candidate.placements[0], crop=CropRect(0, -0.0, 1, 1)),))
        assert review(integral, policy, media).reviewed.digest == baseline

    def test_source_content_change_with_consistent_new_versions_changes_digest(self):
        candidate, policy, media = fixture()
        baseline = review(candidate, policy, media).reviewed.digest
        content = "Led a newly approved team."
        old = policy.sources[0]
        source = replace(old.source, content=content, version=4, source_version_key="source-0:4",
                         content_sha256=sha256(content.encode()).hexdigest())
        ref = replace(old.ref, version=4, source_version_key=source.source_version_key,
                      content_sha256=source.content_sha256)
        versions = replace(candidate.prior, sources=(ref,))
        result = review(replace(candidate, prior=versions), replace(policy, versions=versions,
                        sources=(replace(old, ref=ref, source=source),)), replace(media, versions=versions))
        assert result.reviewed.digest != baseline


    @parameterized("mutation", ["missing_versions", "sharing_unknown", "dict", "duplicate", "mutable"])
    def test_malformed_authority_cannot_yield_review(self, mutation):
        candidate, policy, media = fixture()
        if mutation == "missing_versions":
            policy = replace(policy, versions=None)
        elif mutation == "sharing_unknown":
            policy = replace(policy, sharing_enabled=None)
        elif mutation == "dict":
            policy = {"state": "current"}
        elif mutation == "duplicate":
            policy = replace(policy, entries=policy.entries * 2)
        else:
            policy = replace(policy, sources=list(policy.sources))
        result = review(candidate, policy, media)
        assert result.state is ReadState.UNAVAILABLE and result.reviewed is None


if __name__ == "__main__":
    unittest.main()
