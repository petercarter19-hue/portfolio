"""Proof admission and topology checks; no Docker, SQL or cloud launch."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run_resume_intake_sql_proof as runner


class IntakeProofRunnerTests(unittest.TestCase):
    def test_owner_fixture_needs_only_platform_tables(self):
        from tests.test_resume_intake_sql_engine import seed_owner
        with patch('tests.test_resume_intake_sql_engine.sql') as execute:
            self.assertEqual(seed_owner(object(), 'a'), 'intake-proof-a')
        query, parameters = execute.call_args.args[1:]
        self.assertIn('INSERT dbo.app_users', query)
        self.assertIn('INSERT dbo.member_profiles', query)
        self.assertNotIn('usp_UpsertAppUserFromAuth', query)
        self.assertEqual(parameters, ('intake-proof-a',))

    def test_failure_evidence_preserves_code_and_drops_content(self):
        from tests.test_resume_intake_sql_engine import bounded_sql_failure
        wrapped = RuntimeError('Isolated intake procedure failed.')
        wrapped.__cause__ = RuntimeError(
            '[42000] [SQL Server]RESUME_INTAKE_VALIDATION private wording (300) '
            '(52603) (SQLExecDirectW); password=never-export')
        result = bounded_sql_failure(wrapped)
        self.assertEqual(result, {'markers': ['RESUME_INTAKE_VALIDATION'],
                                  'native_error_numbers': [52603],
                                  'failure_classes': ['RuntimeError'], 'check_labels': []})
        self.assertNotIn('private wording', json.dumps(result))
        self.assertNotIn('password', json.dumps(result))

    def test_non_sql_failure_exposes_only_allowlisted_class_and_check_label(self):
        from tests.test_resume_intake_sql_engine import bounded_sql_failure, check
        for label, expected in [('reload failed', 'reload failed'),
                                ('private fixture wording', 'unclassified_check')]:
            with self.subTest(label=label):
                try:
                    check(False, label)
                except AssertionError as error:
                    result = bounded_sql_failure(error)
                self.assertEqual(result['failure_classes'], ['OracleCheckFailure'])
                self.assertEqual(result['check_labels'], [expected])
                self.assertNotIn('private fixture wording', json.dumps(result))

    def test_inner_failure_records_fixed_fixture_phase_without_raw_error(self):
        source = 'a' * 40
        def fail(_connect, _root, _cases, diagnostics):
            diagnostics['active_phase'] = 'populated_fixture_owner_a'
            raise RuntimeError('[SQL Server]private fixture words (2812) (SQLExecDirectW)')
        environment = {'PEERSLATE_RESUME_PUBLICATION_SQL_HOST': runner.runtime_tools.PROOF_SQL_CONTAINER,
                       'PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA': source}
        with TemporaryDirectory() as directory, patch.dict(os.environ, environment, clear=True), \
                patch.object(runner.platform, 'system', return_value='Linux'), \
                patch('tests.test_resume_intake_sql_engine.run_engine_contracts', side_effect=fail):
            output = Path(directory) / 'result.json'
            self.assertEqual(runner.inner(source, output), 1)
            result = json.loads(output.read_text())
        self.assertEqual(result['diagnostics']['active_phase'], 'populated_fixture_owner_a')
        self.assertEqual(result['diagnostics']['failure']['native_error_numbers'], [2812])
        self.assertNotIn('private fixture words', json.dumps(result))

    def test_oracle_marker_classification_rejects_unrelated_driver_failures(self):
        from tests.test_resume_intake_sql_engine import expect_marker, has_marker
        marker = 'RESUME_INTAKE_VALIDATION'
        driver = RuntimeError('transport unavailable')
        wrapped = RuntimeError('procedure failed')
        wrapped.__cause__ = RuntimeError(marker)
        self.assertTrue(has_marker(wrapped, marker))
        self.assertFalse(has_marker(driver, marker))
        def fail(error):
            raise error
        expect_marker(lambda: fail(wrapped), marker)
        with self.assertRaises(AssertionError):
            expect_marker(lambda: fail(driver), marker)
        with self.assertRaises(AssertionError):
            expect_marker(lambda: None, marker)

    def test_plan_has_exact_closure_and_honest_unexecuted_state(self):
        plan = runner.plan()
        self.assertEqual(plan['status'], 'proposal_not_executed')
        self.assertFalse(plan['production_authority'])
        self.assertEqual(plan['dependency_closure'][-1]['id'], runner.TARGET)
        self.assertEqual(len(plan['generic_gate_migrations']), 6)
        self.assertEqual(plan['topology'], {'internal_network': True,
            'host_ports': False, 'mounts': False, 'docker_socket': False})
        for item in plan['dependency_closure']:
            self.assertIn(item['forward'], plan['source_manifest'])
            self.assertIn(item['rollback'], plan['source_manifest'])
            self.assertEqual(len(plan['executable_digests'][item['id']]['forward']), 64)
        self.assertEqual(runner.plan_digest(), hashlib.sha256(json.dumps(
            plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest())

    def test_authorization_binds_source_plan_and_fresh_operation(self):
        source, authorization, digest = 'a' * 40, 'owner-operation:intake-test', runner.plan_digest()
        environment = {'PEERSLATE_RESUME_INTAKE_EXECUTE': 'authorized',
            'PEERSLATE_RESUME_INTAKE_EXPECTED_SHA': source,
            'PEERSLATE_RESUME_INTAKE_AUTHORIZATION_REF': authorization,
            'PEERSLATE_RESUME_INTAKE_PLAN_DIGEST': digest}
        with patch.dict(os.environ, environment):
            self.assertTrue(runner.authorized(source, authorization, digest))
            self.assertFalse(runner.authorized('b' * 40, authorization, digest))
            self.assertFalse(runner.authorized(source, 'old-operation', digest))
            self.assertFalse(runner.authorized(source, authorization, '0' * 64))

    def test_refusal_precedes_resource_acquisition(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), \
                patch.object(runner.runtime_tools, 'acquire_isolated_sql_runtime') as acquire:
            path = Path(directory) / 'refusal.json'
            self.assertEqual(runner.execute('a' * 40, 'unauthorized', path), 3)
            self.assertEqual(json.loads(path.read_text())['status'], 'refused')
            acquire.assert_not_called()

    def test_windows_host_refusal_precedes_any_runtime(self):
        with TemporaryDirectory() as directory, patch.object(runner, 'authorized', return_value=True), \
                patch.object(runner.platform, 'system', return_value='Windows'), \
                patch.object(runner, 'IntakeRuntime') as runtime:
            self.assertEqual(runner.execute('a' * 40, 'owner-operation', Path(directory)/'result.json'), 3)
            runtime.assert_not_called()

    def test_entrypoint_override_preserves_source_verification_argument(self):
        old = 'scripts/run_resume_publication_sql_proof.py'
        container = runner.runtime_tools.PROOF_CLIENT_CONTAINER
        runtime = runner.IntakeRuntime()
        with patch.object(runner.runtime_tools.IsolatedDockerCliRuntime, '_docker') as docker:
            runtime._docker(['exec', container, 'python', '-c', 'hash file', old])
            self.assertEqual(docker.call_args.args[0][-1], old)
            runtime._docker(['exec', container, 'python', '-B', old, '--in-client-oracles'])
            self.assertEqual(docker.call_args.args[0][-2], 'scripts/run_resume_intake_sql_proof.py')
            with self.assertRaises(runner.runtime_tools.EngineProofError):
                runtime._docker(['exec', container, 'python', old])

    def test_manual_pipeline_has_closed_admission_parameters(self):
        text = (runner.ROOT/'azure-pipelines-resume-intake-sql-proof.yml').read_text()
        self.assertIn('trigger: none', text)
        self.assertIn('pr: none', text)
        self.assertIn('schedules: []', text)
        self.assertIn('default: false', text)
        self.assertIn('expectedPlanDigest', text)
        self.assertIn('--expected-plan-digest', text)
        self.assertNotIn('configure_mvp1_acceptance_sql_authority', text)
        self.assertNotIn('AZURE_SQL_CONNECTIONSTRING', text)


if __name__ == '__main__':
    unittest.main()
