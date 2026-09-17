"""Regression guards for the published Pete Carter résumé PDF."""

import hashlib
import re
import unittest
from io import BytesIO

from pypdf import PdfReader

from app import app
from scripts.generate_public_resume_pdf import OUTPUT, RESUME_LINES, build_pdf


ACCEPTED_TEXT_SHA256 = "37dba960e88d8ee55b8e5a25f08a26856522fc6fdf8f1974fa9fcc26c3eee2a4"
QUIET_PREVIEW_X_ROBOTS_TAG = "noindex, nofollow, noarchive, noimageindex"


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class PublicResumePdfTests(unittest.TestCase):
    def test_checked_in_pdf_is_reproducible_and_structurally_valid(self):
        published = OUTPUT.read_bytes()
        self.assertEqual(published, build_pdf())
        self.assertEqual(published, build_pdf())

        reader = PdfReader(BytesIO(published), strict=True)
        self.assertEqual(len(reader.pages), 1)
        self.assertEqual(float(reader.pages[0].mediabox.width), 612)
        self.assertEqual(float(reader.pages[0].mediabox.height), 792)

    def test_every_accepted_word_is_present_in_the_same_order(self):
        source_text = normalized_text(" ".join(RESUME_LINES))
        extracted = normalized_text(
            PdfReader(BytesIO(OUTPUT.read_bytes()), strict=True).pages[0].extract_text()
        )
        self.assertEqual(
            hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            ACCEPTED_TEXT_SHA256,
        )
        self.assertEqual(extracted, source_text)

    def test_public_download_serves_exact_pdf_with_quiet_bounded_policy(self):
        published = OUTPUT.read_bytes()
        version = hashlib.sha256(published).hexdigest()[:12]
        client = app.test_client()

        for suffix in ("", f"?v={version}", "?v=deadbeef0000"):
            with self.subTest(suffix=suffix):
                response = client.get(
                    "/static/files/pete-carter-resume.pdf" + suffix,
                    base_url="https://peerslate.com",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "application/pdf")
                self.assertEqual(response.data, published)
                self.assertEqual(response.headers.get("Content-Length"), str(len(published)))
                self.assertEqual(response.headers.get("X-Robots-Tag"), QUIET_PREVIEW_X_ROBOTS_TAG)
                self.assertEqual(
                    response.headers.get("Cache-Control"),
                    "public, max-age=3600, stale-while-revalidate=86400",
                )
                response.close()


if __name__ == "__main__":
    unittest.main()
