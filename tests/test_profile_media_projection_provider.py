from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import re
import unittest

from services.profile_core_service import ProfileNotFound, ProfileUnavailableError
from services.profile_media_projection_provider import (
    MediaAudienceDecision,
    MediaProjectionGrant,
    PhotoSourceSnapshot,
    PrivatePhotoPreview,
    ProfileMediaProjectionProvider,
)


PHOTO_BYTES = b"metadata-stripped-photo-preview"
PHOTO_DIGEST = hashlib.sha256(PHOTO_BYTES).digest()
_DEFAULT = object()


def grant(**changes):
    value = MediaProjectionGrant(
        projection_key="mediaProj_123",
        owner_key="ownerAlpha_123",
        projection_version="media:v3",
        audience="public",
        source_key="photoSource_123",
        source_version="photo:v7",
        derivative_sha256_digest=PHOTO_DIGEST,
        published=True,
        revoked=False,
        where_used=True,
        kind="photo",
        title="A quiet lake",
        description="An evening outdoors.",
        derivative_path="/profiles/avery/media/mediaProj_123/preview",
        alt_text="Sunset reflected in a lake.",
    )
    return replace(value, **changes)


def decision(**changes):
    value = MediaAudienceDecision(
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
    value = PhotoSourceSnapshot(
        owner_key="ownerAlpha_123",
        source_key="photoSource_123",
        source_version="photo:v7",
        derivative_sha256_digest=PHOTO_DIGEST,
        lifecycle_state="confirmed",
        current=True,
        deleted=False,
        scan_state="clean",
        media_kind="preview",
        metadata_stripped=True,
        content_type="image/jpeg",
        byte_length=len(PHOTO_BYTES),
    )
    return replace(value, **changes)


def preview(**changes):
    value = PrivatePhotoPreview(
        body=PHOTO_BYTES,
        content_type="image/jpeg",
        byte_length=len(PHOTO_BYTES),
        sha256_digest=PHOTO_DIGEST,
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


class PreviewPort:
    def __init__(self, value, on_open=None):
        self.value = value
        self.on_open = on_open
        self.calls = []

    def open_preview(self, **kwargs):
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
    preview_value=_DEFAULT,
    on_open=None,
):
    grants = GrantPort(grant() if grant_value is _DEFAULT else grant_value)
    audiences = AudiencePort(
        decision() if decision_value is _DEFAULT else decision_value
    )
    sources = SourcePort(source() if source_value is _DEFAULT else source_value)
    previews = PreviewPort(
        preview() if preview_value is _DEFAULT else preview_value, on_open
    )
    return (
        ProfileMediaProjectionProvider(
            grants=grants,
            audiences=audiences,
            sources=sources,
            previews=previews,
        ),
        grants,
        audiences,
        sources,
        previews,
    )


def resolve(value, *, audience="public", viewer_key=None):
    return value.resolve(
        owner_key="ownerAlpha_123",
        viewer_key=viewer_key,
        projection_key="mediaProj_123",
        projection_version="media:v3",
        audience=audience,
    )


class ProfileMediaProjectionProviderTests(unittest.TestCase):
    def test_exact_public_photo_returns_verified_preview_and_accessibility_metadata(self):
        value, grants, audiences, sources, previews = provider()

        result = resolve(value)

        self.assertEqual(result.body, PHOTO_BYTES)
        self.assertEqual(result.derivative_sha256_digest, PHOTO_DIGEST)
        self.assertEqual(result.projection.kind, "photo")
        self.assertEqual(result.projection.alt_text, "Sunset reflected in a lake.")
        self.assertEqual(result.projection.audience, "public")
        self.assertEqual(len(grants.calls), 2)
        self.assertEqual(len(audiences.calls), 2)
        self.assertEqual(len(sources.calls), 2)
        self.assertEqual(
            previews.calls,
            [
                {
                    "owner_key": "ownerAlpha_123",
                    "source_key": "photoSource_123",
                    "source_version": "photo:v7",
                    "expected_sha256_digest": PHOTO_DIGEST,
                    "expected_byte_length": len(PHOTO_BYTES),
                }
            ],
        )
        self.assertNotIn("photoSource_123", repr(result))
        self.assertNotIn(PHOTO_BYTES.decode("ascii"), repr(result))

    def test_connections_are_exact_and_never_fall_back_to_public(self):
        value, _, audiences, sources, previews = provider()
        with self.assertRaisesRegex(ProfileNotFound, "^Media projection unavailable\\.$"):
            resolve(value, audience="connections", viewer_key="viewerBravo_456")
        self.assertEqual(audiences.calls, [])
        self.assertEqual(sources.calls, [])
        self.assertEqual(previews.calls, [])

        value, _, _, _, previews = provider(
            grant_value=grant(audience="connections"),
            decision_value=decision(
                viewer_key="viewerBravo_456", audience="connections"
            ),
        )
        result = resolve(
            value, audience="connections", viewer_key="viewerBravo_456"
        )
        self.assertEqual(result.projection.audience, "connections")
        self.assertEqual(len(previews.calls), 1)

    def test_invalid_grants_fail_before_relationship_source_or_storage(self):
        cases = (
            None,
            object(),
            grant(owner_key="owner-id-11111111"),
            grant(projection_key="mediaOther_456"),
            grant(projection_version="media:v2"),
            grant(audience="connections"),
            grant(published=False),
            grant(revoked=True),
            grant(where_used=False),
            grant(kind="album"),
            grant(kind="video"),
            grant(derivative_sha256_digest=b"short"),
            grant(derivative_path="//storage.example/private"),
            grant(alt_text="   "),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, audiences, sources, previews = provider(grant_value=invalid)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(audiences.calls, [])
                self.assertEqual(sources.calls, [])
                self.assertEqual(previews.calls, [])

    def test_unrelated_and_both_block_directions_stop_before_source_and_bytes(self):
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
                value, _, _, sources, previews = provider(decision_value=denied)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(sources.calls, [])
                self.assertEqual(previews.calls, [])

    def test_stale_deleted_unclean_original_or_cross_owner_source_never_opens(self):
        cases = (
            None,
            object(),
            source(owner_key="owner-id-11111111"),
            source(source_key="photoOther_456"),
            source(source_version="photo:v6"),
            source(derivative_sha256_digest=hashlib.sha256(b"other").digest()),
            source(lifecycle_state="needs_review"),
            source(current=False),
            source(deleted=True),
            source(scan_state="malicious"),
            source(media_kind="original"),
            source(metadata_stripped=False),
            source(content_type="image/svg+xml"),
            source(content_type=[]),
            source(byte_length=True),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, _, _, previews = provider(source_value=invalid)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(previews.calls, [])

    def test_open_races_revalidate_grant_access_and_source_before_return(self):
        mutations = (
            "unpublished",
            "revoked",
            "where_used",
            "block",
            "source_version",
            "deleted",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                value, grants, audiences, sources, previews = provider()

                def mutate():
                    if mutation == "unpublished":
                        grants.value = replace(grants.value, published=False)
                    elif mutation == "revoked":
                        grants.value = replace(grants.value, revoked=True)
                    elif mutation == "where_used":
                        grants.value = replace(grants.value, where_used=False)
                    elif mutation == "block":
                        audiences.value = replace(
                            audiences.value, owner_blocked_viewer=True
                        )
                    elif mutation == "source_version":
                        sources.value = replace(sources.value, source_version="photo:v8")
                    else:
                        sources.value = replace(sources.value, deleted=True)

                previews.on_open = mutate
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(len(previews.calls), 1)

    def test_bytes_length_digest_and_type_are_verified(self):
        cases = (
            None,
            object(),
            preview(body=b"tampered"),
            preview(content_type="image/png"),
            preview(byte_length=len(PHOTO_BYTES) + 1),
            preview(sha256_digest=hashlib.sha256(b"other").digest()),
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                value, _, _, _, previews = provider(preview_value=invalid)
                with self.assertRaises(ProfileNotFound):
                    resolve(value)
                self.assertEqual(len(previews.calls), 1)

    def test_dependency_failures_are_content_free_and_do_not_leak_private_values(self):
        cases = (
            {"grant_value": RuntimeError("source-key-private")},
            {"decision_value": RuntimeError("relationship-private")},
            {"source_value": RuntimeError("blob-name-private")},
            {"preview_value": RuntimeError("sas-token-private")},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                value, *_ = provider(**kwargs)
                with self.assertRaises(ProfileUnavailableError) as raised:
                    resolve(value)
                self.assertEqual(
                    str(raised.exception), "Media projection dependency unavailable."
                )
                self.assertNotIn("private", str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)
                self.assertTrue(raised.exception.__suppress_context__)

    def test_retry_is_idempotent_and_revocation_does_not_resurrect_access(self):
        value, grants, _, _, previews = provider()
        first = resolve(value)
        second = resolve(value)
        self.assertEqual(first, second)
        self.assertEqual(len(previews.calls), 2)

        grants.value = replace(grants.value, revoked=True)
        with self.assertRaises(ProfileNotFound):
            resolve(value)
        self.assertEqual(len(previews.calls), 2)

    def test_malformed_requests_fail_without_touching_any_port(self):
        value, grants, audiences, sources, previews = provider()
        for field, bad in (
            ("owner_key", None),
            ("viewer_key", object()),
            ("projection_key", 7),
            ("projection_version", []),
            ("audience", "friends"),
        ):
            args = {
                "owner_key": "ownerAlpha_123",
                "viewer_key": None,
                "projection_key": "mediaProj_123",
                "projection_version": "media:v3",
                "audience": "public",
            }
            args[field] = bad
            with self.subTest(field=field):
                with self.assertRaises(ProfileNotFound):
                    value.resolve(**args)
        self.assertEqual(grants.calls, [])
        self.assertEqual(audiences.calls, [])
        self.assertEqual(sources.calls, [])
        self.assertEqual(previews.calls, [])

    def test_database_and_original_media_boundaries_remain_unchanged(self):
        database_source = Path("services/database_service.py").read_text(
            encoding="utf-8"
        )
        allowlisted = frozenset(re.findall(r'"(usp_[A-Za-z0-9_]+)"', database_source))
        self.assertIn("usp_GetPhotoMediaForOwner", allowlisted)
        self.assertIn("usp_GetVoiceMediaForOwner", allowlisted)
        self.assertFalse(
            any(name.startswith("usp_GetProfileMedia") for name in allowlisted)
        )
        provider_source = Path(
            "services/profile_media_projection_provider.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("database_service", provider_source)
        self.assertNotIn("usp_", provider_source)
        self.assertNotIn("open_original", provider_source)
        self.assertIn("open_preview", provider_source)


if __name__ == "__main__":
    unittest.main()
