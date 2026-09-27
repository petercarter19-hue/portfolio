"""G real-engine oracles. Import/discovery never connects or executes SQL.

Called only inside the separately authorized invocation-owned SQL client.
Production repositories/services are used; identity content is synthetic.
"""
import base64
import binascii
import copy
import json
import re
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch

from services import resume_publication_adapters as proof

ENGINE_CASES = (
    'empty_forward_verify_rollback_reapply', 'populated_forward_rollback_preserves_canonical',
    'private_draft_atomic_publish_and_identity', 'exact_publish_replay_after_sharing_off',
    'changed_payload_same_key_denied', 'newer_canonical_refuses_stale_draft',
    'independent_display_ai_choices', 'private_candidate_preview_no_publication',
    'personal_entry_create_bind_publish', 'personal_correction_preserves_original',
    'foreign_owner_cannot_bind_personal_entry', 'withdrawn_identity_suppressed',
    'forged_canonical_token_refused_atomically', 'integrated_history_rollback_refused',
    'injected_commit_failure_rolls_back_canonical_draft_receipt', 'application_principal_boundary',
    'media_crop_atomic_publish_and_late_source_refusal',
    'canonical_rowversion_digit_hex_and_stale_sql_fence',
)


class EngineDatabase:
    """Same result-set shape as DatabaseService, bound to one isolated connection."""
    def __init__(self, connection):
        self.connection = connection

    def execute_procedure(self, procedure, parameters=()):
        from services.database_service import DatabaseServiceError
        if not procedure.replace('_', '').isalnum():
            raise ValueError('invalid procedure')
        statement = 'EXEC dbo.' + procedure
        if parameters:
            statement += ' ' + ', '.join(name + '=?' for name, _ in parameters)
        values = tuple(json.dumps(value, ensure_ascii=False, separators=(',', ':'))
                       if isinstance(value, dict) else value for _, value in parameters)
        cursor = self.connection.cursor()
        try:
            cursor.execute(statement, values)
            return proof._fetch_procedure_result_sets(cursor)
        except Exception as error:
            raise DatabaseServiceError('Isolated proof procedure failed.') from error
        finally:
            cursor.close()

    def first_result(self, procedure, parameters=()):
        sets = self.execute_procedure(procedure, parameters)
        return sets[0] if sets else []

    def first_row(self, procedure, parameters=()):
        rows = self.first_result(procedure, parameters)
        return rows[0] if rows else None

    def last_row(self, procedure, parameters=()):
        sets = self.execute_procedure(procedure, parameters)
        return sets[-1][-1] if sets and sets[-1] else None


def commit_draft_sql(drafts, owner, command):
    """Use the real SQL envelope while bypassing only Python currentness checks."""
    from services.resume_draft_service import _command_json
    payload = _command_json(drafts._normalize_command(command))
    return drafts.repository.commit_command(owner, command['request_id'], payload)


def _preview_token_shape(value, current):
    """Classify a failed token without exporting it or changing acceptance."""
    if type(value) is not str:
        return {'is_string': False}
    result = {'is_string': True, 'length': len(value), 'classification_limit_exceeded': len(value) > 128}
    if len(value) > 128:
        return result
    current_bytes = (bytes.fromhex(current) if type(current) is str and
                     re.fullmatch(r'[0-9a-fA-F]{16}', current) else None)
    result.update(current_is_eight_byte_hex=current_bytes is not None,
                  ascii_hex_only=bool(re.fullmatch(r'[0-9a-fA-F]+', value)),
                  has_0x_prefix=value.startswith(('0x', '0X')),
                  has_outer_whitespace=value != value.strip())
    decodings = {}
    if re.fullmatch(r'[0-9a-fA-F]{16}', value):
        decodings['plain_hex'] = bytes.fromhex(value)
    if re.fullmatch(r'0[xX][0-9a-fA-F]{16}', value):
        decodings['prefixed_hex'] = bytes.fromhex(value[2:])
    if len(value) == 12 and value.isascii():
        try:
            decoded = base64.b64decode(value, validate=True)
            if len(decoded) == 8 and base64.b64encode(decoded).decode('ascii') == value:
                decodings['base64'] = decoded
        except (ValueError, binascii.Error):
            pass
    if len(value) == 8 and all(ord(char) <= 255 for char in value):
        decodings['raw_latin1'] = value.encode('latin1')
    if re.fullmatch(r'(?:0|[1-9][0-9]{0,19})', value) and int(value) < 2**64:
        decodings['decimal_big_endian'] = int(value).to_bytes(8, 'big')
    for encoding in ('plain_hex', 'prefixed_hex', 'base64', 'raw_latin1', 'decimal_big_endian'):
        result[encoding + '_eight_bytes'] = encoding in decodings
        result[encoding + '_equals_current_bytes'] = (
            current_bytes is not None and encoding in decodings and decodings[encoding] == current_bytes)
    return result


def _preview_fence_snapshot(document, workspace):
    """Bounded structural evidence only; never retain IDs or source wording."""
    def scalar(value, *, token=False, kind=False):
        types = {str: 'str', int: 'int', bool: 'bool', type(None): 'null'}
        result = {'type': types.get(type(value), 'other')}
        if type(value) is bool or (type(value) is int and 0 <= value < 2**63):
            result['value'] = value
        elif token and type(value) is str and re.fullmatch(r'[0-9a-fA-F]{16}', value):
            result['value'] = value
        elif kind and value in ('role', 'education', 'credential', 'skill', 'accomplishment',
                                'achievement', 'project', 'knowledge'):
            result['value'] = value
        return result

    rows = document.get('entries', [])
    items = [item for item in workspace.get('items', []) if item.get('has_draft')]
    observations = []
    for item in items[:16]:
        matches = [row for row in rows if row.get('entry_key') == item.get('record_key')]
        row = matches[0] if len(matches) == 1 else {}
        observations.append({
            'matching_rows': len(matches),
            'record_type': scalar(item.get('record_type'), kind=True),
            'canonical_type': scalar(row.get('canonical_type'), kind=True),
            'has_draft': scalar(item.get('has_draft')),
            'orphaned': scalar(item.get('orphaned')),
            'draft_is_stale': scalar(item.get('draft_is_stale')),
            'content_token': scalar(item.get('content_token'), token=True),
            'base_content_token': scalar(item.get('draft_base_content_token'), token=True),
            'canonical_revision': scalar(row.get('canonical_revision'), token=True),
            'canonical_revision_shape': _preview_token_shape(
                row.get('canonical_revision'), item.get('content_token')),
            'access_revision': scalar(item.get('access_revision')),
            'base_access_revision': scalar(item.get('draft_base_access_revision')),
            'snapshot_access_revision': scalar(row.get('access_revision')),
        })
    return {'observation': 'actual_failing_projection_arguments',
            'snapshot_draft_revision': scalar(document.get('draft_revision')),
            'workspace_draft_revision': scalar(workspace.get('draft_version')),
            'saved_item_count': len(items), 'truncated': len(items) > 16, 'items': observations}


@contextmanager
def observe_preview_failure(diagnostics):
    """Delegate unchanged and preserve the original exception and result."""
    from services import member_visitor_ai_repository as repository
    original = repository._with_private_draft

    def observed(document, workspace):
        try:
            return original(document, workspace)
        except Exception:
            if 'private_preview_fence' not in diagnostics:
                try:
                    diagnostics['private_preview_fence'] = _preview_fence_snapshot(document, workspace)
                except Exception:
                    diagnostics['private_preview_fence'] = {'observation': 'structural_capture_unavailable'}
            raise

    with patch.object(repository, '_with_private_draft', observed):
        yield


def run_engine_contracts(connect, root: Path, cases: dict, diagnostics: dict):
    from scripts.run_mvp1_acceptance_sql_proof import migration_closure
    from services.entry_policy_repository import SqlEntryPolicyRepository
    from services.entry_policy_service import EntryPolicyService
    from services.living_resume_editor_service import LivingResumeEditorService
    from services.knowledge_service import KnowledgeService
    from services.resume_draft_repository import SqlResumeDraftRepository, LivingResumeCanonicalCatalog
    from services.resume_draft_service import ResumeDraftService
    from services.resume_publication_repository import SqlResumePublicationRepository
    from services.resume_publication_service import ResumePublicationService
    from services.profile_core_repository import SqlProfileCoreRepository
    from services.profile_core_service import ProfileCoreService, ProfileIdentityDraft, make_profile_draft
    from services.mvp1_profile_binding import Mvp1ProfileBinding
    from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository

    def check(condition, message):
        if not condition:
            raise AssertionError(message)

    def error_chain(error):
        seen, parts = set(), []
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            parts.append(type(error).__name__ + ': ' + str(error) + ' ' + str(getattr(error, 'code', '')))
            error = error.__cause__ or error.__context__
        return ' <- '.join(parts)

    def case(name, callback):
        try:
            callback()
        except Exception as error:
            raise RuntimeError('G oracle ' + name + ': ' + error_chain(error)) from error
        cases[name] = 'pass'

    def sql(connection, statement, parameters=()):
        cursor = connection.cursor()
        try:
            cursor.execute(statement, parameters)
            return proof._fetch_procedure_result_sets(cursor)
        finally:
            cursor.close()

    closure = migration_closure(root)
    migration = root / closure[-1]['forward']
    rollback = root / closure[-1]['rollback']
    verify = root / 'SQL FIles/Verification/PS-RESUME-IDENTITY-001_publication_identity_verify.sql'
    override_names = sorted(set(re.findall(r'CREATE OR ALTER PROCEDURE dbo\.(\w+)', migration.read_text(encoding='utf-8'))))
    check(len(override_names) == 14, 'unexpected G procedure override set')

    def module_definitions(connection):
        result = {}
        for name in override_names:
            definition = sql(connection, 'SELECT OBJECT_DEFINITION(OBJECT_ID(?)) AS definition', ('dbo.' + name,))[0][0]['definition']
            check(isinstance(definition, str), 'missing predecessor definition: ' + name)
            result[name] = definition.strip()
        return result

    connection = connect(proof.PROOF_EMPTY_DATABASE)
    try:
        def lifecycle():
            for item in closure[:-1]:
                proof.apply_sql_file(connection, root / item['forward'])
            predecessors = module_definitions(connection)
            for path in (migration, verify, rollback):
                proof.apply_sql_file(connection, path)
            restored = module_definitions(connection)
            for name in override_names:
                check(restored[name] == predecessors[name], 'rollback changed predecessor: ' + name)
            check(sql(connection, "SELECT COL_LENGTH(N'dbo.resume_media_command_receipts',N'catalog_source_bound') AS size")[0][0]['size'] is None,
                  'safe rollback retained catalog provenance column')
            for path in (migration, verify, migration, verify):
                proof.apply_sql_file(connection, path)
        case('empty_forward_verify_rollback_reapply', lifecycle)
    finally:
        connection.close()
    connection = connect(proof.PROOF_POPULATED_DATABASE)
    try:
        for item in closure[:-1]:
            proof.apply_sql_file(connection, root / item['forward'])
        owner = proof.seed_publication_owner(connection)['user_key']
        other = proof.seed_second_proof_owner(connection)
        def populated():
            before = proof.capture_publication_state(connection)
            for path in (migration, verify, rollback):
                proof.apply_sql_file(connection, path)
            check(proof.capture_publication_state(connection) == before, 'rollback changed canonical state')
            proof.apply_sql_file(connection, migration)
        case('populated_forward_rollback_preserves_canonical', populated)
        db = EngineDatabase(connection)
        policy_repo = SqlEntryPolicyRepository(db)
        policy = EntryPolicyService(repository=policy_repo)
        catalog = LivingResumeCanonicalCatalog(LivingResumeEditorService(db), policy_repo, KnowledgeService(db))
        drafts = ResumeDraftService(repository=SqlResumeDraftRepository(db), catalog=catalog)
        profiles = SqlProfileCoreRepository(db)
        core = ProfileCoreService(profiles)
        binding = Mvp1ProfileBinding(profiles)
        publications = SqlResumePublicationRepository(db)
        service = ResumePublicationService(repository=publications, draft_service=drafts, profile_binding=binding)
        service.policy_service = policy
        policy.publication_service = service
        key = proof.PROOF_ENTRY_KEY
        saved_commands = {}

        def edit_draft(entry_key, values):
            workspace = drafts.get_workspace(owner)
            item = next(row for row in workspace['items'] if row['record_key'] == entry_key)
            return drafts.commit(owner, dict(type='save_item', request_id=str(uuid4()), record_key=entry_key,
                record_type=item['record_type'], expected_draft_version=workspace['draft_version'],
                expected_content_token=item['content_token'], expected_access_revision=item['access_revision'], values=values))

        def publish(choices=None):
            reviewed = service.review_for_owner(owner, {'entries': choices} if choices is not None else {}).reviewed
            check(reviewed is not None, 'review did not produce a candidate')
            command = dict(type='publish', request_id=str(uuid4()), slug='g-proof-member',
                profile_identity=reviewed.candidate.profile_identity.to_payload() if reviewed.candidate.profile_identity else None,
                reviewed_digest=reviewed.digest, candidate=service.publish_candidate(reviewed))
            result = service.commit(owner, command)
            return command, result

        def identity_publish():
            draft = make_profile_draft(owner_key=owner, slug='g-proof-member',
                identity=ProfileIdentityDraft('Alex Synthetic', 'Builds useful tools', None, 'Synthetic proof only.'))
            profiles.put_draft(draft, expected_version=None)
            context = core.owner_context(actor_key=owner, subject_owner_key=owner, slug=draft.slug, purpose='edit')
            review = core.review_publication(context, expected_draft_version=draft.version, expected_public_revision=None)
            core.publish_publication(context, expected_draft_version=draft.version, expected_public_revision=None,
                candidate_digest=review['candidate_digest'], idempotency_key=str(uuid4()), confirmed=True)
            edit_draft(key, {'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Owner reviewed draft wording.'})
            saved_commands['first'], _ = publish([dict(entry_key=key, resume_display=True, visitor_ai=False)])
            public = service.guest_read(slug='g-proof-member')
            check(public['public_identity']['display_name'] == 'Alex Synthetic', 'approved identity missing')
            check('Owner reviewed draft wording.' in json.dumps(public['display']), 'draft was not published')
            check(not drafts.repository.load_owner(owner)['items'], 'applied draft not cleared')
        case('private_draft_atomic_publish_and_identity', identity_publish)

        def replay():
            service.commit(owner, dict(type='sharing_off', request_id=str(uuid4())))
            before = publications.load_owner(owner)
            service.commit(owner, saved_commands['first'])
            check(publications.load_owner(owner) == before, 'replay changed current state')
        case('exact_publish_replay_after_sharing_off', replay)

        def whole_state():
            # Compare all rows, not only the current publication. This detects
            # stray receipts, canonical/permission writes and foreign-owner writes.
            tables = ('resume_sharing_state', 'resume_publication_revisions', 'resume_publication_receipts',
                'resume_publication_outbox', 'resume_drafts', 'resume_draft_items', 'resume_draft_command_receipts',
                'resume_media_placements', 'resume_media_command_receipts', 'entry_policy_records',
                'career_chapters', 'career_skills', 'career_achievements', 'knowledge_items', 'knowledge_item_versions')
            return {table: sorted((repr(sorted(row.items())) for row in sql(connection, 'SELECT * FROM dbo.' + table)[0]))
                    for table in tables}

        def denied_unchanged(callback, reason):
            before = whole_state()
            try:
                callback()
            except Exception as error:
                check(reason.lower() in error_chain(error).lower(), 'wrong refusal: ' + error_chain(error))
                check(whole_state() == before, 'refusal partially changed durable state')
                return
            raise AssertionError('invalid operation accepted')
        def rowversion_tokens():
            # Exercise actual engine-generated rowversions, never fabricated tokens.
            # A bounded no-op update advances this isolated fixture to both hex shapes.
            for alphabetic in (False, True):
                for _ in range(4096):
                    workspace = drafts.get_workspace(owner)
                    item = next(row for row in workspace['items'] if row['record_key'] == key)
                    token = item['content_token']
                    if any(c in 'abcdef' for c in token.lower()) == alphabetic:
                        break
                    sql(connection, 'UPDATE c SET summary=c.summary FROM dbo.career_chapters c '
                        'JOIN dbo.entry_policy_records p ON p.canonical_key=c.chapter_key '
                        'AND p.owner_profile_id=c.owner_profile_id WHERE p.entry_key=?', (key,))
                else:
                    raise AssertionError('Could not obtain required canonical rowversion shape')
                check(len(token) == 16, 'canonical token is not raw hexadecimal rowversion')
                # Prove the actual SQL JSON producer emits those same eight bytes
                # as strict hex for both digit-only and alphabetic rowversions.
                snapshot = json.loads(db.first_row('usp_GetMemberVisitorAiPreviewForOwner',
                    [('@UserKey', owner)])['snapshot_json'])
                profile_bytes = sql(connection, 'SELECT p.row_version AS token FROM dbo.member_profiles p '
                    'JOIN dbo.app_users u ON u.id=p.user_id WHERE u.user_key=?', (owner,))[0][0]['token']
                profile_revision = snapshot['profile_revision']
                check(type(profile_revision) is str and re.fullmatch(r'[0-9a-fA-F]{16}', profile_revision)
                      and bytes.fromhex(profile_revision) == bytes(profile_bytes),
                      'snapshot profile revision does not encode current database bytes as strict hex')
                revisions = [row['canonical_revision'] for row in snapshot['entries']
                             if row['entry_key'] == key]
                check(len(revisions) == 1 and type(revisions[0]) is str
                      and re.fullmatch(r'[0-9a-fA-F]{16}', revisions[0]) is not None
                      and bytes.fromhex(revisions[0]) == bytes.fromhex(token),
                      'snapshot canonical revision does not encode the current eight bytes as strict hex')
                command = dict(type='save_item', request_id=str(uuid4()), record_key=key,
                    record_type=item['record_type'], expected_draft_version=workspace['draft_version'],
                    expected_content_token=token, expected_access_revision=item['access_revision'],
                    values={'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Rowversion proof.'})
                drafts.commit(owner, command)
                check(bool(drafts.repository.load_owner(owner)['items']), 'valid canonical token did not save')
                drafts.commit(owner, dict(type='discard_item', request_id=str(uuid4()), record_key=key))
                sql(connection, 'UPDATE c SET summary=c.summary FROM dbo.career_chapters c '
                    'JOIN dbo.entry_policy_records p ON p.canonical_key=c.chapter_key '
                    'AND p.owner_profile_id=c.owner_profile_id WHERE p.entry_key=?', (key,))
                command.update(request_id=str(uuid4()), expected_draft_version=drafts.get_workspace(owner)['draft_version'])
                # Deliberately bypass the Python precheck; SQL must reject either stale shape.
                denied_unchanged(lambda: commit_draft_sql(drafts, owner, command),
                    'RESUME_DRAFT_CHANGED')
        case('canonical_rowversion_digit_hex_and_stale_sql_fence', rowversion_tokens)

        case('changed_payload_same_key_denied', lambda: denied_unchanged(
            lambda: service.commit(owner, dict(saved_commands['first'], slug='different')), 'request_conflict'))

        def stale():
            edit_draft(key, {'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Old draft proposal.'})
            row = policy.get_entry(owner, key)['entry']
            policy.commit(owner, dict(type='edit', request_id=str(uuid4()), entry_key=key,
                expected_content_version=row['content_version'], expected_access_revision=row['access_revision'],
                values={'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Newer canonical correction.'}))
            denied_unchanged(lambda: publish(), 'stale_draft')
            check(catalog.get_item(owner, key)['values']['summary'] == 'Newer canonical correction.', 'new truth overwritten')
            drafts.commit(owner, dict(type='discard_item', request_id=str(uuid4()), record_key=key))
        case('newer_canonical_refuses_stale_draft', stale)

        ai = SqlMemberVisitorAiRepository(db, identity=SimpleNamespace(current_owner_key=lambda: owner), draft_service=drafts)
        def permissions():
            for display in (False, True):
                for use_ai in (False, True):
                    publish([dict(entry_key=key, resume_display=display, visitor_ai=use_ai)])
                    public = service.guest_read(slug='g-proof-member')
                    check((key in public['display']) == display, 'display choice lost')
                    check(len(ai.load_guest('g-proof-member').sources) == int(use_ai), 'AI permission conflated')
        case('independent_display_ai_choices', permissions)

        def private_preview():
            service.commit(owner, dict(type='sharing_off', request_id=str(uuid4())))
            edit_draft(key, {'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Private preview wording.'})
            before = publications.load_owner(owner)
            revision = drafts.get_workspace(owner)['draft_version']
            with observe_preview_failure(diagnostics):
                preview = ai.prepare_preview(expected_draft_revision=revision, choices=((key, True),))
                check('Private preview wording.' in ai.load_preview(preview).sources[0].content, 'candidate absent')
            check(publications.load_owner(owner) == before, 'preview published')
            drafts.commit(owner, dict(type='discard_item', request_id=str(uuid4()), record_key=key))
        case('private_candidate_preview_no_publication', private_preview)

        def rollback_on_failure():
            edit_draft(key, {'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Must roll back together.'})
            before_item = catalog.get_item(owner, key)
            before_draft = drafts.repository.load_owner(owner)
            before_counts = sql(connection, 'SELECT (SELECT COUNT(*) FROM dbo.resume_publication_receipts) receipts, '
                '(SELECT COUNT(*) FROM dbo.resume_publication_revisions) revisions, '
                '(SELECT COUNT(*) FROM dbo.resume_publication_outbox) outbox')[0]
            sql(connection, "CREATE TRIGGER dbo.g_proof_fail_publication ON dbo.resume_publication_revisions AFTER INSERT AS THROW 54999, 'Synthetic proof storage failure.', 1;")
            try:
                denied_unchanged(lambda: publish(), 'Synthetic proof storage failure.')
            finally:
                sql(connection, 'DROP TRIGGER dbo.g_proof_fail_publication')
            check(catalog.get_item(owner, key) == before_item, 'failed commit changed canonical row')
            check(drafts.repository.load_owner(owner) == before_draft, 'failed commit changed draft')
            check(sql(connection, 'SELECT (SELECT COUNT(*) FROM dbo.resume_publication_receipts) receipts, '
                '(SELECT COUNT(*) FROM dbo.resume_publication_revisions) revisions, '
                '(SELECT COUNT(*) FROM dbo.resume_publication_outbox) outbox')[0] == before_counts, 'failed commit left receipt or job')
            drafts.commit(owner, dict(type='discard_item', request_id=str(uuid4()), record_key=key))
        case('injected_commit_failure_rolls_back_canonical_draft_receipt', rollback_on_failure)

        story = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
        def personal():
            drafts.commit(owner, dict(type='create_private_item', request_id=str(uuid4()), record_key=story,
                record_type='knowledge', values={'title': 'Personal introduction', 'wording': 'Original personal wording.',
                'classification': 'personal'}))
            workspace = drafts.get_workspace(owner)
            item = next(row for row in workspace['items'] if row['record_key'] == story)
            check(workspace['story_entry_key'] is None, 'creation silently bound Story')
            drafts.commit(owner, dict(type='bind_story', request_id=str(uuid4()), record_key=story,
                expected_draft_version=workspace['draft_version'], expected_content_token=item['content_token'],
                expected_access_revision=item['access_revision']))
            reviewed = service.review_for_owner(owner, {'entries': [
                dict(entry_key=key, resume_display=True, visitor_ai=True),
                dict(entry_key=story, resume_display=True, visitor_ai=False)]}).reviewed
            check(reviewed is not None and reviewed.candidate.story_entry_key == story,
                  'Story identity did not retain its canonical UUID')
            for invalid_story in (None, '', 'not-a-uuid', story + 'x', story + ('x' * 4000),
                                  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'):
                candidate = service.publish_candidate(reviewed)
                candidate['story_entry_key'] = invalid_story
                command = dict(type='publish', request_id=str(uuid4()), slug='g-proof-member',
                    profile_identity=reviewed.candidate.profile_identity.to_payload()
                        if reviewed.candidate.profile_identity else None,
                    reviewed_digest=reviewed.digest, candidate=candidate)
                denied_unchanged(lambda: publications.commit_command(owner, command['request_id'], command),
                                 'The selected personal entry changed.')
            publish([dict(entry_key=key, resume_display=True, visitor_ai=True),
                     dict(entry_key=story, resume_display=True, visitor_ai=False)])
            persisted = sql(connection, 'SELECT r.owner_profile_id,r.publication_revision,r.display_json,r.visitor_ai_json,r.evidence_json, '
                'k.row_version AS personal_token FROM dbo.resume_sharing_state s '
                'JOIN dbo.resume_publication_revisions r ON r.owner_profile_id=s.owner_profile_id '
                'AND r.publication_revision=s.current_revision '
                'JOIN dbo.knowledge_items k ON k.owner_profile_id=s.owner_profile_id '
                'WHERE s.public_slug=? AND k.knowledge_item_key=?', ('g-proof-member', story))[0][0]
            # json.loads proves the actual persisted serialization, not a fixture reconstruction.
            display = json.loads(persisted['display_json'])
            story_members = [member for entry_key, member in display.items() if entry_key.lower() == story]
            check(len(story_members) == 1, 'persisted Story identity is missing or duplicated')
            check(set(display) == {key, story}, 'display map does not preserve canonical entry UUID keys')
            check(set(json.loads(persisted['visitor_ai_json'])) == {key},
                  'visitor AI map changed canonical keys or included the excluded Story')
            check(set(json.loads(persisted['evidence_json'])) == {key, story},
                  'evidence map does not preserve canonical entry UUID keys')
            snapshot = json.loads(db.first_row('usp_GetMemberVisitorAiPreviewForOwner',
                [('@UserKey', owner)])['snapshot_json'])
            personal_rows = [row for row in snapshot['entries'] if row['entry_key'] == story]
            check(len(personal_rows) == 1, 'snapshot does not preserve canonical Story UUID identity')
            check(personal_rows[0]['evidence_version_key'].startswith('candidate:' + story + ':'),
                  'new candidate evidence ID does not preserve canonical Story UUID identity')
            revision = story_members[0]['canonical_revision']
            check(type(revision) is str and re.fullmatch(r'[0-9a-fA-F]{16}', revision)
                  and bytes.fromhex(revision) == bytes(persisted['personal_token']),
                  'persisted personal revision does not encode current database bytes as strict hex')
            public = service.guest_read(slug='g-proof-member')
            check(public['display'][story]['presentation_section'] == 'story', 'explicit Story binding missing')
            # Exercise the guest SQL fence against missing/null, malformed and stale
            # stored values; restore the exact original manifest after every attempt.
            for invalid_revision in ('missing', None, '', 'g' * 16, revision[:-1], revision + '0',
                                     '0000000000000000'):
                malformed = copy.deepcopy(display)
                member = next(value for entry_key, value in malformed.items() if entry_key.lower() == story)
                if invalid_revision == 'missing':
                    member.pop('canonical_revision')
                else:
                    member['canonical_revision'] = invalid_revision
                try:
                    sql(connection, 'UPDATE dbo.resume_publication_revisions SET display_json=? '
                        'WHERE owner_profile_id=? AND publication_revision=?',
                        (json.dumps(malformed), persisted['owner_profile_id'], persisted['publication_revision']))
                    denied_unchanged(lambda: service.guest_read(slug='g-proof-member'),
                                     'Publication is unavailable.')
                finally:
                    sql(connection, 'UPDATE dbo.resume_publication_revisions SET display_json=? '
                        'WHERE owner_profile_id=? AND publication_revision=?',
                        (persisted['display_json'], persisted['owner_profile_id'], persisted['publication_revision']))
            check(service.guest_read(slug='g-proof-member')['display'] == public['display'],
                  'restored exact personal manifest did not recover the guest read')
            check(all('Original personal wording.' not in source.content for source in ai.load_guest('g-proof-member').sources),
                  'Story AI exclusion lost')
        case('personal_entry_create_bind_publish', personal)

        def correction():
            row = policy.get_entry(owner, story)['entry']
            policy.commit(owner, dict(type='edit', request_id=str(uuid4()), entry_key=story,
                expected_content_version=row['content_version'], expected_access_revision=row['access_revision'],
                values={'title': 'Personal introduction', 'wording': 'Corrected personal wording.', 'classification': 'personal'}))
            item = KnowledgeService(db).get_knowledge_item_for_owner(owner, story)
            check(item['original_member_wording'] == 'Original personal wording.', 'original source changed')
            check('Corrected personal wording.' in json.dumps(service.guest_read(slug='g-proof-member')['display']), 'correction absent')
        case('personal_correction_preserves_original', correction)

        def foreign():
            item = catalog.get_item(owner, story)
            denied_unchanged(lambda: drafts.commit(other, dict(type='bind_story', request_id=str(uuid4()), record_key=story,
                expected_draft_version=drafts.get_workspace(other)['draft_version'],
                expected_content_token=item['content_token'], expected_access_revision=item['access_revision'])), 'not_found')
            check(drafts.get_workspace(other)['story_entry_key'] is None, 'foreign owner acquired Story')
        case('foreign_owner_cannot_bind_personal_entry', foreign)

        def withdrawn():
            reference = binding.select_for_owner(owner)
            context = core.owner_context(actor_key=owner, subject_owner_key=owner, slug='g-proof-member', purpose='edit')
            core.withdraw_publication(context, expected_public_revision=reference.revision_key,
                                     idempotency_key=str(uuid4()), confirmed=True)
            check(service.guest_read(slug='g-proof-member')['public_identity'] is None, 'withdrawn identity disclosed')
        case('withdrawn_identity_suppressed', withdrawn)

        def forged():
            reviewed = service.review_for_owner(owner).reviewed
            command = dict(type='publish', request_id=str(uuid4()), slug='g-proof-member', profile_identity=None,
                reviewed_digest=reviewed.digest, candidate=service.publish_candidate(reviewed))
            tampered = copy.deepcopy(command)
            tampered['candidate']['entries'][0]['canonical_token'] = '0000000000000000'
            # Direct SQL port deliberately bypasses Python review to exercise
            # the transaction's own raw-source fence and rollback.
            denied_unchanged(lambda: publications.commit_command(owner, tampered['request_id'], tampered), 'Canonical information changed.')
            # Retain the later PUBLICATION wrapper's direct-SQL guard even
            # though the normal draft service never emits this legacy payload.
            denied_unchanged(lambda: drafts.repository.commit_command(owner, str(uuid4()),
                dict(type='publish', request_digest='f' * 64)), 'PUBLICATION_COMMAND_REQUIRED')
        case('forged_canonical_token_refused_atomically', forged)

        def media_publish():
            from services.resume_media_application import SqlResumeMediaDraftStore, build_resume_media_application
            from services.resume_media_catalog_repository import SqlResumeCatalogRepository
            proof.seed_proof_catalog_asset(connection)
            sql(connection, 'UPDATE dbo.resume_catalog_assets SET width=1200,height=800 WHERE asset_id=?', (proof.PROOF_CATALOG_ASSET_ID,))
            catalog_authority = SqlResumeCatalogRepository(db)
            sources = SimpleNamespace(get_catalog_asset=lambda asset_id, version: catalog_authority.get_active(asset_id, version))
            media_store = SqlResumeMediaDraftStore(db)
            media = build_resume_media_application(draft_store=media_store, sources=sources,
                persistence_label='isolated_SQL_proof', catalog_label='synthetic_SQL_catalog')
            service.media_application = media
            service.catalog = catalog_authority
            version = drafts.get_workspace(owner)['draft_version']
            crop = dict(x=0, y=0, width=1, height=1)
            payload = dict(request_id=str(uuid4()), expected_draft_version=version,
                choices=[dict(slot='experience_support', source=dict(kind='generated_illustration',
                    asset_id=proof.PROOF_CATALOG_ASSET_ID, asset_version=1), crop=crop, alt_text='', decorative=True, caption=None)])
            with patch.object(db, 'execute_procedure', wraps=db.execute_procedure) as observed:
                accepted = media.add_media(owner_id=owner, payload=payload)
            sent = [dict(call.args[1]) for call in observed.call_args_list
                    if call.args[0] == 'usp_CommitResumeMediaCommandForOwner']
            check(len(sent) == 1, 'valid media save was not one SQL command')
            actual = json.loads(sent[0]['@CommandJson'])
            receipt = sql(connection, 'SELECT catalog_source_bound,outcome_json FROM dbo.resume_media_command_receipts WHERE request_uuid=?',
                          (payload['request_id'],))[0][0]
            check(bool(receipt['catalog_source_bound']), 'accepted catalog history not retained')
            check(json.loads(receipt['outcome_json']) == accepted, 'catalog provenance altered replay outcome')
            before = whole_state()
            check(media.add_media(owner_id=owner, payload=payload) == accepted, 'media replay changed outcome')
            check(whole_state() == before, 'media replay mutated durable state')

            def direct(payload_command, subject=owner):
                media_store.save_owner(subject, {'_pending_command': dict(
                    request_id=payload_command['receipt']['request_uuid'], command_json=json.dumps(payload_command))})

            def fresh():
                command = copy.deepcopy(actual)
                current = drafts.get_workspace(owner)['draft_version']
                command.update(expected_draft_version=current, draft_version=current + 1)
                command['receipt'].update(request_uuid=str(uuid4()), semantic_digest='e' * 64)
                command['receipt']['outcome']['draft_version'] = current + 1
                return command

            # These go straight to the SQL store: Python source prevalidation
            # cannot supply the authoritative durable fence under test.
            for field, value in [('asset_id', str(uuid4())), ('asset_id', proof.PROOF_CATALOG_ASSET_ID + 'x'),
                                 ('asset_version', 2), ('asset_digest', 'd' * 64)]:
                bad = fresh()
                bad['placements'][0][field] = value
                denied_unchanged(lambda: direct(bad), 'source-changed')
            sql(connection, "UPDATE dbo.resume_catalog_assets SET lifecycle=N'withdrawn',withdrawn_at_utc=SYSUTCDATETIME() WHERE asset_id=?", (proof.PROOF_CATALOG_ASSET_ID,))
            denied_unchanged(lambda: direct(fresh()), 'source-changed')
            sql(connection, "UPDATE dbo.resume_catalog_assets SET lifecycle=N'active',withdrawn_at_utc=NULL WHERE asset_id=?", (proof.PROOF_CATALOG_ASSET_ID,))
            denied_unchanged(lambda: proof.apply_sql_file(connection, rollback), 'Rollback refused: catalog media placements exist.')
            media.add_media(owner_id=owner, payload=dict(request_id=str(uuid4()),
                expected_draft_version=drafts.get_workspace(owner)['draft_version'],
                choices=[dict(slot='experience_support', source=None)]))
            check(sql(connection, "SELECT COUNT(*) AS n FROM dbo.resume_media_placements WHERE source_kind=N'generated_illustration'")[0][0]['n'] == 0,
                  'removed media placement remains')
            denied_unchanged(lambda: proof.apply_sql_file(connection, rollback), 'Rollback refused: catalog media command history exists.')
            payload.update(request_id=str(uuid4()), expected_draft_version=drafts.get_workspace(owner)['draft_version'])
            with patch.object(db, 'execute_procedure', wraps=db.execute_procedure) as observed:
                media.add_media(owner_id=owner, payload=payload)
            saved_commands['media_sql'] = next(dict(call.args[1]) for call in observed.call_args_list
                                               if call.args[0] == 'usp_CommitResumeMediaCommandForOwner')
            edit_draft(key, {'role_title': 'Lead', 'employer_name': 'PeerSlate', 'summary': 'Text and selected illustration together.'})
            publish()
            public = service.guest_read(slug='g-proof-member')
            check(public['media']['experience_support']['crop'] == crop, 'crop changed during atomic publish')
            check('Text and selected illustration together.' in json.dumps(public['display']), 'media publish lost text delta')
            guarded = fresh()
            guarded.update(command='keep_words_only', slot='experience_support')
            guarded['receipt']['command_type'] = 'keep_words_only'
            guarded['receipt']['outcome']['command'] = 'keep_words_only'
            denied_unchanged(lambda: direct(guarded), 'PUBLICATION_MEDIA_RESTRICT_REQUIRED')
            reviewed = service.review_for_owner(owner).reviewed
            command = dict(type='publish', request_id=str(uuid4()), slug='g-proof-member', profile_identity=None,
                reviewed_digest=reviewed.digest, candidate=service.publish_candidate(reviewed))
            sql(connection, "UPDATE dbo.resume_catalog_assets SET lifecycle=N'withdrawn',withdrawn_at_utc=SYSUTCDATETIME() WHERE asset_id=?", (proof.PROOF_CATALOG_ASSET_ID,))
            # Bypass Python re-review to prove the transaction's late source fence.
            denied_unchanged(lambda: publications.commit_command(owner, command['request_id'], command),
                'Selected media is no longer available.')
        case('media_crop_atomic_publish_and_late_source_refusal', media_publish)

        def principal():
            from scripts.configure_mvp1_acceptance_sql_authority import plan
            privileges = plan()
            sql(connection, "IF DATABASE_PRINCIPAL_ID('peerslate_app') IS NULL CREATE USER peerslate_app WITHOUT LOGIN;")
            for procedure in privileges['grant_execute']:
                sql(connection, 'GRANT EXECUTE ON dbo.' + procedure + ' TO peerslate_app')
            for procedure in privileges['deny_execute']:
                sql(connection, 'DENY EXECUTE ON dbo.' + procedure + ' TO peerslate_app')
            def allowed():
                check(bool(db.first_row('usp_GetResumePublicationForOwner', [('@UserKey', owner)])), 'public wrapper denied')
                db.execute_procedure('usp_GetResumeDraftForOwner', [('@UserKey', owner)])
                db.execute_procedure('usp_GetResumeMediaDraftForOwner', [('@UserKey', owner)])
                replay = db.first_row('usp_CommitResumeMediaCommandForOwner', list(saved_commands['media_sql'].items()))
                check(bool(replay['replayed']), 'application principal media replay denied')
            proof._effective_principal(connection, 'peerslate_app', allowed)
            def denied_internal():
                try:
                    proof.execute_procedure(connection, 'usp_MemberVisitorAiSnapshotInternal', [('@UserKey', owner), ('@OwnerPreview', True)])
                except Exception as error:
                    check('permission' in str(error).lower() or '229' in str(error), 'wrong internal denial')
                else:
                    raise AssertionError('internal helper executable')
            proof._effective_principal(connection, 'peerslate_app', denied_internal)
        case('application_principal_boundary', principal)
        def rollback_refused():
            denied_unchanged(lambda: proof.apply_sql_file(connection, rollback), 'Rollback refused:')
            check(sql(connection, "SELECT COUNT(*) AS n FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-IDENTITY-001'")[0][0]['n'] == 1,
                  'refused rollback removed migration')
        case('integrated_history_rollback_refused', rollback_refused)
        check(cases == {name: 'pass' for name in ENGINE_CASES}, 'incomplete G engine oracle set')
    finally:
        connection.close()
