"""Workshop voice input — PS-WORKSHOP-001 W2d.

One short recording in, one transcript string out. Nothing else.

**What happens to the audio, precisely.** The recording arrives as a
multipart upload, is validated, is held in one local ``bytes`` value for the
length of a single HTTPS request to Azure Speech fast transcription, and is
then unreferenced when this function returns. It is never written to disk,
never uploaded to Blob storage, never inserted into SQL, and never placed in
the session cookie. This module imports no storage or database client at
all, which is the enforceable version of that claim — ``test_workshop_voice``
asserts both the absence of those collaborators and that a transcription
performed through the real code path writes no file anywhere under the Flask
instance path.

Two honest limits on that claim, stated rather than glossed:

  1. The bytes exist in this process's memory while the request runs, and
     they are inside the outbound TLS request to Microsoft. Azure Speech's
     own retention is Microsoft's policy, not PeerSlate's — this module
     controls what PeerSlate keeps, which is the transcript only, and even
     the transcript is only returned to the caller, not stored here.
  2. WSGI servers may spool a large multipart body to a temporary file
     before the view sees it. That is Werkzeug's own request parsing, not a
     PeerSlate write, and it is bounded by the per-endpoint content-length
     cap the route sets. It is named here because "no audio is retained"
     would otherwise be a slightly larger promise than the code delivers.

**Why this reuses the released path rather than the browser's.** Azure
Speech (``services/speech_transcription_service.py``, PS-VOICE-001) is
already the product's transcription provider, so there is exactly one
server-side transcription implementation. ``static/js/dictation.js`` is a
different thing — browser-local Web Speech recognition for Interview Studio,
which streams text in live and therefore has no discrete "transcribing" step
and no transcript-before-submit moment. R17's six states are a
record-then-transcribe design (state 3 is literally a spinner labelled
"Transcribing…", and state 4 is the transcript sitting editable BEFORE it
becomes the member's words), so Workshop follows the Azure path. The two
coexist deliberately; neither is a duplicate of the other.

**Never canonical.** This returns a proposal. The transcript is handed to
the browser, inserted into a field the member can edit, and becomes their
words only when they submit that field themselves. This module saves,
publishes, sends, and deletes nothing.
"""

import os

from services.speech_transcription_service import (
    SpeechTranscriptionError,
    speech_transcription_service,
)
from services.voice_capture_service import VoiceCaptureError, validate_audio


# Workshop's own bounds, much tighter than owner Voice Capture's 3-minute /
# 20 MB draft. A Workshop dictation is one answer to one question, not a
# recorded memo, and every byte accepted here is billable audio-seconds at
# Azure and a larger body to accept from an anonymous public caller.
MAX_WORKSHOP_VOICE_SECONDS = int(
    os.getenv("WORKSHOP_VOICE_MAX_SECONDS", "90")
)
MAX_WORKSHOP_VOICE_BYTES = int(
    os.getenv("WORKSHOP_VOICE_MAX_BYTES", str(4 * 1024 * 1024))
)

# Longest transcript returned to the browser. Azure will not produce more
# than 90 seconds of speech, so this is a defence against a malformed or
# hostile provider response, not a normal limit a member can reach.
MAX_TRANSCRIPT_CHARS = 4000


class WorkshopVoiceError(RuntimeError):
    """A stable, member-safe Workshop voice outcome code."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


# One honest sentence per failure, written for the member rather than the
# log. R17 state 5's copy ("We couldn't transcribe that recording.") is the
# fallback; the specific ones say what the member can actually do about it.
# None of them blame the member, and every one of them is compatible with
# the field's existing text still being there — because it always is.
VOICE_ERROR_MESSAGES = {
    "required": "No recording arrived. You can try again, or keep typing.",
    "invalid-duration": "That recording could not be read. You can try again, or keep typing.",
    "too-long": (
        "That recording is longer than "
        f"{MAX_WORKSHOP_VOICE_SECONDS} seconds. Record a shorter piece, or keep typing."
    ),
    "too-large": "That recording is too large to send. Record a shorter piece, or keep typing.",
    "unsupported": "This browser's recording format isn't supported. You can keep typing.",
    "speech-empty": "We didn't hear any speech in that recording. You can try again, or keep typing.",
    "speech-unavailable": "Voice input is unavailable right now. You can try again later, or keep typing.",
    "transcription-failed": "We couldn't transcribe that recording. You can try again, or keep typing.",
}

DEFAULT_VOICE_ERROR_MESSAGE = VOICE_ERROR_MESSAGES["transcription-failed"]

# Provider failure codes that mean "nothing was heard" rather than "the
# service broke". They deserve different copy and a different status code:
# an empty recording is a 400-shaped fact about the upload, not a 503-shaped
# fact about Azure.
_EMPTY_SPEECH_CODES = {"speech_empty"}
_UNAVAILABLE_SPEECH_CODES = {
    "speech_unavailable",
    "speech_auth_failed",
    "speech_busy",
    "speech_timeout",
    "unsupported_locale",
}


def message_for(code):
    """The member-facing sentence for one outcome code."""
    return VOICE_ERROR_MESSAGES.get(code, DEFAULT_VOICE_ERROR_MESSAGE)


def transcribe_recording(upload, duration_seconds, speech=None):
    """Validate one recording, transcribe it, and return the transcript text.

    Raises ``WorkshopVoiceError`` with a code from ``VOICE_ERROR_MESSAGES``
    for every failure. It returns a plain string and nothing else — there is
    no draft, no key, no row, and no state for a caller to clean up, which is
    the whole reason this is a separate module from voice_capture_service
    rather than another method on it.
    """
    try:
        audio = validate_audio(
            upload,
            duration_seconds,
            max_bytes=MAX_WORKSHOP_VOICE_BYTES,
            max_duration_seconds=MAX_WORKSHOP_VOICE_SECONDS,
        )
    except VoiceCaptureError as error:
        raise WorkshopVoiceError(error.code) from error

    provider = speech or speech_transcription_service
    try:
        result = provider.transcribe(audio.data, audio.content_type, audio.locale)
    except SpeechTranscriptionError as error:
        if error.code in _EMPTY_SPEECH_CODES:
            raise WorkshopVoiceError("speech-empty") from error
        if error.code in _UNAVAILABLE_SPEECH_CODES:
            raise WorkshopVoiceError("speech-unavailable") from error
        raise WorkshopVoiceError("transcription-failed") from error

    transcript = str((result or {}).get("provider_transcript") or "").strip()
    if not transcript:
        # A 2xx with no usable text is the same fact for the member as
        # speech_empty, and must not become an empty "successful" transcript
        # that silently replaces nothing with nothing.
        raise WorkshopVoiceError("speech-empty")
    return transcript[:MAX_TRANSCRIPT_CHARS]
