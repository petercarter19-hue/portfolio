import unittest
from types import SimpleNamespace

from azure.core.exceptions import ResourceNotFoundError

from services.capture_media_storage_service import (
    CaptureMediaStorageService,
)


ORIGINAL = "photo/v1/ab/ab0123456789abcdef0123456789abcd.jpg"
PREVIEW = "photo/v1/ab/ab0123456789abcdef0123456789abcd-preview.jpg"


class FakeDownload:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class FakeBlob:
    def __init__(self, container, name):
        self.container = container
        self.name = name

    def download_blob(self):
        return FakeDownload(self.container.payloads[self.name])

    def get_blob_properties(self):
        payload = self.container.payloads[self.name]
        return SimpleNamespace(
            size=len(payload),
            etag='"opaque-etag"',
            content_settings=SimpleNamespace(content_type="image/jpeg"),
        )

    def get_blob_tags(self):
        return self.container.tags

    def exists(self):
        return self.name in self.container.payloads


class FakeContainer:
    def __init__(self):
        self.payloads = {}
        self.tags = {}
        self.upload_calls = []

    def upload_blob(self, **kwargs):
        self.upload_calls.append(kwargs)
        self.payloads[kwargs["name"]] = kwargs["data"]
        return SimpleNamespace(etag='"opaque-etag"')

    def get_blob_client(self, name):
        return FakeBlob(self, name)

    def delete_blob(self, name, **kwargs):
        if name not in self.payloads:
            raise ResourceNotFoundError("absent")
        del self.payloads[name]


class CaptureMediaStorageTests(unittest.TestCase):
    def setUp(self):
        self.container = FakeContainer()
        self.service = CaptureMediaStorageService(
            account_url="https://synthetic.blob.core.windows.net",
            container_name="private-capture-media",
        )
        self.service._container_client = self.container

    def test_upload_is_create_only_and_has_no_member_metadata(self):
        result = self.service.upload(ORIGINAL, b"synthetic", "image/jpeg")

        call = self.container.upload_calls[0]
        self.assertEqual(call["name"], ORIGINAL)
        self.assertFalse(call["overwrite"])
        self.assertIsNone(call["metadata"])
        self.assertEqual(result["etag"], '"opaque-etag"')
        self.assertNotIn("credential", call)

    def test_scan_tags_are_read_only_and_normalized(self):
        self.container.tags = {
            "Malware scanning scan result": "No threats found",
            "Malware scanning scan time": "2026-07-19T12:00:00Z",
        }

        result = self.service.get_scan_result(ORIGINAL)

        self.assertEqual(result["result"], "clean")
        self.assertEqual(result["scan_time_utc"].isoformat(), "2026-07-19T12:00:00")
        self.assertFalse(hasattr(self.container, "set_blob_tags"))

    def test_download_delete_and_absence_are_deterministic(self):
        self.container.payloads[PREVIEW] = b"preview"

        result = self.service.download(PREVIEW)
        self.service.delete(PREVIEW)
        self.service.delete(PREVIEW)

        self.assertEqual(result["data"], b"preview")
        self.assertEqual(result["byte_length"], 7)
        self.assertFalse(self.service.exists(PREVIEW))

    def test_rejects_member_or_nonopaque_storage_paths(self):
        for value in (
            "photo/member@example.test.jpg",
            "photo/v1/ab/member-name.jpg",
            "../private.jpg",
            "https://example.test/photo.jpg",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.service.upload(value, b"x", "image/jpeg")

    def test_rejects_unbounded_or_nonphoto_payloads_before_provider_call(self):
        for payload, content_type in (
            (b"", "image/jpeg"),
            (b"x", "application/octet-stream"),
        ):
            with self.subTest(content_type=content_type), self.assertRaises(ValueError):
                self.service.upload(ORIGINAL, payload, content_type)

        self.assertFalse(self.container.upload_calls)


if __name__ == "__main__":
    unittest.main()
