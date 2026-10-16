"""Working-set projection on the existing owner intake/draft foundation."""
from copy import deepcopy
from uuid import UUID, uuid4
import unittest
from unittest.mock import Mock,patch

from tests.test_resume_intake_service import build_service
from services.resume_intake_repository import ResumeIntakeStoreUnavailable
from services.resume_intake_service import ResumeIntakeNotFoundError, ResumeIntakeUnavailableError
from services.resume_guide_service import ResumeGuideService, GuideUnavailableError, GuideConflictError
from services.resume_draft_repository import CanonicalReadUnavailable


class GuideStoredTypeTests(unittest.TestCase):
    def test_real_local_qualification_kinds_get_their_own_groups_without_changing_the_core_order(self):
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        from urllib.request import Request, urlopen
        import json
        owner = "g-member-a"
        with Mvp1AcceptanceServer() as server:
            for kind in ("membership", "publication"):
                server.shared.draft.commit(owner, {"type": "create_private_item", "request_id": str(uuid4()),
                    "record_key": str(uuid4()), "record_type": "credential", "values": {"qualification_kind": kind,
                        "name": "Fictional publication" if kind == "publication" else None,
                        "issuer": "Fictional organization", "issue_date": "2022-01-01",
                        "issue_date_precision": "year", "completion_status": "completed"}})
            def read():
                with urlopen(Request(server.url + "/api/resume-intake/me/guide/working-set",
                        headers={"Cookie": "mvp1-synthetic-owner=" + owner}), timeout=10) as response:
                    self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                    return json.load(response)
            with (patch.object(server.shared.policy.repository, "save_owner", wraps=server.shared.policy.repository.save_owner) as policy_save,
                  patch.object(server.shared.draft.repository, "save_owner", wraps=server.shared.draft.repository.save_owner) as draft_save,
                  patch.object(server.intake.repository, "save_owner", wraps=server.intake.repository.save_owner) as intake_save):
                data = read()
                self.assertEqual(data["section_order"][:7], ["impact_statement", "experience", "skills", "projects", "education", "certifications", "awards"])
                self.assertEqual(set(data["section_order"][7:]), {"memberships", "publications"})
                for key in ("memberships", "publications"):
                    self.assertEqual(next(row for row in data["sections"] if row["key"] == key)["counts"]["saved"], 1)
                self.assertEqual(read()["section_order"], data["section_order"])
                policy_save.assert_not_called(); draft_save.assert_not_called(); intake_save.assert_not_called()

    def test_real_saved_personal_knowledge_needs_the_actual_story_binding_and_contact_stays_non_tab(self):
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        owner = "g-member-a"
        with Mvp1AcceptanceServer() as server:
            story = server.shared.canonical.create_private(owner, {"command_id": str(uuid4()), "record_type": "knowledge",
                "values": {"title": "My Story", "wording": "A fictional personal account.", "classification": "personal"}})
            contact = server.shared.canonical.create_private(owner, {"command_id": str(uuid4()), "record_type": "knowledge",
                "values": {"title": "Contact details", "wording": "fictional@example.test", "classification": "work"}})
            before = server.intake.working_set(owner)
            self.assertIn(story["record_key"], [row["item_ref"] for row in before["unplaced"]])
            self.assertEqual([(row["item_ref"], row["section"]) for row in before["non_tab_items"]], [(contact["record_key"], "contact")])
            workspace = server.shared.draft.get_workspace(owner)
            server.shared.draft.commit(owner, {"type": "bind_story", "request_id": str(uuid4()), "record_key": story["record_key"],
                "expected_draft_version": workspace["draft_version"], "expected_content_token": story["content_token"],
                "expected_access_revision": story["access_revision"]})
            after = server.intake.working_set(owner)
            self.assertIn((story["record_key"], "story"), [(row["item_ref"], row["section"]) for row in after["non_tab_items"]])
            self.assertNotIn("presentation_section", server.shared.canonical.get_item(owner, story["record_key"])["values"])


class GuideFirstArrivalTests(unittest.TestCase):
    def test_first_arrival_does_not_persist_expired_canonical_cleanup(self):
        from datetime import timedelta
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared = SharedMvp1Fixture()
        instant, entry = shared.policy._now(), str(uuid4())
        shared.policy.clock = lambda: instant
        shared.policy.commit("arrival-fictional-a", {"type": "create", "request_id": str(uuid4()),
            "entry_key": entry, "canonical_type": "skill", "values": {"skill_name": "Expired fictional skill"}})
        shared.policy.commit("arrival-fictional-a", {"type": "delete", "request_id": str(uuid4()),
            "entry_key": entry, "expected_content_version": 1, "expected_access_revision": 1,
            "dependent_keys": []})
        shared.policy.clock = lambda: instant + timedelta(days=31)
        self.service.draft_service = shared.draft
        before = deepcopy(shared.policy.repository.load_owner(self.owner))
        with (patch.object(shared.policy.repository, "save_owner", wraps=shared.policy.repository.save_owner) as policy_save,
              patch.object(self.repo, "save_owner", wraps=self.repo.save_owner) as guide_save,
              patch.object(shared.draft.repository, "save_owner", wraps=shared.draft.repository.save_owner) as draft_save):
            self.assertTrue(self.state()["eligible"])
            policy_save.assert_not_called()
            guide_save.assert_not_called()
            draft_save.assert_not_called()
        self.assertEqual(shared.policy.repository.load_owner(self.owner), before)

    def setUp(self):
        self.owner = "arrival-fictional-a"
        self.service, self.catalog, self.draft = build_service()
        self.repo = self.service.repository
        self.guide = ResumeGuideService(repository=self.repo)

    def state(self, owner=None):
        return self.guide.get_first_arrival(owner or self.owner, read_content=self.service.has_private_resume_content)

    def ack(self, payload, owner=None):
        return self.guide.acknowledge_first_arrival(owner or self.owner, payload,
            read_content=self.service.has_private_resume_content)

    def test_new_member_reads_are_qualified_and_write_nothing(self):
        before = self.repo.load_owner(self.owner)
        with patch.object(self.repo, "save_owner", wraps=self.repo.save_owner) as save:
            for _ in range(2):
                state = self.state()
                self.assertEqual(state, {"read_state": "available", "eligible": True,
                    "shown": False, "dismissed": False, "started": False})
            save.assert_not_called()
        self.assertEqual(before, self.repo.load_owner(self.owner))

    def test_existing_private_content_and_guide_choice_prevent_first_arrival(self):
        for kind in ("canonical", "composer", "media", "guide"):
            with self.subTest(kind=kind):
                self.setUp()
                if kind == "canonical":
                    self.catalog.put_item(self.owner, {"record_key": str(uuid4()), "record_type": "skill",
                        "values": {"name": "Private skill"}, "content_token": "1", "access_revision": 1,
                        "resume_display": False, "visitor_ai": False})
                elif kind == "composer":
                    snapshot = self.repo.load_owner(self.owner)
                    snapshot["drafts"] = {"composer": {"text": "Unsent private words", "items": [], "attachments": []}}
                    self.repo.save_owner(self.owner, snapshot)
                elif kind == "media":
                    snapshot = self.draft.repository.load_owner(self.owner)
                    snapshot["media"] = {"placements": [{"slot": "portrait", "media_key": str(uuid4())}]}
                    self.draft.repository.save_owner(self.owner, snapshot)
                else:
                    self.guide.set_status(self.owner, {"request_id": str(uuid4()), "status": "paused"})
                self.assertFalse(self.state()["eligible"])

    def test_empty_composer_navigation_is_not_invented_content(self):
        snapshot = self.repo.load_owner(self.owner)
        snapshot["drafts"] = {"composer": {"text": None, "items": [], "attachments": [],
            "guide_state": {"screen": "welcome", "manual_fields": {"empty_field": "", "unchecked_field": False}}}}
        self.repo.save_owner(self.owner, snapshot)
        self.assertTrue(self.state()["eligible"])

    def test_unreadable_catalog_is_unknown_and_cannot_claim_a_welcome(self):
        with patch.object(self.catalog, "list_items", side_effect=CanonicalReadUnavailable()):
            self.assertIsNone(self.state()["eligible"])
            self.assertEqual(self.state()["read_state"], "unavailable")
            with self.assertRaises(GuideUnavailableError):
                self.ack({"request_id": str(uuid4()), "first_arrival_action": "shown"})
            with self.assertRaises(ResumeIntakeUnavailableError):
                self.service.working_set(self.owner)
        self.assertEqual(self.repo.load_owner(self.owner)["guide"], {})

    def test_only_one_tab_claims_shown_and_exact_replay_never_reopens(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        ready = Barrier(2)
        payloads = [{"request_id": str(uuid4()), "first_arrival_action": "shown"} for _ in range(2)]
        def claim(payload):
            ready.wait(timeout=5)
            return self.ack(payload)
        with patch.object(self.repo, "save_owner", wraps=self.repo.save_owner) as save:
            with ThreadPoolExecutor(max_workers=2) as workers:
                results = list(workers.map(claim, payloads))
            self.assertEqual(sum(r["show_now"] for r in results), 1)
            self.assertEqual(save.call_count, 1)
            index = next(i for i, result in enumerate(results) if result["show_now"])
            replay = self.ack(payloads[index])
            self.assertTrue(replay["replayed"])
            self.assertFalse(replay["show_now"])
            self.assertEqual(replay["receipt"], results[index]["receipt"])
            self.assertEqual(save.call_count, 1)
        self.assertFalse(self.state()["eligible"])
        self.assertTrue(self.state()["shown"])
        self.assertEqual(self.guide.get_state(self.owner)["status"], "not_started")
        self.assertFalse(self.guide.get_state(self.owner)["member_choice"])
        self.assertTrue(self.ack(payloads[index], owner="arrival-fictional-b")["show_now"])

    def test_member_acknowledgments_are_idempotent_not_completion_or_content(self):
        for action in ("dismissed", "started"):
            payload = {"request_id": str(uuid4()), "first_arrival_action": action}
            first = self.ack(payload)
            self.assertTrue(first["first_arrival"][action])
            self.assertFalse(first["show_now"])
            self.assertEqual(first["receipt"], self.ack(payload)["receipt"])
            with self.assertRaises(GuideConflictError):
                self.ack({**payload, "first_arrival_action": "shown"})
        self.assertEqual(self.draft.get_workspace(self.owner)["items"], [])
        self.assertEqual(self.guide.get_state(self.owner)["status"], "not_started")
        self.assertFalse(self.state()["eligible"])

    def test_explicit_dismissal_and_start_do_not_require_an_available_catalog(self):
        with patch.object(self.catalog, "list_items", side_effect=CanonicalReadUnavailable()):
            for action in ("dismissed", "started"):
                result = self.ack({"request_id": str(uuid4()), "first_arrival_action": action})
                self.assertTrue(result["first_arrival"][action])
                self.assertFalse(result["show_now"])
        self.assertEqual(self.guide.get_state(self.owner)["status"], "not_started")

    def test_lost_ack_response_replays_the_stored_receipt_without_a_second_open(self):
        payload = {"request_id": str(uuid4()), "first_arrival_action": "shown"}
        save = self.repo.save_owner
        def lost_response(*args, **kwargs):
            save(*args, **kwargs)
            raise ResumeIntakeStoreUnavailable("Lost acknowledgment response")
        with patch.object(self.repo, "save_owner", side_effect=lost_response):
            with self.assertRaises(GuideUnavailableError):
                self.ack(payload)
        replay = self.ack(payload)
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["show_now"])
        self.assertTrue(replay["receipt"]["persisted"])
        self.assertTrue(self.state()["shown"])

    def test_unqualified_backend_and_corrupt_ack_never_claim_eligibility(self):
        with patch.object(self.repo, "supports_guide_first_arrival", False, create=True):
            self.assertIsNone(self.state()["eligible"])
            with self.assertRaises(GuideUnavailableError):
                self.ack({"request_id": str(uuid4()), "first_arrival_action": "shown"})
        self.repo._owners[self.owner] = self.repo.load_owner(self.owner)
        self.repo._owners[self.owner]["guide"] = {"first_arrival": {"shown": "yes"}}
        self.assertIsNone(self.state()["eligible"])

    def test_malformed_snapshot_and_receipt_are_not_invented_absence_or_acknowledgment(self):
        for malformed in (None, {}, []):
            with self.subTest(snapshot=malformed), patch.object(self.repo, "load_owner", return_value=malformed):
                self.assertIsNone(self.state()["eligible"])
        payload = {"request_id": str(uuid4()), "first_arrival_action": "shown"}
        self.ack(payload)
        self.repo._owners[self.owner]["receipts"][payload["request_id"]]["result"]["action"] = "started"
        with self.assertRaises(GuideUnavailableError):
            self.ack(payload)

    def test_unrelated_old_snapshot_cannot_erase_arrival_or_its_replay_receipt(self):
        from services.resume_intake_repository import COMMAND_PROCEDURES
        old = self.repo.load_owner(self.owner)
        payload = {"request_id": str(uuid4()), "first_arrival_action": "shown"}
        original = self.ack(payload)
        # Exercise the whole-snapshot repository boundary with a stale caller.
        self.repo.save_owner(self.owner, old,
            {"procedure": COMMAND_PROCEDURES["add_submission"], "payload": {}})
        self.assertTrue(self.state()["shown"])
        replay = self.ack(payload)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"], original["receipt"])
        self.guide.set_status(self.owner, {"request_id": str(uuid4()), "status": "paused"})
        self.assertTrue(self.state()["shown"])


class GuideWorkingSetTests(unittest.TestCase):
    def setUp(self):
        self.owner = "fictional-member-a"
        self.service,self.catalog,self.draft = build_service(interpreter=lambda text,kind:[{
            "kind":"new_fact","record_type":"skill","values":{"name":text},"quote":text,"confidence":"certain"}])

    def submit(self, text, owner=None):
        return self.service.submit(owner or self.owner,{
            "type":"add_submission","request_id":str(uuid4()),"text":text})

    def working(self, owner=None):
        method = getattr(self.service,"working_set",None)
        self.assertTrue(callable(method),"Guide needs one owner-bound projection across every upload")
        return method(owner or self.owner)

    def skills(self, result):
        return next(section["items"] for section in result["sections"] if section["key"] == "skills")

    def test_all_uploads_and_saved_items_share_one_read_only_projection(self):
        key = str(uuid4())
        self.catalog.put_item(self.owner,{"record_key":key,"record_type":"skill","values":{"name":"Writing","summary":None},
            "content_token":"1","access_revision":1,"resume_display":False,"visitor_ai":False})
        self.submit("Python"); self.submit("SQL")
        before = self.service.repository.load_owner(self.owner)
        result = self.working()
        self.assertEqual(result["schema_version"],1)
        self.assertEqual(result["load_state"],"loaded")
        self.assertEqual(result["section_order"],["impact_statement","experience","skills","projects","education","certifications","awards"])
        self.assertEqual({row["values"]["name"] for row in self.skills(result)},{"Writing","Python","SQL"})
        self.assertEqual(result["counts"]["saved"],1)
        self.assertEqual(result["counts"]["waiting"],2)
        self.assertEqual(next(row for row in self.skills(result) if row["state"]=="saved")["item_ref"],key)
        self.assertEqual(self.service.repository.load_owner(self.owner),before)
        self.assertEqual(self.working()["working_set_token"],result["working_set_token"])

    def test_pending_identity_is_persisted_once_and_kept_through_revision(self):
        receipt = self.submit("Python")
        snapshot = self.service.repository.load_owner(self.owner)
        old = snapshot["proposals"][receipt["proposals"][0]["proposal_key"]]
        self.assertIsInstance(old.get("item_ref"),str,"Pending identity must be persisted before read")
        UUID(old["item_ref"])
        revised = deepcopy(old)
        revised.update(proposal_key=str(uuid4()),proposed_values={"name":"Python","summary":"Fictional source detail"})
        revised["resume_conversation_v1"] = {"revision_of":old["proposal_key"]}
        old["state"] = "invalidated"; old["superseded_by"] = revised["proposal_key"]
        snapshot["proposals"][revised["proposal_key"]] = revised
        self.service.repository.save_owner(self.owner,snapshot)
        current = self.service.repository.load_owner(self.owner)["proposals"][revised["proposal_key"]]
        self.assertEqual(current["item_ref"],old["item_ref"])
        self.assertEqual(current["revision"],old["revision"]+1)
        items = self.skills(self.working())
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["item_ref"],old["item_ref"])
        self.assertEqual(items[0]["proposal_key"],revised["proposal_key"])

    def test_saved_transition_keeps_an_explicit_pending_identity_alias(self):
        receipt = self.submit("Python")
        proposal = receipt["proposals"][0]
        stored = self.service.repository.load_owner(self.owner)["proposals"][proposal["proposal_key"]]
        self.assertIsInstance(stored.get("item_ref"),str)
        pending_ref = stored["item_ref"]
        self.service.decide(self.owner,{"request_id":str(uuid4()),"proposal_key":proposal["proposal_key"],
            "decision":"accept","confirmed_values":{"name":"Python"}})
        item = self.skills(self.working())[0]
        self.assertEqual(item["state"],"saved")
        self.assertIn(pending_ref,item["identity_aliases"])
        self.assertEqual(item["item_ref"],self.catalog.list_items(self.owner)[0]["record_key"])

    def test_another_owner_cannot_read_or_resolve_an_item_reference(self):
        self.submit("Python")
        items = self.skills(self.working())
        other = self.working("fictional-member-b")
        self.assertEqual(self.skills(other),[])
        method = getattr(self.service,"working_item",None)
        self.assertTrue(callable(method))
        with self.assertRaises(ResumeIntakeNotFoundError):
            method("fictional-member-b",items[0]["item_ref"])

    def test_read_failure_is_unavailable_not_an_empty_member(self):
        self.working()
        with patch.object(self.service.repository,"load_owner",side_effect=ResumeIntakeStoreUnavailable("fictional outage")):
            with self.assertRaises(ResumeIntakeUnavailableError):
                self.working()

    def test_projection_values_do_not_alias_canonical_or_proposal_state(self):
        self.submit("Python")
        result = self.working()
        self.skills(result)[0]["values"]["name"] = "Must not be saved"
        self.assertEqual(self.skills(self.working())[0]["values"]["name"],"Python")

    def test_unplaced_skipped_note_keeps_source_and_status_across_reload(self):
        receipt = self.submit("Fictional unplaced note")
        snapshot = self.service.repository.load_owner(self.owner)
        proposal = snapshot["proposals"][receipt["proposals"][0]["proposal_key"]]
        proposal.update(record_type="unspecified",proposed_values={"text":"Fictional unplaced note"},state="rejected")
        proposal["resume_conversation_v1"] = {"presentation_section":"Unsorted"}
        self.service.repository.save_owner(self.owner,snapshot)
        before = self.service.repository.load_owner(self.owner)
        result = self.working()
        self.assertEqual(len(result["unplaced"]),1)
        self.assertEqual(result["unplaced"][0]["state"],"skipped")
        self.assertEqual(result["unplaced"][0]["evidence"][0]["quote"],"Fictional unplaced note")
        self.assertEqual(self.working()["unplaced"],result["unplaced"])
        self.assertEqual(self.service.repository.load_owner(self.owner),before)

    def test_saved_accomplishment_is_a_child_not_a_second_role(self):
        role_key, child_key = str(uuid4()),str(uuid4())
        common = {"content_token":"1","access_revision":1,"resume_display":False,"visitor_ai":False}
        self.catalog.put_item(self.owner,{**common,"record_key":role_key,"record_type":"role",
            "values":{"role_title":"Engineer","employer_name":"Fictional Acorn Works","summary":"Fictional duties"}})
        self.catalog.put_item(self.owner,{**common,"record_key":child_key,"record_type":"accomplishment",
            "parent_key":role_key,"values":{"wording":"Reviewed 12 fictional records"}})
        result = self.working()
        roles = next(section["items"] for section in result["sections"] if section["key"]=="experience")
        self.assertEqual(len(roles),1)
        self.assertEqual(roles[0]["item_ref"],role_key)
        self.assertEqual(roles[0]["children"][0]["item_ref"],child_key)
        self.assertEqual(roles[0]["children"][0]["parent_ref"],role_key)

    def test_unavailable_source_never_resurrects_a_quote_or_removes_saved_content(self):
        receipt = self.submit("Python")
        proposal = receipt["proposals"][0]
        self.service.decide(self.owner,{"request_id":str(uuid4()),"proposal_key":proposal["proposal_key"],
            "decision":"accept","confirmed_values":{"name":"Python"}})
        snapshot = self.service.repository.load_owner(self.owner)
        row = snapshot["proposals"][proposal["proposal_key"]]
        source = snapshot["sources"][row["binding"]["source_key"]]
        source.update(state="purged",text="",version=source["version"]+1)
        self.service.repository.save_owner(self.owner,snapshot)
        item = self.skills(self.working())[0]
        self.assertEqual(item["state"],"saved")
        self.assertEqual(item["values"]["name"],"Python")
        self.assertFalse(item["evidence"][0]["available"])
        self.assertNotIn("quote",item["evidence"][0])

    def test_partial_manual_draft_keeps_unchanged_values(self):
        key = str(uuid4())
        item = {"record_key":key,"record_type":"skill","values":{"name":"Python","summary":"Original"},
                "has_draft":True,"proposed_values":{"summary":"Manual detail"},"content_token":"1"}
        with patch.object(self.service,"_canonical_view",return_value=([item],1)):
            values = self.skills(self.working())[0]["values"]
        self.assertEqual(values,{"name":"Python","summary":"Manual detail"})

    def test_hidden_only_section_has_no_visible_tab_or_publication_claim(self):
        key = str(uuid4())
        self.catalog.put_item(self.owner,{"record_key":key,"record_type":"skill","values":{"name":"Python"},
            "content_token":"1","access_revision":1,"resume_display":False,"visitor_ai":False})
        receipt = self.submit("Python")
        snapshot = self.service.repository.load_owner(self.owner)
        row = snapshot["proposals"][receipt["proposals"][0]["proposal_key"]]
        row.update(state="accepted",target_key=key,saved_record_key=key,decision="accept",decided_at=row["created_at"])
        row["resume_conversation_v1"] = {"resume_exclusion":True}
        self.service.repository.save_owner(self.owner,snapshot)
        result = self.working()
        section = next(section for section in result["sections"] if section["key"]=="skills")
        self.assertEqual(section["items"][0]["state"],"hidden")
        self.assertFalse(section["tab_visible"])
        self.assertEqual(result["publication_state"],"unknown")

    def test_unqualified_backend_does_not_claim_guide_identity_support(self):
        self.service.repository.supports_resume_conversation = False
        with self.assertRaises(ResumeIntakeUnavailableError):
            self.working()

    def test_failed_organize_without_proposals_keeps_the_source_and_unplaced_units(self):
        from services.resume_onboarding_document_reader import inventory_source
        snapshot = self.service.repository.load_owner(self.owner)
        key = str(uuid4()); text = "Fictional unplaced note."
        units = inventory_source(text,document=True)
        snapshot["sources"][key] = {"source_key":key,"kind":"document","state":"active","version":1,"text":text,
            "structured_values":{"resume_conversation_v1":{"source_units":units,"complete":True,"organization":{"state":"failed"}}}}
        self.service.repository.save_owner(self.owner,snapshot)
        before = self.service.repository.load_owner(self.owner)
        result = self.working()
        self.assertEqual(result["active_sources"][0]["organization"]["state"],"failed")
        self.assertEqual(result["unplaced"][0]["values"]["text"],text)
        self.assertEqual(self.working()["unplaced"][0]["item_ref"],result["unplaced"][0]["item_ref"])
        self.assertEqual(self.service.repository.load_owner(self.owner),before)

    def test_matched_revision_from_another_source_keeps_identity_and_both_evidence_spans(self):
        receipt = self.submit("Python")
        snapshot = self.service.repository.load_owner(self.owner)
        old = snapshot["proposals"][receipt["proposals"][0]["proposal_key"]]
        first_source = old["binding"]["source_key"]
        second_source = str(uuid4())
        snapshot["sources"][second_source] = {**deepcopy(snapshot["sources"][first_source]),"source_key":second_source}
        revised = deepcopy(old); revised["proposal_key"] = str(uuid4())
        revised["binding"]["source_key"] = second_source
        revised["resume_conversation_v1"] = {"revision_of":old["proposal_key"]}
        old["state"] = "invalidated"; old["superseded_by"] = revised["proposal_key"]
        snapshot["proposals"][revised["proposal_key"]] = revised
        self.service.repository.save_owner(self.owner,snapshot)
        result = self.working(); item = self.skills(result)[0]
        self.assertEqual(len(self.skills(result)),1)
        self.assertEqual(item["item_ref"],old["item_ref"])
        self.assertEqual({e["source_key"] for e in item["evidence"]},{first_source,second_source})
        self.assertTrue(all(e["quote"]=="Python" for e in item["evidence"]))
        self.assertEqual(self.skills(self.working())[0]["evidence"],item["evidence"])

    def test_reader_page_count_includes_blank_pages_and_is_not_guessed_from_units(self):
        snapshot = self.service.repository.load_owner(self.owner); key = str(uuid4())
        snapshot["sources"][key] = {"source_key":key,"kind":"document","state":"active","version":1,"text":"Fictional text",
            "structured_values":{"resume_conversation_v1":{"source_units":[{"kind":"content","unit_id":"unit-a",
                "text":"Fictional text","span_start":0,"span_end":14,"page":1}],"pages":[{"page":1},{"page":2}],"complete":True}}}
        self.service.repository.save_owner(self.owner,snapshot)
        self.assertEqual(self.working()["active_sources"][0]["page_count"],2)

    def test_removing_one_contributing_source_keeps_the_other_quote_and_same_item(self):
        receipt=self.submit("Python")
        snapshot=self.service.repository.load_owner(self.owner)
        old=snapshot["proposals"][receipt["proposals"][0]["proposal_key"]]
        first=old["binding"]["source_key"];second=str(uuid4())
        snapshot["sources"][second]={**deepcopy(snapshot["sources"][first]),"source_key":second}
        revised=deepcopy(old)
        revised.update(proposal_key=str(uuid4()),binding={**old["binding"],"source_key":second})
        revised["resume_conversation_v1"]={"revision_of":old["proposal_key"]}
        old.update(state="invalidated",superseded_by=revised["proposal_key"])
        snapshot["proposals"][revised["proposal_key"]]=revised
        self.service.repository.save_owner(self.owner,snapshot)
        original_ref=self.skills(self.working())[0]["item_ref"]
        self.service.purge_source(self.owner,{"request_id":str(uuid4()),"source_key":first})
        current=self.skills(self.working())[0]
        self.assertEqual(current["item_ref"],original_ref)
        evidence={row["source_key"]:row for row in current["evidence"]}
        self.assertFalse(evidence[first]["available"]);self.assertNotIn("quote",evidence[first])
        self.assertEqual(evidence[second]["quote"],"Python")
        self.service.purge_source(self.owner,{"request_id":str(uuid4()),"source_key":second})
        self.assertEqual(self.skills(self.working()),[])


class GuidePdfStageReplayTests(unittest.TestCase):
    """A fictional V001-shaped PDF path; stage proof, not original-cause/model proof."""
    def read_pdf(self):
        from scripts.run_resume_onboarding_acceptance import _pdf
        from services.resume_onboarding_document_reader import ResumeOnboardingDocumentReader
        from services.resume_intake_policy import selected_policy_for_tests
        text = ("FICTIONAL ALEX RIVERS\nEXPERIENCE\nSystems Engineer | Fictional Acorn Works | 2019 - Present\n"
                "- Supported a 4-person team; did not manage it.\nSKILLS\nSQL")
        result = ResumeOnboardingDocumentReader().read("application/pdf",_pdf([[text]]),
            limits=selected_policy_for_tests().import_limits())
        self.assertTrue(result["complete"])
        self.assertIn("Supported a 4-person team; did not manage it.",result["text"])
        return result

    def test_real_pdf_reader_then_fake_organize_keeps_facts_and_normalizes_only_stated_dates(self):
        from tests.test_resume_onboarding_coverage import complete_resume_candidate
        from services.my_data_extraction_adapter import MyDataExtractionAdapter
        from services.resume_intake_service import EDITOR_FIELDS
        parsed = self.read_pdf(); text,units = parsed["text"],parsed["units"]
        role_units = [u for u in units if "Systems Engineer" in u["text"] or "Supported a 4-person" in u["text"]]
        skill_units = [u for u in units if u["text"]=="SQL"]
        quote = text[text.index(role_units[0]["text"]):text.index(role_units[-1]["text"])+len(role_units[-1]["text"])]
        rows = [complete_resume_candidate("role",{"role_title":"Systems Engineer","employer_name":"Fictional Acorn Works",
            "summary":"Supported a 4-person team; did not manage it.","start_date":"2019-03-14","date_precision":"day",
            "current_role":True},quote,role_units,"Experience"),
            complete_resume_candidate("skill",{"name":"SQL"},"SQL",skill_units,"Skills")]
        calls = []
        def fake(request,**options):
            calls.append((request,options))
            return {"candidates":rows}
        adapter = MyDataExtractionAdapter(fake,model="gpt-6.1-sol",reasoning_effort="medium",maximum_output_tokens=24576)
        result = adapter.organize_resume(text,allowed_fields=EDITOR_FIELDS,source_units=units,request_id=str(uuid4()))
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][1]["maximum_output_tokens"],24576)
        self.assertTrue({"role","skill"} <= {row["record_type"] for row in result.drafts})
        self.assertTrue(any(row["record_type"]=="unspecified" and "FICTIONAL ALEX RIVERS" in row.get("quote","")
                            for row in result.drafts),"Unaccounted original content must remain visible, not disappear")
        role = next(row for row in result.drafts if row["record_type"]=="role")["values"]
        self.assertEqual(role["summary"],next(unit["text"] for unit in role_units if "Supported a 4-person" in unit["text"]))
        self.assertEqual((role["start_date"],role["date_precision"]),("2019-01-01","year"))
        self.assertTrue(all(u["text"] in text for u in units))

    def test_provider_failure_is_an_organize_stage_failure_after_successful_pdf_read(self):
        from services.my_data_extraction_adapter import MyDataExtractionAdapter,ExtractionError
        from services.ai_foundation.errors import ProviderUnavailableError
        from services.resume_intake_service import EDITOR_FIELDS
        parsed = self.read_pdf(); original = deepcopy(parsed)
        provider = Mock(side_effect=ProviderUnavailableError("fictional incomplete generation"))
        adapter = MyDataExtractionAdapter(provider,model="gpt-6.1-sol",reasoning_effort="medium",maximum_output_tokens=24576)
        with self.assertRaisesRegex(ExtractionError,"provider_unavailable"):
            adapter.organize_resume(parsed["text"],allowed_fields=EDITOR_FIELDS,source_units=parsed["units"],request_id=str(uuid4()))
        provider.assert_called_once()
        self.assertEqual(parsed,original)


class GuidePublicationTruthTests(unittest.TestCase):
    def state(self, working, preview):
        from services import resume_guide_contract
        method = getattr(resume_guide_contract,"guide_publication_state",None)
        self.assertTrue(callable(method),"Guide privacy wording needs publication authority, not sharing guesses")
        return method(working,preview)

    def working(self, *, state="saved", token="1", has_draft=False):
        return {"sections":[{"items":[{"item_ref":"entry-a","origin":"saved","state":state,"saved_revision":token,
            "saved_content_version":int(token),"saved_access_revision":1,
            "has_draft":has_draft,"children":[]}]}],"unplaced":[],"counts":{"waiting":int(state=="waiting")}}

    def preview(self):
        return {"read_state":"current","sharing_enabled":True,"current":{"revision":1,
            "evidence":{"entry-a":{"canonical_token":"1","access_revision":1}}}}

    def test_unavailable_or_unwired_authority_is_never_no_publication(self):
        self.assertEqual(self.state(self.working(),None),"unknown")
        self.assertEqual(self.state(self.working(),{"read_state":"unavailable"}),"unknown")

    def test_authoritative_absence_or_take_down_is_unpublished(self):
        self.assertEqual(self.state(self.working(),{"read_state":"current","sharing_enabled":False,"current":None}),"unpublished")
        preview = self.preview(); preview["sharing_enabled"] = False
        self.assertEqual(self.state(self.working(),preview),"unpublished")

    def test_current_published_resume_and_waiting_changes_are_distinct(self):
        self.assertEqual(self.state(self.working(),self.preview()),"published")
        for working in (self.working(state="hidden"),
                        self.working(token="2"),self.working(has_draft=True)):
            with self.subTest(working=working):
                self.assertEqual(self.state(working,self.preview()),"changes_waiting")

    def test_pending_suggestion_does_not_change_the_current_publication(self):
        working=self.working();working["counts"]["waiting"]=1
        working["unplaced"].append({"item_ref":"pending-only","origin":"pending","state":"waiting","children":[]})
        self.assertEqual(self.state(working,self.preview()),"published")

    def test_missing_publication_version_basis_is_unknown_without_guessing_a_token_encoding(self):
        working=self.working();working["sections"][0]["items"][0].pop("saved_content_version")
        self.assertEqual(self.state(working,self.preview()),"unknown")

    def test_real_hex_catalog_publication_and_saved_edit_over_http(self):
        import json
        from urllib.request import Request,urlopen
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        owner="g-member-a"
        with Mvp1AcceptanceServer() as server:
            item=server.shared.canonical.create_private(owner,{"command_id":str(uuid4()),"record_type":"skill",
                "values":{"name":"Fictional systems skill","summary":"Original detail"}})
            key=item["record_key"]
            server.shared.seed_publication(owner,[(key,True,False)])
            def read():
                with urlopen(Request(server.url+"/api/resume-intake/me/guide/working-set",
                                     headers={"Cookie":"mvp1-synthetic-owner="+owner}),timeout=10) as response:
                    self.assertEqual(response.headers["Cache-Control"],"private, no-store")
                    return json.load(response)
            published=read()
            self.assertEqual(published["publication_state"],"published")
            self.assertEqual(server.shared.draft.get_workspace(owner)["items"][0]["content_token"],"0000000000000001")
            server.intake.submit(owner,{"type":"add_submission","request_id":str(uuid4()),"text":"An unaccepted fictional note"})
            self.assertEqual(read()["publication_state"],"published")
            workspace=server.shared.draft.get_workspace(owner)
            current=next(row for row in workspace["items"] if row["record_key"]==key)
            server.shared.draft.commit(owner,{"type":"save_item","request_id":str(uuid4()),"record_key":key,
                "record_type":"skill","expected_draft_version":workspace["draft_version"],
                "expected_content_token":current["content_token"],"expected_access_revision":current["access_revision"],
                "values":{"summary":"New private detail"}})
            edited=read()
            self.assertEqual(edited["publication_state"],"changes_waiting")
            self.assertNotEqual(edited["working_set_token"],published["working_set_token"])

    def test_real_http_saved_role_bullet_nesting_per_state_counts_and_no_unplaced_bullet(self):
        import json
        from urllib.request import Request,urlopen
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        owner="g-member-a"
        with Mvp1AcceptanceServer() as server:
            role=server.shared.canonical.create_private(owner,{"command_id":str(uuid4()),"record_type":"role",
                "values":{"role_title":"Engineer","employer_name":"Fictional Acorn Works"}})
            bullet=server.shared.canonical.create_private(owner,{"command_id":str(uuid4()),"record_type":"accomplishment",
                "parent_key":role["record_key"],"values":{"wording":"Reviewed 12 fictional records."}})
            with urlopen(Request(server.url+"/api/resume-intake/me/guide/working-set",
                                 headers={"Cookie":"mvp1-synthetic-owner="+owner}),timeout=10) as response:
                self.assertEqual(response.headers["Cache-Control"],"private, no-store")
                working=json.load(response)
            self.assertTrue(working["success"])
            experience=next(section for section in working["sections"] if section["key"]=="experience")
            saved_one={"saved":1,"waiting":0,"hidden":0,"skipped":0,"updates_waiting":0}
            self.assertEqual({"top":working["counts"],"children":working["child_counts"],
                "child_count":working["child_count"],"cards":experience["counts"],
                "section_children":experience["child_counts"],
                "unplaced":[row["item_ref"] for row in working["unplaced"]]},
                {"top":saved_one,"children":saved_one,"child_count":1,"cards":saved_one,
                 "section_children":saved_one,"unplaced":[]})
            self.assertEqual([row["item_ref"] for row in experience["items"]],[role["record_key"]])
            children=experience["items"][0]["children"]
            self.assertEqual([row["item_ref"] for row in children],[bullet["record_key"]])
            self.assertEqual(children[0]["parent_ref"],role["record_key"])
            self.assertEqual((children[0]["origin"],children[0]["state"]),("saved","saved"))
            self.assertEqual(children[0]["values"],{"wording":"Reviewed 12 fictional records."})
            # Lane D reads this same draft projection, rather than this Guide
            # endpoint. Its real HTTP response must carry the relationship too.
            with urlopen(Request(server.url+"/api/resume-drafts/me",
                                 headers={"Cookie":"mvp1-synthetic-owner="+owner}),timeout=10) as response:
                self.assertEqual(response.headers["Cache-Control"],"private, no-store")
                draft=json.load(response)
            self.assertTrue(draft["success"])
            self.assertEqual(next(row for row in draft["items"] if row["record_key"]==bullet["record_key"])["parent_key"],role["record_key"])


class GuideReferenceResolutionTests(unittest.TestCase):
    def test_owner_bound_saved_references_follow_private_edits_and_filter_hidden_pending_or_wrong_type(self):
        from services.resume_guide_contract import resolve_guide_references
        from hashlib import sha256
        from copy import deepcopy
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_intake_service import ResumeIntakeService
        from services.resume_intake_policy import selected_policy_for_tests
        shared, owner = SharedMvp1Fixture(), 'reference-fictional-owner'
        def create(kind, values, parent=None, member=owner):
            return shared.canonical.create_private(member,{'command_id':str(uuid4()),'record_type':kind,
                'parent_key':parent,'values':values})['record_key']
        role = create('role',{'role_title':'Fictional Engineer','employer_name':'Fictional Orchard',
            'summary':'Original exact summary line.','start_date':'2021-01-01','date_precision':'year'})
        bullet = create('accomplishment',{'wording':'Reviewed 12 fictional records.','metric_value':'12',
            'metric_label':'fictional records'},role)
        skill = create('skill',{'name':'Fictional skill'})
        foreign_role = create('role',{'role_title':'Other role','employer_name':'Other employer'},member='other-fictional-owner')
        foreign = create('accomplishment',{'wording':'Other member secret.'},foreign_role,member='other-fictional-owner')
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),draft_service=shared.draft,
            policy=selected_policy_for_tests())
        pending = service.submit(owner,{'request_id':str(uuid4()),'text':'A pending fictional detail.'})
        pending_ref = service.working_set(owner)['unplaced'][0]['item_ref']
        summary = {'role_record_key':role,'line_digest':sha256(b'Original exact summary line.').hexdigest()}
        choices = {skill:[bullet,summary,foreign,pending_ref,skill]}
        original_choices = deepcopy(choices)
        result = resolve_guide_references(service.working_set(owner),evidence_refs=choices,highlight_refs=[bullet])
        self.assertEqual([row['text'] for row in result['skill_evidence'][skill]],
            ['Reviewed 12 fictional records.','Original exact summary line.'])
        self.assertEqual(result['highlight_tiles'][0]['metric_value'],'12')
        self.assertNotIn('Other member secret',str(result))
        self.assertEqual(choices,original_choices)
        workspace = shared.draft.get_workspace(owner)
        item = next(row for row in workspace['items'] if row['record_key']==bullet)
        shared.draft.commit(owner,{'type':'save_item','request_id':str(uuid4()),'record_key':bullet,'record_type':'accomplishment',
            'expected_draft_version':workspace['draft_version'],'expected_content_token':item['content_token'],
            'expected_access_revision':item['access_revision'],'values':{'wording':'Reviewed 15 fictional records.',
                'metric_value':None}})
        edited = resolve_guide_references(service.working_set(owner),evidence_refs=choices,highlight_refs=[bullet])
        self.assertEqual(edited['skill_evidence'][skill][0]['text'],'Reviewed 15 fictional records.')
        self.assertEqual(edited['highlight_tiles'],[])
        working = service.working_set(owner)
        saved_role = service.working_item(owner,role)
        service.set_guide_visibility(owner,{'request_id':str(uuid4()),'item_ref':role,'hidden':True,
            'expected_working_set_token':working['working_set_token'],'expected_item_revision':saved_role['saved_revision']})
        hidden = resolve_guide_references(service.working_set(owner),evidence_refs=choices,highlight_refs=[bullet])
        self.assertEqual(hidden['skill_evidence'][skill],[])
        self.assertEqual(hidden['highlight_tiles'],[])
        self.assertEqual(choices,original_choices)
        working = service.working_set(owner)
        service.set_guide_visibility(owner,{'request_id':str(uuid4()),'item_ref':role,'hidden':False,
            'expected_working_set_token':working['working_set_token'],
            'expected_item_revision':service.working_item(owner,role)['saved_revision']})
        restored = resolve_guide_references(service.working_set(owner),evidence_refs=choices,highlight_refs=[bullet])
        self.assertEqual([row['text'] for row in restored['skill_evidence'][skill]],
            ['Reviewed 15 fictional records.','Original exact summary line.'])
        self.assertEqual(choices,original_choices)

    def test_summary_digest_needs_recheck_after_edit_and_highlights_are_capped_at_four(self):
        from services.resume_guide_contract import resolve_guide_references
        from hashlib import sha256
        role, skill = str(uuid4()),str(uuid4())
        def node(key,kind,values,children=()):
            return {'item_ref':key,'identity_aliases':[],'record_type':kind,'origin':'saved','state':'saved',
                'values':values,'children':list(children)}
        bullets = [node(str(uuid4()),'accomplishment',{'wording':'Exact '+str(n),'metric_value':str(n),
            'metric_label':'original label'}) for n in range(6)]
        for bullet in bullets:
            bullet['parent_ref']=role
        working = {'sections':[{'items':[node(role,'role',{'summary':'Changed exact line.','employer_name':'Fictional'},bullets),
            node(skill,'skill',{'name':'Fictional'})]}],'unplaced':[],'non_tab_items':[]}
        result = resolve_guide_references(working,evidence_refs={skill:[{'role_record_key':role,
            'line_digest':sha256(b'Original exact line.').hexdigest()}]},highlight_refs=[row['item_ref'] for row in bullets])
        self.assertEqual(result['skill_evidence'][skill],[])
        self.assertEqual([row['reason'] for row in result['needs_recheck']],['summary_changed'])
        self.assertEqual([row['metric_value'] for row in result['highlight_tiles']],['0','1','2','3'])


class GuideReviewDeltaTests(unittest.TestCase):
    def row(self, key="proposal-a", **changes):
        return {"proposal_key":key,"record_type":"skill","state":"pending","created_at":"same-time",
                "binding":{"source_key":"source-a","source_version":1},"proposed_values":{"name":"Python"},
                "span_start":0,"span_end":6,"quote":"Python",**changes}

    def project(self, rows, canonical=(), history=None):
        from services.resume_guide_contract import project_working_set
        return project_working_set("owner-a",{"proposals":{r["proposal_key"]:r for r in rows},"sources":{}},
                                   canonical,0,history=history)

    def test_saved_hidden_card_child_pending_rejected_table(self):
        for hidden in (False,True):
            for state in ("pending","rejected"):
                for child in (False,True):
                    with self.subTest(hidden=hidden,state=state,child=child):
                        parent=str(uuid4());target=str(uuid4()) if child else parent
                        items=[{"record_key":parent,"record_type":"role","content_token":"1","values":{}}]
                        if child:items.append({"record_key":target,"record_type":"accomplishment","parent_key":parent,
                                              "content_token":"1","values":{"wording":"Saved fact"}})
                        row=self.row(target_key=target,record_type="accomplishment" if child else "role",state=state)
                        result=self.project([row],items,history={"inclusion":{parent:hidden,target:hidden}})
                        section=next(s for s in result["sections"] if s["key"]=="experience")
                        item=section["items"][0]["children"][0] if child else section["items"][0]
                        self.assertEqual(item["state"],"hidden" if hidden else "saved")
                        self.assertEqual(item["update_waiting"],state=="pending")
                        self.assertEqual(len(result["legacy_outcomes"]),int(state=="rejected"))
                        self.assertEqual(section["tab_visible"],not hidden)

    def test_waiting_child_counts_are_separate_from_role_card_counts(self):
        parent=str(uuid4())
        result=self.project([self.row(record_type="accomplishment",proposed_values={"suggested_parent_key":parent})],
            [{"record_key":parent,"record_type":"role","content_token":"1","values":{}}])
        section=next(s for s in result["sections"] if s["key"]=="experience")
        self.assertEqual(section["counts"]["saved"],1)
        self.assertEqual(section["counts"]["waiting"],0)
        self.assertEqual(section["child_counts"]["waiting"],1)
        self.assertEqual(result["child_counts"]["waiting"],1)

    def test_projects_use_stored_section_story_contact_are_not_unplaced_notes(self):
        rows=[self.row("project",record_type="knowledge",resume_conversation_v1={"presentation_section":"Independent Project"}),
              self.row("story",record_type="knowledge",resume_conversation_v1={"presentation_section":"My Story"}),
              self.row("contact",record_type="knowledge",resume_conversation_v1={"presentation_section":"Contact details"})]
        saved={"record_key":str(uuid4()),"record_type":"knowledge","content_token":"1",
               "values":{"presentation_section":"Independent Project","wording":"Saved project"}}
        result=self.project(rows,[saved])
        projects=next(s for s in result["sections"] if s["key"]=="projects")
        self.assertEqual(len(projects["items"]),2)
        self.assertTrue(projects["tab_visible"])
        self.assertEqual(result["unplaced"],[])
        self.assertEqual({i["section"] for i in result["non_tab_items"]},{"story","contact"})
        self.assertEqual(result["counts"]["waiting"],1)

    def test_existing_ref_and_alias_are_reserved_before_a_tied_new_row(self):
        from services.resume_guide_contract import bind_item_identities
        snapshot={"proposals":{"z-old":self.row("z-old")}}
        bind_item_identities("owner-a",snapshot)
        old=snapshot["proposals"]["z-old"]["item_ref"]
        snapshot["proposals"]["a-new"]=self.row("a-new")
        bind_item_identities("owner-a",snapshot)
        self.assertNotEqual(snapshot["proposals"]["a-new"]["item_ref"],old)
        self.assertEqual(snapshot["proposals"]["z-old"]["item_ref"],old)
        alias=snapshot["proposals"]["a-new"]["item_ref"]
        snapshot["proposals"]["z-old"]["identity_aliases"]=[alias]
        del snapshot["proposals"]["a-new"]
        snapshot["proposals"]["a-next"]=self.row("a-next")
        bind_item_identities("owner-a",snapshot)
        self.assertNotIn(snapshot["proposals"]["a-next"]["item_ref"],{old,alias})

    def test_pre_upgrade_read_and_next_commit_use_one_identity_without_read_writes(self):
        from services.resume_guide_contract import bind_item_identities
        row=self.row();untouched=deepcopy(row)
        ref=next(s for s in self.project([row])["sections"] if s["key"]=="skills")["items"][0]["item_ref"]
        snapshot={"proposals":{row["proposal_key"]:row}}
        bind_item_identities("owner-a",snapshot)
        self.assertEqual(row["item_ref"],ref)
        self.assertNotIn("item_ref",untouched)

    def test_bad_identity_and_revision_cycle_cannot_block_real_source_purge(self):
        for defect in ("identity","cycle"):
            service,_,_=build_service()
            owner="fictional-purge-"+defect
            receipt=service.submit(owner,{"type":"add_submission","request_id":str(uuid4()),"text":"Fictional private note"})
            snapshot=service.repository._owners[owner]
            row=next(iter(snapshot["proposals"].values()));source=row["binding"]["source_key"]
            if defect=="identity":row["item_ref"]="bad annotation"
            else:row.setdefault("resume_conversation_v1",{})["revision_of"]=row["proposal_key"]
            result=service.purge_source(owner,{"request_id":str(uuid4()),"source_key":source})
            self.assertEqual(result["outcome"],"purged")
            self.assertFalse(service.repository.load_owner(owner)["sources"][source]["text"])


if __name__ == "__main__":
    unittest.main()
