from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_voice_projection_provider import (
    PrivateVoiceAudio,
    ProfileVoiceProjectionProvider,
    VoiceAudienceDecision,
    VoiceProjectionGrant,
    VoiceSourceSnapshot,
)


AUDIO_BYTES = b"retained-member-voice-audio"
AUDIO_DIGEST = hashlib.sha256(AUDIO_BYTES).digest()
_DEFAULT = object()


def grant(**changes):
    value = VoiceProjectionGrant(
        projection_key="voice-id-00000000",
        owner_key="ownerAlpha_123",
        projection_version="voice:v4",
        audience="public",
        source_key="voiceSource_123",
        source_version="voice:v9",
        source_sha256_digest=AUDIO_DIGEST,
        capture_revision="capture:v6",
        published=True,
        revoked=False,
        where_used=True,
        title="Why systems thinking matters",
        context="A short reflection.",
        duration_seconds=73,
        audio_path="/profiles/avery/voice/voice-id-00000000/audio",
        approved_transcript="Systems help us see patterns.",
        transcript_approved=True,
    )
    return replace(value, **changes)


def decision(**changes):
    value = VoiceAudienceDecision(
        owner_key="ownerAlpha_123",
        viewer_key=None,
        audience="public",
        authorization_epoch="access:v4",
        authorized=True,
        owner_blocked_viewer=False,
        viewer_blocked_owner=False,
    )
    return replace(value, **changes)


def source(**changes):
    value = VoiceSourceSnapshot(
        owner_key="ownerAlpha_123",
        source_key="voiceSource_123",
        source_version="voice:v9",
        source_sha256_digest=AUDIO_DIGEST,
        capture_revision="capture:v6",
        lifecycle_state="confirmed",
        current=True,
        deleted=False,
        audio_available=True,
        content_type="audio/webm",
        byte_length=len(AUDIO_BYTES),
        duration_seconds=73,
    )
    return replace(value, **changes)


def audio(**changes):
    value = PrivateVoiceAudio(
        body=AUDIO_BYTES,
        content_type="audio/webm",
        byte_length=len(AUDIO_BYTES),
        sha256_digest=AUDIO_DIGEST,
    )
    return replace(value, **changes)


class GrantPort:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def get_exact_grant(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class AudiencePort:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def authorize(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class SourcePort:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def get_exact_source(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class AudioPort:
    def __init__(self, value, on_open=None):
        self.value = value
        self.on_open = on_open
        self.calls = []

    def open_audio(self, **kwargs):
        self.calls.append(kwargs)
        if self.on_open:
            self.on_open()
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def provider(
    grant_value=_DEFAULT,
    decision_value=_DEFAULT,
    source_value=_DEFAULT,
    audio_value=_DEFAULT,
    on_open=None,
):
    grants = GrantPort(grant() if grant_value is _DEFAULT else grant_value)
    audiences = AudiencePort(
        decision() if decision_value is _DEFAULT else decision_value
    )
    sources = SourcePort(source() if source_value is _DEFAULT else source_value)
    audio_port = AudioPort(audio() if audio_value is _DEFAULT else audio_value, on_open)
    return (
        ProfileVoiceProjectionProvider(
            grants=grants,
            audiences=audiences,
            sources=sources,
            audio=audio_port,
        ),
        grants,
        audiences,
        sources,
        audio_port,
    )


def resolve(value, *, audience="public", viewer_key=None):
    return value.resolve(
        owner_key="ownerAlpha_123",
        viewer_key=viewer_key,
        projection_key="voice-id-00000000",
        projection_version="voice:v4",
        audience=audience,
    )


class ProfileVoiceProjectionProviderTests(unittest.TestCase):
    def test_exact_audio_and_member_approved_transcript_are_bound_and_returned(self):
        value, grants, audiences, sources, audio_port = provider()

        result = resolve(value)

        self.assertEqual(result.audio_body, AUDIO_BYTES)
        self.assertEqual(result.source_sha256_digest, AUDIO_DIGEST)
        self.assertEqual(result.projection.transcript, "Systems help us see patterns.")
        self.assertTrue(result.projection.transcript_approved)
        self.assertTrue(result.transcript_available)
        self.assertFalse(result.autoplay)
        self.assertEqual(result.projection.duration_seconds, 73)
        self.assertEqual(len(grants.calls), 2)
        self.assertEqual(len(audiences.calls), 2)
        self.assertEqual(len(sources.calls), 2)
        self.assertEqual(
            audio_port.calls,
            [
                {
                    "owner_key": "ownerAlpha_123",
                    "source_key": "voiceSource_123",
                    "source_version": "voice:v9",
                    "expected_sha256_digest": AUDIO_DIGEST,
                    "expected_byte_length": len(AUDIO_BYTES),
                }
            ],
        )
        self.assertNotIn("voiceSource_123", repr(result))
        self.assertNotIn(AUDIO_BYTES.decode("ascii"), repr(result))
        self.assertNotIn("Systems help us see patterns.", repr(result))

    def test_approved_transcript_without_audio_is_truthful_and_never_opens_storage(self):
        value, _, _, _, audio_port = provider(
            grant_value=grant(audio_path=None),
            source_value=source(
                audio_available=False, content_type=None, byte_length=None
            ),
        )

        result = resolve(value)

        self.assertIsNone(result.audio_body)
        self.assertIsNone(result.content_type)
        self.assertIsNone(result.byte_length)
        self.assertIsNone(result.projection.audio_path)
        self.assertTrue(result.transcript_available)
        self.assertEqual(audio_port.calls, [])

    def test_audio_without_approved_transcript_is_explicitly_unavailable(self):
        value, _, _, _, audio_port = provider(
            grant_value=grant(
                approved_transcript=None,
                transcript_approved=False,
            )
        )

        result = resolve(value)

        self.assertEqual(result.audio_body, AUDIO_BYTES)
        self.assertIsNone(result.projection.transcript)
        self.assertFalse(result.projection.transcript_approved)
        self.assertFalse(result.transcript_available)
        self.assertFalse(result.autoplay)
        self.assertEqual(len(audio_port.calls), 1)

    def test_provider_transcript_attempt_cannot_be_mislabeled_as_approved(self):
        value, _, audiences, sources, audio_port = provider(
            grant_value=grant(
                approved_transcript="unreviewed provider attempt",
                transcript_approved=False,
            )
        )
        with self.assertRaises(ProfileNotFound):
            resolve(value)
        self.assertEqual(audiences.calls, [])
        self.assertEqual(sources.calls, [])
        self.assertEqual(audio_port.calls, [])

    def test_connections_are_exact_and_never_fall_back_to_public(self):
        value, _, audiences, sources, audio_port = provider()
        with self.assertRaises(ProfileNotFound):
            resolve(value, audience="connections", viewer_key="viewerBravo_456")
        self.assertEqual(audiences.calls, [])
        self.assertEqual(sources.calls, [])
        self.assertEqual(audio_port.calls, [])

        value, _, _, _, audio_port = provider(
            grant_value=grant(audience="connections"),
            decision_value=decision(
                viewer_key="viewerBravo_456", audience="connections"
            ),
        )
        result = resolve(
            value, audience="connections", viewer_key="viewerBravo_456"
        )
        self.assertEqual(result.projection.audience, "connections")
        self.assertEqual(len(audio_port.calls), 1)

    def test_invalid_grants_fail_before_relationship_source_or_storage(self):
        cases = (
            None,
            object(),
            grant(owner_key="owner-id-11111111"),
            grant(projection_key="voice-id-11111111"),
            grant(projection_version="voice:v3"),
            grant(audience="connections"),
            grant(source_sha256_digest=b"short"),
            grant(capture_revision=""),
            grant(published=False),
            grant(revoked=True),
            grant(where_used=False),
            grant(duration_seconds=True),
            grant(audio_path="//storage.example/private"),
            grant(audio_path=None, approved_transcript=None, transcript_approved=False),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, audiences, sources, audio_port = provider(
                    grant_value=invalid
                )
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(audiences.calls, [])
                self.assertEqual(sources.calls, [])
                self.assertEqual(audio_port.calls, [])

    def test_unrelated_and_both_block_directions_stop_before_source_and_audio(self):
        cases = (
            decision(authorized=False),
            decision(owner_blocked_viewer=True),
            decision(viewer_blocked_owner=True),
            decision(owner_key="owner-id-11111111"),
            decision(viewer_key="viewerBravo_456"),
            decision(audience="connections"),
        )
        for denied in cases:
            with self.subTest(denied=denied):
                value, _, _, sources, audio_port = provider(decision_value=denied)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(sources.calls, [])
                self.assertEqual(audio_port.calls, [])

    def test_stale_deleted_cross_owner_or_wrong_capture_source_never_opens(self):
        cases = (
            None,
            object(),
            source(owner_key="owner-id-11111111"),
            source(source_key="voice-id-11111111"),
            source(source_version="voice:v8"),
            source(source_sha256_digest=hashlib.sha256(b"other").digest()),
            source(capture_revision="capture:v5"),
            source(lifecycle_state="needs_review"),
            source(current=False),
            source(deleted=True),
            source(content_type="text/plain"),
            source(content_type=[]),
            source(byte_length=True),
            source(duration_seconds=72),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, _, _, audio_port = provider(source_value=invalid)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(audio_port.calls, [])

    def test_open_races_revalidate_publication_block_capture_and_deletion(self):
        mutations = (
            "unpublished",
            "revoked",
            "where_used",
            "block",
            "source_version",
            "capture_revision",
            "deleted",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                value, grants, audiences, sources, audio_port = provider()

                def mutate():
                    if mutation == "unpublished":
                        grants.value = replace(grants.value, published=False)
                    elif mutation == "revoked":
                        grants.value = replace(grants.value, revoked=True)
                    elif mutation == "where_used":
                        grants.value = replace(grants.value, where_used=False)
                    elif mutation == "block":
                        audiences.value = replace(
                            audiences.value, viewer_blocked_owner=True
                        )
                    elif mutation == "source_version":
                        sources.value = replace(sources.value, source_version="voice:v10")
                    elif mutation == "capture_revision":
                        sources.value = replace(
                            sources.value, capture_revision="capture:v7"
                        )
                    else:
                        sources.value = replace(sources.value, deleted=True)

                audio_port.on_open = mutate
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(len(audio_port.calls), 1)

    def test_audio_length_digest_and_content_type_are_verified(self):
        cases = (
            None,
            object(),
            audio(body=b"tampered"),
            audio(content_type="audio/ogg"),
            audio(byte_length=len(AUDIO_BYTES) + 1),
            audio(sha256_digest=hashlib.sha256(b"other").digest()),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, _, _, audio_port = provider(audio_value=invalid)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(len(audio_port.calls), 1)

    def test_dependency_failures_are_stable_and_content_free(self):
        cases = (
            {"grant_value": RuntimeError("source-key-private")},
            {"decision_value": RuntimeError("relationship-private")},
            {"source_value": RuntimeError("provider-transcript-private")},
            {"audio_value": RuntimeError("blob-locator-private")},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                value, *_ = provider(**kwargs)
                with self.assertRaises(ProfileUnavailableError) as raised:
                    resolve(value)
                self.assertEqual(
                    str(raised.exception), "Voice projection dependency unavailable."
                )
                self.assertNotIn("private", str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)
                self.assertTrue(raised.exception.__suppress_context__)

    def test_retry_is_idempotent_and_terminal_delete_does_not_resurrect(self):
        value, _, _, sources, audio_port = provider()
        first = resolve(value)
        second = resolve(value)
        self.assertEqual(first, second)
        self.assertEqual(len(audio_port.calls), 2)

        sources.value = replace(sources.value, deleted=True)
        with self.assertRaises(ProfileNotFound):
            resolve(value)
        self.assertEqual(len(audio_port.calls), 2)

    def test_malformed_requests_fail_without_touching_any_port(self):
        value, grants, audiences, sources, audio_port = provider()
        for field, bad in (
            ("owner_key", None),
            ("viewer_key", object()),
            ("projection_key", 7),
            ("projection_version", []),
            ("audience", "friends"),
            ("audience", "connections"),
        ):
            args = {
                "owner_key": "ownerAlpha_123",
                "viewer_key": None,
                "projection_key": "voice-id-00000000",
                "projection_version": "voice:v4",
                "audience": "public",
            }
            args[field] = bad
            with self.subTest(field=field, bad=bad):
                with self.assertRaises(ProfileNotFound):
                    value.resolve(**args)
        self.assertEqual(grants.calls, [])
        self.assertEqual(audiences.calls, [])
        self.assertEqual(sources.calls, [])
        self.assertEqual(audio_port.calls, [])

    def test_module_has_no_sql_speech_identity_or_runtime_registration(self):
        provider_source = Path(
            "services/profile_voice_projection_provider.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("database_service", provider_source)
        self.assertNotIn("usp_", provider_source)
        self.assertNotIn("speech_transcription_service", provider_source)
        self.assertNotIn("provider_transcript", provider_source)
        self.assertNotIn("voice_capture_service", provider_source)


if __name__ == "__main__":
    unittest.main()
