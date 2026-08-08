"""The owner-only pull inbox: authorization, truthfulness, and no delete path.

``@owner_required`` is applied to the page AND to the action independently -
protecting only the page is the classic mistake, so both are tested against an
anonymous visitor, a signed-in non-owner, and an unconfigured allowlist.
"""

from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone

from ask_pete_direct_routes import (
    INBOX_NOTICES,
    OWNER_INBOX_PATH,
    PLANNED_RATE_LIMITS,
)

from tests.ask_pete_direct.support import (
    OTHER_USER_KEY,
    OWNER_USER_KEY,
    REPOSITORY_ROOT,
    DirectRouteTestCase,
    form_headers,
)


TEMPLATE = REPOSITORY_ROOT / "templates" / "ask_pete_inbox.html"

QUESTION_FIXTURE = "6f1b7e3a-8a4a-4a1e-9f0e-2b6c9f7d1a55"
OTHER_FIXTURE = "0b2c4d6e-1111-4222-8333-444455556666"
VERSION_STAMP = "00000000000004d2"

STATUS_PATH = f"/owner/ask-pete-inbox/{QUESTION_FIXTURE}/status"


def row(**overrides):
    record = {
        "recruiter_question_key": QUESTION_FIXTURE,
        "question_status": "new",
        "question_text": "Has Pete run a hardware/software integration himself?",
        "contact_text": "Dana Reyes, Northwind Talent",
        "consent_version": "ask-pete-direct-consent.v1",
        "created_at_utc": datetime(2026, 8, 8, 9, 30, tzinfo=timezone.utc),
        "status_changed_at_utc": None,
        "row_version": bytes.fromhex(VERSION_STAMP),
    }
    record.update(overrides)
    return record


def counts(total=1, new=1):
    return [{"total_count": total, "new_count": new}]


class AuthorizationTests(DirectRouteTestCase):
    def test_an_anonymous_visitor_gets_a_bare_404_from_both_routes(self):
        client, database = self.make_app(result_sets=[[row()], counts()])
        page = client.get(OWNER_INBOX_PATH)
        action = client.post(
            STATUS_PATH,
            data={"status": "read", "expected_version": VERSION_STAMP},
            headers=form_headers(),
        )
        self.assertEqual(page.status_code, 404)
        self.assertEqual(action.status_code, 404)
        self.assertEqual(database.calls, [])

    def test_a_signed_in_non_owner_gets_a_bare_404_from_both_routes(self):
        client, database = self.make_app(
            dev_user_key=OTHER_USER_KEY, result_sets=[[row()], counts()]
        )
        self.assertEqual(client.get(OWNER_INBOX_PATH).status_code, 404)
        self.assertEqual(
            client.post(
                STATUS_PATH,
                data={"status": "read", "expected_version": VERSION_STAMP},
                headers=form_headers(),
            ).status_code,
            404,
        )
        self.assertEqual(database.calls, [])

    def test_an_unconfigured_owner_allowlist_locks_everyone_out(self):
        client, database = self.make_app(
            owner_user_keys="", dev_user_key=OWNER_USER_KEY,
            result_sets=[[row()], counts()],
        )
        self.assertEqual(client.get(OWNER_INBOX_PATH).status_code, 404)
        self.assertEqual(database.calls, [])

    def test_the_flag_being_off_hides_the_inbox_from_the_owner_too(self):
        client, database = self.make_app(
            enabled=False, dev_user_key=OWNER_USER_KEY,
            result_sets=[[row()], counts()],
        )
        self.assertEqual(client.get(OWNER_INBOX_PATH).status_code, 404)
        self.assertEqual(database.calls, [])

    def test_the_owner_can_open_the_page(self):
        client, database = self.make_app(
            dev_user_key=OWNER_USER_KEY, result_sets=[[row()], counts()]
        )
        response = client.get(OWNER_INBOX_PATH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.procedures, ["usp_ListRecruiterQuestionsForOwner"])
        self.assertEqual(database.parameters()["@UserKey"], OWNER_USER_KEY)


class RenderTests(DirectRouteTestCase):
    def open_inbox(self, rows=None, count_rows=None, query=""):
        client, database = self.make_app(
            dev_user_key=OWNER_USER_KEY,
            result_sets=[rows if rows is not None else [row()], count_rows or counts()],
        )
        response = client.get(OWNER_INBOX_PATH + query)
        return response, response.get_data(as_text=True), database

    def test_the_question_and_contact_are_shown_to_their_owner(self):
        _, html, _ = self.open_inbox()
        self.assertIn("Has Pete run a hardware/software integration himself?", html)
        self.assertIn("Dana Reyes, Northwind Talent", html)

    def test_a_question_with_no_contact_says_so_rather_than_showing_a_blank(self):
        _, html, _ = self.open_inbox(rows=[row(contact_text=None)])
        self.assertIn("no contact details", html)

    def test_the_page_never_claims_a_reply_can_be_sent_from_it(self):
        _, html, _ = self.open_inbox()
        self.assertIn("outbound channel", html)
        self.assertIn("PeerSlate cannot send a reply for you", " ".join(html.split()))
        for overclaim in ("Reply to sender", "Send reply", "mailto:"):
            with self.subTest(overclaim=overclaim):
                self.assertNotIn(overclaim, html)

    def test_the_counts_are_the_true_ones_not_the_page_length(self):
        _, html, _ = self.open_inbox(rows=[row()], count_rows=counts(total=240, new=7))
        self.assertIn("7 unread of 240", html)
        self.assertIn("Showing the 1 most recent.", html)

    def test_archived_are_excluded_by_default_and_included_on_request(self):
        _, html, database = self.open_inbox()
        self.assertEqual(database.parameters()["@IncludeArchived"], 0)
        self.assertIn("Show archived", html)

        _, archived_html, archived_database = self.open_inbox(query="?archived=1")
        self.assertEqual(archived_database.parameters()["@IncludeArchived"], 1)
        self.assertIn("Hide archived", archived_html)

    def test_each_question_offers_only_the_transitions_it_does_not_already_have(self):
        _, html, _ = self.open_inbox(rows=[row(question_status="new")])
        self.assertIn("Mark read", html)
        self.assertIn("Archive", html)
        self.assertNotIn("Mark unread", html)

        _, archived_html, _ = self.open_inbox(rows=[row(question_status="archived")])
        self.assertIn("Restore to unread", archived_html)
        self.assertNotIn(">Archive<", archived_html)

    def test_every_action_form_carries_the_expected_version(self):
        _, html, _ = self.open_inbox()
        forms = re.findall(r"<form method=\"post\".*?</form>", html, re.S)
        self.assertTrue(forms)
        for form in forms:
            with self.subTest(form=form[:60]):
                self.assertIn(f'name="expected_version" value="{VERSION_STAMP}"', form)
                self.assertIn('method="post"', form)

    def test_there_is_no_delete_control_anywhere_on_the_page(self):
        """Only the three real transitions are offered, on every status."""
        _, html, _ = self.open_inbox(
            rows=[row(question_status=status) for status in ("new", "read", "archived")],
            count_rows=counts(total=3, new=1),
        )
        submitted = set(re.findall(r'name="status" value="([^"]+)"', html))
        self.assertEqual(submitted, {"new", "read", "archived"})
        for forbidden in ('value="delete"', ">Delete<", "Remove permanently", "Purge"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)
        # The only place the word appears at all is the truthful footnote.
        self.assertEqual(html.lower().count("delete"), 1)

    def test_the_page_is_hardened_and_carries_no_script(self):
        response, html, _ = self.open_inbox()
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(
            response.headers["X-Robots-Tag"], "noindex, nofollow, noarchive"
        )
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertIn('name="robots" content="noindex, nofollow, noarchive"', html)
        self.assertNotIn("<script", html)

    def test_an_empty_inbox_reads_as_empty_not_as_broken(self):
        _, html, _ = self.open_inbox(rows=[], count_rows=counts(total=0, new=0))
        self.assertIn("0 unread of 0", html)
        self.assertIn("Nothing waiting", html)

    def test_a_storage_failure_says_so_and_never_implies_an_empty_inbox(self):
        from services.database_service import DatabaseServiceError

        client, _ = self.make_app(
            dev_user_key=OWNER_USER_KEY,
            error=DatabaseServiceError("Database procedure failed."),
        )
        response = client.get(OWNER_INBOX_PATH)
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn("could not be read", html)
        self.assertNotIn("Nothing waiting", html)
        self.assertNotIn("usp_", html)

    def test_only_a_known_notice_key_can_reach_the_page(self):
        for state, expected in INBOX_NOTICES.items():
            with self.subTest(state=state):
                _, html, _ = self.open_inbox(query=f"?state={state}")
                self.assertIn(expected, html)

        _, injected, _ = self.open_inbox(query="?state=%3Cscript%3Ex")
        self.assertNotIn("<script", injected)
        self.assertNotIn("state=", injected.split("<style>")[0])


class StatusActionTests(DirectRouteTestCase):
    def act(self, data, *, headers=None, rows=None, error=None):
        client, database = self.make_app(
            dev_user_key=OWNER_USER_KEY,
            rows=rows
            if rows is not None
            else [
                {
                    "outcome": "success",
                    "question_status": data.get("status", "read"),
                    "row_version": bytes.fromhex("00000000000004d3"),
                }
            ],
            error=error,
        )
        response = client.post(
            STATUS_PATH, data=data, headers=headers if headers is not None else form_headers()
        )
        return response, database

    def test_marking_read_calls_the_version_fenced_procedure_and_redirects(self):
        response, database = self.act(
            {"status": "read", "expected_version": VERSION_STAMP}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            database.procedures, ["usp_SetRecruiterQuestionStatusForOwner"]
        )
        self.assertEqual(
            database.parameters(),
            {
                "@UserKey": OWNER_USER_KEY,
                "@RecruiterQuestionKey": QUESTION_FIXTURE,
                "@Status": "read",
                "@ExpectedRowVersion": bytes.fromhex(VERSION_STAMP),
            },
        )
        self.assertIn("state=read", response.headers["Location"])

    def test_archiving_and_restoring_are_both_available(self):
        for status in ("archived", "new"):
            with self.subTest(status=status):
                response, database = self.act(
                    {"status": status, "expected_version": VERSION_STAMP}
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(database.parameters()["@Status"], status)

    def test_the_archived_view_is_preserved_across_the_redirect(self):
        response, _ = self.act(
            {"status": "read", "expected_version": VERSION_STAMP, "archived": "1"}
        )
        self.assertIn("archived=1", response.headers["Location"])

    def test_a_stale_version_changes_nothing_and_says_so(self):
        response, _ = self.act(
            {"status": "archived", "expected_version": VERSION_STAMP},
            rows=[{"outcome": "changed", "question_status": None, "row_version": None}],
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("state=changed", response.headers["Location"])

    def test_an_unknown_status_never_reaches_the_database(self):
        for status in ("deleted", "purged", "", None):
            with self.subTest(status=status):
                data = {"expected_version": VERSION_STAMP}
                if status is not None:
                    data["status"] = status
                response, database = self.act(data, rows=[])
                self.assertEqual(response.status_code, 302)
                self.assertIn("state=unavailable", response.headers["Location"])
                self.assertEqual(database.calls, [])

    def test_a_malformed_question_key_never_reaches_the_database(self):
        client, database = self.make_app(dev_user_key=OWNER_USER_KEY, rows=[])
        response = client.post(
            "/owner/ask-pete-inbox/not-a-uuid/status",
            data={"status": "read", "expected_version": VERSION_STAMP},
            headers=form_headers(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(database.calls, [])

    def test_a_cross_site_form_post_is_refused(self):
        for headers in (
            form_headers(Origin="https://evil.example"),
            form_headers(Sec_Fetch_Site="cross-site"),
        ):
            with self.subTest(headers=headers):
                response, database = self.act(
                    {"status": "read", "expected_version": VERSION_STAMP},
                    headers=headers,
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(database.calls, [])

    def test_a_post_proving_nothing_at_all_is_refused(self):
        """Fail closed: neither Origin nor Sec-Fetch-Site is not "probably
        fine", it is unproven."""
        response, database = self.act(
            {"status": "read", "expected_version": VERSION_STAMP},
            headers={},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(database.calls, [])

    def test_the_action_accepts_only_post(self):
        client, database = self.make_app(dev_user_key=OWNER_USER_KEY, rows=[])
        for method in ("get", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(
                    getattr(client, method)(STATUS_PATH).status_code, 405
                )
        self.assertEqual(database.calls, [])


class RouteSurfaceTests(unittest.TestCase):
    def test_the_blueprint_exposes_exactly_three_routes_and_no_delete(self):
        from flask import Flask

        import ask_pete_direct_routes

        probe = Flask("inbox_rule_probe")
        probe.register_blueprint(ask_pete_direct_routes.ask_pete_direct)
        rules = {
            rule.endpoint: (str(rule), sorted(rule.methods - {"HEAD", "OPTIONS"}))
            for rule in probe.url_map.iter_rules()
            if rule.endpoint.startswith("ask_pete_direct.")
        }
        self.assertEqual(
            rules,
            {
                "ask_pete_direct.submit_direct_question": (
                    "/api/ask-pete/direct-question", ["POST"]
                ),
                "ask_pete_direct.owner_inbox": ("/owner/ask-pete-inbox", ["GET"]),
                "ask_pete_direct.set_question_status": (
                    "/owner/ask-pete-inbox/<string:question_key>/status", ["POST"]
                ),
            },
        )

    def test_both_write_endpoints_carry_a_planned_rate_limit(self):
        self.assertEqual(
            set(PLANNED_RATE_LIMITS),
            {
                "ask_pete_direct.submit_direct_question",
                "ask_pete_direct.set_question_status",
            },
        )

    def test_owner_required_guards_the_page_and_the_action_independently(self):
        import ask_pete_direct_routes

        source = REPOSITORY_ROOT.joinpath("ask_pete_direct_routes.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count("\n@owner_required\n"), 2)
        for view in ("owner_inbox", "set_question_status"):
            with self.subTest(view=view):
                index = source.index(f"def {view}(")
                self.assertIn("@owner_required", source[index - 120 : index])


class TemplateTruthfulnessTests(DirectRouteTestCase):
    def setUp(self):
        self.template = TEMPLATE.read_text(encoding="utf-8")
        client, _ = self.make_app(
            dev_user_key=OWNER_USER_KEY, result_sets=[[row()], counts()]
        )
        self.rendered = client.get(OWNER_INBOX_PATH).get_data(as_text=True)

    def test_the_page_is_server_rendered_with_no_client_code(self):
        for forbidden in ("<script", "onclick", "fetch(", "addEventListener"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.template)
                self.assertNotIn(forbidden, self.rendered)

    def test_the_page_reopens_no_operating_system_dark_variant(self):
        """Checked on the RENDERED page: the template's own comment explains
        why there is no such variant, and a comment is not a rule."""
        self.assertNotIn("prefers-color-scheme", self.rendered)
        self.assertIn(
            ":root:not([data-ps-dark-theme]) { color-scheme: light; }", self.rendered
        )

    def test_the_retention_note_matches_what_senders_are_told(self):
        self.assertIn("archive after 90 days and remove after 180", self.template)
        self.assertIn("never used to teach Ask Pete", self.template)

    def test_nothing_on_the_page_deletes(self):
        self.assertIn("nothing on this page deletes anything", self.template.lower())


if __name__ == "__main__":
    unittest.main()
