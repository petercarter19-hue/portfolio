import unittest
import xml.etree.ElementTree as ET

from services.response_policy import (
    MEMBER_PUBLICATION_CACHE_CONTROL,
    PUBLIC_RESUME_DATA_STATIC_FILENAME,
    PUBLIC_RESUME_PDF_STATIC_FILENAME,
    PUBLIC_STATIC_FALLBACK_CACHE_CONTROL,
    PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL,
    QUIET_PREVIEW_X_ROBOTS_TAG,
    empty_sitemap_xml,
    is_quiet_preview_response,
    resolve_response_policy,
    robots_txt,
)


class QuietPreviewClassificationTests(unittest.TestCase):
    def test_member_publication_cache_is_private_no_store(self):
        self.assertEqual(MEMBER_PUBLICATION_CACHE_CONTROL, "private, no-store")

    def test_every_public_html_response_is_selected_by_mimetype(self):
        for request_path in (
            "/",
            "/petec/resume",
            "/alice/resume",
            "/not-found",
            "/application",
        ):
            with self.subTest(request_path=request_path):
                self.assertTrue(
                    is_quiet_preview_response(
                        request_path,
                        response_mimetype="text/html",
                    )
                )

    def test_private_app_html_namespace_is_not_selected(self):
        for request_path in ("/app", "/app/", "/app/settings"):
            with self.subTest(request_path=request_path):
                self.assertFalse(
                    is_quiet_preview_response(
                        request_path,
                        response_mimetype="text/html",
                    )
                )

    def test_non_html_is_not_selected_without_an_exact_static_resource(self):
        for response_mimetype in (
            None,
            "application/json",
            "application/pdf",
            "text/plain",
        ):
            with self.subTest(response_mimetype=response_mimetype):
                self.assertFalse(
                    is_quiet_preview_response(
                        "/petec/resume",
                        response_mimetype=response_mimetype,
                    )
                )

    def test_html_mimetype_parameters_and_case_are_accepted(self):
        self.assertTrue(
            is_quiet_preview_response(
                "/",
                response_mimetype="Text/HTML; charset=UTF-8",
            )
        )

    def test_only_exact_canonical_resume_resource_filenames_are_selected(self):
        for filename in (
            PUBLIC_RESUME_DATA_STATIC_FILENAME,
            PUBLIC_RESUME_PDF_STATIC_FILENAME,
        ):
            with self.subTest(filename=filename):
                self.assertTrue(
                    is_quiet_preview_response(
                        "/static/anything",
                        response_mimetype="application/octet-stream",
                        canonical_static_filename=filename,
                    )
                )

        for lookalike, response_mimetype in (
            ("/data/resume_data.json", "application/json"),
            ("data/./resume_data.json", "application/json"),
            ("data/RESUME_DATA.json", "application/json"),
            ("data/resume_data.json?download=1", "application/json"),
            ("data/other.json", "application/json"),
            ("files/pete-carter-resume.pdf/extra", "application/pdf"),
            ("files/other-resume.pdf", "application/pdf"),
        ):
            with self.subTest(filename=lookalike):
                self.assertFalse(
                    is_quiet_preview_response(
                        "/static/anything",
                        response_mimetype=response_mimetype,
                        canonical_static_filename=lookalike,
                    )
                )

        self.assertFalse(
            is_quiet_preview_response(
                "/static/data/resume_data.json",
                response_mimetype="application/json",
            )
        )


class ResponsePolicyResolutionTests(unittest.TestCase):
    def test_selected_html_pdf_and_json_receive_noindex_guidance(self):
        cases = (
            {"request_path": "/", "response_mimetype": "text/html"},
            {
                "request_path": "/alice/resume",
                "response_mimetype": "text/html",
            },
            {
                "request_path": "/not-found",
                "response_mimetype": "text/html",
                "status_code": 404,
            },
            {
                "request_path": "/static/data/resume_data.json",
                "response_mimetype": "application/json",
                "canonical_static_filename": (
                    PUBLIC_RESUME_DATA_STATIC_FILENAME
                ),
            },
            {
                "request_path": "/static/files/pete-carter-resume.pdf",
                "response_mimetype": "application/pdf",
                "canonical_static_filename": (
                    PUBLIC_RESUME_PDF_STATIC_FILENAME
                ),
            },
        )

        for case in cases:
            with self.subTest(case=case):
                policy = resolve_response_policy(**case)
                self.assertEqual(
                    policy.x_robots_tag,
                    QUIET_PREVIEW_X_ROBOTS_TAG,
                )

    def test_existing_robots_header_is_preserved_exactly(self):
        existing = "noindex, nofollow"

        policy = resolve_response_policy(
            "/",
            response_mimetype="text/html",
            existing_x_robots_tag=existing,
        )

        self.assertEqual(policy.x_robots_tag, existing)

    def test_selected_response_adds_noindex_to_other_existing_restrictions(self):
        policy = resolve_response_policy(
            "/",
            response_mimetype="text/html",
            existing_x_robots_tag="unavailable_after: 31 Dec 2026, index",
        )

        self.assertIn("unavailable_after: 31 Dec 2026", policy.x_robots_tag)
        self.assertIn("noindex", policy.x_robots_tag)
        self.assertNotIn(", index", policy.x_robots_tag)

    def test_private_app_and_non_html_responses_do_not_gain_robots_header(self):
        cases = (
            resolve_response_policy("/app", response_mimetype="text/html"),
            resolve_response_policy(
                "/app/settings",
                response_mimetype="text/html",
            ),
            resolve_response_policy(
                "/ordinary.json",
                response_mimetype="application/json",
            ),
        )

        for policy in cases:
            self.assertIsNone(policy.x_robots_tag)

    def test_private_app_preserves_an_existing_stricter_robots_header(self):
        existing = "noindex, nofollow"

        policy = resolve_response_policy(
            "/app/settings",
            response_mimetype="text/html",
            existing_x_robots_tag=existing,
        )

        self.assertEqual(policy.x_robots_tag, existing)

    def test_exact_current_resume_pdf_is_never_immutable(self):
        policy = resolve_response_policy(
            "/static/files/pete-carter-resume.pdf",
            response_mimetype="application/pdf",
            canonical_static_filename=PUBLIC_RESUME_PDF_STATIC_FILENAME,
            static_cache_eligible=True,
            requested_static_version="abc123",
            current_static_version="abc123",
            existing_cache_control=PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL,
        )

        self.assertEqual(
            policy.cache_control,
            PUBLIC_STATIC_FALLBACK_CACHE_CONTROL,
        )
        self.assertNotIn("immutable", policy.cache_control)
        self.assertNotIn("31536000", policy.cache_control)

    def test_resume_pdf_preserves_an_existing_stricter_cache_policy(self):
        for existing in (
            "no-cache, must-revalidate",
            "public, max-age=60",
        ):
            with self.subTest(existing=existing):
                policy = resolve_response_policy(
                    "/static/files/pete-carter-resume.pdf",
                    response_mimetype="application/pdf",
                    canonical_static_filename=PUBLIC_RESUME_PDF_STATIC_FILENAME,
                    static_cache_eligible=True,
                    requested_static_version="abc123",
                    current_static_version="abc123",
                    existing_cache_control=existing,
                )
                self.assertEqual(policy.cache_control, existing)

    def test_private_no_store_and_no_transform_always_take_precedence(self):
        for existing in (
            "private, no-store",
            "no-store, max-age=0",
            "public, max-age=31536000, no-transform",
        ):
            with self.subTest(existing=existing):
                policy = resolve_response_policy(
                    "/static/files/pete-carter-resume.pdf",
                    response_mimetype="application/pdf",
                    canonical_static_filename=PUBLIC_RESUME_PDF_STATIC_FILENAME,
                    static_cache_eligible=True,
                    requested_static_version="abc123",
                    current_static_version="abc123",
                    existing_cache_control=existing,
                )
                self.assertEqual(policy.cache_control, existing)

    def test_exact_current_application_asset_remains_immutable(self):
        policy = resolve_response_policy(
            "/static/css/style.css",
            response_mimetype="text/css",
            canonical_static_filename="css/style.css",
            static_cache_eligible=True,
            requested_static_version="abc123",
            current_static_version="abc123",
        )

        self.assertEqual(
            policy.cache_control,
            PUBLIC_STATIC_IMMUTABLE_CACHE_CONTROL,
        )

    def test_missing_stale_or_wrong_asset_version_uses_bounded_cache(self):
        cases = (
            (None, "abc123"),
            ("", "abc123"),
            ("stale", "abc123"),
            ("abc123", None),
        )

        for requested, current in cases:
            with self.subTest(requested=requested, current=current):
                policy = resolve_response_policy(
                    "/static/css/style.css",
                    response_mimetype="text/css",
                    canonical_static_filename="css/style.css",
                    static_cache_eligible=True,
                    requested_static_version=requested,
                    current_static_version=current,
                )
                self.assertEqual(
                    policy.cache_control,
                    PUBLIC_STATIC_FALLBACK_CACHE_CONTROL,
                )

    def test_non_success_and_noneligible_responses_keep_cache_policy(self):
        existing = "public, max-age=120"
        cases = (
            resolve_response_policy(
                "/static/css/style.css",
                response_mimetype="text/css",
                canonical_static_filename="css/style.css",
                status_code=304,
                static_cache_eligible=True,
                requested_static_version="abc123",
                current_static_version="abc123",
                existing_cache_control=existing,
            ),
            resolve_response_policy(
                "/ordinary",
                response_mimetype="text/plain",
                existing_cache_control=existing,
            ),
        )

        for policy in cases:
            self.assertEqual(policy.cache_control, existing)


class CrawlDocumentTests(unittest.TestCase):
    def test_robots_keeps_public_crawlability_and_private_exclusions(self):
        body = robots_txt()

        self.assertTrue(body.endswith("\n"))
        self.assertIn("User-agent: *\n", body)
        self.assertIn("Allow: /\n", body)
        for path in (
            "/app",
            "/api/",
            "/owner",
            "/the-slate",
            "/interview-studio",
        ):
            with self.subTest(path=path):
                self.assertIn(f"Disallow: {path}\n", body)
        self.assertNotIn("Sitemap:", body)

    def test_sitemap_is_valid_and_empty(self):
        body = empty_sitemap_xml()
        root = ET.fromstring(body)

        self.assertEqual(
            root.tag,
            "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset",
        )
        self.assertEqual(list(root), [])
        self.assertNotIn("<loc>", body)


if __name__ == "__main__":
    unittest.main()
