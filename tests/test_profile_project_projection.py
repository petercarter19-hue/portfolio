from __future__ import annotations
from dataclasses import replace
import unittest

from services.profile_core_service import ProfileNotFound
from services.profile_project_projection_service import ProfileProjectProjection, ProfileProjectProjectionService


class Reader:
    def __init__(self, value): self.value = value
    def get_exact_projection(self, **kwargs): return self.value


class ProfileProjectProjectionTests(unittest.TestCase):
    def test_exact_released_projection_resolves(self):
        value = ProfileProjectProjection(
            "projectProj_123", "ownerAlpha_123", "project:v4", "public",
            "SATCOM Modem MBSE Model", "A model-based foundation.",
            "Systems Engineer", "2023-2024", "Verified architecture.", "/avery/projects/projectProj_123",
        )
        self.assertEqual(ProfileProjectProjectionService(Reader(value)).resolve(
            owner_key="ownerAlpha_123", projection_key="projectProj_123",
            projection_version="project:v4", audience="public"), value)

    def test_arbitrary_project_url_is_rejected(self):
        value = ProfileProjectProjection(
            "projectProj_123", "ownerAlpha_123", "project:v4", "public",
            "Project", "Summary", None, None, None, "https://evil.example/project",
        )
        with self.assertRaises(ProfileNotFound):
            ProfileProjectProjectionService(Reader(value)).resolve(
                owner_key="ownerAlpha_123", projection_key="projectProj_123",
                projection_version="project:v4", audience="public")

    def test_hostile_provider_field_types_fail_neutrally(self):
        valid = ProfileProjectProjection(
            "projectProj_123", "ownerAlpha_123", "project:v4", "public",
            "Project", "Summary", None, None, None, "/avery/projects/projectProj_123",
        )
        for field, hostile in (
            ("owner_key", None), ("projection_key", 7),
            ("projection_version", []), ("audience", {"public"}),
            ("title", object()), ("summary", 3), ("canonical_path", ["/project"]),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ProfileNotFound):
                    ProfileProjectProjectionService(Reader(replace(valid, **{field: hostile}))).resolve(
                        owner_key="ownerAlpha_123", projection_key="projectProj_123",
                        projection_version="project:v4", audience="public")


if __name__ == "__main__": unittest.main()
