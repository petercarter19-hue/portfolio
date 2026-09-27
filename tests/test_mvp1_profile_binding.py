"""Profile approval, pinned identity and digest contracts; no live identity proof."""

from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from services.mvp1_profile_binding import Mvp1ProfileBinding, PinnedResumeNamePort, identity_reference
from services.profile_core_service import (
    InMemoryProfileCoreStore, ProfileCoreService, ProfileIdentityDraft,
    ProfileUnavailableError, make_profile_draft,
)
from services.resume_publication_contracts import (
    ContractError, ReadState, UseAudience, UsePurpose, _context_from_authorized_server,
)
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_publication_service import memory_resume_publication_service, PublicationValidationError
from services.resume_publication_repository import PublicationConflictError
from tests.test_resume_publication_contracts import fixture, review


class Mvp1ProfileBindingTests(TestCase):
    def setUp(self):
        self.owner = "member-a"
        self.draft = make_profile_draft(
            owner_key=self.owner, slug="member-a",
            identity=ProfileIdentityDraft("Alex River", "Engineer", None, "Builds useful tools."),
        )
        self.store = InMemoryProfileCoreStore((self.draft,))
        self.core = ProfileCoreService(self.store)
        self.binding = Mvp1ProfileBinding(self.store)
        self.context = self.core.owner_context(
            actor_key=self.owner, subject_owner_key=self.owner, slug="member-a", purpose="edit",
        )

    def publish(self):
        draft = self.store.draft_for_owner(self.owner)
        prior = self.store.current_publication(self.owner)
        prior_key = prior.revision_key if prior else None
        reviewed = self.core.review_publication(
            self.context, expected_draft_version=draft.version, expected_public_revision=prior_key,
        )
        self.core.publish_publication(
            self.context, expected_draft_version=draft.version,
            expected_public_revision=prior_key, candidate_digest=reviewed["candidate_digest"],
            idempotency_key=str(uuid4()), confirmed=True,
        )
        return self.binding.select_for_owner(self.owner)

    def test_private_draft_is_not_public_approval(self):
        self.assertIsNone(self.binding.select_for_owner(self.owner))

    def test_selected_revision_roundtrips_without_copying_identity(self):
        reference = self.publish()
        self.assertEqual(identity_reference(reference.to_payload()), reference)
        self.assertNotIn("Alex River", str(reference.to_payload()))
        self.assertEqual(self.binding.resolve(self.owner, reference).display_name, "Alex River")
        self.assertIs(self.binding.recheck(self.owner, reference), ReadState.CURRENT)

    def test_profile_update_suppresses_old_selection_without_replacing_it(self):
        reference = self.publish()
        self.core.update_native_draft(
            self.context, expected_version=self.draft.version,
            identity={"display_name": "Alex Brook", "headline": "Engineer",
                      "location": None, "summary": "Builds useful tools."},
        )
        self.assertEqual(self.binding.resolve(self.owner, reference).display_name, "Alex River")
        next_reference = self.publish()
        self.assertNotEqual(next_reference, reference)
        self.assertIsNone(self.binding.resolve(self.owner, reference))
        self.assertEqual(self.binding.resolve(self.owner, next_reference).display_name, "Alex Brook")

    def test_withdrawal_denies_selected_identity(self):
        reference = self.publish()
        self.core.withdraw_publication(
            self.context, expected_public_revision=reference.revision_key,
            idempotency_key="withdraw-identity", confirmed=True,
        )
        self.assertIsNone(self.binding.select_for_owner(self.owner))
        self.assertIsNone(self.binding.resolve(self.owner, reference))

    def test_foreign_owner_and_slug_lookup_cannot_supply_identity(self):
        reference = self.publish()
        self.assertIsNone(self.binding.resolve("member-b", reference))
        with patch.object(self.store, "profile_for_slug", return_value="member-b"):
            self.assertIsNone(self.binding.resolve(self.owner, reference))
            with self.assertRaises(ProfileUnavailableError):
                self.binding.select_for_owner(self.owner)

    def test_malformed_and_unavailable_profile_is_neutral(self):
        reference = self.publish()
        current = self.store.current_publication(self.owner)
        for corrupt in (replace(current, owner_key="member-b"),
                        replace(current, digest="0" * 64), {"display_name": "Not approved"}):
            with self.subTest(corrupt=type(corrupt).__name__), patch.object(
                self.store, "current_publication", return_value=corrupt
            ):
                self.assertIsNone(self.binding.resolve(self.owner, reference))
        with patch.object(self.store, "current_publication", side_effect=RuntimeError("database offline")):
            self.assertIsNone(self.binding.resolve(self.owner, reference))

    def test_closed_reference_and_same_owner_are_required(self):
        reference = self.publish()
        malformed = reference.to_payload()
        malformed["display_name"] = "Unauthorized override"
        with self.assertRaises(ContractError):
            identity_reference(malformed)
        candidate, _, _ = fixture()
        with self.assertRaises(ContractError):
            replace(candidate, profile_identity=replace(reference, owner_key="member-b"))

    def test_review_digest_binds_every_reference_field(self):
        reference = self.publish()
        candidate, policy, media = fixture()
        plain = review(candidate, policy, media).reviewed.digest
        pinned = review(replace(candidate, profile_identity=reference), policy, media).reviewed.digest
        self.assertNotEqual(plain, pinned)
        for changed in (
            replace(reference, revision_key="v2:other"),
            replace(reference, revision_number=reference.revision_number + 1),
            replace(reference, profile_slug="other-slug"),
            replace(reference, publication_digest="0" * 64),
        ):
            self.assertNotEqual(pinned, review(
                replace(candidate, profile_identity=changed), policy, media
            ).reviewed.digest)

    def resume_service(self):
        service = memory_resume_publication_service(profile_binding=self.binding)
        service.policy_service = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        service.bind_slug(self.owner, "member-a")
        return service

    def test_resume_review_pins_identity_and_exact_retry_survives_withdrawal(self):
        selected = self.publish()
        service = self.resume_service()
        reviewed = service.review_for_owner(self.owner).reviewed
        self.assertEqual(reviewed.candidate.profile_identity, selected)
        command = {"type": "publish", "request_id": str(uuid4()), "slug": "member-a",
                   "reviewed_digest": reviewed.digest, "profile_identity": selected.to_payload()}
        first = service.commit(self.owner, command)
        saved = service.repository.load_owner(self.owner)
        self.assertEqual(saved["publications"][saved["current_revision"]]["profile_identity"], selected.to_payload())
        self.core.withdraw_publication(self.context, expected_public_revision=selected.revision_key,
                                       idempotency_key=str(uuid4()), confirmed=True)
        replay = service.commit(self.owner, command)
        self.assertTrue(replay["replayed"])
        self.assertEqual(first["receipt"], replay["receipt"])
        with self.assertRaises(PublicationConflictError):
            service.commit(self.owner, {**command, "profile_identity": None})

    def test_identity_change_after_resume_review_conflicts_without_publishing(self):
        selected = self.publish()
        service = self.resume_service()
        reviewed = service.review_for_owner(self.owner).reviewed
        self.core.withdraw_publication(self.context, expected_public_revision=selected.revision_key,
                                       idempotency_key=str(uuid4()), confirmed=True)
        with self.assertRaises(PublicationConflictError):
            service.commit(self.owner, {"type": "publish", "request_id": str(uuid4()),
                "slug": "member-a", "reviewed_digest": reviewed.digest,
                "profile_identity": selected.to_payload()})
        self.assertIsNone(service.repository.load_owner(self.owner)["current_revision"])

    def test_explicit_neutral_selection_and_no_silent_replacement(self):
        self.publish()
        service = self.resume_service()
        reviewed = service.review_for_owner(self.owner, {"profile_identity": None}).reviewed
        self.assertIsNone(reviewed.candidate.profile_identity)
        with self.assertRaises(PublicationValidationError):
            service.commit(self.owner, {"type": "publish", "request_id": str(uuid4()),
                                       "reviewed_digest": reviewed.digest})
        result = service.commit(self.owner, {"type": "publish", "request_id": str(uuid4()),
            "slug": "member-a", "reviewed_digest": reviewed.digest, "profile_identity": None})
        self.assertEqual(result["outcome"], "published")

    def test_guest_identity_and_ai_name_follow_pinned_publication_and_revoke_late(self):
        selected = self.publish()
        service = self.resume_service()
        reviewed = service.review_for_owner(self.owner).reviewed
        service.commit(self.owner, {"type": "publish", "request_id": str(uuid4()),
            "slug": "member-a", "reviewed_digest": reviewed.digest, "profile_identity": selected.to_payload()})
        guest = service.guest_read(slug="member-a")
        self.assertEqual(guest["public_identity"]["display_name"], "Alex River")
        names = PinnedResumeNamePort(self.binding, service.repository)
        context = _context_from_authorized_server(subject_key=self.owner, resume_key="resume:" + self.owner,
                                                  audience=UseAudience.GUEST, purpose=UsePurpose.VISITOR_AI,
                                                  authenticated_owner_key=None)
        name = names.read_approved(context)
        self.assertEqual(name.full_name, "Alex River")
        self.core.withdraw_publication(self.context, expected_public_revision=selected.revision_key,
                                       idempotency_key=str(uuid4()), confirmed=True)
        self.assertIs(names.recheck(context, name), ReadState.DENIED)
        self.assertIsNone(names.read_approved(context))
        # An unchanged Resume ETag cannot resurrect revoked identity via a 304.
        suppressed = service.guest_read(slug="member-a", if_none_match=guest["etag"])
        self.assertEqual(suppressed["read_state"], "current")
        self.assertIsNone(suppressed["public_identity"])
