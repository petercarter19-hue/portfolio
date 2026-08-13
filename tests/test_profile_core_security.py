"""D0 Profile boundary and exact-reference security tests."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from services.profile_posts_adapter import (
    CommunityPostReferenceAdapter,
    EligibleCommunityPostSource,
    InMemoryCommunityPostSourceReader,
    ProfilePostReferenceNotFound,
    ProfilePostReferenceValidationError,
)


OWNER_A = "ownerAlpha_123"
OWNER_B = "ownerBravo_456"
POST_KEY = "communityPost_123"


class ProfilePostReferenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.source = EligibleCommunityPostSource(
            source_key=POST_KEY,
            owner_key=OWNER_A,
            source_revision="community:v7",
            canonical_path="/the-slate/posts/communityPost_123",
            published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        self.reader = InMemoryCommunityPostSourceReader(
            {(OWNER_A, POST_KEY, "community:v7"): self.source},
            {(OWNER_A, POST_KEY): "community:v7"},
        )
        self.adapter = CommunityPostReferenceAdapter(self.reader)

    def test_exact_owned_revision_becomes_a_reference_not_content(self):
        reference = self.adapter.reference_for(
            owner_key=OWNER_A,
            source_key=POST_KEY,
            source_revision="community:v7",
        )
        self.assertEqual(reference.source_key, POST_KEY)
        self.assertEqual(reference.canonical_path, self.source.canonical_path)
        self.assertFalse(hasattr(reference, "body"))
        self.assertFalse(hasattr(reference, "comments"))

    def test_cross_owner_reference_is_neutral_absence(self):
        with self.assertRaises(ProfilePostReferenceNotFound):
            self.adapter.reference_for(
                owner_key=OWNER_B,
                source_key=POST_KEY,
                source_revision="community:v7",
            )

    def test_revision_mismatch_is_neutral_absence(self):
        with self.assertRaises(ProfilePostReferenceNotFound):
            self.adapter.reference_for(
                owner_key=OWNER_A,
                source_key=POST_KEY,
                source_revision="community:v8",
            )

    def test_source_change_is_owner_safe_signal_not_auto_rewrite(self):
        reference = self.adapter.reference_for(
            owner_key=OWNER_A,
            source_key=POST_KEY,
            source_revision="community:v7",
        )
        self.reader._current_revisions[(OWNER_A, POST_KEY)] = "community:v8"
        status = self.adapter.source_status(owner_key=OWNER_A, reference=reference)
        self.assertEqual(status.state, "source_changed")
        self.assertEqual(reference.source_revision, "community:v7")

    def test_malformed_source_key_is_rejected_before_dependency_read(self):
        with self.assertRaises(ProfilePostReferenceValidationError):
            self.adapter.reference_for(
                owner_key=OWNER_A,
                source_key="../../private",
                source_revision="community:v7",
            )

    def test_external_or_escaped_canonical_paths_are_rejected_before_retention(self):
        for canonical_path in (
            "https://attacker.example/post",
            "//attacker.example/post",
            "/the-slate\\posts\\communityPost_123",
            "/the-slate/../private",
            "/the-slate/posts/communityPost_123?next=https://attacker.example",
            "/the-slate/posts/communityPost_123#attacker",
            "/the-slate/%2f%2fattacker.example",
        ):
            with self.subTest(canonical_path=canonical_path):
                source = EligibleCommunityPostSource(
                    source_key=POST_KEY,
                    owner_key=OWNER_A,
                    source_revision="community:v7",
                    canonical_path=canonical_path,
                    published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                )
                adapter = CommunityPostReferenceAdapter(
                    InMemoryCommunityPostSourceReader(
                        {(OWNER_A, POST_KEY, "community:v7"): source}
                    )
                )
                with self.assertRaises(ProfilePostReferenceValidationError):
                    adapter.reference_for(
                        owner_key=OWNER_A,
                        source_key=POST_KEY,
                        source_revision="community:v7",
                    )
