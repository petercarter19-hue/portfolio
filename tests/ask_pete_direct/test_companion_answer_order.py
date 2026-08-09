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
        """Summary, then the quiet boundary sentence, then the folded
        evidence, then the one contact entry point (Pete's 2026-08-09
        redesign)."""
        order = [
            "ask-pete-evidence-answer__summary",
            "ask-pete-evidence-answer__boundary",
            "renderEvidenceFold(",
            "renderHandoff(",
        ]
        positions = [self.render.index(token) for token in order]
        self.assertEqual(
            positions,
            sorted(positions),
            "the answer must render before the evidence fold and the contact entry",
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

    def test_the_scroll_respects_reduced_motion_and_hidden_tabs(self):
        """Browsers suppress smooth scrolling in a hidden tab (proven on live
        peerslate.com, 2026-08-09): a reduced-motion visitor and a background
        tab both get the instant jump instead."""
        self.assertIn(
            "hasReducedMotion() || document.visibilityState === 'hidden'",
            self.reveal,
        )
        self.assertIn("instant ? 'auto' : 'smooth'", self.reveal)

    def test_an_answer_that_lands_in_a_hidden_tab_is_revealed_on_return(self):
        self.assertIn("state.revealOnReturn = true;", self.reveal)
        self.assertIn("document.addEventListener('visibilitychange'", self.source)
        self.assertIn("state.revealOnReturn = false;", self.source)

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

    def test_the_control_is_prepended_before_the_one_trust_line(self):
        """Since the 2026-08-09 redesign the meta row holds exactly the back
        control (when there is one) and the single answer-level badge. The
        old machinery caption and the compact rule that hid it are gone -
        that rule would now hide the badge itself."""
        self.assertIn("meta.insertBefore(makeBackButton(), meta.firstChild);", self.render)
        self.assertNotIn("'Claim-level evidence and limitations'", self.source)
        self.assertNotIn(
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


class RedesignTests(unittest.TestCase):
    """Pete's owner-directed companion redesign, recorded 2026-08-09.

    Direction, verbatim intent: no per-card "supported" badges ("it's clear
    that there's evidence"); no boundary card - one quiet sentence instead,
    because the server quality contract still requires the boundary claim; no
    "Useful follow-up questions" block; ONE compact contact entry point; the
    ask box pinned always visible; evidence folded behind one line with cards
    that expand on tap. Source-level assertions, like the rest of this file;
    the behaviour is exercised in a real browser through
    run_direct_preview.py.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.css = STYLESHEET.read_text(encoding="utf-8")
        cls.partial = PARTIAL.read_text(encoding="utf-8")
        cls.claim = function_body(cls.source, "renderClaim")
        cls.render = function_body(cls.source, "renderAnswer")
        cls.handoff = function_body(cls.source, "renderHandoff")

    def test_supported_claims_carry_no_badge_and_nuance_keeps_its_label(self):
        self.assertIn("if (claim.state !== 'supported') {", self.claim)
        badge_call = self.claim.index("makeSupportBadge(claim.state")
        self.assertGreater(
            badge_call,
            self.claim.index("if (claim.state !== 'supported') {"),
            "a claim badge may render only where support is NOT established",
        )

    def test_the_answer_keeps_exactly_one_top_level_trust_line(self):
        self.assertIn("makeSupportBadge(payload.state, payload.support_label)", self.render)

    def test_the_boundary_renders_as_one_quiet_sentence_not_a_card(self):
        """The server quality contract (quality.py, requires_boundary=True)
        still receives its boundary claim - it is folded visually, never
        deleted or suppressed."""
        self.assertIn("claim.kind === 'boundary'", self.render)
        self.assertIn("ask-pete-evidence-answer__boundary", self.render)
        self.assertIn("claim.kind !== 'boundary'", self.render)

    def test_the_follow_up_block_is_gone(self):
        self.assertNotIn("renderFollowUps", self.source)
        self.assertNotIn("Useful follow-up questions", self.source)
        self.assertNotIn("data-ask-pete-followup", self.source)
        self.assertNotIn("ask-pete-evidence-followups", self.css)

    def test_the_evidence_folds_behind_one_line_and_expands(self):
        self.assertIn("function renderEvidenceFold(", self.source)
        self.assertIn("'See the evidence'", self.source)
        self.assertIn("'Hide the evidence'", self.source)
        self.assertIn("toggle.dataset.askPeteFoldToggle = '';", self.source)
        self.assertIn("event.target.closest('[data-ask-pete-fold-toggle]')", self.source)
        fold = function_body(self.source, "renderEvidenceFold")
        self.assertIn("body.hidden = true;", fold)

    def test_each_source_gets_one_line_and_one_action(self):
        """The old Show evidence/Open pairs named every source twice; a
        citation now renders its excerpt and a single open-on-resume action."""
        self.assertNotIn("askPeteCitationToggle", self.source)
        self.assertNotIn("'Show evidence'", self.source)
        self.assertIn("makeSourceButton(citation)", self.claim)

    def test_there_is_exactly_one_contact_entry_point(self):
        self.assertNotIn("ask-pete-evidence-answer__section-heading", self.handoff)
        self.assertIn("if (directForm) {", self.handoff)
        self.assertIn("return section;", self.handoff)
        # The contact link renders only on the no-private-path branch, after
        # the direct form has returned - never alongside it.
        self.assertLess(
            self.handoff.index("if (directForm) {"),
            self.handoff.index("askPeteContactUrl"),
        )

    def test_the_ask_box_is_docked_outside_the_scroll_region(self):
        dock = self.partial.index("ask-pete-evidence-companion__dock")
        self.assertLess(self.partial.index("ask-pete-evidence-companion__scroll"), dock)
        self.assertLess(dock, self.partial.index("data-ask-pete-form"))
        self.assertLess(dock, self.partial.index("data-ask-pete-status"))
        self.assertIn(".ask-pete-evidence-companion__dock", self.css)

    def test_the_composer_regained_its_gold_focus_treatment(self):
        self.assertIn(".ask-pete-evidence-composer textarea:focus {", self.css)
        focus_rule = self.css[self.css.index(".ask-pete-evidence-composer textarea:focus {") :]
        focus_rule = focus_rule[: focus_rule.index("}")]
        self.assertIn("var(--ape-gold)", focus_rule)

    def test_the_preview_card_lost_its_badge_too(self):
        self.assertNotIn("ask-pete-support-badge--supported\">Supported", self.partial)


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
