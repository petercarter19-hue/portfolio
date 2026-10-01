"""Actual Flask requests for private originals and route-only multipart bounds."""
from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from flask import Flask, request
import resume_intake_routes as routes
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService
from services.resume_original_file_repository import OriginalFileNotFound


class Files:
    def __init__(self):
        self.key = str(uuid4())
        self.calls = []

    def list(self, owner):
        self.calls.append(("list", owner))
        return []

    def download(self, owner, key):
        self.calls.append(("download", owner, key))
        if owner != "member" or key != self.key:
            raise OriginalFileNotFound()
        return b"synthetic original", "text/plain"

    def delete(self, owner, key, **kwargs):
        self.calls.append(("delete", owner, key, kwargs))
        return {"success": True, "outcome": "delete_pending"}


class OriginalRoutesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask("original-routes-fixture")
        self.files = Files()
        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=InMemoryCanonicalCatalog()),
            policy=SELECTED_RESUME_ONBOARDING_POLICY,
            document_pipeline=lambda *args, **kwargs: ("Synthetic parsed material", "extracted", None, False, ()),
            original_files=self.files,
        )
        # Admission-only large-upload test does not exercise Blob retention.
        self.files.retain = lambda *args: None
        self.app.config.update(TESTING=True, MAX_CONTENT_LENGTH=2*1024*1024,
            PEERSLATE_RESUME_INTAKE_ENABLED=True, RESUME_INTAKE_SERVICE=service)
        self.app.register_blueprint(routes.resume_intake)
        @self.app.post("/unrelated")
        def unrelated():
            return str(len(request.get_data()))
        self.client = self.app.test_client()
        self.identity = patch.object(routes, "get_current_identity", return_value=SimpleNamespace(user_key="member"))
        self.identity.start()
        self.addCleanup(self.identity.stop)

    def test_download_is_attachment_nosniff_private_no_store(self):
        response = self.client.get("/api/resume-intake/me/originals/" + self.files.key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"synthetic original")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn("resume-original.txt", response.headers["Content-Disposition"])
        self.assertEqual(self.files.calls, [("download", "member", self.files.key)])

    def test_foreign_missing_neutral_and_flag_off_before_storage(self):
        url = "/api/resume-intake/me/originals/" + self.files.key
        with patch.object(routes, "get_current_identity", return_value=SimpleNamespace(user_key="foreign")):
            foreign = self.client.get(url)
        missing = self.client.get("/api/resume-intake/me/originals/" + str(uuid4()))
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.get_json(), missing.get_json())
        self.files.calls.clear()
        self.app.config["PEERSLATE_RESUME_INTAKE_ENABLED"] = False
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.files.calls, [])

    def test_delete_requires_same_origin_closed_version_request_and_truthful_pending(self):
        url = "/api/resume-intake/me/originals/" + self.files.key
        body = {"request_id": str(uuid4()), "expected_version": 2}
        self.assertEqual(self.client.delete(url, json=body).status_code, 403)
        headers = {"X-PeerSlate-Request": "same-origin"}
        self.assertEqual(self.client.delete(url, headers={**headers, "Origin": "https://foreign.test"}, json=body).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=headers, json={**body, "blob_name": "private/path"}).status_code, 400)
        response = self.client.delete(url, headers=headers, json=body)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json()["outcome"], "delete_pending")
        self.assertEqual(self.files.calls, [("delete", "member", self.files.key, body)])

    def test_three_mb_document_route_admits_and_unrelated_route_keeps_two_mb_limit(self):
        import json
        key = "document"
        body = {"type": "add_submission", "request_id": str(uuid4()),
                "attachments": [{"kind": "document", "client_key": key, "filename": "fixture.txt", "declared_content_type": "text/plain"}]}
        payload = b"x" * (3 * 1024 * 1024)
        response = self.client.post("/api/resume-intake/me/submissions",
            headers={"X-PeerSlate-Request": "same-origin"},
            data={"request": json.dumps(body), "file:"+key: (BytesIO(payload), "fixture.txt", "text/plain")})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post("/unrelated", data=payload).status_code, 413)
        self.assertEqual(self.app.config["MAX_CONTENT_LENGTH"], 2*1024*1024)


if __name__ == "__main__":
    unittest.main()
