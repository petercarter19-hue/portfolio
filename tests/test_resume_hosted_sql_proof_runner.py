"""Hosted proof admission tests. No SQL, Docker, cloud, or wheel installation."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts import run_resume_hosted_sql_proof as runner

class HostedProofRunnerTests(unittest.TestCase):
    def test_generic_gate_failure_preserves_classification_without_secret_output(self):
        from subprocess import CompletedProcess
        from tests.test_resume_hosted_sql_engine import run_generic_gate
        secret='sensitive-password-(54212) (SQLExecDirectW)'
        dsn='Server=private-host;Database=private-db;UID=private-user;PWD='+secret+';'
        failed=CompletedProcess(['private-command',dsn],1,
            stdout=b'  [1] prerequisites - synthetic\n  [2] forward apply - 3 object(s) created\n  [3] re-apply is a no-op - objects and ledger unchanged\nFAILED: verifier did not return verified = 1 against the gate database.\n',
            stderr=('ProgrammingError: private source words '+dsn+' (54213) (SQLExecDirectW)').encode())
        with TemporaryDirectory() as directory, patch('tests.test_resume_hosted_sql_engine.subprocess.run',return_value=failed):
            diagnostics={}
            with self.assertRaises(AssertionError):
                run_generic_gate(Path(directory),'PS-VISITOR-AI-001','synthetic-db',Path(directory)/'gate.json',
                    {'MSSQL_SA_PASSWORD':secret,'AZURE_SQL_CONNECTIONSTRING':dsn},diagnostics)
        observed=diagnostics['generic_gate_failure']
        self.assertEqual(observed['migration'],'PS-VISITOR-AI-001')
        self.assertEqual(observed['returncode'],1)
        self.assertEqual(observed['last_completed_step'],'re-apply is a no-op')
        self.assertEqual(observed['failed_stage'],'verification')
        self.assertEqual(observed['check_markers'],['verifier_missing_verified'])
        self.assertEqual(observed['public_error_classes'],['ProgrammingError'])
        self.assertEqual(observed['native_error_numbers'],[54213])
        for value in (secret,dsn,'private-command','private-host','private-db','private-user','private source words','stdout','stderr'):
            self.assertNotIn(value,json.dumps(diagnostics))
        self.assertLess(len(json.dumps(diagnostics)),1024)

    def test_generic_gate_timeout_preserves_bounded_partial_steps_without_command(self):
        from subprocess import TimeoutExpired
        from tests.test_resume_hosted_sql_engine import run_generic_gate
        failed=TimeoutExpired(['private-command','password=secret'],240,
            output=b'  [1] prerequisites - private content\n',stderr=b'password=secret;')
        with TemporaryDirectory() as directory, patch('tests.test_resume_hosted_sql_engine.subprocess.run',side_effect=failed) as call:
            diagnostics={}
            with self.assertRaises(AssertionError):
                run_generic_gate(Path(directory),'PS-VISITOR-AI-001','synthetic',Path(directory)/'gate.json',{},diagnostics)
            call.assert_called_once()
            self.assertEqual(call.call_args.kwargs['timeout'],240)
        observed=diagnostics['generic_gate_failure']
        self.assertTrue(observed['timed_out'])
        self.assertIsNone(observed['returncode'])
        self.assertEqual(observed['last_completed_step'],'prerequisites')
        for value in ('private-command','secret','private content'):
            self.assertNotIn(value,json.dumps(diagnostics))

    def test_generic_gate_requires_emitted_evidence_and_success_has_no_failure(self):
        from subprocess import CompletedProcess
        from tests.test_resume_hosted_sql_engine import run_generic_gate
        with TemporaryDirectory() as directory, patch('tests.test_resume_hosted_sql_engine.subprocess.run',return_value=CompletedProcess([],0,b'',b'')):
            output=Path(directory)/'gate.json';diagnostics={}
            with self.assertRaises(AssertionError):run_generic_gate(Path(directory),'PS-VISITOR-AI-001','synthetic',output,{},diagnostics)
            self.assertTrue(diagnostics['generic_gate_failure']['evidence_missing'])
            output.write_text('{}');diagnostics={}
            run_generic_gate(Path(directory),'PS-VISITOR-AI-001','synthetic',output,{},diagnostics)
            self.assertEqual(diagnostics,{})

    def test_hosted_failure_evidence_is_content_free(self):
        from tests.test_resume_hosted_sql_engine import bounded_sql_failure
        result=bounded_sql_failure(RuntimeError('ORIGINAL_ROLLBACK_HAS_MEMBER_DATA private wording password=secret (52610) (SQLExecDirectW)'))
        self.assertEqual(result['markers'],['ORIGINAL_ROLLBACK_HAS_MEMBER_DATA'])
        self.assertEqual(result['native_error_numbers'],[52610])
        self.assertNotIn('private wording',json.dumps(result))
        self.assertNotIn('secret',json.dumps(result))

    def test_exact_hosted_plan_and_unchanged_substrate(self):
        plan=runner.plan()
        self.assertEqual(plan['status'],'proposal_not_executed')
        self.assertFalse(plan['production_authority'])
        self.assertEqual(plan['dependency_closure'][-1]['id'],'PS-RESUME-HOSTED-001')
        self.assertEqual(plan['generic_gate_migrations'],list(runner.GATE_MIGRATIONS))
        self.assertEqual(len(plan['generic_gate_migrations']),7)
        self.assertEqual(plan['declared_closure_targets'],['PS-RESUME-IDENTITY-001','PS-RESUME-HOSTED-001'])
        self.assertEqual(plan['topology'],dict(internal_network=True,host_ports=False,mounts=False,docker_socket=False))
        self.assertEqual(plan['sql_image'],runner.runtime_tools.SQL_IMAGE)
        self.assertEqual(plan['client_image'],runner.runtime_tools.CLIENT_IMAGE)
        for row in plan['dependency_closure']:
            self.assertIn(row['forward'],plan['source_manifest'])
            self.assertIn(row['rollback'],plan['source_manifest'])
        self.assertNotIn('av==',(runner.ROOT/'requirements-resume-publication-sql-proof.txt').read_text())
        self.assertEqual(runner.plan_digest(),hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest())

    def test_refusal_before_resources_or_runtime(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ,{},clear=True), \
                patch.object(runner.runtime_tools,'acquire_isolated_sql_runtime') as acquire, \
                patch.object(runner,'HostedRuntime') as runtime:
            output=Path(directory)/'refusal.json'
            self.assertEqual(runner.execute('a'*40,'missing',output),3)
            self.assertEqual(json.loads(output.read_text())['status'],'refused')
            acquire.assert_not_called();runtime.assert_not_called()

    def test_exact_hosted_authority_cannot_reuse_intake(self):
        source='a'*40; authorization='owner-operation:hosted-local-fixture'; digest=runner.plan_digest()
        selected={'PEERSLATE_RESUME_HOSTED_EXECUTE':'authorized',
            'PEERSLATE_RESUME_HOSTED_EXPECTED_SHA':source,'PEERSLATE_RESUME_HOSTED_AUTHORIZATION_REF':authorization,
            'PEERSLATE_RESUME_HOSTED_PLAN_DIGEST':digest}
        with patch.dict(os.environ,selected,clear=True):
            self.assertTrue(runner.authorized(source,authorization,digest))
            self.assertFalse(runner.authorized('b'*40,authorization,digest))
            self.assertFalse(runner.authorized(source,'old-operation',digest))
            self.assertFalse(runner.authorized(source,authorization,'0'*64))
        old={key.replace('_HOSTED_','_INTAKE_'):value for key,value in selected.items()}
        with patch.dict(os.environ,old,clear=True):self.assertFalse(runner.authorized(source,authorization,digest))

    def test_unsupported_host_refuses_without_runtime(self):
        with TemporaryDirectory() as directory, patch.object(runner,'authorized',return_value=True), \
                patch.object(runner.platform,'system',return_value='Windows'), \
                patch.object(runner,'HostedRuntime') as runtime:
            self.assertEqual(runner.execute('a'*40,'owner-operation',Path(directory)/'result.json'),3)
            runtime.assert_not_called()

    def test_entrypoint_override_preserves_e_source_hash_and_cleanup(self):
        old='scripts/run_resume_publication_sql_proof.py';container=runner.runtime_tools.PROOF_CLIENT_CONTAINER
        runtime=runner.HostedRuntime()
        with patch.object(runner.runtime_tools.IsolatedDockerCliRuntime,'_docker') as docker:
            runtime._docker(['exec',container,'python','-c','hash file',old])
            self.assertEqual(docker.call_args.args[0][-1],old)
            runtime._docker(['exec',container,'python','-B',old,'--in-client-oracles'])
            self.assertEqual(docker.call_args.args[0][-2],'scripts/run_resume_hosted_sql_proof.py')
            with self.assertRaises(runner.runtime_tools.EngineProofError):runtime._docker(['exec',container,'python',old])
        self.assertIs(runner.HostedRuntime.remove,runner.runtime_tools.IsolatedDockerCliRuntime.remove)
        self.assertIs(runner.HostedRuntime.resource_id_present,runner.runtime_tools.IsolatedDockerCliRuntime.resource_id_present)

    def test_manual_pipeline_and_finite_oracle_inventory(self):
        from tests.test_resume_hosted_sql_engine import ENGINE_CASES
        text=(runner.ROOT/'azure-pipelines-resume-hosted-sql-proof.yml').read_text()
        for marker in ['trigger: none','pr: none','schedules: []','default: false','expectedPlanDigest','--expected-plan-digest']:
            self.assertIn(marker,text)
        self.assertNotIn('AZURE_SQL_CONNECTIONSTRING',text)
        self.assertNotIn('pip install',text)
        self.assertEqual(len(ENGINE_CASES),13)
        self.assertEqual(len(ENGINE_CASES),len(set(ENGINE_CASES)))
        self.assertEqual(len(runner.GATE_MIGRATIONS),7)
        self.assertEqual(runner.GATE_MIGRATIONS[-1],'PS-RESUME-HOSTED-001')

if __name__=='__main__':unittest.main()
