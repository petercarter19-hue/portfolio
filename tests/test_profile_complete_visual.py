from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProfileCompleteVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates/profile/profile_destination.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "static/css/profile-experience.css").read_text(encoding="utf-8")

    def test_visual_language_uses_profile_authority_not_blue_or_card_soup(self):
        for token in ("--profile-forest", "--profile-bronze", "--profile-plum", "--profile-canvas"):
            self.assertIn(token, self.css)
        self.assertNotIn("--profile-blue", self.css)
        self.assertNotIn("background: #0b1", self.css.lower())

    def test_mobile_reflow_touch_targets_and_accessibility_states_exist(self):
        for contract in ("@media (max-width: 30rem)", "min-height: 44px", ":focus-visible", "@media (forced-colors: active)", "@media (prefers-reduced-motion: reduce)"):
            self.assertIn(contract, self.css)
        for contract in ('role="search"', 'aria-current="page"', 'tabindex="-1"', 'aria-label="Play selected voice recording"'):
            self.assertIn(contract, self.template)

    def test_media_voice_and_project_destination_states_are_truthful(self):
        for text in ("Private originals", "Playback never starts automatically", "Private Project work remains private"):
            self.assertIn(text, self.template)


if __name__ == "__main__": unittest.main()
