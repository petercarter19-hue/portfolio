"""Adapter agreement and service recovery; these fixtures are not engine proof."""
import copy
import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.database_service import DatabaseServiceError
from services.resume_intake_repository import SqlResumeIntakeRepository, ResumeIntakeStoreUnavailable, map_declared_workspace
from services.resume_intake_service import ResumeIntakeConflictError, ResumeIntakeUnavailableError
from tests.test_my_data_drafts import build_service, draft_body
from tests.test_resume_intake_sql import DeclaredIntakeSimulator


class DraftDatabase(DeclaredIntakeSimulator):
    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()
        self.before_commit = None
        self.lose_reply = False
        self.commits = 0

    def first_result(self, *args, **kwargs):
        with self.lock:
            return super().first_result(*args, **kwargs)

    def execute_procedure(self, name, parameters=None):
        if name != 'usp_ReplaceResumeIntakeDraftsForOwner':
            return super().execute_procedure(name, parameters)
        bound = dict(parameters)
        command = json.loads(bound['@CommandJson'])
        callback, self.before_commit = self.before_commit, None
        if callback:
            callback()
        with self.lock:
            state = self.state(bound['@UserKey'])
            if (command['expected_revision'] != state['draft_revision']
                    or command['expected_lifecycle_epoch'] != state['lifecycle_epoch']):
                outcome = 'conflict'
            else:
                state['drafts'] = copy.deepcopy(command['drafts'])
                state['draft_revision'] += 1
                self.commits += 1
                outcome = 'applied'
            if self.lose_reply:
                self.lose_reply = False
                raise DatabaseServiceError('response lost after commit')
            return [[{'outcome': outcome, 'request_id': bound['@RequestId'],
                      'revision': state['draft_revision']}]]


class DurableDraftTests(unittest.TestCase):
    def setUp(self):
        self.db = DraftDatabase()
        self.a = build_service(repository=SqlResumeIntakeRepository(self.db))
        self.b = build_service(repository=SqlResumeIntakeRepository(self.db))

    def test_sql_workspace_uuid_keys_foreign_keys_and_receipt_preserve_identity(self):
        ids = {name: str(uuid4()) for name in ('submission', 'source', 'job', 'proposal', 'request', 'target')}
        upper = {name: value.upper() for name, value in ids.items()}
        declared = {'lifecycle_epoch': 0, 'policy_version': 1,
            'submissions': [{'submission_key': upper['submission'], 'request_id': upper['request'],
                             'source_keys': [upper['source']], 'proposal_keys': [upper['proposal']]}],
            'sources': [{'source_key': upper['source'], 'submission_key': upper['submission']}],
            'jobs': [{'job_key': upper['job'], 'source_key': upper['source'], 'submission_key': upper['submission']}],
            'proposals': [{'proposal_key': upper['proposal'], 'source_key': upper['source'],
                           'submission_key': upper['submission'], 'target_key': upper['target']}],
            'receipts': [{'request_id': upper['request'], 'submission_key': upper['submission'],
                          'result_json': json.dumps({'request_id': ids['request'], 'request_digest': 'a' * 64,
                                                    'submission': {'submission_key': upper['submission']}})}]}
        result = map_declared_workspace(declared)
        self.assertEqual(result['submissions'][ids['submission']]['source_keys'], [ids['source']])
        self.assertEqual(result['submissions'][ids['submission']]['proposal_keys'], [ids['proposal']])
        self.assertEqual(result['submissions'][ids['submission']]['request_id'], ids['request'])
        self.assertEqual(result['sources'][ids['source']]['submission_key'], ids['submission'])
        self.assertEqual(result['jobs'][ids['job']]['fence']['source_key'], ids['source'])
        self.assertEqual(result['jobs'][ids['job']]['fence']['submission_key'], ids['submission'])
        self.assertEqual(result['proposals'][ids['proposal']]['binding']['source_key'], ids['source'])
        self.assertEqual(result['proposals'][ids['proposal']]['binding']['submission_key'], ids['submission'])
        self.assertEqual(result['proposals'][ids['proposal']]['target_key'], ids['target'])
        receipt = result['receipts'][ids['request']]
        self.assertEqual(receipt['result']['request_id'], ids['request'])
        self.assertEqual(receipt['result']['submission']['submission_key'], ids['submission'])
        self.assertEqual(receipt['submission_key'], ids['submission'])

    def test_sql_workspace_refuses_malformed_identity_and_foreign_receipt_identity(self):
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            map_declared_workspace({'lifecycle_epoch': 0, 'policy_version': 1,
                                    'sources': [{'source_key': 'not-a-uuid'}]})
        request = str(uuid4())
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            map_declared_workspace({'lifecycle_epoch': 0, 'policy_version': 1,
                'receipts': [{'request_id': request.upper(),
                              'result_json': json.dumps({'request_id': str(uuid4())})}]})

    def test_draft_cas_accepts_same_uuid_with_sql_text_casing(self):
        original = self.db.execute_procedure
        def sql_uuid_text(name, parameters=None):
            result = original(name, parameters)
            if name == 'usp_ReplaceResumeIntakeDraftsForOwner':
                result[-1][0]['request_id'] = result[-1][0]['request_id'].upper()
            return result
        self.db.execute_procedure = sql_uuid_text
        self.a.save_draft('a', draft_body(text='recoverable SQL draft'))
        self.assertEqual(self.b.get_draft('a')['draft']['text'], 'recoverable SQL draft')
        self.assertEqual(self.db.commits, 1)

    def test_draft_cas_refuses_foreign_or_malformed_response_uuid_without_retry(self):
        for returned_id in (str(uuid4()), None):
            with self.subTest(returned_id=returned_id):
                db = DraftDatabase()
                original = db.execute_procedure
                def wrong_uuid(name, parameters=None):
                    result = original(name, parameters)
                    if name == 'usp_ReplaceResumeIntakeDraftsForOwner':
                        result[-1][0]['request_id'] = returned_id
                    return result
                db.execute_procedure = wrong_uuid
                service = build_service(repository=SqlResumeIntakeRepository(db))
                with self.assertRaises(ResumeIntakeUnavailableError):
                    service.save_draft('a', draft_body(text='recoverable SQL draft'))
                self.assertEqual(db.commits, 1)

    def test_reload_owner_isolation_and_no_other_state_changes(self):
        before = copy.deepcopy(self.db.state('a'))
        self.a.save_draft('a', draft_body(text='private unfinished words'))
        self.assertEqual(self.b.get_draft('a')['draft']['text'], 'private unfinished words')
        self.assertIsNone(self.b.get_draft('b')['draft'])
        after = self.db.state('a')
        for key in before:
            if key not in {'drafts', 'draft_revision'}:
                self.assertEqual(after[key], before[key])

    def test_structured_only_draft_can_reload_without_text(self):
        self.a.save_draft('a', draft_body(items=[{
            'record_type': 'skill', 'values': {'name': 'Mentoring'}}]))
        row = self.b.get_draft('a')['draft']
        self.assertIsNone(row['text'])
        self.assertEqual(row['items'][0]['values']['name'], 'Mentoring')

    def test_explicit_cas_conflict_reloads_and_preserves_loser_input(self):
        self.a.save_draft('a', draft_body(text='first'))
        self.db.before_commit = lambda: self.b.save_draft('a', draft_body(text='winner', expected_version=1))
        with self.assertRaises(ResumeIntakeConflictError) as raised:
            self.a.save_draft('a', draft_body(text='unsaved loser', expected_version=1))
        self.assertEqual(raised.exception.proposed['text'], 'unsaved loser')
        self.assertEqual(self.a.get_draft('a')['draft']['text'], 'winner')
        self.assertEqual(self.db.commits, 2)

    def test_lost_reply_is_not_blindly_retried_same_request_recovers(self):
        command = draft_body(text='recoverable words')
        self.db.lose_reply = True
        with self.assertRaises(ResumeIntakeUnavailableError):
            self.a.save_draft('a', command)
        self.assertEqual(self.db.commits, 1)
        self.assertTrue(self.b.save_draft('a', command)['replayed'])
        self.assertEqual(self.db.commits, 1)

    def test_discard_recreate_fences_old_device_version(self):
        first = self.a.save_draft('a', draft_body(text='old'))['draft']
        self.b.discard_draft('a', {})
        new = self.b.save_draft('a', draft_body(text='new'))['draft']
        self.assertGreater(new['version'], first['version'])
        with self.assertRaises(ResumeIntakeConflictError):
            self.a.save_draft('a', draft_body(text='old device', expected_version=first['version']))

    def test_read_after_purge_refreshes_attachment_without_extending_expiry(self):
        source = str(uuid4())
        # The adapter only consumes declared source rows; no database is opened.
        self.db.state('a')['sources'].append({'source_key': source, 'kind': 'recording',
            'state': 'active', 'source_version': 1, 'source_text': 'transcript'})
        row = self.a.save_draft('a', draft_body(text='kept words', attachments=[
            {'client_key': 'recording-a', 'kind': 'recording', 'source_key': source}]))['draft']
        state = self.db.state('a')
        state['sources'][0].update(state='purged', source_text=None)
        state['lifecycle_epoch'] += 1
        recovered = self.b.get_draft('a')['draft']
        self.assertTrue(recovered['attachments'][0]['needs_reattach'])
        self.assertEqual(recovered['updated_at'], row['updated_at'])
        self.assertEqual(recovered['expires_at'], row['expires_at'])
        self.assertEqual(recovered['text'], 'kept words')

    def test_draft_scope_rejects_mutating_other_owner_state(self):
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            self.a.repository.with_drafts('a', lambda state: state.update(policy_version=99))
        self.assertEqual(self.db.commits, 0)

    def test_malformed_durable_reader_never_returns_empty_owner(self):
        del self.db.state('a')['draft_revision']
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            self.a.repository.load_owner('a')


class AtomicSourceContractTests(unittest.TestCase):
    def test_unparented_impact_stages_complete_normalized_proposal_values(self):
        from pathlib import Path
        from services.living_resume_editor_service import normalize_editor_values
        database = DraftDatabase()
        service = build_service(repository=SqlResumeIntakeRepository(database))
        source, override = str(uuid4()), str(uuid4())
        raw = {'wording': 'Synthetic impact without a selected parent'}
        expected = normalize_editor_values('accomplishment', raw)
        self.assertIsNone(expected['metric_value'])
        self.assertIsNone(expected['metric_label'])
        database.state('a')['sources'].append({'source_key': source, 'kind': 'recording',
            'state': 'active', 'source_version': 1, 'source_text': 'synthetic transcript',
            'structured_values_json': json.dumps({'_extracted_candidates': [{
                'override_key': override, 'source_key': source, 'source_version': 1,
                'record_type': 'accomplishment', 'state': 'pending', 'values': raw,
                'canonical_values': expected}]})})
        captured = {}
        class Staged(Exception):
            pass
        def capture(owner, procedure, request_id, payload):
            captured.update(payload)
            raise Staged()
        service.repository.commit_command = capture
        with self.assertRaises(Staged):
            service.keep_extracted_separate('a', {'request_id': str(uuid4()), 'override_key': override})
        submission = captured['submission']
        self.assertEqual(submission['canonical_intents'], [])
        self.assertEqual(submission['sources'][0]['structured_values'], expected)
        proposal = submission['proposals'][0]
        self.assertEqual(proposal['proposed_values'], expected)
        self.assertEqual(proposal['kind'], 'ambiguous_match')
        self.assertIsNone(proposal['target_key'])
        # Agreement with the declared SQL boundary; actual execution is a
        # separately authorized engine oracle, never claimed by this check.
        migration = (Path(__file__).resolve().parents[1] / 'SQL FIles/Migrations/'
                     'PS-RESUME-INTAKE-002_durable_composer.sql').read_text()
        impact = migration.split("ELSE IF (SELECT COUNT(*) FROM OPENJSON(@Intents))=0", 1)[1]
        impact = impact.split('SET @Actual=NULL;', 1)[0]
        self.assertIn('FROM OPENJSON(@Expected) e FULL JOIN OPENJSON(@Actual) a', impact)
        self.assertNotIn('@ExpectedFields', impact)

    def test_service_stages_exact_normalized_server_values_and_binding(self):
        from services.living_resume_editor_service import normalize_editor_values
        database = DraftDatabase()
        service = build_service(repository=SqlResumeIntakeRepository(database))
        source, override = str(uuid4()), str(uuid4())
        raw = {'role_title': '  Synthetic Engineer  ', 'employer_name': 'Synthetic Employer'}
        expected = normalize_editor_values('role', raw)
        database.state('a')['sources'].append({'source_key': source.upper(), 'kind': 'recording',
            'state': 'active', 'source_version': 1, 'source_text': 'synthetic transcript',
            'structured_values_json': json.dumps({'_extracted_candidates': [{
                'override_key': override, 'source_key': source, 'source_version': 1,
                'record_type': 'role', 'state': 'pending', 'values': raw,
                'canonical_values': expected}]})})
        captured = {}
        class Staged(Exception):
            pass
        def capture(owner, procedure, request_id, payload):
            captured.update(procedure=procedure, payload=copy.deepcopy(payload))
            raise Staged()
        service.repository.commit_command = capture
        with self.assertRaises(Staged):
            service.keep_extracted_separate('a', {'request_id': str(uuid4()), 'override_key': override})
        self.assertEqual(captured['procedure'], 'usp_CommitResumeIntakeExtractedSourceForOwner')
        body = captured['payload']
        self.assertEqual(body['source_binding'], {'source_key': source, 'source_version': 1,
            'override_key': override, 'record_type': 'role'})
        self.assertEqual(body['submission']['sources'][0]['structured_values'], expected)
        self.assertEqual(body['submission']['canonical_intents'][0]['command']['values'], expected)
        self.assertNotIn('Synthetic Engineer', json.dumps(body['submission']['receipt']))

    def test_changed_normalized_copy_fails_before_any_command(self):
        service = build_service()
        with self.assertRaises(ResumeIntakeUnavailableError):
            service._server_held_extracted_values({'record_type': 'role', 'state': 'pending',
                'values': {'role_title': 'Engineer', 'employer_name': 'Employer'},
                'canonical_values': {'role_title': 'Different'}})

    def test_other_winner_replay_requires_same_override_binding(self):
        winner, request, override = str(uuid4()), str(uuid4()), str(uuid4())
        digest = 'a' * 64
        result = {'request_id': winner, 'request_digest': digest,
                  'submission': {'submission_key': override.upper()}}
        class ReplayDatabase:
            def execute_procedure(self, *args):
                return [[{'committed': True, 'replayed': True, 'request_digest': digest,
                          'receipt_request_id': winner.upper(), 'result_json': json.dumps(result)}]]
        repository = SqlResumeIntakeRepository(ReplayDatabase())
        body = {'source_binding': {'override_key': override}}
        for replay_request in (winner, request):
            response = repository.commit_command('a', 'usp_CommitResumeIntakeExtractedSourceForOwner', replay_request, body)
            self.assertEqual(response['receipt_request_id'], winner)
            self.assertEqual(response['result']['submission']['submission_key'], override)
        body['source_binding']['override_key'] = str(uuid4())
        with self.assertRaises(ResumeIntakeStoreUnavailable):
            repository.commit_command('a', 'usp_CommitResumeIntakeExtractedSourceForOwner', request, body)

    def test_source_replay_refuses_malformed_or_foreign_winner_without_retry(self):
        winner, request, override = str(uuid4()), str(uuid4()), str(uuid4())
        for returned_id in (str(uuid4()), 'invalid-uuid', None):
            with self.subTest(returned_id=returned_id):
                class ReplayDatabase:
                    calls = 0
                    def execute_procedure(self, *args):
                        self.calls += 1
                        return [[{'committed': True, 'replayed': True, 'request_digest': 'a' * 64,
                                  'receipt_request_id': returned_id, 'result_json': json.dumps({
                                      'request_id': winner, 'request_digest': 'a' * 64,
                                      'submission': {'submission_key': override}})}]]
                db = ReplayDatabase()
                with self.assertRaises(ResumeIntakeStoreUnavailable):
                    SqlResumeIntakeRepository(db).commit_command('a',
                        'usp_CommitResumeIntakeExtractedSourceForOwner', request,
                        {'source_binding': {'override_key': override}})
                self.assertEqual(db.calls, 1)


if __name__ == '__main__':
    unittest.main()
