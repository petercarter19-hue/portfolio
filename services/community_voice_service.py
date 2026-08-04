"""Request-only Speech transcription for the bounded Community Voice slice."""

from __future__ import annotations

import math
import unicodedata

from services.community_contracts import (
    CONTRIBUTION_BODY_MAX,
    POST_BODY_MAX,
    utf16_length,
)
from services.speech_transcription_service import speech_transcription_service
from services.voice_capture_service import (
    MAX_VOICE_DURATION_SECONDS,
    VOICE_LOCALE,
    VoiceCaptureError,
    validate_audio,
)


class CommunityVoiceError(RuntimeError):
    """A stable, safe outcome for a request-only Community transcription."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CommunityVoiceService:
    """Validate one transient recording and return only its review proposal.

    This service deliberately owns no database, Blob, Capture, or command
    dependency. The validated audio bytes exist only for the synchronous
    provider call and are released with the request afterwards.
    """

    _LIMITS = {
        "post": POST_BODY_MAX,
        "contribution": CONTRIBUTION_BODY_MAX,
    }

    def __init__(self, speech=None):
        self.speech = speech or speech_transcription_service

    @classmethod
    def _context_limit(cls, composer_context):
        if composer_context not in cls._LIMITS:
            raise CommunityVoiceError("invalid-context")
        return cls._LIMITS[composer_context]

    @staticmethod
    def _normalized_text(value):
        if not isinstance(value, str):
            raise CommunityVoiceError("transcript-empty")
        text = unicodedata.normalize("NFC", value).strip()
        if not text:
            raise CommunityVoiceError("transcript-empty")
        return text

    def transcribe(self, upload, duration_seconds, composer_context):
        maximum = self._context_limit(composer_context)
        try:
            audio = validate_audio(upload, duration_seconds)
        except VoiceCaptureError as error:
            raise CommunityVoiceError(
                {
                    "required": "recording-required",
                    "invalid-duration": "invalid-duration",
                    "too-long": "recording-too-long",
                    "too-large": "recording-too-large",
                    "unsupported": "unsupported-recording",
                }.get(error.code, "unsupported-recording")
            ) from error

        try:
            result = self.speech.transcribe(
                audio.data, audio.content_type, VOICE_LOCALE
            )
        except Exception as error:
            # Provider detail, identifiers, bytes, and payloads never cross
            # this request-only boundary.
            raise CommunityVoiceError("transcription-unavailable") from error

        if not isinstance(result, dict) or not isinstance(
            result.get("provider_transcript"), str
        ):
            raise CommunityVoiceError("transcription-unavailable")
        provider_duration = result.get("duration_seconds")
        try:
            provider_duration = float(provider_duration)
        except (TypeError, ValueError):
            raise CommunityVoiceError("transcription-unavailable")
        if not math.isfinite(provider_duration) or provider_duration < 0:
            raise CommunityVoiceError("transcription-unavailable")
        if provider_duration > MAX_VOICE_DURATION_SECONDS:
            raise CommunityVoiceError("recording-too-long")
        text = self._normalized_text(result["provider_transcript"])
        if utf16_length(text) > maximum:
            raise CommunityVoiceError("transcript-too-long")
        return {
            "text": text,
            "composer_context": composer_context,
            "max_utf16_code_units": maximum,
        }


community_voice_service = CommunityVoiceService()
