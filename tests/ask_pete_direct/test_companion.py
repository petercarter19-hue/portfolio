"""The consent-first question form inside the accepted handoff card.

Three things are proven here:

* **Flag off changes nothing.** The partial's rendered bytes with the flag off
  are identical to rendering the same template with the whole PS-ASK-PETE-
  DIRECT-001 block cut out of its source. If the addition ever leaked outside
  its conditional, cutting the conditional would leave that markup behind and
  this comparison would fail.
* **The client and the server agree.** Endpoint path, honeypot field name,
  field names, and the two length bounds are read from the server modules and
  compared against the JavaScript and the template, so they cannot drift.
* **Nothing new is invented.** The form carries the accepted composer classes,
  every added CSS selector is namespaced, no model text ever reaches markup as
  markup, and the two controls the accepted focus ring never covered get the
  same ring.

There is no JavaScript test runner in this repository (no package.json, and
the pipeline runs none), so the client behaviour is asserted at source level
here, the same way tests/test_journal_frontend.py and its neighbours do.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from flask import render_template_string

from ask_pete_direct_routes import DIRECT_QUESTION_PATH, HONEYPOT_FIELD
from services.ask_pete_direct_service import MAX_CONTACT_UNITS, MAX_QUESTION_UNITS

from tests.ask_pete_direct.support import REPOSITORY_ROOT, DirectRouteTestCase


PARTIAL = REPOSITORY_ROOT / "templates" / "partials" / "ask_pete_evidence_companion.html"
SCRIPT = REPOSITORY_ROOT / "static" / "js" / "ask-pete-evidence-companion.js"
STYLESHEET = REPOSITORY_ROOT / "static" / "css" / "ask-pete-resume-evidence.css"

# The whole addition, including the blank line that separates it from what
# follows, so cutting it restores the partial's pre-package source exactly. The
# leading `{%-` is what makes the flag-off render byte-identical: it strips the
# blank line and indentation that would otherwise survive as stray whitespace.
DIRECT_BLOCK = re.compile(
    r"[ \t]*\{%-\s*if config\.get\('PEERSLATE_ASK_PETE_DIRECT_ENABLED'"
    r".*?\{%\s*endif\s*%\}\n\n",
    re.DOTALL,
)

RENDER_CONTEXT = {
    "portfolio_contact_url": "/petec/contact",
    "portfolio_resume_url": "/petec/resume",
    "ask_pete_evidence_preview": None,
}

# Everything appended by this package, isolated from the accepted stylesheet.
DIRECT_CSS_MARKER = "PS-ASK-PETE-DIRECT-001 - the private question form"


def direct_stylesheet_section():
    """Everything from the opening of this package's banner comment onward."""
    text = STYLESHEET.read_text(encoding="utf-8")
    return text[text.rindex("/*", 0, text.index(DIRECT_CSS_MARKER)) :]


def direct_script_section():
    """The JavaScript this package added, by its own two markers."""
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index("PS-ASK-PETE-DIRECT-001: the private question form")
    end = text.index("function renderHandoff(payload)")
    return text[start:end]


class FlagOffIsUnchangedTests(DirectRouteTestCase):
    def render(self, source, *, enabled):
        client, _ = self.make_app(enabled=enabled)
        with self.app.test_request_context("/petec/resume"):
            return render_template_string(source, **RENDER_CONTEXT)

    def test_the_conditional_block_exists_and_is_cuttable(self):
        source = PARTIAL.read_text(encoding="utf-8")
        self.assertEqual(len(DIRECT_BLOCK.findall(source)), 1)

    def test_flag_off_renders_byte_identically_to_the_template_without_the_block(self):
        source = PARTIAL.read_text(encoding="utf-8")
        stripped = DIRECT_BLOCK.sub("", source)
        self.assertNotIn("ask-pete-direct", stripped)

        with_block = self.render(source, enabled=False)
        without_block = self.render(stripped, enabled=False)
        self.assertEqual(with_block, without_block)

    def test_flag_off_leaves_no_trace_of_the_private_path_in_the_html(self):
        html = self.render(PARTIAL.read_text(encoding="utf-8"), enabled=False)
        for token in ("ask-pete-direct", DIRECT_QUESTION_PATH, HONEYPOT_FIELD):
            with self.subTest(token=token):
                self.assertNotIn(token, html)

    def test_a_non_boolean_flag_value_renders_nothing(self):
        """`is sameas true` matches the blueprint's own `is True` check."""
        for value in ("true", "True", 1, "1", [1]):
            with self.subTest(value=value):
                html = self.render(PARTIAL.read_text(encoding="utf-8"), enabled=value)
                self.assertNotIn("ask-pete-direct", html)

    def test_flag_on_renders_one_hidden_config_element_and_nothing_visible(self):
        html = self.render(PARTIAL.read_text(encoding="utf-8"), enabled=True)
        self.assertEqual(html.count("data-ask-pete-direct-config"), 1)
        self.assertIn(f'data-ask-pete-direct-endpoint="{DIRECT_QUESTION_PATH}"', html)
        # The element is hidden and carries no text: the form is built by the
        # controller inside the handoff card, not rendered here.
        element = re.search(r"<div\s+data-ask-pete-direct-config.*?</div>", html, re.S)
        self.assertIsNotNone(element)
        self.assertIn("hidden", element.group(0))
        self.assertTrue(element.group(0).endswith("></div>"), element.group(0))

    def test_the_template_never_calls_url_for_on_the_unregistered_blueprint(self):
        source = PARTIAL.read_text(encoding="utf-8")
        self.assertNotIn("url_for('ask_pete_direct", source)
        self.assertNotIn('url_for("ask_pete_direct', source)


class ClientServerAgreementTests(unittest.TestCase):
    def test_the_template_endpoint_matches_the_blueprints_rule(self):
        source = PARTIAL.read_text(encoding="utf-8")
        self.assertIn(
            f'data-ask-pete-direct-endpoint="{DIRECT_QUESTION_PATH}"', source
        )

    def test_the_script_honeypot_field_matches_the_server_constant(self):
        self.assertIn(
            f"const DIRECT_HONEYPOT_FIELD = '{HONEYPOT_FIELD}';",
            SCRIPT.read_text(encoding="utf-8"),
        )

    def test_the_script_bounds_match_the_sql_check_constraints(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            f"const MAX_DIRECT_QUESTION_LENGTH = {MAX_QUESTION_UNITS};", script
        )
        self.assertIn(
            f"const MAX_DIRECT_CONTACT_LENGTH = {MAX_CONTACT_UNITS};", script
        )

    def test_the_script_sends_exactly_the_fields_the_endpoint_accepts(self):
        section = direct_script_section()
        self.assertIn("const body = { question, consent: true };", section)
        self.assertIn("body.contact = contact;", section)
        self.assertIn("body[DIRECT_HONEYPOT_FIELD] = honeypotInput.value;", section)
        for forbidden in ("recipient", "owner", "consent_version", "user_key"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f"body.{forbidden}", section)

    def test_the_script_proves_same_origin_and_carries_an_idempotency_key(self):
        section = direct_script_section()
        self.assertIn("'X-PeerSlate-Request': 'same-origin'", section)
        self.assertIn("'Idempotency-Key': requestKey", section)


class ConsentAndTruthfulnessTests(unittest.TestCase):
    def setUp(self):
        self.section = direct_script_section()

    def test_nothing_is_sent_without_an_explicit_tick(self):
        self.assertIn("if (!consentInput.checked)", self.section)
        self.assertIn("consent: true", self.section)
        # The checked box is what sets the flag; there is no other path that
        # can put consent: true on the wire.
        self.assertEqual(self.section.count("consent: true"), 1)

    def test_the_submit_is_never_automatic(self):
        for forbidden in (
            "form.submit()",
            "requestSubmit(",
            "setTimeout(() => form",
            "autoSend",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.section)
        self.assertIn("event.preventDefault();", self.section)

    def test_the_consent_copy_states_storage_privacy_and_retention(self):
        consent = re.search(r"consent: \"(.*?)\",\n", self.section, re.S).group(1)
        for claim in (
            "stored privately",
            "Only Pete can read them",
            "never published",
            "never used to teach Ask Pete",
            "nothing is sent back automatically",
            "he archives what he has read",
            "nothing here is removed on an automatic timetable",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, consent)

    def test_the_consent_copy_promises_no_retention_this_package_cannot_keep(self):
        """Owner decision 2026-08-08 ("published always"): a sentence a visitor
        reads must be true today.

        Nothing in this package expires, purges, or deletes a stored question -
        there is no delete procedure at all, by design - so the copy must not
        name a period after which anything happens on its own. If the
        scheduled-maintenance leg lands, the promise can be strengthened AND
        this test tightened in the same change; until then a timed claim here
        would be false the moment it was published.
        """
        consent = re.search(r"consent: \"(.*?)\",\n", self.section, re.S).group(1)
        for false_promise in (
            "90 days",
            "180",
            "retention policy",
            "automatically deleted",
            "will be deleted",
            "expire",
        ):
            with self.subTest(false_promise=false_promise):
                self.assertNotIn(false_promise, consent)
        self.assertIsNone(
            re.search(r"\b\d+\s*(day|month|year)", consent),
            "the consent copy names a retention period nothing implements",
        )

    def test_no_state_claims_a_reply_or_a_receipt(self):
        for overclaim in (
            "we will reply",
            "expect a response",
            "confirmation email",
            "you will hear back",
        ):
            with self.subTest(overclaim=overclaim):
                self.assertNotIn(overclaim, self.section.lower())

    def test_every_failure_state_says_not_sent_in_words(self):
        for key in ("needQuestion", "tooLong", "contactTooLong", "needConsent",
                    "limited", "unavailable", "error"):
            with self.subTest(state=key):
                value = re.search(rf"{key}: [`'\"](.*?)[`'\"],\n", self.section, re.S)
                self.assertIsNotNone(value, key)
                self.assertIn("Not sent", value.group(1))

    def test_the_four_response_states_are_all_handled(self):
        for token in (
            "result.state === 'already_sent'",
            "response.status === 429",
            "response.status === 422",
            ".catch(",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.section)


class SafeDomTests(unittest.TestCase):
    def setUp(self):
        self.section = direct_script_section()

    def test_no_markup_is_ever_built_from_a_string(self):
        for forbidden in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "document.write",
            "eval(",
            "new Function",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.section)

    def test_the_models_suggested_question_is_placed_as_a_value_not_as_markup(self):
        self.assertIn(
            "questionInput.value = safeText(payload.handoff.question).trim();",
            self.section,
        )

    def test_the_servers_message_is_placed_with_text_content(self):
        self.assertIn("stateLine.textContent = message;", self.section)

    def test_the_optional_config_element_cannot_disable_the_whole_companion(self):
        """It must not join `elements`, whose all-or-nothing guard would turn
        the entire companion off whenever the private path is off."""
        script = SCRIPT.read_text(encoding="utf-8")
        elements_block = script[
            script.index("const elements = {") : script.index(
                "if (Object.values(elements).some"
            )
        ]
        self.assertNotIn("directConfig", elements_block)
        self.assertNotIn("ask-pete-direct", elements_block)
        self.assertIn(
            "const directConfig = companion.querySelector('[data-ask-pete-direct-config]');",
            script,
        )

    def test_the_endpoint_from_the_dom_is_revalidated_as_a_same_origin_path(self):
        self.assertIn(
            "isSafeSameOriginPath(directConfig.dataset.askPeteDirectEndpoint)",
            SCRIPT.read_text(encoding="utf-8"),
        )


class AccessibilityTests(unittest.TestCase):
    def setUp(self):
        self.section = direct_script_section()
        self.css = direct_stylesheet_section()

    def test_both_fields_are_labelled_and_the_contact_field_is_described(self):
        self.assertIn("questionLabel.htmlFor = questionId;", self.section)
        self.assertIn("contactLabel.htmlFor = contactId;", self.section)
        self.assertIn(
            "contactInput.setAttribute('aria-describedby', contactHelpId);", self.section
        )

    def test_the_state_line_is_a_live_region_and_also_reaches_the_shared_one(self):
        self.assertIn("stateLine.setAttribute('role', 'status');", self.section)
        self.assertIn("stateLine.setAttribute('aria-live', 'polite');", self.section)
        self.assertIn("setStatus(message);", self.section)

    def test_the_honeypot_is_hidden_from_assistive_technology_and_the_tab_order(self):
        self.assertIn("honeypot.setAttribute('aria-hidden', 'true');", self.section)
        self.assertIn("honeypotInput.tabIndex = -1;", self.section)
        self.assertIn("honeypotInput.autocomplete = 'off';", self.section)
        self.assertIn(".ask-pete-direct__honeypot {", self.css)

    def test_the_two_new_controls_get_the_accepted_focus_ring(self):
        self.assertIn(".ask-pete-direct__agree input:focus-visible", self.css)
        self.assertIn(".ask-pete-direct > summary:focus-visible", self.css)
        self.assertIn("outline: 3px solid #145fc1; outline-offset: 3px;", self.css)

    def test_the_interactive_targets_are_at_least_the_house_minimum(self):
        self.assertIn("min-height: 2.75rem;", self.css)

    def test_a_state_never_relies_on_colour_alone(self):
        """Every problem state's TEXT begins "Not sent"; the colour is a second
        signal (WCAG 2.2 1.4.1)."""
        self.assertIn("Colour is a second signal", self.css)
        self.assertIn("ask-pete-direct__state--problem", self.section)


class AdditiveStyleTests(unittest.TestCase):
    def setUp(self):
        self.css = direct_stylesheet_section()

    def test_every_added_selector_is_namespaced_to_this_package(self):
        without_comments = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S)
        rules = re.findall(r"^([^@}\s][^{}]*)\{", without_comments, re.M)
        self.assertTrue(rules)
        for rule in rules:
            for selector in rule.split(","):
                selector = selector.strip()
                if not selector:
                    continue
                with self.subTest(selector=selector):
                    self.assertIn("ask-pete-direct", selector)

    def test_the_form_reuses_the_accepted_composer_idiom(self):
        section = direct_script_section()
        self.assertIn(
            "makeElement('form', 'ask-pete-evidence-composer ask-pete-direct__form')",
            section,
        )
        self.assertIn("makeElement('div', 'ask-pete-evidence-composer__field')", section)
        self.assertIn("makeElement('div', 'ask-pete-evidence-composer__meta')", section)

    def test_no_operating_system_driven_dark_variant_is_introduced(self):
        self.assertNotIn("prefers-color-scheme", self.css)

    def test_forced_colours_are_covered_without_editing_the_accepted_block(self):
        self.assertIn("@media (forced-colors: active)", self.css)
        whole = STYLESHEET.read_text(encoding="utf-8")
        self.assertEqual(whole.count("@media (forced-colors: active)"), 2)

    def test_the_addition_is_appended_after_every_accepted_rule(self):
        whole = STYLESHEET.read_text(encoding="utf-8")
        self.assertLess(
            whole.index(".ask-pete-evidence-composer__meta button"),
            whole.index(DIRECT_CSS_MARKER),
        )


if __name__ == "__main__":
    unittest.main()
