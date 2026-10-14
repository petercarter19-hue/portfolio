"""D6a: the publisher refuses a B3 confirmed cross-type conversion, fail closed.

In-memory publication boundary plus the member-visitor preview fixture. The B3
overlay itself is not built here (B3 owns it): each test presents the contract
descriptor on the existing owner draft-workspace item, exactly as the shared
``get_workspace`` read will carry it. Not SQL engine proof.
"""

from __future__ import annotations

import copy
import json
import unittest
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from services.resume_publication_contracts import ReadState
from services.resume_publication_repository import PublicationConflictError
from services import resume_publication_service as publication_module
from tests.mvp1_acceptance_support import SharedMvp1Fixture

# The contract's named reasons, spelled out so the test pins the exact bytes.
TYPE_TRANSITION_UNAVAILABLE = "publication_type_transition_unavailable"
CONVERSION_DESCRIPTOR_INVALID = "publication_conversion_descriptor_invalid"


def conversion_publication_blocker(item):
    return publication_module.conversion_publication_blocker(item)

# Destination values carry a marker that must never reach an old-type merge,
# normalizer or codec. Fictional content only.
MARKER = "D6A-DESTINATION-MARKER"
DESTINATION_VALUES = {"project_name": MARKER + " project", "summary": MARKER + " summary."}
STALE_LABELS = {"stale_draft", "orphaned"}


def descriptor(item, **changes):
    value = {
        "state": "confirmed_private",
        "base_record_type": "knowledge",
        "destination_record_type": "project",
        "destination_parent_ref": None,
        "base_content_token": item["content_token"],
        "base_access_revision": item["access_revision"],
        "conversion_op_ref": "op:" + str(uuid4()),
    }
    value.update(changes)
    return value


class _Fixture:
    """One owner with a saved private draft on a canonical knowledge entry."""

    def __init__(self, owner="d6a-fictional-owner"):
        self.shared = shared = SharedMvp1Fixture()
        self.owner = owner
        self.key = shared.canonical.create_private(owner, {"command_id": str(uuid4()), "record_type": "knowledge",
            "values": {"title": "Independent project", "wording": "Fictional original wording.",
                       "classification": "work"}})["record_key"]
        shared.publication.bind_slug(owner, "d6a-fictional")
        item = self.item()
        shared.draft.commit(owner, {"type": "save_item", "request_id": str(uuid4()), "record_key": self.key,
            "record_type": "knowledge", "expected_draft_version": 0,
            "expected_content_token": item["content_token"], "expected_access_revision": item["access_revision"],
            "values": {"wording": "Fictional saved private wording."}})
        self.original_workspace = shared.draft.get_workspace
        self.conversions = {}

    def item(self, key=None):
        workspace = self.shared.draft.get_workspace(self.owner)
        return next(row for row in workspace["items"] if row["record_key"] == (key or self.key))

    def selections(self, display=True):
        return {"entries": [{"entry_key": self.key, "resume_display": display, "visitor_ai": False}]}

    @contextmanager
    def converted(self, conversion=None, *, key=None, values=DESTINATION_VALUES, **flags):
        """Present B3's descriptor (and its destination overlay values) on one item."""
        key = key or self.key
        conversion = descriptor(self.item(key)) if conversion is None else conversion
        original = self.original_workspace

        def workspace(owner):
            result = original(owner)
            for row in result["items"]:
                if row["record_key"] == key:
                    row["conversion"] = copy.deepcopy(conversion)
                    if values is not None:
                        row["proposed_values"] = copy.deepcopy(values)
                    row.update(flags)
            return result

        with patch.object(self.shared.draft, "get_workspace", side_effect=workspace):
            yield conversion

    def stores(self):
        shared = self.shared
        return copy.deepcopy((shared.policy.repository.load_owner(self.owner),
            shared.draft.repository.load_owner(self.owner),
            shared.publication.repository.load_owner(self.owner),
            shared.publication._pending_reviews))

    def publish_payload(self, selections=None):
        reviewed = self.shared.publication.review_for_owner(self.owner, selections or self.selections()).reviewed
        assert reviewed is not None
        return {"type": "publish", "request_id": str(uuid4()), "slug": "d6a-fictional", "profile_identity": None,
                "reviewed_digest": reviewed.digest, "candidate": self.shared.publication.publish_candidate(reviewed)}


@contextmanager
def old_type_spies(test):
    """Record every old-type merge/normalize/codec seam; fail on the marker."""
    from services import living_resume_editor_service, resume_publication_adapters, resume_publication_projection
    calls = []

    def spy(module, name):
        real = getattr(module, name)
        def observed(*args, **kwargs):
            calls.append(name)
            encoded = repr((args, kwargs))
            test.assertNotIn(MARKER, encoded, f"destination value reached {name}")
            return real(*args, **kwargs)
        return patch.object(module, name, side_effect=observed)

    with ExitStack() as stack:
        for module, name in ((publication_module, "build_owner_review_candidate"),
                             (publication_module, "validate_candidate"),
                             (publication_module, "_codec_values"),
                             (resume_publication_adapters, "policy_snapshot_from_entries"),
                             (resume_publication_projection, "committed_source_bytes"),
                             (living_resume_editor_service, "validate_guide_text_limits"),
                             (living_resume_editor_service, "normalize_editor_values")):
            stack.enter_context(spy(module, name))
        yield calls


class ConfirmedConversionPublicationGuardTests(unittest.TestCase):
    def test_confirmed_cross_type_overlay_blocks_review_basis_publish_and_preview_by_name(self):
        fixture = _Fixture()
        shared, owner, key = fixture.shared, fixture.owner, fixture.key
        payload = fixture.publish_payload()  # A valid candidate reviewed before the move.
        before = fixture.stores()
        with fixture.converted():
            for display in (True, False):
                with self.subTest(display=display):
                    result = shared.publication.review_for_owner(owner, fixture.selections(display))
                    self.assertIsNone(result.reviewed)
                    self.assertIs(result.state, ReadState.UNAVAILABLE)
                    self.assertEqual(result.reason, TYPE_TRANSITION_UNAVAILABLE)
                    self.assertEqual(result.blocked_items, ((key, TYPE_TRANSITION_UNAVAILABLE),))
                    basis = shared.publication.read_publication_basis_for_owner(owner, fixture.selections(display))
                    self.assertEqual(basis["read_state"], "blocked")
                    self.assertEqual(basis["publication_state"], "unknown")
                    self.assertIsNone(basis["change_count"])
                    self.assertIsNone(basis["candidate"])
                    self.assertEqual(basis["blocked_items"], [{"item_ref": key, "reason": TYPE_TRANSITION_UNAVAILABLE}])
                    self.assertIn({"item_ref": key, "reason": TYPE_TRANSITION_UNAVAILABLE}, basis["ineligible_items"])
            with self.assertRaises(PublicationConflictError) as caught:
                shared.publication.commit(owner, copy.deepcopy(payload))
            self.assertEqual(caught.exception.code, TYPE_TRANSITION_UNAVAILABLE)
            for preview in (None, copy.deepcopy(payload)):
                with self.subTest(preview=bool(preview)), self.assertRaises(PublicationConflictError) as caught:
                    shared.publication.draft_preview(owner, preview)
                self.assertEqual(caught.exception.code, TYPE_TRANSITION_UNAVAILABLE)
        # Input and overlay kept: canonical, draft, publication and review memory unchanged.
        self.assertEqual(fixture.stores(), before)
        self.assertIsNone(shared.publication.owner_preview(owner)["current"])
        self.assertEqual(shared.canonical.get_item(owner, key)["values"]["wording"], "Fictional original wording.")

    def test_no_destination_value_reaches_an_old_type_merge_normalizer_or_codec(self):
        fixture = _Fixture()
        shared, owner = fixture.shared, fixture.owner
        payload = fixture.publish_payload()
        with fixture.converted(), old_type_spies(self) as calls:
            shared.publication.read_review_for_owner(owner, fixture.selections())
            shared.publication.review_for_owner(owner, fixture.selections())
            shared.publication.read_publication_basis_for_owner(owner, fixture.selections())
            shared.publication.read_publication_basis_for_owner(owner, fixture.selections(display=False))
            for action in (lambda: shared.publication.commit(owner, copy.deepcopy(payload)),
                           lambda: shared.publication.draft_preview(owner),
                           lambda: shared.publication.draft_preview(owner, copy.deepcopy(payload))):
                with self.assertRaises(PublicationConflictError):
                    action()
        self.assertNotIn("build_owner_review_candidate", calls)
        self.assertNotIn("validate_candidate", calls)
        self.assertNotIn("validate_guide_text_limits", calls)

    def test_spies_observe_the_same_seams_for_an_ordinary_draft(self):
        # Guards the spy itself: without a conversion the same reads do reach
        # the old-type candidate path and the knowledge limits check.
        fixture = _Fixture()
        with old_type_spies(self) as calls:
            basis = fixture.shared.publication.read_publication_basis_for_owner(fixture.owner, fixture.selections())
        self.assertEqual(basis["read_state"], "current")
        self.assertIn("build_owner_review_candidate", calls)
        self.assertIn("validate_guide_text_limits", calls)

    def test_a_valid_conversion_is_never_labelled_stale_or_orphaned(self):
        fixture = _Fixture()
        shared, owner, key = fixture.shared, fixture.owner, fixture.key
        for flags in ({"draft_is_stale": True}, {"orphaned": True}, {"draft_is_stale": True, "orphaned": True}):
            with self.subTest(flags=flags), fixture.converted(**flags):
                result = shared.publication.review_for_owner(owner, fixture.selections())
                self.assertEqual(result.reason, TYPE_TRANSITION_UNAVAILABLE)
                basis = shared.publication.read_publication_basis_for_owner(owner, fixture.selections())
                reasons = {row["reason"] for row in basis["blocked_items"] if row["item_ref"] == key}
                self.assertEqual(reasons, {TYPE_TRANSITION_UNAVAILABLE})
                self.assertFalse(STALE_LABELS & {row["reason"] for row in basis["ineligible_items"]
                                                  if row["item_ref"] == key})


class MalformedConversionDescriptorTests(unittest.TestCase):
    def _variants(self, item):
        valid = descriptor(item)
        def without(name):
            return {k: v for k, v in valid.items() if k != name}
        yield "not an object", "confirmed_private"
        yield "list", [valid]
        yield "empty object", {}
        for name in sorted(valid):
            yield "missing " + name, without(name)
        yield "unknown key", {**valid, "destination_values": {"summary": MARKER}}
        for state in ("pending", "proposed", "confirmed", "CONFIRMED_PRIVATE", "", None, 1, True):
            yield f"state {state!r}", {**valid, "state": state}
        for name in ("base_record_type", "destination_record_type", "base_content_token", "conversion_op_ref"):
            for bad in (None, "", " padded ", 7, ["project"], {"value": "project"}):
                yield f"{name} {bad!r}", {**valid, name: bad}
        for bad in ("", 5, True, [], {"record_key": "role"}):
            yield f"destination_parent_ref {bad!r}", {**valid, "destination_parent_ref": bad}
        for bad in (None, "3", 3.0, True, False, -1):
            yield f"base_access_revision {bad!r}", {**valid, "base_access_revision": bad}
        yield "no actual type change", {**valid, "destination_record_type": valid["base_record_type"]}

    def test_each_malformed_descriptor_fails_closed_with_its_own_reason_without_writes(self):
        fixture = _Fixture()
        shared, owner, key = fixture.shared, fixture.owner, fixture.key
        payload = fixture.publish_payload()
        before = fixture.stores()
        for label, conversion in self._variants(fixture.item()):
            with self.subTest(label), fixture.converted(conversion), old_type_spies(self) as calls:
                self.assertEqual(conversion_publication_blocker({"record_key": key, "conversion": conversion}),
                                 CONVERSION_DESCRIPTOR_INVALID)
                result = shared.publication.review_for_owner(owner, fixture.selections())
                self.assertIsNone(result.reviewed)
                self.assertEqual(result.reason, CONVERSION_DESCRIPTOR_INVALID)
                self.assertEqual(result.blocked_items, ((key, CONVERSION_DESCRIPTOR_INVALID),))
                basis = shared.publication.read_publication_basis_for_owner(owner, fixture.selections())
                self.assertEqual(basis["read_state"], "blocked")
                self.assertEqual(basis["blocked_items"], [{"item_ref": key, "reason": CONVERSION_DESCRIPTOR_INVALID}])
                with self.assertRaises(PublicationConflictError) as caught:
                    shared.publication.commit(owner, copy.deepcopy(payload))
                self.assertEqual(caught.exception.code, CONVERSION_DESCRIPTOR_INVALID)
                self.assertNotIn("build_owner_review_candidate", calls)
        self.assertEqual(fixture.stores(), before)
        self.assertIsNone(shared.publication.owner_preview(owner)["current"])

    def test_descriptor_reader_contract(self):
        item = {"record_key": "k", "content_token": "t", "access_revision": 0}
        self.assertIsNone(conversion_publication_blocker({"record_key": "k"}))
        self.assertIsNone(conversion_publication_blocker({"record_key": "k", "conversion": None}))
        self.assertIsNone(conversion_publication_blocker("not an item"))
        self.assertEqual(conversion_publication_blocker({**item, "conversion": descriptor(item)}),
                         TYPE_TRANSITION_UNAVAILABLE)
        parent = descriptor(item, base_record_type="accomplishment", destination_record_type="role",
                            destination_parent_ref=None)
        self.assertEqual(conversion_publication_blocker({**item, "conversion": parent}), TYPE_TRANSITION_UNAVAILABLE)
        child = descriptor(item, base_record_type="knowledge", destination_record_type="accomplishment",
                           destination_parent_ref="role-key")
        self.assertEqual(conversion_publication_blocker({**item, "conversion": child}), TYPE_TRANSITION_UNAVAILABLE)
        # The opaque operation reference is never parsed: any non-empty trimmed string is accepted.
        for ref in ("op:1", "not-a-uuid", "{\"json\": true}", "a" * 300):
            self.assertEqual(conversion_publication_blocker(
                {**item, "conversion": descriptor(item, conversion_op_ref=ref)}), TYPE_TRANSITION_UNAVAILABLE)


class StaleAndOrphanedReasonsTests(unittest.TestCase):
    def _stale_role(self, shared, owner, delete=False):
        key = str(uuid4())
        shared.policy.commit(owner, {"type": "create", "request_id": str(uuid4()), "entry_key": key,
            "canonical_type": "role", "values": {"role_title": "Engineer", "employer_name": "Fictional Orchard",
                                                 "summary": "Original wording."}})
        item = shared.canonical.get_item(owner, key)
        workspace = shared.draft.get_workspace(owner)
        shared.draft.commit(owner, {"type": "save_item", "request_id": str(uuid4()), "record_key": key,
            "record_type": "role", "expected_content_token": item["content_token"],
            "expected_access_revision": item["access_revision"],
            "expected_draft_version": workspace["draft_version"], "values": {"summary": "Private wording."}})
        if delete:
            shared.policy.commit(owner, {"type": "delete", "request_id": str(uuid4()), "entry_key": key,
                "expected_content_version": 1, "expected_access_revision": 1, "dependent_keys": []})
        else:
            shared.policy.commit(owner, {"type": "edit", "request_id": str(uuid4()), "entry_key": key,
                "expected_content_version": 1, "expected_access_revision": 1,
                "values": {"summary": "New canonical fact.", "role_title": "Engineer",
                           "employer_name": "Fictional Orchard"}})
        return key

    def test_stale_and_orphaned_drafts_still_report_their_own_reasons(self):
        for delete, reason in ((False, "stale_draft"), (True, "orphaned")):
            with self.subTest(reason=reason):
                fixture = _Fixture()
                shared, owner = fixture.shared, fixture.owner
                other = self._stale_role(shared, owner, delete=delete)
                # Alone: today's behaviour.
                with self.assertRaises(PublicationConflictError) as caught:
                    shared.publication.review_for_owner(owner)
                self.assertEqual(caught.exception.code, "stale_draft")
                basis = shared.publication.read_publication_basis_for_owner(owner)
                self.assertIn({"item_ref": other, "reason": reason}, basis["blocked_items"])
                # Beside a conversion: each item keeps its own reason.
                with fixture.converted():
                    with self.assertRaises(PublicationConflictError) as caught:
                        shared.publication.review_for_owner(owner)
                    self.assertEqual(caught.exception.code, "stale_draft")
                    basis = shared.publication.read_publication_basis_for_owner(owner)
                    self.assertEqual(basis["read_state"], "blocked")
                    self.assertIn({"item_ref": other, "reason": reason}, basis["blocked_items"])
                    self.assertIn({"item_ref": fixture.key, "reason": TYPE_TRANSITION_UNAVAILABLE},
                                  basis["blocked_items"])
                    self.assertFalse({row["reason"] for row in basis["blocked_items"]
                                      if row["item_ref"] == fixture.key} & STALE_LABELS)


class NonConversionPublicationTests(unittest.TestCase):
    def test_absent_or_null_descriptor_publishes_exactly_as_before(self):
        fixture = _Fixture()
        shared, owner, key = fixture.shared, fixture.owner, fixture.key
        plain_review = shared.publication.read_review_for_owner(owner, fixture.selections())
        plain_basis = shared.publication.read_publication_basis_for_owner(owner, fixture.selections())
        self.assertEqual(plain_basis["read_state"], "current")
        with _null_conversion(fixture):
            null_review = shared.publication.read_review_for_owner(owner, fixture.selections())
            null_basis = shared.publication.read_publication_basis_for_owner(owner, fixture.selections())
        self.assertEqual(null_review.reviewed.digest, plain_review.reviewed.digest)
        self.assertEqual(null_review.reason, plain_review.reason)
        self.assertEqual(json.dumps(null_basis, sort_keys=True, default=str),
                         json.dumps(plain_basis, sort_keys=True, default=str))
        shared.publication.commit(owner, {"type": "publish", "request_id": str(uuid4()), "slug": "d6a-fictional",
            "profile_identity": None, "reviewed_digest": plain_basis["reviewed_digest"],
            "candidate": plain_basis["candidate"]})
        published = shared.publication.guest_read(slug="d6a-fictional")
        self.assertEqual(published["display"][key]["wording"]["wording"], "Fictional saved private wording.")
        self.assertEqual(shared.publication.read_publication_basis_for_owner(owner)["change_count"], 0)


@contextmanager
def _null_conversion(fixture):
    original = fixture.original_workspace

    def workspace(owner):
        result = original(owner)
        for row in result["items"]:
            row["conversion"] = None
        return result

    with patch.object(fixture.shared.draft, "get_workspace", side_effect=workspace):
        yield


class ReplayAndRepeatedReadTests(unittest.TestCase):
    def test_repeated_reads_and_refused_replays_write_nothing(self):
        fixture = _Fixture()
        shared, owner = fixture.shared, fixture.owner
        payload = fixture.publish_payload()
        before = fixture.stores()
        with fixture.converted(), ExitStack() as stack:
            saves = [stack.enter_context(patch.object(store, "save_owner", wraps=store.save_owner))
                     for store in (shared.policy.repository, shared.draft.repository, shared.publication.repository)]
            bases = [shared.publication.read_publication_basis_for_owner(owner, fixture.selections()) for _ in range(3)]
            reviews = [shared.publication.read_review_for_owner(owner, fixture.selections()) for _ in range(3)]
            for _ in range(3):
                with self.assertRaises(PublicationConflictError):
                    shared.publication.commit(owner, copy.deepcopy(payload))  # Same request id each time.
            for save in saves:
                save.assert_not_called()
        self.assertTrue(all(basis == bases[0] for basis in bases))
        self.assertTrue(all((review.reason, review.blocked_items) == (reviews[0].reason, reviews[0].blocked_items)
                            for review in reviews))
        self.assertEqual(fixture.stores(), before)
        self.assertNotIn(payload["request_id"], shared.publication.repository.load_owner(owner)["receipts"])

    def test_a_publish_receipt_from_before_the_move_replays_without_writing(self):
        fixture = _Fixture()
        shared, owner = fixture.shared, fixture.owner
        payload = fixture.publish_payload()
        first = shared.publication.commit(owner, copy.deepcopy(payload))
        self.assertFalse(first["replayed"])
        published = shared.publication.guest_read(slug="d6a-fictional")
        before = fixture.stores()
        with fixture.converted():
            again = shared.publication.commit(owner, copy.deepcopy(payload))
        self.assertTrue(again["replayed"])
        self.assertEqual(again["receipt"], first["receipt"])
        self.assertEqual(fixture.stores(), before)
        self.assertEqual(shared.publication.guest_read(slug="d6a-fictional"), published)


class SqlBackedPublishTests(unittest.TestCase):
    def test_sql_backed_publish_refuses_before_the_command_procedure(self):
        fixture = _Fixture()
        shared, owner = fixture.shared, fixture.owner
        payload = fixture.publish_payload()
        port = Mock()
        port.get_receipt.return_value = None
        shared.publication.sql_repository = port
        with fixture.converted():
            with self.assertRaises(PublicationConflictError) as caught:
                shared.publication.commit(owner, copy.deepcopy(payload))
        self.assertEqual(caught.exception.code, TYPE_TRANSITION_UNAVAILABLE)
        port.commit_command.assert_not_called()


class MemberVisitorPreviewTests(unittest.TestCase):
    def _repository(self, item):
        from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
        from tests.test_member_visitor_ai_repository import Identity, SnapshotDatabase
        from tests.test_member_visitor_ai_sources import snapshot
        document = snapshot(preview=True)
        workspace = dict(draft_version=2, capabilities={"canonical_read": "ok"}, items=[item])
        db = SnapshotDatabase(document)
        repo = SqlMemberVisitorAiRepository(db, identity=Identity(),
            draft_service=SimpleNamespace(get_workspace=lambda owner: copy.deepcopy(workspace)))
        return repo, db, document

    def _item(self, **extra):
        return dict(record_key="entry-a", record_type="role", content_token="0000000000000011",
                    access_revision=4, has_draft=True, orphaned=False, draft_is_stale=False,
                    draft_base_content_token="0000000000000011", draft_base_access_revision=4,
                    proposed_values={"role_title": "Proposed title", "summary": "Private saved proposal"}, **extra)

    def test_preview_refuses_a_conversion_before_the_old_type_codec(self):
        from services.member_visitor_ai_repository import _with_private_draft
        from services.member_visitor_ai_sources import SourcesUnavailable
        base = self._item()
        valid = descriptor(base, base_record_type="role", destination_record_type="project")
        for conversion, reason in ((valid, TYPE_TRANSITION_UNAVAILABLE),
                                   ({"state": "pending"}, CONVERSION_DESCRIPTOR_INVALID)):
            with self.subTest(reason=reason):
                item = self._item(conversion=conversion)
                item["proposed_values"] = dict(DESTINATION_VALUES)
                repo, db, document = self._repository(item)
                before = copy.deepcopy(document)
                with old_type_spies(self) as calls:
                    with self.assertRaises(SourcesUnavailable):
                        repo.prepare_preview(expected_draft_revision=2, choices=(("entry-a", True),))
                    with self.assertRaises(ValueError) as caught:
                        _with_private_draft(document, dict(draft_version=2, capabilities={"canonical_read": "ok"},
                                                           items=[item]))
                self.assertEqual(str(caught.exception), reason)
                self.assertEqual(calls, [])
                self.assertEqual(db.document, before)

    def test_preview_without_a_conversion_is_unchanged(self):
        for extra in ({}, {"conversion": None}):
            with self.subTest(extra=extra):
                repo, db, document = self._repository(self._item(**extra))
                binding = repo.prepare_preview(expected_draft_revision=2, choices=(("entry-a", True),))
                bundle = repo.load_preview(binding)
                self.assertIn("Private saved proposal", bundle.sources[0].content)
                self.assertEqual(repo.recheck(bundle), ReadState.CURRENT)


class ReviewRouteTests(unittest.TestCase):
    def setUp(self):
        from app import app
        self.app = app
        self.fixture = _Fixture(owner="d6a-route-fictional")
        self.payload = self.fixture.publish_payload()
        self.config = patch.dict(app.config, {"TESTING": True, "PEERSLATE_ALLOW_DEV_IDENTITY": True,
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": False, "PEERSLATE_RESUME_PUBLICATION_ENABLED": True,
            "RESUME_PUBLICATION_SERVICE": self.fixture.shared.publication,
            "RESUME_DRAFT_SERVICE": self.fixture.shared.draft, "ENTRY_POLICY_SERVICE": self.fixture.shared.policy,
            "PEERSLATE_DEV_USER_KEY": self.fixture.owner})
        self.config.start()
        self.addCleanup(self.config.stop)

    def test_review_publish_and_preview_routes_name_the_reason_and_keep_everything(self):
        fixture, headers = self.fixture, {"X-PeerSlate-Request": "same-origin"}
        client = self.app.test_client()
        before = fixture.stores()
        with fixture.converted():
            review = client.post("/api/resume-publication/me/review", headers=headers, json=fixture.selections())
            publish = client.post("/api/resume-publication/me/commands", headers=headers, json=self.payload)
            preview = client.get("/api/resume-publication/me/preview", headers=headers)
        self.assertEqual(review.status_code, 409)
        self.assertEqual(review.get_json()["code"], TYPE_TRANSITION_UNAVAILABLE)
        self.assertEqual(review.get_json()["blocked_items"],
                         [{"item_ref": fixture.key, "reason": TYPE_TRANSITION_UNAVAILABLE}])
        for response in (publish, preview):
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.get_json()["code"], TYPE_TRANSITION_UNAVAILABLE)
        for response in (review, publish, preview):
            self.assertNotIn(MARKER, response.get_data(as_text=True))
        self.assertEqual(fixture.stores(), before)


if __name__ == "__main__":
    unittest.main()
