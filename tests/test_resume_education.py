"""Education command/API tests with a mock procedure boundary, never a live DB."""
from unittest.mock import MagicMock, patch
from uuid import UUID
import unittest
from services.database_service import DatabaseServiceError
from services.living_resume_editor_service import EDUCATION_STATUSES, LivingResumeEditorService, LivingResumeEditorConflictError, LivingResumeEditorUnavailableError, LivingResumeEditorValidationError, normalize_command
COMMAND = str(UUID(int=1, version=4))
RECORD = str(UUID(int=2, version=4))
PROFILE = str(UUID(int=3, version=4))
VERSION = '000000000000002a'

def payload(operation='create', **values):
    return {'command_id': COMMAND, 'record_key': RECORD, 'type': operation + '_education', 'expected_version': None if operation == 'create' else VERSION, 'values': {} if operation == 'remove' else {'title': 'Undergraduate study', 'institution_name': 'Example University', 'degree_name': None, 'field_of_study': 'History', 'education_status': 'in_progress', 'grade_text': None, 'location_text': None, 'summary': 'My own wording', 'start_date': '2024-08-01', 'end_date': None, 'date_precision': 'month', **values}}

def editor_rows(count=1):
    values = normalize_command(payload())[0]['values']
    return [[{'profile_key': PROFILE, 'profile_slug': 'example', 'display_name': 'Example'}], [], [], [], [], [{**values, 'record_key': str(UUID(int=i + 2, version=4)), 'row_version': bytes.fromhex(VERSION), 'editable': 1, 'blocked_reason': None} for i in range(count)]]

def receipt(command, *, replayed=0, changed=False):
    normalized, _, digest = normalize_command(command)
    operation = command['type'].split('_')[0]
    return [[{'committed': 0 if changed else 1, 'error_code': 'changed' if changed else None, 'command_id': COMMAND, 'request_digest': digest, 'command_type': normalized['type'], 'record_key': RECORD, 'outcome': {'create': 'created', 'update': 'updated', 'remove': 'removed'}[operation], 'record_version': None if operation == 'remove' else bytes.fromhex(VERSION), 'replayed': replayed}]]

class ResumeEducationTests(unittest.TestCase):

    def test_owner_read_has_arbitrary_education_list_and_schema_capabilities(self):
        for count in [0, 1, 4]:
            with self.subTest(count=count):
                db = MagicMock()
                db.execute_procedure.return_value = editor_rows(count)
                result = LivingResumeEditorService(db).get_editor('owner-a')
                assert len(result['education']) == count
                assert result['credentials'] == []
                assert set(result['capabilities']['education_statuses']) == EDUCATION_STATUSES
                assert 'approximate' in result['capabilities']['education_date_precisions']
                assert 'approximate' not in result['capabilities']['date_precisions']
                assert {'create_education', 'update_education', 'remove_education'} <= set(result['capabilities']['commands'])
                db.execute_procedure.assert_called_once_with('usp_GetOwnerLivingResumeEditor', (('@UserKey', 'owner-a'),))

    def test_all_canonical_education_statuses_preserve_no_degree_and_end_only_date(self):
        for status in sorted(EDUCATION_STATUSES):
            with self.subTest(status=status):
                normalized, _, _ = normalize_command(payload(education_status=status, start_date=None, end_date='2001-06-15', date_precision='approximate'))
                assert normalized['values']['degree_name'] is None
                assert normalized['values']['education_status'] == status
                assert normalized['values']['end_date'] == '2001-06-15'

    def test_date_normalization_and_original_wording(self):
        for precision, expected in [('day', '2024-08-19'), ('month', '2024-08-01'), ('year', '2024-01-01'), ('unknown', '2024-08-19'), ('approximate', '2024-08-19')]:
            with self.subTest(precision=precision, expected=expected):
                text = 'Member wording: 😀 ' + 'x' * 4500
                normalized, _, _ = normalize_command(payload(start_date='2024-08-19', date_precision=precision, summary=text))
                assert normalized['values']['start_date'] == expected
                assert normalized['values']['summary'] == text

    def test_invalid_or_unowned_fields_fail_before_database_call(self):
        for values in [{'education_status': None}, {'education_status': 'graduated'}, {'title': ''}, {'institution_name': ''}, {'grade_text': 'x' * 101}, {'degree_name': '😀' * 151}, {'summary': '😀' * 4001}, {'summary': '\ud800'}, {'end_date': '2020-01-01'}, {'start_date': '2024-2-01'}, {'date_precision': 'semester'}, {'field_of_study': []}, {'visibility': 'public'}, {'approval_status': 'approved'}, {'owner_profile_id': 4}, {'credential_name': 'Wrong subtype'}]:
            with self.subTest(values=values):
                db = MagicMock()
                with self.assertRaises(LivingResumeEditorValidationError):
                    LivingResumeEditorService(db).commit('owner-a', payload(**values))
                db.execute_procedure.assert_not_called()

    def test_education_commands_bind_owner_and_return_digest_receipt_and_current_record(self):
        for operation in ['create', 'update', 'remove']:
            with self.subTest(operation=operation):
                command = payload(operation)
                db = MagicMock()
                db.execute_procedure.side_effect = [receipt(command), editor_rows(0 if operation == 'remove' else 1)]
                result = LivingResumeEditorService(db).commit('owner-a', command)
                normalized, serialized, digest = normalize_command(command)
                assert result['receipt']['request_digest'] == digest
                assert result['receipt']['type'] == normalized['type']
                assert result['current'] is None if operation == 'remove' else result['current']['record_key'] == RECORD
                db.execute_procedure.assert_any_call('usp_CommitLivingResumeCommandForOwner', (('@UserKey', 'owner-a'), ('@CommandId', COMMAND), ('@CommandJson', serialized)))
                assert all((call.args[1][0] == ('@UserKey', 'owner-a') for call in db.execute_procedure.call_args_list))

    def test_no_parent_forgery_missing_version_or_remove_values(self):
        for operation in ['update', 'remove']:
            with self.subTest(operation=operation):
                for overrides in ({'parent_key': PROFILE}, {'expected_version': None}, {'expected_version': True}):
                    with self.assertRaises(LivingResumeEditorValidationError):
                        normalize_command({**payload(operation), **overrides})
                with self.assertRaises(LivingResumeEditorValidationError):
                    normalize_command({**payload('remove'), 'values': {'title': 'Do not edit'}})

    def test_replay_after_removal_and_changed_conflict_use_owner_editor(self):
        db = MagicMock()
        db.execute_procedure.side_effect = [receipt(payload(), replayed=1), editor_rows(0)]
        result = LivingResumeEditorService(db).commit('owner-b', payload())
        assert result['receipt']['replayed'] and result['current'] is None
        db.execute_procedure.side_effect = [receipt(payload('update'), changed=True), editor_rows()]
        with self.assertRaises(LivingResumeEditorConflictError) as error:
            LivingResumeEditorService(db).commit('owner-b', payload('update'))
        assert error.exception.code == 'changed'
        assert error.exception.current['record_key'] == RECORD
        assert all((call.args[1][0] == ('@UserKey', 'owner-b') for call in db.execute_procedure.call_args_list))

    def test_database_guards_map_to_safe_education_errors_without_read(self):
        for marker, code in [('RESUME_EDITOR_NOT_FOUND', 'not_found'), ('RESUME_EDITOR_PROTECTED', 'protected'), ('RESUME_EDITOR_IDEMPOTENCY_CONFLICT', 'idempotency_conflict')]:
            with self.subTest(marker=marker, code=code):
                db = MagicMock()
                failure = DatabaseServiceError('private details')
                failure.__cause__ = RuntimeError(marker)
                db.execute_procedure.side_effect = failure
                with self.assertRaises(Exception) as error:
                    LivingResumeEditorService(db).commit('owner-a', payload('update'))
                assert error.exception.code == code
                assert 'private details' not in str(error.exception)
                assert db.execute_procedure.call_count == 1

    def test_education_database_shapes_and_versions_fail_closed(self):
        for changes in ({'row_version': None}, {'editable': 0}, {'education_status': 'unknown'}, {'education_status': []}, {'date_precision': 'semester'}, {'date_precision': []}, {'record_key': 'forged'}):
            rows = editor_rows()
            rows[5][0].update(changes)
            db = MagicMock()
            db.execute_procedure.return_value = rows
            with self.assertRaises(LivingResumeEditorUnavailableError):
                LivingResumeEditorService(db).get_editor('owner-a')

    def test_education_api_uses_real_normalization_and_server_identity(self):
        from app import app
        import peerslate_api
        db = MagicMock()
        service = LivingResumeEditorService(db)
        config = dict(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY='owner-api', PEERSLATE_LIVING_RESUME_DB_ENABLED=True, PEERSLATE_TRUST_EASYAUTH_HEADERS=False)
        with patch.dict(app.config, config), patch.object(peerslate_api, 'living_resume_editor_service', service):
            client = app.test_client()
            command = payload()
            db.execute_procedure.side_effect = [receipt(command), editor_rows()]
            response = client.post('/api/living-resume/me/commands?user_key=foreign', headers={'X-PeerSlate-Request': 'same-origin'}, json=command)
            assert response.status_code == 201
            assert response.headers['Cache-Control'] == 'private, no-store'
            assert all((call.args[1][0] == ('@UserKey', 'owner-api') for call in db.execute_procedure.call_args_list))
            db.reset_mock()
            for body, headers, status in [({**command, 'owner_profile_id': 42}, {'X-PeerSlate-Request': 'same-origin'}, 400), (command, {}, 403), (command, {'X-PeerSlate-Request': 'same-origin', 'Origin': 'https://foreign.example'}, 403)]:
                response = client.post('/api/living-resume/me/commands', headers=headers, json=body)
                assert response.status_code == status
                db.execute_procedure.assert_not_called()
            with patch.dict(app.config, {'PEERSLATE_ALLOW_DEV_IDENTITY': False, 'PEERSLATE_DEV_USER_KEY': None}):
                response = client.post('/api/living-resume/me/commands', headers={'X-PeerSlate-Request': 'same-origin'}, json=command)
                assert response.status_code == 401
                db.execute_procedure.assert_not_called()
