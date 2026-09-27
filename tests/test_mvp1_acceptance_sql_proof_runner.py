import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from scripts import run_mvp1_acceptance_sql_proof as runner
from tests.test_mvp1_acceptance_sql_engine import (
    ENGINE_CASES, commit_draft_sql, observe_preview_failure, _preview_token_shape)


class RunnerTests(unittest.TestCase):
    def test_failed_token_encodings_compare_only_exact_eight_bytes(self):
        import base64
        current = '000000000000092f'
        raw = bytes.fromhex(current)
        examples = {
            'plain_hex': current.upper(), 'prefixed_hex': '0x' + current,
            'base64': base64.b64encode(raw).decode('ascii'),
            'raw_latin1': raw.decode('latin1'), 'decimal_big_endian': str(int(current, 16)),
        }
        for encoding, value in examples.items():
            with self.subTest(encoding=encoding):
                result = _preview_token_shape(value, current)
                self.assertEqual(result['length'], len(value))
                self.assertTrue(result[encoding + '_eight_bytes'])
                self.assertTrue(result[encoding + '_equals_current_bytes'])
                stale = _preview_token_shape(value, '0000000000000930')
                self.assertTrue(stale[encoding + '_eight_bytes'])
                self.assertFalse(stale[encoding + '_equals_current_bytes'])
                invalid_current = _preview_token_shape(value, '092f')
                self.assertFalse(invalid_current['current_is_eight_byte_hex'])
                self.assertFalse(invalid_current[encoding + '_equals_current_bytes'])

    def test_failed_token_classification_is_bounded_strict_and_content_free(self):
        current = '000000000000092f'
        malformed = [' 000000000000092f ', '0x092f', '000000000000092g',
                     'AAAAAAAACT9=', 'AAAAAAAACT8=\n', '0000000000000000000002351',
                     '18446744073709551616', '\u0100' * 8, 'DO_NOT_EXPORT_SOURCE']
        for value in malformed:
            with self.subTest(length=len(value)):
                result = _preview_token_shape(value, current)
                self.assertFalse(any(flag for name, flag in result.items()
                                     if name.endswith('_equals_current_bytes')))
                self.assertNotIn(value, json.dumps(result))
        # Noncanonical base64 padding bits cannot be classified as canonical.
        self.assertFalse(_preview_token_shape('AAAAAAAACT9=', current)['base64_eight_bytes'])
        large = _preview_token_shape('SECRET' * 10000, current)
        self.assertEqual(large, {'is_string': True, 'length': 60000,
                                'classification_limit_exceeded': True})
        self.assertEqual(_preview_token_shape(None, current), {'is_string': False})

    def test_capture_failure_still_preserves_original_exception(self):
        from services import member_visitor_ai_repository as repository
        failure = ValueError('original refusal')
        diagnostics = {}
        with patch.object(repository, '_with_private_draft', side_effect=failure), \
                patch('tests.test_mvp1_acceptance_sql_engine._preview_token_shape', side_effect=RuntimeError):
            with observe_preview_failure(diagnostics), self.assertRaises(ValueError) as caught:
                repository._with_private_draft({'entries': []}, {'items': [{'has_draft': True}]})
        self.assertIs(caught.exception, failure)
        self.assertEqual(diagnostics, {'private_preview_fence': {'observation': 'structural_capture_unavailable'}})

    def test_preview_diagnostic_observes_original_failure_without_payloads_or_mutation(self):
        import copy
        from services import member_visitor_ai_repository as repository
        secret = 'DO_NOT_RECORD_SOURCE_OR_OWNER'
        row = dict(entry_key=secret, canonical_type='role', canonical_revision='00000000000000AF',
                   access_revision=9, wording=secret)
        item = dict(record_key=secret, record_type='role', has_draft=True, orphaned=False,
                    draft_is_stale=False, content_token='00000000000000af',
                    draft_base_content_token='00000000000000af', access_revision=8,
                    draft_base_access_revision=8, proposed_values={'summary': secret})
        document = dict(draft_revision=7, subject_key=secret, entries=[row])
        workspace = dict(draft_version=7, items=[copy.deepcopy(item) for _ in range(20)])
        before = copy.deepcopy((document, workspace))
        diagnostics = {}
        failure = ValueError('original refusal')
        with patch.object(repository, '_with_private_draft', side_effect=failure) as original:
            with observe_preview_failure(diagnostics), self.assertRaises(ValueError) as caught:
                repository._with_private_draft(document, workspace)
            self.assertIs(caught.exception, failure)
            original.assert_called_once_with(document, workspace)
        self.assertEqual((document, workspace), before)
        observation = diagnostics['private_preview_fence']
        self.assertTrue(observation['truncated'])
        self.assertEqual(len(observation['items']), 16)
        self.assertEqual(observation['items'][0]['snapshot_access_revision']['value'], 9)
        self.assertEqual(observation['items'][0]['access_revision']['value'], 8)
        self.assertNotIn(secret, json.dumps(diagnostics))
        clean = {}
        result = object()
        with patch.object(repository, '_with_private_draft', return_value=result):
            with observe_preview_failure(clean):
                self.assertIs(repository._with_private_draft(document, workspace), result)
        self.assertEqual(clean, {})

    def test_client_failure_persists_diagnostics_separately_from_sanitized_error(self):
        def fail_with_observation(connect, root, cases, diagnostics):
            diagnostics['private_preview_fence'] = {'observation': 'actual_failing_projection_arguments'}
            raise ValueError('failure ' * 1000)
        source = 'a' * 40
        env = {'PEERSLATE_RESUME_PUBLICATION_SQL_HOST': runner.runtime_tools.PROOF_SQL_CONTAINER,
               'PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA': source}
        with TemporaryDirectory() as directory, patch.dict(os.environ, env), \
                patch.object(runner.platform, 'system', return_value='Linux'), \
                patch('tests.test_mvp1_acceptance_sql_engine.run_engine_contracts', side_effect=fail_with_observation):
            path = Path(directory) / 'evidence.json'
            self.assertEqual(runner.inner(source, path), 1)
            result = json.loads(path.read_text())
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['cases'], {})
        self.assertEqual(result['diagnostics']['private_preview_fence']['observation'],
                         'actual_failing_projection_arguments')

    def test_direct_stale_draft_oracle_supplies_real_digest_without_rechecking_token(self):
        from services.resume_draft_service import ResumeDraftService
        service = ResumeDraftService()
        for token in ('0000000000000123', '00000000000001af'):
            with self.subTest(token=token):
                command = dict(type='save_item', request_id='b1830f56-b6f1-44b6-91e2-ac121d9b524e',
                    record_key='271f4189-8f1b-4817-b1dd-111111111111', record_type='role',
                    expected_draft_version=7, expected_content_token=token, expected_access_revision=1,
                    values={'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Rowversion proof.'})
                port = Mock(return_value='SQL result')
                # No commit/catalog/workspace method is available: the oracle
                # must reach SQL with the deliberately stale token unchanged.
                drafts = SimpleNamespace(_normalize_command=service._normalize_command,
                    repository=SimpleNamespace(commit_command=port))
                self.assertEqual(commit_draft_sql(drafts, 'synthetic-owner', command), 'SQL result')
                owner, request_id, body = port.call_args.args
                payload = json.loads(body)
                self.assertEqual((owner, request_id), ('synthetic-owner', command['request_id']))
                self.assertEqual(payload['request_digest'], service.command_digest(command))
                self.assertRegex(payload['request_digest'], r'^[0-9a-f]{64}$')
                self.assertEqual(payload['expected_content_token'], token)
                self.assertEqual(payload['expected_draft_version'], 7)
                self.assertEqual(payload['expected_access_revision'], 1)
                self.assertNotIn('request_digest', command)


    def test_registry_closure_is_complete_ordered_and_G_is_last(self):
        rows = runner.migration_closure(runner.ROOT)
        registry = json.loads((runner.ROOT/'SQL FIles/Migrations/registry.json').read_text())
        by_id = {row['id']: row for row in registry['migrations']}
        seen = set()
        for row in rows:
            self.assertTrue(set(by_id[row['id']]['requires']) <= seen)
            self.assertNotIn(row['id'], seen)
            seen.add(row['id'])
        self.assertEqual(rows[-1]['id'], 'PS-RESUME-IDENTITY-001')
        self.assertTrue({'PS-PROFILE-002','PS-WORKSHOP-004','PS-VISITOR-AI-001',
                         'PS-COMMUNITY-PUBLIC-PILOT-001'} <= seen)
        ids = [row['id'] for row in rows]
        self.assertLess(ids.index('PS-COMMUNITY-PUBLIC-PILOT-001'), ids.index('PS-PROFILE-002'))

    def test_consumed_F_environment_cannot_authorize_G(self):
        env = {'PEERSLATE_MEMBER_VISITOR_AI_EXECUTE': 'authorized',
               'PEERSLATE_MEMBER_VISITOR_AI_EXPECTED_SHA': 'a'*40,
               'PEERSLATE_MEMBER_VISITOR_AI_AUTHORIZATION_REF': 'consumed-F'}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(runner.authorized('a'*40, 'consumed-F'))

    def test_default_plan_never_acquires_resources(self):
        with patch.object(runner.runtime_tools,'acquire_isolated_sql_runtime') as acquire:
            proposal=runner.plan()
        acquire.assert_not_called()
        self.assertEqual(proposal['status'],'proposal_not_executed')
        self.assertEqual(set(proposal['engine_cases']),set(ENGINE_CASES))
        self.assertIn('services/member_visitor_ai_service.py',proposal['source_manifest'])

    def test_E_environment_or_mismatched_G_authority_cannot_execute(self):
        environments=[{}, {'PEERSLATE_RESUME_PUBLICATION_SQL_PROOF_EXECUTE':'authorized'},
            {'PEERSLATE_MVP1_ACCEPTANCE_EXECUTE':'authorized','PEERSLATE_MVP1_ACCEPTANCE_EXPECTED_SHA':'b'*40,
             'PEERSLATE_MVP1_ACCEPTANCE_AUTHORIZATION_REF':'fresh-G'}]
        with TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.json'
            for env in environments:
                with self.subTest(env=env),patch.dict(os.environ,env,clear=True),patch.object(runner,'AcceptanceRuntime') as runtime:
                    self.assertEqual(runner.execute('a'*40,'fresh-G',path),3)
                    self.assertEqual(json.loads(path.read_text())['status'],'refused')
                    runtime.assert_not_called()

    def test_partial_acquisition_failure_retains_cleanup_custody(self):
        env={'PEERSLATE_MVP1_ACCEPTANCE_EXECUTE':'authorized','PEERSLATE_MVP1_ACCEPTANCE_EXPECTED_SHA':'a'*40,
             'PEERSLATE_MVP1_ACCEPTANCE_AUTHORIZATION_REF':'synthetic-new-G'}
        owned_record={'name':'synthetic','id':'exact-id','marker':'synthetic-marker','kind':'network'}
        def fail(runtime,**kwargs):
            kwargs['owned'].append(owned_record)
            raise RuntimeError('injected acquisition failure')
        with TemporaryDirectory() as directory,patch.dict(os.environ,env,clear=True), \
            patch.object(runner.platform,'system',return_value='Linux'),patch.object(runner.platform,'machine',return_value='x86_64'), \
            patch.object(runner.runtime_tools,'assert_reviewed_source'),patch.object(runner,'AcceptanceRuntime') as runtime, \
            patch.object(runner.runtime_tools,'acquire_isolated_sql_runtime',side_effect=fail), \
            patch.object(runner.runtime_tools,'cleanup_owned_resources',return_value={'status':'pass'}) as cleanup:
            runtime.return_value._sql_password='synthetic-secret'
            path=Path(directory)/'evidence.json'
            self.assertEqual(runner.execute('a'*40,'synthetic-new-G',path),1)
            cleanup.assert_called_once_with(runtime.return_value,[owned_record])
            result=json.loads(path.read_text())
            self.assertEqual(result['cleanup_status'],'pass'); self.assertEqual(result['proof_status'],'fail')
            self.assertNotIn('synthetic-secret',path.read_text())

    def test_only_exact_inherited_oracle_command_selects_G(self):
        with patch.object(runner.runtime_tools.IsolatedDockerCliRuntime,'_docker',return_value='ok') as docker:
            runtime=runner.AcceptanceRuntime()
            runtime._docker(['exec','container','python','-B','scripts/run_resume_publication_sql_proof.py','--in-client-oracles'])
            self.assertIn('scripts/run_mvp1_acceptance_sql_proof.py',docker.call_args.args[0])
            with self.assertRaises(runner.runtime_tools.EngineProofError):
                runtime._docker(['exec','container','scripts/run_resume_publication_sql_proof.py','--execute'])

    def test_inherited_source_verifier_hashes_E_and_G_paths_without_rewriting(self):
        expected={'scripts/run_resume_publication_sql_proof.py':'a'*64,
                  'scripts/run_mvp1_acceptance_sql_proof.py':'b'*64}
        seen=[]
        def process(args,**kwargs):
            # Intercept only the external process; exercise both real adapter layers.
            self.assertEqual(args[0],'docker')
            command=args[1:]
            self.assertEqual(command[:4],['exec',runner.runtime_tools.PROOF_CLIENT_CONTAINER,'python','-c'])
            seen.append(command[-1])
            return subprocess.CompletedProcess(args,0,expected[command[-1]],'')
        runtime=runner.AcceptanceRuntime(runner=process)
        self.assertEqual(runtime.verify_copied_client_source(runner.runtime_tools.PROOF_CLIENT_CONTAINER,expected),expected)
        self.assertEqual(seen,list(expected))

    def test_inherited_oracle_invocation_selects_G_and_preserves_source_and_evidence(self):
        seen=[]
        payload={'proof_id':runner.PROOF_ID,'source_sha':'a'*40,'status':'pass','cases':{}}
        def process(args,**kwargs):
            command=args[1:]
            seen.append(command)
            if command[0]=='cp':
                Path(command[-1]).write_text(json.dumps(payload),encoding='utf-8')
            return subprocess.CompletedProcess(args,0,'','')
        with TemporaryDirectory() as directory,patch.object(runner.runtime_tools.tempfile,'mkdtemp',return_value=directory):
            runtime=runner.AcceptanceRuntime(runner=process)
            self.assertEqual(runtime.run_client_oracles(source_sha='a'*40),payload)
        command=seen[0]
        index=command.index('python')
        self.assertEqual(command[index:],['python','-B','scripts/run_mvp1_acceptance_sql_proof.py',
            '--in-client-oracles','--source-sha','a'*40,'--evidence',runner.runtime_tools.PROOF_CLIENT_REMOTE_EVIDENCE])
        self.assertNotIn('scripts/run_resume_publication_sql_proof.py',command)
