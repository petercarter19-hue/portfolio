"""Contract tests for My Data document and voice source intake.

Selectable-text PDF, DOCX, and TXT files are admitted up to exactly
10,000,000 bytes each; scans without selectable text get a truthful
unsupported message with no implied OCR. English recordings run up to 180
seconds each with several allowed per draft; success keeps an editable
transcript and drops the audio, while failure keeps a private retryable
recording that never reaches the provider twice. Originals stay inspectable
and separately deletable. Deterministic parser and provider doubles only.
"""

from __future__ import annotations

import io
import unittest
from uuid import uuid4

from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.resume_intake_policy import MY_DATA_POLICY, selected_policy_for_tests
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService, ResumeIntakeValidationError
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter
from services.speech_transcription_service import SpeechTranscriptionError


TEN_MB = 10_000_000


class FakeUpload:
    def __init__(self, mimetype, data):
        self.mimetype = mimetype
        self.stream = io.BytesIO(data)


def build_service(*, transcriber=None, pipeline=None):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    transcription = None
    if transcriber is not None:
        transcription = ResumeTranscriptionAdapter(service=transcriber)
    return ResumeIntakeService(
        repository=InMemoryResumeIntakeRepository(),
        draft_service=draft_service,
        transcription_adapter=transcription,
        policy=selected_policy_for_tests(),
        document_pipeline=pipeline,
    )


def recording_payload(content_type, data, duration):
    return FakeUpload(content_type, data), {
        "request_id": str(uuid4()),
        "client_key": "clip-1",
        "duration_seconds": duration,
    }


def wav_bytes(payload=b"\x00" * 64):
    return b"RIFF" + (len(payload) + 36).to_bytes(4, "little") + b"WAVE" + payload


class StubTranscriber:
    def __init__(self, transcript="I led the migration.", fail=None):
        self.transcript = transcript
        self.fail = fail
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({
            "bytes": audio_bytes, "content_type": content_type, "locale": locale,
        })
        if self.fail:
            raise SpeechTranscriptionError(self.fail)
        return {
            "provider_transcript": self.transcript,
            "provider_request_id": "stub-request-1",
            "duration_seconds": 3.0,
        }


def extracted_pipeline(text):
    def run(*args, **kwargs):
        return text, "extracted", None, False, None
    return run


def empty_pipeline(*args, **kwargs):
    return "", "empty", "no_text", False, None


class DocumentBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.service = build_service(pipeline=extracted_pipeline("Led the migration."))
        self.owner = "member-a"

    def add_with_document(self, data, content_type, client_key="doc-1"):
        return self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{
                    "client_key": client_key,
                    "kind": "document",
                    "declared_content_type": content_type,
                    "filename": "notes",
                }],
            },
            files={client_key: FakeUpload(content_type, data)},
        )

    def test_my_data_document_ceiling_is_exactly_ten_million(self):
        self.assertEqual(MY_DATA_POLICY.max_document_bytes, TEN_MB)

    def test_exactly_ten_million_bytes_admits(self):
        adapter = ResumeDocumentAdapter()
        data = b"a" * TEN_MB
        content_type, admitted = adapter.admit(
            FakeUpload("text/plain", data), MY_DATA_POLICY
        )
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(len(admitted), TEN_MB)

    def test_one_byte_over_is_refused_before_parsing(self):
        received = []
        service = build_service(pipeline=lambda *a, **k: received.append(True) or ("x", "extracted", None, False, None))
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{
                    "client_key": "doc-1", "kind": "document",
                    "declared_content_type": "text/plain", "filename": "big.txt",
                }],
            },
            files={"doc-1": FakeUpload("text/plain", b"a" * (TEN_MB + 1))},
        )
        row = receipt["results"][0]
        self.assertEqual(row["outcome"], "failed")
        self.assertEqual(row["code"], "too_large")
        self.assertEqual(received, [])

    def test_selectable_text_becomes_a_proposal_never_a_save(self):
        receipt = self.add_with_document(b"Led the migration.", "text/plain")
        self.assertEqual(receipt["outcome"], "unresolved")
        self.assertEqual(receipt["summary"]["saved"], 0)
        self.assertEqual(len(receipt["proposals"]), 1)

    def test_scan_without_selectable_text_is_truthfully_unsupported(self):
        service = build_service(pipeline=empty_pipeline)
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{
                    "client_key": "doc-1", "kind": "document",
                    "declared_content_type": "application/pdf", "filename": "scan.pdf",
                }],
            },
            files={"doc-1": FakeUpload("application/pdf", b"%PDF-1.4 scan")},
        )
        row = receipt["results"][0]
        self.assertEqual(row["outcome"], "failed")
        message = row["message"]
        self.assertIn("scan", message.lower())
        self.assertNotIn("OCR", message)
        self.assertNotIn("ocr", message.replace("scan", ""))

    def test_unsupported_type_is_refused(self):
        receipt = self.add_with_document(b"GIF89a", "image/png")
        row = receipt["results"][0]
        self.assertEqual(row["outcome"], "failed")
        self.assertEqual(row["code"], "unsupported_type")

    def test_more_than_five_documents_refuses_the_sixth(self):
        files = {}
        attachments = []
        for index in range(6):
            key = f"doc-{index}"
            files[key] = FakeUpload("text/plain", b"note")
            attachments.append({
                "client_key": key, "kind": "document",
                "declared_content_type": "text/plain", "filename": f"{key}.txt",
            })
        receipt = self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "attachments": attachments},
            files=files,
        )
        codes = [row.get("code") for row in receipt["results"]]
        self.assertIn("too_many_documents", codes)
        self.assertEqual(MY_DATA_POLICY.max_documents_per_submission, 5)


class RecordingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.owner = "member-a"

    def test_recording_ceiling_is_180_seconds(self):
        self.assertEqual(MY_DATA_POLICY.max_recording_seconds, 180.0)

    def test_exactly_180_seconds_admits(self):
        transcriber = StubTranscriber()
        service = build_service(transcriber=transcriber)
        upload, payload = recording_payload("audio/wav", wav_bytes(), 180.0)
        result = service.transcribe_recording(self.owner, upload, payload)
        self.assertTrue(result["success"])
        self.assertEqual(result["outcome"], "transcribed")
        self.assertEqual(transcriber.calls[0]["locale"], "en-US")

    def test_over_180_seconds_is_refused(self):
        service = build_service(transcriber=StubTranscriber())
        upload, payload = recording_payload("audio/wav", wav_bytes(), 180.5)
        with self.assertRaises(ResumeIntakeValidationError) as raised:
            service.transcribe_recording(self.owner, upload, payload)
        self.assertIn("longer than this entrance allows", str(raised.exception))

    def test_several_recordings_share_one_draft(self):
        transcriber = StubTranscriber()
        service = build_service(transcriber=transcriber)
        keys = []
        for index in range(3):
            upload = FakeUpload("audio/wav", wav_bytes(bytes([index]) * 64))
            result = service.transcribe_recording(self.owner, upload, {
                "request_id": str(uuid4()),
                "client_key": f"clip-{index}",
                "duration_seconds": 10.0,
            })
            self.assertTrue(result["success"])
            keys.append(result["source_key"])
        self.assertEqual(len(set(keys)), 3)
        self.assertLessEqual(len(keys), MY_DATA_POLICY.max_recordings_per_draft)

    def test_success_keeps_transcript_and_drops_audio(self):
        service = build_service(transcriber=StubTranscriber("I led the migration."))
        upload, payload = recording_payload("audio/wav", wav_bytes(), 12.0)
        result = service.transcribe_recording(self.owner, upload, payload)
        self.assertEqual(result["transcript"], "I led the migration.")
        self.assertFalse(result["receipt"]["audio_retained"])
        snapshot = service.repository.load_owner(self.owner)
        source = snapshot["sources"][result["source_key"]]
        self.assertEqual(source["text"], "I led the migration.")
        self.assertNotIn("audio", {k.lower() for k in source})
        for key, value in source.items():
            self.assertNotIsInstance(value, bytes)

    def test_failure_keeps_private_retryable_recording(self):
        transcriber = StubTranscriber(fail="speech_failed")
        service = build_service(transcriber=transcriber)
        upload, payload = recording_payload("audio/wav", wav_bytes(), 12.0)
        result = service.transcribe_recording(self.owner, upload, payload)
        self.assertFalse(result["success"])
        self.assertEqual(result["outcome"], "failed")
        self.assertTrue(result["input_preserved"])
        self.assertTrue(result["receipt"]["retryable"])
        self.assertEqual(len(transcriber.calls), 1)
        # A retry of the same request never sends the audio twice.
        upload2, payload2 = recording_payload("audio/wav", wav_bytes(), 12.0)
        payload2["request_id"] = payload["request_id"]
        again = service.transcribe_recording(self.owner, upload2, payload2)
        self.assertEqual(len(transcriber.calls), 1)
        self.assertFalse(again["success"])

    def test_empty_transcript_is_not_retryable(self):
        transcriber = StubTranscriber(transcript="   ")
        service = build_service(transcriber=transcriber)
        upload, payload = recording_payload("audio/wav", wav_bytes(), 12.0)
        result = service.transcribe_recording(self.owner, upload, payload)
        self.assertFalse(result["success"])
        self.assertFalse(result["receipt"]["retryable"])


class SourceInspectionTests(unittest.TestCase):
    def test_purged_source_marks_draft_attachment_for_reattach(self):
        service = build_service(transcriber=StubTranscriber("Keepable words."))
        owner = "member-a"
        upload, payload = recording_payload("audio/wav", wav_bytes(), 12.0)
        transcribed = service.transcribe_recording(owner, upload, payload)
        source_key = transcribed["source_key"]
        saved = service.save_draft(owner, {
            "request_id": str(uuid4()),
            "text": "Draft words",
            "attachments": [{
                "client_key": "clip-1", "kind": "recording",
                "duration_seconds": 12.0, "source_key": source_key,
            }],
        })
        self.assertFalse(saved["draft"]["attachments"][0]["needs_reattach"])
        service.purge_source(owner, {
            "request_id": str(uuid4()), "source_key": source_key,
        })
        again = service.save_draft(owner, {
            "request_id": str(uuid4()),
            "text": "Draft words",
            "expected_version": saved["draft"]["version"],
            "attachments": [{
                "client_key": "clip-1", "kind": "recording",
                "duration_seconds": 12.0, "source_key": source_key,
            }],
        })
        self.assertTrue(again["draft"]["attachments"][0]["needs_reattach"])
        self.assertEqual(again["draft"]["text"], "Draft words")


if __name__ == "__main__":
    unittest.main()
