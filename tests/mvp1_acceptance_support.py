"""Owned G synthetic acceptance ports. No application HTTP responses are faked.

The canonical test port shares EntryPolicyService state with My Data and
publication. It is explicitly memory evidence, not SQL or live identity proof.
"""

from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_draft_repository import InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService
from services.resume_publication_service import memory_resume_publication_service
from services.resume_media_application import build_resume_media_application
from services.resume_media_repository import InMemoryResumeMediaRepository, InMemoryMediaStorage
from contextlib import ExitStack
from unittest.mock import patch
import threading


class EntryPolicyCanonicalFixture:
    persistence_label = "g_shared_memory_not_sql"

    def __init__(self, policy):
        self.policy = policy
        self.token_for_version = str

    def list_items(self, owner):
        return [{
            "record_key": row["entry_key"],
            "record_type": "accomplishment" if row["canonical_type"] == "achievement" else row["canonical_type"],
            "content_token": self.token_for_version(row["content_version"]),
            "content_version": row["content_version"], "access_revision": row["access_revision"],
            "editable": True, "blocked_reason": None, "save_mode": "canonical",
            "values": self.editor_values(row),
            "resume_display": row["resume_display"],
            "visitor_ai": row["visitor_ai"],
            "private_assistance_excluded": row.get("private_assistance_excluded", False),
            "publication_eligible": True,
        } for row in self.policy.list_entries(owner)["entries"] if row["lifecycle"] == "active"]

    @staticmethod
    def editor_values(row):
        aliases = {"skill": {"skill_name": "name", "skill_summary": "summary"},
                   "credential": {"credential_name": "name", "issuer_name": "issuer", "credential_identifier": "identifier"}
                   }.get(row["canonical_type"], {})
        return {aliases.get(key, key): value for key, value in row["values"].items()}

    def get_item(self, owner, key):
        return next((row for row in self.list_items(owner) if row["record_key"] == key), None)

    def create_private(self, owner, item):
        from uuid import NAMESPACE_URL, uuid5
        aliases = {"skill": {"name": "skill_name", "summary": "skill_summary"},
                   "credential": {"name": "credential_name", "issuer": "issuer_name", "identifier": "credential_identifier"}
                   }.get(item["record_type"], {})
        key = item.get("record_key") or str(uuid5(NAMESPACE_URL, owner + ":entry:" + item["command_id"]))
        self.policy.commit(owner, {"type": "create", "request_id": str(uuid5(NAMESPACE_URL, owner + ":" + item["command_id"])),
            "entry_key": key, "parent_key": item.get("parent_key"),
            "canonical_type": "achievement" if item["record_type"] == "accomplishment" else item["record_type"],
            "values": {aliases.get(key, key): value for key, value in item["values"].items()}})
        return self.get_item(owner, key)


class SharedMvp1Fixture:
    """One mutable canonical store, owner-scoped draft, and publication boundary."""

    def __init__(self):
        self.policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        self.canonical = EntryPolicyCanonicalFixture(self.policy)
        self.draft = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=self.canonical)
        self.publication = memory_resume_publication_service()
        self.publication.policy_service = self.policy
        self.policy.publication_service = self.publication
        self.publication.draft_service = self.draft
        self.media_sources = InMemoryResumeMediaRepository()
        self.media_storage = InMemoryMediaStorage()
        self.seeded_photo_keys = set()
        # Reuse D's byte-processing boundary fixtures. Upload, scan reconciliation,
        # derivative generation and HTTP delivery still use the real services.
        from tests.test_resume_media_browser import SyntheticPhotoProcedures, SyntheticBoundaryStorage
        from services.photo_capture_service import PhotoCaptureService
        from services.resume_media_application import PhotoCaptureResumeReadinessPort
        from services.resume_media_service import ResumePhotoReadinessAdapter
        class OwnerPhotoProcedures(SyntheticPhotoProcedures):
            def first_row(inner, procedure, parameters=None):
                bound = inner._params(parameters)
                key = str(bound.get("@SourceKey") or "")
                if key:
                    saved = inner.created.get(key)
                    if saved is None or saved.get("@UserKey") != bound.get("@UserKey"):
                        return None
                return super().first_row(procedure, parameters)
        self.capture_storage = SyntheticBoundaryStorage()
        self.capture_procedures = OwnerPhotoProcedures(self.capture_storage)
        self.capture = PhotoCaptureService(database=self.capture_procedures, storage=self.capture_storage)
        capture_readiness = ResumePhotoReadinessAdapter(PhotoCaptureResumeReadinessPort(self.capture))
        from types import SimpleNamespace
        def photo_state(owner, key):
            if key not in self.seeded_photo_keys:
                return capture_readiness.get_source(owner, key)
            from dataclasses import asdict
            record = self.media_sources.get_owner_photo(owner_id=owner, source_id=key)
            if record is None or record.lifecycle != "active":
                return None
            return asdict(record)
        def open_photo(owner, key, variant):
            if key not in self.seeded_photo_keys:
                return capture_readiness.open_source_media(owner, key, variant)
            from io import BytesIO
            record = self.media_sources.get_owner_photo(owner_id=owner, source_id=key)
            if record is None or record.state != "ready" or record.lifecycle != "active":
                return None
            blob = self.media_storage.open(record.derivative_ref)
            return {"stream": BytesIO(blob["data"]), "content_type": record.content_type,
                    "byte_length": record.byte_length}
        self.media = build_resume_media_application(draft_store=self.draft.repository,
            sources=self.media_sources, storage=self.media_storage, persistence_label="g_shared_memory_not_sql",
            photo_readiness=SimpleNamespace(open_source_media=open_photo, get_source=photo_state,
                create_source=capture_readiness.create_source, reconcile_source=capture_readiness.reconcile_source),
            publication_service=self.publication)
        self.publication.media_application = self.media
        from services.resume_publication_adapters import PublishedMediaBytesPort
        self.publication.media_bytes_port = PublishedMediaBytesPort(self.media)

    def seed_publication(self, owner, choices, *, slug='g-alex'):
        """Explicit fixture setup through the real review/commit boundary."""
        from uuid import uuid4
        reviewed = self.publication.review_for_owner(owner, {'entries': [
            dict(entry_key=key, resume_display=display, visitor_ai=ai) for key, display, ai in choices]}).reviewed
        if reviewed is None:
            raise AssertionError('Synthetic fixture could not be reviewed')
        return self.publication.commit(owner, dict(type='publish', request_id=str(uuid4()), slug=slug,
            profile_identity=None, reviewed_digest=reviewed.digest, candidate=self.publication.publish_candidate(reviewed)))

    def seed_photo(self, owner, *, color=(30, 100, 140), width=1800, height=600):
        from hashlib import sha256
        from io import BytesIO
        from uuid import uuid4
        from PIL import Image
        output = BytesIO()
        Image.new("RGB", (width, height), color).save(output, format="PNG")
        data = output.getvalue()
        key = str(uuid4())
        self.seeded_photo_keys.add(key)
        ref = "g-synthetic-photo:" + key
        self.media_storage.put(ref, data, content_type="image/png")
        return self.media_sources.seed_owner_photo(owner_id=owner, source_id=key,
            width=width, height=height, digest=sha256(data).hexdigest(),
            content_type="image/png", byte_length=len(data), derivative_ref=ref)


class Mvp1AcceptanceServer:
    """Local synthetic identity and memory stores; real Flask routes/services.

    Authentication, persistence, media storage and provider transports are
    explicit synthetic boundaries. Actual Flask routes/services are exercised.
    A context without the fixture cookie is a guest. Never production startup.
    """

    def __init__(self, *, interactive=False, port=0):
        self.interactive = interactive
        self.port = port

    def __enter__(self):
        from flask import request
        from werkzeug.serving import make_server
        from app import app, limiter
        from identity import AuthenticationRequired, PeerSlatePrincipal
        from services.mvp1_profile_binding import Mvp1ProfileBinding
        from services.profile_core_service import InMemoryProfileCoreStore
        from services.resume_intake_repository import InMemoryResumeIntakeRepository
        from services.resume_intake_service import ResumeIntakeService
        from services.resume_intake_policy import selected_policy_for_tests
        from services.resume_guide_service import ResumeGuideService

        self.stack = ExitStack()
        self.shared = SharedMvp1Fixture()
        # This server feeds the real SQL-snapshot adapter: represent its
        # synthetic canonical counters as binary(8)-shaped rowversions.
        self.shared.canonical.token_for_version = lambda version: format(version, "016x")
        self.binding = Mvp1ProfileBinding(InMemoryProfileCoreStore())
        self.shared.publication.profile_binding = self.binding
        self.ai_database = GMemoryAiSnapshot(self.shared)
        self.provider = GQuotedEvidenceProvider()
        from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
        from services.member_visitor_ai_service import (MemberVisitorAiService, CitationTicketStore,
            SingleProcessVisitorProtections, VisitorAiRuntime, VisitorOperationalLimits)
        from services.ai_foundation.gateway import AIFoundationGateway
        from services.mvp1_profile_binding import PinnedResumeNamePort
        from types import SimpleNamespace
        from identity import get_current_identity
        repo = SqlMemberVisitorAiRepository(self.ai_database, draft_service=self.shared.draft,
            identity=SimpleNamespace(current_owner_key=lambda: get_current_identity().user_key))
        self.ai = MemberVisitorAiService(repo, repo, AIFoundationGateway(self.provider),
            support=GExactQuoteSupport(), citations=CitationTicketStore(capacity=100, lifetime_seconds=600),
            names=PinnedResumeNamePort(self.binding, self.shared.publication.repository))
        self.ai_runtime = VisitorAiRuntime(VisitorOperationalLimits(
            maximum_request_bytes=16000, maximum_question_characters=1000,
            concurrent_requests=2, timeout_seconds=5, window_seconds=60,
            requests_per_client_window=30, maximum_clients=50, cost_units_per_request=1,
            aggregate_cost_units_per_window=200), SingleProcessVisitorProtections(), scope="single_process")
        self.stack.callback(self.ai_runtime.close)
        intake_store = InMemoryResumeIntakeRepository()
        from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter
        self.transcriber = GRecordingTranscriber()
        self.intake = ResumeIntakeService(repository=intake_store, draft_service=self.shared.draft,
                                         transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
                                         policy=selected_policy_for_tests())
        def principal():
            owner = request.cookies.get("mvp1-synthetic-owner")
            if owner not in {"g-member-a", "g-member-b", "g-member-c"}:
                raise AuthenticationRequired()
            return PeerSlatePrincipal("development", "mvp1-local-fixture", owner,
                                      display_name="Synthetic member", is_development=True)
        try:
            self.stack.enter_context(patch("identity.get_current_principal", side_effect=principal))
            self.stack.enter_context(patch("auth_routes.get_current_principal", side_effect=principal))
            self.stack.enter_context(patch.dict(app.config, {
                "TESTING": True, "PEERSLATE_ALLOW_DEV_IDENTITY": False,
                "PEERSLATE_TRUST_EASYAUTH_HEADERS": True,
                "PEERSLATE_RESUME_EDITOR_ENABLED": True, "PEERSLATE_RESUME_PUBLICATION_ENABLED": True,
                "PEERSLATE_ENTRY_POLICY_ENABLED": True, "PEERSLATE_MY_DATA_ENABLED": True,
                "PEERSLATE_MVP1_PROFILE_ENABLED": True, "PEERSLATE_RESUME_MEDIA_ENABLED": True,
                "PEERSLATE_RESUME_INTAKE_ENABLED": True, "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED": True,
                "PEERSLATE_MEMBER_VISITOR_AI_ENABLED": True,
                "MEMBER_VISITOR_AI_SERVICE": self.ai, "MEMBER_VISITOR_AI_RUNTIME": self.ai_runtime,
                "ENTRY_POLICY_SERVICE": self.shared.policy, "RESUME_DRAFT_SERVICE": self.shared.draft,
                "RESUME_PUBLICATION_SERVICE": self.shared.publication, "RESUME_MEDIA_SERVICE": self.shared.media,
                "MVP1_PROFILE_BINDING": self.binding, "RESUME_INTAKE_SERVICE": self.intake,
                "RESUME_GUIDE_SERVICE": ResumeGuideService(repository=intake_store),
            }))
            self.stack.enter_context(patch.object(limiter, "enabled", False))
            application = _interactive_fixture(app) if self.interactive else app
            self.server = make_server("127.0.0.1", self.port, application, threaded=True)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.url = f"http://127.0.0.1:{self.server.server_port}"
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        try:
            self.server.shutdown()
            self.thread.join(timeout=5)
            self.server.server_close()
        finally:
            self.stack.close()


class GRecordingTranscriber:
    """Synthetic provider transport; actual browser recording bytes are retained in memory only."""
    def __init__(self):
        self.calls = []
        self.hook = lambda: None

    def transcribe(self, audio_bytes, content_type, locale='en-US'):
        self.calls.append((len(audio_bytes), content_type))
        self.hook()
        return {'provider_transcript': 'Synthetic spoken contribution about planning.',
                'provider_request_id': 'g-synthetic-transcription', 'duration_seconds': 2.0}


class GMemoryAiSnapshot:
    """Fresh memory projection into the real F repository's database port.

    This is an explicit persistence fixture. It never supplies application HTTP
    responses, provider quality, SQL transactions or distributed qualifications.
    """
    def __init__(self, shared):
        self.shared = shared
        self.fail = False

    def first_row(self, procedure, parameters):
        import json
        from services.member_visitor_ai_sources import fingerprint
        from services.resume_publication_projection import publication_evidence_version
        from services.resume_publication_service import _codec_values
        if self.fail:
            raise RuntimeError("Synthetic database unavailable")
        args = dict(parameters)
        preview = procedure == "usp_GetMemberVisitorAiPreviewForOwner"
        assert preview or procedure == "usp_GetMemberVisitorAiBySlug"
        owner = args.get("@UserKey") if preview else self.shared.publication._owner_for_slug(args["@ProfileSlug"])
        if owner is None:
            return None
        snapshot = self.shared.publication.repository.load_owner(owner)
        current = self.shared.publication._current(snapshot)
        draft = self.shared.draft.repository.load_owner(owner)
        public = {} if preview else self.shared.publication.guest_read(slug=args["@ProfileSlug"])
        entries = []
        for row in self.shared.policy.list_entries(owner)["entries"]:
            key = row["entry_key"]
            if row["lifecycle"] != "active" or (not preview and key not in (current or {}).get("visitor_ai", {})):
                continue
            version = (publication_evidence_version(owner_key=owner, entry_key=key,
                evidence_key="saved:" + key, evidence_version_key="saved:" + key + ":" + str(row["content_version"]),
                version=row["content_version"], canonical_token=str(row["content_version"]),
                policy_content_version=row["content_version"], access_revision=row["access_revision"],
                canonical_type=row["canonical_type"], values=_codec_values(row["values"], row["canonical_type"]),
                display_eligible=row["resume_display"], visitor_ai_eligible=row["visitor_ai"])
                if preview else current["evidence"][key])
            entries.append({"owner_key": owner, "entry_key": key, "canonical_type": row["canonical_type"],
                "content_version": row["content_version"], "access_revision": row["access_revision"],
                "resume_display": row["resume_display"], "visitor_ai": row["visitor_ai"], "lifecycle": row["lifecycle"],
                "canonical_revision": self.shared.canonical.token_for_version(row["content_version"]).upper(), "dependency_versions": [],
                "content_hex": version.content.hex(), "content_sha256": version.content_sha256,
                "current_content_sha256": publication_evidence_version(owner_key=owner, entry_key=key,
                    evidence_key="saved:" + key, evidence_version_key="current:" + key,
                    version=row["content_version"], canonical_token=str(row["content_version"]),
                    policy_content_version=row["content_version"], access_revision=row["access_revision"],
                    canonical_type=row["canonical_type"], values=_codec_values(row["values"], row["canonical_type"]),
                    display_eligible=row["resume_display"], visitor_ai_eligible=row["visitor_ai"]).content_sha256,
                "evidence_version_key": version.evidence_version_key, "evidence_version": version.version,
                "codec": version.codec, "canonical_token": version.canonical_token,
                "evidence_content_version": version.policy_content_version, "evidence_access_revision": version.access_revision,
                "evidence_display": version.display_eligible, "evidence_ai": version.visitor_ai_eligible})
        document = {"schema_version": 1, "subject_key": owner, "resume_key": "resume:" + owner,
            "mode": "owner_preview" if preview else "guest", "profile_revision": fingerprint(public.get("public_identity")),
            "sharing_enabled": snapshot["sharing_enabled"], "sharing_epoch": snapshot["sharing_epoch"],
            "publication_revision": snapshot["publication_revision"], "current_revision": snapshot["current_revision"],
            "reviewed_digest": (current or {}).get("digest"), "draft_revision": draft["draft_version"],
            "draft_digest": fingerprint(draft), "placement_digest": fingerprint(draft.get("media", {})),
            "publication_media": public.get("media", {}), "media": [], "entries": entries}
        return {"snapshot_json": json.dumps(document)}


class GQuotedEvidenceProvider:
    """Deterministic provider transport substitute; makes no live model call."""
    def __init__(self):
        self.seen = []
        self.hook = lambda: None

    def answer(self, request, sources):
        from services.ai_foundation.contracts import AnswerClaim, AnswerKind, AnswerState, Citation, GroundedAnswer
        from services.resume_publication_contracts import decode_canonical_source
        self.seen.append((request, sources))
        self.hook()
        if not sources:
            return GroundedAnswer("g-answer", AnswerState.NOT_ESTABLISHED, "Not established.")
        source = sources[0]
        decoded = decode_canonical_source(source.content.encode())
        quote = next(value for key in ("summary", "wording", "skill_summary", "role_title", "name")
                     if isinstance(value := decoded.get(key), str) and value)
        start = source.content.index(quote)
        cite = Citation("g-claim", source.source_version_key, start, start + len(quote), quote)
        return GroundedAnswer("g-answer", AnswerState.SUPPORTED, quote,
            (AnswerClaim("g-claim", quote, AnswerKind.EVIDENCE, AnswerState.SUPPORTED, (cite,)),))


class GExactQuoteSupport:
    """Only exact fixture source quotations; no claim of model entailment quality."""
    def validate(self, request, sources, answer):
        from services.member_visitor_ai_service import SupportVerdict
        from services.resume_publication_contracts import decode_canonical_source
        allowed = {value for source in sources for value in decode_canonical_source(source.content.encode()).values()
                   if isinstance(value, str)}
        return SupportVerdict.SUPPORTED if answer.summary in allowed and all(claim.text in allowed for claim in answer.claims) else SupportVerdict.UNSUPPORTED


def _interactive_fixture(application):
    """Loopback-only test identity chooser, outside the production Flask router."""
    from werkzeug.wrappers import Response
    def dispatch(environ, start_response):
        path = environ.get('PATH_INFO', '')
        if not path.startswith('/__mvp1_fixture__/'):
            return application(environ, start_response)
        selected = path.removeprefix('/__mvp1_fixture__/')
        if environ.get('REQUEST_METHOD') != 'GET':
            response = Response('Fixture selector supports GET only.', status=405)
        elif selected in {'member-a', 'member-b', 'member-c', 'guest'}:
            response = Response(status=303, headers={'Location': '/app/resume' if selected != 'guest' else '/g-alex/resume'})
            if selected == 'guest':
                response.delete_cookie('mvp1-synthetic-owner')
            else:
                response.set_cookie('mvp1-synthetic-owner', 'g-' + selected, httponly=True, samesite='Strict')
        elif selected == '':
            response = Response('<!doctype html><html lang="en"><title>G synthetic acceptance fixture</title>'
                '<main><h1>G synthetic acceptance fixture</h1><p>Local memory only. No real account, database or AI provider.</p>'
                '<ul><li><a href="member-a">Use synthetic member A (Riley Finch, early career)</a></li>'
                '<li><a href="member-b">Use synthetic member B (Morgan Vale, mid career)</a></li>'
                '<li><a href="member-c">Use synthetic member C (Casey Rowan, extensive history)</a></li>'
                '<li><a href="guest">Use anonymous guest</a></li></ul>'
                '<p>Start from an empty private Resume. Publish as g-alex to use the guest link. '
                'A restart clears this fixture. Use separate browser contexts for isolation checks.</p></main></html>',
                content_type='text/html; charset=utf-8')
        else:
            response = Response('Not found.', status=404)
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response(environ, start_response)
    return dispatch


def main():
    import argparse
    import json
    import subprocess
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Serve the local synthetic G fixture for independent hands-on review.')
    parser.add_argument('--serve', action='store_true', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--require-sha', default='')
    args = parser.parse_args()
    if args.port != 0 and not 1024 <= args.port <= 65535:
        parser.error('Use port 0 or an unprivileged TCP port.')
    root = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip())
    if args.require_sha and (head != args.require_sha or dirty):
        parser.error('Exact clean reviewed source is required.')
    with Mvp1AcceptanceServer(interactive=True, port=args.port) as server:
        print(json.dumps({'url': server.url + '/__mvp1_fixture__/', 'source_sha': head,
                          'dirty': dirty, 'persistence': 'synthetic_memory', 'provider': 'synthetic_transport'}), flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
