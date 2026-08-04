"""Live first-visitor polish contracts for Workshop (2026-08-04).

These lock the specific defects a first-visitor audit found on the LIVE
public Workshop, so they cannot quietly return:

  P1  the four doors rendered as a ragged, cramped row
  P2  "Related information" claimed a relevance it does not compute
  P3  the public-preview banner was worded five different ways
  P4  mobile dropped the "Your information" explanatory copy
  P5  a status string ("Text entry is available...") leaked into body copy
  P6  the final-wording textarea sliced text through a line of glyphs
  P7  the mic rendered live and focusable with JavaScript off

Most are CSS/markup contracts, so they read the source files directly —
the rendered-HTML behaviour they protect is covered by the route tests in
test_workshop_flows / _review / _work_session / _voice.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_source(relative_path):
    with open(os.path.join(ROOT, relative_path), encoding="utf-8") as handle:
        return handle.read()


class DoorsRowLayoutTests(unittest.TestCase):
    """P1. Measured live at 1448px: heights 330/330/201/222, every card
    166px wide, the whole 710px row floating in large empty margins."""

    def setUp(self):
        self.css = read_source("static/css/workshop.css")

    def test_the_doors_row_sizes_from_its_container_not_the_viewport(self):
        """The bug's root cause: a `max-width: 900px` viewport breakpoint
        decided "four across" while the column the row actually sits in
        was ~710px wide."""
        self.assertIn("repeat(auto-fit, minmax(min(100%, 20rem), 1fr))", self.css)
        self.assertNotIn("grid-template-columns: repeat(4, minmax(0, 1fr));", self.css)

    def test_every_door_fills_its_cell_whatever_wraps_it(self):
        """A door is wrapped as a bare div, a bare button, and a
        single-button form. Only the div stretched, which is what made the
        bottom edge a staircase."""
        self.assertIn(".wk-doors > form {", self.css)
        self.assertIn("height: 100%;", self.css)

    def test_a_resumable_title_is_never_clipped(self):
        """The second Continue entry's own title was cut mid-word by a
        two-line clamp (scrollHeight > clientHeight on the live page)."""
        self.assertNotIn("-webkit-line-clamp: 2;", self.css)

    def test_the_opening_screen_opts_into_a_wider_shell(self):
        self.assertIn(".wk-flow-layout--opening {", self.css)
        self.assertIn("wk-flow-layout wk-flow-layout--opening", read_source("templates/workshop_work.html"))


class RelatedInformationHonestyTests(unittest.TestCase):
    """P2. The rail said PeerSlate "found these private items because they
    may help strengthen this example". It is the first MAX_CONTEXT_ITEMS
    confirmed rows in library order — identical every session, whatever the
    member wrote."""

    def setUp(self):
        self.review = read_source("templates/workshop_work_review.html")
        self.session = read_source("templates/workshop_work_session.html")

    def test_the_review_rail_no_longer_claims_a_relevance_it_never_computes(self):
        self.assertNotIn("may help strengthen this example", self.review)
        self.assertNotIn("PeerSlate found these private items", self.review)

    def test_the_review_rail_says_what_the_list_actually_is(self):
        self.assertIn("Your confirmed information", self.review)
        self.assertIn("From your library, in the order you see it there", self.review)

    def test_the_session_rail_uses_the_same_honest_name(self):
        """Both screens render the same rows in the same order, so they must
        not describe that list two different ways."""
        self.assertIn("Your confirmed information", self.session)
        self.assertNotIn("Related confirmed information</span>", self.session)

    def test_the_relevance_ordering_hazard_stays_documented_in_the_source(self):
        """Ranking this rail is only safe once the context mask stops being
        positional. Keep the reason next to the code that would be changed."""
        routes = read_source("workshop_work_routes.py")
        self.assertIn("positional", routes)
        self.assertIn("id-based", routes)


PREVIEW_BANNER_SCREENS = [
    "templates/workshop.html",
    "templates/workshop_work.html",
    "templates/workshop_work_session.html",
    "templates/workshop_work_review.html",
    "templates/workshop_work_holding.html",
    "templates/workshop_add.html",
    "templates/workshop_review.html",
    "templates/workshop_saved.html",
    "templates/workshop_delete_confirm.html",
]

RETIRED_BANNER_PHRASINGS = [
    "you&#39;re signed out",
    "Saving here keeps this only for",
    "this is in your own session only",
    "this only removes the item from your own preview session",
    "What you add or edit here is kept",
]


class PreviewBannerConsistencyTests(unittest.TestCase):
    """P3. list -> work -> add -> review -> saved told the visitor the same
    thing five different ways, which reads as five different rules."""

    def setUp(self):
        self.banner = read_source("templates/partials/workshop/_preview_banner.html")

    def test_every_preview_screen_includes_the_one_shared_banner(self):
        for screen in PREVIEW_BANNER_SCREENS:
            with self.subTest(screen=screen):
                self.assertIn("partials/workshop/_preview_banner.html", read_source(screen))

    def test_no_screen_still_hand_writes_its_own_banner_markup(self):
        """The consolidation only holds if the markup lives in one place."""
        for screen in PREVIEW_BANNER_SCREENS:
            with self.subTest(screen=screen):
                self.assertNotIn('wk-status-banner wk-status-banner--preview', read_source(screen))

    def test_the_retired_phrasings_are_gone_from_every_screen(self):
        for screen in PREVIEW_BANNER_SCREENS:
            for phrase in RETIRED_BANNER_PHRASINGS:
                with self.subTest(screen=screen, phrase=phrase):
                    self.assertNotIn(phrase, read_source(screen))

    def test_the_banner_has_exactly_the_two_intended_variants(self):
        self.assertIn('variant == "working"', self.banner)
        self.assertEqual(1, self.banner.count("{%- if variant"))

    def test_no_honest_claim_was_dropped_in_the_consolidation(self):
        """Sample content, session-only, and sign-in-makes-it-permanent all
        survive in BOTH variants — the consolidation must not have quietly
        weakened a privacy statement to make the copy shorter."""
        self.assertIn("this is example information, not yours", self.banner)
        self.assertIn("Sign in to keep it permanently in your own private library", self.banner)
        self.assertEqual(2, self.banner.count("for this visit only, in your browser"))


class MobileExplanatoryCopyTests(unittest.TestCase):
    """P4. At 390px the "Your information" card hid both its explanatory
    paragraph and its private-library note, leaving a bare blue button — so
    the phone visitor got strictly LESS explanation than the desktop one."""

    def setUp(self):
        self.css = read_source("static/css/workshop.css")

    def test_the_rail_copy_is_no_longer_hidden_on_a_phone(self):
        self.assertNotIn(
            ".wk-rail__copy,\n    .wk-rail__note {\n        display: none;\n    }",
            self.css,
        )

    def test_the_copy_is_condensed_rather_than_removed(self):
        """Restored, but paying less vertical space than the desktop ramp."""
        mobile_block = self.css.split("@media (max-width: 640px) {", 1)[1]
        self.assertIn(".wk-rail__copy,", mobile_block)
        self.assertIn("font-size: 0.82rem;", mobile_block)

    def test_both_sentences_still_exist_in_the_rail_itself(self):
        rail = read_source("templates/partials/workshop/_your_information_rail.html")
        self.assertIn("Add an experience, skill, interest, accomplishment", rail)
        self.assertIn("This is your private library. Nothing here is public", rail)


VOICE_HINT_SCREENS = [
    "templates/workshop_add.html",
    "templates/workshop_work_session.html",
    "templates/workshop_work.html",
]


class LeakedStatusStringTests(unittest.TestCase):
    """P5. "Text entry is available. You can type or speak." rendered as
    body copy under the composer, the add form, and the session field — it
    read like a status string that escaped into the page."""

    def test_the_status_string_is_gone_from_every_field(self):
        for screen in VOICE_HINT_SCREENS:
            with self.subTest(screen=screen):
                body = read_source(screen)
                self.assertNotIn("Text entry is available", body)

    def test_the_field_still_carries_its_own_affordance(self):
        """Dropped, not relocated: the mic control itself is the affordance,
        and it is honest in BOTH flag states — which is more than the
        sentence managed."""
        for screen in VOICE_HINT_SCREENS:
            with self.subTest(screen=screen):
                self.assertIn("workshop_mic", read_source(screen))

    def test_the_inert_mic_still_says_so_in_its_own_label(self):
        macro = read_source("templates/partials/workshop/_voice.html")
        self.assertIn("Voice input is not available yet", macro)


class NoScriptMicHonestyTests(unittest.TestCase):
    """P7a. With JavaScript off the mic still rendered live: disabled=false,
    focusable, aria-label="Speak your thought" — a promise nothing could
    keep. The honest inert fallback only existed when the FLAG was off, not
    when the script failed to load."""

    def setUp(self):
        self.macro = read_source("templates/partials/workshop/_voice.html")
        self.script = read_source("static/js/workshop-voice.js")

    def test_the_server_renders_the_mic_inert(self):
        self.assertIn('aria-label="Voice input is not available yet"\n            aria-disabled="true"\n            disabled', self.macro)

    def test_the_server_never_renders_the_speak_promise(self):
        """The 'Speak your X' label must come from the script, which is the
        only thing that can honour it."""
        self.assertNotIn('aria-label="Speak your {{ noun }}"', self.macro)
        self.assertIn("'Speak your ' + noun", self.script)

    def test_the_script_enables_the_control_it_promises(self):
        self.assertIn("micButton.removeAttribute('aria-disabled');", self.script)


class FinalWordingFieldTests(unittest.TestCase):
    """P6. The final-wording textarea sliced its last visible line
    horizontally through the glyphs, and the mic floated over the
    bottom-right of the member's own text."""

    def setUp(self):
        self.css = read_source("static/css/workshop.css")

    def test_the_field_states_a_whole_line_height_instead_of_trusting_rows(self):
        """`rows` sizes the content box, but everything in .wk is
        border-box, so padding was eating into the visible rows and cutting
        the last one in half."""
        self.assertIn("min-height: calc(6 * 1.6rem + 0.9rem + 3.2rem + 2px);", self.css)

    def test_the_editor_reserves_a_bottom_band_for_the_mic(self):
        """A bottom band clears the control at any width — the previous
        right band did not, once the voice control grew its inline label."""
        self.assertIn("padding: 0.9rem 0.9rem 3.2rem;", self.css)

    def test_the_field_grows_where_the_browser_supports_it(self):
        self.assertIn("@supports (field-sizing: content)", self.css)
        self.assertIn("field-sizing: content;", self.css)
        self.assertIn("max-height: 60vh;", self.css)

    def test_the_composer_keeps_the_right_band_its_own_mic_needs(self):
        """The composer's mic is the one variant positioned mid-right, so a
        bottom band would not clear it."""
        self.assertIn(".wk-work-composer__row .wk-field__textarea {", self.css)
        self.assertIn("padding: 0.9rem 3rem 0.9rem 0.9rem;", self.css)


if __name__ == "__main__":
    unittest.main()
