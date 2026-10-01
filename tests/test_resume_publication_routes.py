"""Real Flask HTTP journeys for Resume publication. Not SQL engine proof."""

from __future__ import annotations

import unittest
from uuid import uuid4

from app import app
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_publication_service import memory_resume_publication_service


def _create_displayed_role(policy, owner, summary="Led team 0."):
    entry_key = str(uuid4())
    policy.commit(
        owner,
        {
            "type": "create",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "canonical_type": "role",
            "values": {
                "role_title": "Lead",
                "employer_name": "PeerSlate",
                "summary": summary,
            },
        },
    )
    listed = policy.list_entries(owner)["entries"]
    created = next(item for item in listed if item["entry_key"] == entry_key)
    policy.commit(
        owner,
        {
            "type": "change_permissions",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "expected_access_revision": created["access_revision"],
            "permissions": {"resume_display": True, "visitor_ai": False},
        },
    )
    return entry_key


class ResumePublicationRouteTests(unittest.TestCase):
    def test_private_composition_media_uses_owner_draft_delivery_and_revocation_fences(self):
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_media_repository import MediaPlacement, RequestReceipt, provenance_label_for
        from services.resume_media_service import centered_slot_crop
        shared=SharedMvp1Fixture()
        key=str(uuid4())
        shared.policy.commit("member-a",{"type":"create","request_id":str(uuid4()),"entry_key":key,
            "canonical_type":"role","values":{"role_title":"Synthetic role","employer_name":"Fictional Company"}})
        photo=shared.seed_photo("member-a")
        placement=MediaPlacement("experience_support","owner_photo",photo.source_id,photo.version,photo.digest,
            centered_slot_crop(slot="experience_support",width=photo.width,height=photo.height),
            alt_text="Synthetic test landscape",provenance_label=provenance_label_for(source_kind="owner_photo"))
        shared.media.media_repository.commit_draft(owner_id="member-a",expected_version=0,placements=(placement,),
            receipt=RequestReceipt("member-a","add",str(uuid4()),"b"*64,"{}"))
        with patch.dict(app.config,{"RESUME_PUBLICATION_SERVICE":shared.publication,
                "RESUME_MEDIA_SERVICE":shared.media,"PEERSLATE_RESUME_MEDIA_ENABLED":True}):
            client=self._client()
            review=client.post("/api/resume-publication/me/review",headers=self._headers(),json={"entries":[
                {"entry_key":key,"resume_display":True,"visitor_ai":False}]}).get_json()
            payload={"candidate":review["candidate"],"reviewed_digest":review["digest"],"profile_identity":None}
            preview=client.post("/api/resume-publication/me/preview",headers=self._headers(),json=payload)
            self.assertEqual(preview.status_code,200)
            url="/api/resume-publication/me/preview/media/experience_support?expected="+preview.get_json()["media"]["experience_support"]["preview_digest"]
            self.assertIn(url,preview.get_json()["html"])
            self.assertNotIn('/None/resume/media',preview.get_json()["html"])
            self.assertEqual(client.get(url).status_code,200)
            app.config["PEERSLATE_DEV_USER_KEY"]="member-b"
            self.assertEqual(client.get(url).status_code,404)
            app.config["PEERSLATE_DEV_USER_KEY"]="member-a"
            shared.media_sources.update_owner_photo(owner_id="member-a",source_id=photo.source_id,lifecycle="restricted")
            self.assertEqual(client.get(url).status_code,404)
            self.assertEqual(client.post("/api/resume-publication/me/preview",headers=self._headers(),json=payload).status_code,503)
            shared.media_sources.update_owner_photo(owner_id="member-a",source_id=photo.source_id,lifecycle="active")
            self.assertEqual(client.get(url).status_code,200)
            replacement=shared.seed_photo("member-a",color=(100,20,30))
            changed=MediaPlacement("experience_support","owner_photo",replacement.source_id,replacement.version,replacement.digest,
                centered_slot_crop(slot="experience_support",width=replacement.width,height=replacement.height),
                alt_text="Different test landscape",provenance_label=provenance_label_for(source_kind="owner_photo"))
            swap={"done":False}
            def replace_during_read(*args,**kwargs):
                if swap["done"]: return
                swap["done"]=True
                shared.media.media_repository.commit_draft(owner_id="member-a",expected_version=1,placements=(changed,),
                    receipt=RequestReceipt("member-a","add",str(uuid4()),"b"*64,"{}"))
            shared.media_storage.on_open=replace_during_read
            self.assertEqual(client.get(url).status_code,404)
            self.assertTrue(swap["done"])

    def test_temporary_choices_preview_approved_layout_privately_and_reject_stale_or_foreign_candidate(self):
        import copy
        client = self._client()
        row = self.policy.list_entries("member-a")["entries"][0]
        self.policy.commit("member-a", {"type":"change_permissions","request_id":str(uuid4()),
            "entry_key":self.entry_key,"expected_access_revision":row["access_revision"],
            "permissions":{"resume_display":False,"visitor_ai":False}})
        before = copy.deepcopy(self.policy.repository.load_owner("member-a"))
        review = client.post("/api/resume-publication/me/review", headers=self._headers(), json={"entries":[
            {"entry_key":self.entry_key,"resume_display":True,"visitor_ai":False}]}).get_json()
        payload = {"candidate":review["candidate"], "reviewed_digest":review["digest"],
            "profile_identity":review["profile_identity"],"owner_user_key":"member-b"}
        response = client.post("/api/resume-publication/me/preview",json=payload,headers=self._headers())
        self.assertEqual(response.status_code,200)
        body = response.get_json()
        self.assertIn('resume-preview-title',body["html"])
        self.assertIn('Private draft preview',body["html"])
        self.assertIn('Led team 0.',body["html"])
        self.assertNotIn('/alice/resume/media/',body["html"])
        self.assertEqual(body["display"][self.entry_key]["canonical_type"],"role")
        self.assertFalse(body["published"])
        self.assertFalse(body["sharing_enabled"])
        self.assertEqual(response.headers["Cache-Control"],"private, no-store")
        self.assertEqual(self.policy.repository.load_owner("member-a"),before)
        self.assertEqual(client.get("/alice/resume").status_code,404)
        bad = copy.deepcopy(payload); bad["reviewed_digest"] = "0"*64
        self.assertEqual(client.post("/api/resume-publication/me/preview",json=bad,headers=self._headers()).status_code,409)
        app.config["PEERSLATE_DEV_USER_KEY"]="member-b"
        foreign = client.post("/api/resume-publication/me/preview",json=payload,headers=self._headers())
        self.assertIn(foreign.status_code,(400,409))
        self.assertNotIn('Led team 0.',foreign.get_data(as_text=True))
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"]=False
        app.config["PEERSLATE_DEV_USER_KEY"]=None
        self.assertEqual(client.post("/api/resume-publication/me/preview",json=payload,headers=self._headers()).status_code,404)

    def setUp(self):
        self.policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        self.service = memory_resume_publication_service()
        self.policy.publication_service = self.service
        self.service.policy_service = self.policy
        self.service.bind_slug("member-a", "alice")
        self.entry_key = _create_displayed_role(self.policy, "member-a")
        self.original = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS"),
            "PEERSLATE_RESUME_PUBLICATION_ENABLED": app.config.get("PEERSLATE_RESUME_PUBLICATION_ENABLED"),
            "RESUME_PUBLICATION_SERVICE": app.config.get("RESUME_PUBLICATION_SERVICE"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="member-a",
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True,
            RESUME_PUBLICATION_SERVICE=self.service,
        )

    def tearDown(self):
        app.config.update(self.original)

    def _client(self):
        return app.test_client()

    def _headers(self):
        return {"X-PeerSlate-Request": "same-origin"}

    def test_flag_off_is_not_found(self):
        app.config["PEERSLATE_RESUME_PUBLICATION_ENABLED"] = False
        client = self._client()
        self.assertEqual(client.get("/app/resume/publication").status_code, 404)
        self.assertEqual(client.get("/api/resume-publication/me/preview").status_code, 404)

    def test_review_does_not_publish(self):
        client = self._client()
        response = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["digest"])
        guest = client.get("/alice/resume")
        self.assertEqual(guest.status_code, 404)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_publish_guest_sees_result_and_private_cache(self):
        client = self._client()
        reviewed = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()
        published = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed["digest"],
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(published.status_code, 200)
        guest = client.get("/alice/resume")
        self.assertEqual(guest.status_code, 200)
        self.assertIn("private, no-store", guest.headers["Cache-Control"])
        self.assertIn("noindex", guest.headers.get("X-Robots-Tag", ""))
        self.assertIn("Explore the experience this member has chosen to share.", guest.get_data(as_text=True))
        self.assertIn("Led team 0.", guest.get_data(as_text=True))
        api = client.get("/api/public/profiles/alice/living-resume")
        self.assertEqual(api.status_code, 200)
        body = api.get_json()
        self.assertEqual(body["classification"], "member_publication")
        self.assertNotIn("visitor_ai", body["living_resume"])
        etag = api.headers["ETag"]
        cached = client.get(
            "/api/public/profiles/alice/living-resume",
            headers={"If-None-Match": etag},
        )
        self.assertEqual(cached.status_code, 304)
        head = client.head("/alice/resume")
        self.assertEqual(head.status_code, 200)

    def test_unknown_slug_does_not_fallback_to_pete_and_old_alias_redirects(self):
        client = self._client()
        self.assertEqual(client.get("/unknown-member/resume").status_code, 404)
        self.assertEqual(client.get("/unknown-member/resume2").status_code, 404)
        self.assertEqual(client.get("/alice/resume2").status_code, 404)
        reviewed = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()
        published = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": reviewed["digest"],
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(published.status_code, 200)
        redirect = client.get("/alice/resume2")
        self.assertEqual(redirect.status_code, 302)
        self.assertIn("/alice/resume", redirect.headers["Location"])
        media_alias = client.get("/alice/resume2/media/story_banner")
        self.assertEqual(media_alias.status_code, 302)

    def test_stale_publish_conflict_and_replay(self):
        client = self._client()
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        request_id = str(uuid4())
        first = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(first.status_code, 200)
        replay = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertTrue(replay.get_json()["replayed"])
        conflict = client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": request_id,
                "reviewed_digest": digest,
                "slug": "changed",
            },
            headers=self._headers(),
        )
        self.assertEqual(conflict.status_code, 409)

    def test_sharing_off_denies_guest_and_owner_preview_stays_private(self):
        client = self._client()
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        client.post(
            "/api/resume-publication/me/commands",
            json={"type": "sharing_off", "request_id": str(uuid4())},
            headers=self._headers(),
        )
        self.assertEqual(client.get("/alice/resume").status_code, 404)
        preview = client.get("/api/resume-publication/me/preview")
        self.assertEqual(preview.status_code, 200)
        self.assertFalse(preview.get_json()["sharing_enabled"])

    def test_owner_page_uses_accepted_editor_visuals(self):
        client = self._client()
        page = client.get("/app/resume/publication")
        self.assertEqual(page.status_code, 200)
        body = page.get_data(as_text=True)
        self.assertIn("Review without publishing", body)
        self.assertIn("Publish reviewed Resume", body)
        self.assertIn("resume-publication.css", body)

    def test_media_reader_is_gated_and_supports_head(self):
        client = self._client()
        missing = client.get("/alice/resume/media/story_banner")
        self.assertEqual(missing.status_code, 404)
        head = client.head("/alice/resume/media/story_banner")
        self.assertEqual(head.status_code, 404)
        digest = client.post(
            "/api/resume-publication/me/review",
            json={},
            headers=self._headers(),
        ).get_json()["digest"]
        client.post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": str(uuid4()),
                "reviewed_digest": digest,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        after_publish = client.get("/alice/resume/media/story_banner")
        self.assertEqual(after_publish.status_code, 404)
        alias = client.get("/alice/resume2/media/story_banner")
        self.assertEqual(alias.status_code, 302)

    def test_sql_adapter_wrapped_54022_maps_to_http_409(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class WrappedConflictDatabase:
            def first_row(self, name, params=None):
                return {
                    "request_digest": "a" * 64,
                    "request_id": "00000000-0000-4000-8000-000000000099",
                    "command_type": "publish",
                    "outcome": "published",
                    "publication_revision": 1,
                }

            def last_row(self, name, params=None):
                cause = RuntimeError(
                    "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
                    "That request already used a different payload. (54022)"
                )
                raise DatabaseServiceError(
                    "Database procedure usp_CommitResumePublicationCommandForOwner failed."
                ) from cause

        self.service.sql_repository = SqlResumePublicationRepository(
            database=WrappedConflictDatabase()
        )
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": "00000000-0000-4000-8000-000000000099",
                "reviewed_digest": "a" * 64,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "request_conflict")

    def test_sql_adapter_unrelated_failure_maps_to_http_503(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class UnrelatedFailureDatabase:
            def first_row(self, name, params=None):
                return {
                    "request_digest": "a" * 64,
                    "request_id": "00000000-0000-4000-8000-000000000099",
                    "command_type": "publish",
                    "outcome": "published",
                    "publication_revision": 1,
                }

            def last_row(self, name, params=None):
                raise DatabaseServiceError(
                    "Database procedure usp_CommitResumePublicationCommandForOwner failed."
                ) from RuntimeError("login failed for user 'sa'")

        self.service.sql_repository = SqlResumePublicationRepository(
            database=UnrelatedFailureDatabase()
        )
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={
                "type": "publish",
                "request_id": "00000000-0000-4000-8000-000000000099",
                "reviewed_digest": "a" * 64,
                "slug": "alice",
            },
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "unavailable")

    def test_sql_manifest_failure_stays_http_503_with_or_without_number(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        for suffix in ("", " (54015)"):
            class ManifestFailureDatabase:
                def first_row(self, name, params=None):
                    return {"request_digest": "a" * 64, "request_id": "existing",
                            "command_type": "publish", "outcome": "published",
                            "publication_revision": 1}

                def last_row(self, name, params=None):
                    raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                        "Driver Error: [Microsoft][SQL Server]Canonical source is unavailable."
                        + suffix
                    )

            self.service.sql_repository = SqlResumePublicationRepository(ManifestFailureDatabase())
            app.config["RESUME_PUBLICATION_SERVICE"] = self.service
            response = self._client().post(
                "/api/resume-publication/me/commands",
                json={"type": "publish", "request_id": str(uuid4()),
                      "reviewed_digest": "a" * 64, "slug": "alice"},
                headers=self._headers(),
            )
            with self.subTest(suffix=suffix):
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json()["code"], "unavailable")

    def test_sql_numberless_correction_denial_maps_to_http_409(self):
        from services.database_service import DatabaseServiceError
        from services.resume_publication_repository import SqlResumePublicationRepository

        class CorrectionFailureDatabase:
            def first_row(self, name, params=None):
                return None

            def last_row(self, name, params=None):
                raise DatabaseServiceError("Database procedure failed.") from RuntimeError(
                    "Driver Error: [Microsoft][SQL Server]Entry is unavailable."
                )

        self.service.sql_repository = SqlResumePublicationRepository(CorrectionFailureDatabase())
        app.config["RESUME_PUBLICATION_SERVICE"] = self.service
        response = self._client().post(
            "/api/resume-publication/me/commands",
            json={"type": "correct", "request_id": str(uuid4()),
                  "entry_key": self.entry_key, "expected_content_version": 1,
                  "expected_access_revision": 1,
                  "values": {"summary": "Attempted correction."}},
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "denied")


class VisitorRouteDatabase:
    """Synthetic SQL protocol rows, with real F repository/service/HTTP code."""
    def __init__(self):
        from tests.test_member_visitor_ai_sources import snapshot
        self.documents = {'member-a': snapshot(display=False), 'member-b': snapshot(owner='member-b')}
        self.calls = []

    def first_row(self, procedure, parameters):
        import copy
        import json
        self.calls.append((procedure, parameters))
        preview = procedure == 'usp_GetMemberVisitorAiPreviewForOwner'
        key = parameters[0][1] if preview else {'alice': 'member-a', 'bob': 'member-b'}.get(parameters[0][1])
        if key not in self.documents: return None
        doc = copy.deepcopy(self.documents[key])
        doc['mode'] = 'owner_preview' if preview else 'guest'
        return {'snapshot_json': json.dumps(doc)}


def visitor_http_stack(**limit_overrides):
    from resume_publication_routes import RequestVisitorOwner
    from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
    from services.member_visitor_ai_service import (CitationTicketStore, MemberVisitorAiService,
        SingleProcessVisitorProtections, VisitorAiRuntime)
    from services.ai_foundation.gateway import AIFoundationGateway
    from tests.test_member_visitor_ai_service import SyntheticProvider, SyntheticSupportCatalogue, operational_limits
    database = VisitorRouteDatabase()
    repository = SqlMemberVisitorAiRepository(database, identity=RequestVisitorOwner())
    provider = SyntheticProvider()
    service = MemberVisitorAiService(repository, repository, AIFoundationGateway(provider),
        support=SyntheticSupportCatalogue(), citations=CitationTicketStore(capacity=100, lifetime_seconds=120))
    runtime = VisitorAiRuntime(operational_limits(**limit_overrides), SingleProcessVisitorProtections(), scope='single_process')
    return database, repository, provider, service, runtime


def configured_foundry_settings():
    from tests.test_member_visitor_ai_service import operational_limits
    return {'endpoint':'https://synthetic-f.openai.azure.com', 'deployment':'gpt-6-luna',
        'scope':'single_process',
        'limits':vars(operational_limits(timeout_seconds=5, cost_units_per_request=60000,
                                        aggregate_cost_units_per_window=1200000)),
        'provider':{'maximum_input_tokens':17024, 'maximum_input_bytes':16000, 'maximum_output_tokens':2000},
        'prices':{'input_micro_usd_per_million':1000000, 'output_micro_usd_per_million':6000000,
                  'schedule_ref':'synthetic-safety-prices'},
        'citation_capacity':100, 'citation_lifetime_seconds':120}


class ConfiguredFoundryStubTransport:
    """No networking; real Foundry adapter/decoder/support/route consume these bytes."""
    def __init__(self):
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        self.calls, self.claim, self.support_override = [], SAVED_TEXT, None
        self.fail = False

    def post(self, url, *, headers, json, timeout):
        import json as codec
        from types import SimpleNamespace
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        self.calls.append({'url':url, 'body':json, 'timeout':timeout})
        if self.fail: raise OSError('synthetic transport unavailable')
        payload = codec.loads(json['input'])
        if payload['request']['product'] == 'member_visitor_ai_support':
            proposed = codec.loads(payload['request']['question'])
            supported = proposed['summary'] == SAVED_TEXT and all(c['text'] == SAVED_TEXT for c in proposed['claims'])
            output = self.support_override or {'verdict':'supported' if supported else 'unsupported',
                'summary_supported':supported,
                'claims':[{'claim_id':c['claim_id'], 'supported':supported} for c in proposed['claims']]}
        else:
            source = payload['sources'][0]
            start = source['content'].index(SAVED_TEXT)
            output = {'answer_id':'configured-answer', 'state':'supported', 'summary':self.claim,
                'claims':[{'claim_id':'c1', 'text':self.claim, 'kind':'evidence', 'state':'supported',
                    'citations':[{'claim_id':'c1', 'source_version_key':source['source_version_key'],
                        'start':start, 'end':start+len(SAVED_TEXT), 'excerpt':SAVED_TEXT}], 'limitation':None}],
                'follow_up_questions':[], 'handoff':None, 'model_name':None, 'prompt_contract_version':'visitor-v1'}
        wire = {'output':[{'type':'message', 'content':[{'type':'output_text', 'text':codec.dumps(output)}]}],
                'usage':{'input_tokens':1000, 'output_tokens':250}}
        return SimpleNamespace(status_code=200, json=lambda:wire)


class VisitorAiRouteTests(unittest.TestCase):
    def setUp(self):
        self.db, self.repo, self.provider, self.service, self.runtime = visitor_http_stack()
        self.original = {key: app.config.get(key) for key in (
            'TESTING', 'PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY',
            'PEERSLATE_TRUST_EASYAUTH_HEADERS', 'PEERSLATE_RESUME_PUBLICATION_ENABLED',
            'PEERSLATE_MEMBER_VISITOR_AI_ENABLED', 'MEMBER_VISITOR_AI_SERVICE', 'MEMBER_VISITOR_AI_RUNTIME')}
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True, PEERSLATE_MEMBER_VISITOR_AI_ENABLED=True,
            MEMBER_VISITOR_AI_SERVICE=self.service, MEMBER_VISITOR_AI_RUNTIME=self.runtime)
        from flask.testing import FlaskClient
        class BufferedClient(FlaskClient):
            def open(self, *args, **kwargs):
                kwargs.setdefault('buffered', True)
                return super().open(*args, **kwargs)
        self.client = BufferedClient(app, app.response_class)
        self.headers = {'X-PeerSlate-Request': 'same-origin'}
        self.guest = '/api/public/profiles/alice/ai/questions'
        self.preview = '/api/resume/me/visitor-preview/questions'

    def tearDown(self):
        self.runtime.close()
        app.config.update(self.original)

    def ask(self, path=None, **extra):
        return self.client.post(path or self.guest, json={'question': 'What happened in 2021?', **extra}, headers=self.headers)

    def test_registered_gates_do_not_call_provider_or_database_when_off(self):
        app.config['PEERSLATE_MEMBER_VISITOR_AI_ENABLED'] = False
        self.assertEqual(self.ask().status_code, 404)
        self.assertEqual(self.client.get('/api/resume/me/visitor-preview/sources').status_code, 404)
        self.assertEqual(self.db.calls, [])
        self.assertEqual(self.provider.seen, [])

    def test_guest_sixth_question_is_exact_and_citation_independently_revokes(self):
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        for i in range(6):
            response = self.ask()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['state'], 'supported')
        self.assertEqual(self.provider.seen[-1][0].question, 'What happened in 2021?')
        self.assertEqual(self.provider.seen[-1][0].subject_key, 'member-a')
        self.assertNotIn('entry-a', response.get_data(as_text=True))
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        citation_url = response.json['citations'][0]['url']
        citation = self.client.get(citation_url)
        self.assertEqual(citation.json['excerpt'], SAVED_TEXT)
        self.assertEqual(set(citation.json), {'label', 'excerpt'})
        self.assertEqual(citation.headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(self.client.get(citation_url.replace('/alice/', '/bob/')).status_code, 404)
        self.db.documents['member-a']['sharing_enabled'] = False
        denied = self.client.get(citation_url)
        self.assertEqual(denied.status_code, 404)
        self.assertNotIn(SAVED_TEXT, denied.get_data(as_text=True))
        self.assertEqual(len(self.provider.seen), 6)

    def test_authentication_and_preview_choices_are_bound_by_actual_identity(self):
        payload = {'draft_revision': 2, 'choices': [{'entry_key': 'entry-a', 'selected': True}]}
        self.assertEqual(self.ask(self.preview, **payload).status_code, 404)
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'member-a'
        self.db.documents['member-a']['sharing_enabled'] = False
        self.db.documents['member-a']['entries'][0]['visitor_ai'] = False
        choices = self.client.get('/api/resume/me/visitor-preview/sources')
        self.assertEqual(choices.status_code, 200)
        self.assertEqual(choices.json['draft_revision'], 2)
        self.assertFalse(choices.json['choices'][0]['selected'])
        result = self.ask(self.preview, **payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.provider.seen[-1][0].product, 'member_visitor_ai_preview')
        url = result.json['citations'][0]['url']
        self.assertEqual(self.client.get(url).status_code, 200)
        public = '/api/public/profiles/alice/ai/citations/' + url.rsplit('/', 1)[1]
        self.assertEqual(self.client.get(public).status_code, 404)
        app.config['PEERSLATE_DEV_USER_KEY'] = 'member-b'
        self.assertEqual(self.client.get(url).status_code, 404)
        app.config['PEERSLATE_DEV_USER_KEY'] = 'member-a'
        self.db.documents['member-a']['draft_revision'] += 1
        self.assertEqual(self.ask(self.preview, **payload).status_code, 503)
        self.assertEqual(self.client.get(url).status_code, 404)
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = False
        app.config['PEERSLATE_DEV_USER_KEY'] = None
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_forged_context_oversize_duplicate_json_and_cross_origin_rejected_before_provider(self):
        for extra in ({'owner_user_key': 'member-b'}, {'preview': True}, {'sources': ['private']},
                      {'question': 'q' * 4001}):
            self.assertEqual(self.ask(**extra).status_code, 400)
        self.assertEqual(self.client.post(self.guest, data='{"question":"a","question":"b"}',
            content_type='application/json', headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post(self.guest, json={'question': 'a'},
            headers={**self.headers, 'Origin': 'https://other.invalid'}).status_code, 403)
        self.assertEqual(self.client.post(self.guest, json={'question':'a'}).status_code, 403)
        self.assertEqual(self.client.post(self.guest, data='x'*16001,
            content_type='application/json', headers=self.headers).status_code, 400)
        self.assertEqual(self.provider.seen, [])
        self.assertEqual(self.db.calls, [])

    def test_missing_runtime_unknown_member_provider_outage_and_final_http_race_fail_closed(self):
        app.config['MEMBER_VISITOR_AI_RUNTIME'] = None
        self.assertEqual(self.ask().status_code, 503)
        self.assertEqual(self.provider.seen, [])
        app.config['MEMBER_VISITOR_AI_RUNTIME'] = self.runtime
        self.assertEqual(self.ask('/api/public/profiles/unknown/ai/questions').status_code, 503)
        self.assertEqual(self.ask('/api/public/profiles/petec/ai/questions').status_code, 404)
        from services.ai_foundation.errors import ProviderUnavailableError
        def outage(): raise ProviderUnavailableError('private diagnostic')
        self.provider.hook = outage
        result = self.ask()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json['question'], 'What happened in 2021?')
        self.assertNotIn('private diagnostic', result.get_data(as_text=True))
        self.provider.hook = lambda: None
        original = self.service.release_is_current
        def mutate(answer):
            self.db.documents['member-a']['sharing_epoch'] += 1
            return original(answer)
        self.service.release_is_current = mutate
        result = self.ask()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json['citations'], [])
        self.assertEqual(result.json['state'], 'retryable')

    def test_operational_refusal_preserves_question_without_signin_gate(self):
        from tests.test_member_visitor_ai_service import operational_limits
        from services.member_visitor_ai_service import VisitorAiRuntime, SingleProcessVisitorProtections
        self.runtime.close()
        self.runtime = VisitorAiRuntime(operational_limits(aggregate_cost_units_per_window=2),
            SingleProcessVisitorProtections(), scope='single_process')
        app.config['MEMBER_VISITOR_AI_RUNTIME'] = self.runtime
        self.assertEqual(self.ask().status_code, 200)
        response = self.ask()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json['question'], 'What happened in 2021?')
        self.assertNotIn('sign', response.get_data(as_text=True).lower())
        self.assertEqual(len(self.provider.seen), 1)

    def test_citation_revocation_during_accounting_finish_releases_no_excerpt(self):
        result = self.ask()
        url = result.json['citations'][0]['url']
        finish = self.runtime.protections.finish
        def revoke(lease):
            self.db.documents['member-a']['sharing_enabled'] = False
            finish(lease)
        self.runtime.protections.finish = revoke
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(set(response.json), {'state', 'text'})

    def test_citation_expiry_during_finish_releases_no_excerpt(self):
        now = [0]
        self.service.citations.clock = lambda:now[0]
        url = self.ask().json['citations'][0]['url']
        finish = self.runtime.protections.finish
        def expire(lease):
            now[0] = 121
            finish(lease)
        self.runtime.protections.finish = expire
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('excerpt', response.json)

    def test_slow_final_http_fence_is_bounded_and_retains_capacity(self):
        import threading
        import time
        from services.member_visitor_ai_service import VisitorAiRuntime, SingleProcessVisitorProtections
        from tests.test_member_visitor_ai_service import operational_limits
        self.runtime.close()
        self.runtime = VisitorAiRuntime(operational_limits(timeout_seconds=.04, concurrent_requests=1),
                                       SingleProcessVisitorProtections(), scope='single_process')
        app.config['MEMBER_VISITOR_AI_RUNTIME'] = self.runtime
        entered, release = threading.Event(), threading.Event()
        original = self.service.release_is_current
        def slow(answer):
            entered.set()
            release.wait(2)
            return original(answer)
        self.service.release_is_current = slow
        try:
            started = time.monotonic()
            result = self.ask()
            self.assertLess(time.monotonic() - started, .5)
            self.assertEqual(result.status_code, 429)
            self.assertTrue(entered.is_set())
            self.assertEqual(len(self.runtime.protections._active), 1)
            self.assertEqual(self.ask().status_code, 429)
            self.assertEqual(len(self.provider.seen), 1)
        finally:
            release.set()
            self.runtime.close()

    def _configure_foundry(self, settings=None):
        import json
        from resume_publication_routes import install_member_visitor_ai
        self.runtime.close()
        transport = ConfiguredFoundryStubTransport()
        self.assertTrue(install_member_visitor_ai(app, database=self.db,
            settings=json.dumps(settings or configured_foundry_settings()),
            token_provider=lambda:'synthetic-token', transport=transport))
        self.service = app.config['MEMBER_VISITOR_AI_SERVICE']
        self.runtime = app.config['MEMBER_VISITOR_AI_RUNTIME']
        return transport

    def test_real_configured_foundry_and_semantic_support_path_six_questions_via_stub_transport(self):
        import json
        transport = self._configure_foundry()
        self.assertEqual(transport.calls, [])  # composition does not invoke a provider
        for i in range(6):
            response = self.ask()
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['state'], 'supported')
        self.assertEqual(len(transport.calls), 12)
        generation, support = transport.calls[-2:]
        question = json.loads(generation['body']['input'])
        self.assertEqual(question['request']['question'], 'What happened in 2021?')
        self.assertEqual(question['request']['subject_key'], 'member-a')
        self.assertEqual(question['sources'][0]['content'], self.repo.load_guest('alice').sources[0].content)
        evaluation = json.loads(json.loads(support['body']['input'])['request']['question'])
        self.assertEqual(evaluation['summary'], response.json['text'])
        self.assertEqual(evaluation['claims'][0]['citations'][0]['excerpt'], response.json['citations'][0]['excerpt'])
        for call in transport.calls:
            self.assertFalse(call['body']['store'])
            self.assertEqual(call['body']['model'], 'gpt-6-luna')
            self.assertEqual(call['body']['max_output_tokens'], 2000)
            self.assertLessEqual(sum(call['timeout']), 5)
        self.assertNotIn('synthetic PeerSlate product-quality evaluation', generation['body']['instructions'])
        self.assertEqual(self.client.get(response.json['citations'][0]['url']).status_code, 200)
        self.assertEqual(len(transport.calls), 12)

    def test_configured_semantic_adapter_rejects_wrong_claims_and_incomplete_verdict(self):
        transport = self._configure_foundry()
        for claim in ('Was a team member in 2021.', 'Led four people in 2022.',
                      'Led forty people in 2021.', 'The pilot reduced costs.'):
            transport.claim = claim
            result = self.ask()
            self.assertEqual(result.json['state'], 'unsupported')
            self.assertEqual(result.json['citations'], [])
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        transport.claim = SAVED_TEXT
        transport.support_override = {'verdict':'supported', 'summary_supported':True, 'claims':[]}
        self.assertEqual(self.ask().json['state'], 'unsupported')
        transport.support_override = {'verdict':'supported', 'private_diagnostic':'must not escape'}
        result = self.ask()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn('private_diagnostic', result.get_data(as_text=True))

    def test_configured_transport_failure_and_invalid_config_are_unavailable(self):
        from resume_publication_routes import install_member_visitor_ai
        transport = self._configure_foundry()
        transport.fail = True
        self.assertEqual(self.ask().status_code, 503)
        self.assertEqual(len(transport.calls), 1)
        self.runtime.close()
        settings = configured_foundry_settings()
        settings['limits']['cost_units_per_request'] = 1
        self.assertFalse(install_member_visitor_ai(app, database=self.db, settings=settings,
            token_provider=lambda:self.fail('must not acquire token'), transport=transport))
        self.assertEqual(self.ask().status_code, 503)
        self.assertEqual(len(transport.calls), 1)


if __name__ == "__main__":
    unittest.main()
