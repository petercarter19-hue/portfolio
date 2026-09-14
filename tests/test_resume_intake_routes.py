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
from services.resume_intake_policy import selected_policy_for_tests
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
        self.service._policy = None  # resolve the real (unselected) onboarding policy
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
