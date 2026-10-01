"""Actual SQL oracles, invoked only in the admitted invocation-owned client.

Import/discovery does not connect. Results contain case names and structural
counts; synthetic member words and connection strings never leave the client.
"""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from services import resume_publication_adapters as proof

ENGINE_CASES = (
    'actual_generic_migration_gates', 'populated_additive_rollback_preserves_canonical',
    'durable_reload_owner_isolation', 'draft_cas_two_connections',
    'draft_lost_reply_replay_discard_recreate', 'atomic_source_consumption_and_replay',
    'source_replay_after_purge_no_resurrection',
    'impact_without_parent_remains_proposal',
    'foreign_stale_and_changed_values_refused', 'source_keep_two_connections',
    'purge_versus_keep_two_connections', 'purge_versus_save_two_connections',
    'injected_failure_rolls_back_canonical_source_receipt', 'guarded_history_rollback',
)


class EngineDatabase:
    def __init__(self, connection):
        self.connection = connection

    def execute_procedure(self, name, parameters=()):
        from services.database_service import DatabaseServiceError
        if not name.replace('_', '').isalnum():
            raise ValueError('invalid procedure')
        query = 'EXEC dbo.' + name
        if parameters:
            query += ' ' + ', '.join(key + '=?' for key, _ in parameters)
        values = tuple(json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                       if isinstance(value, dict) else value for _, value in parameters)
        try:
            return sql(self.connection, query, values)
        except Exception as error:
            raise DatabaseServiceError('Isolated intake procedure failed.') from error

    def first_result(self, *args, **kwargs):
        rows = self.execute_procedure(*args, **kwargs)
        return rows[0] if rows else []

    def first_row(self, *args, **kwargs):
        rows = self.first_result(*args, **kwargs)
        return rows[0] if rows else None


def sql(connection, query, parameters=()):
    cursor = connection.cursor()
    try:
        cursor.execute(query, parameters)
        return proof._fetch_procedure_result_sets(cursor)
    finally:
        cursor.close()


class OracleCheckFailure(AssertionError):
    def __init__(self, label):
        # Only named checks in the currently failing reload phase are exported.
        self.check_label = label if label in {'reload failed', 'foreign draft disclosed'} else 'unclassified_check'
        super().__init__('isolated intake oracle check failed')


def check(condition, message):
    if not condition:
        raise OracleCheckFailure(message)


def has_marker(error, marker):
    """Classify the actual SQL refusal without exporting exception content."""
    current, seen = error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if marker in str(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def bounded_sql_failure(error):
    """Export fixed SQL markers/numbers, never exception text or parameters."""
    markers = (
        'RESUME_INTAKE_NOT_FOUND', 'RESUME_INTAKE_CHANGED', 'RESUME_INTAKE_VALIDATION',
        'RESUME_INTAKE_IDEMPOTENCY_CONFLICT', 'RESUME_EDITOR_NOT_FOUND',
        'RESUME_EDITOR_VALIDATION', 'RESUME_EDITOR_IDEMPOTENCY_CONFLICT',
        'RESUME_EDITOR_PROTECTED', 'RESUME_INTAKE_DURABLE_ROLLBACK_HAS_DRAFTS',
        'RESUME_INTAKE_DURABLE_ROLLBACK_HAS_HISTORY', 'INTAKE_PROOF_INJECTED_FAILURE',
    )
    allowed_classes = {'OracleCheckFailure', 'AssertionError', 'RuntimeError', 'ValueError',
        'TypeError', 'KeyError', 'ResumeIntakeUnavailableError', 'ResumeIntakeStoreUnavailable',
        'ResumeIntakeConflictError', 'DatabaseServiceError', 'ProgrammingError', 'OperationalError',
        'IntegrityError', 'InterfaceError', 'DatabaseError', 'Error'}
    numbers, classes, labels, current, seen = set(), set(), set(), error, set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ in allowed_classes:
            classes.add(type(current).__name__)
        if isinstance(current, OracleCheckFailure):
            labels.add(current.check_label)
        detail = str(current)[:5120]
        # The driver reports its native error immediately before SQLExecDirect
        # (or another SQL operation); numbers embedded in content do not match.
        numbers.update(int(value) for value in re.findall(
            r'\((\d{1,5})\)(?=\s*\(SQL[A-Za-z]+\))', detail))
        current = current.__cause__ or current.__context__
    return {'markers': [marker for marker in markers if has_marker(error, marker)],
            'native_error_numbers': sorted(numbers)[:8],
            'failure_classes': sorted(classes)[:8], 'check_labels': sorted(labels)[:4]}


def expect_marker(callback, marker):
    try:
        callback()
    except Exception as error:
        check(has_marker(error, marker), 'expected actual SQL marker: ' + marker)
    else:
        raise AssertionError('expected SQL refusal: ' + marker)


def scalar(connection, query, parameters=()):
    return next(iter(sql(connection, query, parameters)[0][0].values()))


def stack(connection):
    from services.entry_policy_repository import SqlEntryPolicyRepository
    from services.living_resume_editor_service import LivingResumeEditorService
    from services.knowledge_service import KnowledgeService
    from services.resume_draft_repository import LivingResumeCanonicalCatalog, SqlResumeDraftRepository
    from services.resume_draft_service import ResumeDraftService
    from services.resume_intake_repository import SqlResumeIntakeRepository
    from services.resume_intake_service import ResumeIntakeService
    from services.resume_intake_policy import selected_policy_for_tests
    db = EngineDatabase(connection)
    catalog = LivingResumeCanonicalCatalog(LivingResumeEditorService(db),
                                          SqlEntryPolicyRepository(db), KnowledgeService(db))
    drafts = ResumeDraftService(repository=SqlResumeDraftRepository(db), catalog=catalog)
    return ResumeIntakeService(repository=SqlResumeIntakeRepository(db),
                               draft_service=drafts, policy=selected_policy_for_tests())


def seed_owner(connection, label):
    # Synthetic fixture rows belong only to the newly acquired proof database.
    # Authentication is outside the intake closure; no auth procedure is needed.
    owner = 'intake-proof-' + label
    sql(connection, "DECLARE @UserId int; "
        "INSERT dbo.app_users(user_key,display_name) VALUES(?,N'Synthetic intake owner'); "
        "SET @UserId=CONVERT(int,SCOPE_IDENTITY()); "
        "INSERT dbo.member_profiles(user_id,display_name,visibility) "
        "VALUES(@UserId,N'Synthetic intake owner',N'private');", (owner,))
    return owner


def seed_candidate(connection, owner, record_type='role'):
    from services.living_resume_editor_service import normalize_editor_values
    # Seed only mutable evidence in the owned synthetic database. The subsequent
    # canonical write runs the actual production service/procedure boundary.
    values = ({'wording': 'Synthetic impact without a selected parent'} if record_type == 'accomplishment'
              else {'role_title': 'Synthetic Engineer', 'employer_name': 'Synthetic Employer'})
    normalized = normalize_editor_values(record_type, values)
    source, override = str(uuid4()), str(uuid4())
    candidate = {'source_key': source, 'source_version': 1, 'override_key': override,
                 'record_type': record_type, 'state': 'pending', 'values': values,
                 'canonical_values': normalized}
    sql(connection, "DECLARE @Owner bigint=(SELECT p.profile_id FROM dbo.member_profiles p "
        "JOIN dbo.app_users u ON p.user_id=u.id WHERE u.user_key=?); "
        "INSERT dbo.resume_intake_sources(owner_profile_id,source_key,kind,state,source_version,"
        "entrance,policy_version,structured_values_json,source_text) "
        "VALUES(@Owner,?,'recording','active',1,'my_data',1,?,N'synthetic transcript');",
        (owner, source, json.dumps({'_extracted_candidates': [candidate]})))
    return source, override


class CapturedCommand(Exception):
    pass


def source_command(connection, owner, override, request=None):
    service = stack(connection)
    captured = {}
    def capture(_owner, procedure, request_id, payload):
        captured.update(procedure=procedure, request_id=request_id, payload=copy.deepcopy(payload))
        raise CapturedCommand()
    service.repository.commit_command = capture
    try:
        service.keep_extracted_separate(owner, {'type': 'keep_extracted_separate',
            'request_id': request or str(uuid4()), 'override_key': override})
    except CapturedCommand:
        pass
    check(bool(captured), 'production service did not stage source command')
    return captured


def execute_source(connection, owner, command):
    sets = EngineDatabase(connection).execute_procedure(command['procedure'], [
        ('@UserKey', owner), ('@RequestId', command['request_id']),
        ('@CommandJson', command['payload'])])
    return next(rows[0] for rows in reversed(sets) if rows)


def draft_command(snapshot, text):
    from datetime import datetime, timezone
    moment = datetime.now(timezone.utc).isoformat()
    return {'expected_revision': snapshot['draft_revision'],
            'expected_lifecycle_epoch': snapshot['lifecycle_epoch'], 'drafts': {'composer': {
                'draft_key': 'composer', 'version': snapshot['draft_revision'] + 1,
                'state': 'active', 'text': text, 'items': [], 'attachments': [],
                'created_at': moment, 'updated_at': moment, 'expires_at': None,
                'last_request_id': str(uuid4())}}}


def execute_draft(connection, owner, command):
    return EngineDatabase(connection).execute_procedure('usp_ReplaceResumeIntakeDraftsForOwner', [
        ('@UserKey', owner), ('@RequestId', str(uuid4())), ('@CommandJson', command)])[-1][0]


def race(connect, callbacks):
    """Two independently opened SQL connections enter the operation together."""
    barrier = threading.Barrier(2, timeout=20)
    def run(callback):
        connection = connect('intake:' + proof.PROOF_POPULATED_DATABASE)
        try:
            barrier.wait()
            try:
                return ('ok', callback(connection))
            except Exception as error:
                return ('refused', {'source_fence': any(has_marker(error, code)
                    for code in ('RESUME_INTAKE_CHANGED', 'RESUME_INTAKE_NOT_FOUND'))})
        finally:
            connection.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, callback) for callback in callbacks]
        return [future.result(timeout=150) for future in futures]


def run_engine_contracts(connect, root: Path, cases: dict, diagnostics: dict):
    from scripts.run_resume_intake_sql_proof import GATE_MIGRATIONS, migration_closure
    from scripts.migration_registry import executable_sha256
    from services.resume_intake_service import ResumeIntakeConflictError
    def case(name, callback):
        diagnostics['active_phase'] = name
        callback()
        cases[name] = 'pass'

    def actual_gates():
        database = proof.PROOF_EMPTY_DATABASE
        check(not (root / '.env').exists(), 'unexpected environment file in isolated source')
        host, secret = os.environ.get('PEERSLATE_RESUME_PUBLICATION_SQL_HOST'), os.environ.get('MSSQL_SA_PASSWORD')
        check(host == proof.PROOF_SQL_CONTAINER and bool(secret), 'isolated gate connection required')
        manifest = json.loads((root / 'SQL FIles/Migrations/registry.json').read_text())
        entries = {row['id']: row for row in manifest['migrations']}
        diagnostics['generic_gates'] = {}
        for migration in GATE_MIGRATIONS:
            diagnostics['active_phase'] = 'generic_gate:' + migration
            connection = connect('intake:' + database)
            try:
                # Fixed database on a freshly acquired invocation-owned server;
                # no user-supplied database, DSN or existing resource is accepted.
                sql(connection, 'USE master; ALTER DATABASE [' + database + '] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; '
                    'DROP DATABASE [' + database + ']; CREATE DATABASE [' + database + '];')
            finally:
                connection.close()
            output = Path('/tmp') / ('intake-gate-' + migration + '.json')
            environment = os.environ.copy()
            environment['AZURE_SQL_CONNECTIONSTRING'] = (f'Server={host};Database={database};UID=sa;'
                f'PWD={secret};Encrypt=yes;TrustServerCertificate=yes;')
            completed = subprocess.run([sys.executable, '-B', str(root / 'scripts/govern_sql_migrations.py'),
                '--database', database, '--emit-evidence', str(output), 'gate', migration,
                '--expect-database', database, '--operator', 'invocation-owned-intake-proof'],
                cwd=root, env=environment, capture_output=True, text=True, timeout=240)
            if completed.returncode != 0 or not output.is_file():
                detail = proof.sanitize_proof_error(RuntimeError((completed.stderr or completed.stdout)[-3000:]), (secret,))
                raise AssertionError('actual generic gate failed: ' + migration + ': ' + detail)
            emitted = json.loads(output.read_text())
            check(emitted.get('action') == 'gate' and emitted.get('migration_id') == migration
                and emitted.get('database') == database
                and emitted['proof']['executable_sha256'] == executable_sha256(root / entries[migration]['forward'])
                and any(step['step'] == 'rollback rehearsal' for step in emitted['steps']),
                'incomplete actual generic gate: ' + migration)
            diagnostics['generic_gates'][migration] = emitted
    case('actual_generic_migration_gates', actual_gates)

    diagnostics['active_phase'] = 'populated_fixture_connect'
    connection = connect('intake:' + proof.PROOF_POPULATED_DATABASE)
    try:
        diagnostics['active_phase'] = 'populated_fixture_apply_prerequisites'
        closure = migration_closure(root)
        for row in closure[:-1]:
            proof.apply_sql_file(connection, root / row['forward'])
        diagnostics['active_phase'] = 'populated_fixture_owner_a'
        owner = seed_owner(connection, 'a')
        diagnostics['active_phase'] = 'populated_fixture_owner_b'
        other = seed_owner(connection, 'b')
        from services.living_resume_editor_service import normalize_editor_values
        command_id = str(uuid4())
        diagnostics['active_phase'] = 'populated_fixture_existing_canonical_role'
        EngineDatabase(connection).execute_procedure('usp_CommitLivingResumeCommandForOwner', [
            ('@UserKey', owner), ('@CommandId', command_id), ('@CommandJson', {
                'command_id': command_id, 'type': 'create_role', 'record_key': str(uuid4()),
                'parent_key': None, 'expected_version': None,
                'values': normalize_editor_values('role', {'role_title': 'Existing synthetic role',
                                                         'employer_name': 'Existing synthetic employer'})})])
        target = closure[-1]
        rollback = root / target['rollback']
        def additive():
            before = scalar(connection, 'SELECT COUNT(*) AS n FROM dbo.member_profiles')
            canonical_before = scalar(connection, 'SELECT * FROM dbo.career_experiences FOR JSON PATH')
            proof.apply_sql_file(connection, root / target['forward'])
            proof.apply_sql_file(connection, root / 'SQL FIles/Verification/PS-RESUME-INTAKE-002_durable_composer_verify.sql')
            proof.apply_sql_file(connection, rollback)
            check(scalar(connection, 'SELECT COUNT(*) AS n FROM dbo.member_profiles') == before, 'rollback changed owners')
            check(scalar(connection, 'SELECT * FROM dbo.career_experiences FOR JSON PATH') == canonical_before,
                  'additive rollback changed canonical rows')
            proof.apply_sql_file(connection, root / target['forward'])
        case('populated_additive_rollback_preserves_canonical', additive)
        service = stack(connection)
        def reload():
            diagnostics['active_phase'] = 'durable_reload_save'
            service.save_draft(owner, {'request_id': str(uuid4()), 'text': 'private unfinished draft'})
            diagnostics['active_phase'] = 'durable_reload_owner_read'
            check(stack(connection).get_draft(owner)['draft']['text'] == 'private unfinished draft', 'reload failed')
            diagnostics['active_phase'] = 'durable_reload_foreign_read'
            check(stack(connection).get_draft(other)['draft'] is None, 'foreign draft disclosed')
        case('durable_reload_owner_isolation', reload)
        def drafts_race():
            snapshot = service.repository.load_owner(owner)
            results = race(connect, [lambda c: execute_draft(c, owner, draft_command(snapshot, 'device-a')),
                                     lambda c: execute_draft(c, owner, draft_command(snapshot, 'device-b'))])
            check(all(outcome == 'ok' for outcome, _ in results)
                and sorted(row['outcome'] for _, row in results) == ['applied', 'conflict'], 'draft CAS race lost fence')
        case('draft_cas_two_connections', drafts_race)
        def lost_reply():
            from datetime import datetime, timedelta, timezone
            service.discard_draft(owner, {})
            body = {'request_id': str(uuid4()), 'text': 'recoverable draft'}
            first = service.save_draft(owner, body)['draft']  # Ignore committed response deliberately.
            check(stack(connection).save_draft(owner, body)['replayed'], 'lost reply replay failed')
            service.discard_draft(owner, {})
            newer = service.save_draft(owner, {'request_id': str(uuid4()), 'text': 'recreated'})['draft']
            check(newer['version'] > first['version'], 'draft tombstone ABA')
            try:
                service.save_draft(owner, {'request_id': str(uuid4()), 'text': 'stale', 'expected_version': first['version']})
            except ResumeIntakeConflictError:
                pass
            else:
                raise AssertionError('old device overwrote recreated draft')
            service.discard_draft(owner, {})
            past = datetime.now(timezone.utc) - timedelta(days=31)
            expired = service.save_draft(owner, {'request_id': str(uuid4()), 'text': 'expired'}, now=past)['draft']
            check(service.get_draft(owner)['draft'] is None, 'SQL expiry did not discard draft')
            restored = service.save_draft(owner, {'request_id': str(uuid4()), 'text': 'after expiry'})['draft']
            check(restored['version'] > expired['version'], 'SQL expiry lost revision tombstone')
        case('draft_lost_reply_replay_discard_recreate', lost_reply)

        def counts():
            return tuple(scalar(connection, 'SELECT COUNT(*) AS n FROM dbo.' + name) for name in (
                'career_experiences', 'resume_intake_command_receipts', 'resume_intake_extracted_actions'))
        replay_fixture = {}
        def atomic():
            source, override = seed_candidate(connection, owner)
            command = source_command(connection, owner, override)
            before = counts()
            result = execute_source(connection, owner, command)
            check(not result['replayed'] and counts() == tuple(n + 1 for n in before), 'atomic rows missing')
            canonical_key = command['payload']['submission']['canonical_intents'][0]['command']['record_key']
            check(scalar(connection, "SELECT COUNT(*) FROM dbo.career_chapters c "
                "JOIN dbo.slate_entities e ON e.entity_id=c.entity_id AND e.owner_profile_id=c.owner_profile_id "
                "WHERE c.chapter_key=? AND c.visibility='private' AND c.approval_status='draft' "
                "AND c.publication_status='unpublished' AND e.visibility='private' AND e.approval_status='draft' "
                "AND e.publication_status='unpublished' AND NOT EXISTS(SELECT 1 FROM dbo.entry_policy_records p "
                "WHERE p.entry_key=c.chapter_key AND (p.resume_display=1 OR p.visitor_ai=1))",
                (canonical_key,)) == 1, 'source action expanded permission')
            payload = json.loads(scalar(connection, 'SELECT structured_values_json FROM dbo.resume_intake_sources WHERE source_key=?', (source,)))
            candidate = payload['_extracted_candidates'][0]
            check(candidate['state'] == 'consumed' and 'values' not in candidate and 'canonical_values' not in candidate,
                  'source values survived consumption')
            check(execute_source(connection, owner, command)['replayed'], 'same-key replay failed')
            other_command = copy.deepcopy(command)
            other_command['request_id'] = str(uuid4())
            other_command['payload']['submission']['request_id'] = other_command['request_id']
            result = execute_source(connection, owner, other_command)
            check(result['replayed'] and str(UUID(str(result['receipt_request_id']))) == command['request_id'],
                  'new-key winner replay failed')
            check(counts() == tuple(n + 1 for n in before), 'replay repeated canonical write')
            receipt = scalar(connection, 'SELECT result_json FROM dbo.resume_intake_command_receipts WHERE request_id=?', (command['request_id'],))
            check('Synthetic Engineer' not in receipt and 'canonical_values' not in receipt, 'receipt retained wording')
            replay_fixture.update(source=source, command=command)
        case('atomic_source_consumption_and_replay', atomic)
        def purged_replay():
            source, command = replay_fixture['source'], replay_fixture['command']
            service.purge_source(owner, {'request_id': str(uuid4()), 'source_key': source})
            before = counts()
            replayed = execute_source(connection, owner, command)
            check(replayed['replayed'] and 'canonical_values' not in replayed['result_json']
                and 'Synthetic Engineer' not in replayed['result_json'], 'purged same-key history retained source wording')
            changed_key = copy.deepcopy(command)
            changed_key['request_id'] = str(uuid4())
            changed_key['payload']['submission']['request_id'] = changed_key['request_id']
            expect_marker(lambda: execute_source(connection, owner, changed_key), 'RESUME_INTAKE_CHANGED')
            row = service.repository.load_owner(owner)['sources'][source]
            check(counts() == before and row['state'] == 'purged' and not row.get('structured_values'),
                  'purged replay resurrected source or wrote new history')
        case('source_replay_after_purge_no_resurrection', purged_replay)
        def impact():
            _, override = seed_candidate(connection, owner, 'accomplishment')
            command = source_command(connection, owner, override)
            check(not command['payload']['submission']['canonical_intents'], 'impact invented a parent')
            submission = command['payload']['submission']
            check(submission['proposals'][0]['proposed_values'] == submission['sources'][0]['structured_values'],
                  'impact proposal lost normalized source fields')
            before = scalar(connection, 'SELECT COUNT(*) FROM dbo.career_achievements')
            bad = copy.deepcopy(command)
            bad['payload']['submission']['proposals'][0]['proposed_values']['wording'] = 'forged'
            unchanged = counts()
            expect_marker(lambda: execute_source(connection, owner, bad), 'RESUME_INTAKE_VALIDATION')
            check(counts() == unchanged, 'impact refusal partially wrote')
            execute_source(connection, owner, command)
            check(scalar(connection, 'SELECT COUNT(*) FROM dbo.career_achievements') == before,
                  'unparented impact became canonical')
            check(scalar(connection, 'SELECT COUNT(*) FROM dbo.resume_intake_proposals WHERE submission_key=?',
                         (override,)) == 1, 'unparented impact lost proposal')
        case('impact_without_parent_remains_proposal', impact)
        def refusals():
            source, override = seed_candidate(connection, owner)
            command = source_command(connection, owner, override)
            before = counts()
            variants = [(other, copy.deepcopy(command)), (owner, copy.deepcopy(command)), (owner, copy.deepcopy(command))]
            variants[1][1]['payload']['source_binding']['source_version'] += 1
            variants[2][1]['payload']['submission']['canonical_intents'][0]['command']['values']['role_title'] = 'forged'
            markers = ('RESUME_INTAKE_NOT_FOUND', 'RESUME_INTAKE_CHANGED', 'RESUME_INTAKE_VALIDATION')
            for (selected_owner, bad), marker in zip(variants, markers):
                expect_marker(lambda: execute_source(connection, selected_owner, bad), marker)
                check(counts() == before, 'refusal partially wrote')
            for table, predicate in (
                ('app_users', 'user_key=?'),
                ('member_profiles', 'user_id=(SELECT id FROM dbo.app_users WHERE user_key=?)')):
                original = scalar(connection, 'SELECT active FROM dbo.' + table + ' WHERE ' + predicate, (owner,))
                check(original == 1, 'inactive-owner fixture was not active')
                sql(connection, 'UPDATE dbo.' + table + ' SET active=0 WHERE ' + predicate, (owner,))
                try:
                    expect_marker(lambda: execute_source(connection, owner, command), 'RESUME_INTAKE_NOT_FOUND')
                    check(counts() == before, 'inactive owner refusal partially wrote')
                finally:
                    sql(connection, 'UPDATE dbo.' + table + ' SET active=? WHERE ' + predicate, (original, owner))
            check(service.repository.load_owner(owner)['sources'][source]['state'] == 'active', 'refusal consumed source')
        case('foreign_stale_and_changed_values_refused', refusals)
        def keep_race():
            _, override = seed_candidate(connection, owner)
            a, b = source_command(connection, owner, override), source_command(connection, owner, override)
            before = counts()
            results = race(connect, [lambda c: execute_source(c, owner, a), lambda c: execute_source(c, owner, b)])
            check(all(outcome == 'ok' for outcome, _ in results)
                and sorted(bool(row['replayed']) for _, row in results) == [False, True], 'keep race did not choose one winner')
            check(counts() == tuple(n + 1 for n in before), 'keep race duplicate canonical write')
        case('source_keep_two_connections', keep_race)
        def purge_keep():
            source, override = seed_candidate(connection, owner)
            command = source_command(connection, owner, override)
            before = counts()
            results = race(connect, [lambda c: execute_source(c, owner, command),
                lambda c: stack(c).purge_source(owner, {'request_id': str(uuid4()), 'source_key': source})])
            check(results[1][0] == 'ok', 'purge failed')
            check(results[0][0] == 'ok' or results[0][1].get('source_fence'), 'unexpected source race failure')
            current = service.repository.load_owner(owner)['sources'][source]
            check(current['state'] == 'purged' and current.get('text') is None
                and not current.get('structured_values'), 'purge resurrected source words')
            check(counts()[0] == before[0] + (1 if results[0][0] == 'ok' else 0), 'purge/keep partial canonical write')
        case('purge_versus_keep_two_connections', purge_keep)
        def purge_save():
            source, _ = seed_candidate(connection, owner)
            current = service.get_draft(owner)['draft']
            request = {'request_id': str(uuid4()), 'expected_version': current['version'],
                'text': 'preserved after purge', 'attachments': [
                    {'client_key': 'proof-recording', 'kind': 'recording', 'source_key': source}]}
            results = race(connect, [lambda c: stack(c).save_draft(owner, request),
                lambda c: stack(c).purge_source(owner, {'request_id': str(uuid4()), 'source_key': source})])
            check(all(outcome == 'ok' for outcome, _ in results), 'purge/save failed')
            row = stack(connection).get_draft(owner)['draft']
            check(row['text'] == request['text'] and row['attachments'][0]['needs_reattach'], 'purge/save lost words or attachment fence')
        case('purge_versus_save_two_connections', purge_save)
        def injected_failure():
            source, override = seed_candidate(connection, owner)
            command = source_command(connection, owner, override)
            before = counts()
            sql(connection, "CREATE TRIGGER dbo.trg_intake_proof_fail ON dbo.resume_intake_extracted_actions "
                "AFTER INSERT AS THROW 52999,'INTAKE_PROOF_INJECTED_FAILURE',1;")
            try:
                expect_marker(lambda: execute_source(connection, owner, command), 'INTAKE_PROOF_INJECTED_FAILURE')
            finally:
                sql(connection, 'DROP TRIGGER dbo.trg_intake_proof_fail;')
            check(counts() == before, 'failure left canonical/receipt/history rows')
            candidate = service.repository.load_owner(owner)['sources'][source]['structured_values']['_extracted_candidates'][0]
            check(candidate['state'] == 'pending' and bool(candidate.get('canonical_values')), 'failure consumed mutable source')
        case('injected_failure_rolls_back_canonical_source_receipt', injected_failure)
        def guarded():
            service.discard_draft(owner, {})
            expect_marker(lambda: proof.apply_sql_file(connection, rollback),
                          'RESUME_INTAKE_DURABLE_ROLLBACK_HAS_HISTORY')
            check(scalar(connection, "SELECT COUNT(*) FROM dbo.schema_migrations WHERE migration_id='PS-RESUME-INTAKE-002'") == 1,
                  'guarded rollback removed ledger')
        case('guarded_history_rollback', guarded)
    finally:
        connection.close()
