from __future__ import annotations

from dataclasses import replace
import unittest

from services.profile_core_service import ProfileNotFound
from services.profile_media_projection_service import (
    ProfileMediaProjection,
    ProfileMediaProjectionService,
)


class Reader:
    def __init__(self, value): self.value = value
    def get_exact_projection(self, **kwargs): return self.value


class ProfileMediaProjectionTests(unittest.TestCase):
    def test_exact_authorized_derivative_resolves_without_source_metadata(self):
        value = ProfileMediaProjection(
            "mediaProj_123", "ownerAlpha_123", "media:v3", "public", "album",
            "Life lately", "Travel and quiet moments.",
            "/profiles/avery/media/mediaProj_123/cover", "Sunset over a lake", item_count=32,
        )
        self.assertEqual(
            ProfileMediaProjectionService(Reader(value)).resolve(
                owner_key="ownerAlpha_123", projection_key="mediaProj_123",
                projection_version="media:v3", audience="public",
            ), value,
        )

    def test_cross_owner_and_external_derivative_fail_neutrally(self):
        for value in (
            ProfileMediaProjection("mediaProj_123", "ownerBravo_456", "media:v3", "public", "photo", "x", None, "/media/x", "x"),
            ProfileMediaProjection("mediaProj_123", "ownerAlpha_123", "media:v3", "public", "photo", "x", None, "//evil.example/x", "x"),
        ):
            with self.subTest(value=value):
                with self.assertRaises(ProfileNotFound):
                    ProfileMediaProjectionService(Reader(value)).resolve(
                        owner_key="ownerAlpha_123", projection_key="mediaProj_123",
                        projection_version="media:v3", audience="public",
                    )

    def test_hostile_provider_field_types_fail_neutrally(self):
        valid = ProfileMediaProjection(
            "mediaProj_123", "ownerAlpha_123", "media:v3", "public", "photo",
            "Title", None, "/media/item", "Useful description",
        )
        for field, hostile in (
            ("owner_key", None), ("projection_key", 7),
            ("projection_version", ["media:v3"]), ("audience", {"public"}),
            ("kind", 1), ("title", []), ("alt_text", object()),
            ("item_count", True), ("duration_seconds", False),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ProfileNotFound):
                    ProfileMediaProjectionService(Reader(replace(valid, **{field: hostile}))).resolve(
                        owner_key="ownerAlpha_123", projection_key="mediaProj_123",
                        projection_version="media:v3", audience="public",
                    )


if __name__ == "__main__": unittest.main()
