"""Azure Speech fast-transcription adapter using Microsoft Entra authentication."""

import os

import requests


SPEECH_TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


class SpeechTranscriptionError(RuntimeError):
    """A normalized provider failure with no transcript or response payload."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class SpeechTranscriptionService:
    """Synchronously transcribe one short, validated recording."""

    def __init__(
        self,
        endpoint=None,
        api_version=None,
        credential=None,
        session=None,
        timeout_seconds=45,
    ):
        self.endpoint = (endpoint or os.getenv("VOICE_SPEECH_ENDPOINT", "")).rstrip(
            "/"
        )
        self.api_version = api_version or os.getenv(
            "VOICE_SPEECH_API_VERSION", "2025-10-15"
        )
        self._credential = credential
        self._session = session or requests.Session()
        self.timeout_seconds = timeout_seconds

    def _access_token(self):
        if not self.endpoint.startswith("https://"):
            raise SpeechTranscriptionError("speech_unavailable")
        try:
            from azure.identity import DefaultAzureCredential

            credential = self._credential or DefaultAzureCredential()
            return credential.get_token(SPEECH_TOKEN_SCOPE).token
        except Exception as error:
            raise SpeechTranscriptionError("speech_auth_failed") from error

    @staticmethod
    def _duration_seconds(payload):
        duration_ms = payload.get("durationMilliseconds")
        if isinstance(duration_ms, (int, float)):
            return float(duration_ms) / 1000.0
        duration = payload.get("duration")
        if isinstance(duration, (int, float)):
            return float(duration)
        return None

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        """Call fast transcription without logging or returning provider payloads."""
        if locale != "en-US":
            raise SpeechTranscriptionError("unsupported_locale")
        url = f"{self.endpoint}/speechtotext/transcriptions:transcribe"
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        definition = '{"locales":["en-US"]}'
        try:
            response = self._session.post(
                url,
                params={"api-version": self.api_version},
                headers=headers,
                files={
                    "audio": ("recording", audio_bytes, content_type),
                    "definition": (None, definition, "application/json"),
                },
                timeout=(5, self.timeout_seconds),
            )
        except requests.Timeout as error:
            raise SpeechTranscriptionError("speech_timeout") from error
        except requests.RequestException as error:
            raise SpeechTranscriptionError("speech_unavailable") from error

        if response.status_code in {401, 403}:
            raise SpeechTranscriptionError("speech_auth_failed")
        if response.status_code == 429:
            raise SpeechTranscriptionError("speech_busy")
        if response.status_code < 200 or response.status_code >= 300:
            raise SpeechTranscriptionError("speech_failed")

        try:
            payload = response.json()
            phrases = payload.get("combinedPhrases") or []
            transcript = " ".join(
                str(phrase.get("text") or "").strip()
                for phrase in phrases
                if isinstance(phrase, dict) and phrase.get("text")
            ).strip()
        except (TypeError, ValueError) as error:
            raise SpeechTranscriptionError("speech_malformed") from error
        if not transcript:
            raise SpeechTranscriptionError("speech_empty")

        return {
            "provider_transcript": transcript,
            "provider_request_id": response.headers.get("apim-request-id")
            or response.headers.get("x-ms-request-id"),
            "duration_seconds": self._duration_seconds(payload),
        }


speech_transcription_service = SpeechTranscriptionService()
