"""Contract tests for the MVP1 C composer intake service.

Everything here runs against real service code with injected in-memory
stores. The in-memory store is labelled test-only; nothing here is SQL engine
proof, provider proof or live-identity proof.
"""

from __future__ import annotations

import io
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_document_adapter import DocumentParseResult, ResumeDocumentAdapter
from services.resume_intake_jobs import JobFence, fence_is_current, lease, enqueue
from services.resume_intake_policy import (
    fixture_policy_for_tests,
    selected_policy_for_tests,
)
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import (
    ResumeIntakeConflictError,
    ResumeIntakeNotFoundError,
    ResumeIntakePolicyError,
    ResumeIntakeService,
    ResumeIntakeUnavailableError,
    ResumeIntakeValidationError,
)
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter


ROLE_VALUES = {
    "role_title": "Systems Engineer",
    "employer_name": "Northrop Grumman",
    "location_text": None,
    "summary": "Supports requirements management and cross-functional systems engineering.",
    "start_date": "2025-01-01",
    "end_date": None,
    "date_precision": "month",
    "employment_type": "full_time",
    "current_role": True,
}


def skill(name, summary=None):
    return {"name": name, "summary": summary}


class FakeUpload:
    def __init__(self, mimetype, data, filename="file.bin"):
        self.mimetype = mimetype
        self.stream = io.BytesIO(data)
        self.filename = filename


class RecordingTranscriber:
    """Deterministic provider stub that records the exact bytes it received."""

    def __init__(self, transcript="I led the migration.", fail=None):
        self.transcript = transcript
        self.fail = fail
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"bytes": audio_bytes, "content_type": content_type, "locale": locale})
        if self.fail:
            from services.speech_transcription_service import SpeechTranscriptionError

            raise SpeechTranscriptionError(self.fail)
        return {
            "provider_transcript": self.transcript,
            "provider_request_id": "stub-request-1",
            "duration_seconds": 3.0,
        }


def wav_bytes(payload=b"\x00" * 64):
    return b"RIFF" + (len(payload) + 36).to_bytes(4, "little") + b"WAVE" + payload


def build_service(*, policy=None, document_pipeline=None, transcriber=None, interpreter=None):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    repository = InMemoryResumeIntakeRepository()
    adapter = None
    if transcriber is not None:
        adapter = ResumeTranscriptionAdapter(service=transcriber)
    service = ResumeIntakeService(
        repository=repository,
        draft_service=draft_service,
        document_adapter=ResumeDocumentAdapter(),
        transcription_adapter=adapter,
        policy=policy or selected_policy_for_tests(),
        interpreter=interpreter,
        document_pipeline=document_pipeline,
    )
    return service, catalog, draft_service


class ExplicitAddTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"

    def add(self, payload, **kwargs):
        body = {"type": "add_submission", "request_id": str(uuid4()), **payload}
        return self.service.submit(self.owner, body, **kwargs)

    def test_structured_facts_save_privately_and_free_text_stays_unresolved(self):
        receipt = self.add(
            {
                "items": [
                    {"client_key": "r1", "record_type": "role", "values": ROLE_VALUES},
                    {"client_key": "s1", "record_type": "skill", "values": skill("Requirements management")},
                    {"client_key": "s2", "record_type": "skill", "values": skill("Systems engineering")},
                ],
                "text": "One project I worked on involved a cross-team migration.",
            }
        )
        self.assertEqual(receipt["summary"]["saved"], 3)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])
        self.assertEqual(receipt["outcome"], "partial")
        saved = [row for row in receipt["results"] if row["outcome"] == "saved"]
        for row in saved:
            self.assertFalse(row["saved"] is False)
            self.assertEqual(row["display"], "off")
            self.assertEqual(row["visitor_ai"], "off")
        # Only the three explicit facts exist; the free text did not invent one.
        items = self.catalog.list_items(self.owner)
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertFalse(item["resume_display"])
            self.assertFalse(item["visitor_ai"])
        pending = self.service.get_workspace(self.owner)["pending_proposals"]
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0]["requires_member_wording"])

    def test_same_request_replays_and_changed_payload_conflicts(self):
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "s1", "record_type": "skill", "values": skill("MBSE")}],
        }
        first = self.service.submit(self.owner, body)
        replay = self.service.submit(self.owner, body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["request_digest"], first["request_digest"])
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": request_id,
                    "items": [{"client_key": "s1", "record_type": "skill", "values": skill("Different")}],
                },
            )
        self.assertEqual(caught.exception.error_code, "idempotency_conflict")
        self.assertIsNotNone(caught.exception.proposed)

    def test_partial_success_is_truthful_and_preserves_the_member_work(self):
        receipt = self.add(
            {
                "items": [{"client_key": "s1", "record_type": "skill", "values": skill("MBSE")}],
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "application/zip", "filename": "wrong.zip"}
                ],
            },
            files={"d1": FakeUpload("application/zip", b"PK\x03\x04not-really")},
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])
        self.assertEqual(receipt["outcome"], "partial")
        failed = next(row for row in receipt["results"] if row["outcome"] == "failed")
        self.assertEqual(failed["code"], "unsupported_type")
        self.assertFalse(failed["saved"])
        self.assertIn("not supported", failed["message"].lower())

    def test_missing_upload_is_a_failed_item_not_a_lost_submission(self):
        receipt = self.add(
            {
                "attachments": [
                    {"client_key": "d1", "kind": "document", "declared_content_type": "text/plain"}
                ]
            }
        )
        self.assertEqual(receipt["outcome"], "failed")
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])

    def test_document_boundary_records_exact_bytes_it_received(self):
        received = []

        def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
            received.append({"content_type": content_type, "data": admitted})
            from services.my_opportunities.member_import_service import ImportStageOutcome

            trail = (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                        outcome="extracted", reason_code=None, occurred_at=now),)
            return ("Extracted resume text from the attachment.", "extracted", None, False, trail)

        service, _catalog, _draft = build_service(document_pipeline=pipeline)
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "text/plain", "filename": "resume.txt"}
                ],
            },
            files={"d1": FakeUpload("text/plain", b"Systems Engineer at Example Co")},
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["content_type"], "text/plain")
        self.assertEqual(received[0]["data"], b"Systems Engineer at Example Co")
        self.assertEqual(receipt["summary"]["unresolved"], 1)

    def test_oversized_document_is_refused_before_parsing(self):
        policy = selected_policy_for_tests(max_document_bytes=16)
        service, _catalog, _draft = build_service(policy=policy)
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "d1", "kind": "document", "declared_content_type": "text/plain"}
                ],
            },
            files={"d1": FakeUpload("text/plain", b"x" * 64)},
        )
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertEqual(receipt["results"][0]["code"], "too_large")

    def test_authority_fields_are_rejected(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({"text": "hello", "owner_user_key": "someone-else"})
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({"text": "hello", "visitor_ai": True})

    def test_empty_add_is_rejected(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({})


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        first = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r1", "record_type": "role", "values": ROLE_VALUES},
                    {"client_key": "s1", "record_type": "skill", "values": skill("MBSE")},
                ],
            },
        )
        self.assertEqual(first["summary"]["saved"], 2)
        self.role_key = next(
            item["record_key"] for item in self.catalog.list_items(self.owner)
            if item["record_type"] == "role"
        )

    def add_text(self, text):
        return self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "text": text},
        )

    def test_merely_similar_skill_is_ambiguous_not_a_duplicate(self):
        self.add_text("I am strong in MBSE.")
        self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s2", "record_type": "skill", "values": skill("mbse")}],
            },
        )
        pending = self.service.get_workspace(self.owner)["pending_proposals"]
        kinds = {row["kind"] for row in pending}
        self.assertIn("ambiguous_match", kinds)
        # Merely-similar wording did not create a second canonical skill.
        skills = [i for i in self.catalog.list_items(self.owner) if i["record_type"] == "skill"]
        self.assertEqual(len(skills), 1)

    def test_changed_employer_for_same_title_is_a_contradiction(self):
        changed = dict(ROLE_VALUES, employer_name="Example Corp")
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r2", "record_type": "role", "values": changed}],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "contradiction")
        self.assertEqual(proposal["target_key"], self.role_key)
        self.assertEqual(proposal["proposed_values"]["employer_name"], "Example Corp")
        # Canonical wording is untouched until the member decides.
        canonical = next(
            i for i in self.catalog.list_items(self.owner) if i["record_key"] == self.role_key
        )
        self.assertEqual(canonical["values"]["employer_name"], "Northrop Grumman")

    def test_added_detail_to_existing_fact_requires_review(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r3", "record_type": "role",
                     "values": dict(ROLE_VALUES, location_text="Huntsville, Alabama")}
                ],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertEqual(receipt["proposals"][0]["kind"], "additional_detail")
        self.assertEqual(receipt["proposals"][0]["target_key"], self.role_key)

    def test_first_acceptance_saves_a_new_fact_without_a_prior_receipt(self):
        created = self.add_text("Certified Kubernetes Administrator")
        proposal_key = created["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": {
                    "record_type": "credential",
                    "name": "Certified Kubernetes Administrator",
                    "issuer": "The Linux Foundation",
                    "completion_status": "completed",
                    "issue_date": "2024-05-01",
                    "identifier": None,
                    "expiration_date": None,
                    "verification_url": None,
                },
            },
        )
        self.assertEqual(decided["outcome"], "saved")
        self.assertFalse(decided["item"]["resume_display"])
        self.assertFalse(decided["item"]["visitor_ai"])
        credential = next(
            i for i in self.catalog.list_items(self.owner) if i["record_type"] == "credential"
        )
        self.assertEqual(credential["values"]["issuer"], "The Linux Foundation")

    def test_accepting_a_change_routes_through_the_private_draft_overlay(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r9", "record_type": "role",
                     "values": dict(ROLE_VALUES, summary="Leads requirements management.")}
                ],
            },
        )
        proposal_key = receipt["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": dict(ROLE_VALUES, summary="Leads requirements management."),
            },
        )
        self.assertEqual(decided["outcome"], "saved")
        self.assertTrue(decided["item"]["draft_overlay"])
        canonical = next(
            i for i in self.catalog.list_items(self.owner) if i["record_key"] == self.role_key
        )
        self.assertEqual(canonical["values"]["summary"], ROLE_VALUES["summary"])

    def test_rejecting_a_proposal_saves_nothing(self):
        created = self.add_text("Maybe some personal notes.")
        proposal_key = created["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {"request_id": str(uuid4()), "proposal_key": proposal_key, "decision": "reject"},
        )
        self.assertEqual(decided["outcome"], "unresolved")
        self.assertIsNone(decided["item"])
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_second_acceptance_of_the_same_proposal_conflicts(self):
        created = self.add_text("Another note")
        proposal_key = created["proposals"][0]["proposal_key"]
        body = {
            "request_id": str(uuid4()),
            "proposal_key": proposal_key,
            "decision": "reject",
        }
        self.service.decide(self.owner, body)
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.decide(self.owner, {**body, "request_id": str(uuid4())})


class SourcePurgeTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        self.receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "I managed a budget of 2 million dollars.",
            },
        )
        self.source_key = self.receipt["submission"]["source_keys"][0]
        self.proposal_key = self.receipt["proposals"][0]["proposal_key"]

    def test_purge_removes_text_and_fences_late_work(self):
        purged = self.service.purge_source(
            self.owner,
            {"request_id": str(uuid4()), "source_key": self.source_key},
        )
        self.assertEqual(purged["outcome"], "purged")
        self.assertFalse(purged["source_resurrected"])
        self.assertTrue(purged["provenance_retained"])
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertIsNone(snapshot["sources"][self.source_key]["text"])
        proposal = snapshot["proposals"][self.proposal_key]
        self.assertTrue(proposal["source_purged"])
        self.assertEqual(proposal["state"], "invalidated")
        # Historical provenance is retained but is not permission to resurrect.
        self.assertEqual(proposal["provenance"]["source_key"], self.source_key)

    def test_accepting_after_purge_conflicts_and_keeps_the_wording(self):
        self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": {"record_type": "accomplishment", "wording": "Kept wording"},
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertIsNotNone(caught.exception.proposed)

    def test_duplicate_purge_is_idempotent_not_an_error(self):
        first = self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        second = self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        self.assertEqual(first["outcome"], "purged")
        self.assertEqual(second["outcome"], "already_purged")

    def test_foreign_source_is_neutral_not_found(self):
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.service.purge_source(
                "member-b", {"request_id": str(uuid4()), "source_key": self.source_key}
            )

    def test_late_job_after_purge_is_stale_and_writes_nothing(self):
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot.setdefault("jobs", {})
        fence = JobFence(
            source_key=self.source_key,
            source_version=int(snapshot["sources"][self.source_key]["version"]),
            submission_key=self.receipt["submission"]["submission_key"],
            submission_version=1,
            policy_version=1,
            lifecycle_epoch=snapshot["lifecycle_epoch"],
        )
        job = enqueue(snapshot, fence, "document_parse")
        self.assertTrue(fence_is_current(snapshot, job["fence"]))
        self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        after = self.service.repository.load_owner(self.owner)
        self.assertFalse(fence_is_current(after, job["fence"]))
        with self.assertRaises(Exception):
            lease(after, job["job_key"])


class FieldIntentTests(unittest.TestCase):
    """A partial change must never blank a field the member did not touch."""

    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        created = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role", "values": ROLE_VALUES}],
            },
        )
        self.assertEqual(created["summary"]["saved"], 1)
        self.record_key = created["saved_items"][0]["record_key"]

    def overlay_values(self):
        snapshot = self.draft_service.repository.load_owner(self.owner)
        return snapshot["items"][self.record_key]["proposed_values"]

    def partial_change(self, values, clears=None):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "r2",
                    "record_type": "role",
                    "values": values,
                    "explicit_clears": clears or [],
                }],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        return receipt["proposals"][0]

    def accept(self, proposal):
        return self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal["proposal_key"],
                "decision": "accept",
                "confirmed_values": proposal["proposed_values"],
            },
        )

    def test_composer_shaped_partial_change_preserves_other_fields(self):
        # Exactly the shape the composer emits when the member fills only the
        # subject fields: no null padding and no default booleans.
        proposal = self.partial_change(
            {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"}
        )
        self.assertEqual(
            set(proposal["proposed_values"]), {"role_title", "employer_name"}
        )
        decided = self.accept(proposal)
        self.assertEqual(decided["outcome"], "saved")
        merged = self.overlay_values()
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])
        self.assertEqual(merged["date_precision"], "month")
        self.assertTrue(merged["current_role"])
        self.assertEqual(merged["employment_type"], "full_time")

    def test_adding_one_detail_keeps_every_other_field(self):
        proposal = self.partial_change(
            {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
                "location_text": "Huntsville, Alabama",
            }
        )
        self.assertEqual(proposal["kind"], "additional_detail")
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertEqual(merged["location_text"], "Huntsville, Alabama")
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])

    def test_explicit_clear_still_works_and_touches_only_that_field(self):
        proposal = self.partial_change(
            {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            clears=["summary"],
        )
        self.assertEqual(proposal["explicit_clears"], ["summary"])
        self.assertIsNone(proposal["proposed_values"]["summary"])
        self.assertEqual(proposal["kind"], "contradiction")
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertIsNone(merged["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])
        self.assertTrue(merged["current_role"])

    def test_explicit_clear_of_an_unchanged_boolean_is_allowed(self):
        proposal = self.partial_change(
            {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            clears=["current_role"],
        )
        self.assertFalse(proposal["proposed_values"]["current_role"])
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertFalse(merged["current_role"])
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])

    def test_setting_and_clearing_the_same_field_is_refused(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "items": [{
                        "client_key": "r3",
                        "record_type": "role",
                        "values": {"role_title": "Systems Engineer",
                                   "employer_name": "Northrop Grumman"},
                        "explicit_clears": ["role_title"],
                    }],
                },
            )

    def test_unknown_clear_field_is_refused(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "items": [{
                        "client_key": "r4",
                        "record_type": "skill",
                        "values": {"name": "MBSE"},
                        "explicit_clears": ["visitor_ai"],
                    }],
                },
            )


class AtomicityTests(unittest.TestCase):
    """One member action commits once: canonical facts and the receipt agree."""

    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"

    def two_skill_body(self, request_id):
        return {
            "type": "add_submission",
            "request_id": request_id,
            "items": [
                {"client_key": "s1", "record_type": "skill", "values": {"name": "First skill"}},
                {"client_key": "s2", "record_type": "skill", "values": {"name": "Second skill"}},
            ],
        }

    def test_intake_store_failure_leaves_no_canonical_fact_and_retries_clean(self):
        from services.resume_intake_repository import ResumeIntakeStoreUnavailable

        original = self.service.repository.save_owner

        def failing(owner, snapshot, command=None):
            raise ResumeIntakeStoreUnavailable("synthetic final-store failure")

        self.service.repository.save_owner = failing
        request_id = str(uuid4())
        with self.assertRaises(ResumeIntakeUnavailableError) as caught:
            self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertIsNotNone(caught.exception.proposed)
        self.assertEqual(self.catalog.list_items(self.owner), [])
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertEqual(snapshot["receipts"], {})
        self.assertEqual(snapshot["submissions"], {})
        self.assertEqual(snapshot["sources"], {})

        self.service.repository.save_owner = original
        retried = self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(retried["summary"]["saved"], 2)
        self.assertEqual(retried["summary"]["unresolved"], 0)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_second_canonical_write_failure_rolls_back_the_first(self):
        from services.resume_draft_service import ResumeDraftUnavailableError

        original = self.draft_service.commit
        calls = {"count": 0}

        def flaky(owner, payload):
            if payload.get("type") == "create_private_item":
                calls["count"] += 1
                if calls["count"] == 2:
                    raise ResumeDraftUnavailableError()
            return original(owner, payload)

        self.draft_service.commit = flaky
        request_id = str(uuid4())
        with self.assertRaises(ResumeIntakeUnavailableError):
            self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(self.service.repository.load_owner(self.owner)["receipts"], {})

        self.draft_service.commit = original
        retried = self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(retried["summary"]["saved"], 2)
        self.assertEqual(retried["summary"]["unresolved"], 0)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_receipt_and_canonical_fact_commit_together_on_success(self):
        receipt = self.service.submit(self.owner, self.two_skill_body(str(uuid4())))
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertIn(receipt["request_id"], snapshot["receipts"])
        self.assertEqual(len(snapshot["submissions"]), 1)
        self.assertEqual(len(snapshot["sources"]), 2)
        self.assertEqual(len(snapshot["jobs"]), 2)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)


class ByteBoundIdempotencyTests(unittest.TestCase):
    """A request digest binds to the admitted bytes, not to their metadata."""

    def test_same_audio_replays_and_different_audio_conflicts(self):
        transcriber = RecordingTranscriber("first recording")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        request_id = str(uuid4())
        body = {"request_id": request_id, "client_key": "mic-1", "duration_seconds": 3.0}
        payload = wav_bytes(b"\x00" * 64)
        first = service.transcribe_recording("member-a", FakeUpload("audio/wav", payload), body)
        replay = service.transcribe_recording("member-a", FakeUpload("audio/wav", payload), body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(transcriber.calls), 1)

        transcriber.transcript = "different second recording"
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            service.transcribe_recording(
                "member-a", FakeUpload("audio/wav", wav_bytes(b"\x01" * 64)), body
            )
        self.assertEqual(caught.exception.error_code, "idempotency_conflict")
        # The provider was never asked to transcribe the changed bytes.
        self.assertEqual(len(transcriber.calls), 1)

        with self.assertRaises(ResumeIntakeConflictError) as duration_conflict:
            service.transcribe_recording(
                "member-a",
                FakeUpload("audio/wav", payload),
                {**body, "duration_seconds": 4.0},
            )
        self.assertEqual(duration_conflict.exception.error_code, "idempotency_conflict")
        self.assertEqual(len(transcriber.calls), 1)

    def test_same_document_bytes_replay_and_changed_bytes_conflict(self):
        received = []

        def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
            received.append(admitted)
            from services.my_opportunities.member_import_service import ImportStageOutcome

            return ("Extracted text.", "extracted", None, False,
                    (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                        outcome="extracted", reason_code=None, occurred_at=now),))

        service, _catalog, _draft = build_service(document_pipeline=pipeline)
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "attachments": [{"client_key": "d1", "kind": "document",
                             "declared_content_type": "text/plain", "filename": "same.txt"}],
        }
        def files(data):
            # A fresh upload per attempt: a real request stream is consumed once.
            return {"d1": FakeUpload("text/plain", data)}

        first = service.submit("member-a", body, files=files(b"same bytes"))
        replay = service.submit("member-a", body, files=files(b"same bytes"))
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(received, [b"same bytes"])
        with self.assertRaises(ResumeIntakeConflictError):
            service.submit("member-a", body, files=files(b"different bytes"))
        self.assertEqual(received, [b"same bytes"])


class UiShapedRecordMatrixTests(unittest.TestCase):
    """Drive the service with the sparse payloads the composer actually emits."""

    def setUp(self):
        self.service, self.catalog, _draft = build_service()
        self.owner = "matrix-member"
        self.parent_key = str(uuid4())
        self.catalog.put_item(
            self.owner,
            {
                "record_key": self.parent_key,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": dict(ROLE_VALUES),
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )

    def _cases(self):
        return {
            "role": {"role_title": "Program Lead", "employer_name": "Example Works"},
            "skill": {"name": "Systems thinking"},
            "education": {
                "title": "Systems Engineering",
                "institution_name": "Example University",
                "education_status": "in_progress",
            },
            "credential": {
                "name": "Architecture Certificate",
                "issuer": "Example Institute",
                "completion_status": "completed",
                "issue_date": "2026-09-01",
            },
            "accomplishment": {"wording": "Reduced review time by 20 percent"},
        }

    def test_direct_add_accepts_ui_shaped_payload_for_every_record_type(self):
        for record_type, values in self._cases().items():
            with self.subTest(record_type=record_type):
                item = {
                    "client_key": "direct-" + record_type,
                    "record_type": record_type,
                    "values": values,
                }
                if record_type == "accomplishment":
                    item["parent_key"] = self.parent_key
                receipt = self.service.submit(
                    self.owner,
                    {"type": "add_submission", "request_id": str(uuid4()), "items": [item]},
                )
                self.assertEqual(receipt["summary"]["saved"], 1)

    def test_proposal_accept_accepts_ui_shaped_values_for_every_record_type(self):
        for record_type, values in self._cases().items():
            with self.subTest(record_type=record_type):
                created = self.service.submit(
                    self.owner,
                    {
                        "type": "add_submission",
                        "request_id": str(uuid4()),
                        "text": "Member wording for " + record_type,
                    },
                )
                confirmed = {"record_type": record_type, **values}
                if record_type == "accomplishment":
                    confirmed["parent_key"] = self.parent_key
                accepted = self.service.decide(
                    self.owner,
                    {
                        "request_id": str(uuid4()),
                        "proposal_key": created["proposals"][0]["proposal_key"],
                        "decision": "accept",
                        "confirmed_values": confirmed,
                    },
                )
                self.assertEqual(accepted["outcome"], "saved")

    def test_existing_record_change_preserves_untouched_required_fields(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "partial-role",
                    "record_type": "role",
                    "values": {"role_title": ROLE_VALUES["role_title"], "summary": "New detail"},
                }],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        accepted = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": receipt["proposals"][0]["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"summary": "New detail"},
            },
        )
        self.assertEqual(accepted["outcome"], "saved")
        self.assertEqual(accepted["item"]["proposed_values"]["summary"], "New detail")
        self.assertEqual(
            accepted["item"]["proposed_values"]["employer_name"],
            ROLE_VALUES["employer_name"],
        )


class SavedReplayContentTests(unittest.TestCase):
    def test_saved_item_replay_hydrates_equal_content_then_labels_current_change(self):
        service, catalog, _draft = build_service()
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "skill", "record_type": "skill", "values": {"name": "MBSE"}}],
        }
        first = service.submit("member-a", body)
        replay = service.submit("member-a", body)
        self.assertEqual(replay["saved_items"][0]["values"]["name"], "MBSE")
        self.assertTrue(replay["saved_items"][0]["content_equivalent_to_first_response"])

        key = first["saved_items"][0]["record_key"]
        changed = catalog.get_item("member-a", key)
        changed["content_token"] = "2"
        changed["values"]["name"] = "Current MBSE wording"
        catalog.put_item("member-a", changed)
        after_change = service.submit("member-a", body)
        item = after_change["saved_items"][0]
        self.assertEqual(item["values"]["name"], "Current MBSE wording")
        self.assertFalse(item["content_equivalent_to_first_response"])
        self.assertEqual(item["values_source"], "current_canonical_at_replay")

        source_key = first["submission"]["source_keys"][0]
        service.purge_source("member-a", {"request_id": str(uuid4()), "source_key": source_key})
        after_purge = service.submit("member-a", body)
        self.assertEqual(after_purge["saved_items"][0]["values"]["name"], "Current MBSE wording")

    def test_recording_replay_distinguishes_missing_version_changed_and_purged(self):
        transcriber = RecordingTranscriber("recoverable words")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        body = {"request_id": str(uuid4()), "client_key": "mic", "duration_seconds": 2.0}
        first = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        snapshot = service.repository.load_owner("member-a")
        source = snapshot["sources"][first["source_key"]]
        source["version"] = 2
        service.repository.save_owner("member-a", snapshot)
        changed = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(changed["source_unavailable_reason"], "version_changed")
        self.assertFalse(changed.get("source_purged", False))

        snapshot = service.repository.load_owner("member-a")
        snapshot["sources"][first["source_key"]]["state"] = "purged"
        service.repository.save_owner("member-a", snapshot)
        purged = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(purged["source_unavailable_reason"], "purged")
        self.assertTrue(purged["source_purged"])

        snapshot = service.repository.load_owner("member-a")
        del snapshot["sources"][first["source_key"]]
        service.repository.save_owner("member-a", snapshot)
        missing = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(missing["source_unavailable_reason"], "missing")
        self.assertFalse(missing.get("source_purged", False))


class StaleAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        created = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role", "values": ROLE_VALUES}],
            },
        )
        self.record_key = created["saved_items"][0]["record_key"]
        pending = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r2", "record_type": "role",
                           "values": {"role_title": "Systems Engineer",
                                      "employer_name": "Example Corp"}}],
            },
        )
        self.proposal = pending["proposals"][0]
        self.proposal_key = self.proposal["proposal_key"]

    def test_edit_decision_enforces_the_same_binding_checks_as_accept(self):
        # The source version moves after the proposal was made.
        snapshot = self.service.repository.load_owner(self.owner)
        source = snapshot["sources"][self.proposal["provenance"]["source_key"]]
        snapshot["sources"][source["source_key"]]["version"] = int(source["version"]) + 1
        self.service.repository.save_owner(self.owner, snapshot)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "edit",
                    "confirmed_values": {"role_title": "Systems Engineer",
                                         "employer_name": "Example Corp"},
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertIsNotNone(caught.exception.proposed)

    def test_acceptance_uses_the_captured_target_versions(self):
        # The canonical record changes after the proposal captured its token.
        self.catalog.bump_content(self.owner, self.record_key)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": self.proposal["proposed_values"],
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertEqual(caught.exception.proposed, self.proposal["proposed_values"])
        # Nothing was written over the newer record.
        canonical = self.catalog.get_item(self.owner, self.record_key)
        self.assertEqual(canonical["values"]["employer_name"], "Northrop Grumman")

    def test_acceptance_uses_the_captured_access_revision(self):
        self.catalog.bump_access(self.owner, self.record_key)
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": self.proposal["proposed_values"],
                },
            )
        self.assertFalse(self.catalog.get_item(self.owner, self.record_key)["resume_display"])

    def test_reject_still_works_on_a_stale_proposal(self):
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot["sources"][self.proposal["provenance"]["source_key"]]["version"] += 1
        self.service.repository.save_owner(self.owner, snapshot)
        decided = self.service.decide(
            self.owner,
            {"request_id": str(uuid4()), "proposal_key": self.proposal_key,
             "decision": "reject"},
        )
        self.assertEqual(decided["outcome"], "unresolved")

    def test_unreadable_canonical_catalog_fails_closed(self):
        class BlindDraft:
            repository = None
            catalog = None

            def get_workspace(self, owner):
                from services.resume_draft_service import ResumeDraftUnavailableError

                raise ResumeDraftUnavailableError()

            def commit(self, owner, payload):  # pragma: no cover - never reached
                raise AssertionError("must not write while the catalog is unreadable")

        from services.resume_draft_service import ResumeDraftService

        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=BlindDraft(),
            policy=selected_policy_for_tests(),
        )
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.submit(
                self.owner,
                {"type": "add_submission", "request_id": str(uuid4()),
                 "items": [{"client_key": "s1", "record_type": "skill",
                            "values": {"name": "MBSE"}}]},
            )

    def test_crafted_confirmed_values_are_refused_not_a_server_error(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": {"role_title": "Systems Engineer",
                                         "employer_name": "Example Corp",
                                         "visitor_ai": True},
                },
            )

    def test_canonical_validation_refusal_is_a_safe_4xx_not_a_500(self):
        from services.resume_draft_service import ResumeDraftValidationError

        class RefusingDraft(ResumeDraftService):
            def commit(self, owner, payload):
                if payload.get("type") == "create_private_item":
                    raise ResumeDraftValidationError("The canonical command was rejected.")
                return super().commit(owner, payload)

        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=RefusingDraft(
                repository=InMemoryResumeDraftRepository(),
                catalog=InMemoryCanonicalCatalog(),
            ),
            policy=selected_policy_for_tests(),
        )
        with self.assertRaises(ResumeIntakeValidationError):
            service.submit(
                "member-a",
                {"type": "add_submission", "request_id": str(uuid4()),
                 "items": [{"client_key": "s1", "record_type": "skill",
                            "values": {"name": "MBSE"}}]},
            )


class OwnerIsolationTests(unittest.TestCase):
    def test_two_members_do_not_share_submissions_or_proposals(self):
        service, catalog, _draft = build_service()
        first = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "A only note.",
            },
        )
        second = service.submit(
            "member-b",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "B only note.",
            },
        )
        self.assertNotEqual(
            first["submission"]["submission_key"], second["submission"]["submission_key"]
        )
        workspace_b = service.get_workspace("member-b")
        self.assertEqual(len(workspace_b["pending_proposals"]), 1)
        self.assertNotEqual(
            workspace_b["pending_proposals"][0]["proposal_key"],
            first["proposals"][0]["proposal_key"],
        )
        self.assertEqual(catalog.list_items("member-a"), [])

    def test_policy_fails_closed_when_onboarding_is_unselected(self):
        service, _catalog, _draft = build_service(policy=fixture_policy_for_tests())
        with self.assertRaises(ResumeIntakePolicyError):
            service.submit(
                "member-a",
                {"type": "add_submission", "request_id": str(uuid4()), "text": "hello"},
            )
        allowed = service.submit(
            "member-a",
            {"type": "add_submission", "request_id": str(uuid4()), "text": "hello"},
            allow_fixture_policy=True,
        )
        self.assertEqual(allowed["summary"]["unresolved"], 1)


class TranscriptionTests(unittest.TestCase):
    def test_in_field_recording_reaches_the_provider_boundary_with_real_bytes(self):
        transcriber = RecordingTranscriber("I supervised twelve engineers.")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        payload = wav_bytes()
        result = service.transcribe_recording(
            "member-a",
            FakeUpload("audio/wav", payload),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["transcript"], "I supervised twelve engineers.")
        self.assertEqual(len(transcriber.calls), 1)
        self.assertEqual(transcriber.calls[0]["bytes"], payload)
        self.assertEqual(transcriber.calls[0]["content_type"], "audio/wav")
        self.assertIn("source_key", result)

    def test_recording_transcription_is_idempotent_and_failures_preserve_input(self):
        transcriber = RecordingTranscriber(fail="speech_timeout")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        request_id = str(uuid4())
        body = {"request_id": request_id, "client_key": "mic-1", "duration_seconds": 2.0}
        first = service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        replay = service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertFalse(first["success"])
        self.assertTrue(first["input_preserved"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(transcriber.calls), 1)

    def test_overlapping_same_request_reaches_provider_once_in_one_process(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingTranscriber(RecordingTranscriber):
            def transcribe(self, audio_bytes, content_type, locale="en-US"):
                result = super().transcribe(audio_bytes, content_type, locale)
                entered.set()
                release.wait(timeout=5)
                return result

        transcriber = BlockingTranscriber("one durable recording")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        body = {
            "request_id": str(uuid4()), "client_key": "mic-race",
            "duration_seconds": 2.0,
        }
        results = []
        errors = []

        def invoke():
            try:
                results.append(service.transcribe_recording(
                    "member-a", FakeUpload("audio/wav", wav_bytes()), body
                ))
            except Exception as error:  # pragma: no cover - assertion reports it
                errors.append(error)

        first = threading.Thread(target=invoke)
        second = threading.Thread(target=invoke)
        first.start()
        self.assertTrue(entered.wait(timeout=5))
        second.start()
        time.sleep(0.05)
        release.set()
        first.join(timeout=5)
        second.join(timeout=5)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(transcriber.calls), 1)
        self.assertEqual(sorted(row["replayed"] for row in results), [False, True])
        self.assertEqual({row["source_key"] for row in results}, {results[0]["source_key"]})

    def test_shared_store_claim_prevents_provider_work_across_service_instances(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingTranscriber(RecordingTranscriber):
            def transcribe(self, audio_bytes, content_type, locale="en-US"):
                result = super().transcribe(audio_bytes, content_type, locale)
                entered.set()
                release.wait(timeout=5)
                return result

        repository = InMemoryResumeIntakeRepository()
        catalog = InMemoryCanonicalCatalog()
        draft = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(), catalog=catalog
        )
        transcriber = BlockingTranscriber("one cross-instance recording")

        def make_service():
            return ResumeIntakeService(
                repository=repository,
                draft_service=draft,
                transcription_adapter=ResumeTranscriptionAdapter(service=transcriber),
                policy=selected_policy_for_tests(),
            )

        holder_service = make_service()
        competing_service = make_service()
        body = {
            "request_id": str(uuid4()), "client_key": "mic-shared",
            "duration_seconds": 2.0,
        }
        holder_results = []

        holder = threading.Thread(target=lambda: holder_results.append(
            holder_service.transcribe_recording(
                "member-a", FakeUpload("audio/wav", wav_bytes()), body
            )
        ))
        holder.start()
        self.assertTrue(entered.wait(timeout=5))

        pending = competing_service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertEqual(pending["outcome"], "pending")
        self.assertEqual(pending["code"], "recording_pending")
        self.assertFalse(pending["provider_called_by_this_attempt"])
        self.assertEqual(len(transcriber.calls), 1)

        release.set()
        holder.join(timeout=5)
        self.assertEqual(len(holder_results), 1)
        replay = competing_service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["source_key"], holder_results[0]["source_key"])
        self.assertEqual(len(transcriber.calls), 1)

    def test_expired_claim_requires_recovery_and_never_transfers_the_lease(self):
        repository = InMemoryResumeIntakeRepository()
        request_id = str(uuid4())
        digest = "a" * 64
        payload = {
            "type": "claim_recording", "request_id": request_id,
            "request_digest": digest, "client_key": "mic-expired",
            "entrance": "resume_onboarding", "policy_version": 1,
            "lifecycle_epoch": 0, "audio_sha256": "b" * 64,
            "byte_length": 72, "content_type": "audio/wav",
            "duration_seconds": 2.0,
        }
        started = datetime(2026, 9, 11, tzinfo=timezone.utc)
        claimed = repository.claim_recording(
            "member-a", request_id, payload, now=started
        )
        expired = repository.claim_recording(
            "member-a", request_id, payload, now=started + timedelta(minutes=6)
        )

        self.assertEqual(claimed["outcome"], "claimed")
        self.assertEqual(expired["outcome"], "pending")
        self.assertTrue(expired["recovery_required"])
        self.assertNotIn("lease_id", expired)
        self.assertNotIn("source_key", expired)
        self.assertEqual(
            repository._recording_claims[("member-a", request_id)]["lease_id"],
            claimed["lease_id"],
        )
        self.assertEqual(
            repository._recording_claims[("member-a", request_id)]["state"],
            "recovery_required",
        )

    def test_unsupported_audio_is_refused_before_the_provider(self):
        transcriber = RecordingTranscriber()
        service, _catalog, _draft = build_service(transcriber=transcriber)
        with self.assertRaises(ResumeIntakeValidationError):
            service.transcribe_recording(
                "member-a",
                FakeUpload("audio/wav", b"not really a wav"),
                {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 2.0},
            )
        self.assertEqual(transcriber.calls, [])

    def test_transcribed_recording_can_be_added_and_becomes_a_proposal(self):
        transcriber = RecordingTranscriber("I led the platform migration.")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        recorded = service.transcribe_recording(
            "member-a",
            FakeUpload("audio/wav", wav_bytes()),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 4.0},
        )
        receipt = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "mic-1", "kind": "recording",
                     "source_key": recorded["source_key"]}
                ],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertEqual(receipt["proposals"][0]["quote"], "I led the platform migration.")

    def test_add_of_an_untranscribed_recording_fails_honestly(self):
        service, _catalog, _draft = build_service()
        receipt = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{"client_key": "mic-1", "kind": "recording"}],
            },
        )
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertEqual(receipt["results"][0]["code"], "recording_not_transcribed")


class RealSeamDocumentTests(unittest.TestCase):
    """The shared document seam runs for real here -- no parser stub.

    These prove the reused decode/parse/extract pipeline (including the
    OS-isolated DOCX child process) is genuinely wired, not only replaceable.
    """

    @staticmethod
    def docx_bytes(*paragraphs):
        """Build a minimal, real DOCX package without a generator dependency."""

        import zipfile

        body = "".join(
            f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
            for text in paragraphs
        )
        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>"
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        )
        relationships = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>'
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", relationships)
            archive.writestr("word/document.xml", document)
        return buffer.getvalue()

    def submit_document(self, service, content_type, data, filename):
        return service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{"client_key": "d1", "kind": "document",
                                 "declared_content_type": content_type,
                                 "filename": filename}],
            },
            files={"d1": FakeUpload(content_type, data, filename)},
        )

    def test_plain_text_document_is_extracted_by_the_real_pipeline(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service, "text/plain", b"Systems Engineer at Northrop Grumman", "resume.txt"
        )
        self.assertEqual(receipt["summary"]["failed"], 0)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertIn("Northrop Grumman", receipt["proposals"][0]["quote"])

    def test_docx_document_is_extracted_by_the_isolated_seam(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            self.docx_bytes("Systems Engineer at Northrop Grumman"),
            "resume.docx",
        )
        self.assertEqual(receipt["summary"]["failed"], 0)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertIn("Northrop Grumman", receipt["proposals"][0]["quote"])

    def test_a_non_text_document_reports_no_selectable_text(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            self.docx_bytes(),
            "empty.docx",
        )
        self.assertEqual(receipt["summary"]["unresolved"], 0)
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertIn("scan", receipt["results"][0]["message"].lower())


class WorkspaceTests(unittest.TestCase):
    def test_workspace_read_does_not_start_processing_and_is_labelled(self):
        service, _catalog, _draft = build_service(policy=fixture_policy_for_tests())
        before = service.repository.load_owner("member-a")
        workspace = service.get_workspace("member-a")
        after = service.repository.load_owner("member-a")
        self.assertEqual(before["jobs"], after["jobs"])
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertFalse(workspace["capabilities"]["persistence_is_live_database"])
        self.assertFalse(workspace["capabilities"]["starts_processing_on_read"])
        self.assertFalse(workspace["capabilities"]["publishes"])
        self.assertFalse(workspace["policy"]["durable_persistence_allowed"])

    def test_document_result_reports_truncation_honestly(self):
        parsed = DocumentParseResult(
            admitted=True, ok=True, outcome="partial", reason="output_truncated",
            text="truncated text", truncated=True, content_type="text/plain",
            byte_length=10, sha256="0" * 64, member_message="Only part of that document could be read.",
        )
        receipt = parsed.as_receipt()
        self.assertTrue(receipt["truncated"])
        self.assertEqual(receipt["outcome"], "partial")
        self.assertTrue(receipt["readable_text"])


if __name__ == "__main__":
    unittest.main()
