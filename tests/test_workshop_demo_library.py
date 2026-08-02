"""Unit tests for services/workshop_demo_library.py — PS-WORKSHOP-001 public
demo library and session play (owner instruction 2026-08-02, doc 20 section
6e).

These exercise the module directly (base content shape/coverage, session
delta merge logic, caps, byte budget) independent of the HTTP routes.
Route-level (HTTP) behavior lives in tests/test_workshop_checkpoint.py's
WorkshopPublicPreviewTests, which this file does not duplicate.
"""

import random
import string
import unittest
import uuid

from app import app
from services import workshop_demo_library as wdl
from tests.test_workshop_checkpoint import service_get_row, service_list_row


LIST_ROW_KEYS = frozenset(service_list_row().keys())
GET_ROW_KEYS = frozenset(service_get_row().keys())


class WorkshopDemoLibraryContentTests(unittest.TestCase):
    """Chunk A: the 17-item Jordan Ellis base library."""

    def test_seventeen_base_items(self):
        self.assertEqual(len(wdl.BASE_ITEMS), 17)

    def test_status_distribution_matches_content_spec(self):
        counts = {}
        for item in wdl.BASE_ITEMS:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        self.assertEqual(counts.get("confirmed"), 11)
        self.assertEqual(counts.get("suggested"), 2)
        self.assertEqual(counts.get("unfinished"), 2)
        self.assertEqual(counts.get("archived"), 2)
        self.assertEqual(sum(counts.values()), 17)

    def test_classification_coverage_includes_every_area(self):
        classifications = {item["classification"] for item in wdl.BASE_ITEMS}
        self.assertEqual(
            classifications, {"work", "personal", "both", "unclassified"}
        )
        # Exactly one "Not set" (unclassified) item, per the content spec.
        unclassified = [
            item for item in wdl.BASE_ITEMS if item["classification"] == "unclassified"
        ]
        self.assertEqual(len(unclassified), 1)

    def test_item_keys_are_stable_deterministic_uuids(self):
        for item in wdl.BASE_ITEMS:
            uuid.UUID(item["item_key"])  # raises ValueError if malformed
        # Deterministic: rebuilding the same slug's key twice agrees, and
        # every key is unique (no accidental collisions across 17 items).
        self.assertEqual(
            wdl._demo_key("rebuilt-patient-intake"),
            wdl._demo_key("rebuilt-patient-intake"),
        )
        keys = [item["item_key"] for item in wdl.BASE_ITEMS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_item_one_carries_real_edit_history(self):
        item_one = wdl.BASE_ITEMS[0]
        self.assertEqual(item_one["title"], "Rebuilt patient intake from 40 minutes to 9")
        self.assertEqual(item_one["current_version"], 3)
        self.assertEqual(item_one["confirmed_version"], 3)
        self.assertEqual(len(item_one["history"]), 3)
        self.assertEqual([h["version"] for h in item_one["history"]], [1, 2, 3])
        for entry in item_one["history"]:
            self.assertEqual(set(entry.keys()), {
                "version", "title", "body_format", "authored_via", "saved_at"
            })

    def test_list_row_shape_matches_real_service_list_row(self):
        rows = wdl.list_rows(wdl.empty_delta())
        self.assertEqual(len(rows), 17)
        for row in rows:
            self.assertEqual(set(row.keys()), LIST_ROW_KEYS)

    def test_get_row_shape_matches_real_service_get_row(self):
        item_one_key = wdl.BASE_ITEMS[0]["item_key"]
        row = wdl.get_row(item_one_key, wdl.empty_delta())
        self.assertIsNotNone(row)
        self.assertEqual(set(row.keys()), GET_ROW_KEYS)

    def test_get_row_returns_none_for_unknown_key(self):
        self.assertIsNone(
            wdl.get_row("00000000-0000-0000-0000-000000000000", wdl.empty_delta())
        )


class WorkshopDemoLibraryMergeTests(unittest.TestCase):
    """Session-delta merge logic, exercised directly (no HTTP)."""

    def setUp(self):
        self.client = app.test_client()

    def test_add_item_appears_in_list_rows(self):
        with self.client.session_transaction() as sess:
            key, error = wdl.add_item(
                sess,
                title="My new item",
                wording="Some wording.",
                classification="work",
                status="confirmed",
            )
            self.assertIsNone(error)
            delta = wdl.read_session_delta(sess)
        rows = wdl.list_rows(delta)
        self.assertIn(key, [row["item_key"] for row in rows])
        self.assertEqual(len(rows), 18)

    def test_add_item_cap_at_four(self):
        with self.client.session_transaction() as sess:
            for i in range(wdl.MAX_ADDED_ITEMS):
                key, error = wdl.add_item(
                    sess,
                    title=f"Item {i}",
                    wording="w",
                    classification="work",
                    status="confirmed",
                )
                self.assertIsNotNone(key)
                self.assertIsNone(error)
            key, error = wdl.add_item(
                sess, title="Fifth", wording="w", classification="work", status="confirmed"
            )
        self.assertIsNone(key)
        self.assertEqual(error, wdl.CAP_ITEMS_MESSAGE)

    def test_add_item_wording_cap(self):
        with self.client.session_transaction() as sess:
            key, error = wdl.add_item(
                sess,
                title="Too long",
                wording="x" * (wdl.MAX_PREVIEW_WORDING_UNITS + 1),
                classification="work",
                status="confirmed",
            )
            self.assertIsNone(key)
            self.assertEqual(error, wdl.CAP_WORDING_MESSAGE)

            # Exactly at the cap succeeds.
            key, error = wdl.add_item(
                sess,
                title="Just right",
                wording="x" * wdl.MAX_PREVIEW_WORDING_UNITS,
                classification="work",
                status="confirmed",
            )
        self.assertIsNotNone(key)
        self.assertIsNone(error)

    def test_edit_item_changes_title_wording_and_classification(self):
        base_key = wdl.BASE_ITEMS[1]["item_key"]
        with self.client.session_transaction() as sess:
            ok, error = wdl.edit_item(
                sess,
                base_key,
                title="Edited title",
                wording="Edited wording.",
                classification="personal",
                status="confirmed",
            )
            self.assertTrue(ok)
            self.assertIsNone(error)
            delta = wdl.read_session_delta(sess)
        row = wdl.get_row(base_key, delta)
        self.assertEqual(row["title"], "Edited title")
        self.assertEqual(row["approved_wording"], "Edited wording.")
        self.assertEqual(row["classification"], "personal")

    def test_edit_item_wording_cap(self):
        base_key = wdl.BASE_ITEMS[1]["item_key"]
        with self.client.session_transaction() as sess:
            ok, error = wdl.edit_item(
                sess,
                base_key,
                title="T",
                wording="x" * (wdl.MAX_PREVIEW_WORDING_UNITS + 1),
                classification="work",
                status="confirmed",
            )
        self.assertFalse(ok)
        self.assertEqual(error, wdl.CAP_WORDING_MESSAGE)

    def test_edit_item_unknown_key_returns_false_with_no_error_message(self):
        with self.client.session_transaction() as sess:
            ok, error = wdl.edit_item(
                sess,
                "00000000-0000-0000-0000-000000000000",
                title="T",
                wording="w",
                classification="work",
                status="confirmed",
            )
        self.assertFalse(ok)
        self.assertIsNone(error)

    def test_archive_then_restore_base_confirmed_item(self):
        base_key = wdl.BASE_ITEMS[1]["item_key"]  # a confirmed item
        with self.client.session_transaction() as sess:
            ok, _ = wdl.archive_item(sess, base_key)
            self.assertTrue(ok)
            delta = wdl.read_session_delta(sess)
        self.assertEqual(wdl.get_row(base_key, delta)["status"], "archived")

        with self.client.session_transaction() as sess:
            ok, _ = wdl.restore_item(sess, base_key)
            self.assertTrue(ok)
            delta = wdl.read_session_delta(sess)
        self.assertEqual(wdl.get_row(base_key, delta)["status"], "confirmed")

    def test_restore_natively_archived_item_returns_to_confirmed(self):
        archived_key = next(
            item["item_key"] for item in wdl.BASE_ITEMS if item["status"] == "archived"
        )
        with self.client.session_transaction() as sess:
            ok, _ = wdl.restore_item(sess, archived_key)
            self.assertTrue(ok)
            delta = wdl.read_session_delta(sess)
        self.assertEqual(wdl.get_row(archived_key, delta)["status"], "confirmed")

    def test_delete_base_item_hides_it(self):
        base_key = wdl.BASE_ITEMS[2]["item_key"]
        with self.client.session_transaction() as sess:
            ok, _ = wdl.delete_item(sess, base_key)
            self.assertTrue(ok)
            delta = wdl.read_session_delta(sess)
        self.assertIsNone(wdl.get_row(base_key, delta))
        self.assertEqual(len(wdl.list_rows(delta)), 16)

    def test_delete_added_item_frees_add_cap_slot(self):
        with self.client.session_transaction() as sess:
            keys = []
            for i in range(wdl.MAX_ADDED_ITEMS):
                key, _ = wdl.add_item(
                    sess, title=f"Item {i}", wording="w", classification="work", status="confirmed"
                )
                keys.append(key)

            fifth_key, error = wdl.add_item(
                sess, title="Fifth", wording="w", classification="work", status="confirmed"
            )
            self.assertIsNone(fifth_key)

            ok, _ = wdl.delete_item(sess, keys[0])
            self.assertTrue(ok)

            new_key, error = wdl.add_item(
                sess, title="New one", wording="w", classification="work", status="confirmed"
            )
        self.assertIsNotNone(new_key)
        self.assertIsNone(error)

    def test_two_sessions_do_not_share_additions(self):
        client_a = app.test_client()
        client_b = app.test_client()

        with client_a.session_transaction() as sess_a:
            key_a, _ = wdl.add_item(
                sess_a, title="A's item", wording="w", classification="work", status="confirmed"
            )

        with client_b.session_transaction() as sess_b:
            delta_b = wdl.read_session_delta(sess_b)

        rows_b = wdl.list_rows(delta_b)
        self.assertNotIn(key_a, [row["item_key"] for row in rows_b])
        self.assertEqual(len(rows_b), 17)


class WorkshopDemoLibrarySessionSizeTests(unittest.TestCase):
    """Chunk B requirement: total session payload stays well under 3KB even
    with both hard caps fully exercised (4 added items, 400-char wording
    each), measured against near-worst-case (low-compressibility) text."""

    def test_session_payload_under_3kb_with_caps_full(self):
        client = app.test_client()
        alphabet = string.ascii_letters + string.digits + " "
        rng = random.Random(20260802)

        with client.session_transaction() as sess:
            for i in range(wdl.MAX_ADDED_ITEMS):
                title = (f"Sample demo title number {i} " * 6)[:160]
                wording = "".join(
                    rng.choices(alphabet, k=wdl.MAX_PREVIEW_WORDING_UNITS)
                )
                key, error = wdl.add_item(
                    sess,
                    title=title,
                    wording=wording,
                    classification="work",
                    status="confirmed",
                )
                self.assertIsNotNone(key, error)

            serializer = app.session_interface.get_signing_serializer(app)
            token = serializer.dumps(dict(sess))

        size = len(token.encode("utf-8")) if isinstance(token, str) else len(token)
        self.assertLess(size, 3072, f"session payload was {size} bytes (want < 3072)")


if __name__ == "__main__":
    unittest.main()
