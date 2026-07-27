import copy
import json
import unittest
from pathlib import Path

from overview_projection_service import (
    BLOCK_DEFINITIONS,
    OverviewProjectionError,
    build_overview_projection,
    build_public_overview_projection,
    list_fixture_options,
    load_fixture_catalog,
)


class MemberOverviewProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_fixture_catalog()
        cls.fixture_ids = [
            option["id"]
            for option in list_fixture_options(cls.catalog)
        ]

    def assert_projection_error(self, expected_code, catalog, fixture_id="early-career"):
        with self.assertRaises(OverviewProjectionError) as raised:
            build_overview_projection(catalog, fixture_id, "story-career")
        self.assertEqual(raised.exception.code, expected_code)

    def fixture_catalog(self, fixture_id):
        catalog = copy.deepcopy(self.catalog)
        catalog["fixtures"] = [
            fixture
            for fixture in catalog["fixtures"]
            if fixture["fixture_id"] == fixture_id
        ]
        return catalog

    def test_required_generic_fixtures_render_in_both_styles(self):
        self.assertEqual(
            self.fixture_ids,
            [
                "early-career",
                "career-changer",
                "experienced-leader",
                "independent-creative",
                "text-only",
            ],
        )
        for fixture_id in self.fixture_ids:
            story = build_overview_projection(
                self.catalog,
                fixture_id,
                "story-career",
            )
            work = build_overview_projection(
                self.catalog,
                fixture_id,
                "work-impact",
            )
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(story["readiness"], {"state": "ready", "errors": []})
                self.assertEqual(story["semantic_block_ids"], work["semantic_block_ids"])
                self.assertEqual(story["blocks"][0]["definition_id"], "identity_hero")
                self.assertEqual(
                    story["blocks"][-1]["definition_id"],
                    "resume_transition",
                )
                self.assertEqual(
                    story["semantic_block_ids"].count("identity_hero"),
                    1,
                )

    def test_count_aware_states_are_deterministic(self):
        expected = {
            "early-career": (0, "omitted", 1, "Career Focus", 1),
            "career-changer": (0, "omitted", 3, "Experience", 1),
            "experienced-leader": (4, "equal-four", 4, "Experience", 2),
            "independent-creative": (0, "omitted", 2, "Experience", 0),
            "text-only": (2, "pair", 2, "Experience", 1),
        }
        for fixture_id, state in expected.items():
            projection = build_overview_projection(
                self.catalog,
                fixture_id,
                "story-career",
            )
            layout = projection["layout"]
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(
                    (
                        layout["proof_count"],
                        layout["proof_variant"],
                        layout["career_count"],
                        layout["career_heading"],
                        layout["education_count"],
                    ),
                    state,
                )

    def test_styles_and_versions_fail_explicitly(self):
        with self.assertRaises(OverviewProjectionError) as raised:
            build_overview_projection(self.catalog, "early-career", "unknown")
        self.assertEqual(raised.exception.code, "unsupported_style")

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"][0]["definition_version"] = 999
        self.assert_projection_error(
            "unsupported_block_version",
            catalog,
        )

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"][0]["definition_id"] = "custom_html"
        self.assert_projection_error("unsupported_block", catalog)

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"][1]["emphasis"] = "cinematic"
        self.assert_projection_error("unsupported_emphasis", catalog)

    def test_order_placement_and_collection_budgets_fail_explicitly(self):
        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"][1]["order"] = 5
        self.assert_projection_error("invalid_order", catalog)

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"][1]["placement_id"] = "early-hero"
        self.assert_projection_error("duplicate_placement_id", catalog)

        catalog = self.fixture_catalog("experienced-leader")
        proof = catalog["fixtures"][0]["blocks"][1]
        fifth = copy.deepcopy(proof["content"]["claims"][-1])
        fifth["value"] = "5"
        fifth["order"] = 5
        proof["content"]["claims"].append(fifth)
        self.assert_projection_error(
            "collection_budget_exceeded",
            catalog,
            "experienced-leader",
        )

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["blocks"] = (
            catalog["fixtures"][0]["blocks"] * 4
        )
        self.assert_projection_error("block_budget_exceeded", catalog)

    def test_proof_claims_reject_provenance_and_unknown_fields(self):
        for forbidden_field in (
            "source",
            "evidence",
            "verification",
            "confidence",
            "provenance",
            "provenance_state",
        ):
            catalog = self.fixture_catalog("experienced-leader")
            claim = catalog["fixtures"][0]["blocks"][1]["content"]["claims"][0]
            claim[forbidden_field] = "not allowed"
            with self.subTest(forbidden_field=forbidden_field):
                self.assert_projection_error(
                    "forbidden_proof_field",
                    catalog,
                    "experienced-leader",
                )

        catalog = self.fixture_catalog("experienced-leader")
        catalog["fixtures"][0]["blocks"][1]["content"]["claims"][0]["badge"] = "new"
        self.assert_projection_error(
            "unsupported_proof_field",
            catalog,
            "experienced-leader",
        )

    def test_unknown_destinations_fail_explicitly(self):
        catalog = self.fixture_catalog("experienced-leader")
        catalog["fixtures"][0]["blocks"][2]["destination"] = {
            "kind": "route",
            "value": "/somewhere",
        }
        self.assert_projection_error(
            "unknown_destination",
            catalog,
            "experienced-leader",
        )

        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["profile"]["contact_destination"] = {
            "kind": "anchor",
            "value": "#missing",
        }
        self.assert_projection_error("unknown_destination", catalog)

    def test_cross_owner_records_and_media_fail_closed(self):
        catalog = self.fixture_catalog("early-career")
        catalog["fixtures"][0]["records"][0]["owner_key"] = "another-owner"
        self.assert_projection_error("cross_owner_reference", catalog)

        catalog = self.fixture_catalog("experienced-leader")
        catalog["fixtures"][0]["media"][0]["owner_key"] = "another-owner"
        self.assert_projection_error(
            "cross_owner_reference",
            catalog,
            "experienced-leader",
        )

    def test_fixture_owner_identifiers_never_overlap(self):
        seen_records = set()
        seen_media = set()
        owners = set()
        for fixture in self.catalog["fixtures"]:
            owner = fixture["owner_key"]
            self.assertNotIn(owner, owners)
            owners.add(owner)
            record_ids = {record["id"] for record in fixture["records"]}
            media_ids = {media["id"] for media in fixture["media"]}
            self.assertFalse(seen_records.intersection(record_ids))
            self.assertFalse(seen_media.intersection(media_ids))
            self.assertTrue(
                all(record["owner_key"] == owner for record in fixture["records"])
            )
            self.assertTrue(
                all(media["owner_key"] == owner for media in fixture["media"])
            )
            seen_records.update(record_ids)
            seen_media.update(media_ids)

    def test_missing_optional_groups_and_media_leave_no_projection_block(self):
        early = build_overview_projection(
            self.catalog,
            "early-career",
            "story-career",
        )
        self.assertNotIn("proof_band", early["block_by_definition"])
        self.assertNotIn("awards", early["block_by_definition"])
        self.assertFalse(early["layout"]["has_media"])
        self.assertTrue(all(not block["media"] for block in early["blocks"]))

        catalog = self.fixture_catalog("text-only")
        proof = catalog["fixtures"][0]["blocks"][1]
        for claim in proof["content"]["claims"]:
            claim["visible"] = False
        projection = build_overview_projection(
            catalog,
            "text-only",
            "story-career",
        )
        self.assertNotIn("proof_band", projection["block_by_definition"])
        self.assertEqual(projection["layout"]["proof_variant"], "omitted")

    def test_skills_must_precede_credentials(self):
        catalog = self.fixture_catalog("early-career")
        blocks = catalog["fixtures"][0]["blocks"]
        blocks[2], blocks[3] = blocks[3], blocks[2]
        blocks[2]["order"], blocks[3]["order"] = 50, 60
        self.assert_projection_error("invalid_semantic_order", catalog)

    def test_contract_is_finite_and_contains_no_custom_html_block(self):
        self.assertNotIn("custom_html", BLOCK_DEFINITIONS)
        fixture_text = (
            Path(__file__).resolve().parents[1]
            / "static/data/overview_fixtures.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Pete Carter", fixture_text)
        self.assertNotIn('"source"', fixture_text)
        self.assertNotIn('"provenance"', fixture_text)

    def test_profile_owned_publication_resolves_against_public_resume_data(self):
        resume_data = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "static/data/resume_data.json"
            ).read_text(encoding="utf-8")
        )

        projection = build_public_overview_projection(resume_data)

        self.assertEqual(
            projection["publication"],
            {
                "schema_version": "member-overview-publication.v1",
                "state": "published",
                "profile_slug": "petec",
                "revision": 1,
            },
        )
        self.assertNotIn("fixture", projection)
        self.assertEqual(projection["style"]["id"], "story-career")
        self.assertEqual(projection["profile"]["display_name"], "Pete Carter")
        self.assertEqual(
            [
                claim["value"]
                for claim in projection["block_by_definition"]["proof_band"][
                    "content"
                ]["claims"]
            ],
            ["30+", "9 / $19.2M", "35%", "70%"],
        )
        for claim in projection["block_by_definition"]["proof_band"]["content"][
            "claims"
        ]:
            self.assertFalse(
                {
                    "source",
                    "source_id",
                    "evidence",
                    "verification",
                    "provenance",
                }.intersection(claim)
            )

    def test_absent_or_nonpublished_selection_returns_summary_fallback_state(self):
        resume_data = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "static/data/resume_data.json"
            ).read_text(encoding="utf-8")
        )

        no_selection = copy.deepcopy(resume_data)
        no_selection.pop("overview_publication")
        self.assertIsNone(build_public_overview_projection(no_selection))

        draft_selection = copy.deepcopy(resume_data)
        draft_selection["overview_publication"]["state"] = "draft"
        self.assertIsNone(build_public_overview_projection(draft_selection))

    def test_invalid_publication_references_and_media_paths_fail_closed(self):
        resume_data = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "static/data/resume_data.json"
            ).read_text(encoding="utf-8")
        )

        unknown_metric = copy.deepcopy(resume_data)
        unknown_metric["overview_publication"]["blocks"][1]["metric_ids"][0] = (
            "another-owner:metric"
        )
        with self.assertRaises(OverviewProjectionError) as raised:
            build_public_overview_projection(unknown_metric)
        self.assertEqual(raised.exception.code, "unknown_metric")

        unsafe_media = copy.deepcopy(resume_data)
        unsafe_media["overview_publication"]["media"][0]["asset_path"] = (
            "../private/headshot.jpg"
        )
        with self.assertRaises(OverviewProjectionError) as raised:
            build_public_overview_projection(unsafe_media)
        self.assertEqual(raised.exception.code, "invalid_media_path")

        invalid_role = copy.deepcopy(resume_data)
        invalid_role["career_roles"][0]["accomplishments"] = "not-a-list"
        with self.assertRaises(OverviewProjectionError) as raised:
            build_public_overview_projection(invalid_role)
        self.assertEqual(
            raised.exception.code,
            "invalid_accomplishment_collection",
        )

    def test_shared_projection_service_contains_no_pete_content(self):
        service_text = (
            Path(__file__).resolve().parents[1]
            / "overview_projection_service.py"
        ).read_text(encoding="utf-8")
        for profile_specific_text in (
            "Pete Carter",
            "Northrop Grumman",
            "L3Harris",
            "Department of Defense",
        ):
            self.assertNotIn(profile_specific_text, service_text)


if __name__ == "__main__":
    unittest.main()
