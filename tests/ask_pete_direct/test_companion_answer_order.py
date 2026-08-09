"""Answer-first ordering and the one-step back control.

Owner feedback, Pete, 2026-08-08, using the local preview harness:

    "the sixty second recruiter view is a two second recruiter view... a lot
    of information, sorted out weird"
    "there's no way to go back"

Investigation verdict (recorded in full in the package README):

* **Ordering is a DEFECT against the locked authority.** The DOM order was
  already answer-first; what was missing was any scroll management of the rail
  at all, so an answer rendered while the rail sat at its bottom left the
  recruiter looking at the follow-ups and the contact card. The accepted
  authority requires "answer first, followed by clearly associated claims and
  inspectable evidence".
* **The back control is an owner-directed ADAPTATION.** The accepted client
  state model holds a single ``answer`` and names multi-answer history as
  future work, so retaining exactly one prior answer is an addition, not a
  correction.

These are source-level assertions. The behaviour itself is verified in a real
browser by ``run_direct_preview.py --check``, which reproduces Pete's exact
sequence (type in the composer, which scrolls the rail to its bottom, then
ask) and measures where the answer lands.
"""

from __future__ import annotations

import re
import unittest

from tests.ask_pete_direct.support import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "static" / "js" / "ask-pete-evidence-companion.js"
STYLESHEET = REPOSITORY_ROOT / "static" / "css" / "ask-pete-resume-evidence.css"
PARTIAL = (
    REPOSITORY_ROOT / "templates" / "partials" / "ask_pete_evidence_companion.html"
)


def function_body(source: str, name: str) -> str:
    """The text of one top-level-in-scope function, to the next one."""
    start = source.index(f"function {name}(")
    remainder = source[start + 1 :]
    match = re.search(r"\n        (?:function |/\* )", remainder)
    return remainder[: match.start()] if match else remainder


class AnswerFirstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.render = function_body(cls.source, "renderAnswer")
        cls.reveal = function_body(cls.source, "revealAnswerTop")

    def test_the_dom_order_is_answer_first(self):
        """Summary, then claims, then sources, then follow-ups, then handoff."""
        order = [
            "ask-pete-evidence-answer__summary",
            "renderClaim(",
            "renderSourceSummary(",
            "renderFollowUps(",
            "renderHandoff(",
        ]
        positions = [self.render.index(token) for token in order]
        self.assertEqual(
            positions,
            sorted(positions),
            "the answer must render before the follow-ups and the handoff card",
        )

    def test_the_rail_is_scrolled_to_the_answer_after_every_render(self):
        self.assertIn("revealAnswerTop();", self.render)
        # Last statement in the function, after the DOM is in place.
        self.assertLess(
            self.render.index("elements.answer.replaceChildren(fragment);"),
            self.render.index("revealAnswerTop();"),
        )

    def test_only_the_rail_is_scrolled_never_the_resume_behind_it(self):
        """scrollIntoView walks every scrollable ancestor; the two existing
        calls deliberately move the résumé, and this one must not."""
        self.assertNotIn("scrollIntoView", self.reveal)
        self.assertIn("scroller.scrollTo(", self.reveal)
        self.assertIn("scroller.scrollTop = top;", self.reveal)

    def test_the_scroll_respects_reduced_motion(self):
        self.assertIn("hasReducedMotion() ? 'auto' : 'smooth'", self.reveal)

    def test_the_scroll_is_a_no_op_when_it_would_change_nothing(self):
        self.assertIn("if (Math.abs(offset) < 2) return;", self.reveal)

    def test_a_missing_scroll_container_cannot_break_the_companion(self):
        """The rail container is resolved outside `elements`, whose
        all-or-nothing guard would otherwise disable everything."""
        elements_block = self.source[
            self.source.index("const elements = {") : self.source.index(
                "if (Object.values(elements).some"
            )
        ]
        self.assertNotIn("scroller", elements_block)
        self.assertNotIn("companion__scroll", elements_block)
        self.assertIn(
            "const scroller = companion.querySelector('.ask-pete-evidence-companion__scroll');",
            self.source,
        )
        self.assertIn("if (!scroller || elements.answer.hidden) return;", self.reveal)


class BackToPreviousAnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.render = function_body(cls.source, "renderAnswer")
        cls.restore = function_body(cls.source, "restorePreviousAnswer")

    def test_exactly_one_prior_answer_is_retained(self):
        self.assertIn("answer: null, previousAnswer: null,", self.source)
        self.assertIn(
            "if (state.answer) state.previousAnswer = state.answer;", self.source
        )
        # One retained answer, not a stack.
        for forbidden in ("history", "answers.push", "state.answers"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.restore)

    def test_the_control_appears_only_when_there_is_somewhere_to_go(self):
        self.assertIn("if (state.previousAnswer) meta.insertBefore(", self.render)

    def test_the_control_is_prepended_so_the_compact_rail_still_works(self):
        """The accepted compact block hides
        `.ask-pete-evidence-answer__meta > span:last-child`. Appending would
        silently stop that rule matching."""
        self.assertIn("meta.insertBefore(makeBackButton(), meta.firstChild);", self.render)
        self.assertIn(
            ".ask-pete-evidence-answer__meta > span:last-child",
            STYLESHEET.read_text(encoding="utf-8"),
        )

    def test_going_back_swaps_rather_than_discards(self):
        self.assertIn("state.previousAnswer = state.answer;", self.restore)
        self.assertIn("state.answer = restored;", self.restore)
        self.assertIn("renderAnswer(restored);", self.restore)

    def test_going_back_clears_the_newer_answers_evidence_markers(self):
        self.assertIn("clearEvidenceMarkers();", self.restore)

    def test_going_back_announces_itself(self):
        self.assertIn("setStatus('Showing the previous answer.", self.restore)

    def test_the_control_is_wired_through_the_existing_delegation(self):
        self.assertIn("event.target.closest('[data-ask-pete-back]')", self.source)
        self.assertIn("restorePreviousAnswer();", self.source)

    def test_no_retained_answer_is_ever_sent_back_to_the_model(self):
        """A follow-up stays independently grounded, as the architecture
        requires: "prior answer text is not silently sent as model context".

        Retaining an answer for the back control must not quietly become
        conversation memory, so the request body is asserted whole.
        """
        request = self.source[
            self.source.index("window.fetch('/api/chat'") : self.source.index(
                "signal: controller.signal,"
            )
        ]
        self.assertIn(
            "body: JSON.stringify({ message, action, context_key: contextKey }),",
            request,
        )
        for forbidden in ("previousAnswer", "state.answer", "summary", "claims"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, request)


class BackControlStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = STYLESHEET.read_text(encoding="utf-8")

    def test_the_control_exists_and_meets_the_44px_rule(self):
        rule = self.css[self.css.index(".ask-pete-evidence-back {") :]
        rule = rule[: rule.index("}")]
        self.assertIn("min-height: 2.75rem;", rule)

    def test_it_introduces_no_new_colour(self):
        rule = self.css[self.css.index(".ask-pete-evidence-back {") :]
        rule = rule[: rule.index(".ask-pete-evidence-answer__summary")]
        self.assertNotIn("#", rule, "use an existing token, not a new literal")
        self.assertIn("var(--ape-forest)", rule)
        self.assertIn("var(--ape-gold)", rule)

    def test_it_sits_with_the_answer_rules_not_in_another_packages_block(self):
        self.assertLess(
            self.css.index(".ask-pete-evidence-back {"),
            self.css.index("PS-ASK-PETE-DIRECT-001 - the private question form"),
        )

    def test_the_shared_focus_ring_already_covers_it(self):
        """It is a <button> inside the companion, so the accepted
        `:is(a, button, textarea):focus-visible` rule applies with no new
        rule of its own."""
        self.assertIn(
            ":is(a, button, textarea):focus-visible", self.css
        )
        self.assertNotIn(".ask-pete-evidence-back:focus-visible", self.css)


class FlagSafetyTests(unittest.TestCase):
    """Neither change touches the server-rendered surface at all."""

    def test_the_partial_is_untouched_by_this_change(self):
        partial = PARTIAL.read_text(encoding="utf-8")
        for token in ("ask-pete-evidence-back", "data-ask-pete-back", "revealAnswerTop"):
            with self.subTest(token=token):
                self.assertNotIn(token, partial)

    def test_the_assets_only_load_where_the_companion_is_enabled(self):
        """A legacy page loads chatbot.css/js instead, so neither the new CSS
        rule nor the new script path can reach it."""
        resume = (REPOSITORY_ROOT / "templates" / "resume2.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("ask_pete_evidence_companion_enabled", resume)
        marker = resume.index("ask-pete-resume-evidence.css")
        self.assertIn(
            "ask_pete_evidence_companion_enabled", resume[max(0, marker - 400) : marker]
        )


if __name__ == "__main__":
    unittest.main()
