"""Committed codec projection. Extra wording keys are dropped."""

from __future__ import annotations

import unittest
import copy

from services.resume_publication_contracts import decode_canonical_source
from services.resume_publication_projection import (
    canonical_fields_from_values,
    committed_source_bytes,
    publication_evidence_version,
    ordered_resume_display,
)


class ResumePublicationProjectionTests(unittest.TestCase):
    def test_one_shared_section_definition_uses_stored_kind_and_actual_story_binding(self):
        from services import resume_publication_projection as projection
        from services.resume_guide_contract import GUIDE_SECTION_ORDER
        classify = getattr(projection, "resume_section_for", None)
        self.assertTrue(callable(classify), "Guide and publication need one actual type/section definition")
        self.assertEqual(projection.RESUME_BASE_SECTION_ORDER, GUIDE_SECTION_ORDER)
        for kind, section in ((None, "certifications"), ("certification", "certifications"), ("license", "certifications"),
                              ("publication", "publications"), ("membership", "memberships")):
            self.assertEqual(classify("credential", {"qualification_kind": kind}), section)
        self.assertEqual(classify("knowledge", {"title": "My Story", "classification": "personal"}), "unplaced")
        self.assertEqual(classify("knowledge", {"title": "My Story", "classification": "personal"}, story_bound=True), "story")
        self.assertEqual(classify("knowledge", {"title": "Contact details", "classification": "work"}), "contact")
        self.assertEqual(classify("knowledge", {"classification": "work"}, presentation_section="Awards"), "awards")

    def test_core_order_is_fixed_and_optional_groups_follow_first_encounter_without_phantom_tabs(self):
        from services import resume_publication_projection as projection
        order = getattr(projection, "resume_section_order", None)
        self.assertTrue(callable(order))
        base = ("impact_statement", "skills", "experience", "projects", "education", "certifications", "awards")
        self.assertEqual(order([]), base)
        self.assertEqual(order(["memberships", "publications", "memberships"]), (*base, "memberships", "publications"))
        self.assertEqual(order(["memberships", "languages", "publications"]), (*base, "languages", "memberships", "publications"))
        display = {"role": {"canonical_type": "role", "wording": {"role_title": "Fictional engineer"}},
            "membership": {"canonical_type": "credential", "wording": {"qualification_kind": "membership"}},
            "skill": {"canonical_type": "skill", "wording": {"name": "Fictional skill"}},
            "publication": {"canonical_type": "credential", "wording": {"qualification_kind": "publication"}}}
        before = copy.deepcopy(display)
        self.assertEqual(list(projection.ordered_resume_display(display)), ["skill", "role", "membership", "publication"])
        self.assertEqual(display, before)

    def test_project_name_maps_to_the_existing_title_slot_without_expanding_codec_v1(self):
        values = {"project_name": "Fictional Orchard", "summary": "Fictional work."}
        before = copy.deepcopy(values)
        decoded = decode_canonical_source(committed_source_bytes("project", values))
        self.assertEqual(decoded["title"], "Fictional Orchard")
        self.assertEqual(values, before)

    def test_credential_projection_commits_independent_precision_without_changing_legacy_codec(self):
        dates={'issue_date':'2022-06-01','expiration_date':'2027-06-01'}
        for issue_precision,expiry_precision,issue,expiry in (
                ('month','month','2022-06','2027-06'),('year','day','2022','2027-06-01'),
                ('day','month','2022-06-01','2027-06')):
            values={**dates,'issue_date_precision':issue_precision,'expiration_date_precision':expiry_precision}
            if issue_precision=='year': values['issue_date']='2022-01-01'
            before=copy.deepcopy(values)
            decoded=decode_canonical_source(committed_source_bytes('credential',values))
            self.assertEqual((decoded['issue_date'],decoded['expiration_date']),(issue,expiry))
            self.assertEqual(values,before)
        self.assertEqual(committed_source_bytes('credential',dates),committed_source_bytes('credential',{
            **dates,'issue_date_precision':'day','expiration_date_precision':'day'}))
        self.assertNotEqual(committed_source_bytes('credential',dates),committed_source_bytes('credential',{
            **dates,'issue_date_precision':'month','expiration_date_precision':'month'}))
        with self.assertRaises(ValueError):
            committed_source_bytes('credential',{'issue_date':'2022-06-19','issue_date_precision':'month'})
        display={'old':{'canonical_type':'credential','wording':{'issue_date':'2020'}},
                 'recent':{'canonical_type':'credential','wording':{'issue_date':'2022-06'}}}
        self.assertEqual(list(ordered_resume_display(display)),['recent','old'])

    def test_order_uses_typed_dates_without_changing_values_or_inventing_unknowns(self):
        def role(**values): return {"canonical_type": "role", "wording": values}
        display = {
            "unknown-first": role(date_precision="unknown", start_date="2099-01-01", summary="Current since 2099"),
            "old": role(date_precision="year", start_date="1993-01-01", end_date="1996-01-01", current_role=False),
            "recent": role(date_precision="month", start_date="2016-06-01", end_date="2020-12-01", current_role=False),
            "current": role(date_precision="month", start_date="2021-01-01", current_role=True),
            "unknown-second": role(date_precision="unknown", current_role="true"),
            "education": {"canonical_type":"education", "wording":{"date_precision":"month", "end_date":"1993-06-01"}},
        }
        before = copy.deepcopy(display)
        ordered = ordered_resume_display(display)
        self.assertEqual(list(ordered), ["current", "recent", "old", "unknown-first", "unknown-second", "education"])
        self.assertEqual(ordered, before)
        self.assertEqual(display, before)
        self.assertIs(ordered["current"]["wording"]["current_role"], True)

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


from services.resume_publication_contracts import ContractError  # noqa: E402


class D6bProjectionV2Tests(unittest.TestCase):
    def test_v2_extras_are_carried_only_when_v1_cannot_say_them(self):
        base = {"name": "Fictional", "issuer": "Fictional Board", "issue_date": "2021-05-01"}
        plain = canonical_fields_from_values("credential", {"credential_name": "Fictional", "issuer_name": "Fictional Board",
                                                            "issue_date": "2021-05-01"})
        certification = canonical_fields_from_values("credential", {"credential_name": "Fictional",
            "issuer_name": "Fictional Board", "issue_date": "2021-05-01", "qualification_kind": "certification"})
        self.assertEqual(certification, plain)
        for kind in ("license", "publication", "membership"):
            fields = canonical_fields_from_values("credential", {"credential_name": "Fictional",
                "issuer_name": "Fictional Board", "issue_date": "2021-05-01", "qualification_kind": kind})
            self.assertEqual(fields["qualification_kind"], kind)
            self.assertTrue(committed_source_bytes("credential", {**base, "credential_name": "Fictional",
                "issuer_name": "Fictional Board", "qualification_kind": kind}).startswith(b"resume-canonical-source.v2"))
        with self.assertRaises(ContractError):
            canonical_fields_from_values("credential", {"credential_name": "x", "qualification_kind": "diploma"})
        project = {"project_name": "Fictional", "summary": "Fictional."}
        self.assertEqual(canonical_fields_from_values("project", {**project, "date_precision": "day",
                                                                  "additional_project_urls": []}),
                         canonical_fields_from_values("project", project))
        rich = canonical_fields_from_values("project", {**project, "project_category": "software",
            "organization_name": "Fictional Institute", "project_role": "Lead", "project_url": "https://a.test",
            "additional_project_urls": ["https://b.test"], "date_precision": "month"})
        self.assertEqual((rich["project_category"], rich["organization_name"], rich["project_role"], rich["project_url"],
                          rich["additional_project_urls"], rich["date_precision"]),
                         ("software", "Fictional Institute", "Lead", "https://a.test", ("https://b.test",), "month"))
        for bad in ({"date_precision": "decade"}, {"additional_project_urls": "https://b.test"},
                    {"project_category": 7}):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                canonical_fields_from_values("project", {**project, **bad})
        # Publication-only reference wording never enters the evidence codec.
        self.assertEqual(canonical_fields_from_values("skill", {"name": "Fictional", "published_evidence_refs": ["entry:k"]}),
                         canonical_fields_from_values("skill", {"name": "Fictional"}))

    def test_evidence_version_label_follows_its_bytes(self):
        common = dict(owner_key="owner", entry_key="entry", evidence_key="evidence:entry",
                      evidence_version_key="evidence:entry:1", version=1, canonical_token="1", policy_content_version=1,
                      access_revision=1, display_eligible=True, visitor_ai_eligible=False)
        plain = publication_evidence_version(canonical_type="project", values={"project_name": "Fictional"}, **common)
        rich = publication_evidence_version(canonical_type="project",
            values={"project_name": "Fictional", "project_role": "Lead"}, **common)
        self.assertEqual((plain.codec, rich.codec), ("resume-canonical-source.v1", "resume-canonical-source.v2"))
        self.assertEqual(decode_canonical_source(rich.content)["project_role"], "Lead")


if __name__ == "__main__":
    unittest.main()
