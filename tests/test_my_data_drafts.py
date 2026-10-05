"""Contract tests for server-persisted My Data composer drafts.

Drafts are unsubmitted private input: they recover across signed-in devices
through the owner-scoped intake snapshot, expire 30 days after the last edit,
never enter matching or canonical writes, and conflicting device saves keep
the member's unsaved version with a truthful recovery choice. The in-memory
store is labelled test-only; nothing here is SQL engine proof.
"""

from __future__ import annotations

import threading
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import (
    InMemoryResumeIntakeRepository,
    ResumeIntakeStoreUnavailable,
    SqlResumeIntakeRepository,
)
from services.resume_intake_service import (
    ResumeIntakeConflictError,
    ResumeIntakeService,
    ResumeIntakeUnavailableError,
    sweep_drafts,
)


def build_service(*, repository=None):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    return ResumeIntakeService(
        repository=repository or InMemoryResumeIntakeRepository(),
        draft_service=draft_service,
        policy=selected_policy_for_tests(),
    )


def draft_body(**kwargs):
    body = {"request_id": str(uuid4())}
    body.update(kwargs)
    return body



class UnavailableDatabase:
    def first_result(self, *args, **kwargs):
        from services.database_service import DatabaseServiceError
        raise DatabaseServiceError("isolated unavailable fixture")

class InterleavingResumeIntakeRepository(InMemoryResumeIntakeRepository):
    """Run one deterministic draft write after a command loaded its snapshot."""

    def __init__(self):
        super().__init__()
        self.before_next_save = None
        self.fail_next_save = False

    def save_owner(self, owner_user_key, snapshot, command=None):
        callback = self.before_next_save
        self.before_next_save = None
        if callback is not None:
            callback()
        if self.fail_next_save:
            self.fail_next_save = False
            raise ResumeIntakeStoreUnavailable("Injected failed command commit.")
        return super().save_owner(owner_user_key, snapshot, command)


class DraftLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service()
        self.owner = "member-a"

    def test_empty_owner_has_no_draft(self):
        result = self.service.get_draft(self.owner)
        self.assertTrue(result["success"])
        self.assertIsNone(result["draft"])
        self.assertTrue(result["drafts_supported"])

    def test_save_then_recover_across_loads(self):
        saved = self.service.save_draft(
            self.owner, draft_body(text="Systems Engineer, Huntsville")
        )
        self.assertTrue(saved["success"])
        self.assertEqual(saved["draft"]["version"], 1)
        self.assertFalse(saved["replayed"])
        # A second load recovers the same draft: cross-device recovery.
        recovered = self.service.get_draft(self.owner)
        self.assertEqual(recovered["draft"]["text"], "Systems Engineer, Huntsville")
        self.assertEqual(recovered["draft"]["version"], 1)
        self.assertEqual(recovered["expires_after_days"], 30)

    def test_second_save_bumps_version_and_resets_expiry(self):
        first = self.service.save_draft(self.owner, draft_body(text="First"))
        second = self.service.save_draft(
            self.owner,
            draft_body(text="Second", expected_version=first["draft"]["version"]),
        )
        self.assertEqual(second["draft"]["version"], 2)
        first_expiry = datetime.fromisoformat(first["draft"]["expires_at"])
        second_expiry = datetime.fromisoformat(second["draft"]["expires_at"])
        self.assertGreaterEqual(second_expiry, first_expiry)
        self.assertEqual(
            (second_expiry - datetime.fromisoformat(second["draft"]["updated_at"])).days,
            30,
        )

    def test_same_request_id_replays_without_new_version(self):
        request_id = str(uuid4())
        first = self.service.save_draft(self.owner, draft_body(
            request_id=request_id, text="Once"))
        replay = self.service.save_draft(self.owner, draft_body(
            request_id=request_id, text="Changed mind"))
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["draft"]["version"], first["draft"]["version"])
        self.assertEqual(replay["draft"]["text"], "Once")

    def test_conflicting_device_save_preserves_unsaved_input(self):
        self.service.save_draft(self.owner, draft_body(text="Device one"))
        # Device two never loaded the draft, so it carries no version.
        with self.assertRaises(ResumeIntakeConflictError) as raised:
            self.service.save_draft(self.owner, draft_body(text="Device two"))
        error = raised.exception
        self.assertEqual(error.error_code, "draft_conflict")
        # The member's unsaved version travels with the conflict.
        self.assertEqual(error.proposed["text"], "Device two")
        self.assertEqual(error.conflicts[0]["server_version"], 1)
        # The server copy is untouched until the member chooses.
        current = self.service.get_draft(self.owner)
        self.assertEqual(current["draft"]["text"], "Device one")
        self.assertEqual(current["draft"]["version"], 1)

    def test_stale_expected_version_after_two_saves_conflicts(self):
        first = self.service.save_draft(self.owner, draft_body(text="v1"))
        self.service.save_draft(
            self.owner,
            draft_body(text="v2", expected_version=first["draft"]["version"]),
        )
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.save_draft(
                self.owner, draft_body(text="v3", expected_version=1)
            )

    def test_discard_is_idempotent(self):
        self.service.save_draft(self.owner, draft_body(text="Temporary"))
        first = self.service.discard_draft(self.owner, {})
        self.assertTrue(first["discarded"])
        self.assertTrue(first["had_draft"])
        second = self.service.discard_draft(self.owner, {})
        self.assertTrue(second["discarded"])
        self.assertFalse(second["had_draft"])
        self.assertIsNone(self.service.get_draft(self.owner)["draft"])

    def test_draft_items_and_attachments_validate(self):
        with self.assertRaises(Exception):
            self.service.save_draft(
                self.owner, draft_body(items=[{"record_type": "hobby"}])
            )
        saved = self.service.save_draft(
            self.owner,
            draft_body(
                text="Notes",
                items=[{
                    "client_key": "r1",
                    "record_type": "skill",
                    "values": {"name": "Mentoring"},
                }],
                attachments=[{
                    "client_key": "doc-1",
                    "kind": "document",
                    "filename": "resume.pdf",
                    "declared_content_type": "application/pdf",
                }],
            ),
        )
        row = saved["draft"]
        self.assertEqual(row["items"][0]["record_type"], "skill")
        # Bytes arrive at Add, so a document descriptor waits for reattach.
        self.assertTrue(row["attachments"][0]["needs_reattach"])

    def test_drafts_never_match_or_save_canonically(self):
        self.service.save_draft(
            self.owner, draft_body(text="Systems Engineer at Northrop Grumman")
        )
        workspace = self.service.draft_service.get_workspace(self.owner)
        self.assertEqual(workspace.get("items"), [])

    def test_owner_isolation(self):
        self.service.save_draft("member-a", draft_body(text="Private A"))
        other = self.service.get_draft("member-b")
        self.assertIsNone(other["draft"])


class DraftAtomicityTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service()
        self.owner = "member-a"

    def test_concurrent_saves_of_the_same_version_conflict(self):
        first = self.service.save_draft(self.owner, draft_body(text="Version one"))
        self.assertEqual(first["draft"]["version"], 1)
        barrier = threading.Barrier(2)
        winners = []
        conflicts = []

        def attempt(text):
            barrier.wait()
            try:
                winners.append(self.service.save_draft(
                    self.owner,
                    draft_body(text=text, expected_version=1),
                ))
            except ResumeIntakeConflictError as error:
                conflicts.append(error)

        threads = [
            threading.Thread(target=attempt, args=("Winner words for version two",)),
            threading.Thread(target=attempt, args=("Loser words that must conflict",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].error_code, "draft_conflict")
        stored = self.service.get_draft(self.owner)["draft"]
        self.assertEqual(stored["version"], 2)
        self.assertEqual(stored["text"], winners[0]["draft"]["text"])
        self.assertIn(stored["text"], {
            "Winner words for version two",
            "Loser words that must conflict",
        })

    def test_draft_get_cannot_undo_an_interleaved_source_purge(self):
        self.service.save_draft(self.owner, draft_body(text="Kept draft words"))
        added = self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Source words"},
        )
        self.assertTrue(added["success"])
        snapshot = self.service.repository.load_owner(self.owner)
        source_key = next(iter(snapshot["sources"]))
        barrier = threading.Barrier(2)

        def do_get():
            barrier.wait()
            self.service.get_draft(self.owner)

        def do_purge():
            barrier.wait()
            self.service.purge_source(
                self.owner,
                {"request_id": str(uuid4()), "source_key": source_key},
            )

        threads = [threading.Thread(target=do_get), threading.Thread(target=do_purge)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        snapshot = self.service.repository.load_owner(self.owner)
        source = snapshot["sources"][source_key]
        self.assertEqual(source["state"], "purged")
        self.assertIsNone(source.get("text"))
        draft = self.service.get_draft(self.owner)["draft"]
        self.assertEqual(draft["text"], "Kept draft words")

    def _assert_newer_draft_survives_command(self, arrange_and_run):
        repository = InterleavingResumeIntakeRepository()
        service = build_service(repository=repository)
        first = service.save_draft(self.owner, draft_body(text="Draft version one"))
        self.assertEqual(first["draft"]["version"], 1)
        repository.before_next_save = lambda: service.save_draft(
            self.owner,
            draft_body(text="Acknowledged draft version two", expected_version=1),
        )
        arrange_and_run(service)
        current = service.get_draft(self.owner)["draft"]
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["text"], "Acknowledged draft version two")

    def test_submission_commit_preserves_interleaved_newer_draft(self):
        self._assert_newer_draft_survives_command(
            lambda service: service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "text": "Submission source words",
                },
            )
        )

    def test_failed_command_rollback_preserves_interleaved_newer_draft(self):
        repository = InterleavingResumeIntakeRepository()
        service = build_service(repository=repository)
        service.save_draft(self.owner, draft_body(text="Draft version one"))
        repository.before_next_save = lambda: service.save_draft(
            self.owner,
            draft_body(text="Acknowledged draft version two", expected_version=1),
        )
        repository.fail_next_save = True
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "text": "Command that cannot commit",
                },
            )
        current = service.get_draft(self.owner)["draft"]
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["text"], "Acknowledged draft version two")

    def test_source_purge_commit_preserves_interleaved_newer_draft(self):
        repository = InterleavingResumeIntakeRepository()
        service = build_service(repository=repository)
        added = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "Source words to purge",
            },
        )
        source_key = added["submission"]["source_keys"][0]
        service.save_draft(self.owner, draft_body(text="Draft version one"))
        repository.before_next_save = lambda: service.save_draft(
            self.owner,
            draft_body(text="Acknowledged draft version two", expected_version=1),
        )
        service.purge_source(
            self.owner,
            {"request_id": str(uuid4()), "source_key": source_key},
        )
        current = service.get_draft(self.owner)["draft"]
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["text"], "Acknowledged draft version two")

    def test_proposal_decision_commit_preserves_interleaved_newer_draft(self):
        repository = InterleavingResumeIntakeRepository()
        service = build_service(repository=repository)
        added = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "Proposal source words",
            },
        )
        proposal_key = added["proposals"][0]["proposal_key"]
        service.save_draft(self.owner, draft_body(text="Draft version one"))
        repository.before_next_save = lambda: service.save_draft(
            self.owner,
            draft_body(text="Acknowledged draft version two", expected_version=1),
        )
        service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "reject",
            },
        )
        current = service.get_draft(self.owner)["draft"]
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["text"], "Acknowledged draft version two")

    def test_expired_draft_delete_leaves_other_owner_state(self):
        self.service.save_draft(self.owner, draft_body(text="Fresh composer words"))
        self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Keep this source"},
        )
        snapshot = self.service.repository.load_owner(self.owner)
        source_keys = set(snapshot["sources"])
        now = datetime.now(timezone.utc)
        snapshot["drafts"]["stale"] = {
            "draft_key": "stale",
            "version": 1,
            "text": "Expired extra draft",
            "updated_at": (now - timedelta(days=40)).isoformat(),
            "expires_at": (now - timedelta(days=10)).isoformat(),
        }
        self.service.repository.save_owner(self.owner, snapshot)
        recovered = self.service.get_draft(self.owner)
        self.assertEqual(recovered["draft"]["text"], "Fresh composer words")
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertNotIn("stale", snapshot["drafts"])
        self.assertIn("composer", snapshot["drafts"])
        self.assertEqual(set(snapshot["sources"]), source_keys)
        source = next(iter(snapshot["sources"].values()))
        self.assertEqual(source.get("text"), "Keep this source")

    def test_concurrent_save_or_discard_cannot_overwrite_sources(self):
        added = self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Unrelated source"},
        )
        self.assertTrue(added["success"])
        self.service.save_draft(self.owner, draft_body(text="First draft"))
        source_keys = set(self.service.repository.load_owner(self.owner)["sources"])
        barrier = threading.Barrier(2)

        def do_save():
            barrier.wait()
            try:
                self.service.save_draft(
                    self.owner,
                    draft_body(text="Updated draft", expected_version=1),
                )
            except ResumeIntakeConflictError:
                pass

        def do_discard():
            barrier.wait()
            self.service.discard_draft(self.owner, {"request_id": str(uuid4())})

        threads = [threading.Thread(target=do_save), threading.Thread(target=do_discard)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertEqual(set(snapshot["sources"]), source_keys)
        source = next(iter(snapshot["sources"].values()))
        self.assertEqual(source.get("text"), "Unrelated source")
        self.assertNotEqual(source.get("state"), "purged")


class DraftExpiryTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service()
        self.owner = "member-a"

    def test_expired_draft_reads_as_missing(self):
        saved = self.service.save_draft(self.owner, draft_body(text="Old words"))
        snapshot = self.service.repository.load_owner(self.owner)
        row = snapshot["drafts"]["composer"]
        backdated = datetime.now(timezone.utc) - timedelta(days=31)
        row["updated_at"] = backdated.isoformat()
        row["expires_at"] = (backdated + timedelta(days=30)).isoformat()
        self.service.repository.save_owner(self.owner, snapshot)
        self.assertIsNone(self.service.get_draft(self.owner)["draft"])

    def test_sweep_drops_only_expired_drafts(self):
        now = datetime.now(timezone.utc)
        snapshot = {
            "drafts": {
                "old": {
                    "draft_key": "old",
                    "updated_at": (now - timedelta(days=40)).isoformat(),
                    "expires_at": (now - timedelta(days=10)).isoformat(),
                },
                "fresh": {
                    "draft_key": "fresh",
                    "updated_at": now.isoformat(),
                    "expires_at": (now + timedelta(days=30)).isoformat(),
                },
            }
        }
        self.assertEqual(sweep_drafts(snapshot, now=now), 1)
        self.assertEqual(set(snapshot["drafts"]), {"fresh"})
        self.assertEqual(sweep_drafts(snapshot, now=now), 0)

    def test_save_after_expiry_starts_a_new_draft(self):
        saved = self.service.save_draft(self.owner, draft_body(text="Old words"))
        snapshot = self.service.repository.load_owner(self.owner)
        row = snapshot["drafts"]["composer"]
        backdated = datetime.now(timezone.utc) - timedelta(days=31)
        row["updated_at"] = backdated.isoformat()
        row["expires_at"] = (backdated + timedelta(days=30)).isoformat()
        self.service.repository.save_owner(self.owner, snapshot)
        fresh = self.service.save_draft(self.owner, draft_body(text="New words"))
        self.assertGreater(fresh["draft"]["version"], saved["draft"]["version"])
        self.assertEqual(fresh["draft"]["text"], "New words")
        self.assertGreater(datetime.fromisoformat(fresh['draft']['expires_at']),datetime.fromisoformat(row['expires_at']))
        self.assertEqual((datetime.fromisoformat(fresh['draft']['expires_at']) - datetime.fromisoformat(fresh['draft']['updated_at'])).days,30)
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.save_draft(self.owner, draft_body(text='Stale device words', expected_version=saved['draft']['version']))
        self.assertEqual(self.service.get_draft(self.owner)['draft']['text'], 'New words')

    def test_legacy_row_high_water_survives_expiry_read_and_discard_without_marker(self):
        for action in ('direct_expiry', 'read_expiry', 'discard'):
            with self.subTest(action=action):
                owner = 'legacy-' + action
                first = self.service.save_draft(owner, draft_body(text='Old device copy'))['draft']
                snapshot = self.service.repository.load_owner(owner)
                snapshot.pop('draft_revision', None)
                snapshot['drafts']['composer']['version'] = 37
                if 'expiry' in action:
                    snapshot['drafts']['composer']['expires_at'] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
                self.service.repository.save_owner(owner, snapshot)
                if action == 'read_expiry':
                    self.assertIsNone(self.service.get_draft(owner)['draft'])
                elif action == 'discard':
                    self.service.discard_draft(owner, {'request_id':str(uuid4()), 'expected_version':37})
                if action != 'direct_expiry':
                    with self.assertRaises(ResumeIntakeConflictError) as missing:
                        self.service.save_draft(owner, draft_body(text='Old device overwrite', expected_version=37))
                    self.assertEqual(missing.exception.conflicts[0]['reason'], 'draft_missing')
                    self.assertEqual(missing.exception.proposed['text'], 'Old device overwrite')
                new = self.service.save_draft(owner, draft_body(text='Deliberately recreated copy'))['draft']
                self.assertGreater(new['version'], 37)
                with self.assertRaises(ResumeIntakeConflictError):
                    self.service.save_draft(owner, draft_body(text='Old device overwrite', expected_version=37))
                self.assertEqual(self.service.get_draft(owner)['draft']['text'], 'Deliberately recreated copy')

    def test_legacy_normalization_noop_reads_and_replay_keep_version_words_and_expiry(self):
        body = draft_body(text='Current words')
        first = self.service.save_draft(self.owner, body)['draft']
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot.pop('draft_revision', None)
        self.service.repository.save_owner(self.owner, snapshot)
        self.assertEqual(self.service.get_draft(self.owner)['draft'], first)
        replay = self.service.save_draft(self.owner, body)
        self.assertTrue(replay['replayed']); self.assertEqual(replay['draft'], first)
        self.assertEqual(self.service.repository.load_owner(self.owner)['draft_revision'], first['version'])

    def test_two_devices_recreate_same_missing_version_only_one_wins(self):
        old = self.service.save_draft(self.owner, draft_body(text='Original'))['draft']
        self.service.discard_draft(self.owner, {'request_id':str(uuid4()), 'expected_version':old['version']})
        barrier = threading.Barrier(2); outcomes = []
        def save(words):
            barrier.wait()
            try:
                result = self.service.save_draft(self.owner, draft_body(text=words))
                outcomes.append(('saved', result['draft']['text']))
            except ResumeIntakeConflictError as error:
                outcomes.append(('conflict', error.proposed['text']))
        threads = [threading.Thread(target=save, args=(words,)) for words in ('Device A', 'Device B')]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sorted(result[0] for result in outcomes), ['conflict', 'saved'])
        self.assertEqual(self.service.get_draft(self.owner)['draft']['text'], next(words for state, words in outcomes if state == 'saved'))


class DraftStoreSupportTests(unittest.TestCase):
    def test_sql_store_reports_drafts_truthfully_unavailable(self):
        service = build_service(repository=SqlResumeIntakeRepository(database=UnavailableDatabase()))
        with self.assertRaises(ResumeIntakeUnavailableError) as raised:
            service.get_draft("member-a")
        self.assertIn("composer is unavailable", str(raised.exception))
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.save_draft("member-a", draft_body(text="Words"))
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.discard_draft("member-a", {})

    def test_sql_store_fails_closed_when_atomic_source_schema_is_unavailable(self):
        service = build_service(repository=SqlResumeIntakeRepository(database=UnavailableDatabase()))
        with self.assertRaises(ResumeIntakeUnavailableError) as raised:
            service.submit(
                "member-a",
                {
                    "type": "keep_extracted_separate",
                    "request_id": str(uuid4()),
                    "override_key": str(uuid4()),
                },
            )
        self.assertIn("composer is unavailable", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
