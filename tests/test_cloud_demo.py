"""Authentication, cross-site identity and durable transaction acceptance."""
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from flask import Flask, request
from werkzeug.security import generate_password_hash
from werkzeug.test import Client
from werkzeug.wrappers import Response

from tools.cloud_demo.runtime import Boundary, Config, ProcessLock, SESSION, MAX_BODY, create_application
from tools.local_reviewer.persistence import Codec, SnapshotStore, State

PASSWORD = 'fictional-test-only-long-password'
HASH = generate_password_hash(PASSWORD, method='scrypt')
SOURCE = Path(__file__).resolve().parents[1]


def config(directory, label='one', owner='g-member-a'):
    origin = 'https://' + label + '.example.test'
    return Config(origin, label + '-demo', HASH, ('a' if label == 'one' else 'b') * 64,
                  owner, hashlib.sha256((origin + '\0' + owner).encode()).hexdigest(),
                  Path(directory) / label, '1' * 40)


def sign_in(client, cfg, password=PASSWORD, username=None):
    page = client.get('/login', base_url=cfg.origin)
    nonce = re.search(r'name="csrf" value="([A-Za-z0-9_-]+)"', page.text).group(1)
    return client.post('/login', base_url=cfg.origin, headers={'Origin': cfg.origin},
                       data={'csrf': nonce, 'username': username or cfg.username, 'password': password})


def fake_boundary(cfg, clock=lambda: 10000):
    cfg.data.mkdir(parents=True, exist_ok=True)
    app = Flask('cloud-demo-' + cfg.username)
    container = type('Box', (), {})()
    container.values = {'text': ''}
    state = State({'fixture.values': (container, 'values')}, Codec())
    store = SnapshotStore(cfg.data / 'state.json', state, namespace=cfg.namespace)
    if store.path.exists():
        store.load()
    else:
        store.save()
    @app.get('/app/resume')
    def view():
        return {'owner': cfg.owner, 'text': container.values['text']}
    @app.post('/api/save')
    def save():
        container.values['text'] = request.get_json()['text']
        return {'saved': True, 'publishes': False}
    return Boundary(cfg, app, {'view', 'save'}, store, clock=clock)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = config(self.tmp.name)
        self.now = 10000
        self.boundary = fake_boundary(self.cfg, lambda: self.now)
        self.client = Client(self.boundary, Response)

    def test_anonymous_wrong_login_and_cookie_attributes(self):
        self.assertEqual(self.client.get('/api/save', base_url=self.cfg.origin).status_code, 401)
        self.assertEqual(sign_in(self.client, self.cfg, 'incorrect').status_code, 403)
        self.assertEqual(sign_in(self.client, self.cfg, username='alien-demo').status_code, 403)
        response = sign_in(self.client, self.cfg)
        self.assertEqual(response.status_code, 303)
        cookie = next(x for x in response.headers.getlist('Set-Cookie') if x.startswith(SESSION + '='))
        for flag in ('Secure', 'HttpOnly', 'SameSite=Strict', 'Path=/'):
            self.assertIn(flag, cookie)
        self.assertNotIn('Domain=', cookie)
        self.assertEqual(self.client.get('/app/resume', base_url=self.cfg.origin).json['owner'], self.cfg.owner)

    def test_expiry_logout_and_forged_tokens(self):
        sign_in(self.client, self.cfg)
        self.now += self.cfg.ttl + 1
        self.assertEqual(self.client.post('/api/save', base_url=self.cfg.origin, headers={'Origin': self.cfg.origin}, json={'text': 'no'}).status_code, 401)
        sign_in(self.client, self.cfg)
        self.assertEqual(self.client.post('/logout', base_url=self.cfg.origin, headers={'Origin': self.cfg.origin}).status_code, 303)
        self.client.set_cookie(SESSION, 'f' * 43, domain='one.example.test')
        self.assertEqual(self.client.get('/api/save', base_url=self.cfg.origin).status_code, 401)

    def test_origin_host_identity_selector_and_control_refusal(self):
        sign_in(self.client, self.cfg)
        for headers in ({}, {'Origin': 'https://foreign.test'}, {'Origin': self.cfg.origin, 'Sec-Fetch-Site': 'cross-site'}):
            self.assertEqual(self.client.post('/api/save', base_url=self.cfg.origin, headers=headers, json={'text': 'no'}).status_code, 403)
        self.assertEqual(self.client.get('/healthz', base_url='https://foreign.test').status_code, 403)
        for header in ('X-MS-CLIENT-PRINCIPAL', 'Tailscale-User-Login', 'X-Demo-Owner', 'X-Reviewer-Token'):
            self.assertEqual(self.client.get('/app/resume', base_url=self.cfg.origin, headers={header: 'alien'}).status_code, 403)
        self.assertEqual(self.client.get('/app/resume?owner=alien', base_url=self.cfg.origin).status_code, 403)
        self.assertEqual(self.client.get('/__reviewer__/control/reset', base_url=self.cfg.origin).status_code, 404)
        self.client.set_cookie('mvp1-synthetic-owner', 'g-member-b', domain='one.example.test')
        self.assertEqual(self.client.get('/app/resume', base_url=self.cfg.origin).status_code, 403)
        self.assertEqual(self.boundary.store.state.validate(self.boundary.store.state.capture())['fixture.values'], {'text': ''})

    def test_two_sites_credentials_tokens_and_content_are_independent(self):
        other_cfg = replace(config(self.tmp.name, 'two', 'g-member-b'), password_hash=generate_password_hash('other-fictional-password'))
        other = fake_boundary(other_cfg, lambda: self.now)
        other_client = Client(other, Response)
        self.assertEqual(sign_in(other_client, other_cfg).status_code, 403)
        sign_in(self.client, self.cfg)
        self.client.post('/api/save', base_url=self.cfg.origin, headers={'Origin': self.cfg.origin}, json={'text': 'Only owner one'})
        first_token = self.client.get_cookie(SESSION, domain='one.example.test').value
        other_client.set_cookie(SESSION, first_token, domain='two.example.test')
        self.assertEqual(other_client.get('/api/save', base_url=other_cfg.origin).status_code, 401)
        sign_in(other_client, other_cfg, 'other-fictional-password')
        result = other_client.get('/app/resume', base_url=other_cfg.origin).json
        self.assertEqual(result, {'owner': 'g-member-b', 'text': ''})
        self.assertNotEqual(self.boundary.store.namespace, other.store.namespace)

    def test_failed_save_restores_memory_disk_and_restart_preserves(self):
        sign_in(self.client, self.cfg)
        headers = {'Origin': self.cfg.origin}
        self.assertEqual(self.client.post('/api/save', base_url=self.cfg.origin, headers=headers, json={'text': 'Durable'}).status_code, 200)
        disk = self.boundary.store.path.read_bytes()
        with patch.object(self.boundary.store, 'save', side_effect=OSError('synthetic full disk')):
            self.assertEqual(self.client.post('/api/save', base_url=self.cfg.origin, headers=headers, json={'text': 'Lost'}).status_code, 503)
        self.assertEqual(self.boundary.store.path.read_bytes(), disk)
        self.assertEqual(self.client.get('/app/resume', base_url=self.cfg.origin).json['text'], 'Durable')
        restarted = fake_boundary(self.cfg, lambda: self.now)
        restored_client = Client(restarted, Response)
        token = self.client.get_cookie(SESSION, domain='one.example.test').value
        restored_client.set_cookie(SESSION, token, domain='one.example.test')
        self.assertEqual(restored_client.get('/app/resume', base_url=self.cfg.origin).json['text'], 'Durable')

    def test_corruption_and_incompatible_namespace_refuse_without_reset(self):
        path = self.boundary.store.path
        original = path.read_bytes()
        path.write_bytes(b'{broken')
        with self.assertRaises(ValueError):
            fake_boundary(self.cfg)
        self.assertEqual(path.read_bytes(), b'{broken')
        path.write_bytes(original)
        with self.assertRaises(ValueError):
            fake_boundary(replace(self.cfg, namespace='f' * 64))
        self.assertEqual(path.read_bytes(), original)

    def test_second_writer_refuses_and_release_allows_restart(self):
        lease = ProcessLock(self.cfg.data)
        try:
            with self.assertRaises(RuntimeError):
                ProcessLock(self.cfg.data)
        finally:
            lease.close()
        restarted = ProcessLock(self.cfg.data)
        restarted.close()

    def test_login_csrf_and_global_attempt_limit(self):
        self.assertEqual(self.client.post('/login', base_url=self.cfg.origin, headers={'Origin': self.cfg.origin}, data={'username': self.cfg.username, 'password': PASSWORD, 'csrf': 'fake'}).status_code, 403)
        for _ in range(12):
            self.assertEqual(sign_in(self.client, self.cfg, 'wrong').status_code, 403)
        self.assertEqual(sign_in(self.client, self.cfg).status_code, 429)
        self.now += 61
        self.assertEqual(sign_in(self.client, self.cfg).status_code, 303)

    def test_large_upload_refuses_without_changing_saved_state(self):
        sign_in(self.client, self.cfg)
        before = self.boundary.store.path.read_bytes()
        result = self.client.post('/api/save', base_url=self.cfg.origin,
            headers={'Origin': self.cfg.origin}, data=b'x' * (MAX_BODY + 1))
        self.assertEqual(result.status_code, 413)
        self.assertEqual(before, self.boundary.store.path.read_bytes())

    def test_generation_width_limit_preserves_disk_memory_and_generation(self):
        sign_in(self.client, self.cfg)
        store = self.boundary.store
        store.generation = 8
        store.save()
        self.assertEqual(store.generation, 9)
        before = store.path.read_bytes()
        previous = store.state.capture()
        values = store.state.validate(previous)
        values['fixture.values']['text'] = 'at boundary'
        store.state.restore(store.state.codec.encode(values))
        proposed = store.state.capture()
        limit = len(store.pack(proposed, 9))
        self.assertEqual(len(store.pack(proposed, 10)), limit + 1)
        store.state.restore(previous)
        with patch('tools.cloud_demo.runtime.MAX_STATE', limit):
            response = self.client.post('/api/save', base_url=self.cfg.origin,
                headers={'Origin': self.cfg.origin}, json={'text': 'at boundary'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(store.state.capture(), previous)
        self.assertEqual(store.generation, 9)
        with patch('tools.cloud_demo.runtime.MAX_STATE', limit + 1):
            response = self.client.post('/api/save', base_url=self.cfg.origin,
                headers={'Origin': self.cfg.origin}, json={'text': 'at boundary'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(store.generation, 10)
        self.assertEqual(len(store.path.read_bytes()), limit + 1)


class ReleaseIdentityTests(unittest.TestCase):
    def test_start_requires_exact_attempt_identity_not_a_later_build(self):
        from scripts import cloud_demo_release as release
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'manifest.json'
            source, artifact = '1' * 40, 'a' * 64
            observed = {'returncode': 0, 'target': 'grok', 'source_sha': source,
                'artifact_sha256': artifact, 'deployment': {'id': None}}
            requested = {'target': 'grok', 'source_sha': source,
                'artifact_sha256': artifact, 'requested_at': '2026-10-03T00:00:00+00:00'}
            (manifest.parent / ('DEPLOY_INTENT_grok_' + source + '.json')).write_text(json.dumps(requested))
            attempt = manifest.parent / ('DEPLOY_REQUEST_grok_' + source + '.json')
            site = {'name': release.SITES['grok']}
            arm = Mock()
            arm.request.side_effect = lambda path, *args: (
                {'properties': {'DEMO_SOURCE_SHA': source, 'DEMO_OWNER': 'g-member-a'}}
                if path.endswith('/config/appsettings/list') else
                {'properties': release.access_settings(blocked=False)}
                if path.endswith('/config/web') else site)
            unrelated = {'id': 'unrelated', 'status': 4, 'complete': True,
                'start_time': '2026-10-03T00:01:00Z'}
            with patch.object(release, 'Arm', return_value=arm), \
                 patch.object(release, 'check_site', return_value=site), \
                 patch.object(release, 'load_manifest', return_value={'source_sha': source, 'artifact_sha256': artifact}), \
                 patch.object(release, 'deployment_status', return_value=[unrelated]) as status, \
                 patch('builtins.print'):
                for identity in (None, 'expected'):
                    observed['deployment']['id'] = identity
                    attempt.write_text(json.dumps(observed))
                    with self.assertRaises(ValueError):
                        release.operate('grok', 'start', manifest)
                    self.assertFalse(any(call.args[0].endswith('/start') for call in arm.request.call_args_list))
                    self.assertFalse(any(call.args[0].endswith('/restart') for call in arm.request.call_args_list))
                    self.assertFalse(any(call.args[0].endswith('/config/web') for call in arm.request.call_args_list))
                status.return_value = [{'id': 'expected', 'status': 4, 'complete': True}]
                release.operate('grok', 'start', manifest)
                restart = next(i for i, call in enumerate(arm.request.call_args_list) if call.args[0].endswith('/restart'))
                admission = next(i for i, call in enumerate(arm.request.call_args_list) if call.args[0].endswith('/config/web'))
                self.assertLess(restart, admission)

    def test_upload_requires_verified_deny_all_before_enabling_linux_scm(self):
        from scripts import cloud_demo_release as release
        for refuse_restrictions in (False, True):
            with self.subTest(refuse_restrictions=refuse_restrictions), tempfile.TemporaryDirectory() as directory:
                manifest = Path(directory) / 'manifest.json'
                source, artifact = '1' * 40, 'a' * 64
                site = {'name': release.SITES['grok'], 'properties': {'enabled': False}}
                secure = {'origin':'https://fictional.example.test','username':'fictional-demo',
                    'password_hash':'synthetic-hash','signing_key':'a'*64,
                    'owner':'g-member-a','namespace':'b'*64}
                effects = []
                def request(path, body=None, method='GET'):
                    effects.append((path, body, method))
                    if path.endswith('/config/web'):
                        properties = dict(body['properties'])
                        if refuse_restrictions:
                            properties['ipSecurityRestrictionsDefaultAction'] = 'Allow'
                        return {'properties': properties}
                    if method == 'PATCH':
                        return {'name':site['name'],'properties':{'enabled':True}}
                    return site
                arm = Mock()
                arm.request.side_effect = request
                arm.verify_plan.return_value = {'synthetic_plan':'existing-test-plan'}
                def upload(*args, **kwargs):
                    effects.append(('UPLOAD', None, None))
                    return subprocess.CompletedProcess(args[0], 0, json.dumps({'id':'exact-test-deployment'}), '')
                with patch.object(release, 'Arm', return_value=arm), \
                     patch.object(release, 'check_site', side_effect=lambda row, target: row), \
                     patch.object(release, 'load_manifest', return_value={
                        'source_sha':source,'artifact_sha256':artifact,'artifact':'synthetic.zip',
                        'startup':'python -u source/tools/cloud_demo/wsgi.py'}), \
                     patch.object(release, 'credentials', return_value=secure), \
                     patch.object(release, 'vault_path', return_value=Path(directory)/'synthetic-vault'), \
                     patch.object(release.subprocess, 'run', side_effect=upload), \
                     patch('builtins.print'):
                    if refuse_restrictions:
                        with self.assertRaises(ValueError):
                            release.deploy(manifest, 'grok')
                        self.assertFalse(any(row[2]=='PATCH' or row[0]=='UPLOAD' or row[0].endswith('/start') for row in effects))
                    else:
                        release.deploy(manifest, 'grok')
                        restriction = next(i for i,row in enumerate(effects) if row[0].endswith('/config/web'))
                        enable = next(i for i,row in enumerate(effects) if row[2]=='PATCH')
                        start = next(i for i,row in enumerate(effects) if row[0].endswith('/start'))
                        uploaded = next(i for i,row in enumerate(effects) if row[0]=='UPLOAD')
                        self.assertLess(restriction, enable)
                        self.assertLess(enable, start)
                        self.assertLess(start, uploaded)
                        self.assertFalse(any(row[1] and row[1].get('properties',{}).get('ipSecurityRestrictionsDefaultAction')=='Allow' for row in effects))


class ActualFixtureTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('waitress'),
                         'Dedicated cloud dependency overlay required; frozen artifact/startup qualification runs this test')
    def test_dedicated_startup_resolves_after_fixture_without_outbound_dns(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'from tests.test_cloud_demo import ActualFixtureTests; ActualFixtureTests().startup_proof()'],
            cwd=SOURCE, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)

    def startup_proof(self):
        import socket
        from waitress.adjustments import Adjustments
        from tools.cloud_demo import wsgi
        with tempfile.TemporaryDirectory() as directory:
            cfg = config(directory)
            def configure(application, **options):
                adjustments = Adjustments(**options)
                self.assertEqual(len(adjustments.listen), 1)
                self.assertEqual(adjustments.listen[0][3][0], '0.0.0.0')
                with self.assertRaises(OSError):
                    socket.getaddrinfo('example.com', 443)
                with socket.socket() as connection:
                    with self.assertRaises(OSError):
                        connection.connect(('203.0.113.1', 443))
            with patch.object(wsgi.Config, 'from_environment', return_value=cfg), \
                 patch('waitress.serve', side_effect=configure) as serve:
                wsgi.main()
                self.assertEqual(serve.call_count, 1)

    def test_accepted_pages_real_owner_draft_save_preview_restart_no_provider(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'from tests.test_cloud_demo import ActualFixtureTests; ActualFixtureTests().fixture_proof()'],
            cwd=SOURCE, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)

    def fixture_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = config(directory)
            with ExitStack() as stack:
                boundary = create_application(SOURCE, cfg, stack)
                client = Client(boundary, Response)
                self.assertEqual(sign_in(client, cfg).status_code, 303)
                for path in ('/app/resume', '/api/resume-intake/me', '/api/resume-intake/me/guide', '/api/resume-publication/me/preview?format=html'):
                    self.assertEqual(client.get(path, base_url=cfg.origin).status_code, 200, path)
                page = client.get('/app/resume', base_url=cfg.origin).text
                self.assertIn('FICTIONAL CLOUD DEMO', page)
                self.assertNotIn('Welcome, Pete', page)
                publication = boundary.store.state.validate(boundary.store.state.capture())['publication._owners']
                saved = client.put('/api/resume-intake/me/draft', base_url=cfg.origin,
                    headers={'Origin': cfg.origin, 'X-PeerSlate-Request': 'same-origin'},
                    json={'request_id': str(uuid4()), 'expected_version': None,
                          'text': 'Fictional cloud draft retained after restart', 'items': [], 'attachments': []})
                self.assertEqual(saved.status_code, 200, saved.text)
                self.assertTrue(saved.json['success'])
                self.assertEqual(publication, boundary.store.state.validate(boundary.store.state.capture())['publication._owners'])
                headers = {'Origin': cfg.origin, 'X-PeerSlate-Request': 'same-origin'}
                submitted = client.post('/api/resume-intake/me/submissions', base_url=cfg.origin,
                    headers=headers, data={'request': json.dumps({'type': 'add_submission',
                        'request_id': str(uuid4()), 'items': [], 'text': 'Fictional contribution',
                        'attachments': [{'client_key': 'doc', 'kind': 'document',
                            'declared_content_type': 'text/plain', 'filename': 'fictional.txt'}]}),
                        'file:doc': (BytesIO(b'Fictional cloud document about a learning project.'), 'fictional.txt', 'text/plain')})
                self.assertEqual(submitted.status_code, 200, submitted.text)
                originals = client.get('/api/resume-intake/me/originals', base_url=cfg.origin)
                self.assertEqual(originals.status_code, 200)
                original_key = originals.json['originals'][0]['original_key']
                downloaded = client.get('/api/resume-intake/me/originals/' + original_key, base_url=cfg.origin)
                self.assertEqual(downloaded.status_code, 200)
                self.assertEqual(downloaded.data, b'Fictional cloud document about a learning project.')
                for path in ('/api/resume-synthesis/me/proposals', '/api/resume-interview/me/turn'):
                    unavailable = client.post(path, base_url=cfg.origin, headers=headers, json={})
                    self.assertEqual(unavailable.status_code, 503, unavailable.text)
                    self.assertIn('manual editor remains available', unavailable.text)
                before = boundary.store.path.read_bytes()
            with ExitStack() as stack:
                restarted = create_application(SOURCE, cfg, stack)
                client = Client(restarted, Response)
                sign_in(client, cfg)
                loaded = client.get('/api/resume-intake/me/draft', base_url=cfg.origin)
                self.assertEqual(loaded.status_code, 200)
                self.assertIn('Fictional cloud draft retained after restart', loaded.text)
                self.assertEqual(before, restarted.store.path.read_bytes())
                self.assertEqual(client.get('/api/resume/me/visitor-preview/sources', base_url=cfg.origin).status_code, 404)

if __name__ == '__main__':
    unittest.main()
