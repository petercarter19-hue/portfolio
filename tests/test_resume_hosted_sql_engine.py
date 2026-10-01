"""Hosted-only real-engine oracles. Import never opens SQL or launches Docker."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from tests.test_resume_intake_sql_engine import (
    EngineDatabase, sql, scalar, check, expect_marker, bounded_sql_failure as intake_failure,
    race, seed_owner, seed_candidate, stack,
)
from services import resume_publication_adapters as proof

ENGINE_CASES=(
    'actual_hosted_generic_gate', 'populated_hosted_additive_rollback',
    'original_owner_and_inactive_isolation', 'original_reserve_upload_version_cas',
    'original_retained_after_source_purge_and_draft_expiry', 'explicit_delete_only_cleanup',
    'pending_delete_recovery_and_version_cas', 'upload_delete_two_connections',
    'source_purge_original_read_two_connections', 'persisted_qualification_cap_and_replay',
    'qualification_concurrency_two_connections', 'immutable_qualification_config_refusal',
    'guarded_hosted_rollback',
)

def bounded_sql_failure(error):
    from tests.test_resume_intake_sql_engine import has_marker
    result=intake_failure(error)
    result['markers']=[marker for marker in ('ORIGINAL_INVALID','ORIGINAL_ROLLBACK_HAS_MEMBER_DATA',
        'ORIGINAL_SCHEMA_VERIFY_FAILED','EXTRACTION_LIMITS_INVALID') if has_marker(error,marker)]
    return result


def gate_failure_diagnostic(migration, result, *, secrets=(), timed_out=False, evidence_missing=False):
    """Closed classifications only; never export stdout/stderr/command/env."""
    def safe_text(value):
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='replace')
        text = value if isinstance(value, str) else ''
        for secret in secrets:
            if isinstance(secret, str) and secret:
                text = text.replace(secret, '[redacted]')
        # Do not interpret a credential-shaped value as a SQL number/class.
        text = re.sub(r'(?i)\b(?:pwd|password|uid|user id|server|database)\s*=\s*[^;\r\n]*', '[redacted]', text)
        return text[-65536:]
    stdout = safe_text(getattr(result, 'stdout', None))
    stderr = safe_text(getattr(result, 'stderr', None))
    detail = stdout + '\n' + stderr
    steps = ('prerequisites', 'forward apply', 're-apply is a no-op', 'verification',
             'rollback rehearsal', 'forward apply after rollback')
    completed = [name for line in stdout.splitlines() for name in steps
                 if re.match(r'^\s*\[\d{1,2}\] ' + re.escape(name) + r'(?: -|$)', line)]
    markers = {
        'verifier_missing_verified': 'did not return verified = 1 against',
        'already_applied': 'A gate must start from a database that does not carry it',
        'missing_forward_ledger': 'ran without recording a ledger row',
        'non_idempotent_objects': 'a second apply changed the object inventory',
        'non_idempotent_ledger': 'a second apply changed the number of ledger rows',
        'rollback_ledger_remaining': 'rollback ran but left the ledger row in place',
        'reapply_ledger_missing': 'Re-applying after rollback did not restore the ledger row',
    }
    matched = [key for key, phrase in markers.items() if phrase in detail]
    classes = ('GovernedMigrationError', 'RegistryError', 'ProgrammingError', 'OperationalError',
               'IntegrityError', 'InterfaceError', 'DatabaseError', 'RuntimeError', 'ValueError',
               'TypeError', 'KeyError', 'FileNotFoundError', 'ModuleNotFoundError', 'Error')
    found_classes = [name for name in classes if re.search(r'(?m)^(?:FAILED: )?' + name + ':', detail)]
    numbers = sorted({int(value) for value in re.findall(
        r'\((\d{1,5})\)(?=\s*\(SQL[A-Za-z]+\))', detail)})[:8]
    code = getattr(result, 'returncode', None)
    return {'migration': migration if isinstance(migration, str) and re.fullmatch(r'PS-[A-Z0-9-]{1,64}', migration) else 'unknown',
            'returncode': code if type(code) is int and -(2**31) <= code < 2**31 else None,
            'timed_out': bool(timed_out), 'evidence_missing': bool(evidence_missing),
            'last_completed_step': completed[-1] if completed else None,
            'failed_stage': 'verification' if 'verifier_missing_verified' in matched else 'unestablished',
            'check_markers': matched, 'public_error_classes': found_classes[:8], 'native_error_numbers': numbers}


def run_generic_gate(root, migration, database, output, environment, diagnostics):
    secrets = (environment.get('MSSQL_SA_PASSWORD'), environment.get('AZURE_SQL_CONNECTIONSTRING'))
    try:
        result = subprocess.run([sys.executable, '-B', str(root/'scripts/govern_sql_migrations.py'),
            '--database', database, '--emit-evidence', str(output), 'gate', migration,
            '--expect-database', database, '--operator', 'invocation-owned-hosted-proof'],
            cwd=root, env=environment, capture_output=True, timeout=240)
    except subprocess.TimeoutExpired as error:
        diagnostics['generic_gate_failure'] = gate_failure_diagnostic(
            migration, error, secrets=secrets, timed_out=True, evidence_missing=not output.is_file())
        check(False, 'actual hosted generic gate timed out')
    if result.returncode != 0 or not output.is_file():
        diagnostics['generic_gate_failure'] = gate_failure_diagnostic(
            migration, result, secrets=secrets, evidence_missing=not output.is_file())
        check(False, 'actual hosted generic gate failed')

def command(connection, owner, value):
    return EngineDatabase(connection).execute_procedure('usp_CommitResumeOriginalFileForOwner',
        [('@UserKey',owner),('@CommandJson',value)])[-1][0]

def originals(connection, owner, key=None):
    from services.resume_original_file_repository import SqlResumeOriginalFileRepository
    return SqlResumeOriginalFileRepository(EngineDatabase(connection)).list(owner,key)

def reserve_file(connection, owner, source=None):
    key=str(uuid4()); token=uuid4().hex
    value={'type':'reserve','original_key':key,'source_key':source or str(uuid4()),
        'source_version':1,'blob_name':'resume/v1/'+token[:2]+'/'+token,
        'sha256':'a'*64,'byte_length':26,'content_type':'text/plain'}
    check(command(connection,owner,value)['outcome']=='ok','original reserve failed')
    return key,value

def uploaded(connection, owner, key, expected=1):
    return command(connection,owner,{'type':'uploaded','original_key':key,
        'expected_version':expected,'blob_etag':'"synthetic-etag"'})

def budget(connection, owner, scope, request=None, **changes):
    values=dict(ReservationMicroUsd=998400,MaximumCalls=6,HardCapMicroUsd=6000000,ConcurrentRequests=1)
    values.update(changes)
    return EngineDatabase(connection).first_row('usp_ReserveResumeHostedExtractionForOwner',
        [('@UserKey',owner),('@Scope',scope),('@RequestId',request or str(uuid4()))]+
        [('@'+name,value) for name,value in values.items()])['reserved']

def finish(connection, owner, scope, request):
    return EngineDatabase(connection).first_row('usp_FinishResumeHostedExtractionForOwner',
        [('@UserKey',owner),('@Scope',scope),('@RequestId',request)])['finished']

def run_engine_contracts(connect, root:Path, cases:dict, diagnostics:dict):
    from scripts.run_resume_hosted_sql_proof import TARGET, GATE_MIGRATIONS, migration_closure
    from scripts.migration_registry import executable_sha256
    def case(name, callback):
        diagnostics['active_phase']=name
        callback()
        cases[name]='pass'
    def actual_gate():
        database=proof.PROOF_EMPTY_DATABASE
        check(not (root/'.env').exists(),'unexpected isolated environment file')
        host=os.environ.get('PEERSLATE_RESUME_PUBLICATION_SQL_HOST'); secret=os.environ.get('MSSQL_SA_PASSWORD')
        check(host==proof.PROOF_SQL_CONTAINER and bool(secret),'isolated gate required')
        entries={row['id']:row for row in migration_closure(root)}
        diagnostics['generic_gates']={}
        for migration in GATE_MIGRATIONS:
            diagnostics['active_phase']='generic_gate:'+migration
            reset=connect('hosted:'+database)
            try:
                sql(reset,'USE master; ALTER DATABASE ['+database+'] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; '
                    'DROP DATABASE ['+database+']; CREATE DATABASE ['+database+'];')
            finally:reset.close()
            output=Path('/tmp')/('hosted-gate-'+migration+'.json')
            environment=os.environ.copy()
            environment['AZURE_SQL_CONNECTIONSTRING']=f'Server={host};Database={database};UID=sa;PWD={secret};Encrypt=yes;TrustServerCertificate=yes;'
            run_generic_gate(root,migration,database,output,environment,diagnostics)
            emitted=json.loads(output.read_text())
            check(emitted.get('action')=='gate' and emitted.get('migration_id')==migration
                and emitted.get('database')==database
                and emitted['proof']['executable_sha256']==executable_sha256(root/entries[migration]['forward'])
                and any(step['step']=='rollback rehearsal' for step in emitted['steps']), 'incomplete hosted gate')
            diagnostics['generic_gates'][migration]=emitted
    case('actual_hosted_generic_gate',actual_gate)
    connection=connect('hosted:'+proof.PROOF_POPULATED_DATABASE)
    try:
        closure=migration_closure(root)
        for row in closure[:-1]:proof.apply_sql_file(connection,root/row['forward'])
        owner=seed_owner(connection,'hosted-a'); other=seed_owner(connection,'hosted-b')
        from services.living_resume_editor_service import normalize_editor_values
        canonical_request=str(uuid4())
        EngineDatabase(connection).execute_procedure('usp_CommitLivingResumeCommandForOwner',[
            ('@UserKey',owner),('@CommandId',canonical_request),('@CommandJson',dict(
                command_id=canonical_request,type='create_role',record_key=str(uuid4()),
                parent_key=None,expected_version=None,
                values=normalize_editor_values('role',dict(role_title='Existing synthetic hosted role',
                    employer_name='Existing synthetic hosted employer'))))])
        target=closure[-1]; rollback=root/target['rollback']
        def additive():
            before=scalar(connection,'SELECT * FROM dbo.member_profiles FOR JSON PATH')
            canonical=scalar(connection,'SELECT * FROM dbo.career_experiences FOR JSON PATH')
            proof.apply_sql_file(connection,root/target['forward'])
            proof.apply_sql_file(connection,root/'SQL FIles/Verification/PS-RESUME-HOSTED-001_original_files_verify.sql')
            check(EngineDatabase(connection).first_row('usp_GetResumeHostedReadiness')['schema_ready'],'applied hosted readiness unavailable')
            proof.apply_sql_file(connection,rollback)
            check(scalar(connection,'SELECT * FROM dbo.member_profiles FOR JSON PATH')==before,'hosted rollback changed owners')
            check(scalar(connection,'SELECT * FROM dbo.career_experiences FOR JSON PATH')==canonical,'hosted rollback changed canonical')
            proof.apply_sql_file(connection,root/target['forward'])
        case('populated_hosted_additive_rollback',additive)
        key,descriptor=reserve_file(connection,owner)
        def isolation():
            check(originals(connection,other,key)==[],'foreign original disclosed')
            check(command(connection,other,dict(type='delete',original_key=key,expected_version=1,request_id=str(uuid4())))['outcome']=='not_found','foreign delete admitted')
            for table,predicate in [('app_users','user_key=?'),('member_profiles','user_id=(SELECT id FROM dbo.app_users WHERE user_key=?)')]:
                sql(connection,'UPDATE dbo.'+table+' SET active=0 WHERE '+predicate,(owner,))
                try:
                    check(originals(connection,owner,key)==[],'inactive original disclosed')
                    check(uploaded(connection,owner,key)['outcome']=='not_found','inactive upload admitted')
                    count=scalar(connection,'SELECT COUNT(*) FROM dbo.resume_hosted_extraction_budgets')
                    check(not budget(connection,owner,'hosted-inactive-'+uuid4().hex),'inactive budget admitted')
                    check(scalar(connection,'SELECT COUNT(*) FROM dbo.resume_hosted_extraction_budgets')==count,'inactive budget partially changed')
                finally:sql(connection,'UPDATE dbo.'+table+' SET active=1 WHERE '+predicate,(owner,))
        case('original_owner_and_inactive_isolation',isolation)
        def upload_cas():
            check(command(connection,owner,descriptor)['outcome']=='conflict','duplicate original reserved')
            check(uploaded(connection,owner,key,2)['outcome']=='conflict','stale upload admitted')
            check(uploaded(connection,owner,key)['version']==2,'upload did not advance version')
            check(uploaded(connection,owner,key)['outcome']=='conflict','upload repeated')
            row=originals(connection,owner,key)[0]
            check(row['downloadable'] and row['sha256']==descriptor['sha256'] and row['byte_length']==26,'uploaded metadata invalid')
        case('original_reserve_upload_version_cas',upload_cas)
        service=stack(connection)
        def retention():
            source,_=seed_candidate(connection,owner)
            source_key,_=reserve_file(connection,owner,source)
            uploaded(connection,owner,source_key)
            service.purge_source(owner,{'request_id':str(uuid4()),'source_key':source})
            service.save_draft(owner,{'request_id':str(uuid4()),'text':'synthetic unfinished'},now=datetime.now(timezone.utc)-timedelta(days=31))
            check(service.get_draft(owner)['draft'] is None,'draft expiry fixture failed')
            check(originals(connection,owner,source_key)[0]['downloadable'],'source purge or draft expiry stranded original')
            check(originals(connection,owner,key)[0]['downloadable'],'source-less original stranded')
        case('original_retained_after_source_purge_and_draft_expiry',retention)
        def explicit_only():
            staged,_=reserve_file(connection,owner)
            sql(connection,'UPDATE dbo.resume_original_files SET created_at_utc=DATEADD(day,-365,SYSUTCDATETIME())')
            rows=EngineDatabase(connection).first_result('usp_ClaimResumeOriginalCleanup',[('@Limit',100)])
            check(rows==[],'age or source absence created deletion intent')
            check(originals(connection,owner,staged)[0]['state']=='reserved','staged reservation auto deleted')
            check(originals(connection,owner,key)[0]['downloadable'],'retained original auto deleted')
        case('explicit_delete_only_cleanup',explicit_only)
        def deletion():
            request=str(uuid4()); payload=dict(type='delete',original_key=key,expected_version=2,request_id=request)
            pending=command(connection,owner,payload)
            check(pending['state']=='delete_pending' and pending['version']==3,'explicit delete not durable')
            check(command(connection,owner,payload)['version']==3,'lost reply delete replay changed version')
            check(not originals(connection,owner,key)[0]['downloadable'],'pending delete downloadable')
            repository=EngineDatabase(connection)
            rows=repository.first_result('usp_ClaimResumeOriginalCleanup',[('@Limit',100)])
            check([str(UUID(str(row['original_key']))) for row in rows]==[key],'cleanup admits unrelated original')
            check(not repository.first_row('usp_CompleteResumeOriginalCleanup',[('@OriginalKey',key),('@ExpectedVersion',2),('@ConfirmedEtag','"synthetic-etag"')])['completed'],'stale cleanup won')
            check(repository.first_row('usp_CompleteResumeOriginalCleanup',[('@OriginalKey',key),('@ExpectedVersion',3),('@ConfirmedEtag','"synthetic-etag"')])['completed'],'pending recovery failed')
            check(not repository.first_row('usp_CompleteResumeOriginalCleanup',[('@OriginalKey',key),('@ExpectedVersion',3),('@ConfirmedEtag','"synthetic-etag"')])['completed'],'duplicate cleanup won')
            final=originals(connection,owner,key)[0]
            check(final['state']=='deleted' and final['blob_name'] is None,'delete tombstone invalid')
        case('pending_delete_recovery_and_version_cas',deletion)
        def upload_delete_race():
            racing,_=reserve_file(connection,owner)
            request=str(uuid4())
            results=race(connect,[lambda c:uploaded(c,owner,racing),lambda c:command(c,owner,
                dict(type='delete',original_key=racing,expected_version=1,request_id=request))])
            check(all(kind=='ok' for kind,_ in results) and sorted(row['outcome'] for _,row in results)==['conflict','ok'],'upload/delete CAS race invalid')
            row=originals(connection,owner,racing)[0]
            check(row['version']==2 and row['state'] in {'uploaded','delete_pending'},'race metadata invalid')
            if row['state']=='delete_pending':
                check(row['blob_name'] and row['blob_etag'] is None,'uncertain upload path lost')
                check(command(connection,owner,dict(type='deleted',original_key=racing,expected_version=2))['outcome']=='conflict','unconfirmed upload intent forgotten')
                check(uploaded(connection,owner,racing,expected=2)['state']=='delete_pending','late completion restored access')
                check(not originals(connection,owner,racing)[0]['downloadable'],'late upload downloadable after delete')
        case('upload_delete_two_connections',upload_delete_race)
        def purge_read_race():
            source,_=seed_candidate(connection,owner)
            retained,_=reserve_file(connection,owner,source); uploaded(connection,owner,retained)
            results=race(connect,[lambda c:stack(c).purge_source(owner,{'request_id':str(uuid4()),'source_key':source}),
                lambda c:originals(c,owner,retained)])
            check(all(kind=='ok' for kind,_ in results) and results[1][1][0]['downloadable'],'purge/read ownership race failed')
            check(originals(connection,owner,retained)[0]['downloadable'],'purge stranded retained metadata')
        case('source_purge_original_read_two_connections',purge_read_race)
        exhausted='hosted-exhaust-'+uuid4().hex
        def cap_replay():
            for index in range(6):
                request=str(uuid4())
                check(budget(connection,owner,exhausted,request),'selected reservation refused')
                check(not budget(connection,owner,exhausted,request),'active request replay dispatched')
                check(not finish(connection,other,exhausted,request),'foreign finish admitted')
                check(finish(connection,owner,exhausted,request) and finish(connection,owner,exhausted,request),'finish replay unavailable')
                check(not budget(connection,owner,exhausted,request),'finished request replay dispatched')
            check(not budget(connection,owner,exhausted),'seventh dispatch admitted')
            check(scalar(connection,'SELECT prepaid_micro_usd FROM dbo.resume_hosted_extraction_budgets WHERE scope=?',(exhausted,))==5990400,'prepaid amount reset/refunded')
            check(scalar(connection,'SELECT dispatched_calls FROM dbo.resume_hosted_extraction_budgets WHERE scope=?',(exhausted,))==6,'dispatch count invalid')
        case('persisted_qualification_cap_and_replay',cap_replay)
        def concurrency():
            scope='hosted-race-'+uuid4().hex
            results=race(connect,[lambda c:budget(c,owner,scope),lambda c:budget(c,other,scope)])
            check(all(kind=='ok' for kind,_ in results) and sorted(bool(value) for _,value in results)==[False,True],'cross-owner aggregate concurrency exceeded')
            check(scalar(connection,'SELECT COUNT(*) FROM dbo.resume_hosted_extraction_reservations WHERE scope=? AND state=\'active\'',(scope,))==1,'aggregate active count invalid')
        case('qualification_concurrency_two_connections',concurrency)
        def immutable_config():
            scope='hosted-config-'+uuid4().hex; request=str(uuid4())
            check(budget(connection,owner,scope,request),'config reservation failed')
            check(finish(connection,owner,scope,request),'config finish failed')
            for changes in [dict(MaximumCalls=7),dict(HardCapMicroUsd=7000000),dict(ConcurrentRequests=2),dict(ReservationMicroUsd=1)]:
                check(not budget(connection,owner,scope,**changes),'immutable configuration changed')
            check(scalar(connection,'SELECT dispatched_calls FROM dbo.resume_hosted_extraction_budgets WHERE scope=?',(scope,))==1,'config refusal partially dispatched')
        case('immutable_qualification_config_refusal',immutable_config)
        def guarded():
            before=scalar(connection,'SELECT COUNT(*) FROM dbo.resume_original_files')
            expect_marker(lambda:proof.apply_sql_file(connection,rollback),'ORIGINAL_ROLLBACK_HAS_MEMBER_DATA')
            check(scalar(connection,'SELECT COUNT(*) FROM dbo.resume_original_files')==before,'rollback erased retained original')
            sql(connection,'BEGIN TRANSACTION; DELETE dbo.resume_original_files;')
            expect_marker(lambda:proof.apply_sql_file(connection,rollback),'ORIGINAL_ROLLBACK_HAS_MEMBER_DATA')
            check(scalar(connection,'SELECT COUNT(*) FROM dbo.resume_original_files')==before,'budget rollback guard lost prior originals')
            check(scalar(connection,"SELECT COUNT(*) FROM dbo.schema_migrations WHERE migration_id='PS-RESUME-HOSTED-001'")==1,'guarded rollback erased ledger')
        case('guarded_hosted_rollback',guarded)
    finally:connection.close()
