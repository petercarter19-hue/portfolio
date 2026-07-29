import json
import os
import re
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from unittest import mock

os.environ.setdefault('ANTHROPIC_API_KEY', 'test-placeholder')

from app import app
from scripts.release_identity import (
    load_release_id,
    release_id_for_build,
)
from scripts.candidate_artifact import build_manifest, write_manifest
from scripts.verify_deployment_smoke import (
    DEFAULT_CHECKS,
    HttpResult,
    SmokeFailure,
    build_checks,
    fetch_url,
    normalize_base_url,
    verify_checks,
    verify_with_retries,
)


ROOT = os.path.dirname(os.path.dirname(__file__))


class OperationalHealthRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_testing = app.config['TESTING']
        app.config.update(TESTING=True)
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        app.config.update(TESTING=cls.original_testing)

    def test_healthz_is_minimal_public_liveness_json(self):
        response = self.client.get('/healthz')

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                'service': 'peerslate',
                'status': 'ok',
                'release': 'unversioned',
            },
            response.get_json(),
        )
        self.assertEqual('no-store', response.headers['Cache-Control'])
        self.assertEqual('nosniff', response.headers['X-Content-Type-Options'])

    def test_healthz_is_not_search_index_inventory(self):
        sitemap = self.client.get('/sitemap.xml').get_data(as_text=True)
        self.assertNotIn('/healthz', sitemap)

class DeploymentSmokeScriptTests(unittest.TestCase):
    def test_release_identity_is_exact_build_specific_and_loadable(self):
        source_version = 'a' * 40
        release_id = release_id_for_build(source_version, '247')
        self.assertRegex(release_id, r'^[0-9a-f]{24}$')
        self.assertNotEqual(
            release_id,
            release_id_for_build(source_version, '248'),
        )

        payload = json.dumps(
            {
                'schema_version': 1,
                'source_version': source_version,
                'build_id': '247',
                'release': release_id,
            }
        )
        with mock.patch.object(Path, 'read_text', return_value=payload):
            self.assertEqual(release_id, load_release_id(Path('ignored.json')))

    def test_candidate_manifest_hashes_exact_archive_and_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '247.zip'
            archive.write_bytes(b'exact candidate bytes')
            output = Path(directory) / 'candidate-manifest.json'
            manifest = write_manifest(
                archive,
                output,
                source_version='a' * 40,
                source_branch='refs/heads/work/example',
                build_id='247',
                python_version='3.12',
            )

            self.assertEqual(archive.name, manifest['artifact_name'])
            self.assertRegex(manifest['artifact_sha256'], r'^[0-9a-f]{64}$')
            self.assertEqual(2, manifest['schema_version'])
            self.assertEqual(
                {'mode': 'disabled'},
                manifest['candidate_admission'],
            )
            self.assertEqual(
                manifest,
                json.loads(output.read_text(encoding='utf-8')),
            )
            checksum = output.with_suffix('.json.sha256').read_text(
                encoding='ascii'
            )
            self.assertEqual(
                f"{manifest['artifact_sha256']}  247.zip\n",
                checksum,
            )

            archive.write_bytes(b'changed candidate bytes')
            changed = build_manifest(
                archive,
                source_version='a' * 40,
                source_branch='refs/heads/work/example',
                build_id='247',
                python_version='3.12',
            )
            self.assertNotEqual(
                manifest['artifact_sha256'],
                changed['artifact_sha256'],
            )

    def test_candidate_manifest_records_package_exact_sha_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '283.zip'
            archive.write_bytes(b'package exact candidate bytes')

            manifest = build_manifest(
                archive,
                source_version='a' * 40,
                source_branch='refs/heads/work/performance-foundation',
                build_id='283',
                python_version='3.12',
                candidate_package='PS-PERFORMANCE-FOUNDATION-001',
                candidate_source_branch=(
                    'refs/heads/work/performance-foundation'
                ),
                candidate_source_version='a' * 40,
            )

        self.assertEqual(
            {
                'mode': 'package_exact_sha',
                'package_id': 'PS-PERFORMANCE-FOUNDATION-001',
                'source_branch': (
                    'refs/heads/work/performance-foundation'
                ),
                'source_version': 'a' * 40,
            },
            manifest['candidate_admission'],
        )

    def test_candidate_manifest_rejects_incomplete_or_mismatched_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '283.zip'
            archive.write_bytes(b'candidate bytes')
            valid = {
                'source_version': 'a' * 40,
                'source_branch': 'refs/heads/work/performance-foundation',
                'build_id': '283',
                'python_version': '3.12',
                'candidate_package': 'PS-PERFORMANCE-FOUNDATION-001',
                'candidate_source_branch': (
                    'refs/heads/work/performance-foundation'
                ),
                'candidate_source_version': 'a' * 40,
            }
            cases = (
                (
                    {'candidate_source_branch': ''},
                    'requires package, branch, and source version',
                ),
                (
                    {'candidate_package': 'performance-foundation'},
                    'must be a PS-\\* package ID',
                ),
                (
                    {
                        'candidate_package': (
                            '$(printf PS-PERFORMANCE-FOUNDATION-001)'
                        )
                    },
                    'must be a PS-\\* package ID',
                ),
                (
                    {'candidate_source_branch': 'refs/heads/work/other'},
                    'branch does not match',
                ),
                (
                    {'candidate_source_version': 'b' * 40},
                    'version does not match',
                ),
                (
                    {
                        'source_branch': 'refs/heads/main',
                        'candidate_source_branch': 'refs/heads/main',
                    },
                    'cannot target main',
                ),
            )

            for overrides, message in cases:
                with self.subTest(overrides=overrides):
                    values = {**valid, **overrides}
                    with self.assertRaisesRegex(ValueError, message):
                        build_manifest(archive, **values)

    def test_fetch_does_not_follow_redirects(self):
        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header(
                    'Location',
                    'https://example.invalid/unexpected-target',
                )
                self.end_headers()

            def log_message(self, format, *args):
                del format, args

        server = ThreadingHTTPServer(('127.0.0.1', 0), RedirectHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.start()
        try:
            result = fetch_url(
                f'http://127.0.0.1:{server.server_port}/redirect',
                timeout_seconds=1.0,
            )
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join()

        self.assertEqual(302, result.status)

    def test_default_contract_accepts_expected_public_responses(self):
        bodies = {
            '/healthz': (
                'application/json',
                json.dumps(
                    {
                        'service': 'peerslate',
                        'status': 'ok',
                        'release': 'unversioned',
                    }
                ),
                {
                    'cache-control': 'no-store',
                    'x-content-type-options': 'nosniff',
                },
            ),
            '/': (
                'text/html; charset=utf-8',
                (
                    '<title>PeerSlate — Your Work. Your Story. Your Future.'
                    '</title><body class="home-v3-page">'
                ),
                {},
            ),
            '/interview-studio': (
                'text/html; charset=utf-8',
                (
                    '<title>Interview Studio | PeerSlate</title>'
                    '<main data-interview-studio>'
                ),
                {},
            ),
            '/robots.txt': (
                'text/plain; charset=utf-8',
                'Sitemap: https://peerslate.com/sitemap.xml',
                {},
            ),
            '/sitemap.xml': (
                'application/xml; charset=utf-8',
                '<urlset></urlset>',
                {},
            ),
        }

        def fake_fetch(url, timeout_seconds):
            del timeout_seconds
            path = urlparse(url).path
            content_type, body, headers = bodies[path]
            return HttpResult(
                200,
                content_type,
                body.encode('utf-8'),
                headers,
            )

        self.assertEqual(
            [check.path for check in DEFAULT_CHECKS],
            verify_checks('https://example.test', fetcher=fake_fetch),
        )

    def test_default_contract_matches_the_real_flask_public_routes(self):
        with app.test_client() as client:
            def flask_fetch(url, timeout_seconds):
                del timeout_seconds
                response = client.get(
                    urlparse(url).path,
                    base_url='https://peerslate.com',
                )
                return HttpResult(
                    response.status_code,
                    response.headers.get('Content-Type', ''),
                    response.data,
                    dict(response.headers),
                )

            self.assertEqual(
                [check.path for check in DEFAULT_CHECKS],
                verify_checks(
                    'https://peerslate.com',
                    fetcher=flask_fetch,
                ),
            )

    def test_candidate_contract_uses_candidate_host(self):
        checks = build_checks(
            'unversioned',
            base_url='https://candidate.example',
        )
        robots = next(check for check in checks if check.path == '/robots.txt')
        self.assertEqual(
            ('Sitemap: https://candidate.example/sitemap.xml',),
            robots.required_texts,
        )

    def test_contract_rejects_wrong_status(self):
        def fake_fetch(url, timeout_seconds):
            del url, timeout_seconds
            return HttpResult(503, 'text/plain', b'unavailable')

        with self.assertRaisesRegex(SmokeFailure, 'returned 503'):
            verify_checks(
                'https://example.test',
                checks=(DEFAULT_CHECKS[0],),
                fetcher=fake_fetch,
            )

    def test_remote_smoke_requires_https_and_no_credentials(self):
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            normalize_base_url('http://peerslate.com')
        with self.assertRaisesRegex(ValueError, 'credentials'):
            normalize_base_url('https://name:secret@peerslate.com')
        self.assertEqual(
            'http://127.0.0.1:5000',
            normalize_base_url('http://127.0.0.1:5000/'),
        )

    def test_health_contract_rejects_extra_fields_and_missing_headers(self):
        expected = build_checks(release_id_for_build('b' * 40, '247'))[0]

        def extra_field_fetcher(url, timeout_seconds):
            del url, timeout_seconds
            return HttpResult(
                200,
                'application/json',
                json.dumps(
                    {
                        **expected.required_json,
                        'member': 'must-not-appear',
                    }
                ).encode(),
                {
                    'cache-control': 'no-store',
                    'x-content-type-options': 'nosniff',
                },
            )

        with self.assertRaisesRegex(SmokeFailure, 'exact public contract'):
            verify_checks(
                'https://example.test',
                checks=(expected,),
                fetcher=extra_field_fetcher,
            )

        def missing_header_fetcher(url, timeout_seconds):
            del url, timeout_seconds
            return HttpResult(
                200,
                'application/json',
                json.dumps(expected.required_json).encode(),
                {},
            )

        with self.assertRaisesRegex(SmokeFailure, 'cache-control'):
            verify_checks(
                'https://example.test',
                checks=(expected,),
                fetcher=missing_header_fetcher,
            )

    def test_route_specific_markers_reject_generic_branded_error_page(self):
        def generic_fetcher(url, timeout_seconds):
            del url, timeout_seconds
            return HttpResult(
                200,
                'text/html',
                b'<title>PeerSlate</title><p>Interview Studio is unavailable.</p>',
            )

        with self.assertRaisesRegex(SmokeFailure, 'did not contain'):
            verify_checks(
                'https://example.test',
                checks=(DEFAULT_CHECKS[1],),
                fetcher=generic_fetcher,
            )
        with self.assertRaisesRegex(SmokeFailure, 'did not contain'):
            verify_checks(
                'https://example.test',
                checks=(DEFAULT_CHECKS[2],),
                fetcher=generic_fetcher,
            )

    def test_transport_failures_are_normalized_and_retried(self):
        calls = []

        def transient_fetcher(url, timeout_seconds):
            del timeout_seconds
            calls.append(url)
            if len(calls) == 1:
                raise TimeoutError('slow response body')
            return HttpResult(200, 'text/plain', b'ok')

        clock = [0.0]

        def monotonic():
            return clock[0]

        def sleeper(delay):
            clock[0] += delay

        check = DEFAULT_CHECKS[3]
        permissive_check = type(check)(
            '/robots.txt',
            expected_content_type='text/plain',
            required_texts=('ok',),
        )
        self.assertEqual(
            ['/robots.txt'],
            verify_with_retries(
                'https://example.test',
                retry_delay_seconds=1,
                timeout_seconds=1,
                warmup_seconds=5,
                checks=(permissive_check,),
                fetcher=transient_fetcher,
                monotonic=monotonic,
                sleeper=sleeper,
            ),
        )
        self.assertEqual(2, len(calls))

    def test_retry_deadline_exhaustion_returns_smoke_failure(self):
        clock = [0.0]

        def monotonic():
            return clock[0]

        def sleeper(delay):
            clock[0] += delay

        def failing_fetcher(url, timeout_seconds):
            del url, timeout_seconds
            raise ConnectionResetError('connection closed')

        with self.assertRaisesRegex(SmokeFailure, 'transport failed'):
            verify_with_retries(
                'https://example.test',
                retry_delay_seconds=1,
                timeout_seconds=1,
                warmup_seconds=2,
                checks=(DEFAULT_CHECKS[1],),
                fetcher=failing_fetcher,
                monotonic=monotonic,
                sleeper=sleeper,
            )

    def test_json_array_is_rejected_as_wrong_shape(self):
        health_check = DEFAULT_CHECKS[0]

        def fake_fetch(url, timeout_seconds):
            del url, timeout_seconds
            return HttpResult(
                200,
                'application/json',
                b'[]',
                {
                    'cache-control': 'no-store',
                    'x-content-type-options': 'nosniff',
                },
            )

        with self.assertRaisesRegex(SmokeFailure, 'must be an object'):
            verify_checks(
                'https://example.test',
                checks=(health_check,),
                fetcher=fake_fetch,
            )

    def test_pipeline_structure_enforces_exact_postdeploy_contract(self):
        with open(
            os.path.join(ROOT, 'azure-pipelines.yml'),
            encoding='utf-8',
        ) as pipeline_file:
            pipeline = pipeline_file.read()

        stage_matches = list(
            re.finditer(r'(?m)^  - stage: ([A-Za-z0-9_]+)\s*$', pipeline)
        )
        stages = [match.group(1) for match in stage_matches]
        self.assertEqual(
            [
                'Build',
                'Deploy',
                'ProductionSmoke',
                'CandidateDeploy',
                'CandidateSmoke',
                'CandidateStop',
            ],
            stages,
        )
        stage_bodies = {}
        for index, match in enumerate(stage_matches):
            end = (
                stage_matches[index + 1].start()
                if index + 1 < len(stage_matches)
                else len(pipeline)
            )
            stage_bodies[match.group(1)] = pipeline[match.start():end]

        self.assertRegex(stage_bodies['Deploy'], r'(?m)^    dependsOn: Build$')
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')",
            stage_bodies['Deploy'],
        )
        smoke_stage = stage_bodies['ProductionSmoke']
        self.assertRegex(smoke_stage, r'(?m)^    dependsOn: Deploy$')
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')",
            smoke_stage,
        )
        self.assertRegex(
            stage_bodies['CandidateDeploy'],
            r'(?m)^    dependsOn: Build$',
        )
        self.assertNotIn("candidatePackage: ''", pipeline)
        self.assertNotIn("candidateSourceBranch: ''", pipeline)
        self.assertNotIn("candidateSourceVersion: ''", pipeline)
        self.assertIn(
            'Azure pipeline metadata',
            pipeline,
        )
        self.assertIn('candidatePackage, candidateSourceBranch, and', pipeline)
        self.assertIn(
            'a YAML value would shadow the reviewed queue values',
            pipeline,
        )
        self.assertNotIn(
            'refs/heads/work/2026-07-28-sec-edge-reland-001',
            pipeline,
        )
        for stage_name in (
            'CandidateDeploy',
            'CandidateSmoke',
            'CandidateStop',
        ):
            normalized = ' '.join(stage_bodies[stage_name].split())
            self.assertIn(
                "ne(variables['candidatePackage'], '')",
                normalized,
            )
            self.assertIn(
                "eq( variables['Build.SourceBranch'], "
                "variables['candidateSourceBranch'] )",
                normalized,
            )
            self.assertIn(
                "eq( variables['Build.SourceVersion'], "
                "variables['candidateSourceVersion'] )",
                normalized,
            )
        self.assertNotIn('az webapp start', stage_bodies['Deploy'])
        self.assertIn('az webapp start', stage_bodies['CandidateDeploy'])
        self.assertLess(
            stage_bodies['CandidateDeploy'].index('az webapp start'),
            stage_bodies['CandidateDeploy'].index('task: AzureWebApp@1'),
        )
        self.assertRegex(
            stage_bodies['CandidateSmoke'],
            r'(?m)^    dependsOn: CandidateDeploy$',
        )
        self.assertRegex(
            stage_bodies['CandidateStop'],
            r'(?m)^    dependsOn: CandidateSmoke$',
        )

        for expected in (
            'python -m pip check',
            'pip-audit==$(pipAuditVersion)',
            'gitleaks_$(gitleaksVersion)_linux_x64.tar.gz',
            '--config .gitleaks.toml',
            '--redact=100',
            'python -m compileall -q',
            'python scripts/release_identity.py',
            'python scripts/candidate_artifact.py',
            '--candidate-package "$CANDIDATE_PACKAGE"',
            '--candidate-source-branch "$CANDIDATE_SOURCE_BRANCH"',
            '--candidate-source-version "$CANDIDATE_SOURCE_VERSION"',
            'CANDIDATE_PACKAGE: $(candidatePackage)',
            'CANDIDATE_SOURCE_BRANCH: $(candidateSourceBranch)',
            'CANDIDATE_SOURCE_VERSION: $(candidateSourceVersion)',
            'scripts/verify_deployment_smoke.py',
            '--expected-source-version "$(Build.SourceVersion)"',
            '--expected-build-id "$(Build.BuildId)"',
            '--warmup-seconds 180',
            'az webapp start',
            'az webapp stop',
            'test "$state" = "Stopped"',
        ):
            self.assertIn(expected, pipeline)
        for unsafe_macro in (
            '--candidate-package "$(candidatePackage)"',
            '--candidate-source-branch "$(candidateSourceBranch)"',
            '--candidate-source-version "$(candidateSourceVersion)"',
        ):
            self.assertNotIn(unsafe_macro, pipeline)
        self.assertLess(
            pipeline.index('python scripts/release_identity.py'),
            pipeline.index('displayName: Prepare deployment package'),
        )


class ProfessionalReadinessGovernanceTests(unittest.TestCase):
    @staticmethod
    def read(relative_path):
        with open(
            os.path.join(ROOT, *relative_path.split('/')),
            encoding='utf-8',
        ) as file:
            return file.read()

    @staticmethod
    def normalize_whitespace(body):
        return ' '.join(body.split())

    def test_four_gates_emergency_mode_and_honest_status_are_durable(self):
        package = self.normalize_whitespace(
            self.read('docs/initiatives/PS-OPS-001/README.md')
        )
        evidence = self.normalize_whitespace(
            self.read('docs/templates/PROFESSIONAL_READINESS_EVIDENCE.md')
        )

        for expected in (
            'Gate Candidate - Production Candidate Readiness',
            'Gate Launch - Public Launch and Operational Readiness',
            'Gate Operate - Operate and Improve',
            'Gate Retire - Safe Decommissioning',
            'Emergency Release Mode',
            '**Gate Candidate:** `Pass` for build `256`',
            '**Gate Launch:** `Not Assessed`',
            '**Gate Operate:** `Not Assessed`',
            '**Gate Retire:** `Not Assessed`',
            'Production-like staging path',
            'Dependency vulnerability scan',
            'Secret scan',
            'Post-production public smoke',
            'does not reduce the blast radius',
            'immutable promotion record',
            'Gate F owns deployment',
            'When classification is uncertain, treat the release as material',
            'may not classify their own material change as non-material',
            'material shared-pipeline/runtime release',
            'approved for the required Azure PR',
        ):
            self.assertIn(expected, package)

        for expected in (
            'Exact source/artifact/environment identity',
            'Dependency vulnerability scan',
            'Accessibility',
            'SEO/content/indexing',
            'Monitoring/alerts/SLO/RTO/RPO',
            'Backup/restore',
            'Continue / Constrain / Rollback or Disable / Escalate',
            'Emergency-mode evidence',
            'Retire-only evidence',
            'Materiality: Material / Non-material',
            'Final decision authority:',
            'Independent separation-of-duty check:',
        ):
            self.assertIn(expected, evidence)

    def test_existing_controls_link_ps_ops_without_duplicate_approval(self):
        paths_and_phrases = {
            'docs/AI_WORKFLOW.md': (
                'Professional transition gates',
                'PROFESSIONAL_READINESS_EVIDENCE.md',
            ),
            'docs/PEERSLATE_SITE_RULES.md': (
                '/healthz',
                'does not prove',
            ),
            'docs/governance/EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md': (
                'Relationship to professional readiness gates',
                'does not replace or approve it',
            ),
            'docs/governance/AI_DELIVERY_AUDIT_REGISTER.md': (
                'Professional readiness controls',
                'approved Candidate `Pass`',
            ),
            'docs/governance/DOCUMENT_CONTROL.md': (
                'PS-OPS-001 Professional Readiness',
                'all gate decisions Not Assessed',
            ),
            'docs/governance/DECISIONS.md': (
                'Establish professional Candidate, Launch, Operate, and Retire gates',
                'Emergency Release Mode',
            ),
            'docs/governance/CURRENT_BASELINE.yaml': (
                '- id: PS-OPS-001',
                'repository_floor_released_pipeline257_candidate_pass',
            ),
            'docs/governance/CURRENT_STATE.md': (
                'Professional readiness controls (2026-07-26)',
                'Gate Candidate is `Pass` for exact Azure build `256`',
            ),
            'docs/governance/ACTIVE_INITIATIVES.md': (
                'PS-OPS-001 - repository floor released; ongoing gates remain',
                'final governance rechecks passed',
            ),
        }
        for relative_path, phrases in paths_and_phrases.items():
            body = self.normalize_whitespace(self.read(relative_path))
            with self.subTest(path=relative_path):
                for phrase in phrases:
                    self.assertIn(phrase, body)

    def test_current_pointer_lineage_and_ps_ops_authority_are_reconciled(self):
        baseline = self.read('docs/governance/CURRENT_BASELINE.yaml')
        state = self.read('docs/governance/CURRENT_STATE.md')
        initiatives = self.read('docs/governance/ACTIVE_INITIATIVES.md')
        handoff = self.read('docs/governance/MANAGER_SESSION_HANDOFF.md')

        for pr in range(174, 184):
            self.assertRegex(
                baseline,
                rf'(?m)^  .+_pr: {pr}$',
            )
            self.assertRegex(
                state,
                rf'(?m)^\| {pr} \|',
            )
        self.assertIn(
            'deployed_main_commit: "b8e9e26ba0e8cb2bc93fa936c4ddd7985e9f72fb"',
            baseline,
        )
        self.assertIn('deployed_pipeline: 279', baseline)
        self.assertIn('PS-AI-OPS-CHECKPOINT-001', baseline)
        self.assertIn('Professional readiness ongoing gates', initiatives)
        self.assertIn(
            'PS-OPS-001 | **Repository floor released.**',
            handoff,
        )
        self.assertIn(
            'PS-AI-OPS-CHECKPOINT-001 | **Conditional/open.**',
            handoff,
        )


if __name__ == '__main__':
    unittest.main()
