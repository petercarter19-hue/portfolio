import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-work-impact-key")

import app as app_module  # noqa: E402
from overview_projection_service import (  # noqa: E402
    OverviewProjectionError,
    build_public_overview_projection,
)


ROOT = Path(__file__).resolve().parents[1]


def load_resume_data():
    return json.loads(
        (ROOT / "static/data/resume_data.json").read_text(encoding="utf-8")
    )


def load_work_impact_data():
    return app_module._apply_overview_style_presentation(
        load_resume_data(),
        "work-impact",
    )


def build_work_impact_projection(resume_data=None):
    return build_public_overview_projection(
        resume_data or load_work_impact_data(),
        style_override="work-impact",
    )


class WorkImpactProjectionTests(unittest.TestCase):
    def test_profile_owned_work_impact_projection_resolves_public_content(self):
        projection = build_work_impact_projection()

        self.assertEqual(projection["style"]["id"], "work-impact")
        self.assertEqual(
            [
                claim["value"]
                for claim in projection["block_by_definition"]["proof_band"][
                    "content"
                ]["claims"]
            ],
            ["30+", "9 / $19.2M", "$36M+", "35%"],
        )
        self.assertEqual(
            [section["id"] for section in projection["work_impact"]["sections"]],
            [
                "systems-requirements",
                "technical-leadership",
                "measurable-impact",
                "sustainment-lifecycle",
                "data-automation-ai",
                "person-behind-work",
                "building-toward",
            ],
        )
        self.assertEqual(
            [section["kind"] for section in projection["work_impact"]["sections"]],
            [
                "feature",
                "feature",
                "outcomes",
                "feature",
                "feature",
                "feature",
                "feature",
            ],
        )
        self.assertEqual(
            [
                metric["value"]
                for metric in projection["work_impact"]["sections"][2]["metrics"]
            ],
            ["$4.6M", "70%", "52%", "$9.1M"],
        )
        self.assertEqual(
            projection["work_impact"]["sections"][3]["media"]["truth_label"],
            "AI-generated illustrative sustainment scene",
        )
        self.assertEqual(
            projection["work_impact"]["hero"]["media"]["src"],
            (
                "/static/images/overview/"
                "work-impact-hero-pete-ai-extended-2026-07-28.webp"
            ),
        )
        self.assertEqual(
            projection["work_impact"]["sections"][1]["media"]["src"],
            (
                "/static/images/overview/"
                "work-impact-leadership-meeting-2026-07-28.webp"
            ),
        )

    def test_work_impact_projection_contains_no_source_or_owner_identifiers(self):
        projection = build_work_impact_projection()
        serialized = json.dumps(projection["work_impact"])

        for private_field in (
            '"source_id"',
            '"owner_key"',
            '"metric_ids"',
            '"media_id"',
            '"skill_ids"',
        ):
            self.assertNotIn(private_field, serialized)

    def test_optional_summary_collections_can_collapse_without_placeholder_data(self):
        resume_data = load_work_impact_data()
        summary = resume_data["overview_publication"]["style_presentations"][
            "work-impact"
        ]["summary"]
        summary["education_ids"] = []
        summary["certification_ids"] = []
        summary["award_ids"] = []

        projection = build_work_impact_projection(resume_data)

        self.assertEqual(projection["work_impact"]["summary"]["education"], [])
        self.assertEqual(
            projection["work_impact"]["summary"]["certifications"],
            [],
        )
        self.assertEqual(projection["work_impact"]["summary"]["awards"], [])

    def test_unknown_work_impact_metric_and_media_fail_closed(self):
        unknown_metric = load_work_impact_data()
        unknown_metric["overview_publication"]["style_presentations"]["work-impact"][
            "sections"
        ][2]["metric_ids"][0] = "not-this-profile"
        with self.assertRaises(OverviewProjectionError) as raised:
            build_work_impact_projection(unknown_metric)
        self.assertEqual(raised.exception.code, "unknown_metric")

        unknown_media = load_work_impact_data()
        unknown_media["overview_publication"]["style_presentations"]["work-impact"][
            "sections"
        ][0]["media_id"] = "private-diagram"
        with self.assertRaises(OverviewProjectionError) as raised:
            build_work_impact_projection(unknown_media)
        self.assertEqual(raised.exception.code, "unknown_media")

    def test_public_static_resume_data_contains_no_work_impact_draft(self):
        raw_public_data = (
            ROOT / "static/data/resume_data.json"
        ).read_text(encoding="utf-8")

        self.assertNotIn("work-impact-presentation.v1", raw_public_data)
        self.assertNotIn("work-impact-hero-pete-ai-extended", raw_public_data)

    def test_publication_overlay_and_static_assets_are_release_inputs(self):
        publication_path = (
            ROOT
            / "docs/initiatives/PS-OVERVIEW-001/work-impact-fidelity"
            / "fixtures/work-impact-publication.json"
        )
        publication = json.loads(publication_path.read_text(encoding="utf-8"))

        self.assertEqual(
            publication["schema_version"],
            "work-impact-publication-overlay.v1",
        )
        for media in publication["media"]:
            self.assertTrue(media["public_eligible"])
            asset_path = ROOT / "static" / media["asset_path"]
            self.assertTrue(asset_path.is_file(), asset_path)

    def test_renderer_files_do_not_hardcode_fixture_identity_or_employers(self):
        renderer_text = "\n".join(
            (
                (ROOT / "overview_projection_service.py").read_text(encoding="utf-8"),
                (
                    ROOT / "templates/partials/member_overview_work_impact.html"
                ).read_text(encoding="utf-8"),
            )
        )
        for fixture_text in (
            "Pete Carter",
            "Northrop Grumman",
            "L3Harris",
            "Department of Defense",
        ):
            self.assertNotIn(fixture_text, renderer_text)


class WorkImpactStyleSwitchRouteTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def test_local_comparison_renders_both_real_profile_styles(self):
        story = self.client.get(
            "/_internal/living-resume-v2?overviewStyle=story-career",
            base_url="http://localhost",
        )
        work = self.client.get(
            "/_internal/living-resume-v2?overviewStyle=work-impact",
            base_url="http://localhost",
        )

        self.assertEqual(story.status_code, 200)
        self.assertEqual(work.status_code, 200)
        self.assertIn(b'data-style-id="story-career"', story.data)
        self.assertIn(b'data-style-id="work-impact"', work.data)
        self.assertIn(b"Choose Overview style", story.data)
        self.assertIn(b"Choose Overview style", work.data)
        self.assertIn(b"Systems Engineering &amp; Requirements", work.data)
        self.assertIn(b"Measurable Impact", work.data)
        self.assertIn(
            b"work-impact-hero-pete-ai-extended-2026-07-28.webp",
            work.data,
        )
        self.assertIn(
            b"work-impact-leadership-meeting-2026-07-28.webp",
            work.data,
        )
        self.assertIn(
            b"work-impact-sustainment-aircraft-2026-07-28.webp",
            work.data,
        )
        self.assertIn(
            b"work-impact-data-ai-dashboard-2026-07-28.webp",
            work.data,
        )
        self.assertIn(
            b"AI-generated presentation derivative",
            work.data,
        )

    def test_capture_mode_keeps_the_real_member_style_switch(self):
        response = self.client.get(
            "/_internal/living-resume-v2?overviewStyle=work-impact&capture=1",
            base_url="http://localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose Overview style", response.data)
        self.assertIn(b'data-style-id="work-impact"', response.data)

    def test_invalid_style_and_nonlocal_comparison_fail_closed(self):
        invalid = self.client.get(
            "/_internal/living-resume-v2?overviewStyle=unknown",
            base_url="http://localhost",
        )
        nonlocal_response = self.client.get(
            "/_internal/living-resume-v2?overviewStyle=work-impact",
            base_url="https://peerslate.com",
        )

        self.assertEqual(invalid.status_code, 404)
        self.assertEqual(nonlocal_response.status_code, 404)

    def test_selected_work_impact_media_is_public_static_content(self):
        filename = "work-impact-leadership-meeting-2026-07-28.webp"
        static_response = self.client.get(
            f"/static/images/overview/{filename}",
            base_url="http://localhost",
        )

        self.assertEqual(static_response.status_code, 200)
        self.assertEqual(static_response.content_type, "image/webp")

    def test_internal_projection_errors_fail_loudly_without_story_fallback(self):
        with patch.object(
            app_module,
            "build_public_overview_projection",
            side_effect=OverviewProjectionError("unknown_media", "broken preview"),
        ):
            response = self.client.get(
                "/_internal/living-resume-v2?overviewStyle=work-impact&capture=1",
                base_url="http://localhost",
            )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'data-style-id="story-career"', response.data)

    def test_public_page_switch_renders_either_style(self):
        default_response = self.client.get(
            "/petec/resume",
            base_url="http://localhost",
        )
        story_response = self.client.get(
            "/petec/resume?overviewStyle=story-career",
            base_url="http://localhost",
        )
        work_response = self.client.get(
            "/petec/resume?overviewStyle=work-impact",
            base_url="http://localhost",
        )

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(story_response.status_code, 200)
        self.assertEqual(work_response.status_code, 200)
        self.assertIn(b'data-style-id="story-career"', default_response.data)
        self.assertIn(b'data-style-id="story-career"', story_response.data)
        self.assertIn(b'data-style-id="work-impact"', work_response.data)
        self.assertNotIn(b'data-style-id="story-career"', work_response.data)
        self.assertIn(
            b"/petec/resume?overviewStyle=story-career#overview",
            work_response.data,
        )
        self.assertIn(
            b"/petec/resume?overviewStyle=work-impact#overview",
            story_response.data,
        )

    def test_invalid_public_style_falls_back_to_published_default(self):
        response = self.client.get(
            "/petec/resume?overviewStyle=unknown",
            base_url="http://localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-style-id="story-career"', response.data)
        self.assertNotIn(b'data-style-id="work-impact"', response.data)


class WorkImpactResponsiveGeometryTests(unittest.TestCase):
    def test_shared_overview_shell_widens_both_styles_by_fifteen_percent(self):
        css = (ROOT / "static/css/resume2.css").read_text(encoding="utf-8")
        selector = ".resume-v2[data-public-overview] .r2-page-grid {"
        start = css.index(selector)
        block = css[start : css.index("}", start) + 1]

        self.assertIn("width: min(calc(100% - 2rem), 103rem);", block)
        self.assertIn(
            "grid-template-columns: 10rem minmax(0, 1fr) 20rem;",
            block,
        )

    def test_work_impact_mobile_breakpoint_releases_fixed_desktop_heights(self):
        css = (
            ROOT / "static/css/member-overview-work-impact.css"
        ).read_text(encoding="utf-8")
        mobile_start = css.index("@media (max-width: 60rem)")
        mobile_end = css.index("@media (max-width: 46.5rem)", mobile_start)
        mobile = css[mobile_start:mobile_end]

        self.assertIn(
            ".work-impact-hero {\n        height: auto;\n        min-height: 0;",
            mobile,
        )
        self.assertIn(
            ".work-impact-proof {\n        height: auto;\n        min-height: 0;",
            mobile,
        )


if __name__ == "__main__":
    unittest.main()
