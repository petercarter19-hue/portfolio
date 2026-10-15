"""Real Flask HTTP journeys for the MVP1 C composer.

These issue actual requests through Flask's test client, including a real
multipart upload whose bytes reach an in-process parser/transcription stub.
They are not browser proof, SQL engine proof or live provider proof, and the
injected in-memory stores are labelled as such.
"""

from __future__ import annotations

import io
import json
import unittest
from uuid import uuid4

from app import app
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_guide_service import ResumeGuideService
from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.resume_intake_policy import selected_policy_for_tests,fixture_policy_for_tests
from services.resume_intake_repository import (
    InMemoryResumeIntakeRepository,
    ResumeIntakeStoreUnavailable,
)
from services.resume_intake_service import ResumeIntakeService
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter


CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_INTAKE_ENABLED",
    "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED",
    "RESUME_INTAKE_SERVICE",
    "RESUME_GUIDE_SERVICE",
)


class GuideProposalHttpTests(unittest.TestCase):
    def test_actual_reference_route_uses_owner_http_token_and_keeps_public_copy_unchanged(self):
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        with Mvp1AcceptanceServer() as server:
            owner = 'g-member-a'
            def create(kind, values, parent=None):
                return server.shared.canonical.create_private(owner,{'command_id':str(uuid4()),'record_type':kind,
                    'parent_key':parent,'values':values})['record_key']
            role = create('role',{'role_title':'Fictional Engineer','employer_name':'Fictional Orchard'})
            bullet = create('accomplishment',{'wording':'Reviewed 12 fictional records.','metric_value':'12'},role)
            skill = create('skill',{'name':'Fictional skill'})
            def read():
                with urlopen(Request(server.url+'/api/resume-intake/me/guide/working-set',
                        headers={'Cookie':'mvp1-synthetic-owner='+owner}),timeout=10) as response:
                    return json.load(response)
            initial = read()
            payload = {'request_id':str(uuid4()),'kind':'skill','item_ref':skill,'references':[bullet],
                'expected_working_set_token':initial['working_set_token']}
            def post(payload, member=owner):
                return urlopen(Request(server.url+'/api/resume-intake/me/guide/references',method='POST',
                    data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-PeerSlate-Request':'same-origin',
                        'Cookie':'mvp1-synthetic-owner='+member}),timeout=10)
            with self.assertRaises(HTTPError) as foreign:
                post(payload,'g-member-b')
            self.assertEqual(foreign.exception.code,404)
            foreign.exception.close()
            with post(payload) as response:
                self.assertEqual(response.headers['Cache-Control'],'private, no-store')
                self.assertEqual(json.load(response)['outcome'],'saved_privately')
            with post(payload) as response:
                self.assertTrue(json.load(response)['replayed'])
            # D6b carries references on the in-memory publisher; a SQL-backed one keeps them closed.
            from unittest.mock import Mock, patch as _patch
            with _patch.object(server.shared.publication,'sql_repository',Mock()):
                current = read()
            self.assertEqual(current['references']['skill_evidence'][skill][0]['text'],'Reviewed 12 fictional records.')
            self.assertEqual(current['publication']['read_state'],'blocked')
            self.assertIsNone(current['publication']['change_count'])
            self.assertIsNone(server.shared.publication.owner_preview(owner)['current'])
            with self.assertRaises(HTTPError) as stale:
                post({**payload,'request_id':str(uuid4()),'references':[]})
            self.assertEqual(stale.exception.code,409)
            stale.exception.close()

    def test_guide_publication_basis_hides_role_and_contact_only_after_explicit_publish(self):
        from urllib.request import Request, urlopen
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        with Mvp1AcceptanceServer() as server:
            owner = "g-member-a"
            keys = []
            for kind, values in (("role", {"role_title":"Fictional Engineer", "employer_name":"Fictional Orchard"}),
                    ("knowledge", {"title":"Contact details", "wording":"fictional@example.test", "classification":"work"})):
                item = server.shared.canonical.create_private(owner, {"command_id":str(uuid4()), "record_type":kind, "values":values})
                keys.append(item["record_key"])
            server.shared.seed_publication(owner, [(key, True, True) for key in keys])
            headers = {"Cookie":"mvp1-synthetic-owner="+owner}
            def read():
                with urlopen(Request(server.url+"/api/resume-intake/me/guide/working-set", headers=headers), timeout=10) as response:
                    return json.load(response)
            with (patch.object(server.shared.policy.repository,"save_owner",wraps=server.shared.policy.repository.save_owner) as policy_save,
                    patch.object(server.shared.draft.repository,"save_owner",wraps=server.shared.draft.repository.save_owner) as draft_save,
                    patch.object(server.shared.publication.repository,"save_owner",wraps=server.shared.publication.repository.save_owner) as publication_save):
                initial = read()
                self.assertEqual(initial["publication"]["change_count"],0)
                self.assertEqual(initial["publication_state"],"published")
                self.assertEqual(set(initial["publication"]["membership"]["display"]),set(keys))
                policy_save.assert_not_called(); draft_save.assert_not_called(); publication_save.assert_not_called()
            for key in keys:
                item = server.intake.working_item(owner,key)
                server.intake.set_guide_visibility(owner, {"request_id":str(uuid4()),"item_ref":key,"hidden":True,
                    "expected_working_set_token":server.intake.working_set(owner)["working_set_token"],
                    "expected_item_revision":item["saved_revision"]})
            hidden = read()
            basis = hidden["publication"]
            self.assertEqual((hidden["publication_state"],basis["change_count"]),("changes_waiting",2))
            self.assertEqual(basis["membership"],{"display":[],"visitor_ai":[]})
            self.assertEqual(set(server.shared.publication.owner_preview(owner)["current"]["display"]),set(keys))
            self.assertEqual(set(server.shared.publication.owner_preview(owner)["current"]["visitor_ai"]),set(keys))
            for item in [row for section in hidden["sections"] for row in section["items"]]+hidden["non_tab_items"]:
                self.assertTrue(item["published_display"])
                self.assertFalse(item["proposed_display"])
            server.shared.publication.commit(owner,{"type":"publish","request_id":str(uuid4()),
                "candidate":basis["candidate"],"reviewed_digest":basis["reviewed_digest"],"profile_identity":None})
            current = server.shared.publication.owner_preview(owner)["current"]
            self.assertEqual(current["display"],{})
            self.assertEqual(current["visitor_ai"],{})
            self.assertEqual(read()["publication"]["change_count"],0)

    def test_real_visibility_uses_the_http_working_token_and_restores_waiting(self):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        with Mvp1AcceptanceServer() as server:
            owner = "g-member-a"
            server.intake.submit(owner, {"request_id": str(uuid4()), "text": "Original fictional source."})
            path = server.url + "/api/resume-intake/me/guide/working-set"
            headers = {"Cookie": "mvp1-synthetic-owner=" + owner}
            def working():
                with urlopen(Request(path, headers=headers), timeout=10) as response:
                    return json.load(response)
            first = working()
            item = first["unplaced"][0]
            payload = {"request_id": str(uuid4()), "item_ref": item["item_ref"], "hidden": True,
                "expected_working_set_token": first["working_set_token"], "expected_item_revision": item["revision"]}
            def post(payload, identity=owner, same_origin=True):
                post_headers = {"Cookie": "mvp1-synthetic-owner=" + identity, "Content-Type": "application/json"}
                if same_origin:
                    post_headers["X-PeerSlate-Request"] = "same-origin"
                return urlopen(Request(server.url + "/api/resume-intake/me/guide/visibility", method="POST",
                    data=json.dumps(payload).encode(), headers=post_headers), timeout=10)
            for identity, origin, status in (("g-member-b", True, 404), (owner, False, 403)):
                with self.assertRaises(HTTPError) as refused:
                    post(payload, identity, origin)
                self.assertEqual(refused.exception.code, status)
                refused.exception.close()
            with post(payload) as response:
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                self.assertEqual(json.load(response)["outcome"], "hidden")
            with post(payload) as response:
                self.assertTrue(json.load(response)["replayed"])
            current = working()
            self.assertEqual(current["unplaced"][0]["state"], "hidden")
            with self.assertRaises(HTTPError) as stale:
                post({**payload, "request_id": str(uuid4()), "hidden": False})
            self.assertEqual(stale.exception.code, 409)
            stale.exception.close()
            with post({**payload, "request_id": str(uuid4()), "hidden": False,
                    "expected_working_set_token": current["working_set_token"],
                    "expected_item_revision": current["unplaced"][0]["revision"]}) as response:
                self.assertEqual(json.load(response)["outcome"], "waiting")
            self.assertEqual(working()["unplaced"][0]["item_ref"], item["item_ref"])
            self.assertEqual(server.shared.canonical.list_items(owner), [])

    def test_real_guide_confirmation_keeps_overlength_original_and_returns_actual_count(self):
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        owner = "g-member-a"
        with Mvp1AcceptanceServer() as server:
            original = " ".join(["original"] * 71)
            submitted = server.intake.submit(owner, {"request_id": str(uuid4()), "text": original})
            key = submitted["proposals"][0]["proposal_key"]
            before = server.intake.repository.load_owner(owner)["proposals"][key]["proposed_values"].copy()
            payload = {"request_id": str(uuid4()), "proposal_key": key, "decision": "accept", "guide_review": True,
                "guide_section": "impact_statement", "confirmed_values": {"record_type": "knowledge",
                    "title": "Professional summary", "wording": original, "classification": "work"}}
            request = Request(server.url + "/api/resume-intake/me/proposals/decision", method="POST",
                data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
                    "X-PeerSlate-Request": "same-origin", "Cookie": "mvp1-synthetic-owner=" + owner})
            with self.assertRaises(HTTPError) as refused:
                urlopen(request, timeout=10)
            with refused.exception as response:
                self.assertEqual(response.status, 400)
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                data = json.load(response)
            self.assertEqual((data["code"], data["actual_count"], data["limit"]), ("impact_statement_too_long", 71, 70))
            after = server.intake.repository.load_owner(owner)["proposals"][key]
            self.assertEqual(after["state"], "pending")
            self.assertEqual(after["proposed_values"], before)
            self.assertEqual(server.shared.canonical.list_items(owner), [])


class RecordingTranscriber:
    def __init__(self, transcript="I led the migration."):
        self.transcript = transcript
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"bytes": audio_bytes, "content_type": content_type})
        return {"provider_transcript": self.transcript, "provider_request_id": "stub", "duration_seconds": 3.0}


def wav_bytes():
    payload = b"\x00" * 64
    return b"RIFF" + (len(payload) + 36).to_bytes(4, "little") + b"WAVE" + payload


class IntakeRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.original = {key: app.config.get(key) for key in CONFIG_KEYS}
        self.catalog = InMemoryCanonicalCatalog()
        self.draft_service = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(), catalog=self.catalog
        )
        self.repository = InMemoryResumeIntakeRepository()
        self.received_documents = []
        self.transcriber = RecordingTranscriber()

        def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
            self.received_documents.append({"content_type": content_type, "data": admitted})
            from services.my_opportunities.member_import_service import ImportStageOutcome

            return (
                "Systems Engineer at Northrop Grumman. Supports requirements management.",
                "extracted", None, False,
                (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                    outcome="extracted", reason_code=None, occurred_at=now),),
            )

        self.service = ResumeIntakeService(
            repository=self.repository,
            draft_service=self.draft_service,
            document_adapter=ResumeDocumentAdapter(),
            transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
            policy=selected_policy_for_tests(),
            document_pipeline=pipeline,
        )
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="member-a",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_INTAKE_ENABLED=True,
            PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=True,
            RESUME_INTAKE_SERVICE=self.service,
            RESUME_GUIDE_SERVICE=ResumeGuideService(repository=self.repository),
        )

    def tearDown(self):
        app.config.update(self.original)

    def client(self):
        return app.test_client()

    def submission(self, client, payload, files=None):
        data = {"request": json.dumps(payload)}
        if files:
            for field, (filename, content, content_type) in files.items():
                data["file:" + field] = (io.BytesIO(content), filename, content_type)
        return client.post(
            "/api/resume-intake/me/submissions",
            headers={"X-PeerSlate-Request": "same-origin"},
            data=data,
            content_type="multipart/form-data",
        )


class GateTests(unittest.TestCase):
    def setUp(self):
        self.original = {key: app.config.get(key) for key in CONFIG_KEYS}
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="member-a",
            PEERSLATE_RESUME_INTAKE_ENABLED=False,
            PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=False,
        )

    def tearDown(self):
        app.config.update(self.original)

    def test_feature_off_is_a_neutral_404(self):
        client = app.test_client()
        self.assertEqual(client.get("/api/resume-intake/me").status_code, 404)
        self.assertEqual(client.post('/api/resume-intake/me/saved-choices/review',json={},
            headers={'X-PeerSlate-Request':'same-origin'}).status_code,404)
        self.assertEqual(
            client.post(
                "/api/resume-intake/me/submissions",
                headers={"X-PeerSlate-Request": "same-origin"},
                data={"request": "{}"},
                content_type="multipart/form-data",
            ).status_code,
            404,
        )

    def test_signed_out_is_not_found_without_identity_leak(self):
        app.config.update(PEERSLATE_RESUME_INTAKE_ENABLED=True)
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=False, PEERSLATE_DEV_USER_KEY=None)
        response = app.test_client().get("/api/resume-intake/me")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("member-a", response.get_data(as_text=True))

    def test_editor_page_is_unchanged_while_the_composer_flag_is_off(self):
        app.config.update(
            PEERSLATE_RESUME_EDITOR_ENABLED=True,
            PEERSLATE_RESUME_INTAKE_ENABLED=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="member-a",
        )
        page = app.test_client().get("/app/resume")
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn("resume-editor", body)
        self.assertNotIn("resume-intake", body)


class ComposerHttpTests(IntakeRoutesTestCase):
    def test_recovery_and_confirmation_work_when_actual_interview_feature_is_disabled(self):
        from tests.test_my_data_intake_ai import add_request
        from unittest.mock import Mock
        keys = ('PEERSLATE_RESUME_EDITOR_ENABLED', 'PEERSLATE_RESUME_INTERVIEW_ENABLED', 'RESUME_PRIVATE_ASSISTANCE_SERVICE')
        old = {key: app.config.get(key) for key in keys}
        self.addCleanup(app.config.update, old)
        forbidden_assistance = Mock(side_effect=AssertionError('No provider or reservation may be used by recovery'))
        app.config.update(PEERSLATE_RESUME_EDITOR_ENABLED=True, PEERSLATE_RESUME_INTERVIEW_ENABLED=False,
            RESUME_PRIVATE_ASSISTANCE_SERVICE=forbidden_assistance)
        self.service._interpreter = lambda text, kind: [{'kind': 'inferred_wording', 'record_type': 'role',
            'confidence': 'certain', 'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}}]
        original = self.service.submit('member-a', add_request(text='Engineer at Example Labs.'))['proposals'][0]
        self.service.decide('member-a', {'request_id': str(uuid4()), 'proposal_key': original['proposal_key'], 'decision': 'reject'})
        client = self.client(); headers = {'X-PeerSlate-Request': 'same-origin'}
        self.assertEqual(client.post('/api/resume-intake/me/interview', json={}, headers=headers).status_code, 404)
        row = client.get('/api/resume-intake/me').get_json()['resume_recoverable_details'][0]
        review = client.post('/api/resume-intake/me/excluded-details/review', headers=headers, json={
            'request_id': str(uuid4()), 'recovery_key': row['recovery_key'], 'recovery_token': row['recovery_token']})
        self.assertEqual(review.status_code, 200)
        pending = review.get_json()['proposals'][0]
        response = client.post('/api/resume-intake/me/proposals/decision', headers=headers, json={
            'request_id': str(uuid4()), 'proposal_key': pending['proposal_key'], 'decision': 'accept',
            'confirmed_values': pending['proposed_values']})
        self.assertEqual(response.status_code, 200); self.assertEqual(len(self.catalog.list_items('member-a')), 1)
        forbidden_assistance.assert_not_called()

    def test_excluded_detail_review_enforces_identity_origin_closed_payload_and_explicit_confirm(self):
        from tests.test_my_data_intake_ai import add_request
        endpoint = '/api/resume-intake/me/excluded-details/review'
        client = self.client(); headers = {'X-PeerSlate-Request': 'same-origin'}
        self.assertEqual(client.post(endpoint, json={}).status_code, 403)
        self.assertEqual(client.post(endpoint, json={}, headers={**headers, 'Origin': 'https://elsewhere.invalid'}).status_code, 403)
        self.assertEqual(client.post(endpoint, json={'owner': 'forged'}, headers=headers).status_code, 400)
        self.service._interpreter = lambda text, kind: [{'kind': 'inferred_wording', 'record_type': 'role',
            'confidence': 'certain', 'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}}]
        original = self.service.submit('member-a', add_request(text='Engineer at Example Labs.'))['proposals'][0]
        self.service.decide('member-a', {'request_id': str(uuid4()), 'proposal_key': original['proposal_key'], 'decision': 'reject'})
        row = client.get('/api/resume-intake/me').get_json()['resume_recoverable_details'][0]
        request = {'request_id': str(uuid4()), 'recovery_key': row['recovery_key'], 'recovery_token': row['recovery_token']}
        response = client.post(endpoint, json=request, headers=headers)
        self.assertEqual(response.status_code, 200)
        pending = response.get_json()['proposals'][0]
        self.assertFalse(response.get_json()['saved']); self.assertEqual(self.catalog.list_items('member-a'), [])
        self.assertEqual(client.post(endpoint, json=request, headers=headers).get_json()['proposals'][0]['proposal_key'], pending['proposal_key'])
        confirm = client.post('/api/resume-intake/me/proposals/decision', json={
            'request_id': str(uuid4()), 'proposal_key': pending['proposal_key'], 'decision': 'accept',
            'confirmed_values': pending['proposed_values']}, headers=headers)
        self.assertEqual(confirm.status_code, 200); self.assertEqual(len(self.catalog.list_items('member-a')), 1)
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=False, PEERSLATE_DEV_USER_KEY=None)
        response = client.post(endpoint, json=request, headers=headers)
        self.assertEqual(response.status_code, 404); self.assertIn('no-store', response.headers['Cache-Control'])

    def test_saved_choice_review_enforces_private_identity_origin_and_closed_request(self):
        endpoint='/api/resume-intake/me/saved-choices/review'
        client=self.client()
        self.assertEqual(client.post(endpoint,json={}).status_code,403)
        self.assertEqual(client.post(endpoint,json={},headers={'X-PeerSlate-Request':'same-origin',
            'Origin':'https://unrelated.invalid'}).status_code,403)
        self.assertEqual(client.post(endpoint,json={'bypass':True},
            headers={'X-PeerSlate-Request':'same-origin'}).status_code,400)
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=False,PEERSLATE_DEV_USER_KEY=None)
        response=client.post(endpoint,json={},headers={'X-PeerSlate-Request':'same-origin'})
        self.assertEqual(response.status_code,404)
        self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertEqual(self.catalog.list_items('member-a'),[])

    def test_workspace_read_is_private_and_does_not_process(self):
        client = self.client()
        response = client.get("/api/resume-intake/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        payload = response.get_json()
        self.assertFalse(payload["capabilities"]["starts_processing_on_read"])
        self.assertFalse(payload["capabilities"]["publishes"])
        self.assertEqual(payload["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertEqual(self.repository.load_owner("member-a")["jobs"], {})

    def test_same_origin_header_is_required_for_writes(self):
        response = self.client().post(
            "/api/resume-intake/me/submissions",
            json={"type": "add_submission", "request_id": str(uuid4()), "text": "hi"},
        )
        self.assertEqual(response.status_code, 403)

    def test_cross_origin_write_is_rejected(self):
        response = self.client().post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin", "Origin": "https://evil.example"},
            json={"request_id": str(uuid4()), "proposal_key": str(uuid4()), "decision": "reject"},
        )
        self.assertEqual(response.status_code, 403)

    def test_multipart_add_saves_structured_facts_and_reports_partial_truth(self):
        client = self.client()
        response = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r1", "record_type": "role",
                     "values": {
                         "role_title": "Systems Engineer",
                         "employer_name": "Northrop Grumman",
                         "location_text": None,
                         "summary": None,
                         "start_date": None,
                         "end_date": None,
                         "date_precision": "unknown",
                         "employment_type": None,
                         "current_role": False,
                     }},
                ],
                "text": "One project I worked on involved a cross-team migration.",
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "text/plain", "filename": "resume.txt"}
                ],
            },
            files={"d1": ("resume.txt", b"Systems Engineer at Northrop Grumman", "text/plain")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["saved"], 1)
        self.assertEqual(payload["summary"]["unresolved"], 2)
        self.assertFalse(payload["summary"]["all_saved"])
        self.assertEqual(payload["outcome"], "partial")
        # The server really received the uploaded bytes through the seam.
        self.assertEqual(len(self.received_documents), 1)
        self.assertEqual(self.received_documents[0]["data"], b"Systems Engineer at Northrop Grumman")
        self.assertEqual(self.received_documents[0]["content_type"], "text/plain")
        items = self.catalog.list_items("member-a")
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["resume_display"])

    def test_rejected_file_is_a_failed_item_and_other_work_is_kept(self):
        client = self.client()
        response = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s1", "record_type": "skill",
                           "values": {"name": "MBSE", "summary": None}}],
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "application/zip", "filename": "bad.zip"}
                ],
            },
            files={"d1": ("bad.zip", b"PK\x03\x04nope", "application/zip")},
        )
        payload = response.get_json()
        self.assertEqual(payload["summary"]["saved"], 1)
        self.assertEqual(payload["summary"]["failed"], 1)
        failed = next(row for row in payload["results"] if row["outcome"] == "failed")
        self.assertEqual(failed["code"], "unsupported_type")

    def test_idempotent_retry_returns_the_original_structure(self):
        client = self.client()
        request_id = str(uuid4())
        payload = {
            "type": "add_submission",
            "request_id": request_id,
            "text": "Only a note.",
        }
        first = self.submission(client, payload).get_json()
        second = self.submission(client, payload).get_json()
        self.assertFalse(first["replayed"])
        self.assertTrue(second["replayed"])
        self.assertEqual(
            first["submission"]["submission_key"], second["submission"]["submission_key"]
        )
        changed = self.submission(client, {**payload, "text": "Different note."})
        self.assertEqual(changed.status_code, 409)
        self.assertTrue(changed.get_json()["input_preserved"])

    def test_recording_transcription_reaches_the_provider_with_real_bytes(self):
        client = self.client()
        response = client.post(
            "/api/resume-intake/me/recordings",
            headers={"X-PeerSlate-Request": "same-origin"},
            data={
                "request": json.dumps({
                    "request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0
                }),
                "recording": (io.BytesIO(wav_bytes()), "recording.wav", "audio/wav"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["transcript"], "I led the migration.")
        self.assertEqual(len(self.transcriber.calls), 1)
        self.assertTrue(self.transcriber.calls[0]["bytes"].startswith(b"RIFF"))

    def test_proposal_decision_flow_over_http(self):
        client = self.client()
        # An Impact entry is a child of an existing owner entry, so seed a role.
        seeded = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role",
                           "values": {
                               "role_title": "Engineering Manager",
                               "employer_name": "Northrop Grumman",
                               "location_text": None, "summary": None,
                               "start_date": None, "end_date": None,
                               "date_precision": "unknown", "employment_type": None,
                               "current_role": False,
                           }}],
            },
        ).get_json()
        parent_key = seeded["saved_items"][0]["record_key"]
        created = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()),
             "text": "I supervised twelve engineers."},
        ).get_json()
        proposal_key = created["proposals"][0]["proposal_key"]
        decided = client.post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": {
                    "record_type": "accomplishment",
                    "wording": "Supervised twelve engineers.",
                    "metric_value": "12",
                    "metric_label": "engineers",
                    "parent_key": parent_key,
                },
            },
        )
        self.assertEqual(decided.status_code, 200)
        body = decided.get_json()
        self.assertEqual(body["outcome"], "saved")
        self.assertFalse(body["item"]["resume_display"])
        self.assertIn("privately", body["message"].lower())

    def test_source_purge_over_http_keeps_provenance_and_fences_late_work(self):
        client = self.client()
        created = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "A private note."},
        ).get_json()
        source_key = created["submission"]["source_keys"][0]
        purged = client.post(
            "/api/resume-intake/me/sources/purge",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "source_key": source_key},
        )
        self.assertEqual(purged.status_code, 200)
        body = purged.get_json()
        self.assertEqual(body["outcome"], "purged")
        self.assertTrue(body["provenance_retained"])
        self.assertFalse(body["source_resurrected"])
        snapshot = self.repository.load_owner("member-a")
        self.assertIsNone(snapshot["sources"][source_key]["text"])

    def test_foreign_source_is_a_neutral_not_found(self):
        client = self.client()
        created = self.submission(
            client, {"type": "add_submission", "request_id": str(uuid4()), "text": "A note."}
        ).get_json()
        app.config["PEERSLATE_DEV_USER_KEY"] = "member-b"
        other = self.client().post(
            "/api/resume-intake/me/sources/purge",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()),
                  "source_key": created["submission"]["source_keys"][0]},
        )
        self.assertEqual(other.status_code, 404)

    def test_organize_route_is_same_origin_guarded_and_unavailable_without_an_organizer(self):
        client = self.client()
        body = {"request_id": str(uuid4()), "source_key": str(uuid4()), "mode": "retry"}
        url = "/api/resume-intake/me/sources/organize"
        self.assertEqual(client.post(url, json=body).status_code, 403)
        refused = client.post(url, headers={"X-PeerSlate-Request": "same-origin"}, json=body)
        self.assertEqual(refused.status_code, 503)
        self.assertFalse(refused.get_json()["success"])

    def test_authority_fields_are_refused(self):
        response = self.submission(
            self.client(),
            {"type": "add_submission", "request_id": str(uuid4()),
             "text": "hi", "visitor_ai": True},
        )
        self.assertEqual(response.status_code, 400)

    def test_document_receipt_reports_processing_states_separately(self):
        client = self.client()
        payload = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()),
             "attachments": [{"client_key": "d1", "kind": "document",
                              "declared_content_type": "text/plain", "filename": "r.txt"}]},
            files={"d1": ("r.txt", b"Systems Engineer", "text/plain")},
        ).get_json()
        row = payload["results"][0]
        self.assertEqual(row["outcome"], "unresolved")
        self.assertEqual(row["kind"], "document")
        self.assertFalse(row["saved"])
        self.assertIn("document", row)
        self.assertTrue(row["document"]["readable_text"])

    def test_manual_editor_save_fences_pending_intake_references(self):
        client = self.client()
        # Create one private role through the composer.
        created = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role",
                           "values": {
                               "role_title": "Systems Engineer",
                               "employer_name": "Northrop Grumman",
                               "location_text": None, "summary": None,
                               "start_date": None, "end_date": None,
                               "date_precision": "unknown", "employment_type": None,
                               "current_role": False,
                           }}],
            },
        ).get_json()
        self.assertEqual(created["summary"]["saved"], 1)
        record_key = created["saved_items"][0]["record_key"]
        # A contradictory change to that same role becomes a pending proposal.
        pending = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r2", "record_type": "role",
                           "values": {
                               "role_title": "Systems Engineer",
                               "employer_name": "Example Corp",
                               "location_text": None, "summary": None,
                               "start_date": None, "end_date": None,
                               "date_precision": "unknown", "employment_type": None,
                               "current_role": False,
                           }}],
            },
        ).get_json()
        proposal_key = pending["proposals"][0]["proposal_key"]
        self.assertEqual(pending["proposals"][0]["target_key"], record_key)

        # A manual editor save of that record fences the pending proposal.
        with app.app_context():
            self.draft_service.commit(
                "member-a",
                {
                    "request_id": str(uuid4()),
                    "type": "save_item",
                    "record_key": record_key,
                    "record_type": "role",
                    "expected_content_token": self.catalog.get_item("member-a", record_key)["content_token"],
                    "expected_access_revision": self.catalog.get_item("member-a", record_key)["access_revision"],
                    "values": {"employer_name": "Northrop Grumman"},
                },
            )
        snapshot = self.repository.load_owner("member-a")
        self.assertEqual(snapshot["proposals"][proposal_key]["state"], "invalidated")
        decision = client.post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "proposal_key": proposal_key, "decision": "accept"},
        )
        self.assertEqual(decision.status_code, 409)
        self.assertTrue(decision.get_json()["input_preserved"])

    def test_workspace_response_never_exposes_raw_source_records(self):
        client = self.client()
        self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()),
             "text": "A private sentence about my career."},
        )
        body = client.get("/api/resume-intake/me").get_data(as_text=True)
        self.assertNotIn('"sources"', body)
        self.assertNotIn('"sha256"', body)
        self.assertNotIn("origin_client_key", body)

    def test_purge_redacts_retained_proposal_and_receipt_copies(self):
        client = self.client()
        created = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()),
             "text": "Confidential sentence that must not survive purge."},
        ).get_json()
        source_key = created["submission"]["source_keys"][0]
        proposal_key = created["proposals"][0]["proposal_key"]
        purged = client.post(
            "/api/resume-intake/me/sources/purge",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "source_key": source_key},
        )
        self.assertEqual(purged.status_code, 200)
        body = purged.get_json()
        self.assertEqual(body["outcome"], "purged")
        self.assertTrue(body["provenance_retained"])
        self.assertFalse(body["source_resurrected"])
        self.assertGreaterEqual(body["redacted_proposals"], 1)
        snapshot = self.repository.load_owner("member-a")
        proposal = snapshot["proposals"][proposal_key]
        self.assertIsNone(proposal["quote"])
        self.assertEqual(proposal["proposed_values"], {"redacted": True})
        # Historical provenance is retained without any resurrectable text.
        self.assertEqual(proposal["provenance"]["source_key"], source_key)
        blob = json.dumps(snapshot)
        self.assertNotIn("Confidential sentence", blob)

    def test_crafted_confirmed_values_are_a_400_not_a_server_error(self):
        client = self.client()
        created = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "A note."},
        ).get_json()
        response = client.post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "proposal_key": created["proposals"][0]["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"record_type": "skill", "name": "MBSE",
                                     "visitor_ai": True},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Traceback", response.get_data(as_text=True))

    def test_unknown_record_type_in_confirmed_values_is_a_closed_refusal(self):
        client = self.client()
        created = self.submission(
            client,
            {"type": "add_submission", "request_id": str(uuid4()), "text": "A note."},
        ).get_json()
        response = client.post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "proposal_key": created["proposals"][0]["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"record_type": "not_a_type", "name": "MBSE"},
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "reconciliation_required")


class PolicyBoundaryHttpTests(IntakeRoutesTestCase):
    """Privacy cleanup never waits on policy; canonical writes do."""

    def setUp(self):
        super().setUp()
        from services.resume_intake_policy import fixture_policy_for_tests

        self.fixture_service = ResumeIntakeService(
            repository=self.repository,
            draft_service=self.draft_service,
            policy=fixture_policy_for_tests(),
        )
        app.config["RESUME_INTAKE_SERVICE"] = self.fixture_service

    def _note(self):
        return self.submission(
            self.client(),
            {"type": "add_submission", "request_id": str(uuid4()),
             "text": "A private onboarding note."},
        ).get_json()

    def test_accept_needs_a_selected_policy_but_reject_does_not(self):
        created = self._note()
        proposal_key = created["proposals"][0]["proposal_key"]
        app.config.update(PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=False)
        accept = self.client().post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": {"record_type": "skill", "name": "MBSE"},
            },
        )
        self.assertEqual(accept.status_code, 503)
        self.assertEqual(accept.get_json()["code"], "policy_not_selected")
        reject = self.client().post(
            "/api/resume-intake/me/proposals/decision",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "proposal_key": proposal_key,
                  "decision": "reject"},
        )
        self.assertEqual(reject.status_code, 200)
        self.assertEqual(reject.get_json()["outcome"], "unresolved")

    def test_purge_is_not_policy_gated(self):
        created = self._note()
        source_key = created["submission"]["source_keys"][0]
        app.config.update(PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=False)
        purged = self.client().post(
            "/api/resume-intake/me/sources/purge",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "source_key": source_key},
        )
        self.assertEqual(purged.status_code, 200)
        self.assertEqual(purged.get_json()["outcome"], "purged")


class PolicyGateHttpTests(IntakeRoutesTestCase):
    def test_unselected_onboarding_policy_refuses_instead_of_using_fixtures(self):
        app.config.update(PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=False)
        self.service._policy = fixture_policy_for_tests()  # explicitly unselected policy stays refused
        response = self.submission(
            self.client(),
            {"type": "add_submission", "request_id": str(uuid4()), "text": "hello"},
        )
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["code"], "policy_not_selected")
        self.assertFalse(body["policy_selected"])
        self.assertEqual(self.repository.load_owner("member-a")["submissions"], {})


class GuideHttpTests(IntakeRoutesTestCase):
    def test_first_arrival_read_and_once_ack_use_real_owner_routes_without_provider_work(self):
        from unittest.mock import patch
        client = self.client()
        before = self.repository.load_owner("member-a")
        with (patch.object(self.repository, "save_owner", wraps=self.repository.save_owner) as save,
              patch.object(self.draft_service.repository, "save_owner", wraps=self.draft_service.repository.save_owner) as draft_save,
              patch.object(self.catalog, "put_item", wraps=self.catalog.put_item) as canonical_write,
              patch.object(self.service, "_interpreter", side_effect=AssertionError("No provider work from arrival")) as provider):
            response = client.get("/api/resume-intake/me/guide")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["first_arrival"]["eligible"])
            self.assertIn("no-store", response.headers["Cache-Control"])
            self.assertIn("private", response.headers["Cache-Control"])
            working_before = client.get("/api/resume-intake/me/guide/working-set").get_json()
            save.assert_not_called()
            self.assertEqual(before, self.repository.load_owner("member-a"))
            payload = {"request_id": str(uuid4()), "first_arrival_action": "shown"}
            first = client.post("/api/resume-intake/me/guide/status",
                headers={"X-PeerSlate-Request": "same-origin"}, json=payload)
            self.assertEqual(first.status_code, 200)
            self.assertTrue(first.get_json()["show_now"])
            replay = client.post("/api/resume-intake/me/guide/status",
                headers={"X-PeerSlate-Request": "same-origin"}, json=payload)
            self.assertEqual(replay.status_code, 200)
            self.assertTrue(replay.get_json()["replayed"])
            self.assertFalse(replay.get_json()["show_now"])
            self.assertEqual(save.call_count, 1)
            draft_save.assert_not_called()
            canonical_write.assert_not_called()
            provider.assert_not_called()
        after = client.get("/api/resume-intake/me/guide/working-set").get_json()
        self.assertFalse(after["first_arrival"]["eligible"])
        self.assertTrue(after["first_arrival"]["shown"])
        self.assertEqual(after["counts"]["saved"], 0)
        self.assertEqual(after["working_set_token"], working_before["working_set_token"])
        self.assertEqual(after["draft_version"], working_before["draft_version"])
        self.assertEqual(self.received_documents, [])
        self.assertEqual(self.transcriber.calls, [])

    def test_first_arrival_unreadable_catalog_stays_unknown_and_working_set_unavailable(self):
        from unittest.mock import patch
        from services.resume_draft_repository import CanonicalReadUnavailable
        with patch.object(self.catalog, "list_items", side_effect=CanonicalReadUnavailable()):
            guide = self.client().get("/api/resume-intake/me/guide")
            self.assertEqual(guide.status_code, 200)
            self.assertIsNone(guide.get_json()["first_arrival"]["eligible"])
            working = self.client().get("/api/resume-intake/me/guide/working-set")
            self.assertEqual(working.status_code, 503)
            self.assertEqual(working.get_json()["load_state"], "unavailable")

    def test_first_arrival_rejects_client_owner_and_mixed_status_selectors(self):
        for extra in ({"owner_user_key": "member-b"}, {"status": "completed"}, {"first_arrival_action": {}}):
            with self.subTest(extra=extra):
                response = self.client().post("/api/resume-intake/me/guide/status",
                    headers={"X-PeerSlate-Request": "same-origin"},
                    json={"request_id": str(uuid4()), "first_arrival_action": "shown", **extra})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client().get("/api/resume-intake/me/guide?owner_user_key=member-b").status_code, 400)
        self.assertEqual(self.repository.load_owner("member-a")["guide"], {})
        self.assertEqual(self.repository.load_owner("member-b")["guide"], {})

    def test_guide_read_does_not_start_processing_or_invent_a_new_member(self):
        client = self.client()
        response = client.get("/api/resume-intake/me/guide")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["load_state"], "loaded")
        self.assertEqual(body["status"], "not_started")
        self.assertFalse(body["member_choice"])
        self.assertTrue(body["read_does_not_start_processing"])
        self.assertEqual(self.repository.load_owner("member-a")["jobs"], {})

    def test_completion_is_a_member_choice(self):
        client = self.client()
        response = client.post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"status": "completed"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "completed")
        self.assertTrue(body["member_choice"])
        self.assertTrue(body["completion_is_member_action"])

    def test_same_guide_request_replays_and_changed_status_conflicts(self):
        request_id = str(uuid4())
        first = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": request_id, "status": "paused"},
        )
        replay = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": request_id, "status": "paused"},
        )
        conflict = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": request_id, "status": "completed"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.get_json()["replayed"])
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.get_json()["replayed"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["code"], "idempotency_conflict")

    def test_guide_replay_keeps_original_receipt_and_labels_current_state(self):
        completed_request = str(uuid4())
        completed = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": completed_request, "status": "completed"},
        )
        self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": str(uuid4()), "status": "paused"},
        )
        replay = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"request_id": completed_request, "status": "completed"},
        )

        self.assertEqual(completed.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        body = replay.get_json()
        self.assertTrue(body["replayed"])
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["receipt"]["status"], "completed")
        self.assertEqual(body["current_state"]["status"], "paused")
        self.assertEqual(body["request_id"], completed_request)

    def test_invalid_guide_status_is_refused(self):
        response = self.client().post(
            "/api/resume-intake/me/guide/status",
            headers={"X-PeerSlate-Request": "same-origin"},
            json={"status": "not_started"},
        )
        self.assertEqual(response.status_code, 400)

    def test_read_failure_is_unavailable_not_an_empty_member(self):
        class DownRepository(InMemoryResumeIntakeRepository):
            persistence_label = "sql_proposed_unapplied"

            def load_owner(self, owner):
                raise ResumeIntakeStoreUnavailable()

            def save_owner(self, owner, snapshot, command=None):
                raise ResumeIntakeStoreUnavailable()

        app.config["RESUME_GUIDE_SERVICE"] = ResumeGuideService(repository=DownRepository())
        response = self.client().get("/api/resume-intake/me/guide")
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["load_state"], "unavailable")
        self.assertIsNone(body["status"])
        self.assertTrue(body["read_error_is_not_new_member"])

    def test_unavailable_store_preserves_the_member_input(self):
        class DownRepository(InMemoryResumeIntakeRepository):
            persistence_label = "sql_proposed_unapplied"

            def save_owner(self, owner, snapshot, command=None):
                raise ResumeIntakeStoreUnavailable()

        down = ResumeIntakeService(
            repository=DownRepository(),
            draft_service=self.draft_service,
            policy=selected_policy_for_tests(),
        )
        app.config["RESUME_INTAKE_SERVICE"] = down
        response = self.submission(
            self.client(),
            {"type": "add_submission", "request_id": str(uuid4()), "text": "Do not lose this"},
        )
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertTrue(body["input_preserved"])
        self.assertEqual(body["proposed_values"]["text"], "Do not lose this")
        self.assertNotIn("Traceback", response.get_data(as_text=True))


class GuideWorkingSetHttpTests(IntakeRoutesTestCase):
    def seed(self):
        return self.service.submit("member-a",{"type":"add_submission","request_id":str(uuid4()),
            "text":"Fictional member-a source"})

    def test_working_set_read_is_private_read_only_and_does_not_extract(self):
        from unittest.mock import patch
        self.seed()
        before = self.repository.load_owner("member-a")
        with patch.object(self.service,"_canonical_items",side_effect=AssertionError("Do not perform a second catalog read")):
            response = self.client().get("/api/resume-intake/me/guide/working-set")
        self.assertEqual(response.status_code,200,response.get_data(as_text=True)[:512])
        result = response.get_json()
        self.assertTrue(result["success"])
        self.assertEqual(result["counts"]["waiting"],1)
        self.assertIn("no-store",response.headers["Cache-Control"])
        self.assertEqual(self.repository.load_owner("member-a"),before)

    def test_working_set_never_uses_a_client_owner_selector(self):
        self.seed()
        app.config["PEERSLATE_DEV_USER_KEY"] = "member-b"
        client = self.client()
        response = client.get("/api/resume-intake/me/guide/working-set?owner_user_key=member-a")
        self.assertEqual(response.status_code,400)
        own = client.get("/api/resume-intake/me/guide/working-set")
        self.assertEqual(own.status_code,200)
        self.assertEqual(own.get_json()["counts"]["waiting"],0)
        self.assertNotIn("Fictional member-a source",own.get_data(as_text=True))

    def test_working_set_outage_is_unavailable_not_new_member(self):
        from unittest.mock import patch
        with patch.object(self.repository,"load_owner",side_effect=ResumeIntakeStoreUnavailable("fictional outage")):
            response = self.client().get("/api/resume-intake/me/guide/working-set")
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.get_json()["load_state"],"unavailable")
        self.assertNotIn("counts",response.get_json())

    def test_working_set_stays_behind_existing_feature_gate(self):
        app.config["PEERSLATE_RESUME_INTAKE_ENABLED"] = False
        self.assertEqual(self.client().get("/api/resume-intake/me/guide/working-set").status_code,404)

    def test_privacy_state_reads_the_current_owner_publication_without_publishing(self):
        from unittest.mock import Mock,patch
        publication = Mock()
        publication.read_display_selection_provenance.return_value = None
        publication.read_publication_basis_for_owner.return_value = {"read_state":"current", "publication_state":"published",
            "change_count":0,"membership":{"display":[],"visitor_ai":[]},"items":[],"candidate":{"draft_revision":0}}
        with patch.dict(app.config,{"RESUME_PUBLICATION_SERVICE":publication}):
            initial=self.client().get("/api/resume-intake/me/guide/working-set").get_json()
            self.assertEqual(initial["publication_state"],"published")
            self.seed()
            self.assertEqual(self.client().get("/api/resume-intake/me/guide/working-set").get_json()["publication_state"],"published")
            publication.read_publication_basis_for_owner.side_effect = RuntimeError("fictional publication read outage")
            before_outage=self.client().get("/api/resume-intake/me/guide/working-set").get_json()
            self.assertEqual(before_outage["publication_state"],"unknown")
            publication.read_publication_basis_for_owner.side_effect = None
            restored=self.client().get("/api/resume-intake/me/guide/working-set").get_json()
            self.assertNotEqual(restored["working_set_token"],before_outage["working_set_token"])
        publication.read_publication_basis_for_owner.assert_called_with("member-a",{"entries":[]})
        publication.commit.assert_not_called()


class DraftHttpTests(IntakeRoutesTestCase):
    HEADERS = {"X-PeerSlate-Request": "same-origin"}

    def test_draft_round_trip_recovers_across_requests(self):
        client = self.client()
        empty = client.get("/api/resume-intake/me/draft")
        self.assertEqual(empty.status_code, 200)
        self.assertIsNone(empty.get_json()["draft"])
        saved = client.put(
            "/api/resume-intake/me/draft",
            headers=self.HEADERS,
            json={"request_id": str(uuid4()), "text": "Systems Engineer notes"},
        )
        self.assertEqual(saved.status_code, 200)
        body = saved.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["draft"]["version"], 1)
        # A later request recovers the same draft: cross-device recovery.
        recovered = client.get("/api/resume-intake/me/draft").get_json()
        self.assertEqual(recovered["draft"]["text"], "Systems Engineer notes")
        discarded = client.delete("/api/resume-intake/me/draft", headers=self.HEADERS)
        self.assertTrue(discarded.get_json()["discarded"])
        self.assertIsNone(client.get("/api/resume-intake/me/draft").get_json()["draft"])

    def test_draft_conflict_returns_409_with_both_versions(self):
        client = self.client()
        client.put(
            "/api/resume-intake/me/draft",
            headers=self.HEADERS,
            json={"request_id": str(uuid4()), "text": "Device one"},
        )
        conflict = client.put(
            "/api/resume-intake/me/draft",
            headers=self.HEADERS,
            json={"request_id": str(uuid4()), "text": "Device two"},
        )
        self.assertEqual(conflict.status_code, 409)
        body = conflict.get_json()
        self.assertEqual(body["code"], "draft_conflict")
        self.assertTrue(body["input_preserved"])
        self.assertEqual(body["proposed_values"]["text"], "Device two")
        self.assertEqual(body["conflicts"][0]["server_version"], 1)

    def test_draft_write_needs_same_origin_header(self):
        response = self.client().put(
            "/api/resume-intake/me/draft",
            json={"request_id": str(uuid4()), "text": "hi"},
        )
        self.assertEqual(response.status_code, 403)


class KeepSeparateHttpTests(IntakeRoutesTestCase):
    def test_structured_duplicate_then_keep_as_separate_saves(self):
        client = self.client()
        values = {
            "role_title": "Route Duplicate",
            "employer_name": "Northwind",
        }
        first = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "r1", "record_type": "role", "values": values,
                }],
            },
        )
        self.assertEqual(first.get_json()["summary"]["saved"], 1)
        duplicate = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "r2", "record_type": "role", "values": values,
                }],
            },
        )
        body = duplicate.get_json()
        self.assertEqual(body["outcome"], "duplicate")
        keep = body["results"][0]["keep_separate"]
        self.assertEqual(keep["values"], values)
        separate = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": keep["client_key"],
                    "record_type": keep["record_type"],
                    "values": keep["values"],
                    "explicit_clears": keep.get("explicit_clears") or [],
                    "as_separate": True,
                }],
            },
        )
        self.assertEqual(separate.get_json()["summary"]["saved"], 1)


class ExtractedKeepSeparateHttpTests(IntakeRoutesTestCase):
    def test_extracted_keep_separate_over_http(self):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter

        fake = DeterministicFakeExtractionAdapter()
        service = ResumeIntakeService(
            repository=self.repository,
            draft_service=self.draft_service,
            document_adapter=ResumeDocumentAdapter(),
            transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
            policy=selected_policy_for_tests(),
            extraction_adapter=fake,
            matching_exclusions=lambda owner: set(),
        )
        app.config["RESUME_INTAKE_SERVICE"] = service
        client = self.client()
        values = {
            "role_title": "Route Duplicate",
            "employer_name": "Northwind",
        }
        first = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "r1", "record_type": "role", "values": values,
                }],
            },
        )
        record_key = first.get_json()["saved_items"][0]["record_key"]
        text = "Route Duplicate at Northwind"
        fake.scripted.append({
            "record_type": "role",
            "values": dict(values),
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        duplicate = self.submission(
            client,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": text,
            },
        )
        body = duplicate.get_json()
        self.assertEqual(body["outcome"], "duplicate")
        keep = body["results"][0]["keep_separate_actions"][0]
        self.assertTrue(keep["override_key"])
        self.assertNotIn("extracted_fields", keep)
        separate = self.submission(
            client,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(separate.get_json()["summary"]["saved"], 1)
        replay = self.submission(
            client,
            {
                "type": "keep_extracted_separate",
                "request_id": separate.get_json()["request_id"],
                "override_key": keep["override_key"],
            },
        )
        self.assertTrue(replay.get_json()["replayed"])
        source_key = body["submission"]["source_keys"][0]
        canonical_count = len(service._canonical_items("member-a"))
        service.purge_source(
            "member-a",
            {"request_id": str(uuid4()), "source_key": source_key},
        )
        self.assertEqual(len(service._canonical_items("member-a")), canonical_count)
        stale = self.submission(
            client,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["error_code"], "source_purged")
        app.config.update(PEERSLATE_DEV_USER_KEY="member-b")
        denied = self.submission(
            client,
            {
                "type": "keep_extracted_separate",
                "request_id": str(uuid4()),
                "override_key": keep["override_key"],
            },
        )
        self.assertEqual(denied.status_code, 404)


if __name__ == "__main__":
    unittest.main()


# Selected model/private assistance integration regressions; fixtures only.
class BoundedWorkerPoolHttpTests(unittest.TestCase):
    """B2b: same-request duplicates give their worker back on a fixed pool.

    The local private sites serve from a fixed pool of worker threads
    (waitress, four). While one submit holds its fake provider, duplicates
    of that exact request must return the existing retryable intake conflict
    instead of holding every worker, so an unrelated request still completes.
    """

    WORKERS = 4

    def setUp(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from werkzeug.serving import BaseWSGIServer
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter

        import app as app_module
        self.original = {key: app.config.get(key) for key in CONFIG_KEYS}
        # Rate limits are not under test here; keep this test's requests from
        # spending the shared in-memory quota other tests rely on.
        limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False
        self.addCleanup(setattr, app_module.limiter, 'enabled', limiter_was_enabled)
        self.entered, self.released = threading.Event(), threading.Event()
        self.addCleanup(self.released.set)
        self.adapter = DeterministicFakeExtractionAdapter([{'record_type': 'skill',
            'values': {'name': 'Radio restoration'}, 'quote': 'I restore fictional radios.',
            'outcome': 'new', 'confidence': 'certain'}])
        provider, dispatches = self.adapter._provider, []
        self.dispatches = dispatches

        def held(request, **kwargs):
            dispatches.append(1)
            self.entered.set()
            if not self.released.wait(30):
                raise AssertionError('The bounded fake provider was never released')
            return provider(request, **kwargs)

        self.adapter._provider = held
        catalog = InMemoryCanonicalCatalog()
        repository = InMemoryResumeIntakeRepository()
        self.service = ResumeIntakeService(repository=repository,
            draft_service=ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog),
            policy=selected_policy_for_tests(), extraction_adapter=self.adapter)
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY='member-a',
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_RESUME_INTAKE_ENABLED=True,
            PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=True, RESUME_INTAKE_SERVICE=self.service,
            RESUME_GUIDE_SERVICE=ResumeGuideService(repository=repository))
        self.addCleanup(app.config.update, self.original)

        class BoundedPoolServer(BaseWSGIServer):
            """A fixed worker pool, like waitress's: no thread per request."""

            def __init__(server, *args, workers, **kwargs):
                super().__init__(*args, **kwargs)
                server.pool = ThreadPoolExecutor(max_workers=workers)

            def process_request(server, request, client_address):
                server.pool.submit(server._handle, request, client_address)

            def _handle(server, request, client_address):
                try:
                    server.finish_request(request, client_address)
                except Exception:
                    server.handle_error(request, client_address)
                finally:
                    server.shutdown_request(request)

        self.server = BoundedPoolServer('127.0.0.1', 0, app, workers=self.WORKERS)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.pool.shutdown, wait=False)
        self.addCleanup(self.server.shutdown)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def _call(self, path, *, payload=None, timeout):
        import time
        import urllib.error
        import urllib.request
        data, headers = None, {}
        if payload is not None:
            boundary = 'b2bprobe' + uuid4().hex
            data = (f'--{boundary}\r\nContent-Disposition: form-data; name="request"\r\n\r\n'
                    f'{json.dumps(payload)}\r\n--{boundary}--\r\n').encode()
            headers = {'Content-Type': 'multipart/form-data; boundary=' + boundary,
                       'X-PeerSlate-Request': 'same-origin'}
        start = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(self.url + path, data=data, headers=headers),
                                        timeout=timeout) as response:
                return response.status, json.loads(response.read() or b'{}'), time.monotonic() - start
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b'{}'), time.monotonic() - start

    def test_duplicates_of_a_held_request_return_busy_and_an_unrelated_request_completes(self):
        import threading
        payload = {'request_id': str(uuid4()), 'text': 'I restore fictional radios.'}
        results = {}

        def run(name, path, body=None):
            try:
                results[name] = self._call(path, payload=body, timeout=20)
            except Exception as error:  # a timed-out client is a starved worker pool
                results[name] = ('error', repr(error), None)

        holder = threading.Thread(target=run, args=('holder', '/api/resume-intake/me/submissions', payload),
                                  daemon=True)
        holder.start()
        self.assertTrue(self.entered.wait(10), 'The real submit route must reach its held fake provider')
        duplicates = [threading.Thread(target=run, args=(f'dup{i}', '/api/resume-intake/me/submissions', payload),
                                       daemon=True) for i in range(self.WORKERS)]
        for thread in duplicates:
            thread.start()
        try:
            unrelated = self._call('/api/resume-intake/me', timeout=8)
        finally:
            for thread in duplicates:
                thread.join(10)
            self.released.set()
            holder.join(10)
        self.assertEqual(unrelated[0], 200, 'An unrelated request must complete while duplicates wait')
        for i in range(self.WORKERS):
            status, body, _seconds = results[f'dup{i}']
            # The retryable 503 shape today's client keeps the request id for.
            self.assertEqual(status, 503, results[f'dup{i}'])
            self.assertEqual(body['code'], 'request_in_progress')
            self.assertTrue(body['retryable'])
            self.assertTrue(body['input_preserved'])
            self.assertEqual(body['proposed_values']['text'], 'I restore fictional radios.')
            self.assertEqual(body['request_id'], payload['request_id'])
        self.assertEqual(results['holder'][0], 200, results['holder'])
        replay = self._call('/api/resume-intake/me/submissions', payload=payload, timeout=10)
        self.assertEqual(replay[0], 200)
        self.assertTrue(replay[1]['replayed'])
        self.assertEqual(len(self.dispatches), 1)


class RouteBoundaryTests(unittest.TestCase):
    def test_too_large_context_is_explained_in_plain_words_before_any_model_call(self):
        from tests.test_resume_onboarding_conversation import ConversationTests
        from unittest.mock import patch
        fixture = ConversationTests(); fixture.setUp(); fixture.owner = 'fiction-owner'
        fixture.assistance.limits['maximum_input_bytes'] = 2000
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'] = fixture.assistance
        command = fixture.command('Engineer at Example Labs.')
        with patch.object(self.routes, '_service', return_value=fixture.intake):
            response = self.client.post('/api/resume-interview/me/turn', json=command,
                headers={'X-PeerSlate-Request': 'same-origin'})
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body['code'], 'input_too_large')
        self.assertIn('too much to read at once', body['message'])
        self.assertIn('Nothing was changed', body['message'])
        self.assertNotIn('could not complete', body['message'])
        self.assertEqual(fixture.calls, [])

    def test_actual_rejected_conversation_returns_only_closed_private_diagnostic(self):
        from tests.test_resume_onboarding_conversation import ConversationTests, operation
        from unittest.mock import patch
        fixture = ConversationTests(); fixture.setUp(); fixture.owner = 'fiction-owner'
        fixture.behavior = lambda ctx: {'response':'MODEL_PRIVATE_MARKER','next_question':'',
            'operations':[operation(ctx, op='add_content', values={'PRIVATE_FIELD_MARKER':'MODEL_PRIVATE_MARKER'})]}
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'] = fixture.assistance
        command = fixture.command('Engineer at Example Labs. OWNER_PRIVATE_MARKER.')
        with patch.object(self.routes, '_service', return_value=fixture.intake):
            response = self.client.post('/api/resume-interview/me/turn', json=command,
                headers={'X-PeerSlate-Request':'same-origin'})
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body['code'], 'invalid_output')
        self.assertIn('I could not turn that message into résumé details this time.', body['message'])
        self.assertIn('Nothing was changed', body['message'])
        self.assertEqual(body['diagnostic'], {'schema_version':1,'stage':'operation_contract','reason':'value_field'})
        self.assertNotIn('PRIVATE_MARKER', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        meta = fixture.intake.get_workspace(fixture.owner)['source_accounting'][0]
        self.assertEqual(meta['request_id'], command['request_id'])
        self.assertEqual(meta['failure_diagnostic'], body['diagnostic'])
        self.assertEqual(meta['text'], command['statement'])
        self.assertEqual(len(fixture.calls), 1)

    def test_b3a_a_busy_turn_is_the_retryable_503_with_its_request_id_and_words(self):
        from tests.test_resume_onboarding_conversation import ConversationTests
        from services.resume_intake_service import ResumeIntakeBusyError
        from unittest.mock import patch
        fixture = ConversationTests(); fixture.setUp()
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'] = fixture.assistance
        command = fixture.command('I restore fictional radios.')
        busy = ResumeIntakeBusyError(command['request_id'], proposed={'statement': command['statement']})
        with patch.object(self.routes, '_service', return_value=fixture.intake),                 patch.object(fixture.intake, 'converse', side_effect=busy):
            response = self.client.post('/api/resume-interview/me/turn', json=command,
                headers={'X-PeerSlate-Request': 'same-origin'})
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual((body['code'], body['retryable'], body['request_id']),
                         ('request_in_progress', True, command['request_id']))
        self.assertEqual((body['input_preserved'], body['proposed_values']), (True, {'statement': command['statement']}))
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        self.assertEqual(fixture.calls, [])

    def test_b3a_a_reused_turn_id_with_changed_words_is_a_409_idempotency_conflict(self):
        from tests.test_resume_onboarding_conversation import ConversationTests
        from unittest.mock import patch
        fixture = ConversationTests(); fixture.setUp()
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'] = fixture.assistance
        command = fixture.command('I restore fictional radios.')
        with patch.object(self.routes, '_service', return_value=fixture.intake):
            first = self.client.post('/api/resume-interview/me/turn', json=command,
                headers={'X-PeerSlate-Request': 'same-origin'})
            self.assertEqual(first.status_code, 200)
            response = self.client.post('/api/resume-interview/me/turn', json={**command, 'statement': 'Other words.'},
                headers={'X-PeerSlate-Request': 'same-origin'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['code'], 'idempotency_conflict')
        self.assertEqual(len(fixture.calls), 1)

    def test_untrusted_diagnostic_attributes_do_not_escape_other_assistance_errors(self):
        from services.resume_intake_runtime import SynthesisError
        error = SynthesisError('invalid_output')
        error.conversation_diagnostic = {'schema_version':1,'stage':'operation_contract',
            'reason':'PRIVATE_MARKER','raw_response':'PRIVATE_MARKER'}
        self.service.generate.side_effect = error
        response = self.client.post('/api/resume-synthesis/me/proposals',
            json={'request_id':str(uuid4())}, headers={'X-PeerSlate-Request':'same-origin'})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('diagnostic', response.get_json())
        self.assertNotIn('PRIVATE_MARKER', response.get_data(as_text=True))

    def test_actual_conversation_timeout_is_unavailable_and_same_key_never_redispatches(self):
        from tests.test_resume_onboarding_conversation import ConversationTests
        from unittest.mock import patch
        fixture=ConversationTests();fixture.setUp()
        fixture.behavior=lambda ctx: (_ for _ in ()).throw(TimeoutError('synthetic private provider timeout'))
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE']=fixture.assistance
        payload=fixture.command('What could I add?')
        with patch.object(self.routes,'_service',return_value=fixture.intake):
            for attempt in range(2):
                response=self.client.post('/api/resume-interview/me/turn',json=payload,
                    headers={'X-PeerSlate-Request':'same-origin'})
                self.assertEqual(response.status_code,503,response.get_json())
                self.assertEqual(response.get_json()['code'],'unavailable')
        self.assertEqual(len(fixture.calls),1)
        self.assertEqual(fixture.intake.draft_service.catalog.list_items('fiction-owner'),[])

    def test_correction_binds_owner_pending_source_and_refuses_a_foreign_or_changed_proposal(self):
        from unittest.mock import Mock, patch
        proposal={'proposal_key':str(uuid4()),'state':'pending','record_type':'role',
            'quote':'Owner source','proposed_values':{'role_title':'Designer'}}
        intake=Mock();intake.get_workspace.return_value={'pending_proposals':[proposal]}
        payload={'request_id':str(uuid4()),'expected_draft_version':7,
            'statement':'The start year was 2021.','proposal_key':proposal['proposal_key']}
        self.service.interview.return_value={'saved':False,'publishes':False,'candidates':[]}
        with patch.object(self.routes,'_service',return_value=intake):
            response=self.client.post('/api/resume-interview/me/turn',json=payload,
                headers={'X-PeerSlate-Request':'same-origin'})
            self.assertEqual(response.status_code,200)
            self.service.interview.assert_called_once_with('fiction-owner',
                {k:v for k,v in payload.items() if k!='proposal_key'},review_proposal=proposal)
            self.assertTrue(all(call.args==('fiction-owner',) for call in intake.get_workspace.call_args_list))
            self.service.interview.reset_mock()
            intake.get_workspace.return_value={'pending_proposals':[]}
            response=self.client.post('/api/resume-interview/me/turn',json=payload,
                headers={'X-PeerSlate-Request':'same-origin'})
            self.assertEqual(response.status_code,404);self.service.interview.assert_not_called()
            intake.get_workspace.side_effect=[{'pending_proposals':[proposal]},
                {'pending_proposals':[{**proposal,'state':'accepted'}]}]
            response=self.client.post('/api/resume-interview/me/turn',json=payload,
                headers={'X-PeerSlate-Request':'same-origin'})
            self.assertEqual(response.status_code,409)

    def test_private_flag_off_precedes_cross_origin_and_identity(self):
        from unittest.mock import patch
        self.app.config['PEERSLATE_RESUME_SYNTHESIS_ENABLED'] = False
        with patch.object(self.routes, '_identity_or_not_found') as identity:
            result = self.client.post('/api/resume-synthesis/me/proposals', json={},
                                      headers={'Origin': 'https://other.invalid'})
            self.assertEqual(result.status_code, 404)
            identity.assert_not_called()
        self.service.generate.assert_not_called()

    def setUp(self):
        from flask import Flask
        import resume_intake_routes
        from unittest.mock import Mock, patch
        from types import SimpleNamespace
        self.routes = resume_intake_routes
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, PEERSLATE_RESUME_INTAKE_ENABLED=True,
            PEERSLATE_RESUME_EDITOR_ENABLED=True, PEERSLATE_RESUME_SYNTHESIS_ENABLED=True,
            PEERSLATE_RESUME_INTERVIEW_ENABLED=True)
        self.service = Mock()
        self.app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'] = self.service
        self.app.register_blueprint(resume_intake_routes.resume_intake)
        self.client = self.app.test_client()
        self.identity = patch.object(resume_intake_routes, '_identity_or_not_found',
                                      return_value=SimpleNamespace(user_key='fiction-owner'))
        self.identity.start()
        self.addCleanup(self.identity.stop)

    def test_off_same_origin_and_private_headers(self):
        self.app.config['PEERSLATE_RESUME_SYNTHESIS_ENABLED'] = False
        result = self.client.post('/api/resume-synthesis/me/proposals', json={},
                                  headers={'X-PeerSlate-Request': 'same-origin'})
        self.assertEqual(result.status_code, 404)
        self.service.generate.assert_not_called()
        self.app.config['PEERSLATE_RESUME_SYNTHESIS_ENABLED'] = True
        self.assertEqual(self.client.post('/api/resume-synthesis/me/proposals', json={}).status_code, 403)
        self.service.generate.return_value = {'state': 'proposal', 'saved': False, 'publishes': False}
        result = self.client.post('/api/resume-synthesis/me/proposals', json={'request_id': str(uuid4())},
                                  headers={'X-PeerSlate-Request': 'same-origin'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers['Cache-Control'], 'private, no-store')
        self.assertEqual(result.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.service.generate.call_args.args[0], 'fiction-owner')

    def test_duplicate_keys_and_overlimit_body_refuse_before_service(self):
        for data, expected in [(b'{"request_id":"a","request_id":"b"}', 400), (b' ' * 100001, 413)]:
            response = self.client.post('/api/resume-synthesis/me/proposals', data=data,
                content_type='application/json', headers={'X-PeerSlate-Request': 'same-origin'})
            self.assertEqual(response.status_code, expected)
        self.service.generate.assert_not_called()


from tests.test_resume_intake_browser import (
    CHROME_EXECUTABLE, sync_playwright, install_intake_runtime_fixtures, start_browser,
)


@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
    'Playwright and Chrome required for typed candidate click-to-save proof')
class TypedExtractionReviewBrowserTests(unittest.TestCase):
    """Actual UI and Flask save; deterministic extraction, never a model call."""

    @classmethod
    def setUpClass(cls):
        install_intake_runtime_fixtures(cls)
        start_browser(cls)

    def test_private_preview_long_paragraph_wraps_without_changing_text_or_saving(self):
        from unittest.mock import Mock, patch
        text = ('Independent Projects\n\n' +
            'An independent ETL pilot retained the documented limitations and source attribution. ' * 35 +
            '\n\n' + 'UnbrokenFixtureReference' * 35)
        service = Mock()
        service.generate.return_value = {'state': 'proposal', 'saved': False, 'publishes': False,
            'proof': 'display-fixture-only', 'proposal': {'resume_text': text, 'uncertainties': []}}
        owner = 'private-preview-wrap-browser'
        with patch.dict(app.config, {'PEERSLATE_RESUME_SYNTHESIS_ENABLED': True,
                'RESUME_PRIVATE_ASSISTANCE_SERVICE': service, 'PEERSLATE_DEV_USER_KEY': owner}):
            for width in (1440, 390):
                with self.subTest(viewport_width=width):
                    context = self.browser.new_context(viewport={'width': width, 'height': 1000})
                    try:
                        page = context.new_page()
                        page.route('https://fonts.**', lambda route: route.abort())
                        page.goto(self.base_url + '/app/resume')
                        guide_hide = page.locator('#resume-intake-hide')
                        if guide_hide.is_visible():
                            guide_hide.click()
                        page.locator('#resume-synthesis-task').fill('Preview the independent contribution.')
                        page.locator('#resume-synthesis-form button[type="submit"]').click()
                        output = page.locator('#resume-synthesis-text')
                        output.wait_for(state='visible')
                        self.assertEqual(output.text_content(), text)
                        layout = output.evaluate('''element => {
                            const box = element.getBoundingClientRect();
                            const style = getComputedStyle(element);
                            return {client: element.clientWidth, scroll: element.scrollWidth,
                                right: box.right, viewport: innerWidth, height: box.height,
                                lineHeight: parseFloat(style.lineHeight), whiteSpace: style.whiteSpace};
                        }''')
                        self.assertEqual(layout['whiteSpace'], 'pre-wrap')
                        self.assertLessEqual(layout['scroll'], layout['client'] + 1)
                        self.assertLessEqual(layout['right'], layout['viewport'] + 1)
                        self.assertGreater(layout['height'], layout['lineHeight'] * 6)
                        self.assertTrue(page.locator('#resume-synthesis-confirm').is_disabled())
                        self.assertEqual(self.catalog.list_items(owner), [])
                        service.confirm.assert_not_called()
                    finally:
                        context.close()
        self.assertEqual(service.generate.call_count, 2)

    def test_reviewed_typed_role_and_education_preserve_values_on_save_and_reload(self):
        from services.my_data_extraction_adapter import MyDataExtractionAdapter, EXTRACTION_VALUE_FIELDS
        text = ('Riley was a Data Support Intern at Example Orchard Cooperative from June through August 2025. '
                'Riley cleaned 240 inventory rows and wrote a short handoff guide. No efficiency result is established. '
                'Riley completed a Bachelor of Science in Information Systems at Example Lake College in May 2026.')
        role_quote, education_quote = text.rsplit('Riley completed', 1)
        education_quote = 'Riley completed' + education_quote
        values = {
            'role': {'role_title': 'Data Support Intern', 'employer_name': 'Example Orchard Cooperative',
                'summary': 'Cleaned 240 inventory rows and wrote a handoff guide. No efficiency result is established.',
                'start_date': '2025-06-01', 'end_date': '2025-08-01', 'date_precision': 'month',
                'current_role': False, 'employment_type': 'Internship'},
            'education': {'title': 'Bachelor of Science in Information Systems',
                'institution_name': 'Example Lake College', 'degree_name': 'Bachelor of Science',
                'field_of_study': 'Information Systems', 'education_status': 'completed',
                'end_date': '2026-05-01', 'date_precision': 'month'},
        }
        def extract(*args, **kwargs):
            return {'candidates': [{'record_type': kind,
                'values': {field: values[kind].get(field) for field in EXTRACTION_VALUE_FIELDS[kind]},
                'quote': quote, 'outcome': 'new', 'match_reference': None, 'confidence': 'certain'}
                for kind, quote in [('role', role_quote), ('education', education_quote)]]}
        self.intake_service._extraction_adapter = MyDataExtractionAdapter(provider=extract)
        owner = 'typed-extraction-review-browser'
        app.config['PEERSLATE_DEV_USER_KEY'] = owner
        context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        page.route('https://fonts.**', lambda route: route.abort())
        confirmations = []
        page.on('request', lambda request: confirmations.append(request.post_data_json)
            if request.url.endswith('/api/resume-intake/me/proposals/decision') else None)
        page.goto(self.base_url + '/app/resume')
        page.locator('#resume-intake').wait_for(state='visible')
        if page.locator('#resume-intake-start-type').is_visible():
            page.locator('#resume-intake-start-type').click()
        page.locator('#resume-intake-text').fill(text)
        page.locator('#resume-intake-add').click()
        proposals = page.locator('#resume-intake-proposals > li:not(.resume-intake__hint)')
        proposals.first.wait_for()
        self.assertEqual(proposals.count(), 1)
        self.assertIn('2 suggestions', page.locator('#resume-intake-review-position').inner_text())
        self.assertEqual(self.catalog.list_items(owner), [])  # Review is not a canonical save.
        for kind in ('role', 'education'):
            proposal = proposals.first
            self.assertEqual(proposal.get_by_role('combobox', name='Save this as', exact=True).count(), 0)
            proposal.get_by_role('button', name='Confirm details', exact=True).click()
            if kind == 'role':
                page.locator('#resume-intake-review-position').get_by_text('One suggestion to review', exact=False).wait_for()
            else:
                page.locator('#resume-intake-next:visible').wait_for()
            confirmed = confirmations[-1]['confirmed_values']
            self.assertNotIn('record_type', confirmed)
            page.locator('#resume-editor-lists h3').filter(has_text=values[kind].get('role_title') or values[kind]['title']).wait_for()
            for field, value in values[kind].items():
                self.assertEqual(confirmed[field], 'internship' if field == 'employment_type' else value)
        page.reload()
        rows = self.draft_service.get_workspace(owner)['items']
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertFalse(row['resume_display'])
            self.assertFalse(row['visitor_ai'])
            for field, value in values[row['record_type']].items():
                self.assertEqual(row['values'][field], 'internship' if field == 'employment_type' else value)

    def _proposal_page(self, owner, kind, values, text):
        from services.my_data_extraction_adapter import MyDataExtractionAdapter, EXTRACTION_VALUE_FIELDS
        self.intake_service._extraction_adapter = MyDataExtractionAdapter(provider=lambda *args, **kwargs: {
            'candidates': [{'record_type': kind,
                'values': {field: values.get(field) for field in EXTRACTION_VALUE_FIELDS[kind]},
                'quote': text, 'outcome': 'new', 'match_reference': None, 'confidence': 'certain'}]})
        app.config['PEERSLATE_DEV_USER_KEY'] = owner
        context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.addCleanup(context.close)
        page = context.new_page()
        page.route('https://fonts.**', lambda route: route.abort())
        page.goto(self.base_url + '/app/resume')
        page.locator('#resume-intake').wait_for(state='visible')
        for _ in range(12):
            if page.locator('#resume-intake-input').is_visible():
                break
            if page.locator('#resume-intake-start-type').is_visible():
                page.locator('#resume-intake-start-type').click()
            elif page.locator('#resume-intake-next-question').is_visible():
                page.locator('#resume-intake-next-question').click()
            elif page.locator('#resume-intake-keep-adding').is_visible():
                page.locator('#resume-intake-keep-adding').click()
            else:
                page.locator('#resume-intake-back').click()
        page.locator('#resume-intake-input').wait_for(state='visible')
        page.locator('#resume-intake-text').fill(text)
        page.locator('#resume-intake-add').click()
        proposal = page.locator('#resume-intake-proposals > li:not(.resume-intake__hint)').first
        proposal.wait_for()
        return page, proposal

    def test_unsupported_employment_type_requires_visible_explicit_correction(self):
        owner = 'unsupported-employment-browser'
        page, proposal = self._proposal_page(owner, 'role', {
            'role_title': 'Assistant', 'employer_name': 'Example Cooperative',
            'employment_type': 'Seasonal fellowship', 'summary': 'An explicitly described seasonal fellowship.'},
            'Riley worked as an Assistant at Example Cooperative in a seasonal fellowship.')
        proposal.get_by_role('button', name='Edit fields manually', exact=True).click()
        employment = proposal.get_by_role('combobox', name='Employment type', exact=True)
        self.assertIn('Source: Seasonal fellowship', employment.inner_text())
        self.assertEqual(employment.input_value(), 'Seasonal fellowship')
        proposal.get_by_role('button', name='Confirm details', exact=True).click()
        page.wait_for_function("document.querySelector('#resume-intake-status').textContent.includes('Choose a supported employment type')")
        self.assertEqual(self.catalog.list_items(owner), [])
        employment.select_option('other')
        proposal.get_by_role('button', name='Confirm details', exact=True).click()
        page.locator('#resume-editor-lists h3').filter(has_text='Assistant').wait_for()
        row = self.draft_service.get_workspace(owner)['items'][0]
        self.assertEqual(row['values']['employment_type'], 'other')
        self.assertEqual(row['values']['summary'], 'An explicitly described seasonal fellowship.')

    def test_member_changes_completed_credential_status_without_stale_dates(self):
        for status in ('planned', 'in_progress'):
            with self.subTest(status=status):
                owner = 'credential-status-' + status
                page, proposal = self._proposal_page(owner, 'credential', {
                    'name': 'Example License', 'issuer': 'Example Board', 'completion_status': 'completed',
                    'issue_date': '2024-06-01', 'expiration_date': '2027-06-01', 'identifier': 'fixture-credential'},
                    'Riley completed Example License issued by Example Board on June 1, 2024, expiring June 1, 2027.')
                proposal.get_by_role('button', name='Edit fields manually', exact=True).click()
                proposal.get_by_role('combobox', name='Credential status', exact=True).select_option(status)
                self.assertTrue(proposal.locator('[data-proposal-field=issue_date]').is_hidden())
                proposal.get_by_role('button', name='Confirm details', exact=True).click()
                page.locator('#resume-editor-lists h3').filter(has_text='Example License').wait_for()
                row = self.draft_service.get_workspace(owner)['items'][0]
                self.assertEqual(row['values']['completion_status'], status)
                self.assertIsNone(row['values']['issue_date'])
                self.assertIsNone(row['values']['expiration_date'])
                self.assertEqual(row['values']['identifier'], 'fixture-credential')

    def test_fact_saved_refresh_does_not_replace_unsaved_editor_wording(self):
        owner = 'unsaved-editor-browser'
        self.catalog.create_private(owner, {'record_key': str(uuid4()), 'record_type': 'skill',
            'values': {'name': 'Existing strength', 'summary': 'Original summary'},
            'resume_display': False, 'visitor_ai': False})
        page, proposal = self._proposal_page(owner, 'skill', {'name': 'New strength'},
            'Riley has a new strength.')
        page.locator('#resume-intake-hide').click()
        page.get_by_role('heading', name='Existing strength', exact=True).wait_for()
        page.get_by_text('Edit', exact=True).first.click()
        summary = page.locator('#resume-editor-lists textarea[name="summary"]')
        summary.fill('My unsaved manual wording')
        page.locator('#resume-intake-reopen').click()
        proposal.get_by_role('button', name='Confirm details', exact=True).click()
        page.wait_for_function("document.querySelector('#resume-editor-status').textContent.includes('unsaved edits are kept')")
        self.assertEqual(summary.input_value(), 'My unsaved manual wording')
        self.assertEqual(len(self.catalog.list_items(owner)), 2)
        self.assertEqual(page.locator('#resume-editor-lists h3').filter(has_text='New strength').count(), 0)


@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
    'Playwright and Chrome required for the busy-retry client proof')
class LegacyClientBusyRetryBrowserTests(unittest.TestCase):
    """B2b: today's intake client (Guide rebuild off) keeps the same request id
    across a busy reply, so the retry replays instead of dispatching twice."""

    @classmethod
    def setUpClass(cls):
        install_intake_runtime_fixtures(cls)
        start_browser(cls)

    def test_busy_reply_then_retry_reuses_the_same_request_and_stores_once(self):
        from unittest.mock import patch
        from services.resume_intake_service import ResumeIntakeBusyError
        owner = 'busy-retry-browser-member'
        seen, real = [], self.intake_service.submit
        documents_before = len(self.received_documents)

        def busy_once(member, payload, **kwargs):
            seen.append(payload.get('request_id'))
            if len(seen) == 1:
                # The original request completes on the server, but this client
                # only sees the busy reply the bounded guard gives a duplicate
                # (as after a lost response and an automatic retry).
                real(member, payload, **kwargs)
                raise ResumeIntakeBusyError(payload.get('request_id'),
                    proposed={'text': None, 'items': [], 'attachments': payload.get('attachments')})
            return real(member, payload, **kwargs)

        with patch.dict(app.config, {'PEERSLATE_DEV_USER_KEY': owner,
                                     'PEERSLATE_GUIDE_REBUILD_ENABLED': False}), \
                patch.object(self.intake_service, 'submit', side_effect=busy_once):
            context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
            self.addCleanup(context.close)
            page = context.new_page()
            page.set_default_timeout(7000)
            page.route('https://fonts.**', lambda route: route.abort())
            page.goto(self.base_url + '/app/resume')
            if not page.locator('#resume-intake[open]').count():
                page.locator('#resume-intake-reopen').click()
            if page.locator('#resume-intake-welcome').is_visible():
                page.locator('#resume-intake-start-type').click()
            page.locator('#resume-intake-file').set_input_files({'name': 'synthetic-resume.txt',
                'mimeType': 'text/plain', 'buffer': b'Skills\nSQL.'})
            with page.expect_response(lambda response: response.url.endswith('/api/resume-intake/me/submissions')
                                      and response.status == 503) as busy:
                page.locator('#resume-intake-add').click()
            self.assertEqual(busy.value.json()['code'], 'request_in_progress')
            page.wait_for_function("() => !document.getElementById('resume-intake-add').disabled")
            with page.expect_response(lambda response: response.url.endswith('/api/resume-intake/me/submissions')
                                      and response.status == 200) as retried:
                page.locator('#resume-intake-add').click()
            self.assertTrue(retried.value.json()['replayed'], 'The retry must replay, not dispatch again')
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0], seen[1], 'The retry must reuse the busy request id')
        stored = self.repository.load_owner(owner)
        self.assertEqual(list(stored['receipts']), [seen[0]])
        self.assertEqual(len(self.received_documents) - documents_before, 1, 'The document is read once')
