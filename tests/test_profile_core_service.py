"""D0 Profile-core publication and owner-isolation contracts."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from services.profile_core_service import (
    InMemoryProfileCoreStore,
    ProfileAboutDraft,
    ProfileAuthorizationError,
    ProfileConflictError,
    ProfileCoreService,
    ProfileCurrentChapterDraft,
    ProfileIdentityDraft,
    ProfileNotFound,
    ProfilePlacementDraft,
    ProfilePublicationCommand,
    ProfilePublicationItem,
    PROFILE_PUBLICATION_ACTION_PUBLISH,
    PROFILE_PUBLICATION_ACTION_WITHDRAW,
    ProfileUnavailableError,
    ProfileValidationError,
    make_profile_draft,
)
from services.profile_posts_adapter import (
    CommunityPostReferenceAdapter,
    CommunityPostReference,
    EligibleCommunityPostSource,
    InMemoryCommunityPostSourceReader,
)


OWNER_A = "ownerAlpha_123"
OWNER_B = "ownerBravo_456"
POST_KEY = "communityPost_123"


class AdversarialProfileStore(InMemoryProfileCoreStore):
    """Test double that can return a foreign/malformed record for A's lookup."""

    def __init__(self, drafts):
        super().__init__(drafts)
        self.foreign_draft = None
        self.foreign_publication = None
        self.foreign_command = None

    def draft_for_owner(self, owner_key):
        return self.foreign_draft or super().draft_for_owner(owner_key)

    def current_publication(self, owner_key):
        return self.foreign_publication or super().current_publication(owner_key)

    def command_for(self, owner_key, idempotency_key):
        return self.foreign_command or super().command_for(owner_key, idempotency_key)


class ConcurrentProfileStore(InMemoryProfileCoreStore):
    def append_publication(self, revision, command, *, action, expected_public_revision, expected_draft):
        current = self._publications.get(revision.owner_key)
        if current is None:
            competitor = replace(revision, revision_key="v1:competitor", digest=revision.digest)
            self._publications[revision.owner_key] = competitor
        return super().append_publication(
            revision,
            command,
            action=action,
            expected_public_revision=expected_public_revision,
            expected_draft=expected_draft,
        )


class ConcurrentIdenticalCommandStore(InMemoryProfileCoreStore):
    """Simulate SQL observing a winning identical command after local build."""

    def append_publication(self, revision, command, *, action, expected_public_revision, expected_draft):
        winner_revision = replace(revision, revision_key="v1:winning-command")
        winner = replace(
            command,
            command_key="winningCommand_123",
            revision=winner_revision,
        )
        self._publications[revision.owner_key] = winner_revision
        self._commands[(command.owner_key, command.idempotency_key)] = winner
        return super().append_publication(
            revision,
            command,
            action=action,
            expected_public_revision=expected_public_revision,
            expected_draft=expected_draft,
        )


class DraftChangedAtCommitStore(InMemoryProfileCoreStore):
    """Simulate another writer saving after review and before commit."""

    def append_publication(self, revision, command, *, action, expected_public_revision, expected_draft):
        current = self._drafts[revision.owner_key]
        self._drafts[revision.owner_key] = replace(
            current,
            version="v99:concurrent",
            identity=replace(current.identity, headline="Changed by another writer"),
        )
        return super().append_publication(
            revision,
            command,
            action=action,
            expected_public_revision=expected_public_revision,
            expected_draft=expected_draft,
        )


class TamperingPublicationStore(InMemoryProfileCoreStore):
    """Exercise the storage-side fence before it can replace current state."""

    def __init__(self, drafts):
        super().__init__(drafts)
        self.rewrite_candidate = None

    def append_publication(self, revision, command, *, action, expected_public_revision, expected_draft):
        if self.rewrite_candidate is not None:
            revision = self.rewrite_candidate(revision)
            command = replace(command, revision=revision)
        return super().append_publication(
            revision,
            command,
            action=action,
            expected_public_revision=expected_public_revision,
            expected_draft=expected_draft,
        )


def _identity(name="Avery Carter"):
    return ProfileIdentityDraft(
        display_name=name,
        headline="Systems engineer and technical leader",
        location="Huntsville, Alabama",
        summary="I build complex systems with care and clarity.",
    )


def _chapter():
    return ProfileCurrentChapterDraft(
        label="Building deliberately",
        body="A present-tense note about the work and people around it.",
    )


def _about():
    return ProfileAboutDraft(
        heading="The person behind the work",
        body="A short, Profile-specific orientation that does not duplicate a story.",
        resume_path="/avery/resume",
        story_path="/avery/my-story",
        ask_path="/ask-avery",
    )


def _draft(owner=OWNER_A, slug="avery", name="Avery Carter"):
    return make_profile_draft(
        owner_key=owner,
        slug=slug,
        identity=_identity(name),
        current_chapter=_chapter(),
        about=_about(),
    )


class ProfileCoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryProfileCoreStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        self.community_source = EligibleCommunityPostSource(
            source_key=POST_KEY,
            owner_key=OWNER_A,
            source_revision="community:v7",
            canonical_path="/the-slate/posts/communityPost_123",
            published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        self.community_reader = InMemoryCommunityPostSourceReader(
            {(OWNER_A, POST_KEY, "community:v7"): self.community_source},
            {(OWNER_A, POST_KEY): "community:v7"},
        )
        self.community_references = CommunityPostReferenceAdapter(self.community_reader)
        self.service = ProfileCoreService(
            self.store, community_post_references=self.community_references
        )
        self.owner_a = self.service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="api"
        )
        self.owner_b_on_a = self.service.owner_context(
            actor_key=OWNER_B, subject_owner_key=OWNER_A, slug="avery", purpose="api"
        )

    def _review(self):
        draft = self.store.draft_for_owner(OWNER_A)
        return self.service.review_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=None,
        )

    def _publish(self, *, key="publish-request-0001"):
        draft = self.store.draft_for_owner(OWNER_A)
        current = self.store.current_publication(OWNER_A)
        review = self.service.review_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=current.revision_key if current else None,
        )
        return self.service.publish_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=current.revision_key if current else None,
            candidate_digest=review["candidate_digest"],
            idempotency_key=key,
            confirmed=True,
        )

    def test_public_read_requires_immutable_publication(self):
        with self.assertRaises(ProfileNotFound):
            self.service.public_read(slug="avery", destination="home")

        command = self._publish()
        public = self.service.public_read(slug="avery", destination="home")

        self.assertEqual(public.publication_revision, command.revision.revision_key)
        self.assertEqual(public.mode, "public")
        self.assertEqual(public.identity["display_name"], "Avery Carter")
        self.assertNotIn("owner_key", public.identity)

    def test_draft_compare_and_swap_allows_only_one_writer(self):
        original = self.store.draft_for_owner(OWNER_A)
        first = replace(original, version="v2:first-writer", identity=_identity("First Writer"))
        second = replace(original, version="v2:second-writer", identity=_identity("Second Writer"))
        self.store.put_draft(first, expected_version=original.version)
        with self.assertRaises(ProfileConflictError):
            self.store.put_draft(second, expected_version=original.version)
        self.assertEqual(self.store.draft_for_owner(OWNER_A), first)

    def test_concurrent_identical_publish_returns_exact_winning_command(self):
        store = ConcurrentIdenticalCommandStore([_draft()])
        service = ProfileCoreService(store)
        context = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        draft = store.draft_for_owner(OWNER_A)
        review = service.review_publication(
            context, expected_draft_version=draft.version, expected_public_revision=None
        )
        result = service.publish_publication(
            context,
            expected_draft_version=draft.version,
            expected_public_revision=None,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-2001",
            confirmed=True,
        )
        self.assertEqual(result.command_key, "winningCommand_123")
        self.assertEqual(result.revision.revision_key, "v1:winning-command")
        self.assertEqual(store.command_for(OWNER_A, "publish-request-2001"), result)

    def test_draft_change_at_commit_rejects_publish_and_preserves_prior_public(self):
        first = self._publish(key="publish-request-2002")
        race_store = DraftChangedAtCommitStore([self.store.draft_for_owner(OWNER_A)])
        race_store._publications[OWNER_A] = first.revision
        service = ProfileCoreService(race_store)
        context = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        draft = race_store.draft_for_owner(OWNER_A)
        review = service.review_publication(
            context,
            expected_draft_version=draft.version,
            expected_public_revision=first.revision.revision_key,
        )
        with self.assertRaises(ProfileConflictError):
            service.publish_publication(
                context,
                expected_draft_version=draft.version,
                expected_public_revision=first.revision.revision_key,
                candidate_digest=review["candidate_digest"],
                idempotency_key="publish-request-2003",
                confirmed=True,
            )
        self.assertEqual(race_store.current_publication(OWNER_A), first.revision)

    def test_owner_preview_is_field_equivalent_to_public_reader(self):
        self._publish()

        preview = self.service.owner_preview_public(self.owner_a, destination="home")
        public = self.service.public_read(slug="avery", destination="home")

        self.assertEqual(preview, public)

    def test_cross_owner_cannot_read_private_owner_state_or_update_draft(self):
        with self.assertRaises(ProfileAuthorizationError):
            self.service.owner_state(self.owner_b_on_a)
        draft = self.store.draft_for_owner(OWNER_A)
        with self.assertRaises(ProfileAuthorizationError):
            self.service.update_native_draft(
                self.owner_b_on_a,
                expected_version=draft.version,
                identity={
                    "display_name": "Attempted takeover",
                    "headline": "No",
                    "location": None,
                    "summary": "No",
                },
            )

    def test_draft_update_is_version_fenced_and_does_not_change_publication(self):
        initial = self._publish()
        draft = self.store.draft_for_owner(OWNER_A)

        updated = self.service.update_native_draft(
            self.owner_a,
            expected_version=draft.version,
            identity={
                "display_name": "Avery Carter",
                "headline": "A clearer next chapter",
                "location": "Huntsville, Alabama",
                "summary": "Draft text is private until explicit publication.",
            },
        )

        self.assertNotEqual(updated.version, draft.version)
        public = self.service.public_read(slug="avery", destination="home")
        self.assertEqual(public.publication_revision, initial.revision.revision_key)
        self.assertEqual(public.identity["headline"], "Systems engineer and technical leader")
        with self.assertRaises(ProfileConflictError):
            self.service.update_native_draft(
                self.owner_a,
                expected_version=draft.version,
                identity={
                    "display_name": "Avery Carter",
                    "headline": "Lost update",
                    "location": None,
                    "summary": "This must fail.",
                },
            )

    def test_about_paths_reject_noncanonical_same_origin_tricks_on_input_and_storage(self):
        unsafe_paths = (
            "/\\evil.example/phish",
            "//evil.example/phish",
            "/%2fevil.example/phish",
            "/avery/%5cprivate",
            "/avery/%2e%2e/private",
            "/avery/../private",
            "/avery/resume?next=evil",
            "/avery/my-story#private",
        )
        original = self.store.draft_for_owner(OWNER_A)
        for unsafe_path in unsafe_paths:
            with self.subTest(boundary="input", unsafe_path=unsafe_path):
                with self.assertRaises(ProfileValidationError):
                    self.service.update_native_draft(
                        self.owner_a,
                        expected_version=original.version,
                        about={
                            "heading": "About Avery",
                            "body": "Only canonical same-origin Profile links are retained.",
                            "resume_path": unsafe_path,
                            "story_path": "/avery/my-story",
                            "ask_path": "/ask-pete",
                        },
                    )
                self.assertEqual(self.store.draft_for_owner(OWNER_A), original)

            with self.subTest(boundary="stored manifest", unsafe_path=unsafe_path):
                hostile = replace(
                    original,
                    about=replace(original.about, resume_path=unsafe_path),
                )
                self.store._drafts[OWNER_A] = hostile
                with self.assertRaises(ProfileUnavailableError):
                    self.service.owner_state(self.owner_a)
                with self.assertRaises(ProfileUnavailableError):
                    self.service.review_publication(
                        self.owner_a,
                        expected_draft_version=hostile.version,
                        expected_public_revision=None,
                    )
                self.store._drafts[OWNER_A] = original

        updated = self.service.update_native_draft(
            self.owner_a,
            expected_version=original.version,
            about={
                "heading": "About Avery",
                "body": "Canonical Profile routes remain valid.",
                "resume_path": "/avery/resume",
                "story_path": "/avery/my-story",
                "ask_path": "/ask-pete",
            },
        )
        self.assertEqual(updated.about.resume_path, "/avery/resume")
        self.assertEqual(updated.about.story_path, "/avery/my-story")
        self.assertEqual(updated.about.ask_path, "/ask-pete")

    def test_publish_is_explicit_idempotent_and_preserves_old_revision(self):
        first = self._publish(key="publish-request-0001")
        draft = self.store.draft_for_owner(OWNER_A)
        second = self.service.publish_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=None,
            candidate_digest=first.revision.digest,
            idempotency_key="publish-request-0001",
            confirmed=True,
        )
        self.assertEqual(first, second)

        draft = self.store.draft_for_owner(OWNER_A)
        updated = self.service.update_native_draft(
            self.owner_a,
            expected_version=draft.version,
            about={
                "heading": "A changed About",
                "body": "New draft wording awaits an exact review.",
                "resume_path": "/avery/resume",
                "story_path": "/avery/my-story",
                "ask_path": "/ask-avery",
                "principles": [
                    {"title": "Clarity over complexity", "body": "Make work understandable."},
                    {"title": "People before process", "body": "Great systems start with listening."},
                ],
            },
        )
        review = self.service.review_publication(
            self.owner_a,
            expected_draft_version=updated.version,
            expected_public_revision=first.revision.revision_key,
        )
        new = self.service.publish_publication(
            self.owner_a,
            expected_draft_version=updated.version,
            expected_public_revision=first.revision.revision_key,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-0002",
            confirmed=True,
        )
        self.assertNotEqual(new.revision.revision_key, first.revision.revision_key)
        self.assertEqual(first.revision.about.heading, "The person behind the work")
        self.assertEqual(new.revision.about.heading, "A changed About")
        self.assertEqual(len(new.revision.about.principles), 2)

    def test_wrong_candidate_digest_does_not_advance_publication(self):
        draft = self.store.draft_for_owner(OWNER_A)
        with self.assertRaises(ProfileConflictError):
            self.service.publish_publication(
                self.owner_a,
                expected_draft_version=draft.version,
                expected_public_revision=None,
                candidate_digest="0" * 64,
                idempotency_key="publish-request-0003",
                confirmed=True,
            )
        self.assertIsNone(self.store.current_publication(OWNER_A))

    def _assert_rejected_publication_tamper_preserves_prior(self, *, include_placement, rewrite):
        store = TamperingPublicationStore([_draft()])
        service = ProfileCoreService(store, community_post_references=self.community_references)
        context = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        if include_placement:
            draft = service.add_community_post_reference(
                context,
                expected_version=store.draft_for_owner(OWNER_A).version,
                source_key=POST_KEY,
                source_revision="community:v7",
            )
        else:
            draft = store.draft_for_owner(OWNER_A)
        first_review = service.review_publication(
            context, expected_draft_version=draft.version, expected_public_revision=None
        )
        first = service.publish_publication(
            context,
            expected_draft_version=draft.version,
            expected_public_revision=None,
            candidate_digest=first_review["candidate_digest"],
            idempotency_key="publish-request-3101",
            confirmed=True,
        )
        store.rewrite_candidate = rewrite
        second_review = service.review_publication(
            context,
            expected_draft_version=draft.version,
            expected_public_revision=first.revision.revision_key,
        )
        with self.assertRaises(ProfileConflictError):
            service.publish_publication(
                context,
                expected_draft_version=draft.version,
                expected_public_revision=first.revision.revision_key,
                candidate_digest=second_review["candidate_digest"],
                idempotency_key="publish-request-3102",
                confirmed=True,
            )
        self.assertEqual(store.current_publication(OWNER_A), first.revision)

    def test_publish_rejects_tampered_native_item_and_action_before_replacing_prior_revision(self):
        cases = (
            ("omitted_native", False, lambda revision: replace(revision, current_chapter=None)),
            (
                "changed_item_kind",
                True,
                lambda revision: replace(
                    revision,
                    items=(replace(revision.items[0], content_kind="project_reference"),),
                ),
            ),
            (
                "action_confusion",
                False,
                lambda revision: replace(
                    revision,
                    action=PROFILE_PUBLICATION_ACTION_WITHDRAW,
                    identity=None,
                    current_chapter=None,
                    about=None,
                    items=(),
                ),
            ),
        )
        for label, include_placement, rewrite in cases:
            with self.subTest(label=label):
                self._assert_rejected_publication_tamper_preserves_prior(
                    include_placement=include_placement, rewrite=rewrite
                )

    def test_publish_rejects_case_only_native_source_metadata_and_content_kind_tampering(self):
        cases = (
            (
                "native",
                False,
                lambda revision: replace(
                    revision,
                    identity=replace(revision.identity, display_name="avery Carter"),
                ),
            ),
            (
                "source_metadata",
                True,
                lambda revision: replace(
                    revision,
                    items=(replace(
                        revision.items[0],
                        source_reference=replace(
                            revision.items[0].source_reference,
                            canonical_path="/the-Slate/posts/communityPost_123",
                        ),
                    ),),
                ),
            ),
            (
                "content_kind",
                True,
                lambda revision: replace(
                    revision,
                    items=(replace(
                        revision.items[0], content_kind="Community_post_reference"
                    ),),
                ),
            ),
        )
        for label, include_placement, rewrite in cases:
            with self.subTest(label=label):
                self._assert_rejected_publication_tamper_preserves_prior(
                    include_placement=include_placement, rewrite=rewrite
                )

    def test_publish_rejects_accent_only_native_source_metadata_and_content_kind_tampering(self):
        cases = (
            (
                "native",
                False,
                lambda revision: replace(
                    revision,
                    identity=replace(revision.identity, display_name=chr(0x00C1) + "very Carter"),
                ),
            ),
            (
                "source_metadata",
                True,
                lambda revision: replace(
                    revision,
                    items=(replace(
                        revision.items[0],
                        source_reference=replace(
                            revision.items[0].source_reference,
                            canonical_path="/the-sl" + chr(0x00E1) + "te/posts/communityPost_123",
                        ),
                    ),),
                ),
            ),
            (
                "content_kind",
                True,
                lambda revision: replace(
                    revision,
                    items=(replace(
                        revision.items[0], content_kind="c" + chr(0x00F3) + "mmunity_post_reference"
                    ),),
                ),
            ),
        )
        for label, include_placement, rewrite in cases:
            with self.subTest(label=label):
                self._assert_rejected_publication_tamper_preserves_prior(
                    include_placement=include_placement, rewrite=rewrite
                )

    def test_withdraw_creates_new_empty_revision_and_preserves_prior_revision(self):
        first = self._publish()
        withdrawn = self.service.withdraw_publication(
            self.owner_a,
            expected_public_revision=first.revision.revision_key,
            idempotency_key="publish-request-0004",
            confirmed=True,
        )
        self.assertNotEqual(first.revision.revision_key, withdrawn.revision.revision_key)
        self.assertIsNotNone(first.revision.identity)
        self.assertIsNone(withdrawn.revision.identity)
        with self.assertRaises(ProfileNotFound):
            self.service.public_read(slug="avery", destination="home")
        review = self.service.review_publication(
            self.owner_a,
            expected_draft_version=self.store.draft_for_owner(OWNER_A).version,
            expected_public_revision=withdrawn.revision.revision_key,
        )
        republished = self.service.publish_publication(
            self.owner_a,
            expected_draft_version=self.store.draft_for_owner(OWNER_A).version,
            expected_public_revision=withdrawn.revision.revision_key,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-0004-republish",
            confirmed=True,
        )
        self.assertEqual(republished.revision.action, PROFILE_PUBLICATION_ACTION_PUBLISH)
        self.assertIsNotNone(republished.revision.identity)

    def test_community_reference_is_not_copied_into_public_payload(self):
        draft = self.store.draft_for_owner(OWNER_A)
        draft = self.service.add_community_post_reference(
            self.owner_a,
            expected_version=draft.version,
            source_key=POST_KEY,
            source_revision="community:v7",
            destination="posts",
            region="stream",
        )
        review = self.service.review_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=None,
        )
        self.service.publish_publication(
            self.owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=None,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-0005",
            confirmed=True,
        )
        posts = self.service.public_read(slug="avery", destination="posts")
        self.assertEqual(posts.posts[0]["canonical_path"], self.community_source.canonical_path)
        self.assertNotIn("source_key", posts.posts[0])
        self.assertNotIn("source_revision", posts.posts[0])
        self.assertNotIn("body", posts.posts[0])

    def test_exact_publish_retry_returns_immutable_command_after_source_changes(self):
        for source_state in ("changed", "revoked"):
            with self.subTest(source_state=source_state):
                self.setUp()
                draft = self.service.add_community_post_reference(
                    self.owner_a,
                    expected_version=self.store.draft_for_owner(OWNER_A).version,
                    source_key=POST_KEY,
                    source_revision="community:v7",
                    destination="posts",
                    region="stream",
                )
                review = self.service.review_publication(
                    self.owner_a,
                    expected_draft_version=draft.version,
                    expected_public_revision=None,
                )
                original = self.service.publish_publication(
                    self.owner_a,
                    expected_draft_version=draft.version,
                    expected_public_revision=None,
                    candidate_digest=review["candidate_digest"],
                    idempotency_key="publish-request-1020",
                    confirmed=True,
                )
                if source_state == "changed":
                    self.community_reader._current_revisions[(OWNER_A, POST_KEY)] = "community:v8"
                else:
                    del self.community_reader._records[(OWNER_A, POST_KEY, "community:v7")]

                retry = self.service.publish_publication(
                    self.owner_a,
                    expected_draft_version=draft.version,
                    expected_public_revision=None,
                    candidate_digest=review["candidate_digest"],
                    idempotency_key="publish-request-1020",
                    confirmed=True,
                )
                self.assertEqual(retry, original)
                with self.assertRaises(ProfileUnavailableError):
                    self.service.publish_publication(
                        self.owner_a,
                        expected_draft_version=draft.version,
                        expected_public_revision=original.revision.revision_key,
                        candidate_digest=review["candidate_digest"],
                        idempotency_key="publish-request-1021",
                        confirmed=True,
                    )
                self.assertEqual(self.store.current_publication(OWNER_A), original.revision)

    def test_unverified_or_cross_owner_community_reference_never_enters_a_draft(self):
        draft = self.store.draft_for_owner(OWNER_A)
        for source_key, source_revision in ((POST_KEY, "community:v8"), ("communityPost_456", "community:v7")):
            with self.subTest(source_key=source_key, source_revision=source_revision):
                with self.assertRaises(ProfileNotFound):
                    self.service.add_community_post_reference(
                        self.owner_a,
                        expected_version=draft.version,
                        source_key=source_key,
                        source_revision=source_revision,
                    )
        self.assertEqual(self.store.draft_for_owner(OWNER_A).placements, ())

    def test_hostile_preloaded_placement_cannot_be_reviewed_or_published(self):
        draft = self.store.draft_for_owner(OWNER_A)
        hostile_reference = CommunityPostReference(
            source_key=POST_KEY,
            source_revision="community:v7",
            canonical_path="https://attacker.example/profile",
            published_at=self.community_source.published_at,
        )
        hostile_draft = replace(
            draft,
            placements=(
                ProfilePlacementDraft(
                    placement_key="placement_hostile_123",
                    content_kind="community_post_reference",
                    destination="posts",
                    region="stream",
                    rank=0,
                    featured=False,
                    source_reference=hostile_reference,
                ),
            ),
        )
        self.store.put_draft(hostile_draft, expected_version=draft.version)

        with self.assertRaises(ProfileUnavailableError):
            self.service.review_publication(
                self.owner_a,
                expected_draft_version=hostile_draft.version,
                expected_public_revision=None,
            )
        with self.assertRaises(ProfileUnavailableError):
            self.service.publish_publication(
                self.owner_a,
                expected_draft_version=hostile_draft.version,
                expected_public_revision=None,
                candidate_digest="0" * 64,
                idempotency_key="publish-request-1014",
                confirmed=True,
            )
        self.assertIsNone(self.store.current_publication(OWNER_A))

    def test_changed_or_revoked_source_cannot_publish_and_preserves_prior_publication(self):
        for source_state in ("changed", "revoked"):
            with self.subTest(source_state=source_state):
                self.setUp()
                first = self._publish(key="publish-request-1015")
                draft = self.service.add_community_post_reference(
                    self.owner_a,
                    expected_version=self.store.draft_for_owner(OWNER_A).version,
                    source_key=POST_KEY,
                    source_revision="community:v7",
                    destination="posts",
                    region="stream",
                )
                review = self.service.review_publication(
                    self.owner_a,
                    expected_draft_version=draft.version,
                    expected_public_revision=first.revision.revision_key,
                )
                if source_state == "changed":
                    self.community_reader._current_revisions[(OWNER_A, POST_KEY)] = "community:v8"
                else:
                    del self.community_reader._records[(OWNER_A, POST_KEY, "community:v7")]

                with self.assertRaises(ProfileUnavailableError):
                    self.service.publish_publication(
                        self.owner_a,
                        expected_draft_version=draft.version,
                        expected_public_revision=first.revision.revision_key,
                        candidate_digest=review["candidate_digest"],
                        idempotency_key="publish-request-1016",
                        confirmed=True,
                    )
                self.assertEqual(self.store.current_publication(OWNER_A), first.revision)
                self.assertEqual(
                    self.service.public_read(slug="avery", destination="home").publication_revision,
                    first.revision.revision_key,
                )

    def test_malformed_nested_publication_manifest_is_neutral_and_owner_fail_closed(self):
        command = self._publish(key="publish-request-1017")
        revision = command.revision
        malformed_digest = replace(revision, digest="0" * 64)
        self.store._publications[OWNER_A] = malformed_digest
        with self.assertRaises(ProfileNotFound):
            self.service.public_read(slug="avery", destination="home")
        with self.assertRaises(ProfileUnavailableError):
            self.service.owner_state(self.owner_a)

        hostile_item = ProfilePublicationItem(
            placement_key="placement_hostile_456",
            content_kind="community_post_reference",
            destination="posts",
            region="stream",
            rank=0,
            featured=False,
            source_reference=CommunityPostReference(
                source_key=POST_KEY,
                source_revision="community:v7",
                canonical_path="/safe\\hostile",
                published_at=self.community_source.published_at,
            ),
        )
        self.store._publications[OWNER_A] = replace(revision, items=(hostile_item,))
        with self.assertRaises(ProfileNotFound):
            self.service.public_read(slug="avery", destination="posts")
        with self.assertRaises(ProfileUnavailableError):
            self.service.owner_state(self.owner_a)

    def test_malformed_idempotent_command_revision_is_never_returned(self):
        adversarial = AdversarialProfileStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        service = ProfileCoreService(adversarial, community_post_references=self.community_references)
        owner_a = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        draft = adversarial._drafts[OWNER_A]
        review = service.review_publication(
            owner_a, expected_draft_version=draft.version, expected_public_revision=None
        )
        command = service.publish_publication(
            owner_a,
            expected_draft_version=draft.version,
            expected_public_revision=None,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-1018",
            confirmed=True,
        )
        adversarial.foreign_command = replace(
            command, revision=replace(command.revision, digest="0" * 64)
        )
        with self.assertRaises(ProfileUnavailableError):
            service.publish_publication(
                owner_a,
                expected_draft_version=draft.version,
                expected_public_revision=None,
                candidate_digest=review["candidate_digest"],
                idempotency_key="publish-request-1018",
                confirmed=True,
            )

    def test_store_returning_bravo_draft_for_avery_is_neutral_absence(self):
        adversarial = AdversarialProfileStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        adversarial.foreign_draft = adversarial._drafts[OWNER_B]
        service = ProfileCoreService(
            adversarial, community_post_references=self.community_references
        )
        context = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        with self.assertRaises(ProfileNotFound):
            service.owner_state(context)
        with self.assertRaises(ProfileNotFound):
            service.update_native_draft(
                context,
                expected_version=adversarial.foreign_draft.version,
                identity={
                    "display_name": "Attempt", "headline": "No", "location": None, "summary": "No"
                },
            )

    def test_foreign_current_publication_is_neutral_public_absence_and_owner_fail_closed(self):
        adversarial = AdversarialProfileStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        service = ProfileCoreService(
            adversarial, community_post_references=self.community_references
        )
        owner_b = service.owner_context(
            actor_key=OWNER_B, subject_owner_key=OWNER_B, slug="bravo", purpose="test"
        )
        bravo_draft = adversarial._drafts[OWNER_B]
        review = service.review_publication(
            owner_b, expected_draft_version=bravo_draft.version, expected_public_revision=None
        )
        foreign_command = service.publish_publication(
            owner_b,
            expected_draft_version=bravo_draft.version,
            expected_public_revision=None,
            candidate_digest=review["candidate_digest"],
            idempotency_key="publish-request-1010",
            confirmed=True,
        )
        adversarial.foreign_publication = foreign_command.revision
        owner_a = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        with self.assertRaises(ProfileNotFound):
            service.public_read(slug="avery", destination="home")
        with self.assertRaises(ProfileUnavailableError):
            service.review_publication(
                owner_a,
                expected_draft_version=adversarial._drafts[OWNER_A].version,
                expected_public_revision=None,
            )

    def test_malformed_current_publication_fails_closed_for_publish_and_withdraw(self):
        adversarial = AdversarialProfileStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        service = ProfileCoreService(
            adversarial, community_post_references=self.community_references
        )
        owner_a = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        a_draft = adversarial._drafts[OWNER_A]
        review = service.review_publication(
            owner_a, expected_draft_version=a_draft.version, expected_public_revision=None
        )
        adversarial.foreign_publication = object()
        with self.assertRaises(ProfileUnavailableError):
            service.publish_publication(
                owner_a,
                expected_draft_version=a_draft.version,
                expected_public_revision=None,
                candidate_digest=review["candidate_digest"],
                idempotency_key="publish-request-1012",
                confirmed=True,
            )
        with self.assertRaises(ProfileUnavailableError):
            service.withdraw_publication(
                owner_a,
                expected_public_revision="v1:known",
                idempotency_key="publish-request-1013",
                confirmed=True,
            )

    def test_foreign_idempotent_command_is_never_returned(self):
        adversarial = AdversarialProfileStore([_draft(), _draft(OWNER_B, "bravo", "Bravo Member")])
        service = ProfileCoreService(
            adversarial, community_post_references=self.community_references
        )
        owner_b = service.owner_context(
            actor_key=OWNER_B, subject_owner_key=OWNER_B, slug="bravo", purpose="test"
        )
        bravo_draft = adversarial._drafts[OWNER_B]
        review_b = service.review_publication(
            owner_b, expected_draft_version=bravo_draft.version, expected_public_revision=None
        )
        foreign_command = service.publish_publication(
            owner_b,
            expected_draft_version=bravo_draft.version,
            expected_public_revision=None,
            candidate_digest=review_b["candidate_digest"],
            idempotency_key="publish-request-1011",
            confirmed=True,
        )
        adversarial.foreign_command = foreign_command
        owner_a = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        a_draft = adversarial._drafts[OWNER_A]
        review_a = service.review_publication(
            owner_a, expected_draft_version=a_draft.version, expected_public_revision=None
        )
        with self.assertRaises(ProfileUnavailableError):
            service.publish_publication(
                owner_a,
                expected_draft_version=a_draft.version,
                expected_public_revision=None,
                candidate_digest=review_a["candidate_digest"],
                idempotency_key="publish-request-1011",
                confirmed=True,
            )

    def test_atomic_store_expected_revision_allows_only_one_concurrent_winner(self):
        store = ConcurrentProfileStore([_draft()])
        service = ProfileCoreService(
            store, community_post_references=self.community_references
        )
        context = service.owner_context(
            actor_key=OWNER_A, subject_owner_key=OWNER_A, slug="avery", purpose="test"
        )
        draft = store._drafts[OWNER_A]
        review = service.review_publication(
            context, expected_draft_version=draft.version, expected_public_revision=None
        )
        with self.assertRaises(ProfileConflictError):
            service.publish_publication(
                context,
                expected_draft_version=draft.version,
                expected_public_revision=None,
                candidate_digest=review["candidate_digest"],
                idempotency_key="publish-request-2020",
                confirmed=True,
            )
        self.assertEqual(store.current_publication(OWNER_A).revision_key, "v1:competitor")
