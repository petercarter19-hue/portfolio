"""Workshop D saved-slate use disclosure — PS-WORKSHOP-USE-DISCLOSURE-001.

Covers the one new read (services/opportunity_use_service.py ->
usp_GetOpportunitySlateUseForOwner), its three Workshop render surfaces
(item detail, edit, delete-confirm), the degraded unavailable state, the
anonymous zero-call promise, and the static construction of the
PS-OPPSLATE-USE-001 migration/rollback/verifier/registry entry and the
procedure allowlist. Everything is mocked at the service or database seam —
no real database, no provider call, no network. The disposable-database gate
rehearsal (apply, idempotent reapply, verify, rollback, reapply) is a
separately governed operator step; this offline suite pins both the file
shapes it exercises and the resulting exact-byte registry proof.

Every behavioral test uses a generic fixture member key, never a
Pete-specific identifier.
"""

import json
import re
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import app, limiter
from db import serialize_sql_value
from identity import AuthenticationRequired
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError
from services.knowledge_service import KnowledgeItemListResult
from services.opportunity_use_service import (
    USE_ROW_FIELDS,
    OpportunityUseService,
    OpportunityUseServiceError,
    SlateUse,
)
from scripts.migration_registry import executable_sha256

ROOT = Path(__file__).resolve().parents[1]

ITEM_KEY = "11111111-1111-1111-1111-111111111111"
VERSION_TOKEN = "0000000000000001"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

CITED_USE = SlateUse(
    citing_version_count=2,
    latest_saved_at_utc=datetime(2026, 8, 20, 12, 0, 0),
    latest_save_version_number=2,
    cites_latest_saved_version=True,
)
OLDER_ONLY_USE = SlateUse(
    citing_version_count=1,
    latest_saved_at_utc=datetime(2026, 8, 10, 9, 0, 0),
    latest_save_version_number=1,
    cites_latest_saved_version=False,
)


def member(name, user_key):
    return SimpleNamespace(display_name=name, user_key=user_key)


def use_row(**overrides):
    row = {
        "citing_version_count": 2,
        "latest_saved_at_utc": datetime(2026, 8, 20, 12, 0, 0),
        "latest_save_version_number": 2,
        "cites_latest_saved_version": True,
    }
    row.update(overrides)
    return row


def service_get_row(**overrides):
    row = {
        "item_key": ITEM_KEY,
        "status": "confirmed",
        "classification": "work",
        "current_version": 1,
        "confirmed_version": 1,
        "confirmed_at": "2026-07-10T00:00:00Z",
        "archived_at": None,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "version_token": VERSION_TOKEN,
        "version": 1,
        "title": "Systems Engineering Leadership",
        "approved_wording": "You led a system architecture effort end to end.",
        "original_member_wording": "You led a system architecture effort end to end.",
        "body_format": "plain",
        "authored_via": "typed",
        "saved_at": "2026-07-10T00:00:00Z",
        "history": [],
    }
    row.update(overrides)
    return row


def service_list_row(**overrides):
    row = {
        "item_key": ITEM_KEY,
        "status": "confirmed",
        "classification": "work",
        "current_version": 1,
        "confirmed_version": 1,
        "confirmed_at": "2026-07-10T00:00:00Z",
        "archived_at": None,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "version_token": VERSION_TOKEN,
        "title": "Systems Engineering Leadership",
        "body_format": "plain",
        "authored_via": "typed",
    }
    row.update(overrides)
    return row


def collapse(body):
    """Whitespace-collapse a rendered page so assertions survive Jinja's
    source-line wrapping."""
    return " ".join(body.split())


class FakeUseDatabase:
    """Records the exact procedure call and returns a scripted result."""

    def __init__(self, result_sets):
        self.result_sets = result_sets
        self.calls = []

    def execute_procedure(self, procedure_name, parameters=None):
        self.calls.append((procedure_name, list(parameters or [])))
        return self.result_sets


class SlateUseServiceTests(unittest.TestCase):
    """The service contract: exact threading, exact shape, zero substitution."""

    def run_read(self, result_sets, *, user_key="member-use-1", item_key=ITEM_KEY):
        database = FakeUseDatabase(result_sets)
        service = OpportunityUseService(database=database)
        value = service.get_slate_use_for_owner(user_key, item_key)
        return value, database

    def test_a_cited_row_deserializes_exactly(self):
        value, database = self.run_read([[use_row()]])

        self.assertEqual(
            database.calls,
            [
                (
                    "usp_GetOpportunitySlateUseForOwner",
                    [("@UserKey", "member-use-1"), ("@KnowledgeItemKey", ITEM_KEY)],
                )
            ],
        )
        self.assertEqual(value.citing_version_count, 2)
        self.assertEqual(value.latest_save_version_number, 2)
        self.assertIs(value.cites_latest_saved_version, True)
        self.assertEqual(
            value.latest_saved_at_utc,
            datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_the_database_serialized_iso_timestamp_becomes_aware_utc(self):
        serialized = serialize_sql_value(datetime(2026, 8, 20, 12, 0, 0))
        self.assertEqual(serialized, "2026-08-20T12:00:00")

        value, _ = self.run_read([[use_row(latest_saved_at_utc=serialized)]])

        self.assertEqual(
            value.latest_saved_at_utc,
            datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_an_aware_driver_timestamp_is_normalized_to_utc(self):
        source = datetime(
            2026, 8, 20, 14, 0, 0, tzinfo=timezone(timedelta(hours=2))
        )

        value, _ = self.run_read([[use_row(latest_saved_at_utc=source)]])

        self.assertEqual(
            value.latest_saved_at_utc,
            datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
        )

    def test_zero_rows_return_none_not_an_error(self):
        for result_sets in ([[]], []):
            value, _ = self.run_read(result_sets)
            self.assertIsNone(value)

    def test_only_exact_sql_bit_values_are_accepted(self):
        for raw, expected in ((False, False), (0, False), (True, True), (1, True)):
            with self.subTest(raw=raw):
                value, _ = self.run_read(
                    [[use_row(cites_latest_saved_version=raw)]]
                )
                self.assertIs(value.cites_latest_saved_version, expected)

    def test_a_forged_user_key_is_passed_through_unchanged(self):
        """The service never substitutes, derives, or drops the given
        user_key. Authorization is the procedure's job, proven separately by
        PS-OPPSLATE-USE-001_owner_isolation_verify.sql."""
        _, database = self.run_read(
            [[]], user_key="forged-user-key-does-not-exist"
        )
        parameters = dict(database.calls[0][1])
        self.assertEqual(parameters["@UserKey"], "forged-user-key-does-not-exist")

    def test_the_item_key_is_normalized_to_canonical_uuid_form(self):
        _, database = self.run_read(
            [[]], item_key="{11111111-1111-1111-1111-111111111111}"
        )
        parameters = dict(database.calls[0][1])
        self.assertEqual(parameters["@KnowledgeItemKey"], ITEM_KEY)

    def test_a_missing_user_key_never_reaches_the_database(self):
        for bad in ("", "   ", None, 7):
            database = FakeUseDatabase([[]])
            service = OpportunityUseService(database=database)
            with self.assertRaises(OpportunityUseServiceError) as caught:
                service.get_slate_use_for_owner(bad, ITEM_KEY)
            self.assertEqual(caught.exception.code, "no_identity")
            self.assertEqual(database.calls, [])

    def test_a_malformed_item_key_never_reaches_the_database(self):
        for bad in ("not-a-uuid", "", None):
            database = FakeUseDatabase([[]])
            service = OpportunityUseService(database=database)
            with self.assertRaises(OpportunityUseServiceError) as caught:
                service.get_slate_use_for_owner("member-use-1", bad)
            self.assertEqual(caught.exception.code, "invalid")
            self.assertEqual(database.calls, [])

    def test_unexpected_shapes_are_refused(self):
        for result_sets in (
            [[use_row(), use_row()]],  # two rows
            [[use_row()], [use_row()]],  # two result sets
            [[{**use_row(), "excerpt": "leak"}]],  # widened row
            [[{"citing_version_count": 1}]],  # narrowed row
            [[list(USE_ROW_FIELDS)]],  # non-dict row with the exact field names
        ):
            with self.assertRaises(OpportunityUseServiceError) as caught:
                self.run_read(result_sets)
            self.assertEqual(caught.exception.code, "invalid")

    def test_invalid_values_are_refused(self):
        for overrides in (
            {"citing_version_count": 0},
            {"citing_version_count": False},
            {"citing_version_count": "many"},
            {"latest_save_version_number": -1},
            {"latest_save_version_number": True},
            {"latest_saved_at_utc": "2026-08-20"},
            {"latest_saved_at_utc": "not-a-datetime"},
            {"latest_saved_at_utc": date(2026, 8, 20)},
            {"latest_saved_at_utc": 7},
            {"latest_saved_at_utc": None},
            {"cites_latest_saved_version": None},
            {"cites_latest_saved_version": "0"},
            {"cites_latest_saved_version": 2},
        ):
            with self.assertRaises(OpportunityUseServiceError) as caught:
                self.run_read([[use_row(**overrides)]])
            self.assertEqual(caught.exception.code, "invalid")

    def test_the_exact_field_contract_matches_the_procedure(self):
        self.assertEqual(
            USE_ROW_FIELDS,
            {
                "citing_version_count",
                "latest_saved_at_utc",
                "latest_save_version_number",
                "cites_latest_saved_version",
            },
        )

    def test_the_module_talks_only_to_the_database_service(self):
        """No provider, AI, or network import — this module is a single
        owner-scoped SQL read and nothing else."""
        source = (ROOT / "services" / "opportunity_use_service.py").read_text(
            encoding="utf-8"
        )
        for forbidden in ("anthropic", "openai", "requests", "httpx", "urllib"):
            self.assertNotIn(forbidden, source)
        service_imports = re.findall(r"from services\.(\w+) import", source)
        self.assertEqual(service_imports, ["database_service"])


class WorkshopUseRouteTestCase(unittest.TestCase):
    """Shared harness mirroring tests/test_workshop_flows.py exactly."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_fixture_flag = app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = False
        self.identity_patch = patch(
            "workshop_routes.get_current_identity",
            return_value=member("Checkpoint Member", "member-checkpoint-1"),
        )
        self.identity_patch.start()
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        self.identity_patch.stop()
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_DEV_FIXTURE"] = self.original_fixture_flag

    def library_page(self, use_result, *, query="", get_row=None):
        """GET /app/workshop with one selected item and a scripted use read.

        ``use_result`` is a SlateUse, None, or an exception instance."""
        kwargs = (
            {"side_effect": use_result}
            if isinstance(use_result, Exception)
            else {"return_value": use_result}
        )
        with patch(
            "workshop_routes.knowledge_service.confirm_authored_knowledge_backlog_for_owner",
            return_value={"confirmed_count": 0, "remaining_count": 0},
        ), patch(
            "workshop_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=KnowledgeItemListResult(
                items=[get_row or service_list_row()], total_count=1
            ),
        ), patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(
                **({"status": get_row["status"]} if get_row else {})
            ),
        ), patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner",
            **kwargs,
        ) as use_mock:
            response = self.client.get(f"/app/workshop?item={ITEM_KEY}{query}")
        return response, use_mock


class DetailDisclosureTests(WorkshopUseRouteTestCase):
    def test_a_cited_item_shows_the_real_citation_state(self):
        response, use_mock = self.library_page(CITED_USE)

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)
        self.assertIn(
            "Used by Opportunity Slate — cited in 2 saved versions, "
            "including your latest save",
            body,
        )
        # The chip carries the short badge form, so the string appears at
        # both render sites.
        self.assertGreaterEqual(body.count("Used by Opportunity Slate"), 2)
        self.assertNotIn("Not used elsewhere", body)

    def test_an_older_version_only_citation_is_still_disclosed(self):
        response, _ = self.library_page(OLDER_ONLY_USE)

        body = collapse(response.data.decode("utf-8"))
        self.assertIn(
            "Used by Opportunity Slate — cited in 1 saved version", body
        )
        self.assertNotIn("including your latest save", body)

    def test_an_uncited_item_keeps_the_truthful_negative(self):
        """"Not used elsewhere" renders ONLY on a successful zero-row read."""
        response, use_mock = self.library_page(None)

        body = collapse(response.data.decode("utf-8"))
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)
        self.assertIn("Not used elsewhere", body)
        self.assertNotIn("Used by Opportunity Slate", body)

    def test_an_unavailable_check_omits_the_row_entirely(self):
        """A failed read must never render a definite negative — the row and
        badge are omitted, and the page still renders."""
        response, _ = self.library_page(DatabaseServiceError("unavailable"))

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        self.assertIn("Systems Engineering Leadership", body)
        self.assertNotIn("Not used elsewhere", body)
        self.assertNotIn("Used by Opportunity Slate", body)
        self.assertNotIn("Downstream use", body)

    def test_a_service_error_is_equally_degrade_safe(self):
        response, _ = self.library_page(
            OpportunityUseServiceError("bad shape", code="invalid")
        )
        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        self.assertNotIn("Not used elsewhere", body)

    def test_an_archived_item_still_gets_the_citation_read(self):
        """Archived items are selectable under the Archived filter and their
        citation state matters most at restore/delete time."""
        archived_row = service_list_row(
            status="archived", archived_at="2026-08-01T00:00:00Z"
        )
        # The default "All current" filter excludes archived rows, so the
        # selection only resolves under the Archived filter — exactly where
        # a member reviews archived items.
        response, use_mock = self.library_page(
            CITED_USE, get_row=archived_row, query="&status=archived"
        )

        self.assertEqual(response.status_code, 200)
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)

    def test_a_caller_supplied_user_key_is_ignored(self):
        """?user_key= changes nothing: the read is keyed by the server-derived
        identity alone."""
        response, use_mock = self.library_page(
            CITED_USE, query="&user_key=someone-else"
        )

        self.assertEqual(response.status_code, 200)
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)
        self.assertNotIn(b"someone-else", response.data)

    def test_two_members_each_see_only_their_own_citation_state(self):
        """Byte canary: the disclosure reflects exactly the key the identity
        resolved, never another member's state."""
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Avery", "member-avery"),
        ):
            avery, avery_mock = self.library_page(CITED_USE)
        with patch(
            "workshop_routes.get_current_identity",
            return_value=member("Morgan", "member-morgan"),
        ):
            morgan, morgan_mock = self.library_page(None)

        avery_mock.assert_called_once_with("member-avery", ITEM_KEY)
        morgan_mock.assert_called_once_with("member-morgan", ITEM_KEY)
        self.assertIn("Used by Opportunity Slate", collapse(avery.data.decode("utf-8")))
        self.assertNotIn(
            "Used by Opportunity Slate", collapse(morgan.data.decode("utf-8"))
        )
        self.assertNotIn(b"member-avery", avery.data)
        self.assertNotIn(b"member-morgan", morgan.data)


class EditDisclosureTests(WorkshopUseRouteTestCase):
    def edit_page(self, use_result):
        kwargs = (
            {"side_effect": use_result}
            if isinstance(use_result, Exception)
            else {"return_value": use_result}
        )
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ), patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner",
            **kwargs,
        ) as use_mock:
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/edit")
        return response, use_mock

    def test_a_cited_item_gets_the_informational_card(self):
        response, use_mock = self.edit_page(CITED_USE)

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)
        self.assertIn("Used by Opportunity Slate", body)
        self.assertIn(
            "cites this item in 2 saved versions, including your latest save",
            body,
        )
        self.assertIn("editing here never rewrites it", body)
        self.assertIn(
            "will show this input as changed rather than current", body
        )
        self.assertIn("this is information, not a restriction", body)
        # The form itself is untouched: same action, same fenced token.
        self.assertIn('name="expected_row_version"', body)
        self.assertIn("Edit information", body)

    def test_an_uncited_item_renders_the_screen_unchanged(self):
        response, _ = self.edit_page(None)

        body = collapse(response.data.decode("utf-8"))
        self.assertNotIn("Used by Opportunity Slate", body)
        self.assertIn("Edit information", body)

    def test_an_unavailable_check_renders_no_card_and_no_claim(self):
        response, _ = self.edit_page(DatabaseServiceError("unavailable"))

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        self.assertNotIn("Used by Opportunity Slate", body)
        self.assertNotIn("Not used elsewhere", body)

    def test_edit_posts_never_consult_the_use_read(self):
        """Warnings inform GET renders only; every POST outcome is unchanged
        and the disclosure read never runs on a write path."""
        with patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner"
        ) as use_mock, patch(
            "workshop_routes.knowledge_service.update_knowledge_item_for_owner",
            return_value={"outcome": "success", "version": 2,
                          "version_token": "0000000000000002"},
        ) as update_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}",
                data={
                    "title": "Systems Engineering Leadership",
                    "wording": "You led a system architecture effort end to end.",
                    "classification": "work",
                    "expected_row_version": VERSION_TOKEN,
                    "save_action": "confirm",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        use_mock.assert_not_called()
        update_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)


class DeleteDisclosureTests(WorkshopUseRouteTestCase):
    def confirm_page(self, use_result):
        kwargs = (
            {"side_effect": use_result}
            if isinstance(use_result, Exception)
            else {"return_value": use_result}
        )
        with patch(
            "workshop_routes.knowledge_service.get_knowledge_item_for_owner",
            return_value=service_get_row(),
        ), patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner",
            **kwargs,
        ) as use_mock:
            response = self.client.get(f"/app/workshop/items/{ITEM_KEY}/delete")
        return response, use_mock

    def test_a_cited_item_names_the_affected_uses_before_deletion(self):
        response, use_mock = self.confirm_page(CITED_USE)

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        use_mock.assert_called_once_with("member-checkpoint-1", ITEM_KEY)
        self.assertIn(
            "Your saved Opportunity Slate cites this item in 2 saved "
            "versions, including your latest save.",
            body,
        )
        self.assertIn("those saved versions stay readable", body)
        self.assertIn("changed rather than current", body)
        # The existing permanent-delete truth and controls are unchanged.
        self.assertIn("permanently deletes this item and its version history", body)
        self.assertIn("Nothing else in your private library is affected.", body)
        self.assertIn('name="confirm_delete"', body)
        self.assertIn("Delete permanently", body)

    def test_an_uncited_item_adds_nothing(self):
        response, _ = self.confirm_page(None)

        body = collapse(response.data.decode("utf-8"))
        self.assertNotIn("Your saved Opportunity Slate cites this item", body)
        self.assertNotIn("could not check just now", body)
        self.assertIn("permanently deletes this item and its version history", body)

    def test_an_unavailable_check_is_named_not_omitted(self):
        """On THIS screen omission would silently remove the guard, so the
        unavailable state is stated plainly — and it never claims either
        way, and never says "Not used elsewhere"."""
        response, _ = self.confirm_page(DatabaseServiceError("unavailable"))

        self.assertEqual(response.status_code, 200)
        body = collapse(response.data.decode("utf-8"))
        self.assertIn(
            "PeerSlate could not check just now whether your saved "
            "Opportunity Slate cites this item.",
            body,
        )
        self.assertNotIn("Not used elsewhere", body)
        self.assertNotIn("Your saved Opportunity Slate cites this item in", body)
        self.assertIn('name="confirm_delete"', body)

    def test_the_delete_post_is_unchanged_and_never_consults_the_read(self):
        with patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner"
        ) as use_mock, patch(
            "workshop_routes.knowledge_service.delete_knowledge_item_for_owner",
            return_value={"outcome": "success", "deleted_version_count": 1},
        ) as delete_mock:
            response = self.client.post(
                f"/app/workshop/items/{ITEM_KEY}/delete",
                data={
                    "expected_row_version": VERSION_TOKEN,
                    "confirm_delete": "delete",
                },
                headers=SAME_ORIGIN_HEADERS,
            )

        use_mock.assert_not_called()
        delete_mock.assert_called_once_with(
            "member-checkpoint-1", ITEM_KEY, VERSION_TOKEN
        )
        self.assertEqual(response.status_code, 302)


class AnonymousZeroCallTests(unittest.TestCase):
    """The anonymous demo path never reaches the disclosure read — the
    module's no-database promise for signed-out visitors holds."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def test_every_disclosure_surface_makes_zero_calls_when_signed_out(self):
        with patch(
            "workshop_routes.get_current_identity",
            side_effect=AuthenticationRequired("Sign in is required."),
        ), patch(
            "workshop_routes.opportunity_use_service.get_slate_use_for_owner"
        ) as use_mock:
            library = self.client.get("/app/workshop")
            edit = self.client.get(f"/app/workshop/items/{ITEM_KEY}/edit")
            confirm = self.client.get(f"/app/workshop/items/{ITEM_KEY}/delete")

        use_mock.assert_not_called()
        self.assertEqual(library.status_code, 200)
        # Unknown keys stay neutral for anonymous visitors too.
        self.assertEqual(edit.status_code, 302)
        self.assertEqual(confirm.status_code, 302)


class AllowlistTests(unittest.TestCase):
    def test_the_procedure_is_allowlisted_exactly_once(self):
        self.assertIn("usp_GetOpportunitySlateUseForOwner", ALLOWED_PROCEDURES)
        source = (ROOT / "services" / "database_service.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count("usp_GetOpportunitySlateUseForOwner"), 1)


class MigrationConstructionTests(unittest.TestCase):
    """Static construction of the PS-OPPSLATE-USE-001 package: the registry
    entry, the forward/rollback pair the gate rehearsal will apply, reapply,
    verify, roll back, and reapply, and the owner-isolation verifier."""

    FORWARD = ROOT / "SQL FIles" / "Migrations" / "PS-OPPSLATE-USE-001_opportunity_slate_use.sql"
    ROLLBACK = ROOT / "SQL FIles" / "Migrations" / "PS-OPPSLATE-USE-001_opportunity_slate_use_rollback.sql"
    VERIFIER = ROOT / "SQL FIles" / "Verification" / "PS-OPPSLATE-USE-001_owner_isolation_verify.sql"

    def test_the_registry_entry_is_exact(self):
        document = json.loads(
            (ROOT / "SQL FIles" / "Migrations" / "registry.json").read_text(
                encoding="utf-8"
            )
        )
        entries = [m for m in document["migrations"] if m["id"] == "PS-OPPSLATE-USE-001"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(
            {"id", "forward", "rollback", "requires", "summary", "gate"},
            set(entry),
        )
        self.assertEqual(
            entry["forward"],
            "SQL FIles/Migrations/PS-OPPSLATE-USE-001_opportunity_slate_use.sql",
        )
        self.assertEqual(
            entry["rollback"],
            "SQL FIles/Migrations/PS-OPPSLATE-USE-001_opportunity_slate_use_rollback.sql",
        )
        self.assertEqual(entry["requires"], ["PS-OPPSLATE-003"])
        gate = entry["gate"]
        self.assertIsInstance(gate, dict)
        self.assertEqual(gate["executable_sha256"], executable_sha256(self.FORWARD))
        self.assertEqual(
            gate["gate_database"], "ps-oppslate-use-001-gate-20260828-r2"
        )
        self.assertEqual(gate["gate_server"], "peerslate")
        self.assertEqual(gate["prerequisites"][-1], "PS-OPPSLATE-003")
        self.assertIn(
            "PS-OPPSLATE-USE-001_owner_isolation_verify.sql returned verified = 1",
            gate["verification"],
        )
        self.assertEqual(gate["operator"], "agent:/root/workshop_implementer")
        self.assertIn("no production database contacted", gate["notes"])
        self.assertTrue(self.FORWARD.is_file())
        self.assertTrue(self.ROLLBACK.is_file())
        self.assertTrue(self.VERIFIER.is_file())

    def test_the_forward_migration_is_additive_and_self_registering(self):
        forward = self.FORWARD.read_text(encoding="utf-8")
        # Idempotent reapply: the whole body sits behind the ledger guard.
        self.assertIn(
            "IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations "
            "WHERE migration_id = N'PS-OPPSLATE-USE-001')",
            forward,
        )
        self.assertIn(
            "CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunitySlateUseForOwner",
            forward,
        )
        self.assertIn("@UserKey nvarchar(300)", forward)
        self.assertNotIn("@OwnerProfileId", forward)
        self.assertIn("owner_profile_id = @ProfileId", forward)
        self.assertNotIn("@CurrentSaveVersion", forward)
        self.assertIn("FROM dbo.opportunity_slates AS slate", forward)
        self.assertIn(
            "saved_result.opportunity_slate_id = slate.opportunity_slate_id",
            forward,
        )
        self.assertIn("GROUP BY slate.current_save_version_number", forward)
        self.assertIn(
            "MAX(saved_result.save_version_number) = slate.current_save_version_number",
            forward,
        )
        # The F6-coupled kind predicate (doubled quotes inside EXEC N'...').
        self.assertIn("evidence_kind = N''knowledge_item''", forward)
        self.assertIn("IX_opportunity_saved_evidence_owner_use", forward)
        self.assertIn(
            "(owner_profile_id, evidence_kind, evidence_key)", forward
        )
        self.assertIn("ONLINE = ON", forward)
        self.assertIn("WAIT_AT_LOW_PRIORITY", forward)
        self.assertIn("MAX_DURATION = 1 MINUTES", forward)
        self.assertIn("ABORT_AFTER_WAIT = SELF", forward)
        self.assertNotIn("The table is small", forward)
        self.assertIn("INSERT dbo.schema_migrations", forward)
        self.assertIn("N'PS-OPPSLATE-USE-001'", forward)
        self.assertIn("SET XACT_ABORT ON;", forward)
        # Additive only: no table/column/row mutation anywhere.
        for forbidden in ("CREATE TABLE", "ALTER TABLE", "DROP TABLE",
                          "UPDATE dbo.opportunity", "DELETE dbo.opportunity"):
            self.assertNotIn(forbidden, forward)
        self.assertIsNone(
            re.search(r"(?mi)^[ \t]*GO[ \t]*\r?$", forward),
            "forward migration contains a GO batch separator",
        )

    def test_the_rollback_drops_both_objects_and_deregisters(self):
        rollback = self.ROLLBACK.read_text(encoding="utf-8")
        self.assertIn(
            "DROP PROCEDURE dbo.usp_GetOpportunitySlateUseForOwner", rollback
        )
        self.assertIn(
            "DROP INDEX IX_opportunity_saved_evidence_owner_use "
            "ON dbo.opportunity_saved_evidence",
            rollback,
        )
        self.assertRegex(rollback, r"DELETE\s+dbo\.schema_migrations")
        self.assertIn("rollback refused because a later migration", rollback)
        self.assertIsNone(re.search(r"(?mi)^[ \t]*GO[ \t]*\r?$", rollback))

    def test_the_verifier_has_three_owners_forged_key_and_outer_rollback(self):
        verifier = self.VERIFIER.read_text(encoding="utf-8")
        for required in (
            "@SubjectA",
            "@SubjectB",
            "@SubjectC",
            "@UserKeyA",
            "@UserKeyB",
            "@UserKeyC",
            "@ProfileIdA",
            "@ProfileIdB",
            "@ProfileIdC",
            "usp_UpsertAppUserFromAuth",
            "N'forged-user-key-does-not-exist'",
            "MUST NOT ENTER OWNER A RESULT",
            "An owner with no slate returned a use row",
            "ROLLBACK TRANSACTION",
            "CAST(1 AS bit) AS verified",
        ):
            self.assertIn(required, verifier)
        self.assertNotIn("COMMIT TRANSACTION", verifier)

    def test_the_verifier_proves_the_disclosure_specific_states(self):
        verifier = self.VERIFIER.read_text(encoding="utf-8")
        for required in (
            # Owner resolution and the F6 kind filter, via OBJECT_DEFINITION.
            "OBJECT_DEFINITION",
            "@OwnerProfileId",
            "owner_profile_id = @ProfileId",
            "evidence_kind = N''knowledge_item''",
            # Any-version scope: an item cited only by an older version.
            "cited only by an older saved version",
            "The cited-in-both-versions aggregates are wrong",
            "cites_latest_saved_version = 1",
            "cites_latest_saved_version = 0",
            # The moment-kind row must not leak through.
            "leaked through the knowledge_item filter",
            # A deleted item's citation still reports.
            "deleted item''s saved-slate citation stopped reporting",
            # The supporting index exists.
            "IX_opportunity_saved_evidence_owner_use",
        ):
            self.assertIn(required, verifier)


if __name__ == "__main__":
    unittest.main()
