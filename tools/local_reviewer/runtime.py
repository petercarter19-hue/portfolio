"""Offline fixture runtime, durable request boundary and local control protocol."""
from __future__ import annotations

from contextlib import ExitStack
import dataclasses
import enum
import hashlib
import hmac
import html
from http.cookies import SimpleCookie
import importlib
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import socket
import sys
import threading
import warnings
from unittest.mock import patch
from urllib.parse import urlsplit

from .persistence import Codec, SnapshotStore, State, atomic_write, canonical
from .private_identity import PrivateIdentity, PrivateAccessDenied

MEMBERS = ("g-member-a", "g-member-b", "g-member-c")
WORKER_THREADS = 4
OFFLINE_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
               "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; media-src 'self' blob:; "
               "worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


def private_access(install):
    """Explicit local configuration; no remote request can enable access."""
    path = install / "private-access.json"
    if not path.exists():
        return None
    if path.is_symlink() or path.is_junction() or not path.is_file():
        raise ValueError("Private access configuration must be an ordinary file")
    config = json.loads(path.read_text(encoding="utf-8"))
    return PrivateIdentity.from_config(config)


def offline_html(body):
    # Preserve all application escaping/script text. Remove external link
    # resource hints/stylesheets; the additional CSP blocks other subresources.
    def keep(match):
        return b"" if re.search(rb'''\bhref\s*=\s*["'](?:https?:)?//''', match.group(), re.I) else match.group()
    return re.sub(rb"<link\b[^>]*>", keep, body, flags=re.I)


def loopback_only(original):
    def connect(sock, address):
        host = address[0] if isinstance(address, tuple) else ""
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
        if not local:
            raise OSError("Offline reviewer refuses outbound transport")
        return original(sock, address)
    return connect


def refuse_sql(*args, **kwargs):
    raise RuntimeError("SQL is unavailable in the offline reviewer")


def local_resolution(original):
    def resolve(host, *args, **kwargs):
        if host not in {None, "127.0.0.1", "::1", "localhost"}:
            raise OSError("Offline reviewer refuses external name resolution")
        return original(host, *args, **kwargs)
    return resolve


def isolated_environment():
    # This is a separate child process. Drop ALL inherited application/credential
    # settings rather than attempting to enumerate every possible secret name.
    allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA",
               "USERPROFILE", "PROGRAMFILES", "PROGRAMFILES(X86)", "COMSPEC", "PATHEXT"}
    retained = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    os.environ.clear()
    os.environ.update(retained)
    os.environ.update(PYTHON_DOTENV_DISABLED="1", PYTHONDONTWRITEBYTECODE="1",
                      ANTHROPIC_API_KEY="offline-placeholder", FLASK_ENV="development")
    sys.dont_write_bytecode = True


class CapturedServer:
    """Capture the fixture WSGI app without creating an unguarded HTTP listener."""
    def __init__(self, host, port, application, **kwargs):
        self.application, self.server_port = application, port
    def serve_forever(self):
        pass
    def shutdown(self):
        pass
    def server_close(self):
        pass


class OriginalStorage:
    persistence_label = "reviewer_snapshot_not_blob"
    def __init__(self):
        self.blobs = {}
    def upload(self, path, data, content_type):
        from services.resume_original_storage_service import require_path, MAX_ORIGINAL_BYTES, ResumeOriginalStorageError
        require_path(path)
        if type(data) is not bytes or not 1 <= len(data) <= MAX_ORIGINAL_BYTES or path in self.blobs:
            raise ResumeOriginalStorageError()
        etag = '"reviewer-' + hashlib.sha256(data).hexdigest() + '"'
        self.blobs[path] = (data, etag)
        return etag
    def read(self, path, *, etag, byte_length, sha256):
        from services.resume_original_storage_service import require_path, ResumeOriginalStorageError
        require_path(path)
        value = self.blobs.get(path)
        if value is None or value[1] != etag or len(value[0]) != byte_length or hashlib.sha256(value[0]).hexdigest() != sha256:
            raise ResumeOriginalStorageError("original_integrity_unavailable")
        return value[0]
    def confirm_upload(self, path, *, byte_length, sha256):
        from services.resume_original_storage_service import ResumeOriginalStorageError
        value = self.blobs.get(path)
        if value is None:
            raise ResumeOriginalStorageError()
        self.read(path, etag=value[1], byte_length=byte_length, sha256=sha256)
        return value[1]
    def delete(self, path, *, etag):
        from services.resume_original_storage_service import ResumeOriginalStorageError
        value = self.blobs.get(path)
        if value and value[1] != etag:
            raise ResumeOriginalStorageError()
        self.blobs.pop(path, None)
        return True


class UnavailableSpeech:
    def transcribe(self, *args, **kwargs):
        from services.resume_intake_transcription_adapter import RecordingIntakeError
        raise RecordingIntakeError("transcription_unavailable")


def build_fixture(source: Path, stack: ExitStack, *, live_ai=False):
    isolated_environment()
    # Fixture consumers share the test process; suppression belongs to this
    # runtime's lifetime and must not disable unrelated application audit tests.
    stack.callback(logging.disable, logging.root.manager.disable)
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore", message="Using the in-memory storage.*", category=UserWarning)
    sys.path.insert(0, str(source))
    os.chdir(source)
    stack.enter_context(patch("dotenv.load_dotenv", return_value=False))
    stack.enter_context(patch("mssql_python.connect", side_effect=refuse_sql))
    if not live_ai:
        stack.enter_context(patch.object(socket.socket, "connect", loopback_only(socket.socket.connect)))
        stack.enter_context(patch.object(socket.socket, "connect_ex", loopback_only(socket.socket.connect_ex)))
        stack.enter_context(patch.object(socket, "getaddrinfo", local_resolution(socket.getaddrinfo)))
    # No credential discovery, hosted factory or native-provider hook is loaded.
    from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
    with patch("werkzeug.serving.make_server", CapturedServer):
        fixture = stack.enter_context(Mvp1AcceptanceServer(interactive=True))
    from app import app
    from services.resume_intake_policy import SELECTED_RESUME_ONBOARDING_POLICY
    from services.resume_recording_probe import ProbedResumeTranscriptionAdapter
    from services.resume_original_file_service import ResumeOriginalFileService
    from services.resume_intake_runtime import PrivateResumeMatchingExclusions
    from tests.test_resume_original_files import Metadata
    fixture.original_storage, fixture.original_metadata = OriginalStorage(), Metadata()
    fixture.intake._policy = SELECTED_RESUME_ONBOARDING_POLICY
    fixture.intake.transcription_adapter = ProbedResumeTranscriptionAdapter(service=UnavailableSpeech())
    fixture.intake.original_files = ResumeOriginalFileService(repository=fixture.original_metadata, storage=fixture.original_storage)
    fixture.intake._matching_exclusions = PrivateResumeMatchingExclusions(fixture.shared.policy, fixture.shared.canonical)
    app.config.update(PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=False,
                      PEERSLATE_RESUME_SYNTHESIS_ENABLED=True, PEERSLATE_RESUME_INTERVIEW_ENABLED=True,
                      RESUME_PRIVATE_ASSISTANCE_SERVICE=None,
                      SESSION_COOKIE_NAME="reviewer-flask-session", SESSION_COOKIE_SAMESITE="Strict",
                      SECRET_KEY=os.urandom(32).hex())
    shared = fixture.shared
    objects = {
        "policy": (shared.policy.repository, ("_owners",)),
        "draft": (shared.draft.repository, ("_owners",)),
        "publication": (shared.publication.repository, ("_owners",)),
        "intake": (fixture.intake.repository, ("_owners", "_recording_claims")),
        "profile": (fixture.binding.store, ("_owners_by_slug", "_drafts", "_publications", "_commands")),
        "media": (shared.media_sources, ("_drafts", "_publications", "_receipts", "_owner_photos", "_catalog", "_sequence", "_catalog_generation", "_mutations", "_failures")),
        "media_bytes": (shared.media_storage, ("_objects",)),
        "capture": (shared.capture_procedures, ("created", "completed", "_counter")),
        "capture_bytes": (shared.capture_storage, ("objects", "uploads")),
        "originals": (fixture.original_metadata, ("rows", "sources", "events")),
        "original_bytes": (fixture.original_storage, ("blobs",)),
        "seeded": (shared, ("seeded_photo_keys",)),
    }
    bindings = {name + "." + attr: (obj, attr) for name, (obj, attrs) in objects.items() for attr in attrs}
    classes = set()
    for module in ("services.resume_publication_contracts", "services.resume_media_repository",
                   "services.profile_core_service", "services.profile_posts_adapter"):
        for value in vars(importlib.import_module(module)).values():
            if isinstance(value, type) and (dataclasses.is_dataclass(value) or issubclass(value, enum.Enum)):
                classes.add(value)
    state = State(bindings, Codec(classes))
    # Limit dispatch to fixture-backed blueprints plus immutable assets and the
    # actual public Resume view. Root/legacy/account/admin APIs are unavailable.
    blueprints = {"resume_draft", "resume_intake", "resume_publication", "resume_media", "entry_policy", "mvp1_profile"}
    endpoints = {r.endpoint for r in app.url_map.iter_rules() if r.endpoint.split(".")[0] in blueprints}
    for route in app.url_map.iter_rules():
        if route.rule in {"/<profile_slug>/resume", "/<profile_slug>/resume/media/<slot>"} or route.endpoint == "static":
            endpoints.add(route.endpoint)
    return fixture, app, endpoints, state


def owned(value, key, owner):
    if key == owner or isinstance(key, tuple) and key and key[0] == owner:
        return True
    if isinstance(value, dict):
        return any(value.get(field) == owner for field in ("owner", "owner_key", "owner_id", "owner_user_key", "@UserKey"))
    return any(getattr(value, field, None) == owner for field in ("owner_key", "owner_id", "owner_user_key"))


def reset_member(state: State, owner):
    if owner not in MEMBERS:
        raise ValueError("Choose one fictional member")
    # Remove references and the associated private bytes together; retain
    # global catalog content/counters and every other member's records.
    values = state.validate(state.capture())
    original_refs = {r.get("blob_name") for r in values["originals.rows"].values() if r.get("owner") == owner}
    capture_keys = {k for k, v in values["capture.created"].items() if owned(v, k, owner)}
    capture_refs = {v.get(f) for k, v in values["capture.created"].items() if k in capture_keys
                    for f in ("@OriginalBlobName", "@DerivativeBlobName")}
    media_refs = {getattr(v, "derivative_ref", None) for k, v in values["media._owner_photos"].items() if owned(v, k, owner)}
    for name in ("policy._owners", "draft._owners", "publication._owners", "intake._owners", "intake._recording_claims",
                 "profile._owners_by_slug", "profile._drafts", "profile._publications", "profile._commands",
                 "media._drafts", "media._publications", "media._receipts", "media._owner_photos", "media._failures",
                 "originals.rows", "originals.sources", "capture.created"):
        values[name] = {k: v for k, v in values[name].items() if not owned(v, k, owner) and not (name == "profile._owners_by_slug" and v == owner)}
    values["original_bytes.blobs"] = {k: v for k, v in values["original_bytes.blobs"].items() if k not in original_refs}
    values["capture_bytes.objects"] = {k: v for k, v in values["capture_bytes.objects"].items() if k not in capture_refs}
    values["capture_bytes.uploads"] = [v for v in values["capture_bytes.uploads"] if v not in capture_refs]
    values["capture.completed"] -= capture_keys
    values["media_bytes._objects"] = {k: v for k, v in values["media_bytes._objects"].items() if k not in media_refs}
    values["seeded.seeded_photo_keys"] -= capture_keys | {k[-1] for k, v in state.validate(state.capture())["media._owner_photos"].items() if owned(v, k, owner)}
    state.restore(state.codec.encode(values))


class Boundary:
    def __init__(self, fixture, app, endpoints, store, install, metadata, token, stop_event):
        self.fixture, self.app, self.endpoints = fixture, app, endpoints
        self.store, self.install, self.metadata, self.token, self.stop_event = store, install, metadata, token, stop_event
        self.lock = threading.RLock()
        # Leave a worker available for Stop/Status even when app requests wait.
        self.application_slots = threading.BoundedSemaphore(WORKER_THREADS - 1)
        self.host = "127.0.0.1:" + str(metadata["port"])
        self.private_access = private_access(install)
        self.app.config["TRUSTED_HOSTS"] = ["127.0.0.1"] + ([urlsplit(self.private_access.origin).hostname] if self.private_access else [])
        self.app.config["SESSION_COOKIE_SECURE"] = bool(self.private_access)

    def local_control(self, environ):
        """Process controls do not use browser identity or wait behind AI."""
        return (environ.get("REMOTE_ADDR") == "127.0.0.1"
                and environ.get("HTTP_HOST") == self.host
                and not any(k.startswith(("HTTP_X_FORWARDED_", "HTTP_TAILSCALE_")) or k == "HTTP_FORWARDED" for k in environ)
                and not environ.get("HTTP_ORIGIN")
                and environ.get("HTTP_SEC_FETCH_SITE") != "cross-site"
                and hmac.compare_digest(environ.get("HTTP_X_REVIEWER_TOKEN", ""), self.token))

    def status(self, environ):
        if not self.local_control(environ):
            return self.response({"error": "Local process token required"}, 403)
        return self.response({**self.metadata, "running": True, "stopping": self.stop_event.is_set(), "generation": self.store.generation,
                              "state_contract": self.store.state.contract})

    def response(self, value, status=200):
        from werkzeug.wrappers import Response
        return Response(json.dumps(value), status=status, content_type="application/json")

    def checkpoint(self):
        from datetime import datetime, timezone
        from uuid import uuid4
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".json"
        atomic_write(self.install / "checkpoints" / name, self.store.pack(self.store.state.capture()))
        return name

    def control(self, environ):
        supplied = environ.get("HTTP_X_REVIEWER_TOKEN", "")
        if not hmac.compare_digest(supplied, self.token):
            return self.response({"error": "Control token required"}, 403)
        length = int(environ.get("CONTENT_LENGTH") or 0)
        if not 0 <= length <= 2000:
            return self.response({"error": "Control request too large"}, 413)
        request = json.loads(environ["wsgi.input"].read(length) or b"{}")
        action = environ["PATH_INFO"].removeprefix("/__reviewer__/control/")
        if action == "checkpoint":
            return self.response({"checkpoint": self.checkpoint()})
        if action == "stop":
            self.stop_event.set()
            return self.response({"stopping": True, "finishes_current_request": True}, 202)
        if action == "reset":
            if self.private_access:
                return self.response({"error": "Private personal profile reset is unavailable"}, 400)
            owner = request.get("member")
            if owner not in MEMBERS:
                return self.response({"error": "Choose a fictional member"}, 400)
            checkpoint = self.checkpoint()
            reset_member(self.store.state, owner)
            return self.response({"reset": owner, "checkpoint": checkpoint})
        if action == "restore":
            name = request.get("checkpoint", "")
            if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
                return self.response({"error": "Invalid checkpoint name"}, 400)
            path = self.install / "checkpoints" / name
            if path.is_symlink() or not path.is_file():
                return self.response({"error": "Checkpoint not found"}, 404)
            body = self.store.unpack(path.read_bytes())
            previous = self.checkpoint()
            self.store.state.restore(body["state"])
            return self.response({"restored": name, "previous": previous})
        return self.response({"error": "Unknown control"}, 404)

    def dispatch(self, environ):
        from werkzeug.wrappers import Response
        method, path = environ.get("REQUEST_METHOD"), environ.get("PATH_INFO", "")
        host = environ.get("HTTP_HOST", "")
        access = self.private_access
        if path == "/__reviewer__/status" and method == "GET":
            return self.status(environ)
        if path.startswith("/__reviewer__/control/"):
            if method != "POST":
                return self.response({"error": "POST required"}, 405)
            if not self.local_control(environ):
                return self.response({"error": "Local process token required"}, 403)
            return self.control(environ)
        if access:
            try:
                environ["local_reviewer.private_owner"] = access.authorize(environ)
            except PrivateAccessDenied:
                return self.response({"error": "Open the private address with your Tailscale account"}, 403)
        elif (environ.get("REMOTE_ADDR") != "127.0.0.1" or host != self.host
              or any(k.startswith(("HTTP_X_FORWARDED_", "HTTP_TAILSCALE_")) or k == "HTTP_FORWARDED" for k in environ)):
            return self.response({"error": "Loopback installation only"}, 403)
        expected_origin = access.origin if access else "http://" + self.host
        origin = environ.get("HTTP_ORIGIN")
        if origin and origin != expected_origin:
            return self.response({"error": "Foreign origin refused"}, 403)
        if environ.get("HTTP_SEC_FETCH_SITE") == "cross-site":
            return self.response({"error": "Cross-site request refused"}, 403)
        for key in list(environ):
            if key.startswith(("HTTP_X_FORWARDED_", "HTTP_TAILSCALE_", "HTTP_X_MS_CLIENT_PRINCIPAL")) or key == "HTTP_FORWARDED":
                del environ[key]
        if access:
            environ["wsgi.url_scheme"] = "https"
            parsed = urlsplit(access.origin)
            environ["SERVER_NAME"], environ["SERVER_PORT"] = parsed.hostname, str(parsed.port or 443)
            environ["reviewer.private_https"] = True
        environ["HTTP_ACCEPT_ENCODING"] = "identity"
        cookies = SimpleCookie()
        cookies.load(environ.get("HTTP_COOKIE", ""))
        owner = cookies.get("reviewer-fictional-owner")
        # Browser cookies are shared across ports. Translate ONLY this
        # installation's selector cookie into the fixture's expected name.
        cookies.pop("mvp1-synthetic-owner", None)
        if owner is not None and not access:
            cookies["mvp1-synthetic-owner"] = owner.value
        environ["HTTP_COOKIE"] = "; ".join(k + "=" + v.coded_value for k, v in cookies.items())
        if method not in {"GET", "HEAD", "OPTIONS"} and origin != expected_origin:
            return self.response({"error": "Same-origin mutation required"}, 403)
        if path == "/":
            return Response(status=303, headers={"Location": "/app/resume" if access else "/__mvp1_fixture__/"})
        if access and path.startswith("/__mvp1_fixture__/"):
            return self.response({"error": "Use your private test profile"}, 404)
        if path == "/__mvp1_fixture__/":
            choices = "".join('<li><a href="' + name.removeprefix("g-") + '">' + label + '</a></li>' for name, label in zip(MEMBERS, ("Riley Finch · early career", "Morgan Vale · mid career", "Casey Rowan · extensive history")))
            return Response('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PeerSlate local reviewer</title><body><main><h1>PeerSlate local reviewer</h1><p>Fictional accounts. Changes persist on this PC.</p><ul>' + choices + '<li><a href="guest">Anonymous guest</a></li></ul><p>Start private. Publish deliberately as g-alex for the guest view.</p><p>Manual editing works. Intake uses a deterministic uncertain proposal; visitor answers quote approved evidence synthetically. AI synthesis, career interview and speech are unavailable. No real account, SQL, Blob or provider call.</p><p><a href="/__reviewer__/inputs">Download fictional test inputs</a></p><p>Use the installed command shortcuts to stop, checkpoint, restore or reset one member.</p><p>Resume and MVP1 Profile are available here. Other site navigation is unavailable in this focused offline environment.</p><p>Candidate: ' + html.escape(self.metadata["candidate_state"]) + ' · ' + html.escape(self.metadata["source_sha"]) + '</p></main></body></html>', content_type="text/html; charset=utf-8")
        if path == "/__reviewer__/inputs" and method == "GET":
            names = ("early-career.txt", "mid-career.txt", "extensive-history.txt", "conflicting-update.txt", "empty.txt")
            links = "".join('<li><a href="/__reviewer__/input/' + name + '">' + name + '</a></li>' for name in names)
            return Response('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fictional test inputs</title><main><h1>Fictional test inputs</h1><p>Download a file and attach it to a fictional member’s private Resume. Offline extraction requires your review and manual wording.</p><ul>' + links + '</ul><a href="/__mvp1_fixture__/">Choose member</a></main></html>', content_type="text/html; charset=utf-8")
        if path.startswith("/__reviewer__/input/") and method == "GET":
            name = path.removeprefix("/__reviewer__/input/")
            if name not in {"early-career.txt", "mid-career.txt", "extensive-history.txt", "conflicting-update.txt", "empty.txt"}:
                return self.response({"error": "Not found"}, 404)
            return Response((self.install / "inputs" / name).read_bytes(), content_type="text/plain; charset=utf-8",
                            headers={"Content-Disposition": 'attachment; filename="' + name + '"'})
        if path.startswith("/__mvp1_fixture__/"):
            response = Response.from_app(self.fixture.server.application, environ, buffered=True)
            headers = response.headers.getlist("Set-Cookie")
            response.headers.remove("Set-Cookie")
            for value in headers:
                response.headers.add("Set-Cookie", value.replace("mvp1-synthetic-owner=", "reviewer-fictional-owner=", 1))
            return response
        adapter = self.app.url_map.bind_to_environ(environ)
        try:
            endpoint, _ = adapter.match()
        except Exception:
            return self.response({"error": "Route unavailable in local reviewer"}, 404)
        if endpoint not in self.endpoints:
            return self.response({"error": "Route unavailable in local reviewer"}, 404)
        response = Response.from_app(self.app, environ, buffered=True)
        if response.mimetype == "text/html" and not response.headers.get("Content-Encoding"):
            body = offline_html(response.get_data())
            start = body.find(b"<body")
            position = body.find(b">", start) + 1 if start >= 0 else body.find(b"<main")
            if position >= 0:
                banner = '<aside role="note" style="padding:10px;background:#fff0bd;color:#231c00"><strong>LOCAL REVIEWER · FICTIONAL ACCOUNTS.</strong> Saved on this PC. Synthetic visitor answers; AI assistance and speech unavailable. <a href="/__mvp1_fixture__/">Choose member</a></aside>'
                if access:
                    banner = '<aside role="note" style="padding:10px;background:#e8f1fb;color:#17324d"><strong>PRIVATE TEST SITE.</strong> Saved on your PC. Live AI is connected; selected content is sent to Azure AI when you use it. Test publishing stays inside this private site.</aside>'
                response.set_data(body[:position] + banner.encode() + body[position:])
        return response

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO") == "/__reviewer__/status" and environ.get("REQUEST_METHOD") == "GET":
            response = self.status(environ)
            response.headers["Cache-Control"] = "private, no-store"
            return response(environ, start_response)
        if environ.get("PATH_INFO") == "/__reviewer__/control/stop" and environ.get("REQUEST_METHOD") == "POST":
            if not self.local_control(environ):
                response = self.response({"error": "Local process token required"}, 403)
            else:
                try:
                    response = self.control(environ)
                except (ValueError, TypeError):
                    response = self.response({"error": "Invalid stop request"}, 400)
            response.headers["Cache-Control"] = "private, no-store"
            return response(environ, start_response)
        # Immutable assets neither read nor change the saved workspace. Browser
        # loads request many concurrently; do not reject them behind AI/edit
        # admission slots. Dispatch still applies the complete private boundary.
        if environ.get("REQUEST_METHOD") in {"GET", "HEAD"}:
            try:
                endpoint, _ = self.app.url_map.bind_to_environ(environ).match()
            except Exception:
                endpoint = None
            if endpoint == "static":
                if self.stop_event.is_set():
                    response = self.response({"error": "The test site is stopping."}, 503)
                else:
                    try:
                        response = self.dispatch(environ)
                    except Exception:
                        response = self.response({"error": "Local asset unavailable."}, 503)
                return self.respond(response, environ, start_response)
        if not self.application_slots.acquire(blocking=False):
            response = self.response({"error": "The test site is busy. Let the current request finish."}, 503)
            response.headers["Cache-Control"] = "private, no-store"
            return response(environ, start_response)
        try:
            return self.application_request(environ, start_response)
        finally:
            self.application_slots.release()

    def application_request(self, environ, start_response):
        def draining():
            response = self.response({"error": "The test site is stopping after its current request."}, 503)
            response.headers["Cache-Control"] = "private, no-store"
            return response(environ, start_response)
        if self.stop_event.is_set():
            return draining()
        # Serialize the complete response, including lazy iterators, before
        # publishing state. A successful response never precedes its disk save.
        with self.lock:
            # Recheck after waiting: a request may have queued before Stop.
            if self.stop_event.is_set():
                return draining()
            previous = self.store.state.capture()
            try:
                response = self.dispatch(environ)
                current = self.store.state.capture()
                if current != previous:
                    self.store.save(current)
            except Exception as error:
                self.store.state.restore(previous)
                try:
                    atomic_write(self.install / "logs" / "last-error.json", canonical({"error_type": type(error).__name__, "path": "operation", "generation": self.store.generation}))
                except OSError:
                    pass
                response = self.response({"error": "Local operation failed; the previous durable state is preserved. Check installation diagnostics."}, 503)
            return self.respond(response, environ, start_response)

    def respond(self, response, environ, start_response):
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        # A second policy intersects with the candidate's policy; never
        # replace or relax its existing restrictions.
        response.headers.add("Content-Security-Policy", OFFLINE_CSP)
        if environ.get("reviewer.private_https"):
            cookies = response.headers.getlist("Set-Cookie")
            response.headers.remove("Set-Cookie")
            for value in cookies:
                response.headers.add("Set-Cookie", value if re.search(r"(?:^|;)\s*Secure(?:;|$)", value, re.I) else value + "; Secure")
        return response(environ, start_response)


def serve(install: Path, release: Path, metadata, token):
    from waitress import create_server
    with ExitStack() as stack:
        identity = private_access(install)
        fixture, app, endpoints, state = build_fixture(release / "source", stack, live_ai=bool(identity))
        if identity:
            from .providers import load_configuration, configure_private_providers
            configuration = load_configuration(install, identity, release / "source")
            identity.bind_principal(stack)
            configure_private_providers(fixture, app, install, identity, configuration)
            metadata = {**metadata, "provider": "live_azure_ai", "url": identity.origin}
        store = SnapshotStore(install / "data" / "state.json", state)
        if store.path.exists():
            store.load()  # Corruption/incompatibility stops startup, never reset.
        else:
            store.save()
        stop_event = threading.Event()
        boundary = Boundary(fixture, app, endpoints, store, install, metadata, token, stop_event)
        server = create_server(boundary, host="127.0.0.1", port=metadata["port"], threads=WORKER_THREADS,
                               max_request_body_size=51_000_000, expose_tracebacks=False,
                               clear_untrusted_proxy_headers=False)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            while not stop_event.wait(0.2):
                if not thread.is_alive():
                    raise RuntimeError("Local server exited")
        finally:
            # Let the tiny stop response leave the owned listener before closing.
            threading.Event().wait(0.2)
            # The sole admitted app operation owns this lock through provider
            # completion and durable state save. Stop cannot cut it off.
            with boundary.lock:
                server.close()
            server.task_dispatcher.shutdown()
            thread.join(timeout=5)
