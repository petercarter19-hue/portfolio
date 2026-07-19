import unittest
from unittest.mock import Mock

import requests
from azure.core.exceptions import ResourceNotFoundError

from services.media_storage_service import MediaStorageError, MediaStorageService
from services.speech_transcription_service import (
    SPEECH_TOKEN_SCOPE,
    SpeechTranscriptionError,
    SpeechTranscriptionService,
)


BLOB_NAME = "voice/v1/ab/ab0123456789abcdef0123456789abcd.webm"


class FakeDownload:
    def readall(self):
        return b"synthetic-audio"


class FakeContainer:
    def __init__(self):
        self.upload_calls = []
        self.deleted = []
        self.absent = False

    def upload_blob(self, **kwargs):
        self.upload_calls.append(kwargs)

    def download_blob(self, name):
        self.downloaded = name
        return FakeDownload()

    def delete_blob(self, name, **kwargs):
        if self.absent:
            raise ResourceNotFoundError("absent")
        self.deleted.append((name, kwargs))

    def get_blob_client(self, name):
        client = Mock()
        client.exists.return_value = not self.absent
        return client


class MediaStorageAdapterTests(unittest.TestCase):
    def setUp(self):
        self.container = FakeContainer()
        self.service = MediaStorageService(
            account_url="https://synthetic.blob.core.windows.net",
            container_name="private-voice",
        )
        self.service._container_client = self.container

    def test_upload_has_no_metadata_sas_or_overwrite(self):
        self.service.upload(BLOB_NAME, b"synthetic-audio", "audio/webm")

        call = self.container.upload_calls[0]
        self.assertEqual(call["name"], BLOB_NAME)
        self.assertIsNone(call["metadata"])
        self.assertFalse(call["overwrite"])
        self.assertNotIn("credential", call)

    def test_download_delete_and_already_absent_are_deterministic(self):
        self.assertEqual(self.service.download(BLOB_NAME), b"synthetic-audio")
        self.service.delete(BLOB_NAME)
        self.container.absent = True
        self.service.delete(BLOB_NAME)
        self.assertFalse(self.service.exists(BLOB_NAME))

    def test_rejects_identity_or_member_text_in_untrusted_path(self):
        with self.assertRaises(ValueError):
            self.service.upload("voice/member@example.test.webm", b"x", "audio/webm")


class FakeCredential:
    def __init__(self):
        self.scopes = []

    def get_token(self, scope):
        self.scopes.append(scope)
        return Mock(token="opaque-token")


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class SpeechAdapterTests(unittest.TestCase):
    def setUp(self):
        self.credential = FakeCredential()
        self.session = Mock()
        self.service = SpeechTranscriptionService(
            endpoint="https://synthetic.cognitiveservices.azure.com",
            credential=self.credential,
            session=self.session,
        )

    def test_success_uses_entra_scope_timeout_and_normalizes_result(self):
        self.session.post.return_value = FakeResponse(
            payload={
                "combinedPhrases": [{"text": "Synthetic phrase."}],
                "durationMilliseconds": 1250,
            },
            headers={"apim-request-id": "opaque-request"},
        )

        result = self.service.transcribe(b"audio", "audio/webm")

        self.assertEqual(self.credential.scopes, [SPEECH_TOKEN_SCOPE])
        self.assertEqual(result["provider_transcript"], "Synthetic phrase.")
        self.assertEqual(result["duration_seconds"], 1.25)
        call = self.session.post.call_args
        self.assertEqual(call.kwargs["params"]["api-version"], "2025-10-15")
        self.assertEqual(call.kwargs["timeout"][0], 5)

    def test_timeout_is_normalized_without_provider_payload(self):
        self.session.post.side_effect = requests.Timeout("PRIVATE RESPONSE")

        with self.assertRaisesRegex(SpeechTranscriptionError, "speech_timeout") as raised:
            self.service.transcribe(b"audio", "audio/webm")

        self.assertNotIn("PRIVATE", str(raised.exception))

    def test_malformed_empty_and_provider_errors_are_safe(self):
        cases = (
            (FakeResponse(payload=ValueError("PRIVATE")), "speech_malformed"),
            (FakeResponse(payload={"combinedPhrases": []}), "speech_empty"),
            (FakeResponse(status=403, payload={"private": "payload"}), "speech_auth_failed"),
            (FakeResponse(status=429, payload={"private": "payload"}), "speech_busy"),
            (FakeResponse(status=500, payload={"private": "payload"}), "speech_failed"),
        )
        for response, expected in cases:
            with self.subTest(expected=expected):
                self.session.post.return_value = response
                with self.assertRaisesRegex(SpeechTranscriptionError, expected) as raised:
                    self.service.transcribe(b"audio", "audio/webm")
                self.assertNotIn("payload", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
