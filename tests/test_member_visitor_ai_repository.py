import json
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
