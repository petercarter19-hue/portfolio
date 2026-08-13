from __future__ import annotations
from dataclasses import replace
import unittest

from services.profile_core_service import ProfileNotFound
from services.profile_voice_projection_service import ProfileVoiceProjection, ProfileVoiceProjectionService


class Reader:
    def __init__(self, value): self.value = value
    def get_exact_projection(self, **kwargs): return self.value


class ProfileVoiceProjectionTests(unittest.TestCase):
    def test_member_approved_transcript_and_audio_can_resolve(self):
        value = ProfileVoiceProjection(
            "voiceProj_123", "ownerAlpha_123", "voice:v2", "public",
            "Why systems thinking matters", None, 134,
            "/profiles/avery/voice/voiceProj_123/audio", "Systems help us see patterns.", True,
        )
        self.assertEqual(ProfileVoiceProjectionService(Reader(value)).resolve(
            owner_key="ownerAlpha_123", projection_key="voiceProj_123",
            projection_version="voice:v2", audience="public"), value)

    def test_unapproved_transcript_cannot_claim_approval(self):
        value = ProfileVoiceProjection(
            "voiceProj_123", "ownerAlpha_123", "voice:v2", "public", "Reflection",
            None, 20, None, None, True,
        )
        with self.assertRaises(ProfileNotFound):
            ProfileVoiceProjectionService(Reader(value)).resolve(
                owner_key="ownerAlpha_123", projection_key="voiceProj_123",
                projection_version="voice:v2", audience="public")

    def test_unapproved_transcript_content_is_never_returned(self):
        value = ProfileVoiceProjection(
            "voiceProj_123", "ownerAlpha_123", "voice:v2", "public", "Reflection",
            None, 20, "/profiles/avery/voice/voiceProj_123/audio", "unapproved words", False,
        )
        with self.assertRaises(ProfileNotFound):
            ProfileVoiceProjectionService(Reader(value)).resolve(
                owner_key="ownerAlpha_123", projection_key="voiceProj_123",
                projection_version="voice:v2", audience="public")

    def test_hostile_provider_field_types_fail_neutrally(self):
        valid = ProfileVoiceProjection(
            "voiceProj_123", "ownerAlpha_123", "voice:v2", "public", "Reflection",
            None, 20, "/profiles/avery/voice/voiceProj_123/audio", None, False,
        )
        for field, hostile in (
            ("owner_key", None), ("projection_key", 7),
            ("projection_version", []), ("audience", {"public"}),
            ("title", object()), ("duration_seconds", True),
            ("transcript_approved", "yes"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ProfileNotFound):
                    ProfileVoiceProjectionService(Reader(replace(valid, **{field: hostile}))).resolve(
                        owner_key="ownerAlpha_123", projection_key="voiceProj_123",
                        projection_version="voice:v2", audience="public")


if __name__ == "__main__": unittest.main()
