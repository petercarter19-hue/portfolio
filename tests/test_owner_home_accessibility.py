"""Accessibility and reflow contract for the neutral /app launchpad."""

import unittest
import re
from pathlib import Path

from app import app


ROOT = Path(__file__).resolve().parents[1]


def _relative_luminance(hex_color):
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first, second):
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class OwnerLaunchpadAccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_WORKSHOP_ENABLED": app.config.get(
                "PEERSLATE_WORKSHOP_ENABLED"
            ),
            "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": app.config.get(
                "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"
            ),
            "PEERSLATE_OPPORTUNITY_SLATE_ENABLED": app.config.get(
                "PEERSLATE_OPPORTUNITY_SLATE_ENABLED"
            ),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="test-owner",
            PEERSLATE_WORKSHOP_ENABLED=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_OPPORTUNITY_SLATE_ENABLED=True,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original)

    def test_landmarks_heading_and_link_names_are_complete_without_javascript(self):
        body = self.client.get("/app").get_data(as_text=True)
        self.assertEqual(body.count("<main"), 1)
        self.assertEqual(body.count("<h1"), 1)
        self.assertIn('aria-labelledby="owner-workspace-title"', body)
        self.assertIn('aria-label="Your PeerSlate destinations"', body)
        self.assertEqual(body.count('class="owner-app__destination"'), 5)
        for label in (
            "Public Resume",
            "Opportunity Slate",
            "Interview Studio",
            "Community",
            "Settings",
        ):
            self.assertIn(f'>{label}<', body)
        for held_label in ("Workshop", "Capture", "Slate Board"):
            self.assertNotIn(f'>{held_label}<', body)
        self.assertNotIn("javascript:", body.lower())
        self.assertNotIn("onclick=", body.lower())
        self.assertNotIn("data-open-chat", body)

    def test_focus_and_reflow_rules_cover_keyboard_narrow_and_zoom_layouts(self):
        css = (ROOT / "static/css/owner-app.css").read_text(encoding="utf-8")
        self.assertIn(".owner-app__destination:focus-visible", css)
        self.assertIn("outline: 3px solid", css)
        focus_rule = css.split(
            ".owner-app__destination:focus-visible {", 1
        )[1].split("}", 1)[0]
        focus_color = re.search(r"outline:\s*3px solid (#[0-9a-fA-F]{6})", focus_rule)
        self.assertIsNotNone(focus_color)
        for adjacent_background in ("#ffffff", "#f6f8fc"):
            self.assertGreaterEqual(
                _contrast_ratio(focus_color.group(1), adjacent_background), 3.0
            )
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", css)
        self.assertIn("@media (max-width: 640px)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css)
        self.assertIn("overflow-wrap: anywhere", css)
        destination = css.split(".owner-app__destination {", 1)[1].split("}", 1)[0]
        self.assertNotIn("white-space: nowrap", destination)

    def test_every_launchpad_destination_has_a_generous_target(self):
        css = (ROOT / "static/css/owner-app.css").read_text(encoding="utf-8")
        destination = css.split(".owner-app__destination {", 1)[1].split("}", 1)[0]
        self.assertIn("min-height: 9rem", destination)
        self.assertIn("padding: 1.35rem", destination)


if __name__ == "__main__":
    unittest.main()
