"""PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001 shared-shell regressions.

These checks exercise the only composed product seam.  Source-package suites
retain their own complete route, visual, accessibility, and privacy coverage.
"""

import hashlib
import json
import os
import re
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from app import app
from services.owner_home_service import OwnerHomeContractError
from PIL import Image, ImageChops

from tests.test_owner_home import (
    FLAG_OFF_APP_RENDER_BYTE_LENGTH,
    FLAG_OFF_APP_RENDER_SHA256,
)


DEV_USER_KEY = "milestone-journal-owner"
EVIDENCE_ROOT = Path("artifacts/ps-community-journal-home-milestone-001")
PACKAGE_CAPTURE_DIRECTORIES = {
    "community": EVIDENCE_ROOT / "community",
    "journal": EVIDENCE_ROOT / "journal",
    "owner_home": EVIDENCE_ROOT / "owner_home",
}
COMMUNITY_SOURCE_DIRECTORY = Path("artifacts/ps-community-tabs-001")
PACKAGE_SOURCE_DIRECTORIES = {
    "community": COMMUNITY_SOURCE_DIRECTORY,
    "journal": Path("artifacts/ps-journal-001-j1-frontend"),
    "owner_home": Path("artifacts/ps-home-frontend-001/screenshots"),
}
EXPECTED_EVIDENCE_COUNTS = {"community": 15, "journal": 62, "owner_home": 21}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
DIMENSIONS = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*$")


def _journal_items():
    return [
        {
            "moment_key": "11111111-1111-1111-1111-111111111111",
            "moment_kind": "reflection",
            "title": "A private integrated-shell check",
            "occurred_on": None,
            "occurred_precision": "unknown",
            "visibility": "private",
            "source_type": "text",
            "lifecycle_state": "active",
            "version_number": 1,
        }
    ]


def _list_owner_journal(*_args, **_kwargs):
    return {"items": _journal_items(), "next_cursor": None}


class MilestoneSharedShellTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_config = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_JOURNAL_ENABLED",
                "PEERSLATE_OWNER_HOME_ENABLED",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
            )
        }

    def tearDown(self):
        app.config.update(self.original_config)

    def test_template_retains_both_explicit_control_signals(self):
        with open("templates/base.html", encoding="utf-8") as template:
            body = template.read()

        self.assertIn("standalone_owner_shell", body)
        self.assertIn("is_private_journal_path", body)
        self.assertIn("_p.startswith('/app/journal')", body)
        self.assertIn("{% if not standalone_owner_shell %}", body)
        self.assertIn("and not is_private_journal_path", body)

    def test_default_flags_remain_off(self):
        self.assertIs(app.config["PEERSLATE_JOURNAL_ENABLED"], False)
        self.assertIs(app.config["PEERSLATE_OWNER_HOME_ENABLED"], False)

    def test_community_uses_the_global_shell_without_profile_navigation(self):
        response = self.client.get("/the-slate")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="global-header"', body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertIn('class="footer"', body)
        self.assertNotIn('class="owner-home-shell"', body)

    def test_flag_off_app_preserves_the_released_workspace_bytes(self):
        app.config.update(
            PEERSLATE_OWNER_HOME_ENABLED=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="existing-owner",
        )

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        # Private workspace renders are no-store; the released bytes asserted
        # below are unchanged.
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(len(response.data), FLAG_OFF_APP_RENDER_BYTE_LENGTH)
        self.assertEqual(
            hashlib.sha256(response.data).hexdigest(), FLAG_OFF_APP_RENDER_SHA256
        )
        self.assertIn(b"My PeerSlate", response.data)
        self.assertNotIn(b"owner-home-shell", response.data)

    @patch("owner_routes.journal_service")
    def test_private_journal_keeps_normal_header_but_excludes_public_actions(self, service):
        app.config.update(
            PEERSLATE_JOURNAL_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
        )
        service.list_owner_journal.side_effect = _list_owner_journal

        response = self.client.get("/app/journal")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="global-header"', body)
        self.assertIn('class="footer"', body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertNotIn('data-open-chat', body)
        self.assertNotIn('id="chat-toggle"', body)
        self.assertNotIn('class="owner-home-shell"', body)

    @patch("auth_routes.owner_home_service")
    def test_flag_on_owner_home_is_standalone_without_public_shell(self, service):
        app.config.update(
            PEERSLATE_OWNER_HOME_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="milestone-owner",
        )
        service.get_home.side_effect = OwnerHomeContractError("synthetic check")

        response = self.client.get("/app")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 503)
        self.assertIn('class="owner-home-shell"', body)
        self.assertNotIn('class="global-header"', body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertNotIn('class="footer"', body)
        self.assertNotIn('id="chat-toggle"', body)
        self.assertNotIn('static/js/theme-toggle.js', body)

    def test_unrelated_route_retains_only_the_ordinary_global_shell(self):
        response = self.client.get("/peerslate")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="global-header"', body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertIn('class="footer"', body)
        self.assertNotIn('id="chat-toggle"', body)
        self.assertNotIn('class="owner-home-shell"', body)

    def test_package_local_j1_playback_deferral_is_explicit_and_narrow(self):
        decision = Path(
            "docs/initiatives/PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001/"
            "J1_PLAYBACK_DECISION_2026-07-22.md"
        ).read_text(encoding="utf-8")
        decision_words = " ".join(decision.split())
        for contract in (
            "Pete explicitly decided on 2026-07-22",
            "for J1 only",
            "`Coming later`",
            "does not prove, imply, or authorize working audio playback",
            "No fake playback",
            "does not expose or leak storage Blob URLs",
            "revoked, deleted, missing, quarantined",
            "keyboard behavior",
            "audio lifecycle behavior",
            "privacy, authorization, cache, range-request, content-type",
            "changes no shared governance file",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, decision_words)

        journal_template = Path("templates/journal.html").read_text(encoding="utf-8")
        journal_script = Path("static/js/journal.js").read_text(encoding="utf-8")
        for source in (journal_template, journal_script):
            self.assertIn('class="ps-journal__voice-play" disabled aria-disabled="true"', source)
            self.assertIn("Playback for this voice Moment is coming later", source)


class MilestoneEvidenceIntegrityTests(unittest.TestCase):
    """Validate generated candidate evidence when its rendered SHA is supplied."""

    def test_targeted_manifest_integrity(self):
        expected_rendered_commit = os.environ.get(
            "PEERSLATE_MILESTONE_RENDERED_PRODUCT_COMMIT"
        )
        manifest = json.loads((EVIDENCE_ROOT / "EVIDENCE_MANIFEST.json").read_text())

        self.assertEqual(manifest["package"], "PS-COMMUNITY-JOURNAL-HOME-MILESTONE-001")
        self.assertRegex(manifest["rendered_product_commit"], GIT_SHA)

        # Evidence is regenerated only after the rendered-product commit is
        # frozen. Normal pre-capture test runs validate the suite itself;
        # the evidence gate supplies that SHA and performs the full audit.
        if not expected_rendered_commit:
            return

        self.assertRegex(expected_rendered_commit, GIT_SHA)
        self.assertEqual(manifest["rendered_product_commit"], expected_rendered_commit)

        declared_comparison_artifacts = {
            item["file"] for item in manifest.get("comparison_artifacts", [])
        }
        for package, directory in PACKAGE_CAPTURE_DIRECTORIES.items():
            declared_captures = {
                item["file"] for item in manifest["packages"][package]["captures"]
            }
            actual_pngs = {
                str(path.relative_to(directory))
                for path in directory.rglob("*.png")
            }
            self.assertSetEqual(
                actual_pngs,
                declared_captures | {
                    artifact.removeprefix(f"{package}/")
                    for artifact in declared_comparison_artifacts
                    if artifact.startswith(f"{package}/")
                },
            )

        for package, expected_count in EXPECTED_EVIDENCE_COUNTS.items():
            with self.subTest(package=package):
                package_manifest = manifest["packages"][package]
                captures = package_manifest["captures"]
                self.assertEqual(package_manifest["capture_count"], expected_count)
                self.assertEqual(len(captures), expected_count)

                hashes_to_files = defaultdict(list)
                for capture in captures:
                    for field in (
                        "file",
                        "route",
                        "state",
                        "viewport",
                        "theme",
                        "file_type",
                        "dimensions",
                        "file_sha256",
                        "decoded_rgba_sha256",
                        "rendered_product_commit",
                    ):
                        self.assertIn(field, capture)
                    self.assertEqual(capture["file_type"], "png")
                    self.assertRegex(capture["dimensions"], DIMENSIONS)
                    self.assertRegex(capture["viewport"], DIMENSIONS)
                    self.assertRegex(capture["file_sha256"], SHA256)
                    self.assertRegex(capture["decoded_rgba_sha256"], SHA256)
                    self.assertEqual(
                        capture["rendered_product_commit"], expected_rendered_commit
                    )

                    path = PACKAGE_CAPTURE_DIRECTORIES[package] / capture["file"]
                    payload = path.read_bytes()
                    self.assertEqual(payload[:8], b"\x89PNG\r\n\x1a\n")
                    self.assertEqual(
                        hashlib.sha256(payload).hexdigest(), capture["file_sha256"]
                    )
                    with Image.open(path) as image:
                        self.assertEqual(image.format, "PNG")
                        self.assertEqual(
                            f"{image.width}x{image.height}", capture["dimensions"]
                        )
                        decoded = image.convert("RGBA").tobytes()
                    self.assertEqual(
                        hashlib.sha256(decoded).hexdigest(),
                        capture["decoded_rgba_sha256"],
                    )
                    source_path = PACKAGE_SOURCE_DIRECTORIES[package] / capture["file"]
                    source_payload = source_path.read_bytes()
                    self.assertEqual(
                        hashlib.sha256(source_payload).hexdigest(),
                        capture["source_file_sha256"],
                    )
                    with Image.open(source_path) as source_image:
                        source_rgba = source_image.convert("RGBA")
                        source_decoded = source_rgba.tobytes()
                        source_dimensions = f"{source_image.width}x{source_image.height}"
                    self.assertEqual(source_dimensions, capture["source_dimensions"])
                    self.assertEqual(
                        hashlib.sha256(source_decoded).hexdigest(),
                        capture["source_decoded_rgba_sha256"],
                    )
                    comparison = capture["source_pixel_comparison"]
                    dimensions_equal = capture["dimensions"] == source_dimensions
                    self.assertEqual(comparison["dimensions_equal"], dimensions_equal)
                    self.assertEqual(
                        comparison["decoded_pixel_identical"],
                        dimensions_equal and decoded == source_decoded,
                    )
                    self.assertIn("raster_explanation", comparison)
                    for metric in (
                        "changed_rgb_pixel_count",
                        "changed_rgb_bbox",
                        "mean_absolute_rgb_channel_error",
                        "rmse_rgb_channel_error",
                        "max_channel_delta",
                        "pixels_above_delta_8",
                        "pixels_above_delta_16",
                        "pixels_above_delta_32",
                        "percent_pixels_above_delta_8",
                        "percent_pixels_above_delta_16",
                        "percent_pixels_above_delta_32",
                    ):
                        self.assertIn(metric, comparison)
                    if dimensions_equal:
                        with Image.open(path) as candidate_image:
                            difference = ImageChops.difference(
                                candidate_image.convert("RGB"), source_rgba.convert("RGB")
                            )
                        changed = sum(pixel != (0, 0, 0) for pixel in difference.getdata())
                        self.assertEqual(comparison["changed_rgb_pixel_count"], changed)
                        bbox = difference.getbbox()
                        self.assertEqual(
                            comparison["changed_rgb_bbox"], list(bbox) if bbox else None
                        )
                    else:
                        self.assertEqual(comparison["changed_rgb_pixel_count"], "size_mismatch")

                    if package == "community":
                        assertions = capture["semantic_assertions"]
                        self.assertTrue(assertions["expected_panel_visible"])
                        self.assertTrue(assertions["expected_tab_selected"])
                        if capture["state"] == "keyboard-focus":
                            self.assertEqual(assertions["location_pathname"], "/the-slate/break")
                            self.assertEqual(assertions["active_tab"], "break")
                            self.assertEqual(assertions["focused_tab"], "break")
                            self.assertTrue(assertions["focus_ring_visible"])
                        elif capture["state"] == "feed":
                            self.assertTrue(assertions["feed_content_ready"])
                            self.assertGreater(assertions["feed_post_count"], 0)
                        if capture.get("region") == "lower":
                            self.assertIn("region_anchor", assertions)
                            self.assertGreaterEqual(assertions["scroll_y"], 0)
                            for required in assertions["required_visible_content"]:
                                self.assertTrue(required)
                    hashes_to_files[capture["file_sha256"]].append(capture["file"])

                self.assertEqual(
                    len(hashes_to_files), package_manifest["unique_exact_hash_count"]
                )
                actual_duplicates = sorted(
                    sorted(files)
                    for files in hashes_to_files.values()
                    if len(files) > 1
                )
                declared_duplicates = sorted(
                    sorted(files)
                    for files in package_manifest["permitted_exact_duplicate_groups"]
                )
                self.assertEqual(actual_duplicates, declared_duplicates)
                if package == "owner_home":
                    owner_by_file = {item["file"]: item for item in captures}
                    self.assertNotEqual(
                        owner_by_file["01-desktop-1440-populated.png"]["file_sha256"],
                        owner_by_file["09-long-content-bidi-desktop.png"]["file_sha256"],
                    )
                    self.assertNotEqual(
                        owner_by_file["02-mobile-390-populated.png"]["file_sha256"],
                        owner_by_file["09b-long-content-bidi-mobile-390.png"]["file_sha256"],
                    )

        journal_by_file = {
            item["file"]: item for item in manifest["packages"]["journal"]["captures"]
        }
        for filename in (
            "composer-type-desktop-light-1440.png",
            "composer-speak-mobile-dark-390.png",
            "composer-mobile-save-failure-390.png",
            "composer-mobile-voice-failure-dark-320.png",
        ):
            self.assertNotEqual(journal_by_file[filename]["state"], "timeline")
        journal_zoom = journal_by_file["timeline-desktop-200pct-zoom-light-1440.png"]
        self.assertEqual(journal_zoom["viewport"], "720x520")
        self.assertEqual(journal_zoom["dimensions"], "720x520")
        self.assertEqual(journal_zoom["capture_method"], "css-viewport-reflow-equivalent")
        self.assertFalse(journal_zoom["reflow"]["horizontal_overflow"])
        self.assertFalse(journal_zoom["reflow"]["headline_action_overlap"])
        self.assertEqual(journal_zoom["reflow"]["focused_control"], "journal-open-composer")

        owner_by_file = {
            item["file"]: item for item in manifest["packages"]["owner_home"]["captures"]
        }
        owner_zoom = owner_by_file["05-200pct-zoom-reflow-720x450.png"]
        self.assertEqual(owner_zoom["viewport"], "720x450")
        self.assertTrue(owner_zoom["dimensions"].startswith("720x"))
        self.assertEqual(owner_zoom["capture_method"], "css-viewport-reflow-equivalent")
        self.assertFalse(owner_zoom["reflow"]["horizontal_overflow"])
        self.assertFalse(owner_zoom["reflow"]["hero_capture_overlap"])
        self.assertEqual(owner_zoom["reflow"]["focused_selector"], ".oh__capture-card")
        self.assertTrue(owner_zoom["reflow"]["focus_outline_visible"])
