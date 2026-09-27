import json
import copy
import unittest
from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
from services.member_visitor_ai_sources import SourcesUnavailable
from services.resume_publication_contracts import ReadState
from tests.test_member_visitor_ai_sources import snapshot


class SnapshotDatabase:
    """Protocol fixture, never claimed as engine evidence. No global patches."""
    def __init__(self, document):
        self.document=document; self.calls=[]; self.fail=False
    def first_row(self, procedure, params):
        self.calls.append((procedure,params))
        if self.fail: raise RuntimeError('database unavailable')
        return {'snapshot_json':json.dumps(self.document)}


class Identity:
    owner='member-a'
    def current_owner_key(self): return self.owner


class RepositoryTests(unittest.TestCase):
    def test_draft_preview_rejects_stale_bases_and_changes_between_reads(self):
        from types import SimpleNamespace
        document = snapshot(preview=True)
        item = dict(record_key='entry-a', record_type='role', content_token='0000000000000011',
                    access_revision=4, has_draft=True, orphaned=False, draft_is_stale=False,
                    draft_base_content_token='0000000000000011', draft_base_access_revision=4,
                    proposed_values={'role_title': 'Proposed title', 'summary': 'Private saved proposal'})
        workspace = dict(draft_version=2, capabilities={'canonical_read': 'ok'}, items=[item])
        db = SnapshotDatabase(document)
        draft = SimpleNamespace(get_workspace=lambda owner: copy.deepcopy(workspace))
        repo = SqlMemberVisitorAiRepository(db, identity=Identity(), draft_service=draft)
        binding = repo.prepare_preview(expected_draft_revision=2, choices=(('entry-a', True),))
        bundle = repo.load_preview(binding)
        self.assertIn('Private saved proposal', bundle.sources[0].content)
        self.assertEqual(db.document, document)
        for field, value in [('draft_base_content_token', 'old'), ('access_revision', 99),
                             ('orphaned', True), ('draft_is_stale', True), ('record_type', 'skill')]:
            old = item[field]
            item[field] = value
            with self.subTest(field=field), self.assertRaises(SourcesUnavailable):
                repo.load_preview(binding)
            item[field] = old
        def change_during_read(owner):
            db.document['sharing_epoch'] += 1
            return copy.deepcopy(workspace)
        draft.get_workspace = change_during_read
        with self.assertRaises(SourcesUnavailable):
            repo.prepare_preview(expected_draft_revision=2, choices=(('entry-a', True),))

    def test_private_draft_rowversion_compares_exact_bytes_across_sql_hex_case(self):
        from types import SimpleNamespace
        from services.living_resume_editor_service import _version
        for raw in (bytes.fromhex('0000000000000011'), bytes.fromhex('00000000000000af')):
            with self.subTest(raw=raw.hex()):
                document = snapshot(preview=True)
                document['entries'][0]['canonical_revision'] = raw.hex().upper()
                token = _version(raw)
                item = dict(record_key='entry-a', record_type='role', content_token=token,
                            access_revision=4, has_draft=True, orphaned=False, draft_is_stale=False,
                            draft_base_content_token=token, draft_base_access_revision=4,
                            proposed_values={'role_title': 'Private title', 'summary': 'Private saved proposal'})
                workspace = dict(draft_version=2, capabilities={'canonical_read': 'ok'}, items=[item])
                db = SnapshotDatabase(document)
                repo = SqlMemberVisitorAiRepository(db, identity=Identity(),
                    draft_service=SimpleNamespace(get_workspace=lambda owner: copy.deepcopy(workspace)))
                before = copy.deepcopy(document)
                binding = repo.prepare_preview(expected_draft_revision=2, choices=(('entry-a', True),))
                bundle = repo.load_preview(binding)
                self.assertIn('Private saved proposal', bundle.sources[0].content)
                self.assertEqual(repo.recheck(bundle), ReadState.CURRENT)
                self.assertEqual(db.document, before)
                for field in ('content_token', 'draft_base_content_token'):
                    for invalid in ('00000000000000b0', '11', '0x' + token,
                                    token + ' ', '00000000000000gg', None, 17):
                        with self.subTest(field=field, invalid=invalid):
                            item[field] = invalid
                            with self.assertRaises(SourcesUnavailable):
                                repo.prepare_preview(expected_draft_revision=2, choices=(('entry-a', True),))
                            self.assertEqual(repo.recheck(bundle), ReadState.UNAVAILABLE)
                        item[field] = token
                document['entries'][0]['canonical_revision'] = '00000000000000b0'
                self.assertEqual(repo.recheck(bundle), ReadState.UNAVAILABLE)
                self.assertEqual(item['content_token'], token)
                self.assertEqual(item['draft_base_content_token'], token)

    def test_real_adapter_parameter_binding_and_live_reread(self):
        db=SnapshotDatabase(snapshot()); repo=SqlMemberVisitorAiRepository(db)
        bundle=repo.load_guest('safe-slug')
        self.assertEqual(db.calls,[('usp_GetMemberVisitorAiBySlug',[('@ProfileSlug','safe-slug')])])
        self.assertEqual(repo.recheck(bundle),ReadState.CURRENT)
        self.assertEqual(len(db.calls),2)
        db.document['sharing_epoch']+=1
        self.assertEqual(repo.recheck(bundle),ReadState.STALE)
        db.fail=True
        self.assertEqual(repo.recheck(bundle),ReadState.UNAVAILABLE)

    def test_preview_uses_current_server_identity_on_every_read(self):
        db=SnapshotDatabase(snapshot(preview=True)); identity=Identity()
        repo=SqlMemberVisitorAiRepository(db,identity=identity)
        binding=repo.prepare_preview(expected_draft_revision=2,choices=(('entry-a',True),))
        bundle=repo.load_preview(binding)
        self.assertEqual(repo.recheck(bundle),ReadState.CURRENT)
        self.assertTrue(all(params==[('@UserKey','member-a')] for _,params in db.calls))
        identity.owner='member-b'
        with self.assertRaises(SourcesUnavailable): repo.load_preview(binding)
        with self.assertRaises(SourcesUnavailable): repo.load_preview({'owner':'member-a'})

    def test_malformed_or_unavailable_database_never_falls_back(self):
        for row in (None,{}, {'snapshot_json':'{}'}, {'snapshot_json':'{"subject_key":"a","subject_key":"b"}'}):
            class BadDatabase:
                def first_row(self,*args): return row
            with self.subTest(row=row),self.assertRaises(SourcesUnavailable):
                SqlMemberVisitorAiRepository(BadDatabase()).load_guest('a')
