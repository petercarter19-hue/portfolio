import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import run_member_visitor_ai_sql_proof as runner
from tests.test_member_visitor_ai_sql_engine import ENGINE_CASES


class RunnerTests(unittest.TestCase):
    def test_default_plan_never_acquires_resources(self):
        with patch.object(runner.runtime_tools,'acquire_isolated_sql_runtime') as acquire:
            proposal=runner.plan()
        acquire.assert_not_called()
        self.assertEqual(proposal['status'],'proposal_not_executed')
        self.assertEqual(set(proposal['engine_cases']),set(ENGINE_CASES))
        self.assertIn('services/member_visitor_ai_service.py',proposal['source_manifest'])

    def test_E_environment_or_mismatched_F_authority_cannot_execute(self):
        environments=[{}, {'PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE':'authorized'},
            {'PEERSLATE_MEMBER_VISITOR_AI_EXECUTE':'authorized','PEERSLATE_MEMBER_VISITOR_AI_EXPECTED_SHA':'b'*40,
             'PEERSLATE_MEMBER_VISITOR_AI_AUTHORIZATION_REF':'fresh-F'}]
        with TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.json'
            for env in environments:
                with self.subTest(env=env),patch.dict(os.environ,env,clear=True),patch.object(runner,'VisitorRuntime') as runtime:
                    self.assertEqual(runner.execute('a'*40,'fresh-F',path),3)
                    self.assertEqual(json.loads(path.read_text())['status'],'refused')
                    runtime.assert_not_called()

    def test_partial_acquisition_failure_retains_cleanup_custody(self):
        env={'PEERSLATE_MEMBER_VISITOR_AI_EXECUTE':'authorized','PEERSLATE_MEMBER_VISITOR_AI_EXPECTED_SHA':'a'*40,
             'PEERSLATE_MEMBER_VISITOR_AI_AUTHORIZATION_REF':'synthetic-new-F'}
        owned_record={'name':'synthetic','id':'exact-id','marker':'synthetic-marker','kind':'network'}
        def fail(runtime,**kwargs):
            kwargs['owned'].append(owned_record)
            raise RuntimeError('injected acquisition failure')
        with TemporaryDirectory() as directory,patch.dict(os.environ,env,clear=True), \
            patch.object(runner.platform,'system',return_value='Linux'),patch.object(runner.platform,'machine',return_value='x86_64'), \
            patch.object(runner.runtime_tools,'assert_reviewed_source'),patch.object(runner,'VisitorRuntime') as runtime, \
            patch.object(runner.runtime_tools,'acquire_isolated_sql_runtime',side_effect=fail), \
            patch.object(runner.runtime_tools,'cleanup_owned_resources',return_value={'status':'pass'}) as cleanup:
            runtime.return_value._sql_password='synthetic-secret'
            path=Path(directory)/'evidence.json'
            self.assertEqual(runner.execute('a'*40,'synthetic-new-F',path),1)
            cleanup.assert_called_once_with(runtime.return_value,[owned_record])
            result=json.loads(path.read_text())
            self.assertEqual(result['cleanup_status'],'pass'); self.assertEqual(result['proof_status'],'fail')
            self.assertNotIn('synthetic-secret',path.read_text())

    def test_only_exact_inherited_oracle_command_selects_F(self):
        with patch.object(runner.runtime_tools.IsolatedDockerCliRuntime,'_docker',return_value='ok') as docker:
            runtime=runner.VisitorRuntime()
            runtime._docker(['exec','container','python','-B','scripts/run_resume_publication_sql_proof.py','--in-client-oracles'])
            self.assertIn('scripts/run_member_visitor_ai_sql_proof.py',docker.call_args.args[0])
            with self.assertRaises(runner.runtime_tools.EngineProofError):
                runtime._docker(['exec','container','scripts/run_resume_publication_sql_proof.py','--execute'])

    def test_inherited_source_verifier_hashes_E_and_F_paths_without_rewriting(self):
        expected={'scripts/run_resume_publication_sql_proof.py':'a'*64,
                  'scripts/run_member_visitor_ai_sql_proof.py':'b'*64}
        seen=[]
        def process(args,**kwargs):
            # Intercept only the external process; exercise both real adapter layers.
            self.assertEqual(args[0],'docker')
            command=args[1:]
            self.assertEqual(command[:4],['exec',runner.runtime_tools.PROOF_CLIENT_CONTAINER,'python','-c'])
            seen.append(command[-1])
            return subprocess.CompletedProcess(args,0,expected[command[-1]],'')
        runtime=runner.VisitorRuntime(runner=process)
        self.assertEqual(runtime.verify_copied_client_source(runner.runtime_tools.PROOF_CLIENT_CONTAINER,expected),expected)
        self.assertEqual(seen,list(expected))

    def test_inherited_oracle_invocation_selects_F_and_preserves_source_and_evidence(self):
        seen=[]
        payload={'proof_id':runner.PROOF_ID,'source_sha':'a'*40,'status':'pass','cases':{}}
        def process(args,**kwargs):
            command=args[1:]
            seen.append(command)
            if command[0]=='cp':
                Path(command[-1]).write_text(json.dumps(payload),encoding='utf-8')
            return subprocess.CompletedProcess(args,0,'','')
        with TemporaryDirectory() as directory,patch.object(runner.runtime_tools.tempfile,'mkdtemp',return_value=directory):
            runtime=runner.VisitorRuntime(runner=process)
            self.assertEqual(runtime.run_client_oracles(source_sha='a'*40),payload)
        command=seen[0]
        index=command.index('python')
        self.assertEqual(command[index:],['python','-B','scripts/run_member_visitor_ai_sql_proof.py',
            '--in-client-oracles','--source-sha','a'*40,'--evidence',runner.runtime_tools.PROOF_CLIENT_REMOTE_EVIDENCE])
        self.assertNotIn('scripts/run_resume_publication_sql_proof.py',command)
