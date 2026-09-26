"""Committed codec projection. Extra wording keys are dropped."""

from __future__ import annotations

import unittest

from services.resume_publication_contracts import decode_canonical_source
from services.resume_publication_projection import (
    canonical_fields_from_values,
    committed_source_bytes,
    publication_evidence_version,
)


class ResumePublicationProjectionTests(unittest.TestCase):
    def test_skill_summary_alias_and_unknown_keys_are_dropped(self):
        fields = canonical_fields_from_values(
            "skill",
            {"name": "Python", "summary": "Built tools", "note": "private"},
        )
        self.assertEqual(fields["skill_summary"], "Built tools")
        self.assertIsNone(fields.get("note"))
        payload = committed_source_bytes("role", {"summary": "Led team", "note": "ignore"})
        decoded = decode_canonical_source(payload)
        self.assertEqual(decoded["summary"], "Led team")
        self.assertEqual(decoded["canonical_type"], "role")

    def test_evidence_digest_matches_actual_committed_bytes(self):
        versioned = publication_evidence_version(
            owner_key="member-a",
            entry_key="role:0",
            evidence_key="evidence:role:0",
            evidence_version_key="evidence:role:0:2",
            version=2,
            canonical_token="row-2",
            policy_content_version=3,
            access_revision=3,
            canonical_type="role",
            values={"summary": "Brand new wording."},
            display_eligible=True,
            visitor_ai_eligible=True,
        )
        again = committed_source_bytes("role", {"summary": "Brand new wording."})
        self.assertEqual(versioned.content, again)
        self.assertNotEqual(
            versioned.content_sha256,
            publication_evidence_version(
                owner_key="member-a",
                entry_key="role:0",
                evidence_key="evidence:role:0",
                evidence_version_key="evidence:role:0:1",
                version=1,
                canonical_token="row-1",
                policy_content_version=2,
                access_revision=2,
                canonical_type="role",
                values={"summary": "Old wording."},
                display_eligible=True,
                visitor_ai_eligible=True,
            ).content_sha256,
        )


if __name__ == "__main__":
    unittest.main()
