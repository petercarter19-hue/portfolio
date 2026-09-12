"""Bounded voice transcription adapter for the MVP1 C composer.

Reuses the existing Voice Capture validation contract (container signature,
MIME match, byte and duration ceilings) and the existing Speech transcription
client, without activating Capture, Journal or Workshop. Nothing here writes a
canonical record, and no audio is retained: the caller receives a transcript
and a content-free result code.

Audio has its own parametric byte ceiling (``policy.max_recording_bytes``);
it is not the document ceiling. Bytes are read once, bounded, then hashed by
the caller so a request digest can bind to the actual audio rather than to a
filename or duration. The transcription call is injectable so tests can install
a deterministic provider stub that records exactly which bytes it received.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from services.speech_transcription_service import (
    SpeechTranscriptionError,
    speech_transcription_service,
)
from services.voice_capture_service import VoiceCaptureError, validate_audio


_TRANSCRIPTION_MESSAGES = {
    "required": "Choose or record a clip first.",
    "invalid-duration": "That recording length could not be read.",
    "too-long": "That recording is longer than this entrance allows.",
    "too-large": "That recording is larger than this entrance allows.",
    "unsupported": "That audio format is not supported.",
    "speech_unavailable": "Transcription is not available right now. Keep typing and try again.",
    "speech_auth_failed": "Transcription is not available right now. Keep typing and try again.",
    "speech_timeout": "Transcription took too long. Try a shorter recording.",
    "speech_busy": "Transcription is busy right now. Try again in a moment.",
    "speech_failed": "That recording could not be transcribed. Please try again.",
    "speech_malformed": "That recording could not be transcribed. Please try again.",
    "speech_empty": "No speech was detected in that recording.",
}


class RecordingIntakeError(RuntimeError):
    """A pre-admission recording refusal."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.member_message = message or _TRANSCRIPTION_MESSAGES.get(
            code, "That recording could not be read."
        )
        super().__init__(code)


@dataclass(frozen=True)
class TranscriptionResult:
    ok: bool
    transcript: str | None
    code: str | None
    member_message: str
    duration_seconds: float
    content_type: str
    byte_length: int
    sha256: str
    provider_request_id: str | None
    retryable: bool
    audio_retained: bool

    def as_receipt(self) -> dict:
        return {
            "kind": "recording",
            "content_type": self.content_type,
            "byte_length": self.byte_length,
            "sha256": self.sha256,
            "duration_seconds": self.duration_seconds,
            "outcome": "transcribed" if self.ok else "failed",
            "code": self.code,
            "transcript": self.transcript,
            "message": self.member_message,
            "retryable": self.retryable,
            "audio_retained": self.audio_retained,
        }


class _BytesUpload:
    """Minimal upload shape the shared Voice Capture validator expects."""

    def __init__(self, content_type: str, data: bytes) -> None:
        self.mimetype = content_type
        self.stream = io.BytesIO(data)


class ResumeTranscriptionAdapter:
    def __init__(self, service=None, validator=None) -> None:
        self._service = service
        self._validator = validator or validate_audio

    @staticmethod
    def read_bounded(upload, policy) -> bytes:
        """Read at most ``policy.max_recording_bytes`` bytes plus one sentinel."""

        stream = getattr(upload, "stream", None)
        if stream is None:
            raise RecordingIntakeError("required")
        data = stream.read(policy.max_recording_bytes + 1)
        if len(data) > policy.max_recording_bytes:
            raise RecordingIntakeError("too-large")
        if not data:
            raise RecordingIntakeError("required")
        return data

    def admit_bytes(self, content_type, data, duration_seconds, policy):
        """Validate bytes that were already read once, bounded."""

        try:
            return self._validator(
                _BytesUpload(content_type, data),
                duration_seconds,
                max_bytes=policy.max_recording_bytes,
                max_duration_seconds=policy.max_recording_seconds,
            )
        except VoiceCaptureError as error:
            raise RecordingIntakeError(error.code) from error

    def admit(self, upload, duration_seconds, policy):
        """Validate one recording against the entrance policy's own bounds."""

        content_type = str(getattr(upload, "mimetype", "") or "").lower().split(";", 1)[0].strip()
        data = self.read_bounded(upload, policy)
        return self.admit_bytes(content_type, data, duration_seconds, policy)

    def transcribe(self, validated, policy, *, transcribe=None) -> TranscriptionResult:
        """Transcribe admitted audio. Never returns or retains provider payloads."""

        digest = hashlib.sha256(validated.data).hexdigest()
        runner = transcribe or getattr(self._service or speech_transcription_service, "transcribe", None)
        if runner is None:
            return TranscriptionResult(
                ok=False, transcript=None, code="speech_unavailable",
                member_message=_TRANSCRIPTION_MESSAGES["speech_unavailable"],
                duration_seconds=validated.duration_seconds,
                content_type=validated.content_type, byte_length=validated.byte_length,
                sha256=digest, provider_request_id=None, retryable=True,
                audio_retained=not policy.cleanup_audio_after_transcription,
            )
        try:
            payload = runner(validated.data, validated.content_type, locale=validated.locale)
        except SpeechTranscriptionError as error:
            code = error.code
            return TranscriptionResult(
                ok=False, transcript=None, code=code,
                member_message=_TRANSCRIPTION_MESSAGES.get(code, _TRANSCRIPTION_MESSAGES["speech_failed"]),
                duration_seconds=validated.duration_seconds,
                content_type=validated.content_type, byte_length=validated.byte_length,
                sha256=digest, provider_request_id=None,
                retryable=code != "speech_empty",
                audio_retained=False,
            )
        except Exception:  # noqa: BLE001 - provider-neutral boundary
            return TranscriptionResult(
                ok=False, transcript=None, code="speech_unavailable",
                member_message=_TRANSCRIPTION_MESSAGES["speech_unavailable"],
                duration_seconds=validated.duration_seconds,
                content_type=validated.content_type, byte_length=validated.byte_length,
                sha256=digest, provider_request_id=None, retryable=True,
                audio_retained=False,
            )
        transcript = (payload or {}).get("provider_transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            return TranscriptionResult(
                ok=False, transcript=None, code="speech_empty",
                member_message=_TRANSCRIPTION_MESSAGES["speech_empty"],
                duration_seconds=validated.duration_seconds,
                content_type=validated.content_type, byte_length=validated.byte_length,
                sha256=digest, provider_request_id=None, retryable=False,
                audio_retained=False,
            )
        return TranscriptionResult(
            ok=True, transcript=transcript.strip(), code=None, member_message="Transcribed.",
            duration_seconds=(payload or {}).get("duration_seconds") or validated.duration_seconds,
            content_type=validated.content_type, byte_length=validated.byte_length,
            sha256=digest, provider_request_id=(payload or {}).get("provider_request_id"),
            retryable=False,
            audio_retained=not policy.cleanup_audio_after_transcription,
        )


resume_transcription_adapter = ResumeTranscriptionAdapter()
