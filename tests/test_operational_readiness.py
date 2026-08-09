import json
import os
import re
import threading
import tempfile
import tomllib
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


class GitleaksConfigurationTests(unittest.TestCase):
    def test_community_false_positive_allowlists_stay_exact_and_conjunctive(
        self,
    ):
        with open(os.path.join(ROOT, '.gitleaks.toml'), 'rb') as config_file:
            allowlists = tomllib.load(config_file)['allowlists']

        # Any additional suppression is a new security decision that must
        # update this regression explicitly.
        self.assertEqual(3, len(allowlists))
        self.assertEqual(
            {
                'description': (
                    'Known non-secret member UUID used only as a '
                    'deterministic test fixture.'
                ),
                'targetRules': ['generic-api-key'],
                'regexes': [
                    r'^45ab728a-44bc-4f80-a79f-d010e04d5453$'
                ],
            },
            allowlists[0],
        )

        community_doc_path = ''.join(
            (
                r'^docs/initiatives/',
                'PS-COMMUNITY-',
                'PUBLIC-PILOT-001/',
                'PRIMARY_FEED_',
                'ARCHITECTURE_',
                'AMENDMENT_',
                r'2026-08-01\.md$',
            )
        )
        community_doc_line = ''.join(
            (
                r'^\s*server audio, ',
                'no content-bearing logs, ',
                'owner-only ',
                'access, ',
                r'size/duration and\s*$',
            )
        )

        # These were pinned to three branch commit SHAs until 2026-08-04. The
        # Community pull request was squash-merged, which rewrites every branch
        # commit into one new SHA, so all three pins stopped matching at once,
        # the two false positives they covered reappeared as leaks, and the
        # deploy for the merge commit failed. Squash merge is this repository's
        # required strategy, so pinning guaranteed that outcome. They are now
        # scoped by path and exact line instead, which survives the merge and
        # is still narrow enough that any other line in the file fails the scan.
        expected = {
            r'^services/community_cursor\.py$': (
                r'^\s*token,\s+max_age='
                r'CURSOR_MAX_AGE_SECONDS\s*$'
            ),
            community_doc_path: community_doc_line,
        }

        scoped = [
            allowlist for allowlist in allowlists if 'paths' in allowlist
        ]
        self.assertEqual(
            {allowlist['paths'][0] for allowlist in scoped},
            set(expected),
        )
        for allowlist in scoped:
            path = allowlist['paths'][0]
            self.assertEqual(['generic-api-key'], allowlist['targetRules'])
            self.assertEqual('AND', allowlist['condition'])
            self.assertEqual(1, len(allowlist['paths']))
            self.assertEqual('line', allowlist['regexTarget'])
            self.assertEqual([expected[path]], allowlist['regexes'])
            self.assertNotIn(
                'commits',
                allowlist,
                'a commit-pinned allowlist cannot survive a squash merge',
            )


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

    def test_candidate_manifest_accepts_pr_merge_validation_without_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '352.zip'
            archive.write_bytes(b'pr validation candidate bytes')

            manifest = build_manifest(
                archive,
                source_version='a' * 40,
                source_branch='refs/pull/245/merge',
                build_id='352',
                python_version='3.12',
            )

        self.assertEqual('refs/pull/245/merge', manifest['source_branch'])
        self.assertEqual({'mode': 'disabled'}, manifest['candidate_admission'])

    def test_candidate_manifest_rejects_candidate_inputs_on_pr_merge_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '352.zip'
            archive.write_bytes(b'pr validation candidate bytes')
            valid = {
                'source_version': 'a' * 40,
                'source_branch': 'refs/pull/245/merge',
                'build_id': '352',
                'python_version': '3.12',
            }
            cases = (
                {'candidate_package': 'PS-PERFORMANCE-FOUNDATION-001'},
                {
                    'candidate_source_branch': (
                        'refs/heads/work/performance-foundation'
                    )
                },
                {'candidate_source_version': 'a' * 40},
                {
                    'candidate_package': 'PS-PERFORMANCE-FOUNDATION-001',
                    'candidate_source_branch': (
                        'refs/heads/work/performance-foundation'
                    ),
                    'candidate_source_version': 'a' * 40,
                },
            )

            for candidate_inputs in cases:
                with self.subTest(candidate_inputs=candidate_inputs):
                    with self.assertRaisesRegex(
                        ValueError,
                        'not permitted for Azure PR merge validation builds',
                    ):
                        build_manifest(archive, **valid, **candidate_inputs)

    def test_candidate_manifest_rejects_malformed_pr_merge_refs(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / '352.zip'
            archive.write_bytes(b'pr validation candidate bytes')
            malformed_refs = (
                'refs/pull/0/merge',
                'refs/pull/01/merge',
                'refs/pull/245/head',
                'refs/pull/245',
                'refs/pull/245/merge/extra',
                'refs/pull/not-a-number/merge',
                'refs/tags/v1.0.0',
            )

            for source_branch in malformed_refs:
                with self.subTest(source_branch=source_branch):
                    with self.assertRaisesRegex(
                        ValueError,
                        'source branch must be a refs/heads branch or exact '
                        'Azure PR merge validation ref',
                    ):
                        build_manifest(
                            archive,
                            source_version='a' * 40,
                            source_branch=source_branch,
                            build_id='352',
                            python_version='3.12',
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
                    {'candidate_source_branch': 'refs/pull/245/merge'},
                    'candidate source branch must be a refs/heads branch',
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
                'ProductionOperation',
                'ProductionReleaseSkipped',
                'CandidateDeploy',
                'CandidateSmoke',
                'CandidateStop',
                'CommunityMaintenance',
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

        candidate_artifact_display_name = (
            'displayName: Record immutable candidate artifact hash'
        )
        self.assertEqual(1, pipeline.count(candidate_artifact_display_name))
        candidate_artifact_step = re.search(
            r'(?ms)^          - script: >-\n'
            r'              python scripts/candidate_artifact\.py\n'
            r'.*?^            '
            + re.escape(candidate_artifact_display_name)
            + r'\n.*?(?=^          - |\Z)',
            stage_bodies['Build'],
        )
        self.assertIsNotNone(candidate_artifact_step)
        candidate_artifact_body = candidate_artifact_step.group()
        # The script admits the exact disabled PR-validation form and rejects
        # Candidate inputs there. It must therefore run for every build source:
        # a task condition keyed to branch or reason could otherwise skip the
        # fail-closed validator while later Candidate-stage conditions see
        # matching queue inputs.
        self.assertNotRegex(
            candidate_artifact_body,
            r'(?m)^            condition\s*:',
        )

        production_stage = stage_bodies['ProductionOperation']
        self.assertIn('batch: true', pipeline)
        self.assertIn('name: forceProductionDeploy', pipeline)
        self.assertIn('type: boolean', pipeline)
        self.assertIn('default: false', pipeline)
        self.assertIn('name: manualProductionSourceVersion', pipeline)
        self.assertRegex(
            pipeline,
            r'(?ms)- name: manualProductionSourceVersion.*?default: \'\'',
        )
        self.assertIn(
            'python scripts/production_operation_preflight.py',
            production_stage,
        )
        self.assertIn('SYSTEM_ACCESSTOKEN: $(System.AccessToken)', production_stage)
        self.assertIn(
            'MANUAL_SOURCE_VERSION: '
            '${{ parameters.manualProductionSourceVersion }}',
            production_stage,
        )
        self.assertRegex(production_stage, r'(?m)^    dependsOn: Build$')
        self.assertRegex(
            production_stage,
            r'(?m)^    lockBehavior: sequential$',
        )
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')",
            production_stage,
        )
        self.assertIn(
            "ne(variables['Build.Reason'], 'Manual')",
            production_stage,
        )
        self.assertIn(
            '${{ eq(parameters.forceProductionDeploy, true) }}',
            production_stage,
        )
        self.assertEqual(1, production_stage.count('deployment: DeployWebApp'))
        self.assertEqual(
            1,
            production_stage.count(
                'displayName: Verify liveness and canonical public routes'
            ),
        )
        self.assertLess(
            production_stage.index('task: AzureWebApp@1'),
            production_stage.index(
                'python scripts/verify_deployment_smoke.py'
            ),
        )
        # Build 443 deployed correctly but reported `failed`: the container
        # answered /healthz about 25 seconds after the 180-second budget ran
        # out. Production cold start on this plan must fit inside the budget,
        # or a real release keeps being reported as a failure.
        self.assertIn('--warmup-seconds 420', production_stage)
        self.assertNotIn('--warmup-seconds 180', production_stage)

        # A manual main run that skips the deploy must announce itself rather
        # than report a bare success.
        skipped_stage = stage_bodies['ProductionReleaseSkipped']
        self.assertRegex(skipped_stage, r'(?m)^    dependsOn: Build$')
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')",
            skipped_stage,
        )
        self.assertIn(
            "eq(variables['Build.Reason'], 'Manual')",
            skipped_stage,
        )
        self.assertIn(
            '${{ eq(parameters.forceProductionDeploy, false) }}',
            skipped_stage,
        )
        self.assertIn(
            "${{ eq(parameters.schemaAction, 'none') }}",
            skipped_stage,
        )
        self.assertIn('##vso[task.logissue type=warning]', skipped_stage)
        self.assertIn(
            '##vso[task.complete result=SucceededWithIssues;]',
            skipped_stage,
        )
        # It reports only; it must never touch the web app.
        self.assertNotIn('AzureWebApp@1', skipped_stage)
        self.assertNotIn('az webapp', skipped_stage)

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
        self.assertNotIn('az webapp start', production_stage)
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
            # Production uses 420 (see the postdeploy-contract test); the
            # isolated candidate keeps the shorter 180-second budget.
            '--warmup-seconds 420',
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

    def test_schema_migration_stage_is_deliberate_gated_and_fail_closed(self):
        """Database schema must never move because a pull request merged.

        Three schema applies reached production in one week by an agent
        connecting directly with a credential read out of App Service settings.
        Every one of them contradicted this repository's own statement that
        Azure DevOps is the only production deployment path. This stage is the
        replacement, and these assertions are the properties that make it a
        control rather than a habit.
        """

        with open(
            os.path.join(ROOT, 'azure-pipelines.yml'),
            encoding='utf-8',
        ) as pipeline_file:
            pipeline = pipeline_file.read()

        stage_matches = list(
            re.finditer(r'(?m)^  - stage: ([A-Za-z0-9_]+)\s*$', pipeline)
        )
        stage_bodies = {}
        for index, match in enumerate(stage_matches):
            end = (
                stage_matches[index + 1].start()
                if index + 1 < len(stage_matches)
                else len(pipeline)
            )
            stage_bodies[match.group(1)] = pipeline[match.start():end]
        schema_stage = stage_bodies['ProductionOperation']
        schema_jobs = schema_stage.split(
            '- job: SchemaReadOnlyPreflight', 1
        )[1]
        schema_mutation_job = schema_stage.split(
            '- deployment: GovernedSchemaMigration', 1
        )[1]
        production_job = schema_stage.split('- deployment: DeployWebApp', 1)[1]
        production_job = production_job.split('- job: SchemaReadOnlyPreflight', 1)[0]

        # 1. Never automatic. The trigger is a queue-time parameter that
        #    defaults to doing nothing, plus an environment an approver must
        #    release.
        self.assertIn('name: schemaAction', pipeline)
        self.assertRegex(
            pipeline,
            r'(?ms)- name: schemaAction.*?default: none',
        )
        self.assertRegex(
            pipeline,
            r'(?ms)- name: schemaAction.*?values:\s*\n'
            r'\s*- none\s*\n\s*- report\s*\n\s*- apply\s*\n\s*- rollback',
        )
        self.assertIn(
            "${{ ne(parameters.schemaAction, 'none') }}",
            schema_stage,
        )
        self.assertIn(
            'environment: peerslate-database-schema', schema_mutation_job
        )
        # Only main. A task branch must not be able to move production schema.
        self.assertIn(
            "eq(variables['Build.SourceBranch'], 'refs/heads/main')",
            schema_stage,
        )
        # A queued schema run must be serialized, never dropped for a later
        # one: schema is not a cumulative artifact.
        self.assertRegex(schema_stage, r'(?m)^    lockBehavior: sequential$')
        self.assertRegex(schema_stage, r'(?m)^    dependsOn: Build$')

        # 2. Fail closed before connecting. The offline registry and gate-proof
        #    validation runs first, and it runs for every action.
        self.assertIn('SchemaReadOnlyPreflight', schema_stage)
        self.assertIn('preflight "$SCHEMA_ACTION"', schema_jobs)
        self.assertIn('artifact: SchemaPreflightEvidence', schema_jobs)
        self.assertIn(
            'mkdir -p "$(Build.ArtifactStagingDirectory)/schema-preflight"',
            schema_jobs,
        )
        self.assertLess(
            schema_stage.index('- job: SchemaReadOnlyPreflight'),
            schema_stage.index('- deployment: GovernedSchemaMigration'),
        )
        self.assertIn(
            'python scripts/govern_sql_migrations.py check', schema_jobs
        )
        self.assertLess(
            schema_jobs.index('govern_sql_migrations.py check'),
            schema_jobs.index('- deployment: GovernedSchemaMigration'),
        )

        # 3. Each action is its own guarded step, and the target database is
        #    named and confirmed rather than inherited from whatever the
        #    connection string happens to say.
        for action in ('report', 'apply', 'rollback'):
            self.assertIn(
                "${{ if eq(parameters.schemaAction, '%s') }}" % action,
                schema_mutation_job,
            )
        self.assertEqual(
            3,
            schema_mutation_job.count('--expect-database "$(schemaDatabaseName)"'),
        )
        self.assertIn("schemaDatabaseName: 'peerslate-database'", pipeline)
        # Every action renders the repository's record of what production
        # carries, so the record cannot be forgotten.
        self.assertEqual(3, schema_mutation_job.count('--write-state'))
        self.assertEqual(3, schema_mutation_job.count('--azure-pipelines'))
        self.assertIn('--migration "$SCHEMA_MIGRATION_ID"', schema_mutation_job)
        self.assertIn('--expect "$SCHEMA_MIGRATION_ID"', schema_mutation_job)

        # 4. Rollback is deliberately awkward: two independently typed queue
        #    values must agree before anything destructive runs.
        self.assertIn('name: schemaRollbackConfirm', pipeline)
        self.assertIn('--confirm "$SCHEMA_ROLLBACK_CONFIRM"', schema_mutation_job)
        self.assertIn(
            'SCHEMA_ROLLBACK_CONFIRM: ${{ parameters.schemaRollbackConfirm }}',
            schema_mutation_job,
        )

        # 5. Credentials come from a secret pipeline variable and reach the
        #    script as process environment data, never as Bash source and never
        #    from App Service settings read by an agent.
        self.assertEqual(
            3,
            schema_mutation_job.count(
                'AZURE_SQL_CONNECTIONSTRING: $(schemaConnectionString)'
            ),
        )
        self.assertNotIn('echo $(schemaConnectionString)', pipeline)
        self.assertNotIn('az webapp config appsettings list', pipeline)
        for leaked in (
            '$(schemaConnectionString)"',
            "'$(schemaConnectionString)'",
        ):
            self.assertNotIn(f'echo {leaked}', pipeline)

        # 6. This stage moves schema only. It must never deploy the web app,
        #    and the production deploy must never touch a database.
        self.assertNotIn('AzureWebApp@1', schema_jobs)
        self.assertNotIn('az webapp', schema_jobs)
        self.assertNotIn('govern_sql_migrations.py', production_job)
        self.assertNotIn(
            'govern_sql_migrations.py',
            stage_bodies['ProductionReleaseSkipped'],
        )

        # 7. Evidence survives the agent.
        self.assertIn('artifact: SchemaMigrationEvidence', schema_mutation_job)
        self.assertEqual(3, schema_mutation_job.count('--emit-evidence'))

        # The existing production controls must be untouched by all of this.
        production_stage = stage_bodies['ProductionOperation']
        self.assertIn(
            '${{ eq(parameters.forceProductionDeploy, true) }}',
            production_stage,
        )
        self.assertIn(
            '${{ eq(parameters.forceProductionDeploy, false) }}',
            stage_bodies['ProductionReleaseSkipped'],
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
            'Gate Candidate - Protected promotion',
            'Gate Launch - material audience expansion',
            'Gate Operate - meaningful operating milestone',
            'Gate Retire - shutdown/destructive removal',
            'Emergency release',
            'Routine and Bounded releases use the normal PR',
            'do not require a Candidate admission record',
            'exact source SHA, immutable artifact',
            'newly load-bearing production settings',
            'stop/rollback action and operator',
            '`Pass`, `Conditional`, `Fail`, or `Not Assessed`',
            'does not block Routine or Bounded delivery',
            'CANDIDATE_EVIDENCE_2026-07-27.md',
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

    def test_azure_release_reliability_rules_are_durable(self):
        package = self.normalize_whitespace(
            self.read('docs/initiatives/PS-OPS-001/README.md')
        )

        for expected in (
            'Azure production release reliability',
            'automatic Azure run for a merged `main` SHA is authoritative',
            'same-SHA fallback while the automatic run exists',
            'manual production deployment must be an explicit',
            'Production deployment and its exact source/build smoke',
            'Batch rapid `main` changes',
            'Once ZipDeploy/Oryx has begun, do not cancel casually',
            'Classify every red record by pipeline, branch, reason',
            'Target-branch movement expires the prior result',
            'final squash commit message',
        ):
            self.assertIn(expected, package)

    def test_existing_controls_link_ps_ops_without_duplicate_approval(self):
        paths_and_phrases = {
            'docs/AI_WORKFLOW.md': (
                'Protected release',
                '`PS-OPS-001`',
            ),
            'docs/PEERSLATE_SITE_RULES.md': (
                '/healthz',
                'OPS gates apply only',
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
                'A specialist standard only in its stated risk domain',
                'smallest authoritative record',
            ),
            'docs/governance/DECISIONS.md': (
                'Establish professional Candidate, Launch, Operate, and Retire gates',
                'Emergency Release Mode',
            ),
            'docs/governance/CURRENT_BASELINE.yaml': (
                'id: candidate_admission',
                'resolved by PS-OPS-CANDIDATE-ADMISSION-001',
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

        self.assertIn('schema_version: 5', baseline)
        self.assertIn('version: "3.0"', baseline)
        self.assertIn('PeerSlate_Constitution_v3.0.md', baseline)
        self.assertIn('PeerSlate_Roadmap_v3.0.md', baseline)
        self.assertNotIn('\nholds:', baseline)
        # These pointers move in lockstep with each release-evidence record in
        # CURRENT_BASELINE.yaml. PR 228 updated the baseline for the PR 223
        # release but not these expectations, and its [skip ci] merge meant no
        # pipeline ran to catch that until the next runtime merge (pipeline
        # 329) failed on it. Update both files in the same commit, and do not
        # record release evidence with [skip ci] unless this test was run
        # locally against the exact record being merged.
        self.assertIn(
            'deployed_main_commit: "7a7c99de085a8d25ab12ce386c7cb2509cda2057"',
            baseline,
        )
        self.assertIn('deployed_pipeline: 711', baseline)
        expected_release = release_id_for_build(
            '7a7c99de085a8d25ab12ce386c7cb2509cda2057',
            '711',
        )
        self.assertIn(f'/healthz release {expected_release}', baseline)
        self.assertIn(
            'application_behavior_commit: "7a7c99de085a8d25ab12ce386c7cb2509cda2057"',
            baseline,
        )
        self.assertIn('application_behavior_pipeline: 711', baseline)
        self.assertIn('PS-AZURE-RELEASE-RELIABILITY-001', baseline)
        self.assertIn('PS-DELIVERY-RESET-001', baseline)
        self.assertIn('PS-GOV-LEAN-001', baseline)
        self.assertIn('Historical narrative snapshot', state)
        self.assertIn('Historical lane snapshot', initiatives)
        self.assertIn('Use this only when another person or agent will continue', handoff)
        self.assertLess(len(handoff.split()), 300)


if __name__ == '__main__':
    unittest.main()
