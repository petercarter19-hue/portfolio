"""Contract tests for the MVP1 C composer intake service.

Everything here runs against real service code with injected in-memory
stores. The in-memory store is labelled test-only; nothing here is SQL engine
proof, provider proof or live-identity proof.
"""

from __future__ import annotations

import io
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_intake_document_adapter import DocumentParseResult, ResumeDocumentAdapter
from services.resume_intake_jobs import JobFence, fence_is_current, lease, enqueue
from services.resume_intake_policy import (
    fixture_policy_for_tests,
    selected_policy_for_tests,
)
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import (
    ResumeIntakeConflictError,
    ResumeIntakeNotFoundError,
    ResumeIntakePolicyError,
    ResumeIntakeService,
    ResumeIntakeUnavailableError,
    ResumeIntakeValidationError,
)
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter


ROLE_VALUES = {
    "role_title": "Systems Engineer",
    "employer_name": "Northrop Grumman",
    "location_text": None,
    "summary": "Supports requirements management and cross-functional systems engineering.",
    "start_date": "2025-01-01",
    "end_date": None,
    "date_precision": "month",
    "employment_type": "full_time",
    "current_role": True,
}


def skill(name, summary=None):
    return {"name": name, "summary": summary}


class FakeUpload:
    def __init__(self, mimetype, data, filename="file.bin"):
        self.mimetype = mimetype
        self.stream = io.BytesIO(data)
        self.filename = filename


class RecordingTranscriber:
    """Deterministic provider stub that records the exact bytes it received."""

    def __init__(self, transcript="I led the migration.", fail=None):
        self.transcript = transcript
        self.fail = fail
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"bytes": audio_bytes, "content_type": content_type, "locale": locale})
        if self.fail:
            from services.speech_transcription_service import SpeechTranscriptionError

            raise SpeechTranscriptionError(self.fail)
        return {
            "provider_transcript": self.transcript,
            "provider_request_id": "stub-request-1",
            "duration_seconds": 3.0,
        }


def wav_bytes(payload=b"\x00" * 64):
    return b"RIFF" + (len(payload) + 36).to_bytes(4, "little") + b"WAVE" + payload


def build_service(*, policy=None, document_pipeline=None, transcriber=None, interpreter=None):
    catalog = InMemoryCanonicalCatalog()
    draft_repository = InMemoryResumeDraftRepository()
    draft_service = ResumeDraftService(repository=draft_repository, catalog=catalog)
    repository = InMemoryResumeIntakeRepository()
    adapter = None
    if transcriber is not None:
        adapter = ResumeTranscriptionAdapter(service=transcriber)
    service = ResumeIntakeService(
        repository=repository,
        draft_service=draft_service,
        document_adapter=ResumeDocumentAdapter(),
        transcription_adapter=adapter,
        policy=policy or selected_policy_for_tests(),
        interpreter=interpreter,
        document_pipeline=document_pipeline,
    )
    return service, catalog, draft_service


class GuideReferenceCommandTests(unittest.TestCase):
    def test_malformed_reference_metadata_is_unavailable_instead_of_an_empty_reference_view(self):
        self.setup_shared()
        snapshot = self.shared.draft.repository.load_owner(self.owner)
        snapshot['highlight_refs'] = None
        self.shared.draft.repository.save_owner(self.owner,snapshot)
        result = self.service.guide_reference_view(self.owner,self.service.working_set(self.owner))
        self.assertEqual(result['read_state'],'unavailable')
        self.assertIsNone(result['highlight_tiles'])
        self.assertIsNone(self.shared.draft.repository.load_owner(self.owner)['highlight_refs'])

    def test_unqualified_sql_keeps_reference_input_and_never_calls_the_database(self):
        from unittest.mock import Mock
        from services.resume_intake_repository import SqlResumeIntakeRepository
        database = Mock()
        service = ResumeIntakeService(repository=SqlResumeIntakeRepository(database),policy=selected_policy_for_tests())
        payload = {'request_id':str(uuid4()),'kind':'skill','item_ref':str(uuid4()),'references':[str(uuid4())],
            'expected_working_set_token':'a'*64}
        with self.assertRaises(ResumeIntakeUnavailableError) as refused:
            service.set_guide_references('fictional-sql-owner',payload)
        self.assertEqual(refused.exception.proposed['references'],payload['references'])
        self.assertEqual(database.mock_calls,[])

    def test_reference_choices_resolve_retained_item_aliases_to_actual_saved_record_keys(self):
        self.setup_shared()
        submitted = self.service.submit(self.owner,{'request_id':str(uuid4()),'text':'A separate fictional skill.'})
        proposal = submitted['proposals'][0]
        alias = self.service.working_set(self.owner)['unplaced'][0]['item_ref']
        saved = self.service.decide(self.owner,{'request_id':str(uuid4()),'proposal_key':proposal['proposal_key'],
            'decision':'accept','confirmed_values':{'record_type':'skill','name':'A separate fictional skill'}})
        key = saved['item']['record_key']
        self.assertIn(alias,self.service.working_item(self.owner,key)['identity_aliases'])
        result = self.service.set_guide_references(self.owner,self.command('skill',[self.bullet],alias))
        self.assertEqual(result['item_ref'],key)
        item = next(row for row in self.shared.draft.get_workspace(self.owner)['items'] if row['record_key']==key)
        self.assertEqual(item['evidence_refs'],[self.bullet])

    def test_hard_delete_prunes_private_links_in_the_same_commit_and_failure_restores_all_three_stores(self):
        import copy
        from unittest.mock import patch
        from services.resume_publication_repository import PublicationStoreUnavailable
        from services.resume_publication_service import PublicationUnavailableError
        self.setup_shared()
        self.service.set_guide_references(self.owner,self.command('skill',[self.bullet],self.skill))
        self.service.set_guide_references(self.owner,self.command('highlights',[self.bullet]))
        before = (copy.deepcopy(self.shared.policy.repository._owners),copy.deepcopy(self.shared.draft.repository._owners),
            copy.deepcopy(self.shared.publication.repository._owners))
        role = next(row for row in self.shared.policy.read_entries(self.owner)['entries'] if row['entry_key']==self.role)
        command = {'type':'delete','request_id':str(uuid4()),'entry_key':self.role,'dependent_keys':[self.bullet],
            'expected_content_version':role['content_version'],'expected_access_revision':role['access_revision']}
        with patch.object(self.shared.publication.repository,'save_owner',side_effect=PublicationStoreUnavailable('injected linked failure')):
            with self.assertRaises(PublicationUnavailableError):
                self.shared.policy.commit(self.owner,command)
        self.assertEqual((self.shared.policy.repository._owners,self.shared.draft.repository._owners,
            self.shared.publication.repository._owners),before)
        version = self.shared.draft.get_workspace(self.owner)['draft_version']
        self.shared.policy.commit(self.owner,command)
        workspace = self.shared.draft.get_workspace(self.owner)
        skill = next(row for row in workspace['items'] if row['record_key']==self.skill)
        self.assertEqual(skill['evidence_refs'],[])
        self.assertEqual(workspace['highlight_refs'],[])
        self.assertEqual(workspace['draft_version'],version+1)
        self.shared.policy.commit(self.owner,command)
        self.assertEqual(self.shared.draft.get_workspace(self.owner)['draft_version'],version+1)

    def setup_shared(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        self.shared,self.owner = SharedMvp1Fixture(),'guide-reference-command-fictional'
        # B3c m1: the draft reads Looking Ahead restore claims only through this injected port.
        self.shared.draft.placement_claims = self.shared.policy
        self.service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),draft_service=self.shared.draft,
            policy=selected_policy_for_tests())
        def create(kind, values, parent=None):
            return self.shared.canonical.create_private(self.owner,{'command_id':str(uuid4()),'record_type':kind,
                'parent_key':parent,'values':values})['record_key']
        self.role = create('role',{'role_title':'Fictional Engineer','employer_name':'Fictional Orchard',
            'summary':'An exact fictional summary line.'})
        self.bullet = create('accomplishment',{'wording':'Reviewed 12 fictional records.','metric_value':'12',
            'metric_label':'fictional records'},self.role)
        self.skill = create('skill',{'name':'Fictional skill'})

    def command(self, kind, references, item=None):
        return {'request_id':str(uuid4()),'kind':kind,'item_ref':item,'references':references,
            'expected_working_set_token':self.service.working_set(self.owner)['working_set_token']}

    def test_reference_choices_are_atomic_replayed_and_preserved_by_later_manual_word_edits(self):
        import copy
        from unittest.mock import patch
        self.setup_shared()
        self.shared.seed_publication(self.owner,[(key,True,False) for key in (self.role,self.bullet,self.skill)])
        public = copy.deepcopy(self.shared.publication.owner_preview(self.owner)['current'])
        command = self.command('skill',[self.bullet],self.skill)
        with patch.object(self.shared.policy.repository,'save_owner',wraps=self.shared.policy.repository.save_owner) as save:
            first = self.service.set_guide_references(self.owner,command)
            self.assertTrue(self.service.set_guide_references(self.owner,command)['replayed'])
            save.assert_not_called()
        version = self.shared.draft.get_workspace(self.owner)['draft_version']
        workspace = self.shared.draft.get_workspace(self.owner)
        item = next(row for row in workspace['items'] if row['record_key']==self.skill)
        self.assertEqual(item['evidence_refs'],[self.bullet])
        self.assertTrue(item['evidence_refs_manual'])
        self.shared.draft.commit(self.owner,{'type':'save_item','request_id':str(uuid4()),'record_key':self.skill,
            'record_type':'skill','expected_draft_version':version,'expected_content_token':item['content_token'],
            'expected_access_revision':item['access_revision'],'values':{'summary':'A later manual explanation.'}})
        item = next(row for row in self.shared.draft.get_workspace(self.owner)['items'] if row['record_key']==self.skill)
        self.assertEqual(item['evidence_refs'],[self.bullet])
        self.service.set_guide_references(self.owner,self.command('highlights',[self.bullet]))
        self.assertEqual(self.shared.draft.get_workspace(self.owner)['highlight_refs'],[self.bullet])
        view = self.service.guide_reference_view(self.owner,self.service.working_set(self.owner))
        self.assertEqual(view['skill_evidence'][self.skill][0]['text'],'Reviewed 12 fictional records.')
        self.assertEqual(view['highlight_tiles'][0]['metric_value'],'12')
        # D6b carries references on the in-memory publisher; a SQL-backed one keeps them closed.
        from unittest.mock import Mock, patch as _patch
        with _patch.object(self.shared.publication,'sql_repository',Mock()):
            basis = self.shared.publication.read_publication_basis_for_owner(self.owner)
        self.assertEqual(basis['read_state'],'blocked')
        self.assertIn({'item_ref':self.skill,'reason':'publication_codec_skill_references'},basis['blocked_items'])
        self.assertIn({'item_ref':'resume','reason':'publication_codec_highlight_references'},basis['blocked_items'])
        self.assertEqual(self.shared.publication.owner_preview(self.owner)['current'],public)

    def test_reference_command_refuses_foreign_pending_hidden_wrong_type_and_stale_summary(self):
        from hashlib import sha256
        self.setup_shared()
        for ref in (str(uuid4()),self.skill,{'role_record_key':self.role,'line_digest':sha256(b'Old line.').hexdigest()}):
            with self.subTest(ref=ref):
                with self.assertRaises((ResumeIntakeNotFoundError,ResumeIntakeConflictError)):
                    self.service.set_guide_references(self.owner,self.command('skill',[ref],self.skill))
        stale = self.command('skill',[self.bullet],self.skill)
        current = self.service.working_item(self.owner,self.role)
        self.service.set_guide_visibility(self.owner,{'request_id':str(uuid4()),'item_ref':self.role,'hidden':True,
            'expected_working_set_token':self.service.working_set(self.owner)['working_set_token'],
            'expected_item_revision':current['saved_revision']})
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.set_guide_references(self.owner,stale)
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.service.set_guide_references(self.owner,self.command('skill',[self.bullet],self.skill))
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.service.set_guide_references('other-fictional-owner',self.command('skill',[self.bullet],self.skill))
        self.assertNotIn('evidence_refs',self.shared.draft.repository.load_owner(self.owner)['items'].get(self.skill,{}))

    def test_reference_receipt_failure_rolls_back_private_metadata_and_version(self):
        import copy
        from unittest.mock import patch
        self.setup_shared()
        before = copy.deepcopy(self.shared.draft.repository._owners)
        command = self.command('skill',[self.bullet],self.skill)
        with patch.object(self.service.repository,'save_owner',side_effect=RuntimeError('injected receipt failure')):
            with self.assertRaisesRegex(RuntimeError,'injected receipt failure'):
                self.service.set_guide_references(self.owner,command)
        self.assertEqual(self.shared.draft.repository._owners,before)
        self.assertNotIn(command['request_id'],self.service.repository.load_owner(self.owner)['receipts'])


class GuideTileTests(unittest.TestCase):
    """B3t: per-tile metric selection, resolution states and the Looking Ahead placement (plan edff4959)."""
    setup_shared = GuideReferenceCommandTests.setup_shared
    command = GuideReferenceCommandTests.command
    WORDING = 'Led 30+ fictional engineers on 9 redesigns worth $19.2M.'

    def setup_tiles(self):
        self.setup_shared()
        self.lead = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'accomplishment',
            'parent_key': self.role, 'values': {'wording': self.WORDING, 'metric_value': '30+',
                                                'metric_label': 'fictional engineers led'}})['record_key']

    def choose(self, refs):
        return self.service.set_guide_references(self.owner, self.command('highlights', refs))

    def stored(self):
        return self.shared.draft.get_workspace(self.owner).get('highlight_refs')

    def tiles(self):
        return self.service.guide_reference_view(self.owner, self.service.working_set(self.owner))['highlight_tiles']

    def edit_lead(self, wording):
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == self.lead)
        self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': self.lead,
            'record_type': 'accomplishment', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': {'wording': wording}})

    # GuideConversionTests helpers, reused for the B3b interplay case.
    def working(self):
        return self.service.working_set(self.owner)

    def item(self, ref):
        return self.service.working_item(self.owner, ref)

    def reviewed(self, staged):
        from services.resume_guide_turns import tile_key
        moved = staged['item_ref']
        return [{'kind': row['kind'], 'container_ref': row['container_ref'], 'before_digest': row['before_digest'],
                 'references': [] if row['container_ref'] == moved
                 else [ref for ref in row['references'] if tile_key(ref)[0] != moved]} for row in staged['affected_references']]

    def test_one_bullet_backs_two_tiles_with_a_server_set_fingerprint(self):
        self.setup_tiles()
        self.choose([self.lead, {'item_ref': self.lead, 'metric_index': 2, 'caption': 'in redesigns overseen'}])
        self.assertEqual(self.stored(), [self.lead, {'item_ref': self.lead, 'metric_index': 2, 'metric_text': '$19.2M',
                                                     'caption': 'in redesigns overseen'}])
        tiles = self.tiles()
        self.assertEqual([(t['metric_index'], t['value'], t['label'], t['state'], t['publish']) for t in tiles],
                         [(0, '30+', 'fictional engineers led', 'shown', 'as_today'),
                          (2, '$19.2M', 'in redesigns overseen', 'shown', 'after_update')])
        self.assertEqual({t['role_ref'] for t in tiles}, {self.role})
        draft_tiles = self.shared.draft.get_workspace(self.owner)['highlight_tiles']
        self.assertEqual([(t['item_ref'], t['metric_index'], t['value'], t['state'], t['publish']) for t in draft_tiles],
                         [(t['item_ref'], t['metric_index'], t['value'], t['state'], t['publish']) for t in tiles])

    def test_shapes_refuse_before_any_effect(self):
        self.setup_tiles()
        before = self.stored()
        refusals = [
            [{'item_ref': self.lead, 'metric_index': 2, 'metric_text': '$19.2M'}],
            [{'item_ref': self.lead, 'metric_index': 2, 'caption': 'x' * 81}],
            [{'item_ref': self.lead, 'metric_index': 2, 'caption': '   '}],
            [self.lead, {'item_ref': self.lead, 'metric_index': 0, 'caption': 'again'}],
            [self.lead, self.bullet, {'item_ref': self.lead, 'metric_index': 1}, {'item_ref': self.lead, 'metric_index': 2},
             {'item_ref': self.bullet, 'metric_index': 1}],
            [{'item_ref': self.lead, 'metric_index': -1}],
        ]
        for refs in refusals:
            with self.subTest(refs=refs), self.assertRaises(ResumeIntakeValidationError):
                self.choose(refs)
        with self.assertRaises(ResumeIntakeConflictError) as absent:
            self.choose([{'item_ref': self.lead, 'metric_index': 9}])
        self.assertEqual(absent.exception.error_code, 'changed')
        self.assertEqual(self.stored(), before)
        self.choose([{'item_ref': self.lead, 'metric_index': 0}])
        self.assertEqual(self.stored(), [self.lead], 'Index 0 without a caption is stored as the plain key')

    def test_a_changed_number_needs_review_and_a_missing_caption_is_asked_for(self):
        self.setup_tiles()
        self.choose([self.lead, {'item_ref': self.lead, 'metric_index': 2, 'caption': 'in redesigns overseen'},
                     {'item_ref': self.lead, 'metric_index': 1}])
        self.assertEqual([t['state'] for t in self.tiles()], ['shown', 'shown', 'needs_caption'])
        self.edit_lead('Led 30+ fictional engineers on 9 redesigns worth $21M.')
        states = [(t['metric_index'], t['state'], t['value']) for t in self.tiles()]
        self.assertEqual(states, [(0, 'shown', '30+'), (2, 'needs_review', None), (1, 'needs_caption', '9')],
                         'A drifted number never shows a different value')
        self.assertEqual(self.stored()[1]['metric_text'], '$19.2M', 'The fingerprint is never rewritten by a read')

    def test_publish_keeps_plain_tiles_and_drops_object_tiles_honestly(self):
        self.setup_tiles()
        self.shared.seed_publication(self.owner, [(key, True, True) for key in (self.role, self.bullet, self.lead, self.skill)])
        self.choose([self.lead, self.bullet])
        plain = self.shared.publication.read_publication_basis_for_owner(self.owner)
        self.choose([self.lead, self.bullet, {'item_ref': self.lead, 'metric_index': 2, 'caption': 'in redesigns overseen'}])
        mixed = self.shared.publication.read_publication_basis_for_owner(self.owner)
        # Lockstep with Lane D's D6c (coordination 61e201f): until D6c, an object tile drops as reference_invalid;
        # D6c names it highlight_tile_unpublishable. Either is honest; this narrows to D6c's reason once it lands.
        tile_reasons = {'reference_invalid', 'highlight_tile_unpublishable'}
        self.assertEqual([r for r in mixed.get('dropped_references', []) if r['reason'] not in tile_reasons],
                         plain.get('dropped_references', []))
        # Mode-tolerant (D6c review R1, the B2c pattern): before D6c the captioned tile drops with a tile reason; once D6c
        # is in it publishes, so there is no tile reason and the bullet's row carries its published tiles.
        row = (((mixed.get('proposed') or {}).get('display') or {}).get(self.lead) or {})
        self.assertTrue(tile_reasons & {r['reason'] for r in mixed.get('dropped_references', [])}
                        or 'published_highlight_tiles' in (row.get('wording') or {}),
                        'The captioned tile is either dropped with a tile reason or published on the tiled bullet row')
        self.assertEqual([t['publish'] for t in self.tiles()], ['as_today', 'as_today', 'after_update'])

    def test_deleting_a_bullet_prunes_every_tile_it_backs_without_error(self):
        from services.resume_draft_service import ResumeDraftService
        snapshot = {'draft_version': 4, 'items': {}, 'highlight_refs': [
            'a', {'item_ref': 'a', 'metric_index': 2, 'metric_text': '$1M'}, 'b',
            {'item_ref': 'b', 'metric_index': 1, 'metric_text': '9', 'caption': 'kept'}]}
        after = ResumeDraftService.prune_deleted_private_references(snapshot, {'a'})
        self.assertEqual(after['highlight_refs'], ['b', {'item_ref': 'b', 'metric_index': 1, 'metric_text': '9', 'caption': 'kept'}])
        self.assertEqual(after['draft_version'], 5)

    def test_moving_a_tiled_bullet_drops_all_its_tiles_and_undo_restores_them(self):
        self.setup_tiles()
        self.choose([self.lead, {'item_ref': self.lead, 'metric_index': 2, 'caption': 'in redesigns overseen'}, self.bullet])
        before = self.stored()
        staged = GuideConversionTests.stage(self, self.lead, 'skill', {'name': 'Fictional leadership'})
        highlights = next(row for row in staged['affected_references'] if row['kind'] == 'highlights')
        self.assertEqual(highlights['references'], before)
        confirmed = GuideConversionTests.confirm(self, staged)
        self.assertEqual(self.stored(), [self.bullet])
        GuideConversionTests.undo(self, confirmed)
        self.assertEqual(self.stored(), before)

    # ---- B3t round 2 (review a60cb95)

    def test_f4_a_bullet_backed_only_by_an_object_tile_is_affected_by_a_move(self):
        from services.resume_guide_turns import tile_key
        self.setup_tiles()
        self.choose([{'item_ref': self.lead, 'metric_index': 2, 'caption': 'in redesigns overseen'}, self.bullet])
        before = self.stored()
        staged = GuideConversionTests.stage(self, self.lead, 'skill', {'name': 'Fictional leadership'})
        highlights = next(row for row in staged['affected_references'] if row['kind'] == 'highlights')
        self.assertEqual(highlights['references'], before)
        keep_object = [{**row, 'references': list(row['references'])} for row in self.reviewed(staged)]
        for row in keep_object:
            if row['kind'] == 'highlights':
                row['references'] = list(before)
        with self.assertRaises(ResumeIntakeConflictError) as kept:
            GuideConversionTests.confirm(self, staged, keep_object)
        self.assertEqual(kept.exception.error_code, 'reconciliation_required')
        confirmed = GuideConversionTests.confirm(self, staged)
        self.assertEqual([tile_key(ref)[0] for ref in self.stored()], [self.bullet])
        GuideConversionTests.undo(self, confirmed)
        self.assertEqual(self.stored(), before)

    def test_f4_an_alias_and_its_key_cannot_make_a_repeated_pair(self):
        self.setup_tiles()
        submitted = self.service.submit(self.owner, {'request_id': str(uuid4()), 'text': 'A separate fictional result.'})
        proposal = submitted['proposals'][0]
        alias = self.service.working_set(self.owner)['unplaced'][0]['item_ref']
        saved = self.service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': proposal['proposal_key'],
            'decision': 'accept', 'confirmed_values': {'record_type': 'accomplishment', 'parent_key': self.role,
            'wording': 'Ran 5 fictional pilots and 7 reviews.', 'metric_value': '5', 'metric_label': 'pilots'}})
        key = saved['item']['record_key']
        self.assertIn(alias, self.item(key)['identity_aliases'])
        before = self.stored()
        with self.assertRaises(ResumeIntakeValidationError):
            self.choose([{'item_ref': alias, 'metric_index': 1, 'caption': 'reviews'},
                         {'item_ref': key, 'metric_index': 1, 'caption': 'again'}])
        self.assertEqual(self.stored(), before)

    def test_f5_captions_are_visible_plain_text(self):
        self.setup_tiles()
        for caption in ('a\nb', '​', ' ​ ', 'tab\there', 'zero​width'):
            with self.subTest(caption=repr(caption)), self.assertRaises(ResumeIntakeValidationError):
                self.choose([{'item_ref': self.lead, 'metric_index': 2, 'caption': caption}])
        self.choose([{'item_ref': self.lead, 'metric_index': 2, 'caption': '  in redesigns  '}])
        self.assertEqual(self.stored()[0]['caption'], 'in redesigns')


class LookingAheadPlacementTests(unittest.TestCase):
    """B3t: the private Looking Ahead placement and its rename guard (manager condition 1)."""
    setup_shared = GuideReferenceCommandTests.setup_shared

    def create(self, values, placement='looking_ahead', owner_fixture=None):
        target = owner_fixture or self
        payload = {'type': 'create_private_item', 'request_id': str(uuid4()), 'record_key': str(uuid4()),
                   'record_type': 'knowledge', 'values': values}
        if placement is not None:
            payload['presentation_section'] = placement
        target.shared.draft.commit(target.owner, payload)
        return payload['record_key']

    def row(self, key):
        return next(r for r in self.shared.draft.get_workspace(self.owner)['items'] if r['record_key'] == key)

    def save(self, key, values):
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == key)
        return self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': key,
            'record_type': 'knowledge', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': values})

    def test_placement_is_private_metadata_honoured_by_the_guide(self):
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        self.assertEqual(self.row(key)['presentation_section'], 'looking_ahead')
        self.assertNotIn('presentation_section', self.shared.canonical.get_item(self.owner, key).get('values') or {},
                         'The placement is never stored in canonical values')
        self.assertEqual(self.service.working_item(self.owner, key)['section'], 'looking_ahead')

    def test_placement_refuses_other_values_types_empty_and_long_words(self):
        from services.resume_draft_service import ResumeDraftValidationError
        self.setup_shared()
        cases = [({'title': 'Looking Ahead', 'wording': 'Fine.', 'classification': 'work'}, 'impact_statement'),
                 ({'title': 'Looking Ahead', 'wording': '', 'classification': 'work'}, 'looking_ahead'),
                 ({'title': 'Looking Ahead', 'wording': 'x' * 121, 'classification': 'work'}, 'looking_ahead'),
                 ({'title': 'Where I am headed', 'wording': 'Fine.', 'classification': 'work'}, 'looking_ahead')]
        for values, placement in cases:
            with self.subTest(placement=placement, title=values['title'], words=len(values['wording'])):
                with self.assertRaises(Exception) as refused:
                    self.create(values, placement)
                self.assertIn(type(refused.exception).__name__, {'ResumeDraftValidationError', 'ResumeDraftConflictError'})
        with self.assertRaises(ResumeDraftValidationError):
            self.shared.draft.commit(self.owner, {'type': 'create_private_item', 'request_id': str(uuid4()),
                'record_key': str(uuid4()), 'record_type': 'skill', 'values': {'name': 'Placed skill'},
                'presentation_section': 'looking_ahead'})

    def test_renaming_a_placed_entry_is_refused_and_changes_nothing(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        before = self.shared.draft.repository.load_owner(self.owner)
        with self.assertRaises(ResumeDraftConflictError) as refused:
            self.save(key, {'title': 'Where I am headed'})
        self.assertEqual(refused.exception.error_code, 'looking_ahead_rename_unavailable')
        self.assertEqual(str(refused.exception), "The Looking Ahead name can't be changed yet. Your words are kept.")
        self.assertEqual(self.shared.draft.repository.load_owner(self.owner), before)
        self.save(key, {'wording': 'Lead harbor automation controls.'})
        self.assertEqual(self.row(key)['proposed_values']['wording'], 'Lead harbor automation controls.')
        self.assertEqual(self.row(key)['presentation_section'], 'looking_ahead', 'The placement survives an ordinary edit')

    def test_a_placed_looking_ahead_publishes_exactly_as_an_unplaced_one(self):
        values = {'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'}
        self.setup_shared()
        self.create(values)
        placed = self.shared.publication.read_publication_basis_for_owner(self.owner)
        self.setup_shared()
        self.create(values, placement=None)
        unplaced = self.shared.publication.read_publication_basis_for_owner(self.owner)
        for name in ('read_state', 'blocked_items', 'ineligible_items', 'dropped_references', 'change_count',
                     'publication_state', 'sharing_enabled'):
            self.assertEqual(placed.get(name), unplaced.get(name), name)

    # ---- B3t round 2 (review a60cb95)

    def test_f1_placement_needs_a_work_entry(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        for values in ({'title': 'Looking Ahead', 'wording': 'A personal plan.', 'classification': 'personal'},
                       {'title': 'Looking Ahead', 'wording': 'No classification given.'}):
            with self.subTest(values=values), self.assertRaises(ResumeDraftConflictError) as refused:
                self.create(values)
            self.assertEqual(refused.exception.error_code, 'looking_ahead_placement_unavailable')
            self.assertEqual(str(refused.exception), 'Looking Ahead is for a work entry. Your words are kept.')
        both = self.create({'title': 'Looking Ahead', 'wording': 'A shared plan.', 'classification': 'both'})
        self.assertEqual(self.row(both)['presentation_section'], 'looking_ahead')
        before = self.shared.draft.repository.load_owner(self.owner)
        with self.assertRaises(ResumeDraftConflictError) as personal:
            self.save(both, {'classification': 'personal'})
        self.assertEqual(personal.exception.error_code, 'looking_ahead_placement_unavailable')
        self.assertEqual(self.shared.draft.repository.load_owner(self.owner), before)

    def test_f2_the_my_data_edit_route_cannot_rename_or_make_personal_a_placed_entry(self):
        from app import app
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        names = ('TESTING', 'PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY', 'PEERSLATE_TRUST_EASYAUTH_HEADERS',
                 'PEERSLATE_ENTRY_POLICY_ENABLED', 'ENTRY_POLICY_SERVICE')
        original = {name: app.config.get(name) for name in names}
        self.addCleanup(app.config.update, original)
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY=self.owner,
                          PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_ENTRY_POLICY_ENABLED=True,
                          ENTRY_POLICY_SERVICE=self.shared.policy)
        client = app.test_client()
        def edit(values):
            version = client.get('/api/entry-policy/me/entries/' + key).get_json()['entry']['content_version']
            return client.post('/api/entry-policy/me/commands', headers={'X-PeerSlate-Request': 'same-origin'},
                json={'request_id': str(uuid4()), 'type': 'edit', 'entry_key': key, 'expected_content_version': version,
                      'values': values})
        before = self.shared.policy.repository.load_owner(self.owner)
        renamed = edit({'title': 'Where I am headed', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        self.assertEqual(renamed.status_code, 409)
        self.assertEqual(renamed.get_json()['error_code'], 'looking_ahead_rename_unavailable')
        self.assertEqual(renamed.get_json()['message'], "The Looking Ahead name can't be changed yet. Your words are kept.")
        personal = edit({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'personal'})
        self.assertEqual(personal.status_code, 409)
        self.assertEqual(personal.get_json()['error_code'], 'looking_ahead_placement_unavailable')
        self.assertEqual(self.shared.policy.repository.load_owner(self.owner), before, 'Nothing is saved')
        worded = edit({'title': 'Looking Ahead', 'wording': 'Lead harbor automation controls.', 'classification': 'work'})
        self.assertEqual(worded.status_code, 200, worded.get_json())

    def test_f3_the_guide_accept_path_keeps_the_rename_wording(self):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.test_my_data_intake_sources import extracted_pipeline
        words = 'Looking Ahead' + chr(10) + 'Where I am headed' + chr(10)
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'knowledge', 'values': {'title': 'Where I am headed'},
            'outcome': 'additional_detail', 'match_reference': key, 'quote': 'Where I am headed', 'confidence': 'certain'}])
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=self.shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(words), extraction_adapter=adapter,
            matching_exclusions=lambda member: set())
        submitted = service.submit(self.owner, {'request_id': str(uuid4()), 'attachments': [{'client_key': 'document',
            'kind': 'document', 'declared_content_type': 'text/plain', 'filename': 'fictional.txt'}]},
            files={'document': FakeUpload('text/plain', words.encode(), 'fictional.txt')})
        proposal = next(p for p in submitted['proposals'] if p.get('target_key') == key)
        before = self.shared.draft.repository.load_owner(self.owner)
        with self.assertRaises(ResumeIntakeConflictError) as refused:
            service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': proposal['proposal_key'],
                                        'decision': 'accept', 'confirmed_values': {'title': 'Where I am headed'}})
        self.assertEqual(refused.exception.error_code, 'looking_ahead_rename_unavailable')
        self.assertEqual(str(refused.exception), "The Looking Ahead name can't be changed yet. Your words are kept.")
        self.assertEqual(self.shared.draft.repository.load_owner(self.owner), before)

    # ---- B3t round 3 (review 584b425, R2-F1): one choke point for every My Data command

    def policy_client(self):
        from app import app
        names = ('TESTING', 'PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY', 'PEERSLATE_TRUST_EASYAUTH_HEADERS',
                 'PEERSLATE_ENTRY_POLICY_ENABLED', 'ENTRY_POLICY_SERVICE')
        original = {name: app.config.get(name) for name in names}
        self.addCleanup(app.config.update, original)
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY=self.owner,
                          PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_ENTRY_POLICY_ENABLED=True,
                          ENTRY_POLICY_SERVICE=self.shared.policy)
        return app.test_client()

    def policy_command(self, client, key, payload):
        version = client.get('/api/entry-policy/me/entries/' + key).get_json()['entry']['content_version']
        return client.post('/api/entry-policy/me/commands', headers={'X-PeerSlate-Request': 'same-origin'},
            json={'request_id': str(uuid4()), 'entry_key': key, 'expected_content_version': version, **payload})

    def test_r3_an_edit_that_omits_the_classification_is_refused(self):
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        client = self.policy_client()
        before = self.shared.policy.repository.load_owner(self.owner)
        omitted = self.policy_command(client, key, {'type': 'edit',
            'values': {'title': 'Looking Ahead', 'wording': 'Lead harbor automation controls.'}})
        self.assertEqual(omitted.status_code, 409, omitted.get_json())
        self.assertEqual(omitted.get_json()['error_code'], 'looking_ahead_placement_unavailable')
        self.assertEqual(omitted.get_json()['message'], 'Looking Ahead is for a work entry. Your words are kept.')
        self.assertEqual(self.shared.policy.repository.load_owner(self.owner), before, 'Nothing is written')

    def test_r3_resolving_a_match_cannot_rename_or_make_personal_a_placed_entry(self):
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        renaming = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'knowledge',
            'values': {'title': 'Where I am headed', 'wording': 'Lead port automation.', 'classification': 'work'}})['record_key']
        personal = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'knowledge',
            'values': {'title': 'Looking Ahead', 'wording': 'A personal plan.', 'classification': 'personal'}})['record_key']
        client = self.policy_client()
        before = self.shared.policy.repository.load_owner(self.owner)
        cases = [(renaming, 'equivalent', 'looking_ahead_rename_unavailable'),
                 (renaming, 'additional_detail', 'looking_ahead_rename_unavailable'),
                 (personal, 'equivalent', 'looking_ahead_placement_unavailable'),
                 (personal, 'additional_detail', 'looking_ahead_placement_unavailable')]
        for candidate, decision, code in cases:
            with self.subTest(decision=decision, code=code):
                refused = self.policy_command(client, key, {'type': 'resolve_match', 'candidate_key': candidate,
                                                            'match_decision': decision})
                self.assertEqual(refused.status_code, 409, refused.get_json())
                self.assertEqual(refused.get_json()['error_code'], code)
                self.assertEqual(self.shared.policy.repository.load_owner(self.owner), before)

    def test_r3_any_command_that_reaches_the_persist_point_is_checked(self):
        from unittest.mock import patch
        from services.entry_policy_service import EntryPolicyConflictError
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        policy = self.shared.policy
        version = policy.get_entry(self.owner, key)['entry']['content_version']
        original_apply = policy._apply

        def future_command(snapshot, command, now):
            # Stands in for any command added later: it changes the stored values its own way.
            affected, presented = original_apply(snapshot, command, now)
            snapshot['entries'][key]['values'] = {**snapshot['entries'][key]['values'], 'title': 'A new name'}
            return affected, presented

        before = policy.repository.load_owner(self.owner)
        with patch.object(policy, '_apply', side_effect=future_command):
            with self.assertRaises(EntryPolicyConflictError) as refused:
                policy.commit(self.owner, {'type': 'edit', 'request_id': str(uuid4()), 'entry_key': key,
                    'expected_content_version': version,
                    'values': {'title': 'Looking Ahead', 'wording': 'Words.', 'classification': 'work'}})
        self.assertEqual(refused.exception.error_code, 'looking_ahead_rename_unavailable')
        self.assertEqual(policy.repository.load_owner(self.owner), before)

    # ---- B3t round 4 (review 44d80ad)

    def publish_now(self):
        reviewed = self.shared.publication.review_for_owner(self.owner, {}).reviewed
        return self.shared.publication.commit(self.owner, {'type': 'publish', 'request_id': str(uuid4()),
            'profile_identity': None, 'reviewed_digest': reviewed.digest,
            'candidate': self.shared.publication.publish_candidate(reviewed)})

    def test_r4_publish_keeps_the_placement_and_the_rename_guard(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        self.shared.seed_publication(self.owner, [(key, True, False)], slug='r4-placement')
        self.save(key, {'wording': 'Lead harbor automation controls.'})
        self.publish_now()
        draft = self.shared.draft.repository.load_owner(self.owner)
        self.assertNotIn(key, draft['items'], 'Publish consumed the item draft')
        self.assertEqual(draft.get('presentation_placements'), {key: 'looking_ahead'})
        self.assertEqual(self.row(key)['presentation_section'], 'looking_ahead', 'The placement survives publish')
        self.assertEqual(self.shared.canonical.get_item(self.owner, key)['values']['wording'], 'Lead harbor automation controls.')
        with self.assertRaises(ResumeDraftConflictError) as renamed:
            self.save(key, {'title': 'Where I am headed'})
        self.assertEqual(renamed.exception.error_code, 'looking_ahead_rename_unavailable')
        client = self.policy_client()
        refused = self.policy_command(client, key, {'type': 'edit',
            'values': {'title': 'Where I am headed', 'wording': 'Lead harbor automation controls.', 'classification': 'work'}})
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.get_json()['error_code'], 'looking_ahead_rename_unavailable')
        # A second edit and publish still work, and the placement stays.
        self.save(key, {'wording': 'Lead harbor and rail automation controls.'})
        self.publish_now()
        self.assertEqual(self.shared.canonical.get_item(self.owner, key)['values']['wording'],
                         'Lead harbor and rail automation controls.')
        self.assertEqual(self.row(key)['presentation_section'], 'looking_ahead')

    def test_r4_an_unrelated_change_is_never_blocked_by_another_placed_entry(self):
        self.setup_shared()
        placed = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        # A placed entry that is already out of shape (written past every guard) must not block unrelated edits.
        policy = self.shared.policy.repository.load_owner(self.owner)
        policy['entries'][placed]['values'] = {**policy['entries'][placed]['values'], 'title': 'Broken elsewhere'}
        self.shared.policy.repository.save_owner(self.owner, policy)
        client = self.policy_client()
        unrelated = self.policy_command(client, self.skill, {'type': 'edit',
            'values': {'skill_name': 'Renamed fictional skill', 'skill_summary': None}})
        self.assertEqual(unrelated.status_code, 200, unrelated.get_json())

    def test_f4_discard_keeps_the_placement(self):
        self.setup_shared()
        key = self.create({'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'})
        self.save(key, {'wording': 'Unsaved words to discard.'})
        version = self.shared.draft.get_workspace(self.owner)['draft_version']
        self.shared.draft.commit(self.owner, {'type': 'discard_item', 'request_id': str(uuid4()), 'record_key': key,
                                              'expected_draft_version': version})
        row = self.row(key)
        self.assertEqual(row['presentation_section'], 'looking_ahead')
        self.assertFalse((row.get('proposed_values') or {}).get('wording'), 'The unsaved words are discarded')


class GuideConversionTests(unittest.TestCase):
    """B3b: same-key private moves and revision-safe Undo (ruling 41e46cf, B3b design answers)."""
    setup_shared = GuideReferenceCommandTests.setup_shared

    def working(self):
        return self.service.working_set(self.owner)

    def item(self, ref):
        return self.service.working_item(self.owner, ref)

    def stage(self, ref, record_type, values, parent=None, request_id=None):
        item, working = self.item(ref), self.working()
        revision = item['revision'] if item['origin'] == 'pending' else item['saved_revision']
        return self.service.guide_conversion(self.owner, {'request_id': request_id or str(uuid4()), 'action': 'stage',
            'item_ref': ref, 'expected_working_set_token': working['working_set_token'], 'expected_item_revision': revision,
            'destination': {'record_type': record_type, 'values': values, 'parent_ref': parent}})

    def reviewed(self, staged):
        return [{'kind': row['kind'], 'container_ref': row['container_ref'], 'before_digest': row['before_digest'],
                 'references': [] if row['container_ref'] == staged['item_ref']
                 else [ref for ref in row['references'] if ref != staged['item_ref']]} for row in staged['affected_references']]

    def confirm(self, staged, reconciliation=None, request_id=None):
        return self.service.guide_conversion(self.owner, {'request_id': request_id or str(uuid4()), 'action': 'confirm',
            'conversion_key': staged['conversion_key'], 'conversion_token': staged['conversion_token'],
            'expected_working_set_token': self.working()['working_set_token'],
            'reference_reconciliation': self.reviewed(staged) if reconciliation is None else reconciliation})

    def undo(self, confirmed, request_id=None):
        return self.service.guide_conversion(self.owner, {'request_id': request_id or str(uuid4()), 'action': 'undo',
            'operation_ref': confirmed['operation_ref'], 'undo_token': confirmed['undo_token']})

    def raw_draft(self):
        import copy
        snapshot = self.shared.draft.repository.load_owner(self.owner)
        return copy.deepcopy(snapshot.get('items') or {}), copy.deepcopy(snapshot.get('highlight_refs'))

    def canonical(self):
        import copy
        return copy.deepcopy(sorted(self.shared.canonical.list_items(self.owner), key=lambda row: row['record_key']))

    def presented(self, key):
        return next((row for row in self.shared.draft.get_workspace(self.owner)['items'] if row['record_key'] == key), None)

    def test_saved_skill_moves_to_a_project_privately_while_public_copy_stays_canonical(self):
        import copy
        from services.resume_guide_turns import CONVERSION_DESCRIPTOR_KEYS
        self.setup_shared()
        self.shared.seed_publication(self.owner, [(key, True, False) for key in (self.role, self.bullet, self.skill)])
        public = copy.deepcopy(self.shared.publication.owner_preview(self.owner)['current'])
        canonical = self.canonical()
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A fictional project.'})
        self.assertEqual((staged['outcome'], staged['saved'], staged['missing_required_fields']), ('staged', False, []))
        self.assertEqual(self.item(self.skill)['record_type'], 'skill', 'Staging changes nothing')
        confirmed = self.confirm(staged)
        self.assertEqual((confirmed['outcome'], confirmed['canonical_changed'], confirmed['publishes']),
                         ('saved_privately', False, False))
        self.assertEqual(self.canonical(), canonical)
        self.assertEqual(self.shared.publication.owner_preview(self.owner)['current'], public)
        presented = self.presented(self.skill)
        self.assertEqual(presented['record_type'], 'skill', 'The publisher keeps the canonical type')
        self.assertEqual(set(presented['conversion']), set(CONVERSION_DESCRIPTOR_KEYS))
        self.assertEqual((presented['conversion']['state'], presented['conversion']['destination_record_type'],
                          presented['conversion']['conversion_op_ref']), ('confirmed_private', 'project', confirmed['operation_ref']))
        moved = self.item(self.skill)
        self.assertEqual((moved['item_ref'], moved['record_type'], moved['values']['summary']),
                         (self.skill, 'project', 'A fictional project.'))
        basis = self.shared.publication.read_publication_basis_for_owner(self.owner)
        # Lockstep with Lane D's D6c (coordination 181c5c4): before D6c a moved type can't publish yet, so the basis is
        # blocked by name; with D6c the move publishes and the basis is current. Either is honest; this narrows to
        # D6c's state once it lands.
        blocked = {'item_ref': self.skill, 'reason': 'publication_type_transition_unavailable'}
        self.assertIn(basis['read_state'], {'blocked', 'current'})
        if basis['read_state'] == 'blocked':
            self.assertIn(blocked, basis['blocked_items'])
        else:
            self.assertNotIn(blocked, basis.get('blocked_items') or [])

    def test_pending_suggestion_moves_with_the_same_item_ref_and_no_canonical_record(self):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        self.setup_shared()
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'skill', 'values': {'name': 'Radio restoration'},
            'quote': 'I do Radio restoration.', 'outcome': 'new', 'confidence': 'certain'}])
        self.service = ResumeIntakeService(repository=self.service.repository, draft_service=self.shared.draft,
            policy=selected_policy_for_tests(), extraction_adapter=adapter)
        self.service.submit(self.owner, {'request_id': str(uuid4()), 'text': 'I do Radio restoration.'})
        pending = next(row for section in self.working()['sections'] for row in section['items'] if row['origin'] == 'pending')
        canonical = self.canonical()
        staged = self.stage(pending['item_ref'], 'project', {'project_name': 'Radio restoration', 'summary': 'Restored radios.'})
        confirmed = self.confirm(staged)
        moved = self.item(pending['item_ref'])
        self.assertEqual((moved['origin'], moved['record_type'], moved['state']), ('pending', 'project', 'waiting'))
        self.assertEqual(self.canonical(), canonical, 'A pending move never makes a canonical record')
        self.undo(confirmed)
        back = self.item(pending['item_ref'])
        self.assertEqual((back['origin'], back['record_type'], back['values'].get('name')), ('pending', 'skill', 'Radio restoration'))

    def test_incomplete_destination_stays_waiting_and_cannot_be_confirmed(self):
        self.setup_shared()
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill'})
        self.assertEqual(staged['missing_required_fields'], ['summary'])
        with self.assertRaises(ResumeIntakeValidationError) as missing:
            self.confirm(staged)
        self.assertEqual((missing.exception.code, missing.exception.missing_required_fields),
                         ('missing_required_fields', ['summary']))
        bullet = self.stage(self.skill, 'accomplishment', {'wording': 'Fictional skill in use.'})
        self.assertEqual(bullet['missing_required_fields'], ['parent_ref'])
        self.assertNotIn('conversion', self.presented(self.skill) or {})

    def test_stage_replays_and_a_changed_reuse_is_a_conflict(self):
        self.setup_shared()
        request_id = str(uuid4())
        first = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'}, request_id=request_id)
        again = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'}, request_id=request_id)
        self.assertTrue(again['replayed'])
        self.assertEqual(again['conversion_key'], first['conversion_key'])
        with self.assertRaises(ResumeIntakeConflictError) as conflict:
            self.stage(self.skill, 'project', {'project_name': 'Other', 'summary': 'A project.'}, request_id=request_id)
        self.assertEqual(conflict.exception.error_code, 'idempotency_conflict')

    def test_confirm_applies_once_with_one_version_change(self):
        self.setup_shared()
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'})
        before = self.shared.draft.get_workspace(self.owner)['draft_version']
        payload = {'request_id': str(uuid4()), 'action': 'confirm', 'conversion_key': staged['conversion_key'],
            'conversion_token': staged['conversion_token'], 'expected_working_set_token': self.working()['working_set_token'],
            'reference_reconciliation': self.reviewed(staged)}
        first = self.service.guide_conversion(self.owner, dict(payload))
        self.assertTrue(self.service.guide_conversion(self.owner, dict(payload))['replayed'], 'A lost-response retry replays')
        second = self.confirm(staged)
        self.assertEqual((second['operation_ref'], second['replayed']), (first['operation_ref'], True))
        self.assertEqual(self.shared.draft.get_workspace(self.owner)['draft_version'], before + 1)

    def test_moving_a_bullet_needs_every_reference_reviewed_and_undo_restores_them(self):
        self.setup_shared()
        reference = GuideReferenceCommandTests.command
        self.service.set_guide_references(self.owner, reference(self, 'skill', [self.bullet], self.skill))
        self.service.set_guide_references(self.owner, reference(self, 'highlights', [self.bullet]))
        before = self.raw_draft()
        staged = self.stage(self.bullet, 'skill', {'name': 'Reviewed fictional records'})
        self.assertEqual(sorted(row['kind'] for row in staged['affected_references']), ['highlights', 'skill'])
        kept = [{**row, 'references': [self.bullet]} for row in self.reviewed(staged)]
        for reconciliation in ([], kept):
            with self.subTest(reconciliation=reconciliation), self.assertRaises(ResumeIntakeConflictError) as refused:
                self.confirm(staged, reconciliation)
            self.assertEqual(refused.exception.error_code, 'reconciliation_required')
        confirmed = self.confirm(staged)
        workspace = self.shared.draft.get_workspace(self.owner)
        skill = next(row for row in workspace['items'] if row['record_key'] == self.skill)
        self.assertEqual((skill['evidence_refs'], workspace['highlight_refs']), ([], []))
        self.undo(confirmed)
        self.assertEqual(self.raw_draft(), before)

    def test_a_later_manual_edit_makes_undo_stale_and_discard_needs_undo(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        confirmed = self.confirm(self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'}))
        presented = self.presented(self.skill)
        version = self.shared.draft.get_workspace(self.owner)['draft_version']
        with self.assertRaises(ResumeDraftConflictError) as discard:
            self.shared.draft.commit(self.owner, {'type': 'discard_item', 'request_id': str(uuid4()),
                'record_key': self.skill, 'expected_draft_version': version})
        self.assertEqual(discard.exception.error_code, 'conversion_undo_required')
        self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': self.skill,
            'record_type': 'project', 'expected_draft_version': version, 'expected_content_token': presented['content_token'],
            'expected_access_revision': presented['access_revision'], 'values': {'summary': 'An edited fictional project.'}})
        self.assertEqual(self.item(self.skill)['values']['summary'], 'An edited fictional project.')
        edited = self.raw_draft()
        with self.assertRaises(ResumeIntakeConflictError) as stale:
            self.undo(confirmed)
        self.assertEqual(stale.exception.error_code, 'stale_undo')
        self.assertEqual(self.raw_draft(), edited)

    def create(self, kind, values, parent=None):
        return self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': kind,
            'parent_key': parent, 'values': values})['record_key']

    def hide(self, ref):
        current = self.item(ref)
        self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': ref, 'hidden': True,
            'expected_working_set_token': self.working()['working_set_token'],
            'expected_item_revision': current['saved_revision']})

    def edit_saved(self, key, values):
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(row for row in workspace['items'] if row['record_key'] == key)
        self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': key,
            'record_type': (row.get('conversion_destination') or row)['record_type'],
            'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': values})

    def test_unrelated_changes_after_a_move_never_make_undo_stale(self):
        reference = GuideReferenceCommandTests.command
        changes = {
            'unrelated edit': lambda other: self.edit_saved(other, {'summary': 'An unrelated fictional edit.'}),
            'hide of another item': lambda other: self.hide(other),
            "another skill's references": lambda other: self.service.set_guide_references(
                self.owner, reference(self, 'skill', [self.bullet], other)),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                self.setup_shared()
                other = self.create('skill', {'name': 'Unrelated fictional skill'})
                before = self.raw_draft()[0].get(self.skill)
                confirmed = self.confirm(self.stage(self.skill, 'project',
                                                   {'project_name': 'Fictional skill', 'summary': 'A project.'}))
                change(other)
                kept = self.raw_draft()[0].get(other)
                self.assertEqual(self.undo(confirmed)['outcome'], 'undone')
                self.assertEqual(self.raw_draft()[0].get(self.skill), before, 'The moved item is exactly restored')
                self.assertEqual(self.raw_draft()[0].get(other), kept, 'and the unrelated change is kept')
                self.assertEqual(self.item(self.skill)['record_type'], 'skill')

    def test_a_change_to_the_moved_item_its_links_or_its_parent_makes_undo_stale(self):
        reference = GuideReferenceCommandTests.command
        def move_bullet_with_links():
            self.service.set_guide_references(self.owner, reference(self, 'skill', [self.bullet], self.skill))
            self.service.set_guide_references(self.owner, reference(self, 'highlights', [self.bullet]))
            self.second = self.create('accomplishment', {'wording': 'Checked 3 fictional records.',
                'metric_value': '3', 'metric_label': 'fictional records'}, self.role)
            return self.confirm(self.stage(self.bullet, 'skill', {'name': 'Reviewed fictional records'}))
        def move_skill_under_role():
            return self.confirm(self.stage(self.skill, 'accomplishment',
                                           {'wording': 'Used the fictional skill on 4 fictional records.'}, self.role))
        cases = {
            'an edit of the moved item': (move_bullet_with_links,
                lambda: self.edit_saved(self.bullet, {'name': 'Edited fictional records'})),
            "a link change in the moved item's skill": (move_bullet_with_links,
                lambda: self.service.set_guide_references(self.owner, reference(self, 'skill', [self.second], self.skill))),
            "a link change in the moved item's highlights": (move_bullet_with_links,
                lambda: self.service.set_guide_references(self.owner, reference(self, 'highlights', [self.second]))),
            'a hide of the parent role': (move_skill_under_role, lambda: self.hide(self.role)),
        }
        for name, (move, change) in cases.items():
            with self.subTest(change=name):
                self.setup_shared()
                confirmed = move()
                change()
                changed = self.raw_draft()
                with self.assertRaises(ResumeIntakeConflictError) as stale:
                    self.undo(confirmed)
                self.assertEqual(stale.exception.error_code, 'stale_undo')
                self.assertEqual(self.raw_draft(), changed, 'A stale Undo changes nothing')

    def test_private_consumers_see_the_effective_move_and_public_copy_stays_canonical(self):
        import copy
        self.setup_shared()
        self.shared.seed_publication(self.owner, [(key, True, True) for key in (self.role, self.bullet, self.skill)])
        public = copy.deepcopy(self.shared.publication.owner_preview(self.owner)['current'])
        guest = copy.deepcopy(self.shared.publication.guest_read(slug='g-alex'))
        moves = ((self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A fictional project.'}, None),
                 (self.bullet, 'skill', {'name': 'Reviewed fictional records'}, None))
        for key, record_type, values, parent in moves:
            staged = self.stage(key, record_type, values, parent)
            self.confirm(staged)
        extra = self.create('skill', {'name': 'Another fictional skill'})
        self.confirm(self.stage(extra, 'accomplishment', {'wording': 'Used it on 4 fictional records.'}, self.role))
        for key, record_type in ((self.skill, 'project'), (self.bullet, 'skill'), (extra, 'accomplishment')):
            with self.subTest(item=key):
                guide = self.item(key)
                destination = self.presented(key)['conversion_destination']
                self.assertEqual(guide['record_type'], record_type)
                # The owner page and private preview read this private workspace projection.
                self.assertEqual((destination['record_type'], destination['values'], destination['parent_key'],
                                  destination['section']),
                                 (guide['record_type'], guide['values'], guide['parent_ref'], guide['section']))
        self.assertEqual(self.presented(extra)['conversion_destination']['section'], self.item(self.role)['section'])
        self.assertEqual(self.shared.publication.owner_preview(self.owner)['current'], public,
                         'Published resume and visitor-AI choices stay canonical')
        self.assertEqual(self.shared.publication.guest_read(slug='g-alex'), guest, 'Visitors see no change')

    def test_fresh_undo_restores_the_exact_prior_private_state(self):
        self.setup_shared()
        before = self.raw_draft()
        confirmed = self.confirm(self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'}))
        self.assertNotEqual(self.raw_draft(), before)
        undone = self.undo(confirmed)
        self.assertEqual(undone['outcome'], 'undone')
        self.assertEqual(self.raw_draft(), before)
        self.assertEqual(self.item(self.skill)['record_type'], 'skill')
        with self.assertRaises(ResumeIntakeConflictError):
            self.undo(confirmed)

    def test_foreign_unknown_and_unsupported_moves_refuse_before_effects(self):
        self.setup_shared()
        other = self.shared.canonical.create_private('guide-conversion-other-fictional', {'command_id': str(uuid4()),
            'record_type': 'skill', 'parent_key': None, 'values': {'name': 'Other fictional skill'}})['record_key']
        before = self.raw_draft()
        working = self.working()
        for ref in (other, str(uuid4())):
            with self.subTest(ref=ref), self.assertRaises(ResumeIntakeNotFoundError):
                self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'stage', 'item_ref': ref,
                    'expected_working_set_token': working['working_set_token'], 'expected_item_revision': 'x',
                    'destination': {'record_type': 'project', 'values': {}, 'parent_ref': None}})
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'undo',
                'operation_ref': 'op:' + str(uuid4()) + ':0', 'undo_token': '0' * 64})
        with self.assertRaises(ResumeIntakeValidationError) as unsupported:
            self.stage(self.role, 'skill', {'name': 'Fictional Engineer'})
        self.assertEqual(unsupported.exception.code, 'conversion_unsupported')
        self.assertEqual(self.raw_draft(), before)

    def test_unqualified_sql_refuses_a_move_before_any_effect(self):
        from unittest.mock import Mock
        from services.resume_intake_repository import SqlResumeIntakeRepository
        database = Mock()
        service = ResumeIntakeService(repository=SqlResumeIntakeRepository(database), policy=selected_policy_for_tests())
        payload = {'request_id': str(uuid4()), 'action': 'stage', 'item_ref': str(uuid4()),
            'expected_working_set_token': 'a' * 64, 'expected_item_revision': 'x',
            'destination': {'record_type': 'project', 'values': {'project_name': 'P'}, 'parent_ref': None}}
        with self.assertRaises(ResumeIntakeUnavailableError) as refused:
            service.guide_conversion('fictional-sql-owner', payload)
        self.assertEqual(refused.exception.proposed, payload)
        self.assertEqual(database.mock_calls, [])

    def test_an_injected_failure_restores_every_store_and_a_retry_succeeds(self):
        import copy
        from unittest.mock import patch
        from services.resume_intake_repository import ResumeIntakeStoreUnavailable
        self.setup_shared()
        reference = GuideReferenceCommandTests.command
        self.service.set_guide_references(self.owner, reference(self, 'skill', [self.bullet], self.skill))
        staged = self.stage(self.bullet, 'skill', {'name': 'Reviewed fictional records'})
        def stores():
            return (copy.deepcopy(self.service.repository._owners), copy.deepcopy(self.shared.draft.repository._owners),
                    copy.deepcopy(self.shared.policy.repository._owners))
        before = stores()
        with patch.object(self.service.repository, 'save_owner', side_effect=ResumeIntakeStoreUnavailable('injected')):
            with self.assertRaises(ResumeIntakeUnavailableError):
                self.confirm(staged)
        self.assertEqual(stores(), before)
        self.assertEqual(self.confirm(staged)['outcome'], 'saved_privately')

    def test_a_staged_move_survives_a_reload_into_a_new_service(self):
        self.setup_shared()
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A project.'})
        reloaded = ResumeIntakeService(repository=self.service.repository, draft_service=self.shared.draft,
            policy=selected_policy_for_tests())
        snapshot = reloaded.repository.load_owner(self.owner)
        self.assertEqual(snapshot['guide']['conversions'][staged['conversion_key']]['state'], 'staged')
        self.service = reloaded
        self.assertEqual(self.confirm(staged)['outcome'], 'saved_privately')


class GuideVisibilityTests(unittest.TestCase):
    def _command(self, service, owner, item, hidden):
        return {"request_id": str(uuid4()), "item_ref": item["item_ref"], "hidden": hidden,
            "expected_working_set_token": service.working_set(owner)["working_set_token"],
            "expected_item_revision": item["revision"] if item["origin"] == "pending" else item["saved_revision"]}

    def test_pending_hide_show_keeps_original_pending_identity_and_never_saves(self):
        import copy
        from unittest.mock import patch
        service, catalog, draft = build_service()
        owner = "visibility-pending-fictional"
        submitted = service.submit(owner, {"request_id": str(uuid4()), "text": "Original fictional detail."})
        key = submitted["proposals"][0]["proposal_key"]
        before = copy.deepcopy(service.repository.load_owner(owner)["proposals"][key])
        item = service.working_set(owner)["unplaced"][0]
        hide = self._command(service, owner, item, True)
        with patch.object(draft.repository, "save_owner", wraps=draft.repository.save_owner) as saved:
            result = service.set_guide_visibility(owner, hide)
            self.assertEqual(result["outcome"], "hidden")
            self.assertTrue(service.set_guide_visibility(owner, hide)["replayed"])
            saved.assert_not_called()
        hidden = service.working_set(owner)["unplaced"][0]
        self.assertEqual(hidden["state"], "hidden")
        self.assertEqual(hidden["item_ref"], item["item_ref"])
        row = service.repository.load_owner(owner)["proposals"][key]
        for name in ("state", "proposed_values", "binding", "quote"):
            self.assertEqual(row[name], before[name])
        self.assertEqual(row["state"], "pending")
        service.set_guide_visibility(owner, self._command(service, owner, hidden, False))
        shown = service.working_set(owner)["unplaced"][0]
        self.assertEqual(shown["state"], "waiting")
        self.assertEqual(shown["values"], item["values"])
        self.assertEqual(catalog.list_items(owner), [])
        with self.assertRaises(ResumeIntakeConflictError):
            service.set_guide_visibility(owner, self._command(service, owner, shown, False))
        service.set_guide_visibility(owner, self._command(service, owner, shown, True))
        service.purge_source(owner, {"request_id":str(uuid4()), "source_key":before["binding"]["source_key"]})
        self.assertEqual(service.working_set(owner)["unplaced"], [])

    def test_saved_visibility_invalidates_old_publish_review_without_changing_public_copy(self):
        import copy
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared, owner = SharedMvp1Fixture(), "visibility-saved-fictional"
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests())
        item = shared.canonical.create_private(owner, {"command_id": str(uuid4()), "record_type": "skill",
            "values": skill("Fictional skill")})
        key = item["record_key"]
        shared.seed_publication(owner, [(key, True, True)])
        public = copy.deepcopy(shared.publication.owner_preview(owner)["current"])
        reviewed = shared.publication.review_for_owner(owner, {}).reviewed
        packet = shared.publication.publish_candidate(reviewed)
        before = shared.draft.get_workspace(owner)["draft_version"]
        working_item = service.working_item(owner, key)
        command = self._command(service, owner, working_item, True)
        service.set_guide_visibility(owner, command)
        self.assertEqual(shared.draft.get_workspace(owner)["draft_version"], before + 1)
        self.assertEqual(service._resume_history(service.repository.load_owner(owner))["inclusion"][key], True)
        self.assertEqual(service.working_item(owner, key)["state"], "hidden")
        self.assertEqual(shared.publication.owner_preview(owner)["current"], public)
        self.assertEqual(shared.canonical.get_item(owner, key)["values"], item["values"])
        self.assertTrue(service.set_guide_visibility(owner, command)["replayed"])
        self.assertEqual(shared.draft.get_workspace(owner)["draft_version"], before + 1)
        from services.resume_publication_repository import PublicationConflictError
        with self.assertRaises(PublicationConflictError):
            shared.publication.commit(owner, {"type": "publish", "request_id": str(uuid4()),
                "candidate": packet, "reviewed_digest": reviewed.digest, "profile_identity": None})
        service.set_guide_visibility(owner, self._command(service, owner, service.working_item(owner, key), False))
        self.assertEqual(service.working_item(owner, key)["state"], "saved")
        self.assertEqual(shared.draft.get_workspace(owner)["draft_version"], before + 2)
        self.assertEqual(shared.publication.owner_preview(owner)["current"], public)

    def test_visibility_rejects_stale_foreign_and_changed_request_and_rolls_back_failed_save(self):
        import copy
        from unittest.mock import patch
        service, catalog, draft = build_service()
        owner, key = "visibility-fenced-fictional", str(uuid4())
        catalog.put_item(owner, {"record_key": key, "record_type": "skill", "values": skill("Fictional"),
            "content_token": "1", "access_revision": 1})
        command = self._command(service, owner, service.working_item(owner, key), True)
        with self.assertRaises(ResumeIntakeNotFoundError):
            service.set_guide_visibility("other-fictional", command)
        with self.assertRaises(ResumeIntakeConflictError):
            service.set_guide_visibility(owner, {**command, "expected_item_revision": "outdated"})
        before = copy.deepcopy(draft.repository._owners)
        with patch.object(service.repository, "save_owner", side_effect=RuntimeError("injected write failure")):
            with self.assertRaisesRegex(RuntimeError, "injected write failure"):
                service.set_guide_visibility(owner, command)
        self.assertEqual(draft.repository._owners, before)
        self.assertNotIn(command["request_id"], service.repository.load_owner(owner)["receipts"])
        service.set_guide_visibility(owner, command)
        with self.assertRaises(ResumeIntakeConflictError):
            service.set_guide_visibility(owner, {**command, "hidden": False})

    def test_publication_basis_refuses_a_concurrent_draft_change_and_keeps_unknown_counts(self):
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared, owner = SharedMvp1Fixture(), "visibility-race-fictional"
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests())
        original = shared.publication.read_publication_basis_for_owner
        def changed(owner, payload):
            basis = original(owner,payload)
            shared.draft.stamp_private_resume_choice(owner,str(uuid4()),"a"*64)
            return basis
        with patch.object(shared.publication,"read_publication_basis_for_owner",side_effect=changed):
            basis = service.guide_publication_basis(owner,service.working_set(owner),shared.publication)
        self.assertEqual(basis["publication_state"],"unknown")
        self.assertIsNone(basis["change_count"])
        self.assertIsNone(basis["membership"])


class GuideProposalEssentialsTests(unittest.TestCase):
    def test_explicit_story_save_binds_actual_personal_entry_once_and_rolls_back_failed_binding(self):
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_draft_service import ResumeDraftUnavailableError
        for fail_binding in (False, True):
            with self.subTest(fail_binding=fail_binding):
                shared, owner = SharedMvp1Fixture(), "guide-story-fictional"
                service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
                    policy=selected_policy_for_tests())
                submitted = service.submit(owner,{"request_id":str(uuid4()),"text":"I restore fictional radios."})
                key = submitted["proposals"][0]["proposal_key"]
                command = {"request_id":str(uuid4()),"proposal_key":key,"decision":"accept","guide_review":True,
                    "guide_section":"story","confirmed_values":{"record_type":"knowledge","title":"My Story",
                        "wording":"I restore fictional radios.","classification":"personal"}}
                original = shared.draft.commit
                def commit(owner, payload):
                    if fail_binding and payload["type"] == "bind_story":
                        raise ResumeDraftUnavailableError("injected story-binding failure")
                    return original(owner,payload)
                with patch.object(shared.draft,"commit",side_effect=commit):
                    if fail_binding:
                        with self.assertRaises(ResumeIntakeUnavailableError):
                            service.decide(owner,command)
                        self.assertEqual(shared.canonical.list_items(owner),[])
                        self.assertEqual(service.repository.load_owner(owner)["proposals"][key]["state"],"pending")
                        self.assertIsNone(shared.draft.get_workspace(owner)["story_entry_key"])
                        continue
                    saved = service.decide(owner,command)
                    record_key = saved["item"]["record_key"]
                    self.assertEqual(shared.draft.get_workspace(owner)["story_entry_key"],record_key)
                    self.assertEqual(service.working_item(owner,record_key)["section"],"story")
                    version = shared.draft.get_workspace(owner)["draft_version"]
                    self.assertTrue(service.decide(owner,command)["replayed"])
                    self.assertEqual(shared.draft.get_workspace(owner)["draft_version"],version)
                    self.assertEqual(len(shared.canonical.list_items(owner)),1)
                    self.assertFalse(saved["item"]["resume_display"])

    def test_failed_guide_confirm_restores_linked_publication_provenance_with_all_owner_stores(self):
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_draft_service import ResumeDraftUnavailableError
        from services.resume_intake_repository import ResumeIntakeStoreUnavailable
        for published in (False,True):
            for failure in ('binding','receipt'):
                with self.subTest(published=published,failure=failure):
                    shared,owner=SharedMvp1Fixture(),'outer-provenance-fictional'
                    if published:
                        old=shared.canonical.create_private(owner,{'command_id':str(uuid4()),'record_type':'role',
                            'values':{'role_title':'Fictional engineer','employer_name':'Fictional Orchard'}})
                        shared.seed_publication(owner,[(old['record_key'],True,True)])
                    repository=InMemoryResumeIntakeRepository()
                    service=ResumeIntakeService(repository=repository,draft_service=shared.draft,
                        policy=selected_policy_for_tests())
                    submitted=service.submit(owner,{'request_id':str(uuid4()),'text':'I restore fictional radios.'})
                    key=submitted['proposals'][0]['proposal_key']
                    before=[store.load_owner(owner) for store in
                        (repository,shared.draft.repository,shared.policy.repository,shared.publication.repository)]
                    command={'request_id':str(uuid4()),'proposal_key':key,'decision':'accept','guide_review':True,
                        'guide_section':'story','confirmed_values':{'record_type':'knowledge','title':'My Story',
                            'wording':'I restore fictional radios.','classification':'personal'}}
                    original=shared.draft.commit
                    def fail_binding(member,payload):
                        if payload['type']=='bind_story': raise ResumeDraftUnavailableError('fictional binding failure')
                        return original(member,payload)
                    fault=(patch.object(shared.draft,'commit',side_effect=fail_binding) if failure=='binding' else
                        patch.object(repository,'save_owner',side_effect=ResumeIntakeStoreUnavailable('fictional receipt failure')))
                    with fault,self.assertRaises(ResumeIntakeUnavailableError):
                        service.decide(owner,command)
                    after=[store.load_owner(owner) for store in
                        (repository,shared.draft.repository,shared.policy.repository,shared.publication.repository)]
                    self.assertEqual(after,before)

    def test_publish_and_failed_guide_confirm_share_lock_order_and_preserve_the_publish(self):
        import threading
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_draft_service import ResumeDraftUnavailableError
        shared,owner=SharedMvp1Fixture(),'outer-publish-fictional'
        old=shared.canonical.create_private(owner,{'command_id':str(uuid4()),'record_type':'role',
            'values':{'role_title':'Fictional engineer','employer_name':'Fictional Orchard'}})
        shared.seed_publication(owner,[(old['record_key'],True,True)])
        reviewed=shared.publication.review_for_owner(owner,{}).reviewed
        publication_command={'type':'publish','request_id':str(uuid4()),'profile_identity':None,
            'reviewed_digest':reviewed.digest,'candidate':shared.publication.publish_candidate(reviewed)}
        service=ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),draft_service=shared.draft,
            policy=selected_policy_for_tests())
        submitted=service.submit(owner,{'request_id':str(uuid4()),'text':'I restore fictional radios.'})
        command={'request_id':str(uuid4()),'proposal_key':submitted['proposals'][0]['proposal_key'],
            'decision':'accept','guide_review':True,'guide_section':'story','confirmed_values':{
                'record_type':'knowledge','title':'My Story','wording':'I restore fictional radios.',
                'classification':'personal'}}
        publisher_ready,guide_waiting=threading.Event(),threading.Event()
        outcomes={}
        original_guard=service.repository.owner_guard
        original_save=shared.publication._save_integrated_memory
        def observed_guard(member):
            if threading.current_thread().name=='fictional-guide-confirm': guide_waiting.set()
            return original_guard(member)
        def held_save(*args,**kwargs):
            publisher_ready.set()
            if not guide_waiting.wait(5): raise AssertionError('Guide never attempted the common owner guard')
            return original_save(*args,**kwargs)
        def publish():
            try:
                outcomes['publish']=shared.publication.commit(owner,publication_command)
                outcomes['published_state']=shared.publication.repository.load_owner(owner)
            except BaseException as error: outcomes['publish_error']=error
        def confirm():
            try:
                if not publisher_ready.wait(5): raise AssertionError('Publisher never acquired its lock')
                service.decide(owner,command)
            except BaseException as error: outcomes['confirm_error']=error
        original=shared.draft.commit
        def fail_binding(member,payload):
            if payload['type']=='bind_story': raise ResumeDraftUnavailableError('fictional binding failure')
            return original(member,payload)
        with patch.object(service.repository,'owner_guard',side_effect=observed_guard),patch.object(
                shared.publication,'_save_integrated_memory',side_effect=held_save),patch.object(
                shared.draft,'commit',side_effect=fail_binding):
            publisher=threading.Thread(target=publish,daemon=True,name='fictional-publish')
            guide=threading.Thread(target=confirm,daemon=True,name='fictional-guide-confirm')
            publisher.start();guide.start()
            publisher.join(7);guide.join(7)
            self.assertFalse(publisher.is_alive() or guide.is_alive(),'Publish and Guide must not deadlock')
        self.assertNotIn('publish_error',outcomes)
        self.assertIsInstance(outcomes.get('confirm_error'),ResumeIntakeUnavailableError)
        self.assertEqual(shared.publication.repository.load_owner(owner),outcomes['published_state'])
        self.assertEqual([item['record_key'] for item in shared.canonical.list_items(owner)],[old['record_key']])
        self.assertEqual(service.repository.load_owner(owner)['proposals'][command['proposal_key']]['state'],'pending')

    def test_unit_of_work_refuses_unqualified_publication_and_releases_locks_on_entry_failure(self):
        import threading
        from unittest.mock import patch
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from services.resume_intake_repository import ResumeIntakeStoreUnavailable
        shared=SharedMvp1Fixture()
        repository=InMemoryResumeIntakeRepository()
        with patch.object(shared.publication,'repository',object()):
            with self.assertRaises(ResumeIntakeStoreUnavailable):
                with repository.unit_of_work(shared.draft,owner="entry-failure-fictional"): self.fail('Unqualified storage must refuse entry')
        class BrokenSnapshot(dict):
            def __deepcopy__(inner,memo): raise RuntimeError('fictional snapshot failure')
        with patch.object(shared.draft.repository,'_owners',{'entry-failure-fictional':BrokenSnapshot()}):
            with self.assertRaisesRegex(RuntimeError,'fictional snapshot failure'):
                with repository.unit_of_work(shared.draft,owner="entry-failure-fictional"): self.fail('Snapshot must fail before writes')
        acquired=[]
        def probe():
            from services.resume_intake_repository import resume_owner_guard
            with resume_owner_guard('entry-failure-fictional'),shared.draft.repository._lock: acquired.append(True)
        thread=threading.Thread(target=probe,daemon=True)
        thread.start();thread.join(5)
        self.assertEqual(acquired,[True],'Failed entry must release both acquired locks')
        self.assertEqual(repository._owners,{})

    def test_guide_proposal_missing_year_stays_pending_and_valid_year_saves_the_same_words_once(self):
        service, catalog, draft = build_service()
        owner = "guide-education-fictional"
        submitted = service.submit(owner, {"request_id": str(uuid4()), "text": "I studied at Fictional University."})
        key = submitted["proposals"][0]["proposal_key"]
        before = service.repository.load_owner(owner)["proposals"][key].copy()
        with self.assertRaises(ResumeIntakeValidationError) as missing:
            service.decide(owner, {"request_id": str(uuid4()), "proposal_key": key, "decision": "accept", "guide_review": True,
                "confirmed_values": {"record_type": "education", "institution_name": "Fictional University"}})
        self.assertEqual(missing.exception.code, "missing_required_fields")
        self.assertEqual(missing.exception.missing_required_fields, ["end_date"])
        after = service.repository.load_owner(owner)["proposals"][key]
        self.assertEqual(after["state"], "pending")
        self.assertEqual(after["proposed_values"], before["proposed_values"])
        self.assertEqual(catalog.list_items(owner), [])
        command = {"request_id": str(uuid4()), "proposal_key": key, "decision": "accept", "guide_review": True,
            "confirmed_values": {"record_type": "education", "institution_name": "Fictional University", "end_date": "2024"}}
        result = service.decide(owner, command)
        self.assertEqual(result["outcome"], "saved")
        self.assertIsNone(result["item"]["values"]["title"])
        self.assertEqual(result["item"]["values"]["end_date"], "2024-01-01")
        self.assertTrue(service.decide(owner, command)["replayed"])
        self.assertEqual(len(catalog.list_items(owner)), 1)

    def test_guide_impact_proposal_over_limit_keeps_the_exact_original_pending(self):
        service, catalog, draft = build_service()
        owner = "guide-impact-fictional"
        original = " ".join(["original"] * 71)
        submitted = service.submit(owner, {"request_id": str(uuid4()), "text": original})
        key = submitted["proposals"][0]["proposal_key"]
        before = service.repository.load_owner(owner)["proposals"][key]["proposed_values"].copy()
        with self.assertRaises(ResumeIntakeValidationError) as too_long:
            service.decide(owner, {"request_id": str(uuid4()), "proposal_key": key, "decision": "accept", "guide_review": True,
                "guide_section": "impact_statement", "confirmed_values": {"record_type": "knowledge",
                    "title": "Professional summary", "wording": original, "classification": "work"}})
        self.assertEqual(too_long.exception.code, "impact_statement_too_long")
        self.assertEqual(too_long.exception.actual_count, 71)
        after = service.repository.load_owner(owner)["proposals"][key]
        self.assertEqual(after["state"], "pending")
        self.assertEqual(after["proposed_values"], before)
        self.assertEqual(catalog.list_items(owner), [])


class ConversationStoryTests(unittest.TestCase):
    def test_unqualified_sql_story_path_keeps_input_and_uses_no_canonical_intent(self):
        from unittest.mock import Mock
        from services.resume_intake_repository import SqlIntakeUnitOfWork
        service,catalog,draft=build_service()
        receipt=service.submit('synthetic-owner',{'type':'add_submission','request_id':str(uuid4()),'text':'I repair radios outside work.'})
        unit=SqlIntakeUnitOfWork(Mock());service.repository.unit_of_work=lambda draft_service, **kwargs:unit
        with self.assertRaisesRegex(ResumeIntakeValidationError,'input is kept'):
            service.decide('synthetic-owner',{'request_id':str(uuid4()),'proposal_key':receipt['proposals'][0]['proposal_key'],
                'decision':'accept','confirmed_values':{'record_type':'knowledge','title':'Radio repair','wording':'I repair radios outside work.','classification':'personal'}})
        self.assertEqual(unit.intents,[]);self.assertEqual(unit.repository.mock_calls,[])
        self.assertEqual(len(service.get_workspace('synthetic-owner')['pending_proposals']),1)
        self.assertEqual(catalog.list_items('synthetic-owner'),[])
    def test_sql_intake_precision_refusal_keeps_pending_source_and_stages_no_write(self):
        from unittest.mock import Mock
        from services.resume_intake_repository import SqlIntakeUnitOfWork
        service,catalog,draft=build_service()
        receipt=service.submit('synthetic-owner',{'type':'add_submission','request_id':str(uuid4()),
            'text':'My certificate was issued June 2022 and expires June 2027.'})
        proposal=receipt['proposals'][0]
        unit=SqlIntakeUnitOfWork(Mock())
        service.repository.unit_of_work=lambda draft_service, **kwargs: unit
        with self.assertRaisesRegex(ResumeIntakeValidationError,'input is kept'):
            service.decide('synthetic-owner',{'request_id':str(uuid4()),'proposal_key':proposal['proposal_key'],
                'decision':'accept','confirmed_values':{'record_type':'credential','name':'Design Practitioner',
                'issuer':'Example Institute','completion_status':'completed','issue_date':'2022-06-01',
                'issue_date_precision':'month','expiration_date':'2027-06-01','expiration_date_precision':'month'}})
        self.assertEqual(unit.intents,[]);self.assertEqual(unit.repository.mock_calls,[])
        self.assertEqual(service.get_workspace('synthetic-owner')['pending_proposals'][0]['proposal_key'],proposal['proposal_key'])
        self.assertEqual(catalog.list_items('synthetic-owner'),[])

    def test_untyped_story_confirmation_is_private_atomic_and_idempotent(self):
        service, catalog, draft = build_service()
        source = 'Outside work I restore radios at a community repair cafe.'
        receipt = service.submit('fiction-story', {'request_id': str(uuid4()), 'text': source})
        proposal = receipt['proposals'][0]
        self.assertEqual(proposal['record_type'], 'unspecified')
        self.assertEqual(catalog.list_items('fiction-story'), [])
        command = {'request_id': str(uuid4()), 'proposal_key': proposal['proposal_key'],
            'decision': 'accept', 'confirmed_values': {'record_type': 'knowledge',
                'title': 'Repair cafe', 'wording': source, 'classification': 'personal'}}
        result = service.decide('fiction-story', command)
        self.assertEqual(result['outcome'], 'saved')
        replay = service.decide('fiction-story', command)
        self.assertTrue(replay['replayed'])
        items = catalog.list_items('fiction-story')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['record_type'], 'knowledge')
        self.assertFalse(items[0]['resume_display'])
        self.assertFalse(items[0]['visitor_ai'])
        self.assertIsNone(draft.get_workspace('fiction-story').get('story_entry_key'))
        self.assertEqual(result['proposal']['state'], 'accepted')

    def test_sql_overlay_precision_clear_refuses_before_staging_and_keeps_source_and_proposal(self):
        from unittest.mock import Mock
        from services.resume_intake_repository import SqlIntakeUnitOfWork
        for field in ('issue_date_precision','expiration_date_precision'):
            with self.subTest(field=field):
                service,catalog,draft=build_service();owner='synthetic-precision-clear'
                service.submit(owner,{'type':'add_submission','request_id':str(uuid4()),'items':[{
                    'client_key':'credential','record_type':'credential','values':{'name':'Design Practitioner',
                    'issuer':'Original Institute','completion_status':'completed','issue_date':'2022-06-15',
                    'expiration_date':'2027-06-15'}}]})
                changed={'name':'Design Practitioner','issuer':'Corrected Institute'}
                receipt=service.submit(owner,{'type':'add_submission','request_id':str(uuid4()),'items':[{
                    'client_key':'correction','record_type':'credential','values':changed,'explicit_clears':[field]}]})
                proposal=receipt['proposals'][0]
                before=service.get_workspace(owner);canonical=catalog.list_items(owner)
                unit=SqlIntakeUnitOfWork(Mock());service.repository.unit_of_work=lambda draft_service, **kwargs:unit
                with self.assertRaisesRegex(ResumeIntakeValidationError,'input is kept'):
                    service.decide(owner,{'request_id':str(uuid4()),'proposal_key':proposal['proposal_key'],
                        'decision':'accept','confirmed_values':changed})
                self.assertEqual(unit.intents,[]);self.assertEqual(unit.repository.mock_calls,[])
                self.assertEqual(service.get_workspace(owner),before)
                self.assertEqual(catalog.list_items(owner),canonical)

    def test_nonpersonal_story_refuses_without_losing_proposal_or_creating_fact(self):
        service, catalog, draft = build_service()
        receipt = service.submit('fiction-story', {'request_id': str(uuid4()), 'text': 'I repair radios.'})
        with self.assertRaises(ResumeIntakeValidationError):
            service.decide('fiction-story', {'request_id': str(uuid4()),
                'proposal_key': receipt['proposals'][0]['proposal_key'], 'decision': 'accept',
                'confirmed_values': {'record_type': 'knowledge', 'title': 'Radios',
                                     'wording': 'I repair radios.', 'classification': 'professional'}})
        self.assertEqual(catalog.list_items('fiction-story'), [])
        self.assertEqual(len(service.get_workspace('fiction-story')['pending_proposals']), 1)


class IntakeConcurrencyTests(unittest.TestCase):
    def test_working_set_and_held_document_submission_finish_after_provider_release(self):
        from contextlib import contextmanager
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_sources import extracted_pipeline

        shared, owner = SharedMvp1Fixture(), "fictional-intake-lock-order"
        repository = InMemoryResumeIntakeRepository()
        words = "Experience\nEngineer at Fictional Orchard\n"
        entered, released, read_attempted, read_owned = (threading.Event() for _ in range(4))
        adapter = DeterministicFakeExtractionAdapter([{
            "record_type": "role", "values": {
                "role_title": "Engineer", "employer_name": "Fictional Orchard",
            }, "quote": "Engineer at Fictional Orchard", "outcome": "new", "confidence": "certain",
        }])
        provider = adapter._provider

        def held_provider(request, **kwargs):
            entered.set()
            if not released.wait(6):
                raise AssertionError("The bounded fake organizer was not released")
            return provider(request, **kwargs)

        adapter._provider = held_provider
        service = ResumeIntakeService(
            repository=repository, draft_service=shared.draft, policy=selected_policy_for_tests(),
            document_pipeline=extracted_pipeline(words), extraction_adapter=adapter,
        )
        original_guard = repository.owner_guard

        @contextmanager
        def observed_guard(member):
            reader = threading.current_thread().name == "fictional-working-set"
            if reader:
                read_attempted.set()
            with original_guard(member):
                if reader:
                    read_owned.set()
                yield

        repository.owner_guard = observed_guard
        results, errors = {}, []

        def submit():
            try:
                results["submission"] = service.submit(owner, {
                    "request_id": str(uuid4()), "attachments": [{
                        "client_key": "document", "kind": "document",
                        "declared_content_type": "text/plain", "filename": "fictional-resume.txt",
                    }],
                }, files={"document": FakeUpload("text/plain", words.encode(), "fictional-resume.txt")})
            except BaseException as error:
                errors.append(error)

        def read():
            try:
                results["working_set"] = service.working_set(owner)
            except BaseException as error:
                errors.append(error)

        producer = threading.Thread(target=submit, daemon=True, name="fictional-submission")
        reader = threading.Thread(target=read, daemon=True, name="fictional-working-set")
        producer.start()
        try:
            self.assertTrue(entered.wait(3), "The real submit path did not reach its fake organizer")
            reader.start()
            self.assertTrue(read_attempted.wait(2), "The real working-set read was not scheduled")
            # On the broken path the reader owns intake while waiting on draft;
            # on the corrected path it waits for intake before acquiring draft.
            read_owned.wait(.2)
            reader.join(.5)
            read_completed_while_provider_held = not reader.is_alive()
        finally:
            released.set()
        producer.join(3)
        reader.join(3)
        self.assertFalse(producer.is_alive(), "Submission deadlocked after its provider returned")
        self.assertFalse(reader.is_alive(), "Working-set refresh deadlocked with submission")
        self.assertEqual(errors, [])
        self.assertTrue(results["submission"]["persisted"])
        self.assertIsInstance(results["working_set"]["sections"], list)
        self.assertTrue(read_completed_while_provider_held,
                        "A working-set read must not wait for the organizer provider")
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(shared.canonical.list_items(owner), [])


class GuideProviderConcurrencyMatrixTests(unittest.TestCase):
    """Real memory services/stores, held fake transport, no private-lock spies."""
    DEADLINE = 3.0

    def _thread(self, name, call):
        result = {'done': threading.Event()}
        def run():
            try:
                result['value'] = call()
            except BaseException as error:
                result['error'] = error
            finally:
                result['done'].set()
        result['thread'] = threading.Thread(target=run, name=name, daemon=True)
        result['thread'].start()
        return result

    def _join(self, actors, seconds=None):
        until = time.monotonic() + (self.DEADLINE if seconds is None else seconds)
        for actor in actors:
            actor['thread'].join(max(0, until - time.monotonic()))
        return [actor['thread'].name for actor in actors if actor['thread'].is_alive()]

    def _fixture(self, mode):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from services.resume_guide_service import ResumeGuideService
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_sources import extracted_pipeline
        shared, owner = SharedMvp1Fixture(), 'matrix-owner-a'
        repository = InMemoryResumeIntakeRepository()
        words = 'Experience\nEngineer at Fictional New Place\n'
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role', 'values': {
            'role_title': 'Engineer', 'employer_name': 'Fictional New Place'},
            'quote': 'Engineer at Fictional New Place', 'outcome': 'new', 'confidence': 'certain'}])
        service = ResumeIntakeService(repository=repository, draft_service=shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(words), extraction_adapter=adapter)
        role = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'values': {'role_title': 'Existing engineer', 'employer_name': 'Fictional Existing Place'}})['record_key']
        skill_key = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'skill',
            'values': {'name': 'Existing fictional skill'}})['record_key']
        shared.seed_publication(owner, [(role, True, False)])
        pending = service.submit(owner, {'request_id': str(uuid4()), 'text': 'I restore fictional radios.'})
        proposal = pending['proposals'][0]['proposal_key']
        request = {'request_id': str(uuid4()), 'attachments': [{'client_key': 'document', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'fictional-resume.txt'}]}
        def upload(member, payload):
            return service.submit(member, payload, files={'document': FakeUpload('text/plain', words.encode(), 'fictional-resume.txt')})
        source_key = None
        requests = {owner: request, 'matrix-owner-b': request}
        if mode == 'organize_source':
            adapter.fail_with = 'provider_unavailable'
            initial = upload(owner, request)
            source_key = initial['submission']['source_keys'][0]
            request = {'request_id': str(uuid4()), 'source_key': source_key, 'mode': 'retry'}
            other = upload('matrix-owner-b', {**requests[owner], 'request_id': str(uuid4())})
            requests = {owner: request, 'matrix-owner-b': {'request_id': str(uuid4()),
                'source_key': other['submission']['source_keys'][0], 'mode': 'retry'}}
            adapter.fail_with = None
        entered, released, two_entered = threading.Event(), threading.Event(), threading.Event()
        dispatches = []
        provider = adapter._provider
        def held(request, **kwargs):
            dispatches.append(threading.current_thread().name)
            entered.set()
            if len(dispatches) == 2:
                two_entered.set()
            if not released.wait(20):
                raise AssertionError('Test never released its bounded fake provider')
            return provider(request, **kwargs)
        adapter._provider = held
        self.addCleanup(released.set)
        def invoke(member=owner):
            return upload(member, requests[member]) if mode == 'submit' else service.organize_source(member, requests[member])
        return dict(shared=shared, service=service, owner=owner, role=role, skill=skill_key,
            proposal=proposal, guide=ResumeGuideService(repository), source_key=source_key,
            request=request, invoke=invoke, entered=entered, released=released, dispatches=dispatches, two_entered=two_entered)

    def _start(self, case):
        producer = self._thread('matrix-provider-a', case['invoke'])
        self.assertTrue(case['entered'].wait(self.DEADLINE), 'Actual service must reach the held fake provider')
        return producer

    def _finish_provider(self, case, producer, *, changed=False):
        case['released'].set()
        self.assertEqual(self._join([producer]), [], 'Provider finalization must have a hard deadline')
        if changed and 'error' in producer:
            self.assertIsInstance(producer['error'], (ResumeIntakeConflictError, ResumeIntakeNotFoundError))
        else:
            self.assertNotIn('error', producer, repr(producer.get('error')))

    def _read_matrix(self, mode):
        case = self._fixture(mode)
        s, p, owner = case['service'], case['shared'].publication, case['owner']
        producer = self._start(case)
        reads = {
            'guide_state': lambda: case['guide'].get_state(owner),
            'first_arrival_existing': lambda: case['guide'].get_first_arrival(owner,
                read_content=lambda member: bool(case['shared'].draft.get_workspace(member)['items'])),
            'first_arrival_new_member': lambda: case['guide'].get_first_arrival('matrix-new-member',
                read_content=lambda member: bool(case['shared'].draft.get_workspace(member)['items'])),
            'working_set': lambda: s.working_set(owner),
            'basis': lambda: s.guide_publication_basis(owner, s.working_set(owner), p),
            'references': lambda: s.guide_reference_view(owner, s.working_set(owner)),
            'provenance': lambda: p.read_display_selection_provenance(owner, [case['role']]),
            'publication_read_review': lambda: p.read_review_for_owner(owner),
            'publication_explicit_review': lambda: p.review_for_owner(owner),
            'owner_preview': lambda: p.owner_preview(owner),
            'guest_snapshot': lambda: p.guest_read(slug='g-alex'),
            'other_owner_create': lambda: case['shared'].canonical.create_private('matrix-owner-b',
                {'command_id': str(uuid4()), 'record_type': 'skill', 'values': {'name': 'Other owner skill'}}),
        }
        actors = {name: self._thread('matrix-'+name, call) for name, call in reads.items()}
        try:
            blocked = self._join(list(actors.values()))
            errors = {name: repr(actor['error']) for name, actor in actors.items() if 'error' in actor}
        finally:
            case['released'].set()
        # Finish all threads against one further deadline, not N sequential waits.
        unfinished = self._join([producer, *actors.values()])
        self.assertEqual(blocked, [], 'Readers/other owner create must finish BEFORE provider release')
        self.assertEqual(unfinished, [], 'No thread may survive the finalization deadline')
        self.assertEqual(errors, {})
        self.assertNotIn('error', producer, repr(producer.get('error')))
        self.assertTrue(actors['first_arrival_new_member']['value']['eligible'])
        self.assertEqual(len(case['dispatches']), 1)

    def test_held_submit_all_guide_reads_and_other_owner_create_finish_before_release(self):
        self._read_matrix('submit')

    def test_held_existing_organize_all_guide_reads_and_other_owner_create_finish_before_release(self):
        self._read_matrix('organize_source')

    def _mutation(self, case, kind):
        s, shared, owner = case['service'], case['shared'], case['owner']
        if kind == 'hide_show':
            result = None
            for hidden in (True, False):
                item = s.working_item(owner, case['role'])
                result = s.set_guide_visibility(owner, {'request_id': str(uuid4()), 'item_ref': item['item_ref'],
                    'hidden': hidden, 'expected_working_set_token': s.working_set(owner)['working_set_token'],
                    'expected_item_revision': item['saved_revision']})
            return result
        if kind == 'references':
            return s.set_guide_references(owner, {'request_id': str(uuid4()), 'kind': 'highlights',
                'item_ref': None, 'references': [], 'expected_working_set_token': s.working_set(owner)['working_set_token']})
        if kind == 'canonical':
            return shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'skill',
                'values': {'name': 'Manual mutation during provider'}})
        if kind == 'manual_draft':
            item = shared.canonical.get_item(owner, case['role'])
            return shared.draft.commit(owner, {'type': 'save_item', 'request_id': str(uuid4()),
                'record_key': case['role'], 'record_type': 'role',
                'expected_content_token': item['content_token'], 'expected_access_revision': item['access_revision'],
                'expected_draft_version': shared.draft.get_workspace(owner)['draft_version'],
                'values': {'summary': 'Manual words must win over the held provider.'}})
        raise AssertionError(kind)

    def _command_matrix(self, mode):
        for kind in ('hide_show', 'references', 'canonical', 'manual_draft'):
            with self.subTest(mode=mode, command=kind):
                case = self._fixture(mode)
                producer = self._start(case)
                actor = self._thread('matrix-'+kind, lambda: self._mutation(case, kind))
                try:
                    blocked = self._join([actor])
                finally:
                    case['released'].set()
                unfinished = self._join([producer, actor])
                self.assertEqual(blocked, [], 'Member commands must not wait for model work')
                self.assertEqual(unfinished, [])
                self.assertNotIn('error', actor, repr(actor.get('error')))
                if 'error' in producer:
                    self.assertIsInstance(producer['error'], ResumeIntakeConflictError)
                else:
                    self.assertTrue(producer['value']['success'])

    def test_held_submit_hide_show_reference_manual_and_canonical_commands_do_not_wait(self):
        self._command_matrix('submit')

    def test_held_existing_organize_hide_show_reference_manual_and_canonical_commands_do_not_wait(self):
        self._command_matrix('organize_source')

    def test_two_owners_reach_fake_providers_in_parallel(self):
        for mode in ('submit', 'organize_source'):
            with self.subTest(mode=mode):
                case = self._fixture(mode)
                first = self._start(case)
                second = self._thread('matrix-provider-b', lambda: case['invoke']('matrix-owner-b'))
                try:
                    both_entered = case['two_entered'].wait(self.DEADLINE)
                finally:
                    case['released'].set()
                self.assertEqual(self._join([first, second]), [])
                self.assertTrue(both_entered, 'Owner B must dispatch while owner A provider is held')
                self.assertNotIn('error', first, repr(first.get('error')))
                self.assertNotIn('error', second, repr(second.get('error')))

    def test_identical_inflight_request_waits_then_replays_without_second_dispatch(self):
        for mode in ('submit', 'organize_source'):
            with self.subTest(mode=mode):
                case = self._fixture(mode)
                first = self._start(case)
                scheduled = threading.Event()
                def replay():
                    scheduled.set()
                    return case['invoke']()
                second = self._thread('matrix-identical-replay', replay)
                try:
                    self.assertTrue(scheduled.wait(self.DEADLINE))
                    second['done'].wait(.1)
                    self.assertEqual(len(case['dispatches']), 1)
                finally:
                    case['released'].set()
                self.assertEqual(self._join([first, second]), [])
                self.assertNotIn('error', first, repr(first.get('error')))
                self.assertNotIn('error', second, repr(second.get('error')))
                self.assertEqual(len(case['dispatches']), 1)
                self.assertTrue(second['value']['replayed'])
                self.assertEqual(first['value']['request_digest'], second['value']['request_digest'])

    def test_late_provider_result_cannot_reapply_over_manual_mutation_or_purged_source(self):
        # An unrelated new canonical fact no longer invalidates the paid result
        # (N1); a purged source still refuses. Matched-target edits are proven
        # in ProcessingFenceScopeTests.
        for mode, mutation in (('submit', 'canonical'), ('organize_source', 'canonical'), ('organize_source', 'purge')):
            with self.subTest(mode=mode, mutation=mutation):
                case = self._fixture(mode)
                producer = self._start(case)
                def change():
                    if mutation == 'purge':
                        return case['service'].purge_source(case['owner'],
                            {'request_id': str(uuid4()), 'source_key': case['source_key']})
                    return self._mutation(case, mutation)
                actor = self._thread('matrix-stale-fence-mutation', change)
                try:
                    blocked = self._join([actor])
                finally:
                    case['released'].set()
                self.assertEqual(self._join([producer, actor]), [])
                self.assertEqual(blocked, [], 'Mutation/purge must complete before provider release')
                self.assertNotIn('error', actor, repr(actor.get('error')))
                if mutation == 'purge':
                    self.assertIsInstance(producer.get('error'), (ResumeIntakeConflictError, ResumeIntakeNotFoundError),
                        'A purged source must refuse the stale prepared result rather than force apply')
                else:
                    self.assertNotIn('error', producer, 'An unrelated new fact must not discard the paid result')
                    self.assertTrue(producer['value']['success'])
                snapshot = case['service'].repository.load_owner(case['owner'])
                if mutation == 'purge':
                    self.assertEqual(snapshot['sources'][case['source_key']]['state'], 'purged')
                    self.assertIsNone(snapshot['sources'][case['source_key']]['text'])
                else:
                    self.assertTrue(any(row['values'].get('name') == 'Manual mutation during provider'
                        for row in case['shared'].canonical.list_items(case['owner'])))

    def test_publish_and_failed_confirm_during_each_provider_preserve_successful_publish(self):
        from unittest.mock import patch
        from services.resume_draft_service import ResumeDraftUnavailableError
        for mode in ('submit', 'organize_source'):
            with self.subTest(mode=mode):
                case = self._fixture(mode)
                shared, owner, s = case['shared'], case['owner'], case['service']
                reviewed = shared.publication.review_for_owner(owner, {}).reviewed
                payload = {'type': 'publish', 'request_id': str(uuid4()), 'profile_identity': None,
                    'reviewed_digest': reviewed.digest, 'candidate': shared.publication.publish_candidate(reviewed)}
                command = {'request_id': str(uuid4()), 'proposal_key': case['proposal'], 'decision': 'accept',
                    'guide_review': True, 'guide_section': 'story', 'confirmed_values': {'record_type': 'knowledge',
                        'title': 'My Story', 'wording': 'I restore fictional radios.', 'classification': 'personal'}}
                saved, confirm_started = threading.Event(), threading.Event()
                original_save, original_commit = shared.publication.repository.save_owner, shared.draft.commit
                def observed_save(member, snapshot):
                    original_save(member, snapshot)
                    if threading.current_thread().name == 'matrix-publish':
                        saved.set()
                        if not confirm_started.wait(self.DEADLINE):
                            raise AssertionError('Confirm did not attempt during the real publication transaction')
                def fail_binding(member, operation):
                    if operation['type'] == 'bind_story':
                        raise ResumeDraftUnavailableError('Fictional bind failure')
                    return original_commit(member, operation)
                def confirm():
                    if not saved.wait(self.DEADLINE):
                        raise AssertionError('Publisher never reached its actual store commit')
                    confirm_started.set()
                    return s.decide(owner, command)
                producer = self._start(case)
                with patch.object(shared.publication.repository, 'save_owner', side_effect=observed_save), \
                        patch.object(shared.draft, 'commit', side_effect=fail_binding):
                    publisher = self._thread('matrix-publish', lambda: shared.publication.commit(owner, payload))
                    failed = self._thread('matrix-failed-confirm', confirm)
                    try:
                        blocked = self._join([publisher, failed])
                    finally:
                        case['released'].set()
                    unfinished = self._join([producer, publisher, failed])
                self.assertEqual(blocked, [], 'Publish and failed confirm must complete before provider release')
                self.assertEqual(unfinished, [])
                self.assertNotIn('error', publisher, repr(publisher.get('error')))
                self.assertIsInstance(failed.get('error'), ResumeIntakeUnavailableError)
                snapshot = shared.publication.repository.load_owner(owner)
                self.assertIn(payload['request_id'], snapshot['receipts'])
                self.assertEqual(snapshot['publication_revision'], 2)
                self.assertEqual(s.repository.load_owner(owner)['proposals'][case['proposal']]['state'], 'pending')
                self.assertEqual(set(snapshot['publications'][snapshot['current_revision']]['display']), {case['role']})


class InMemoryStoreLockOrderTests(unittest.TestCase):
    """One in-memory store order across owners and paths.

    Owner guard first, then media lifecycle, bound media, draft store and
    intake store. Each case parks a second owner's real command at the exact
    point where it holds an earlier lock, then proves both finish by a hard
    deadline (the old orders deadlocked here) and nothing is lost.
    """
    DEADLINE = 3.0

    def _thread(self, name, call):
        result = {}
        def run():
            try:
                result['value'] = call()
            except BaseException as error:
                result['error'] = error
        result['thread'] = threading.Thread(target=run, name=name, daemon=True)
        result['thread'].start()
        return result

    def _join(self, *actors):
        until = time.monotonic() + self.DEADLINE
        for actor in actors:
            actor['thread'].join(max(0, until - time.monotonic()))
        return [actor['thread'].name for actor in actors if actor['thread'].is_alive()]

    def _park(self, target, attribute, thread_name, parked, go):
        original = getattr(target, attribute)
        def parked_call(*args, **kwargs):
            if threading.current_thread().name == thread_name:
                parked.set()
                if not go.wait(self.DEADLINE):
                    raise AssertionError('The parked command was never released')
            return original(*args, **kwargs)
        setattr(target, attribute, parked_call)
        self.addCleanup(go.set)

    def _placement(self, shared, owner):
        from services.resume_media_repository import MediaPlacement, RequestReceipt, provenance_label_for
        from services.resume_media_service import centered_slot_crop
        photo = shared.seed_photo(owner)
        placement = MediaPlacement('experience_support', 'owner_photo', photo.source_id, photo.version, photo.digest,
            centered_slot_crop(slot='experience_support', width=photo.width, height=photo.height),
            alt_text='Synthetic test landscape', provenance_label=provenance_label_for(source_kind='owner_photo'))
        receipt = RequestReceipt(owner, 'add', str(uuid4()), 'b' * 64, '{}')
        return placement, receipt

    def test_publish_and_another_owners_media_read_finish_in_one_store_order(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared, owner, other = SharedMvp1Fixture(), 'store-order-publisher', 'store-order-reader'
        role = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'values': {'role_title': 'Fictional engineer', 'employer_name': 'Fictional Place'}})['record_key']
        shared.seed_publication(owner, [(role, True, False)], slug='store-order-a')
        reviewed = shared.publication.review_for_owner(owner, {}).reviewed
        payload = {'type': 'publish', 'request_id': str(uuid4()), 'profile_identity': None,
            'reviewed_digest': reviewed.digest, 'candidate': shared.publication.publish_candidate(reviewed)}
        parked, go = threading.Event(), threading.Event()
        # The reader holds the bound-media lock and is about to take the draft store.
        self._park(shared.draft.repository, 'load_owner', 'store-order-media-read', parked, go)
        reader = self._thread('store-order-media-read', lambda: shared.media.media_repository.get_draft(other))
        self.assertTrue(parked.wait(self.DEADLINE))
        publisher = self._thread('store-order-publish', lambda: shared.publication.commit(owner, payload))
        publisher['thread'].join(.3)
        go.set()
        self.assertEqual(self._join(reader, publisher), [], 'Publish and a media read must not deadlock')
        self.assertNotIn('error', reader, repr(reader.get('error')))
        self.assertNotIn('error', publisher, repr(publisher.get('error')))
        self.assertIn(payload['request_id'], shared.publication.repository.load_owner(owner)['receipts'])

    def test_guide_hide_with_media_and_another_owners_media_command_finish_in_one_store_order(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared, owner, other = SharedMvp1Fixture(), 'store-order-guide', 'store-order-media'
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests())
        role = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'values': {'role_title': 'Fictional engineer', 'employer_name': 'Fictional Place'}})['record_key']
        shared.seed_publication(owner, [(role, True, False)], slug='store-order-g')
        own_placement, own_receipt = self._placement(shared, owner)
        shared.media.media_repository.commit_draft(owner_id=owner,
            expected_version=shared.media.media_repository.get_draft(owner).version,
            placements=(own_placement,), receipt=own_receipt)
        other_placement, other_receipt = self._placement(shared, other)
        parked, go = threading.Event(), threading.Event()
        # The media command holds the media lifecycle lock and is about to take the draft store.
        self._park(shared.draft.repository, 'commit_owner_command', 'store-order-media-command', parked, go)
        media = self._thread('store-order-media-command', lambda: shared.media.media_repository.commit_draft(
            owner_id=other, expected_version=0, placements=(other_placement,), receipt=other_receipt))
        self.assertTrue(parked.wait(self.DEADLINE))
        item = service.working_item(owner, role)
        token = service.working_set(owner)['working_set_token']

        def route_working_set(member):
            # As the Guide route does: the working set carries the publish basis,
            # which reads this owner's draft media inside the command.
            working = service.working_set(member)
            working['publication'] = service.guide_publication_basis(member, working, shared.publication)
            return working

        hide = self._thread('store-order-hide', lambda: service.set_guide_visibility(owner, {
            'request_id': str(uuid4()), 'item_ref': item['item_ref'], 'hidden': True,
            'expected_working_set_token': token, 'expected_item_revision': item['saved_revision']},
            read_working_set=route_working_set))
        hide['thread'].join(.3)
        go.set()
        self.assertEqual(self._join(media, hide), [], 'A Guide command and a media command must not deadlock')
        self.assertNotIn('error', media, repr(media.get('error')))
        self.assertNotIn('error', hide, repr(hide.get('error')))
        self.assertEqual(len(shared.media.media_repository.get_draft(other).placements), 1)

    def test_recording_finalization_and_a_guarded_owner_write_never_lose_either_receipt(self):
        transcriber = RecordingTranscriber('I restored a fictional radio.')
        service, _catalog, _draft = build_service(transcriber=transcriber)
        owner, recording_id, add_id = 'store-order-recording', str(uuid4()), str(uuid4())
        parked, go = threading.Event(), threading.Event()
        # Finalization has reloaded the owner after the provider and is about to save.
        self._park(service.repository, 'save_owner', 'store-order-transcribe', parked, go)
        recording = self._thread('store-order-transcribe', lambda: service.transcribe_recording(owner,
            FakeUpload('audio/wav', wav_bytes()), {'request_id': recording_id, 'client_key': 'mic-1',
                'duration_seconds': 3.0}))
        self.assertTrue(parked.wait(self.DEADLINE))
        add = self._thread('store-order-add', lambda: service.submit(owner, {'type': 'add_submission',
            'request_id': add_id, 'items': [{'client_key': 's1', 'record_type': 'skill',
                'values': skill('Requirements management')}]}))
        add['thread'].join(.3)
        add_waited = add['thread'].is_alive()
        go.set()
        self.assertEqual(self._join(recording, add), [])
        self.assertNotIn('error', recording, repr(recording.get('error')))
        self.assertNotIn('error', add, repr(add.get('error')))
        self.assertTrue(add_waited, 'An owner write must wait for the recording finalization it would overwrite')
        receipts = service.repository.load_owner(owner)['receipts']
        self.assertIn(recording_id, receipts)
        self.assertIn(add_id, receipts)
        self.assertEqual(len(transcriber.calls), 1)


class ProcessingFenceScopeTests(unittest.TestCase):
    """N1: a prepared result is fenced on what it depends on, not on unrelated work.

    The provider is held while a real member command runs, then released. An
    unrelated change must let the paid result apply; an edit to the matched
    target must report stale with nothing forced and the input kept.
    """
    DEADLINE = 3.0
    WORDS = 'Experience\nEngineer at Fictional New Place\n'

    def _case(self, mode):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_sources import extracted_pipeline
        shared, owner = SharedMvp1Fixture(), 'fence-owner'
        role = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Fictional New Place'}})['record_key']
        other = shared.canonical.create_private(owner, {'command_id': str(uuid4()), 'record_type': 'skill',
            'values': {'name': 'Unrelated fictional skill'}})['record_key']
        shared.seed_publication(owner, [(role, True, False), (other, True, False)], slug='fence-a')
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role',
            'values': {'location_text': 'Fictional Town'}, 'outcome': 'additional_detail',
            'match_reference': role, 'quote': 'Engineer at Fictional New Place', 'confidence': 'certain'}])
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(self.WORDS),
            extraction_adapter=adapter, matching_exclusions=lambda member: set())
        pending = service.submit(owner, {'request_id': str(uuid4()), 'text': 'I restore fictional radios.'})
        unrelated_proposal = pending['proposals'][0]['proposal_key']
        upload = {'request_id': str(uuid4()), 'attachments': [{'client_key': 'document', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'fictional-resume.txt'}]}
        def send(payload):
            return service.submit(owner, payload, files={'document': FakeUpload('text/plain', self.WORDS.encode(),
                'fictional-resume.txt')})
        source_key = None
        if mode == 'organize_source':
            adapter.fail_with = 'provider_unavailable'
            source_key = send(upload)['submission']['source_keys'][0]
            adapter.fail_with = None
            request = {'request_id': str(uuid4()), 'source_key': source_key, 'mode': 'retry'}
            invoke = lambda: service.organize_source(owner, request)
        else:
            invoke = lambda: send(upload)
        entered, released, dispatches = threading.Event(), threading.Event(), []
        provider = adapter._provider
        def held(request, **kwargs):
            dispatches.append(1)
            entered.set()
            if not released.wait(20):
                raise AssertionError('The bounded fake provider was never released')
            return provider(request, **kwargs)
        adapter._provider = held
        self.addCleanup(released.set)
        return dict(shared=shared, service=service, owner=owner, role=role, other=other, invoke=invoke,
                    unrelated_proposal=unrelated_proposal, entered=entered, released=released,
                    dispatches=dispatches, source_key=source_key)

    def _edit(self, case, key, summary):
        shared = case['shared']
        item = shared.canonical.get_item(case['owner'], key)
        return shared.draft.commit(case['owner'], {'type': 'save_item', 'request_id': str(uuid4()),
            'record_key': key, 'record_type': item['record_type'],
            'expected_content_token': item['content_token'], 'expected_access_revision': item['access_revision'],
            'expected_draft_version': shared.draft.get_workspace(case['owner'])['draft_version'],
            'values': {'summary': summary}})

    def _mutate(self, case, kind):
        service, shared, owner = case['service'], case['shared'], case['owner']
        if kind == 'hide_then_show':
            for hidden in (True, False):
                item = service.working_item(owner, case['other'])
                service.set_guide_visibility(owner, {'request_id': str(uuid4()), 'item_ref': item['item_ref'],
                    'hidden': hidden, 'expected_working_set_token': service.working_set(owner)['working_set_token'],
                    'expected_item_revision': item['saved_revision']})
        elif kind == 'references':
            service.set_guide_references(owner, {'request_id': str(uuid4()), 'kind': 'highlights', 'item_ref': None,
                'references': [], 'expected_working_set_token': service.working_set(owner)['working_set_token']})
        elif kind == 'publish':
            reviewed = shared.publication.review_for_owner(owner, {}).reviewed
            shared.publication.commit(owner, {'type': 'publish', 'request_id': str(uuid4()), 'profile_identity': None,
                'reviewed_digest': reviewed.digest, 'candidate': shared.publication.publish_candidate(reviewed)})
        elif kind == 'unrelated_decision':
            service.decide(owner, {'request_id': str(uuid4()), 'proposal_key': case['unrelated_proposal'],
                'decision': 'reject'})
        elif kind == 'unrelated_edit':
            self._edit(case, case['other'], 'Edited while organizing.')
        elif kind == 'source_row_change':
            # A direct change to the organized source's own row (a version
            # bump), with no epoch or bound-proposal change: only the fence's
            # source component can see it.
            with service.repository.owner_guard(owner):
                snapshot = service.repository.load_owner(owner)
                row = snapshot['sources'][case['source_key']]
                row['version'] = int(row.get('version') or 1) + 1
                service.repository.save_owner(owner, snapshot)
        elif kind == 'matched_target_edit':
            # The saved fact the organized detail was matched against changes.
            entry = shared.policy.get_entry(owner, case['role'])['entry']
            shared.policy.commit(owner, {'type': 'edit', 'request_id': str(uuid4()), 'entry_key': case['role'],
                'expected_content_version': entry['content_version'],
                'values': {'role_title': 'Engineer', 'employer_name': 'Fictional New Place',
                           'location_text': 'Edited Town'}})
        else:
            raise AssertionError(kind)

    def _run(self, mode, kind):
        case = self._case(mode)
        result = {}
        def produce():
            try:
                result['value'] = case['invoke']()
            except BaseException as error:
                result['error'] = error
        producer = threading.Thread(target=produce, name='fence-provider', daemon=True)
        producer.start()
        self.assertTrue(case['entered'].wait(self.DEADLINE), 'The real path must reach its held fake provider')
        try:
            self._mutate(case, kind)
        finally:
            case['released'].set()
        producer.join(self.DEADLINE)
        self.assertFalse(producer.is_alive())
        self.assertEqual(len(case['dispatches']), 1)
        return case, result

    def test_unrelated_private_work_during_organizing_lets_the_paid_result_apply(self):
        for mode in ('submit', 'organize_source'):
            for kind in ('hide_then_show', 'references', 'publish', 'unrelated_decision', 'unrelated_edit'):
                with self.subTest(mode=mode, change=kind):
                    case, result = self._run(mode, kind)
                    self.assertNotIn('error', result, repr(result.get('error')))
                    self.assertTrue(result['value']['success'])
                    stored = case['service'].repository.load_owner(case['owner'])
                    bound = [row for row in stored['proposals'].values()
                             if row.get('target_key') == case['role'] and row['state'] == 'pending']
                    self.assertTrue(bound, 'The organized detail for the matched role must be kept')

    def test_a_change_to_the_organized_source_row_during_organizing_refuses_the_stale_result(self):
        case, result = self._run('organize_source', 'source_row_change')
        self.assertIsInstance(result.get('error'), ResumeIntakeConflictError, result)
        self.assertEqual(result['error'].error_code, 'changed')
        stored = case['service'].repository.load_owner(case['owner'])
        self.assertFalse([row for row in stored['proposals'].values() if row.get('target_key') == case['role']])

    def _second_source(self, case, payload_extra=None):
        upload = {'request_id': str(uuid4()), 'attachments': [{'client_key': 'document', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'second-fictional-resume.txt'}], **(payload_extra or {})}
        return case['service'].submit(case['owner'], upload, files={'document': FakeUpload('text/plain',
            b'Second fictional file bytes', 'second-fictional-resume.txt')})['submission']['source_keys'][0]

    def test_a_second_organize_of_the_same_source_under_a_new_request_id_never_dispatches_twice(self):
        # "Try organizing again" in two tabs (an unavailable source) and the
        # first organize after a source-only receipt (a not_started source).
        from services.resume_intake_service import ResumeIntakeBusyError
        for initial in ('unavailable', 'not_started'):
            with self.subTest(initial=initial):
                case = self._case('organize_source')
                service, owner, source_key = case['service'], case['owner'], case['source_key']
                if initial == 'not_started':
                    case['released'].set()
                    source_key = self._second_source(case, {'source_only': True})
                    case['released'].clear(); case['entered'].clear(); case['dispatches'].clear()
                    first = {'request_id': str(uuid4()), 'source_key': source_key, 'mode': 'retry'}
                    invoke = lambda: service.organize_source(owner, first)
                else:
                    invoke = case['invoke']
                result = {}
                def produce():
                    try:
                        result['value'] = invoke()
                    except BaseException as error:
                        result['error'] = error
                producer = threading.Thread(target=produce, daemon=True)
                producer.start()
                self.assertTrue(case['entered'].wait(self.DEADLINE))
                second = {'request_id': str(uuid4()), 'source_key': source_key, 'mode': 'retry'}
                try:
                    with self.assertRaises(ResumeIntakeBusyError) as busy:
                        service.organize_source(owner, second)
                    self.assertEqual(busy.exception.code, 'request_in_progress')
                finally:
                    case['released'].set()
                producer.join(self.DEADLINE)
                self.assertNotIn('error', result, repr(result.get('error')))
                self.assertEqual(service.organize_source(owner, second)['outcome'], 'already_organized')
                self.assertEqual(len(case['dispatches']), 1, 'One paid organize per source')

    def test_organizing_two_different_sources_of_one_owner_proceeds_independently(self):
        case = self._case('organize_source')
        case['released'].set()
        other_key = self._second_source(case, {'source_only': True})
        case['released'].clear(); case['entered'].clear(); case['dispatches'].clear()
        service, owner = case['service'], case['owner']
        results, threads = {}, []
        for name, key in (('first', case['source_key']), ('second', other_key)):
            def run(name=name, key=key):
                try:
                    results[name] = service.organize_source(owner, {'request_id': str(uuid4()), 'source_key': key,
                                                                    'mode': 'retry'})
                except BaseException as error:
                    results[name] = error
            threads.append(threading.Thread(target=run, daemon=True))
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + self.DEADLINE
        while len(case['dispatches']) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        both_dispatched = len(case['dispatches']) == 2
        case['released'].set()
        for thread in threads:
            thread.join(self.DEADLINE)
        self.assertTrue(both_dispatched, 'A different source must not wait on another source')
        self.assertTrue(all(isinstance(value, dict) and value['success'] for value in results.values()), results)

    def test_an_edit_to_the_matched_target_during_organizing_reports_stale_and_forces_nothing(self):
        for mode in ('submit', 'organize_source'):
            with self.subTest(mode=mode):
                case, result = self._run(mode, 'matched_target_edit')
                self.assertIsInstance(result.get('error'), ResumeIntakeConflictError)
                self.assertEqual(result['error'].error_code, 'changed')
                stored = case['service'].repository.load_owner(case['owner'])
                self.assertFalse([row for row in stored['proposals'].values() if row.get('target_key') == case['role']])
                if mode == 'submit':
                    self.assertEqual(result['error'].proposed['attachments'][0]['filename'], 'fictional-resume.txt')
                else:
                    self.assertEqual(stored['sources'][case['source_key']]['state'], 'active')
                self.assertEqual(case['shared'].canonical.get_item(case['owner'], case['role'])['values']['location_text'],
                                 'Edited Town')


class SourceOnlyReceiptTests(unittest.TestCase):
    """Opt-in first document receipt: store and read now, organize later (96c4fd1)."""
    WORDS = 'Experience\nEngineer at Fictional Orchard\n'

    def _service(self):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_sources import extracted_pipeline
        shared = SharedMvp1Fixture()
        adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role', 'values': {
            'role_title': 'Engineer', 'employer_name': 'Fictional Orchard'},
            'quote': 'Engineer at Fictional Orchard', 'outcome': 'new', 'confidence': 'certain'}])
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(self.WORDS),
            extraction_adapter=adapter)
        return service, adapter, shared

    def _send(self, service, owner, request_id, *, source_only=True, extra=None):
        body = {'request_id': request_id, 'attachments': [{'client_key': 'document', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'fictional-resume.txt'}], **(extra or {})}
        if source_only is not None:
            body['source_only'] = source_only
        return service.submit(owner, body, files={'document': FakeUpload('text/plain', self.WORDS.encode(),
            'fictional-resume.txt')})

    def test_source_only_stores_and_reads_the_file_with_no_organizer_dispatch_then_organize_source_follows(self):
        service, adapter, shared = self._service()
        owner, request_id = 'source-only-member', str(uuid4())
        receipt = self._send(service, owner, request_id)
        self.assertTrue(receipt['success'])
        self.assertTrue(receipt['persisted'])
        self.assertEqual(len(adapter.calls), 0, 'A source-only receipt must not dispatch the organizer')
        source_key = receipt['submission']['source_keys'][0]
        self.assertEqual(receipt['message'], 'Your file is saved privately. Organizing comes next.')
        self.assertEqual(receipt['proposals'], [])
        self.assertEqual(receipt['results'][0]['organization']['state'], 'not_started')
        stored = service.repository.load_owner(owner)
        self.assertEqual(stored['sources'][source_key]['state'], 'active')
        self.assertEqual(stored['sources'][source_key]['text'], self.WORDS)
        self.assertEqual(stored['proposals'], {})
        self.assertEqual(shared.canonical.list_items(owner), [])
        replay = self._send(service, owner, request_id)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['submission']['source_keys'], [source_key])
        self.assertEqual(len(adapter.calls), 0)
        organized = service.organize_source(owner, {'request_id': str(uuid4()), 'source_key': source_key,
            'mode': 'retry'})
        self.assertTrue(organized['success'])
        self.assertEqual(len(adapter.calls), 1)
        self.assertTrue(service.repository.load_owner(owner)['proposals'])
        again = service.organize_source(owner, {'request_id': str(uuid4()), 'source_key': source_key,
            'mode': 'retry'})
        self.assertEqual(again['outcome'], 'already_organized')
        self.assertEqual(len(adapter.calls), 1)

    def test_absent_or_false_opt_in_keeps_the_legacy_request_and_digest(self):
        service, adapter, _shared = self._service()
        legacy = self._send(service, 'legacy-member', str(uuid4()), source_only=None)
        self.assertEqual(len(adapter.calls), 1)
        self.assertNotEqual(legacy['message'], 'Your file is saved privately. Organizing comes next.')
        request_id = str(uuid4())
        absent = self._send(service, 'digest-member', request_id, source_only=None)
        explicit_false = self._send(service, 'digest-member', request_id, source_only=False)
        self.assertTrue(explicit_false['replayed'])
        self.assertEqual(absent['request_digest'], explicit_false['request_digest'])

    def test_same_request_id_cannot_switch_between_source_only_and_legacy(self):
        service, adapter, _shared = self._service()
        request_id = str(uuid4())
        self._send(service, 'switch-member', request_id)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self._send(service, 'switch-member', request_id, source_only=None)
        self.assertEqual(caught.exception.error_code, 'idempotency_conflict')
        self.assertEqual(len(adapter.calls), 0)

    def test_malformed_or_mixed_source_only_requests_refuse_before_any_effect(self):
        service, adapter, _shared = self._service()
        owner = 'refused-member'
        for name, kwargs in (('non_boolean', {'source_only': 'yes'}),
                             ('with_text', {'extra': {'text': 'Also this note.'}}),
                             ('with_item', {'extra': {'items': [{'client_key': 's1', 'record_type': 'skill',
                                 'values': {'name': 'Fictional skill'}}]}})):
            with self.subTest(case=name), self.assertRaises(ResumeIntakeValidationError):
                self._send(service, owner, str(uuid4()), **kwargs)
        with self.assertRaises(ResumeIntakeValidationError):
            service.submit(owner, {'request_id': str(uuid4()), 'source_only': True, 'attachments': [
                {'client_key': 'a', 'kind': 'document', 'declared_content_type': 'text/plain', 'filename': 'a.txt'},
                {'client_key': 'b', 'kind': 'document', 'declared_content_type': 'text/plain', 'filename': 'b.txt'}]},
                files={'a': FakeUpload('text/plain', b'One'), 'b': FakeUpload('text/plain', b'Two')})
        self.assertEqual(len(adapter.calls), 0)
        stored = service.repository.load_owner(owner)
        self.assertEqual((stored['sources'], stored['receipts'], stored['proposals']), ({}, {}, {}))

    def test_without_an_organizer_the_source_only_send_is_unavailable_and_keeps_input(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_sources import extracted_pipeline
        shared = SharedMvp1Fixture()
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(self.WORDS))
        with self.assertRaises(ResumeIntakeUnavailableError) as caught:
            self._send(service, 'no-organizer-member', str(uuid4()))
        self.assertEqual(caught.exception.proposed['attachments'][0]['filename'], 'fictional-resume.txt')
        self.assertEqual(service.repository.load_owner('no-organizer-member')['sources'], {})


class ExplicitAddTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"

    def add(self, payload, **kwargs):
        body = {"type": "add_submission", "request_id": str(uuid4()), **payload}
        return self.service.submit(self.owner, body, **kwargs)

    def test_structured_facts_save_privately_and_free_text_stays_unresolved(self):
        receipt = self.add(
            {
                "items": [
                    {"client_key": "r1", "record_type": "role", "values": ROLE_VALUES},
                    {"client_key": "s1", "record_type": "skill", "values": skill("Requirements management")},
                    {"client_key": "s2", "record_type": "skill", "values": skill("Systems engineering")},
                ],
                "text": "One project I worked on involved a cross-team migration.",
            }
        )
        self.assertEqual(receipt["summary"]["saved"], 3)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])
        self.assertEqual(receipt["outcome"], "partial")
        saved = [row for row in receipt["results"] if row["outcome"] == "saved"]
        for row in saved:
            self.assertFalse(row["saved"] is False)
            self.assertEqual(row["display"], "off")
            self.assertEqual(row["visitor_ai"], "off")
        # Only the three explicit facts exist; the free text did not invent one.
        items = self.catalog.list_items(self.owner)
        self.assertEqual(len(items), 3)
        for item in items:
            self.assertFalse(item["resume_display"])
            self.assertFalse(item["visitor_ai"])
        pending = self.service.get_workspace(self.owner)["pending_proposals"]
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0]["requires_member_wording"])

    def test_same_request_replays_and_changed_payload_conflicts(self):
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "s1", "record_type": "skill", "values": skill("MBSE")}],
        }
        first = self.service.submit(self.owner, body)
        replay = self.service.submit(self.owner, body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["request_digest"], first["request_digest"])
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": request_id,
                    "items": [{"client_key": "s1", "record_type": "skill", "values": skill("Different")}],
                },
            )
        self.assertEqual(caught.exception.error_code, "idempotency_conflict")
        self.assertIsNotNone(caught.exception.proposed)

    def test_partial_success_is_truthful_and_preserves_the_member_work(self):
        receipt = self.add(
            {
                "items": [{"client_key": "s1", "record_type": "skill", "values": skill("MBSE")}],
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "application/zip", "filename": "wrong.zip"}
                ],
            },
            files={"d1": FakeUpload("application/zip", b"PK\x03\x04not-really")},
        )
        self.assertEqual(receipt["summary"]["saved"], 1)
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])
        self.assertEqual(receipt["outcome"], "partial")
        failed = next(row for row in receipt["results"] if row["outcome"] == "failed")
        self.assertEqual(failed["code"], "unsupported_type")
        self.assertFalse(failed["saved"])
        self.assertIn("not supported", failed["message"].lower())

    def test_missing_upload_is_a_failed_item_not_a_lost_submission(self):
        receipt = self.add(
            {
                "attachments": [
                    {"client_key": "d1", "kind": "document", "declared_content_type": "text/plain"}
                ]
            }
        )
        self.assertEqual(receipt["outcome"], "failed")
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertFalse(receipt["summary"]["all_saved"])

    def test_document_boundary_records_exact_bytes_it_received(self):
        received = []

        def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
            received.append({"content_type": content_type, "data": admitted})
            from services.my_opportunities.member_import_service import ImportStageOutcome

            trail = (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                        outcome="extracted", reason_code=None, occurred_at=now),)
            return ("Extracted resume text from the attachment.", "extracted", None, False, trail)

        service, _catalog, _draft = build_service(document_pipeline=pipeline)
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "d1", "kind": "document",
                     "declared_content_type": "text/plain", "filename": "resume.txt"}
                ],
            },
            files={"d1": FakeUpload("text/plain", b"Systems Engineer at Example Co")},
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["content_type"], "text/plain")
        self.assertEqual(received[0]["data"], b"Systems Engineer at Example Co")
        self.assertEqual(receipt["summary"]["unresolved"], 1)

    def test_oversized_document_is_refused_before_parsing(self):
        policy = selected_policy_for_tests(max_document_bytes=16)
        service, _catalog, _draft = build_service(policy=policy)
        receipt = service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "d1", "kind": "document", "declared_content_type": "text/plain"}
                ],
            },
            files={"d1": FakeUpload("text/plain", b"x" * 64)},
        )
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertEqual(receipt["results"][0]["code"], "too_large")

    def test_authority_fields_are_rejected(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({"text": "hello", "owner_user_key": "someone-else"})
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({"text": "hello", "visitor_ai": True})

    def test_empty_add_is_rejected(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.add({})


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        first = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r1", "record_type": "role", "values": ROLE_VALUES},
                    {"client_key": "s1", "record_type": "skill", "values": skill("MBSE")},
                ],
            },
        )
        self.assertEqual(first["summary"]["saved"], 2)
        self.role_key = next(
            item["record_key"] for item in self.catalog.list_items(self.owner)
            if item["record_type"] == "role"
        )

    def add_text(self, text):
        return self.service.submit(
            self.owner,
            {"type": "add_submission", "request_id": str(uuid4()), "text": text},
        )

    def test_merely_similar_skill_is_ambiguous_not_a_duplicate(self):
        self.add_text("I am strong in MBSE.")
        self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "s2", "record_type": "skill", "values": skill("mbse")}],
            },
        )
        pending = self.service.get_workspace(self.owner)["pending_proposals"]
        kinds = {row["kind"] for row in pending}
        self.assertIn("ambiguous_match", kinds)
        # Merely-similar wording did not create a second canonical skill.
        skills = [i for i in self.catalog.list_items(self.owner) if i["record_type"] == "skill"]
        self.assertEqual(len(skills), 1)

    def test_changed_employer_for_same_title_is_a_contradiction(self):
        changed = dict(ROLE_VALUES, employer_name="Example Corp")
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r2", "record_type": "role", "values": changed}],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        proposal = receipt["proposals"][0]
        self.assertEqual(proposal["kind"], "contradiction")
        self.assertEqual(proposal["target_key"], self.role_key)
        self.assertEqual(proposal["proposed_values"]["employer_name"], "Example Corp")
        # Canonical wording is untouched until the member decides.
        canonical = next(
            i for i in self.catalog.list_items(self.owner) if i["record_key"] == self.role_key
        )
        self.assertEqual(canonical["values"]["employer_name"], "Northrop Grumman")

    def test_added_detail_to_existing_fact_requires_review(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r3", "record_type": "role",
                     "values": dict(ROLE_VALUES, location_text="Huntsville, Alabama")}
                ],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertEqual(receipt["proposals"][0]["kind"], "additional_detail")
        self.assertEqual(receipt["proposals"][0]["target_key"], self.role_key)

    def test_first_acceptance_saves_a_new_fact_without_a_prior_receipt(self):
        created = self.add_text("Certified Kubernetes Administrator")
        proposal_key = created["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": {
                    "record_type": "credential",
                    "name": "Certified Kubernetes Administrator",
                    "issuer": "The Linux Foundation",
                    "completion_status": "completed",
                    "issue_date": "2024-05-01",
                    "identifier": None,
                    "expiration_date": None,
                    "verification_url": None,
                },
            },
        )
        self.assertEqual(decided["outcome"], "saved")
        self.assertFalse(decided["item"]["resume_display"])
        self.assertFalse(decided["item"]["visitor_ai"])
        credential = next(
            i for i in self.catalog.list_items(self.owner) if i["record_type"] == "credential"
        )
        self.assertEqual(credential["values"]["issuer"], "The Linux Foundation")

    def test_accepting_a_change_routes_through_the_private_draft_overlay(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {"client_key": "r9", "record_type": "role",
                     "values": dict(ROLE_VALUES, summary="Leads requirements management.")}
                ],
            },
        )
        proposal_key = receipt["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal_key,
                "decision": "accept",
                "confirmed_values": dict(ROLE_VALUES, summary="Leads requirements management."),
            },
        )
        self.assertEqual(decided["outcome"], "saved")
        self.assertTrue(decided["item"]["draft_overlay"])
        canonical = next(
            i for i in self.catalog.list_items(self.owner) if i["record_key"] == self.role_key
        )
        self.assertEqual(canonical["values"]["summary"], ROLE_VALUES["summary"])

    def test_rejecting_a_proposal_saves_nothing(self):
        created = self.add_text("Maybe some personal notes.")
        proposal_key = created["proposals"][0]["proposal_key"]
        decided = self.service.decide(
            self.owner,
            {"request_id": str(uuid4()), "proposal_key": proposal_key, "decision": "reject"},
        )
        self.assertEqual(decided["outcome"], "unresolved")
        self.assertIsNone(decided["item"])
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_second_acceptance_of_the_same_proposal_conflicts(self):
        created = self.add_text("Another note")
        proposal_key = created["proposals"][0]["proposal_key"]
        body = {
            "request_id": str(uuid4()),
            "proposal_key": proposal_key,
            "decision": "reject",
        }
        self.service.decide(self.owner, body)
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.decide(self.owner, {**body, "request_id": str(uuid4())})


class SourcePurgeTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        self.receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "I managed a budget of 2 million dollars.",
            },
        )
        self.source_key = self.receipt["submission"]["source_keys"][0]
        self.proposal_key = self.receipt["proposals"][0]["proposal_key"]

    def test_purge_removes_text_and_fences_late_work(self):
        purged = self.service.purge_source(
            self.owner,
            {"request_id": str(uuid4()), "source_key": self.source_key},
        )
        self.assertEqual(purged["outcome"], "purged")
        self.assertFalse(purged["source_resurrected"])
        self.assertTrue(purged["provenance_retained"])
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertIsNone(snapshot["sources"][self.source_key]["text"])
        proposal = snapshot["proposals"][self.proposal_key]
        self.assertTrue(proposal["source_purged"])
        self.assertEqual(proposal["state"], "invalidated")
        # Historical provenance is retained but is not permission to resurrect.
        self.assertEqual(proposal["provenance"]["source_key"], self.source_key)

    def test_accepting_after_purge_conflicts_and_keeps_the_wording(self):
        self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": {"record_type": "accomplishment", "wording": "Kept wording"},
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertIsNotNone(caught.exception.proposed)

    def test_duplicate_purge_is_idempotent_not_an_error(self):
        first = self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        second = self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        self.assertEqual(first["outcome"], "purged")
        self.assertEqual(second["outcome"], "already_purged")

    def test_foreign_source_is_neutral_not_found(self):
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.service.purge_source(
                "member-b", {"request_id": str(uuid4()), "source_key": self.source_key}
            )

    def test_late_job_after_purge_is_stale_and_writes_nothing(self):
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot.setdefault("jobs", {})
        fence = JobFence(
            source_key=self.source_key,
            source_version=int(snapshot["sources"][self.source_key]["version"]),
            submission_key=self.receipt["submission"]["submission_key"],
            submission_version=1,
            policy_version=1,
            lifecycle_epoch=snapshot["lifecycle_epoch"],
        )
        job = enqueue(snapshot, fence, "document_parse")
        self.assertTrue(fence_is_current(snapshot, job["fence"]))
        self.service.purge_source(
            self.owner, {"request_id": str(uuid4()), "source_key": self.source_key}
        )
        after = self.service.repository.load_owner(self.owner)
        self.assertFalse(fence_is_current(after, job["fence"]))
        with self.assertRaises(Exception):
            lease(after, job["job_key"])


class FieldIntentTests(unittest.TestCase):
    """A partial change must never blank a field the member did not touch."""

    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        created = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role", "values": ROLE_VALUES}],
            },
        )
        self.assertEqual(created["summary"]["saved"], 1)
        self.record_key = created["saved_items"][0]["record_key"]

    def overlay_values(self):
        snapshot = self.draft_service.repository.load_owner(self.owner)
        return snapshot["items"][self.record_key]["proposed_values"]

    def partial_change(self, values, clears=None):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "r2",
                    "record_type": "role",
                    "values": values,
                    "explicit_clears": clears or [],
                }],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        return receipt["proposals"][0]

    def accept(self, proposal):
        return self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": proposal["proposal_key"],
                "decision": "accept",
                "confirmed_values": proposal["proposed_values"],
            },
        )

    def test_composer_shaped_partial_change_preserves_other_fields(self):
        # Exactly the shape the composer emits when the member changes one
        # filled field: no null padding and no default booleans. An identical
        # restatement with no change is a quiet duplicate instead.
        proposal = self.partial_change(
            {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
                "employment_type": "part_time",
            }
        )
        self.assertEqual(proposal["kind"], "contradiction")
        self.assertEqual(
            set(proposal["proposed_values"]),
            {"role_title", "employer_name", "employment_type"},
        )
        decided = self.accept(proposal)
        self.assertEqual(decided["outcome"], "saved")
        merged = self.overlay_values()
        self.assertEqual(merged["employment_type"], "part_time")
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])
        self.assertEqual(merged["date_precision"], "month")
        self.assertTrue(merged["current_role"])

    def test_adding_one_detail_keeps_every_other_field(self):
        proposal = self.partial_change(
            {
                "role_title": "Systems Engineer",
                "employer_name": "Northrop Grumman",
                "location_text": "Huntsville, Alabama",
            }
        )
        self.assertEqual(proposal["kind"], "additional_detail")
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertEqual(merged["location_text"], "Huntsville, Alabama")
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])

    def test_explicit_clear_still_works_and_touches_only_that_field(self):
        proposal = self.partial_change(
            {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            clears=["summary"],
        )
        self.assertEqual(proposal["explicit_clears"], ["summary"])
        self.assertIsNone(proposal["proposed_values"]["summary"])
        self.assertEqual(proposal["kind"], "contradiction")
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertIsNone(merged["summary"])
        self.assertEqual(merged["start_date"], ROLE_VALUES["start_date"])
        self.assertTrue(merged["current_role"])

    def test_explicit_clear_of_an_unchanged_boolean_is_allowed(self):
        proposal = self.partial_change(
            {"role_title": "Systems Engineer", "employer_name": "Northrop Grumman"},
            clears=["current_role"],
        )
        self.assertFalse(proposal["proposed_values"]["current_role"])
        self.accept(proposal)
        merged = self.overlay_values()
        self.assertFalse(merged["current_role"])
        self.assertEqual(merged["summary"], ROLE_VALUES["summary"])

    def test_setting_and_clearing_the_same_field_is_refused(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "items": [{
                        "client_key": "r3",
                        "record_type": "role",
                        "values": {"role_title": "Systems Engineer",
                                   "employer_name": "Northrop Grumman"},
                        "explicit_clears": ["role_title"],
                    }],
                },
            )

    def test_unknown_clear_field_is_refused(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.submit(
                self.owner,
                {
                    "type": "add_submission",
                    "request_id": str(uuid4()),
                    "items": [{
                        "client_key": "r4",
                        "record_type": "skill",
                        "values": {"name": "MBSE"},
                        "explicit_clears": ["visitor_ai"],
                    }],
                },
            )


class AtomicityTests(unittest.TestCase):
    """One member action commits once: canonical facts and the receipt agree."""

    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"

    def two_skill_body(self, request_id):
        return {
            "type": "add_submission",
            "request_id": request_id,
            "items": [
                {"client_key": "s1", "record_type": "skill", "values": {"name": "First skill"}},
                {"client_key": "s2", "record_type": "skill", "values": {"name": "Second skill"}},
            ],
        }

    def test_intake_store_failure_leaves_no_canonical_fact_and_retries_clean(self):
        from services.resume_intake_repository import ResumeIntakeStoreUnavailable

        original = self.service.repository.save_owner

        def failing(owner, snapshot, command=None):
            raise ResumeIntakeStoreUnavailable("synthetic final-store failure")

        self.service.repository.save_owner = failing
        request_id = str(uuid4())
        with self.assertRaises(ResumeIntakeUnavailableError) as caught:
            self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertIsNotNone(caught.exception.proposed)
        self.assertEqual(self.catalog.list_items(self.owner), [])
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertEqual(snapshot["receipts"], {})
        self.assertEqual(snapshot["submissions"], {})
        self.assertEqual(snapshot["sources"], {})

        self.service.repository.save_owner = original
        retried = self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(retried["summary"]["saved"], 2)
        self.assertEqual(retried["summary"]["unresolved"], 0)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_second_canonical_write_failure_rolls_back_the_first(self):
        from services.resume_draft_service import ResumeDraftUnavailableError

        original = self.draft_service.commit
        calls = {"count": 0}

        def flaky(owner, payload):
            if payload.get("type") == "create_private_item":
                calls["count"] += 1
                if calls["count"] == 2:
                    raise ResumeDraftUnavailableError()
            return original(owner, payload)

        self.draft_service.commit = flaky
        request_id = str(uuid4())
        with self.assertRaises(ResumeIntakeUnavailableError):
            self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(self.service.repository.load_owner(self.owner)["receipts"], {})

        self.draft_service.commit = original
        retried = self.service.submit(self.owner, self.two_skill_body(request_id))
        self.assertEqual(retried["summary"]["saved"], 2)
        self.assertEqual(retried["summary"]["unresolved"], 0)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)

    def test_receipt_and_canonical_fact_commit_together_on_success(self):
        receipt = self.service.submit(self.owner, self.two_skill_body(str(uuid4())))
        snapshot = self.service.repository.load_owner(self.owner)
        self.assertIn(receipt["request_id"], snapshot["receipts"])
        self.assertEqual(len(snapshot["submissions"]), 1)
        self.assertEqual(len(snapshot["sources"]), 2)
        self.assertEqual(len(snapshot["jobs"]), 2)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 2)


class ByteBoundIdempotencyTests(unittest.TestCase):
    """A request digest binds to the admitted bytes, not to their metadata."""

    def test_same_audio_replays_and_different_audio_conflicts(self):
        transcriber = RecordingTranscriber("first recording")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        request_id = str(uuid4())
        body = {"request_id": request_id, "client_key": "mic-1", "duration_seconds": 3.0}
        payload = wav_bytes(b"\x00" * 64)
        first = service.transcribe_recording("member-a", FakeUpload("audio/wav", payload), body)
        replay = service.transcribe_recording("member-a", FakeUpload("audio/wav", payload), body)
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(transcriber.calls), 1)

        transcriber.transcript = "different second recording"
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            service.transcribe_recording(
                "member-a", FakeUpload("audio/wav", wav_bytes(b"\x01" * 64)), body
            )
        self.assertEqual(caught.exception.error_code, "idempotency_conflict")
        # The provider was never asked to transcribe the changed bytes.
        self.assertEqual(len(transcriber.calls), 1)

        with self.assertRaises(ResumeIntakeConflictError) as duration_conflict:
            service.transcribe_recording(
                "member-a",
                FakeUpload("audio/wav", payload),
                {**body, "duration_seconds": 4.0},
            )
        self.assertEqual(duration_conflict.exception.error_code, "idempotency_conflict")
        self.assertEqual(len(transcriber.calls), 1)

    def test_same_document_bytes_replay_and_changed_bytes_conflict(self):
        received = []

        def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
            received.append(admitted)
            from services.my_opportunities.member_import_service import ImportStageOutcome

            return ("Extracted text.", "extracted", None, False,
                    (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                        outcome="extracted", reason_code=None, occurred_at=now),))

        service, _catalog, _draft = build_service(document_pipeline=pipeline)
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "attachments": [{"client_key": "d1", "kind": "document",
                             "declared_content_type": "text/plain", "filename": "same.txt"}],
        }
        def files(data):
            # A fresh upload per attempt: a real request stream is consumed once.
            return {"d1": FakeUpload("text/plain", data)}

        first = service.submit("member-a", body, files=files(b"same bytes"))
        replay = service.submit("member-a", body, files=files(b"same bytes"))
        self.assertFalse(first["replayed"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(received, [b"same bytes"])
        with self.assertRaises(ResumeIntakeConflictError):
            service.submit("member-a", body, files=files(b"different bytes"))
        self.assertEqual(received, [b"same bytes"])


class UiShapedRecordMatrixTests(unittest.TestCase):
    """Drive the service with the sparse payloads the composer actually emits."""

    def setUp(self):
        self.service, self.catalog, _draft = build_service()
        self.owner = "matrix-member"
        self.parent_key = str(uuid4())
        self.catalog.put_item(
            self.owner,
            {
                "record_key": self.parent_key,
                "record_type": "role",
                "content_token": "1",
                "access_revision": 1,
                "editable": True,
                "blocked_reason": None,
                "save_mode": "canonical",
                "values": dict(ROLE_VALUES),
                "resume_display": False,
                "visitor_ai": False,
                "private_assistance_excluded": False,
            },
        )

    def _cases(self):
        return {
            "role": {"role_title": "Program Lead", "employer_name": "Example Works"},
            "skill": {"name": "Systems thinking"},
            "education": {
                "title": "Systems Engineering",
                "institution_name": "Example University",
                "education_status": "in_progress",
            },
            "credential": {
                "name": "Architecture Certificate",
                "issuer": "Example Institute",
                "completion_status": "completed",
                "issue_date": "2026-09-01",
            },
            "accomplishment": {"wording": "Reduced review time by 20 percent"},
        }

    def test_direct_add_accepts_ui_shaped_payload_for_every_record_type(self):
        for record_type, values in self._cases().items():
            with self.subTest(record_type=record_type):
                item = {
                    "client_key": "direct-" + record_type,
                    "record_type": record_type,
                    "values": values,
                }
                if record_type == "accomplishment":
                    item["parent_key"] = self.parent_key
                receipt = self.service.submit(
                    self.owner,
                    {"type": "add_submission", "request_id": str(uuid4()), "items": [item]},
                )
                self.assertEqual(receipt["summary"]["saved"], 1)

    def test_proposal_accept_accepts_ui_shaped_values_for_every_record_type(self):
        for record_type, values in self._cases().items():
            with self.subTest(record_type=record_type):
                created = self.service.submit(
                    self.owner,
                    {
                        "type": "add_submission",
                        "request_id": str(uuid4()),
                        "text": "Member wording for " + record_type,
                    },
                )
                confirmed = {"record_type": record_type, **values}
                if record_type == "accomplishment":
                    confirmed["parent_key"] = self.parent_key
                accepted = self.service.decide(
                    self.owner,
                    {
                        "request_id": str(uuid4()),
                        "proposal_key": created["proposals"][0]["proposal_key"],
                        "decision": "accept",
                        "confirmed_values": confirmed,
                    },
                )
                self.assertEqual(accepted["outcome"], "saved")

    def test_existing_record_change_preserves_untouched_required_fields(self):
        receipt = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "partial-role",
                    "record_type": "role",
                    "values": {"role_title": ROLE_VALUES["role_title"], "summary": "New detail"},
                }],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        accepted = self.service.decide(
            self.owner,
            {
                "request_id": str(uuid4()),
                "proposal_key": receipt["proposals"][0]["proposal_key"],
                "decision": "accept",
                "confirmed_values": {"summary": "New detail"},
            },
        )
        self.assertEqual(accepted["outcome"], "saved")
        self.assertEqual(accepted["item"]["proposed_values"]["summary"], "New detail")
        self.assertEqual(
            accepted["item"]["proposed_values"]["employer_name"],
            ROLE_VALUES["employer_name"],
        )


class SavedReplayContentTests(unittest.TestCase):
    def test_saved_item_replay_hydrates_equal_content_then_labels_current_change(self):
        service, catalog, _draft = build_service()
        request_id = str(uuid4())
        body = {
            "type": "add_submission",
            "request_id": request_id,
            "items": [{"client_key": "skill", "record_type": "skill", "values": {"name": "MBSE"}}],
        }
        first = service.submit("member-a", body)
        replay = service.submit("member-a", body)
        self.assertEqual(replay["saved_items"][0]["values"]["name"], "MBSE")
        self.assertTrue(replay["saved_items"][0]["content_equivalent_to_first_response"])

        key = first["saved_items"][0]["record_key"]
        changed = catalog.get_item("member-a", key)
        changed["content_token"] = "2"
        changed["values"]["name"] = "Current MBSE wording"
        catalog.put_item("member-a", changed)
        after_change = service.submit("member-a", body)
        item = after_change["saved_items"][0]
        self.assertEqual(item["values"]["name"], "Current MBSE wording")
        self.assertFalse(item["content_equivalent_to_first_response"])
        self.assertEqual(item["values_source"], "current_canonical_at_replay")

        source_key = first["submission"]["source_keys"][0]
        service.purge_source("member-a", {"request_id": str(uuid4()), "source_key": source_key})
        after_purge = service.submit("member-a", body)
        self.assertEqual(after_purge["saved_items"][0]["values"]["name"], "Current MBSE wording")

    def test_recording_replay_distinguishes_missing_version_changed_and_purged(self):
        transcriber = RecordingTranscriber("recoverable words")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        body = {"request_id": str(uuid4()), "client_key": "mic", "duration_seconds": 2.0}
        first = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        snapshot = service.repository.load_owner("member-a")
        source = snapshot["sources"][first["source_key"]]
        source["version"] = 2
        service.repository.save_owner("member-a", snapshot)
        changed = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(changed["source_unavailable_reason"], "version_changed")
        self.assertFalse(changed.get("source_purged", False))

        snapshot = service.repository.load_owner("member-a")
        snapshot["sources"][first["source_key"]]["state"] = "purged"
        service.repository.save_owner("member-a", snapshot)
        purged = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(purged["source_unavailable_reason"], "purged")
        self.assertTrue(purged["source_purged"])

        snapshot = service.repository.load_owner("member-a")
        del snapshot["sources"][first["source_key"]]
        service.repository.save_owner("member-a", snapshot)
        missing = service.transcribe_recording("member-a", FakeUpload("audio/wav", wav_bytes()), body)
        self.assertEqual(missing["source_unavailable_reason"], "missing")
        self.assertFalse(missing.get("source_purged", False))


class StaleAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.service, self.catalog, self.draft_service = build_service()
        self.owner = "member-a"
        created = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r1", "record_type": "role", "values": ROLE_VALUES}],
            },
        )
        self.record_key = created["saved_items"][0]["record_key"]
        pending = self.service.submit(
            self.owner,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{"client_key": "r2", "record_type": "role",
                           "values": {"role_title": "Systems Engineer",
                                      "employer_name": "Example Corp"}}],
            },
        )
        self.proposal = pending["proposals"][0]
        self.proposal_key = self.proposal["proposal_key"]

    def test_edit_decision_enforces_the_same_binding_checks_as_accept(self):
        # The source version moves after the proposal was made.
        snapshot = self.service.repository.load_owner(self.owner)
        source = snapshot["sources"][self.proposal["provenance"]["source_key"]]
        snapshot["sources"][source["source_key"]]["version"] = int(source["version"]) + 1
        self.service.repository.save_owner(self.owner, snapshot)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "edit",
                    "confirmed_values": {"role_title": "Systems Engineer",
                                         "employer_name": "Example Corp"},
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertIsNotNone(caught.exception.proposed)

    def test_acceptance_uses_the_captured_target_versions(self):
        # The canonical record changes after the proposal captured its token.
        self.catalog.bump_content(self.owner, self.record_key)
        with self.assertRaises(ResumeIntakeConflictError) as caught:
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": self.proposal["proposed_values"],
                },
            )
        self.assertEqual(caught.exception.error_code, "changed")
        self.assertEqual(caught.exception.proposed, self.proposal["proposed_values"])
        # Nothing was written over the newer record.
        canonical = self.catalog.get_item(self.owner, self.record_key)
        self.assertEqual(canonical["values"]["employer_name"], "Northrop Grumman")

    def test_acceptance_uses_the_captured_access_revision(self):
        self.catalog.bump_access(self.owner, self.record_key)
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": self.proposal["proposed_values"],
                },
            )
        self.assertFalse(self.catalog.get_item(self.owner, self.record_key)["resume_display"])

    def test_reject_still_works_on_a_stale_proposal(self):
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot["sources"][self.proposal["provenance"]["source_key"]]["version"] += 1
        self.service.repository.save_owner(self.owner, snapshot)
        decided = self.service.decide(
            self.owner,
            {"request_id": str(uuid4()), "proposal_key": self.proposal_key,
             "decision": "reject"},
        )
        self.assertEqual(decided["outcome"], "unresolved")

    def test_unreadable_canonical_catalog_fails_closed(self):
        class BlindDraft:
            repository = None
            catalog = None

            def get_workspace(self, owner):
                from services.resume_draft_service import ResumeDraftUnavailableError

                raise ResumeDraftUnavailableError()

            def commit(self, owner, payload):  # pragma: no cover - never reached
                raise AssertionError("must not write while the catalog is unreadable")

        from services.resume_draft_service import ResumeDraftService

        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=BlindDraft(),
            policy=selected_policy_for_tests(),
        )
        with self.assertRaises(ResumeIntakeUnavailableError):
            service.submit(
                self.owner,
                {"type": "add_submission", "request_id": str(uuid4()),
                 "items": [{"client_key": "s1", "record_type": "skill",
                            "values": {"name": "MBSE"}}]},
            )

    def test_crafted_confirmed_values_are_refused_not_a_server_error(self):
        with self.assertRaises(ResumeIntakeValidationError):
            self.service.decide(
                self.owner,
                {
                    "request_id": str(uuid4()),
                    "proposal_key": self.proposal_key,
                    "decision": "accept",
                    "confirmed_values": {"role_title": "Systems Engineer",
                                         "employer_name": "Example Corp",
                                         "visitor_ai": True},
                },
            )

    def test_canonical_validation_refusal_is_a_safe_4xx_not_a_500(self):
        from services.resume_draft_service import ResumeDraftValidationError

        class RefusingDraft(ResumeDraftService):
            def commit(self, owner, payload):
                if payload.get("type") == "create_private_item":
                    raise ResumeDraftValidationError("The canonical command was rejected.")
                return super().commit(owner, payload)

        service = ResumeIntakeService(
            repository=InMemoryResumeIntakeRepository(),
            draft_service=RefusingDraft(
                repository=InMemoryResumeDraftRepository(),
                catalog=InMemoryCanonicalCatalog(),
            ),
            policy=selected_policy_for_tests(),
        )
        with self.assertRaises(ResumeIntakeValidationError):
            service.submit(
                "member-a",
                {"type": "add_submission", "request_id": str(uuid4()),
                 "items": [{"client_key": "s1", "record_type": "skill",
                            "values": {"name": "MBSE"}}]},
            )


class OwnerIsolationTests(unittest.TestCase):
    def test_two_members_do_not_share_submissions_or_proposals(self):
        service, catalog, _draft = build_service()
        first = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "A only note.",
            },
        )
        second = service.submit(
            "member-b",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "text": "B only note.",
            },
        )
        self.assertNotEqual(
            first["submission"]["submission_key"], second["submission"]["submission_key"]
        )
        workspace_b = service.get_workspace("member-b")
        self.assertEqual(len(workspace_b["pending_proposals"]), 1)
        self.assertNotEqual(
            workspace_b["pending_proposals"][0]["proposal_key"],
            first["proposals"][0]["proposal_key"],
        )
        self.assertEqual(catalog.list_items("member-a"), [])

    def test_policy_fails_closed_when_onboarding_is_unselected(self):
        service, _catalog, _draft = build_service(policy=fixture_policy_for_tests())
        with self.assertRaises(ResumeIntakePolicyError):
            service.submit(
                "member-a",
                {"type": "add_submission", "request_id": str(uuid4()), "text": "hello"},
            )
        allowed = service.submit(
            "member-a",
            {"type": "add_submission", "request_id": str(uuid4()), "text": "hello"},
            allow_fixture_policy=True,
        )
        self.assertEqual(allowed["summary"]["unresolved"], 1)


class TranscriptionTests(unittest.TestCase):
    def test_in_field_recording_reaches_the_provider_boundary_with_real_bytes(self):
        transcriber = RecordingTranscriber("I supervised twelve engineers.")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        payload = wav_bytes()
        result = service.transcribe_recording(
            "member-a",
            FakeUpload("audio/wav", payload),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 3.0},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["transcript"], "I supervised twelve engineers.")
        self.assertEqual(len(transcriber.calls), 1)
        self.assertEqual(transcriber.calls[0]["bytes"], payload)
        self.assertEqual(transcriber.calls[0]["content_type"], "audio/wav")
        self.assertIn("source_key", result)

    def test_recording_transcription_is_idempotent_and_failures_preserve_input(self):
        transcriber = RecordingTranscriber(fail="speech_timeout")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        request_id = str(uuid4())
        body = {"request_id": request_id, "client_key": "mic-1", "duration_seconds": 2.0}
        first = service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        replay = service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertFalse(first["success"])
        self.assertTrue(first["input_preserved"])
        self.assertTrue(replay["replayed"])
        self.assertEqual(len(transcriber.calls), 1)

    def test_overlapping_same_request_reaches_provider_once_in_one_process(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingTranscriber(RecordingTranscriber):
            def transcribe(self, audio_bytes, content_type, locale="en-US"):
                result = super().transcribe(audio_bytes, content_type, locale)
                entered.set()
                release.wait(timeout=5)
                return result

        transcriber = BlockingTranscriber("one durable recording")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        body = {
            "request_id": str(uuid4()), "client_key": "mic-race",
            "duration_seconds": 2.0,
        }
        results = []
        errors = []

        def invoke():
            try:
                results.append(service.transcribe_recording(
                    "member-a", FakeUpload("audio/wav", wav_bytes()), body
                ))
            except Exception as error:  # pragma: no cover - assertion reports it
                errors.append(error)

        first = threading.Thread(target=invoke)
        second = threading.Thread(target=invoke)
        first.start()
        self.assertTrue(entered.wait(timeout=5))
        second.start()
        time.sleep(0.05)
        release.set()
        first.join(timeout=5)
        second.join(timeout=5)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(transcriber.calls), 1)
        self.assertEqual(sorted(row["replayed"] for row in results), [False, True])
        self.assertEqual({row["source_key"] for row in results}, {results[0]["source_key"]})

    def test_shared_store_claim_prevents_provider_work_across_service_instances(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingTranscriber(RecordingTranscriber):
            def transcribe(self, audio_bytes, content_type, locale="en-US"):
                result = super().transcribe(audio_bytes, content_type, locale)
                entered.set()
                release.wait(timeout=5)
                return result

        repository = InMemoryResumeIntakeRepository()
        catalog = InMemoryCanonicalCatalog()
        draft = ResumeDraftService(
            repository=InMemoryResumeDraftRepository(), catalog=catalog
        )
        transcriber = BlockingTranscriber("one cross-instance recording")

        def make_service():
            return ResumeIntakeService(
                repository=repository,
                draft_service=draft,
                transcription_adapter=ResumeTranscriptionAdapter(service=transcriber),
                policy=selected_policy_for_tests(),
            )

        holder_service = make_service()
        competing_service = make_service()
        body = {
            "request_id": str(uuid4()), "client_key": "mic-shared",
            "duration_seconds": 2.0,
        }
        holder_results = []

        holder = threading.Thread(target=lambda: holder_results.append(
            holder_service.transcribe_recording(
                "member-a", FakeUpload("audio/wav", wav_bytes()), body
            )
        ))
        holder.start()
        self.assertTrue(entered.wait(timeout=5))

        pending = competing_service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertEqual(pending["outcome"], "pending")
        self.assertEqual(pending["code"], "recording_pending")
        self.assertFalse(pending["provider_called_by_this_attempt"])
        self.assertEqual(len(transcriber.calls), 1)

        release.set()
        holder.join(timeout=5)
        self.assertEqual(len(holder_results), 1)
        replay = competing_service.transcribe_recording(
            "member-a", FakeUpload("audio/wav", wav_bytes()), body
        )
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["source_key"], holder_results[0]["source_key"])
        self.assertEqual(len(transcriber.calls), 1)

    def test_expired_claim_requires_recovery_and_never_transfers_the_lease(self):
        repository = InMemoryResumeIntakeRepository()
        request_id = str(uuid4())
        digest = "a" * 64
        payload = {
            "type": "claim_recording", "request_id": request_id,
            "request_digest": digest, "client_key": "mic-expired",
            "entrance": "resume_onboarding", "policy_version": 1,
            "lifecycle_epoch": 0, "audio_sha256": "b" * 64,
            "byte_length": 72, "content_type": "audio/wav",
            "duration_seconds": 2.0,
        }
        started = datetime(2026, 9, 11, tzinfo=timezone.utc)
        claimed = repository.claim_recording(
            "member-a", request_id, payload, now=started
        )
        expired = repository.claim_recording(
            "member-a", request_id, payload, now=started + timedelta(minutes=6)
        )

        self.assertEqual(claimed["outcome"], "claimed")
        self.assertEqual(expired["outcome"], "pending")
        self.assertTrue(expired["recovery_required"])
        self.assertNotIn("lease_id", expired)
        self.assertNotIn("source_key", expired)
        self.assertEqual(
            repository._recording_claims[("member-a", request_id)]["lease_id"],
            claimed["lease_id"],
        )
        self.assertEqual(
            repository._recording_claims[("member-a", request_id)]["state"],
            "recovery_required",
        )

    def test_unsupported_audio_is_refused_before_the_provider(self):
        transcriber = RecordingTranscriber()
        service, _catalog, _draft = build_service(transcriber=transcriber)
        with self.assertRaises(ResumeIntakeValidationError):
            service.transcribe_recording(
                "member-a",
                FakeUpload("audio/wav", b"not really a wav"),
                {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 2.0},
            )
        self.assertEqual(transcriber.calls, [])

    def test_transcribed_recording_can_be_added_and_becomes_a_proposal(self):
        transcriber = RecordingTranscriber("I led the platform migration.")
        service, _catalog, _draft = build_service(transcriber=transcriber)
        recorded = service.transcribe_recording(
            "member-a",
            FakeUpload("audio/wav", wav_bytes()),
            {"request_id": str(uuid4()), "client_key": "mic-1", "duration_seconds": 4.0},
        )
        receipt = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [
                    {"client_key": "mic-1", "kind": "recording",
                     "source_key": recorded["source_key"]}
                ],
            },
        )
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertEqual(receipt["proposals"][0]["quote"], "I led the platform migration.")

    def test_add_of_an_untranscribed_recording_fails_honestly(self):
        service, _catalog, _draft = build_service()
        receipt = service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{"client_key": "mic-1", "kind": "recording"}],
            },
        )
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertEqual(receipt["results"][0]["code"], "recording_not_transcribed")


class RealSeamDocumentTests(unittest.TestCase):
    """The shared document seam runs for real here -- no parser stub.

    These prove the reused decode/parse/extract pipeline (including the
    OS-isolated DOCX child process) is genuinely wired, not only replaceable.
    """

    @staticmethod
    def docx_bytes(*paragraphs):
        """Build a minimal, real DOCX package without a generator dependency."""

        import zipfile

        body = "".join(
            f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
            for text in paragraphs
        )
        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>"
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>"
        )
        relationships = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>'
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", relationships)
            archive.writestr("word/document.xml", document)
        return buffer.getvalue()

    def submit_document(self, service, content_type, data, filename):
        return service.submit(
            "member-a",
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "attachments": [{"client_key": "d1", "kind": "document",
                                 "declared_content_type": content_type,
                                 "filename": filename}],
            },
            files={"d1": FakeUpload(content_type, data, filename)},
        )

    def test_plain_text_document_is_extracted_by_the_real_pipeline(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service, "text/plain", b"Systems Engineer at Northrop Grumman", "resume.txt"
        )
        self.assertEqual(receipt["summary"]["failed"], 0)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertIn("Northrop Grumman", receipt["proposals"][0]["quote"])

    def test_docx_document_is_extracted_by_the_isolated_seam(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            self.docx_bytes("Systems Engineer at Northrop Grumman"),
            "resume.docx",
        )
        self.assertEqual(receipt["summary"]["failed"], 0)
        self.assertEqual(receipt["summary"]["unresolved"], 1)
        self.assertIn("Northrop Grumman", receipt["proposals"][0]["quote"])

    def test_a_non_text_document_reports_no_selectable_text(self):
        service, _catalog, _draft = build_service()
        receipt = self.submit_document(
            service,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            self.docx_bytes(),
            "empty.docx",
        )
        self.assertEqual(receipt["summary"]["unresolved"], 0)
        self.assertEqual(receipt["summary"]["failed"], 1)
        self.assertIn("scan", receipt["results"][0]["message"].lower())


class WorkspaceTests(unittest.TestCase):
    def test_workspace_read_does_not_start_processing_and_is_labelled(self):
        service, _catalog, _draft = build_service(policy=fixture_policy_for_tests())
        before = service.repository.load_owner("member-a")
        workspace = service.get_workspace("member-a")
        after = service.repository.load_owner("member-a")
        self.assertEqual(before["jobs"], after["jobs"])
        self.assertEqual(workspace["capabilities"]["persistence"], "in_memory_not_live_db")
        self.assertFalse(workspace["capabilities"]["persistence_is_live_database"])
        self.assertFalse(workspace["capabilities"]["starts_processing_on_read"])
        self.assertFalse(workspace["capabilities"]["publishes"])
        self.assertFalse(workspace["policy"]["durable_persistence_allowed"])

    def test_document_result_reports_truncation_honestly(self):
        parsed = DocumentParseResult(
            admitted=True, ok=True, outcome="partial", reason="output_truncated",
            text="truncated text", truncated=True, content_type="text/plain",
            byte_length=10, sha256="0" * 64, member_message="Only part of that document could be read.",
        )
        receipt = parsed.as_receipt()
        self.assertTrue(receipt["truncated"])
        self.assertEqual(receipt["outcome"], "partial")
        self.assertTrue(receipt["readable_text"])


import copy
import unittest
from uuid import uuid4
from services.living_resume_editor_service import (
    normalize_guide_values, normalize_editor_values, GuideRequiredFieldsError,
    LivingResumeEditorValidationError,
)
from services.resume_draft_service import ResumeDraftValidationError
from services.resume_intake_service import ResumeIntakeService, ResumeIntakeValidationError
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_policy import selected_policy_for_tests
from tests.mvp1_acceptance_support import SharedMvp1Fixture


class GuideRemainingMappingTests(unittest.TestCase):
    def shared(self):
        shared = SharedMvp1Fixture()
        service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(),
            draft_service=shared.draft, policy=selected_policy_for_tests())
        return shared, service, "remaining-mapping-fictional"

    def create(self, shared, owner, record_type, values, **options):
        return shared.draft.commit(owner, {"type":"create_private_item", "request_id":str(uuid4()),
            "record_key":str(uuid4()), "record_type":record_type, "values":values, **options})

    def test_guide_label_only_role_and_award_save_in_actual_shared_catalog(self):
        shared, service, owner = self.shared()
        for kind, values, absent in (("role", {"role_title":"Fictional engineer"}, "employer_name"),
                ("knowledge", {"title":"Fictional award", "classification":"work"}, "wording")):
            with self.subTest(kind=kind):
                saved = self.create(shared, owner, kind, values, guide_review=True)
                key = saved["item"]["record_key"]
                self.assertIsNone(shared.canonical.get_item(owner, key)["values"][absent])
                self.assertFalse(saved["item"]["resume_display"])
                self.assertFalse(saved["item"]["visitor_ai"])
        self.assertEqual(len(shared.canonical.list_items(owner)), 2)

    def test_role_and_knowledge_remain_strict_without_explicit_guide_mode(self):
        shared, service, owner = self.shared()
        for kind, values in (("role", {"role_title":"Fictional engineer"}),
                ("knowledge", {"title":"Fictional award", "classification":"work"})):
            with self.subTest(kind=kind), self.assertRaises(ResumeDraftValidationError):
                self.create(shared, owner, kind, values)
        with self.assertRaises(LivingResumeEditorValidationError):
            normalize_editor_values("role", {"role_title":"Fictional engineer"})
        self.assertEqual(shared.canonical.list_items(owner), [])

    def test_guide_proposals_save_label_only_role_and_award_once(self):
        for kind, section, values, absent in (("role", "experience", {"role_title":"Fictional engineer"}, "employer_name"),
                ("knowledge", "awards", {"title":"Fictional award", "classification":"work"}, "wording")):
            with self.subTest(kind=kind):
                shared, service, owner = self.shared()
                submitted = service.submit(owner, {"request_id":str(uuid4()), "text":"A fictional detail."})
                key = submitted["proposals"][0]["proposal_key"]
                command = {"request_id":str(uuid4()), "proposal_key":key, "decision":"accept", "guide_review":True,
                    "guide_section":section, "confirmed_values":{"record_type":kind, **values}}
                result = service.decide(owner, command)
                self.assertEqual(result["outcome"], "saved")
                self.assertIsNone(result["item"]["values"][absent])
                self.assertTrue(service.decide(owner, command)["replayed"])
                self.assertEqual(len(shared.canonical.list_items(owner)), 1)

    def test_text_sections_wait_for_actual_words_and_keep_original_proposal(self):
        for section, title, classification in (("impact_statement", "Professional summary", "work"),
                ("story", "My Story", "personal"), ("looking_ahead", "Looking Ahead", "work"),
                ("contact", "Contact details", "work")):
            with self.subTest(section=section):
                shared, service, owner = self.shared()
                submitted = service.submit(owner, {"request_id":str(uuid4()), "text":"Original fictional words."})
                key = submitted["proposals"][0]["proposal_key"]
                before = copy.deepcopy(service.repository.load_owner(owner)["proposals"][key])
                with self.assertRaises(ResumeIntakeValidationError) as missing:
                    service.decide(owner, {"request_id":str(uuid4()), "proposal_key":key, "decision":"accept",
                        "guide_review":True, "guide_section":section, "confirmed_values":{"record_type":"knowledge",
                            "title":title, "wording":" ", "classification":classification}})
                self.assertEqual(missing.exception.code, "missing_required_fields")
                self.assertEqual(missing.exception.missing_required_fields, ["wording"])
                after = service.repository.load_owner(owner)["proposals"][key]
                self.assertEqual(after["state"], "pending")
                self.assertEqual(after["proposed_values"], before["proposed_values"])
                self.assertEqual(shared.canonical.list_items(owner), [])

    def test_text_section_cannot_bypass_required_words_by_renaming_its_label(self):
        for section in ("impact_statement", "story", "looking_ahead", "contact"):
            with self.subTest(section=section), self.assertRaises(GuideRequiredFieldsError) as missing:
                normalize_guide_values("knowledge", {"title":"Member label", "classification":"work"}, section=section)
            self.assertEqual(missing.exception.missing_required_fields, ["wording"])

    def test_unqualified_sql_refuses_guide_before_storage_effects(self):
        from unittest.mock import Mock
        from services.resume_draft_repository import SqlResumeDraftRepository
        from services.resume_draft_service import ResumeDraftService
        from services.entry_policy_service import EntryPolicyService, EntryPolicyValidationError
        database, catalog = Mock(), Mock()
        draft = ResumeDraftService(repository=SqlResumeDraftRepository(database), catalog=catalog)
        for kind, values in (("role", {"role_title":"Fictional engineer"}),
                ("knowledge", {"title":"Fictional award", "classification":"work"})):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(ResumeDraftValidationError, "input is kept"):
                    draft.commit("sql-fictional", {"type":"create_private_item", "request_id":str(uuid4()),
                        "record_key":str(uuid4()), "record_type":kind, "values":values, "guide_review":True})
                policy_repository = Mock()
                policy_repository.list_entries.return_value = []
                policy_repository.commit_command.return_value = {}
                policy = EntryPolicyService(repository=policy_repository)
                with self.assertRaisesRegex(EntryPolicyValidationError, "input is kept"):
                    policy.commit("sql-fictional", {"type":"create", "request_id":str(uuid4()),
                        "entry_key":str(uuid4()), "canonical_type":kind, "values":values, "guide_review":True})
                policy_repository.commit_command.assert_not_called()
                policy_repository.load_owner.assert_not_called()
        database.execute_procedure.assert_not_called()
        catalog.create_private.assert_not_called()

    def test_saved_text_sections_cannot_be_emptied_by_renaming_the_label(self):
        for title, classification, bind_story in (("Contact details", "work", False),
                ("A custom story label", "personal", True)):
            with self.subTest(title=title):
                shared, service, owner = self.shared()
                saved = self.create(shared, owner, "knowledge", {"title":title,
                    "wording":"Original fictional words.", "classification":classification})["item"]
                key = saved["record_key"]
                if bind_story:
                    shared.draft.commit(owner, {"type":"bind_story", "request_id":str(uuid4()), "record_key":key,
                        "expected_draft_version":0, "expected_content_token":saved["content_token"],
                        "expected_access_revision":saved["access_revision"]})
                workspace = shared.draft.get_workspace(owner)
                with self.assertRaises(ResumeDraftValidationError) as missing:
                    shared.draft.commit(owner, {"type":"save_item", "request_id":str(uuid4()), "record_key":key,
                        "record_type":"knowledge", "guide_review":True, "expected_draft_version":workspace["draft_version"],
                        "expected_content_token":saved["content_token"], "expected_access_revision":saved["access_revision"],
                        "values":{"title":"Renamed label", "wording":None}})
                self.assertEqual(missing.exception.code, "missing_required_fields")
                self.assertEqual(missing.exception.missing_required_fields, ["wording"])
                self.assertEqual(shared.canonical.get_item(owner, key)["values"]["wording"], "Original fictional words.")




class BoundedRecordingGuardTests(unittest.TestCase):
    """B3a: a same-instance duplicate waits only the bounded guard time, then gets the busy reply."""

    def test_duplicate_recording_returns_busy_quickly_then_replays_with_one_transcription(self):
        import threading, time
        from services.resume_intake_service import ResumeIntakeBusyError
        from tests.test_my_data_intake_sources import StubTranscriber, build_service, recording_payload, wav_bytes
        entered, released = threading.Event(), threading.Event()
        self.addCleanup(released.set)
        stub = StubTranscriber('I restore fictional radios.')
        real = stub.transcribe
        def held(*args, **kwargs):
            entered.set()
            if not released.wait(30):
                raise AssertionError('The held fake transcription was never released')
            return real(*args, **kwargs)
        stub.transcribe = held
        service = build_service(transcriber=stub)
        upload, payload = recording_payload('audio/wav', wav_bytes(), 12.0)
        results = {}
        worker = threading.Thread(target=lambda: results.setdefault('first',
            service.transcribe_recording('member-a', upload, dict(payload))))
        worker.start()
        self.assertTrue(entered.wait(5))
        started = time.monotonic()
        with self.assertRaises(ResumeIntakeBusyError) as busy:
            service.transcribe_recording('member-a', recording_payload('audio/wav', wav_bytes(), 12.0)[0], dict(payload))
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual((busy.exception.code, busy.exception.request_id), ('request_in_progress', payload['request_id']))
        released.set(); worker.join(10)
        replay = service.transcribe_recording('member-a', recording_payload('audio/wav', wav_bytes(), 12.0)[0], dict(payload))
        self.assertEqual(replay['source_key'], results['first']['source_key'])
        self.assertEqual(len(stub.calls), 1)


class GuideB3mTests(unittest.TestCase):
    """B3m: missing essentials, hidden tabs, order and D23 place (map coordination 1d2b73b, plan e7bb8d4e)."""
    NL = chr(10)
    TEXT = NL.join(['EXPERIENCE', 'Fictional Orchard, Engineer, 2019 - 2021', '- Ran the fictional harvest audit',
                    'SKILLS', '- Fictional Pruning', 'AWARDS', '- Fictional Orchard Prize 2020', ''])
    ROLE = {'record_type': 'role', 'values': {'role_title': 'Engineer', 'employer_name': 'Fictional Orchard'},
            'quote': 'Fictional Orchard, Engineer, 2019 - 2021', 'outcome': 'new', 'confidence': 'certain'}

    def setUp(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        self.shared, self.owner = SharedMvp1Fixture(), 'guide-b3m-fictional'

    def organized(self, scripted=None, fail=None, text=None):
        from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
        from services.resume_intake_policy import selected_policy_for_tests
        from tests.test_my_data_intake_sources import extracted_pipeline
        text = text or self.TEXT
        self.adapter = DeterministicFakeExtractionAdapter([self.ROLE] if scripted is None else scripted)
        if fail:
            self.adapter.fail_with = fail
        self.service = ResumeIntakeService(repository=InMemoryResumeIntakeRepository(), draft_service=self.shared.draft,
            policy=selected_policy_for_tests(), document_pipeline=extracted_pipeline(text),
            extraction_adapter=self.adapter, matching_exclusions=lambda member: set())
        self.service.submit(self.owner, {'request_id': str(uuid4()), 'attachments': [{'client_key': 'document',
            'kind': 'document', 'declared_content_type': 'text/plain', 'filename': 'fictional.txt'}]},
            files={'document': FakeUpload('text/plain', text.encode(), 'fictional.txt')})
        return self.service.working_set(self.owner)

    def line(self, text, working=None):
        working = working or self.service.working_set(self.owner)
        return next(row for row in working['unplaced'] if (row['values'] or {}).get('text') == text)

    def section(self, key, working=None):
        working = working or self.service.working_set(self.owner)
        return next(row for row in working['sections'] if row['key'] == key)

    def place(self, item, destination, request_id=None, working=None):
        working = working or self.service.working_set(self.owner)
        return self.service.guide_place(self.owner, {'request_id': request_id or str(uuid4()), 'action': 'place',
            'item_ref': item['item_ref'], 'destination': destination,
            'expected_working_set_token': working['working_set_token'], 'expected_item_revision': item['revision']})

    def undo(self, placed, request_id=None):
        return self.service.guide_place(self.owner, {'request_id': request_id or str(uuid4()), 'action': 'undo',
            'operation_ref': placed['operation_ref'], 'undo_token': placed['undo_token']})

    def stored(self):
        import copy
        return copy.deepcopy(self.service.repository.load(self.owner)) if hasattr(self.service.repository, 'load') \
            else copy.deepcopy(self.service._load(self.owner))

    def public(self):
        import copy
        return (copy.deepcopy(sorted(self.shared.canonical.list_items(self.owner), key=lambda row: row['record_key'])),
                copy.deepcopy(self.shared.draft.repository.load_owner(self.owner)),
                copy.deepcopy(self.shared.publication.owner_preview(self.owner)))

    def role_ref(self, working=None):
        return self.section('experience', working)['items'][0]['item_ref']

    # ---- missing_required (I1)

    def test_missing_required_is_exactly_what_a_guide_accept_refuses(self):
        from services.living_resume_editor_service import GuideRequiredFieldsError, guide_required_fields, normalize_guide_values
        from services.resume_guide_contract import guide_missing_required
        complete = {
            'role': ({'role_title': 'Engineer', 'employer_name': 'Fictional Orchard'}, 'experience'),
            'education': ({'institution_name': 'Fictional College', 'end_date': '2015'}, 'education'),
            'skill': ({'name': 'Fictional Pruning'}, 'skills'),
            'project': ({'project_name': 'Fictional Mill', 'summary': 'A fictional mill.'}, 'projects'),
            'accomplishment': ({'wording': 'Ran a fictional audit.'}, 'experience'),
            'credential': ({'name': 'Fictional Licence', 'issuer': 'Fictional Board', 'issue_date': '2020'}, 'certifications'),
            'knowledge': ({'title': 'Professional summary', 'wording': 'Fictional words.', 'classification': 'work'},
                          'impact_statement'),
        }
        for record_type, (values, section) in complete.items():
            node = {'record_type': record_type, 'section': section, 'values': values}
            self.assertEqual(guide_missing_required(node), [], record_type)
            for field in guide_required_fields(record_type, values, section=section) or list(values):
                if field not in values or field == 'classification':
                    continue
                partial = {**values, field: ''}
                with self.subTest(record_type=record_type, removed=field):
                    expected = guide_missing_required({**node, 'values': partial})
                    try:
                        normalize_guide_values(record_type, partial, section=section)
                        refused = []
                    except GuideRequiredFieldsError as error:
                        refused = error.missing_required_fields
                    except Exception:  # another validation (a date), not a missing essential
                        continue
                    self.assertEqual(expected, refused)
        self.assertIsNone(guide_missing_required({'record_type': 'unspecified', 'section': 'unplaced', 'values': {'text': 'x'}}))

    def test_a_waiting_role_without_its_title_says_so_and_accept_refuses_with_the_same_list(self):
        role = {**self.ROLE, 'values': {'employer_name': 'Fictional Orchard'}}
        working = self.organized([role])
        item = self.section('experience', working)['items'][0]
        self.assertEqual(item['missing_required'], ['role_title'])
        self.assertIsNone(self.line('- Fictional Pruning', working)['missing_required'])
        with self.assertRaises(ResumeIntakeValidationError) as refused:
            self.service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': item['proposal_key'],
                                             'decision': 'accept', 'guide_review': True, 'guide_section': 'experience'})
        self.assertEqual(refused.exception.missing_required_fields, ['role_title'])
        complete = self.organized()
        self.assertEqual(self.section('experience', complete)['items'][0]['missing_required'], [])

    # ---- tab_hidden

    def test_a_section_with_only_hidden_content_keeps_a_hidden_tab(self):
        working = self.organized()
        role = self.section('experience', working)['items'][0]
        self.assertEqual((self.section('experience', working)['tab_visible'], self.section('experience', working)['tab_hidden']),
                         (True, False))
        self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': role['item_ref'], 'hidden': True,
            'expected_working_set_token': working['working_set_token'], 'expected_item_revision': role['revision']})
        hidden = self.service.working_set(self.owner)
        experience = self.section('experience', hidden)
        self.assertEqual((experience['tab_visible'], experience['tab_hidden']), (False, True))
        self.assertFalse(any(row['tab_visible'] and row['tab_hidden'] for row in hidden['sections']))
        role = experience['items'][0]
        self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': role['item_ref'], 'hidden': False,
            'expected_working_set_token': hidden['working_set_token'], 'expected_item_revision': role['revision']})
        shown = self.section('experience')
        self.assertEqual((shown['tab_visible'], shown['tab_hidden']), (True, False))
        self.assertEqual(self.section('awards', hidden)['tab_hidden'], False, 'An empty section has no tab at all')

    # ---- order

    def test_sections_run_experience_before_skills_and_items_most_recent_first(self):
        from services.resume_publication_projection import RESUME_BASE_SECTION_ORDER
        def create(values):
            return self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'role',
                'parent_key': None, 'values': values})['record_key']
        older = create({'role_title': 'Clerk', 'employer_name': 'Fictional Mill', 'start_date': '2010-01-01',
                        'end_date': '2012-01-01', 'date_precision': 'year'})
        current = create({'role_title': 'Lead', 'employer_name': 'Fictional Grove', 'start_date': '2021-01-01',
                          'current_role': True, 'date_precision': 'year'})
        pending = {**self.ROLE, 'values': {'role_title': 'Engineer', 'employer_name': 'Fictional Orchard',
                                           'start_date': '2019', 'end_date': '2021', 'date_precision': 'year'}}
        working = self.organized([pending])
        self.assertEqual(working['section_order'][:7], ['impact_statement', 'experience', 'skills', 'projects', 'education',
                                                        'certifications', 'awards'])
        # The Guide's order holds whichever order Lane D's shared constant has (D6c map line 172): it is sorted here.
        self.assertIn(tuple(RESUME_BASE_SECTION_ORDER[:3]), {('impact_statement', 'skills', 'experience'),
                                                             ('impact_statement', 'experience', 'skills')})
        refs = [row['item_ref'] for row in self.section('experience', working)['items']]
        self.assertEqual(refs[0], current)
        self.assertEqual(refs[-1], older)
        self.assertEqual(len(refs), 3, 'Saved and waiting roles interleave by date')

    # ---- best guess and place

    def test_unplaced_lines_carry_a_deterministic_best_guess_without_any_provider_call(self):
        working = self.organized()
        calls = len(self.adapter.calls)
        self.assertEqual(self.line('- Ran the fictional harvest audit', working)['best_guess'], {'role_ref': self.role_ref(working)})
        self.assertEqual(self.line('- Fictional Pruning', working)['best_guess'], {'section': 'skills'})
        self.assertEqual(self.line('- Fictional Orchard Prize 2020', working)['best_guess'], {'section': 'awards'})
        self.service.working_set(self.owner)
        self.assertEqual(len(self.adapter.calls), calls, 'Reading the best guess calls no provider')
        unheaded = self.organized([], text='A fictional line with no heading' + self.NL)
        self.assertIsNone(unheaded['unplaced'][0]['best_guess'])

    def test_place_into_each_destination_keeps_the_exact_text_and_changes_nothing_public(self):
        working = self.organized()
        before = self.public()
        role = self.role_ref(working)
        bullet = self.line('- Ran the fictional harvest audit', working)
        placed = self.place(bullet, {'role_ref': role})
        self.assertEqual((placed['outcome'], placed['saved'], placed['canonical_changed'], placed['publishes']),
                         ('waiting', False, False, False))
        working = self.service.working_set(self.owner)
        parent = next(row for row in self.section('experience', working)['items'] if row['item_ref'] == role)
        child = next(row for row in parent['children'] if row['item_ref'] == bullet['item_ref'])
        self.assertEqual((child['record_type'], child['values']['wording'], child['state']),
                         ('accomplishment', 'Ran the fictional harvest audit', 'waiting'), 'One list marker is dropped')
        skill = self.line('- Fictional Pruning', working)
        self.place(skill, {'section': 'skills'})
        award = self.line('- Fictional Orchard Prize 2020')
        self.place(award, {'section': 'awards'})
        working = self.service.working_set(self.owner)
        placed_skill = next(row for row in self.section('skills', working)['items'] if row['item_ref'] == skill['item_ref'])
        self.assertEqual((placed_skill['record_type'], placed_skill['values'], placed_skill['missing_required']),
                         ('skill', {'name': 'Fictional Pruning'}, []))
        placed_award = next(row for row in self.section('awards', working)['items'] if row['item_ref'] == award['item_ref'])
        self.assertEqual((placed_award['record_type'], placed_award['values']), ('knowledge', {'wording': 'Fictional Orchard Prize 2020'}))
        self.assertEqual(placed_award['missing_required'], ['title'], 'The title is asked for, never guessed')
        self.assertEqual(working['unplaced'], [])
        self.assertEqual(self.public(), before, 'No canonical record, draft or publication change')

    def test_place_replays_conflicts_and_refuses_before_any_effect(self):
        working = self.organized()
        skill = self.line('- Fictional Pruning', working)
        request_id = str(uuid4())
        placed = self.place(skill, {'section': 'skills'}, request_id=request_id, working=working)
        after = self.stored()
        self.assertTrue(self.place(skill, {'section': 'skills'}, request_id=request_id, working=working)['replayed'])
        with self.assertRaises(ResumeIntakeConflictError) as reused:
            self.place(skill, {'section': 'awards'}, request_id=request_id, working=working)
        self.assertEqual(reused.exception.error_code, 'idempotency_conflict')
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.place(skill, {'section': 'awards'})  # already placed: it is no longer an unplaced line
        self.assertEqual(self.stored(), after, 'Replay, reuse and a second place change nothing')
        award = self.line('- Fictional Orchard Prize 2020')
        fresh = self.service.working_set(self.owner)
        for destination in ({'section': 'education'}, {'section': 'certifications'}, {'section': 'looking_ahead'},
                            {'section': 'skills', 'role_ref': str(uuid4())}, {}):
            with self.subTest(destination=destination), self.assertRaises(ResumeIntakeValidationError):
                self.place(award, destination, working=fresh)
        with self.assertRaises(ResumeIntakeConflictError):
            self.place(award, {'role_ref': str(uuid4())}, working=fresh)
        with self.assertRaises(ResumeIntakeConflictError):
            self.place(award, {'section': 'awards'}, working=working)  # a stale working-set token
        with self.assertRaises(ResumeIntakeConflictError):
            self.place({**award, 'revision': award['revision'] + 1}, {'section': 'awards'}, working=fresh)
        self.assertEqual(self.stored(), after, 'Every refusal comes before any effect')
        self.assertTrue(placed['undo_token'])

    def test_undo_returns_the_line_and_is_stale_once_the_suggestion_changed(self):
        working = self.organized()
        skill = self.line('- Fictional Pruning', working)
        before = self.public()
        placed = self.place(skill, {'section': 'skills'})
        undone = self.undo(placed)
        self.assertEqual((undone['outcome'], undone['publishes']), ('unplaced', False))
        back = self.line('- Fictional Pruning')
        self.assertEqual((back['item_ref'], back['state'], back['best_guess']), (skill['item_ref'], 'waiting', {'section': 'skills'}))
        self.assertTrue(self.undo(placed, request_id=undone['request_id'])['replayed'])
        with self.assertRaises(ResumeIntakeConflictError) as again:
            self.undo(placed)
        self.assertEqual(again.exception.error_code, 'stale_undo')
        replaced = self.place(back, {'section': 'skills'})  # place, Undo, place again
        working = self.service.working_set(self.owner)
        item = next(row for row in self.section('skills', working)['items'] if row['item_ref'] == skill['item_ref'])
        self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': item['item_ref'], 'hidden': True,
            'expected_working_set_token': working['working_set_token'], 'expected_item_revision': item['revision']})
        with self.assertRaises(ResumeIntakeConflictError) as hidden:
            self.undo(replaced)
        self.assertEqual(hidden.exception.error_code, 'stale_undo')
        award = self.line('- Fictional Orchard Prize 2020')
        accepted_place = self.place(award, {'section': 'skills'})
        item = next(row for row in self.section('skills')['items'] if row['item_ref'] == award['item_ref'])
        self.service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': item['proposal_key'], 'decision': 'accept',
            'confirmed_values': {'name': 'Fictional Orchard Prize'}, 'guide_review': True, 'guide_section': 'skills'})
        with self.assertRaises(ResumeIntakeConflictError) as decided:
            self.undo(accepted_place)
        self.assertEqual(decided.exception.error_code, 'stale_undo')
        self.assertEqual(self.public()[2], before[2], 'The public view never moved')

    # ---- writer mutation pass: each test below kills one mutant that survived the first run

    def visibility(self, item, hidden, working=None):
        working = working or self.service.working_set(self.owner)
        return self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': item['item_ref'],
            'hidden': hidden, 'expected_working_set_token': working['working_set_token'],
            'expected_item_revision': item['revision']})

    def test_an_unplaced_knowledge_line_has_no_missing_essentials(self):
        note = {'record_type': 'knowledge', 'values': {'title': 'Fictional note', 'wording': '- Fictional Pruning'},
                'quote': '- Fictional Pruning', 'outcome': 'new', 'confidence': 'certain', 'presentation_section': 'Unsorted'}
        working = self.organized([self.ROLE, note])
        line = next(row for row in working['unplaced'] if row['record_type'] == 'knowledge')
        self.assertIsNone(line['missing_required'], 'Unplaced items are not judged until they have a place')

    def test_a_section_with_visible_and_hidden_items_is_not_a_hidden_tab(self):
        self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'parent_key': None, 'values': {'role_title': 'Clerk', 'employer_name': 'Fictional Mill'}})
        working = self.organized()
        pending = next(row for row in self.section('experience', working)['items'] if row['origin'] == 'pending')
        self.visibility(pending, True, working)
        experience = self.section('experience')
        self.assertEqual(experience['counts']['hidden'], 1)
        self.assertEqual((experience['tab_visible'], experience['tab_hidden']), (True, False))

    def test_a_hidden_line_and_a_non_role_destination_are_refused_before_any_effect(self):
        working = self.organized()
        skill = self.line('- Fictional Pruning', working)
        award = self.line('- Fictional Orchard Prize 2020', working)
        self.visibility(skill, True, working)
        hidden = next(row for row in self.service.working_set(self.owner)['unplaced'] if row['item_ref'] == skill['item_ref'])
        before = self.stored()
        with self.assertRaises(ResumeIntakeConflictError):
            self.place(hidden, {'section': 'skills'})
        with self.assertRaises(ResumeIntakeConflictError):
            self.place(self.line('- Fictional Orchard Prize 2020'), {'role_ref': award['item_ref']})
        with self.assertRaises(ResumeIntakeConflictError):
            self.place(self.line('- Fictional Orchard Prize 2020'), {'role_ref': hidden['item_ref']})
        self.assertEqual(self.stored(), before)

    def test_undo_needs_its_own_token_and_is_stale_after_hide_then_show(self):
        working = self.organized()
        placed = self.place(self.line('- Fictional Pruning', working), {'section': 'skills'})
        with self.assertRaises(ResumeIntakeConflictError) as forged:
            self.undo({**placed, 'undo_token': '0' * 64})
        self.assertEqual(forged.exception.error_code, 'stale_undo')
        item = next(row for row in self.section('skills')['items'] if row['origin'] == 'pending')
        self.visibility(item, True)
        item = next(row for row in self.section('skills')['items'] if row['origin'] == 'pending')
        self.visibility(item, False)
        with self.assertRaises(ResumeIntakeConflictError) as shown:
            self.undo(placed)
        self.assertEqual(shown.exception.error_code, 'stale_undo', 'Hide then Show is still a change since the place')

    def test_placing_ends_organize_retry_and_undo_offers_it_again(self):
        working = self.organized(fail='provider_unavailable')
        source_key = working['active_sources'][0]['source_key']
        retry = lambda: self.service.organize_source(self.owner, {'request_id': str(uuid4()), 'source_key': source_key,
                                                                  'mode': 'retry'})
        placed = self.place(self.line('- Fictional Pruning', working), {'section': 'skills'})
        calls = len(self.adapter.calls)
        self.assertEqual(retry()['outcome'], 'already_organized', 'The member decided a line: no paid retry')
        self.assertEqual(len(self.adapter.calls), calls)
        self.undo(placed)
        self.adapter.fail_with = None
        retry()
        self.assertEqual(len(self.adapter.calls), calls + 1, 'After Undo the retry is offered again')

    def test_moving_a_placed_suggestion_makes_its_undo_stale(self):
        working = self.organized()
        placed = self.place(self.line('- Fictional Pruning', working), {'section': 'skills'})
        item = next(row for row in self.section('skills')['items'] if row['origin'] == 'pending')
        current = self.service.working_set(self.owner)
        staged = self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'stage',
            'item_ref': item['item_ref'], 'expected_working_set_token': current['working_set_token'],
            'expected_item_revision': item['revision'], 'destination': {'record_type': 'project',
            'values': {'project_name': '- Fictional Pruning', 'summary': 'A fictional project.'}, 'parent_ref': None}})
        self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'confirm',
            'conversion_key': staged['conversion_key'], 'conversion_token': staged['conversion_token'],
            'expected_working_set_token': self.service.working_set(self.owner)['working_set_token'],
            'reference_reconciliation': []})
        before = self.stored()
        with self.assertRaises(ResumeIntakeConflictError) as moved:
            self.undo(placed)
        self.assertEqual(moved.exception.error_code, 'stale_undo')
        self.assertEqual(self.stored(), before)

    # ---- round 2 (review f3b44a7): I1 through the real accept, F2 and the F3 mutants

    def accept(self, item, confirmed=None):
        # A bullet's own type has no section; its accept leaves the section to the server (the panel does the same).
        body = {'request_id': str(uuid4()), 'proposal_key': item['proposal_key'], 'decision': 'accept',
                'guide_review': True, 'guide_section': None if item['record_type'] == 'accomplishment' else item['section']}
        if confirmed is not None:
            body['confirmed_values'] = confirmed
        return self.service.decide(self.owner, body)

    def find(self, ref, working=None):
        working = working or self.service.working_set(self.owner)
        return self.service._find_working_item(working, ref)

    def assert_i1(self, item, confirmed=None):
        """I1 through the real accept: the card's missing list and wording flag say exactly what accept does."""
        import copy
        before = copy.deepcopy(self.service._load(self.owner))
        if item['waits_for_parent']:
            # A bullet saves only under a saved role; the card says it waits for its role.
            with self.assertRaises(ResumeIntakeConflictError) as refused:
                self.accept(item, confirmed)
            self.assertEqual(refused.exception.error_code, 'reconciliation_required')
            return
        if item['needs_member_wording'] and confirmed is None:
            # Accept as shown first asks the member to check the words; the card says so with the flag.
            with self.assertRaises(ResumeIntakeConflictError) as refused:
                self.accept(item)
            self.assertEqual(refused.exception.error_code, 'reconciliation_required')
            confirmed = {k: v for k, v in item['values'].items() if k != 'suggested_parent_key'}
        if item['missing_required'] and confirmed in (None, {k: v for k, v in item['values'].items() if k != 'suggested_parent_key'}):
            # Accepting the words the card shows refuses with exactly the card's missing list.
            with self.assertRaises(ResumeIntakeValidationError) as refused:
                self.accept(item, confirmed)
            self.assertEqual(refused.exception.missing_required_fields, item['missing_required'])
            self.assertEqual(self.service._load(self.owner)['proposals'], before['proposals'], 'A refusal changes nothing')
        else:
            saved = self.accept(item, confirmed)
            self.assertEqual(saved['outcome'], 'saved', item['record_type'])

    def test_i1_holds_through_the_real_accept_for_organized_suggestions(self):
        nl = self.NL
        cases = [  # each line holds exactly the values organize keeps
            ('EXPERIENCE', 'Fictional Orchard', {'record_type': 'role', 'values': {'employer_name': 'Fictional Orchard'}}, ['role_title']),
            ('EDUCATION', 'Fictional College', {'record_type': 'education', 'values': {'institution_name': 'Fictional College'}}, ['end_date']),
            ('SKILLS', 'Fictional Pruning', {'record_type': 'skill', 'values': {'name': 'Fictional Pruning'}}, []),
            ('SKILLS', 'Fictional Grafting', {'record_type': 'skill', 'values': {'name': 'Fictional Grafting'}, 'confidence': 'uncertain'}, []),
        ]
        for heading, line, script, missing in cases:
            with self.subTest(script=script):
                self.setUp()
                working = self.organized([{'quote': line, 'outcome': 'new', 'confidence': 'certain', **script}],
                                         text=heading + nl + line + nl)
                item = next(row for section in working['sections'] for row in section['items'])
                self.assertEqual(item['missing_required'], missing)
                self.assertIsInstance(item['needs_member_wording'], bool)
                self.assert_i1(item)

    def test_i1_holds_through_the_real_accept_for_every_placed_destination(self):
        destinations = ['skills', 'impact_statement', 'projects', 'awards', 'story', 'role']
        for destination in destinations:
            for edited in (False, True):
                with self.subTest(destination=destination, edited=edited):
                    self.setUp()
                    working = self.organized()
                    line = self.line('- Fictional Orchard Prize 2020', working)
                    self.place(line, {'role_ref': self.role_ref(working)} if destination == 'role' else {'section': destination})
                    item = self.find(line['item_ref'])
                    self.assertFalse(item['needs_member_wording'], 'Placing is the member choosing what it becomes')
                    if destination in {'skills', 'role'}:
                        self.assertEqual(item['missing_required'], [])
                    else:
                        self.assertEqual(item['missing_required'], ['title'], 'A knowledge title is asked for, never guessed')
                    confirmed = None
                    if edited:
                        confirmed = ({'name': 'Fictional Orchard Prize'} if destination == 'skills' else
                                     {'wording': 'Fictional Orchard Prize 2020'} if destination == 'role' else
                                     {'title': {'impact_statement': 'Professional summary', 'projects': 'Independent Project',
                                                'awards': 'Awards', 'story': 'My Story'}[destination],
                                      'wording': 'Fictional Orchard Prize 2020',
                                      'classification': 'personal' if destination == 'story' else 'work'})
                    self.assert_i1(item, confirmed)

    def test_a_bullet_placed_under_a_waiting_role_waits_for_it_then_saves_as_placed(self):
        working = self.organized()
        role = self.section('experience', working)['items'][0]
        bullet = self.line('- Ran the fictional harvest audit', working)
        self.place(bullet, {'role_ref': role['item_ref']})
        waiting = self.find(bullet['item_ref'])
        self.assertEqual((waiting['missing_required'], waiting['needs_member_wording'], waiting['waits_for_parent']), ([], False, True))
        self.assert_i1(waiting)
        saved = self.accept(role, {'role_title': 'Engineer', 'employer_name': 'Fictional Orchard'})
        parent = self.find(saved['item']['record_key'])
        child = next(row for row in parent['children'] if row['item_ref'] == bullet['item_ref'])
        self.assertFalse(child['waits_for_parent'], 'Once its role is saved the bullet stays under it and can be saved')
        self.assertEqual(self.accept(child)['outcome'], 'saved')
        bullet_saved = next(row for row in self.find(saved['item']['record_key'])['children'] if row['origin'] == 'saved')
        self.assertEqual(bullet_saved['values']['wording'], 'Ran the fictional harvest audit')

    def test_a_bullet_placed_under_a_saved_role_saves_as_placed(self):
        key = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'parent_key': None, 'values': {'role_title': 'Clerk', 'employer_name': 'Fictional Mill'}})['record_key']
        working = self.organized()
        bullet = self.line('- Ran the fictional harvest audit', working)
        self.place(bullet, {'role_ref': key})
        item = self.find(bullet['item_ref'])
        self.assertEqual((item['waits_for_parent'], item['needs_member_wording'], item['missing_required']), (False, False, []))
        self.assert_i1(item)

    def test_a_pending_move_is_the_members_choice_and_its_undo_restores_the_wording_check(self):
        line = 'Fictional Pruning'
        working = self.organized([{'record_type': 'skill', 'values': {'name': 'Fictional Pruning'}, 'quote': line,
                                   'outcome': 'new', 'confidence': 'uncertain'}], text='SKILLS' + self.NL + line + self.NL)
        item = self.section('skills', working)['items'][0]
        self.assertTrue(item['needs_member_wording'])
        staged = self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'stage',
            'item_ref': item['item_ref'], 'expected_working_set_token': working['working_set_token'],
            'expected_item_revision': item['revision'], 'destination': {'record_type': 'project',
            'values': {'project_name': 'Fictional Pruning', 'summary': 'A fictional project.'}, 'parent_ref': None}})
        confirmed = self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'confirm',
            'conversion_key': staged['conversion_key'], 'conversion_token': staged['conversion_token'],
            'expected_working_set_token': self.service.working_set(self.owner)['working_set_token'],
            'reference_reconciliation': []})
        moved = self.find(item['item_ref'])
        self.assertEqual((moved['record_type'], moved['needs_member_wording'], moved['missing_required']), ('project', False, []))
        self.service.guide_conversion(self.owner, {'request_id': str(uuid4()), 'action': 'undo',
            'operation_ref': confirmed['operation_ref'], 'undo_token': confirmed['undo_token']})
        self.assertTrue(self.find(item['item_ref'])['needs_member_wording'], 'Undo restores the original wording check')
        self.assert_i1(self.find(item['item_ref']))

    def test_a_bullet_left_by_a_rejected_role_can_be_rescued_into_another_role(self):
        saved_role = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'role',
            'parent_key': None, 'values': {'role_title': 'Clerk', 'employer_name': 'Fictional Mill'}})['record_key']
        working = self.organized()
        pending_role = next(row for row in self.section('experience', working)['items'] if row['origin'] == 'pending')
        bullet = self.line('- Ran the fictional harvest audit', working)
        self.place(bullet, {'role_ref': pending_role['item_ref']})
        self.service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': pending_role['proposal_key'],
                                         'decision': 'reject'})
        orphan = next(row for row in self.service.working_set(self.owner)['unplaced'] if row['item_ref'] == bullet['item_ref'])
        self.assertEqual((orphan['record_type'], orphan['state']), ('accomplishment', 'waiting'))
        placed = self.place(orphan, {'role_ref': saved_role})
        role = self.find(saved_role)
        child = next(row for row in role['children'] if row['item_ref'] == bullet['item_ref'])
        self.assertEqual((child['values']['wording'], child['needs_member_wording']), ('Ran the fictional harvest audit', False))
        self.undo(placed)
        back = next(row for row in self.service.working_set(self.owner)['unplaced'] if row['item_ref'] == bullet['item_ref'])
        self.assertEqual(back['record_type'], 'accomplishment', 'Undo returns the orphan exactly')

    def test_a_reused_request_id_for_another_line_is_a_conflict(self):
        working = self.organized()
        request_id = str(uuid4())
        self.place(self.line('- Fictional Pruning', working), {'section': 'skills'}, request_id=request_id, working=working)
        before = self.stored()
        other = self.line('- Fictional Orchard Prize 2020', working)
        self.assertEqual(other['revision'], self.line('- Fictional Pruning', working)['revision'])
        with self.assertRaises(ResumeIntakeConflictError) as reused:  # only the line differs: same token and revision
            self.place(other, {'section': 'skills'}, request_id=request_id, working=working)
        self.assertEqual(reused.exception.error_code, 'idempotency_conflict')
        self.assertEqual(self.stored(), before)

    def test_the_role_guess_is_the_nearest_role_above_the_line(self):
        nl = self.NL
        first, second = 'Fictional Orchard, Engineer, 2019 - 2021', 'Fictional Grove, Analyst, 2016 - 2019'
        text = nl.join(['EXPERIENCE', first, '', second, '- Ran the fictional grove audit', ''])
        working = self.organized([{**self.ROLE, 'quote': first},
            {'record_type': 'role', 'values': {'role_title': 'Analyst', 'employer_name': 'Fictional Grove'},
             'quote': second, 'outcome': 'new', 'confidence': 'certain'}], text=text)
        grove = next(row for row in self.section('experience', working)['items'] if row['values']['employer_name'] == 'Fictional Grove')
        self.assertEqual(self.line('- Ran the fictional grove audit', working)['best_guess'], {'role_ref': grove['item_ref']})

    def test_saved_items_carry_their_missing_list_too(self):
        key = self.shared.canonical.create_private(self.owner, {'command_id': str(uuid4()), 'record_type': 'skill',
            'parent_key': None, 'values': {'name': 'Fictional Pruning'}})['record_key']
        working = self.organized()
        saved = self.find(key, working)
        self.assertEqual((saved['missing_required'], saved['needs_member_wording']), ([], False))

    def test_undo_details_labels_units_and_operation_type(self):
        working = self.organized()
        line = self.line('- Fictional Pruning', working)
        snapshot = self.service._load(self.owner)
        original = snapshot['proposals'][line['proposal_key']]
        source = snapshot['sources'][original['binding']['source_key']]
        unit_id = original['resume_conversation_v1']['unit_ids'][0]
        def unit():
            live = self.service._load(self.owner)['sources'][source['source_key']]
            return next(row for row in live['structured_values']['resume_conversation_v1']['source_units'] if row['unit_id'] == unit_id)
        placed = self.place(line, {'section': 'skills'})
        live = self.find(line['item_ref'])
        self.assertEqual((unit()['proposal_key'], unit()['disposition']), (live['proposal_key'], 'pending'))
        visibility = self.service.set_guide_visibility(self.owner, {'request_id': str(uuid4()), 'item_ref': live['item_ref'],
            'hidden': True, 'expected_working_set_token': self.service.working_set(self.owner)['working_set_token'],
            'expected_item_revision': live['revision']})
        with self.assertRaises(ResumeIntakeNotFoundError):
            self.undo({'operation_ref': 'place:' + visibility['request_id'], 'undo_token': placed['undo_token']})
        self.setUp()
        working = self.organized()
        line = self.line('- Fictional Pruning', working)
        original_meta = dict(self.service._load(self.owner)['proposals'][line['proposal_key']]['resume_conversation_v1'])
        self.undo(self.place(line, {'section': 'skills'}))
        back = self.line('- Fictional Pruning')
        restored = self.service._load(self.owner)['proposals'][back['proposal_key']]
        meta = restored['resume_conversation_v1']
        self.assertEqual((meta.get('presentation_section'), meta.get('placement')),
                         (original_meta.get('presentation_section'), original_meta.get('placement')))
        self.assertEqual(restored['proposed_values'], {'text': '- Fictional Pruning'}, 'Undo restores the line exactly')
        original_flag = self.service._load(self.owner)['proposals'][line['proposal_key']].get('requires_member_wording', True)
        self.assertEqual(restored['requires_member_wording'], original_flag, "Undo restores the original's wording check")
        self.assertEqual(self.line('- Fictional Pruning')['needs_member_wording'], original_flag)
        live_unit = next(row for row in self.service._load(self.owner)['sources'][restored['binding']['source_key']]
                         ['structured_values']['resume_conversation_v1']['source_units'] if row['unit_id'] == meta['unit_ids'][0])
        self.assertEqual((live_unit['proposal_key'], live_unit['disposition']), (restored['proposal_key'], 'unresolved'))

    def test_a_source_line_undo_releases_its_unit(self):
        working = self.organized(fail='provider_unavailable')
        line = self.line('- Fictional Pruning', working)
        source_key = line['evidence'][0]['source_key']
        def unit():
            live = self.service._load(self.owner)['sources'][source_key]
            return next(row for row in live['structured_values']['resume_conversation_v1']['source_units']
                        if row['unit_id'] == line['source_unit_ref'])
        placed = self.place(line, {'section': 'skills'})
        self.assertEqual(unit()['disposition'], 'pending')
        self.undo(placed)
        self.assertEqual((unit()['disposition'], unit().get('proposal_key')), ('unresolved', None))

    def test_a_placed_no_suggestion_line_saves_as_placed(self):
        working = self.organized(fail='provider_unavailable')
        line = self.line('- Fictional Pruning', working)
        self.place(line, {'section': 'skills'})
        self.assert_i1(self.find(line['item_ref']))
        self.assertEqual([row['values']['name'] for row in self.section('skills')['items'] if row['origin'] == 'saved'],
                         ['Fictional Pruning'])

    def test_a_superseded_source_or_storage_without_guide_support_refuses_before_any_effect(self):
        from unittest.mock import patch
        working = self.organized(fail='provider_unavailable')
        line = self.line('- Fictional Pruning', working)
        snapshot = self.service._load(self.owner)
        stale = self.service.working_set(self.owner)
        snapshot['sources'][line['evidence'][0]['source_key']]['state'] = 'superseded'
        self.service.repository.save_owner(self.owner, snapshot)
        before = self.stored()
        with self.assertRaises(ResumeIntakeConflictError):
            self.service.guide_place(self.owner, {'request_id': str(uuid4()), 'action': 'place', 'item_ref': line['item_ref'],
                'destination': {'section': 'skills'}, 'expected_working_set_token': stale['working_set_token'],
                'expected_item_revision': line['revision']}, read_working_set=lambda owner: stale)
        self.assertEqual(self.stored(), before)
        with patch.object(self.service.repository, 'supports_guide_first_arrival', False), \
                self.assertRaises(ResumeIntakeUnavailableError):
            self.place(line, {'section': 'skills'}, working=stale)

    def test_a_line_no_suggestion_accounts_for_can_be_placed_and_undone(self):
        working = self.organized(fail='provider_unavailable')
        line = self.line('- Fictional Pruning', working)
        self.assertEqual(line['origin'], 'source')
        self.assertEqual(line['best_guess'], {'section': 'skills'})
        placed = self.place(line, {'section': 'skills'})
        item = next(row for row in self.section('skills')['items'] if row['item_ref'] == line['item_ref'])
        self.assertEqual((item['origin'], item['record_type'], item['values']['name']), ('pending', 'skill', 'Fictional Pruning'))
        self.assertFalse(item['needs_member_wording'], 'Placing a no-suggestion line is the member choosing too')
        self.undo(placed)
        back = self.line('- Fictional Pruning')
        self.assertEqual((back['origin'], back['item_ref']), ('source', line['item_ref']))



class GuideB3cTests(unittest.TestCase):
    """B3c (map coordination 3d61ccf; plan 0271bb52): placement, restore, move safety, markers."""
    setup_shared = GuideReferenceCommandTests.setup_shared
    create = LookingAheadPlacementTests.create
    row = LookingAheadPlacementTests.row
    save = LookingAheadPlacementTests.save
    stage = GuideConversionTests.stage
    reviewed = GuideConversionTests.reviewed
    confirm = GuideConversionTests.confirm
    undo = GuideConversionTests.undo
    item = GuideConversionTests.item
    working = GuideConversionTests.working
    raw_draft = GuideConversionTests.raw_draft
    WORDS = {'title': 'Looking Ahead', 'wording': 'Lead port automation controls.', 'classification': 'work'}

    def entry(self, key):
        return self.shared.policy.get_entry(self.owner, key)['entry']

    def policy(self, kind, key, **extra):
        entry = self.entry(key)
        return self.shared.policy.commit(self.owner, {'request_id': str(uuid4()), 'type': kind, 'entry_key': key,
            'expected_content_version': entry['content_version'], 'expected_access_revision': entry['access_revision'],
            **extra})

    def delete(self, key):
        return self.policy('delete', key, dependent_keys=[])

    def restore(self, key):
        return self.policy('restore', key)

    def placed(self):
        return {row['record_key'] for row in self.shared.draft.get_workspace(self.owner)['items']
                if row.get('presentation_section') == 'looking_ahead'}

    def draft_maps(self):
        stored = self.shared.draft.repository.load_owner(self.owner)
        return dict(stored.get('presentation_placements') or {}), dict(stored.get('presentation_placements_retired') or {})

    def place_by_save(self, key):
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == key)
        return self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': key,
            'record_type': 'knowledge', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': dict(self.WORDS), 'presentation_section': 'looking_ahead'})

    # ---- one Looking Ahead entry (Q1)

    def test_a_second_placement_is_refused_by_create_and_by_save_and_a_re_save_passes(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        before = self.shared.draft.repository.load_owner(self.owner)
        with self.assertRaises(ResumeDraftConflictError) as by_create:
            self.create(dict(self.WORDS))
        self.assertEqual((by_create.exception.error_code, str(by_create.exception)),
                         ('looking_ahead_already_placed', 'Looking Ahead already has an entry. Your words are kept.'))
        other = self.create(dict(self.WORDS), placement=None)
        with self.assertRaises(ResumeDraftConflictError) as by_save:
            self.place_by_save(other)
        self.assertEqual(by_save.exception.error_code, 'looking_ahead_already_placed')
        self.assertEqual(self.placed(), {first})
        self.assertEqual(self.draft_maps()[0], {first: 'looking_ahead'}, 'Nothing was written by a refusal')
        self.save(first, {'wording': 'Second words.'})
        self.assertEqual(self.placed(), {first}, 'Re-saving the placed entry passes')
        self.assertTrue(before)

    def test_a_title_alone_is_not_a_placement_and_a_deleted_placement_does_not_count(self):
        self.setup_shared()
        self.create(dict(self.WORDS), placement=None)  # titled "Looking Ahead", not placed
        first = self.create(dict(self.WORDS))
        self.assertEqual(self.placed(), {first})
        self.delete(first)
        self.assertEqual(self.draft_maps(), ({}, {first: 'looking_ahead'}), 'B3t m1: delete removes the live placement')
        second = self.create(dict(self.WORDS))
        self.assertEqual(self.placed(), {second}, 'A deleted placement does not count')

    def test_an_existing_entry_can_be_placed_through_a_save(self):
        self.setup_shared()
        key = self.create(dict(self.WORDS), placement=None)
        self.place_by_save(key)
        self.assertEqual((self.placed(), self.draft_maps()[0]), ({key}, {key: 'looking_ahead'}))

    # ---- re-place on restore (Q2)

    def test_restore_into_an_empty_looking_ahead_places_it_again_and_the_next_save_keeps_it(self):
        from services.resume_draft_service import ResumeDraftConflictError
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.delete(key)
        self.assertEqual(self.placed(), set())
        restored = self.restore(key)
        self.assertEqual(restored['looking_ahead'], 'replaced')
        self.assertEqual(self.placed(), {key}, 'Derived at read: no draft write on restore')
        self.assertEqual(self.draft_maps(), ({}, {key: 'looking_ahead'}))
        with self.assertRaises(ResumeDraftConflictError) as renamed:
            self.save(key, {'title': 'Plans'})
        self.assertEqual(renamed.exception.error_code, 'looking_ahead_rename_unavailable', 'The guards see it too')
        with self.assertRaises(ResumeDraftConflictError) as second:
            self.create(dict(self.WORDS))
        self.assertEqual(second.exception.error_code, 'looking_ahead_already_placed')
        self.save(key, {'wording': 'Words after the restore.'})
        self.assertEqual(self.draft_maps(), ({key: 'looking_ahead'}, {}), 'The next save persists the placement')

    def test_restore_while_another_entry_is_placed_comes_back_unplaced_and_says_so(self):
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        second = self.create(dict(self.WORDS))
        restored = self.restore(first)
        self.assertEqual(restored['looking_ahead'], 'not_replaced')
        self.assertEqual(self.placed(), {second}, 'The one-entry rule wins')
        self.assertNotIn('presentation_section', self.row(first))
        self.save(first, {'title': 'My next step'})
        self.assertEqual(self.placed(), {second}, 'The unplaced entry can be renamed freely')

    def two_retired(self):
        """Two entries each placed in Looking Ahead in turn, then both deleted: both retired placements."""
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        second = self.create(dict(self.WORDS))
        self.delete(second)
        self.assertEqual(self.draft_maps(), ({}, {first: 'looking_ahead', second: 'looking_ahead'}))
        return first, second

    def claims(self):
        entries = self.shared.policy.repository.load_owner(self.owner)['entries']
        return {key: entry['looking_ahead_claim'] for key, entry in entries.items() if 'looking_ahead_claim' in entry}

    def test_the_first_restore_keeps_looking_ahead_in_either_order(self):
        for order in ('first_then_second', 'second_then_first'):
            with self.subTest(order=order):
                first, second = self.two_retired()
                one, two = (first, second) if order == 'first_then_second' else (second, first)
                self.assertEqual(self.restore(one)['looking_ahead'], 'replaced')
                self.assertEqual(self.claims(), {one: 1}, 'The claim is stored in the restore commit itself')
                self.assertEqual(self.restore(two)['looking_ahead'], 'not_replaced', 'A held claim counts as placed')
                self.assertEqual(self.claims(), {one: 1}, 'The second restore claims nothing')
                self.assertEqual(self.placed(), {one}, 'The first restore keeps it, whatever the order')
                self.assertEqual(self.draft_maps()[0], {}, 'Restore writes no draft placement')

    def test_a_delete_releases_the_claim_and_never_brings_back_the_other_entry(self):
        first, second = self.two_retired()
        self.restore(first)
        self.restore(second)
        self.delete(first)
        self.assertEqual(self.claims(), {}, 'A delete releases the claim')
        self.assertEqual(self.placed(), set(), 'The unclaimed entry is not placed by a later delete')
        third = self.create(dict(self.WORDS))
        self.assertEqual(self.placed(), {third}, 'Looking Ahead is empty, so a new entry can be placed')
        self.delete(third)
        self.assertEqual(self.restore(first)['looking_ahead'], 'replaced', 'Restoring again claims it again')
        self.assertEqual((self.placed(), self.claims()), ({first}, {first: 2}))

    def test_the_placement_rule_pins_states_no_current_path_produces(self):
        """Rule pins (writer mutants retired_returned_with_live, claim_without_retired_check, claims_include_deleted):
        stored states that today's paths never create, so a later path (an un-place, a migration) can't widen it."""
        from services.resume_draft_service import effective_placements
        LA = 'looking_ahead'
        self.assertEqual(effective_placements({'b': LA}, {'a': LA}, {'a', 'b'}, {'a': 1}), {'b'}, 'A live placement wins')
        self.assertEqual(effective_placements({}, {}, {'a'}, {'a': 1}), set(), 'A consumed claim places nothing')
        self.assertEqual(effective_placements({}, {'a': LA, 'b': LA}, {'a', 'b'}, {'b': 2, 'a': 1}), {'a'}, 'The first claim')
        self.assertEqual(effective_placements({}, {'a': LA}, {'a'}, {}), set(), 'An unclaimed retired copy stays unplaced')
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        snapshot = self.shared.policy.repository.load_owner(self.owner)
        snapshot['entries'][first]['looking_ahead_claim'] = 1
        self.shared.policy.repository.save_owner(self.owner, snapshot)
        self.assertEqual(self.shared.policy.looking_ahead_claims(self.owner), {}, "A deleted entry's claim is never read")

    def test_a_stale_claim_never_takes_the_place_back_after_a_delete(self):
        first, second = self.two_retired()
        self.restore(first)
        self.delete(first)
        self.assertEqual(self.restore(second)['looking_ahead'], 'replaced', 'Looking Ahead is empty again')
        self.assertEqual(self.restore(first)['looking_ahead'], 'not_replaced')
        self.assertEqual((self.placed(), self.claims()), ({second}, {second: 2}), 'The released claim stays released')

    def test_a_save_consumes_the_claim_and_a_later_delete_resurrects_nothing(self):
        first, second = self.two_retired()
        self.restore(first)
        self.restore(second)
        self.save(first, {'wording': 'Words after the restore.'})
        self.assertEqual(self.draft_maps(), ({first: 'looking_ahead'}, {second: 'looking_ahead'}),
                         'The save persists the place; the claim is consumed')
        self.delete(first)
        self.assertEqual(self.claims(), {})
        self.assertEqual(self.placed(), set(), 'Neither the stale claim nor the other retired copy places anything')

    def test_a_never_placed_restore_says_nothing_and_the_retired_map_is_never_public(self):
        import json
        self.setup_shared()
        plain = self.create({'title': 'Plans', 'wording': 'Fictional words.', 'classification': 'work'}, placement=None)
        self.delete(plain)
        self.assertNotIn('looking_ahead', self.restore(plain))
        key = self.create(dict(self.WORDS))
        self.shared.seed_publication(self.owner, [(key, True, False)])
        self.delete(key)
        public = json.dumps([self.shared.publication.owner_preview(self.owner),
                             self.shared.publication.read_publication_basis_for_owner(self.owner)], default=str)
        self.assertNotIn('presentation_placements_retired', public)
        restored = self.restore(key)
        self.assertEqual(self.claims(), {key: 1})
        shown = json.dumps([restored, self.shared.publication.owner_preview(self.owner), self.shared.policy.get_entry(self.owner, key),
                            self.shared.publication.read_publication_basis_for_owner(self.owner),
                            self.shared.draft.get_workspace(self.owner)], default=str)
        self.assertNotIn('looking_ahead_claim', shown, 'The restore claim is private policy state, never presented')

    def test_a_permanently_deleted_placement_never_comes_back(self):
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.delete(key)
        self.policy('permanently_delete', key)
        self.assertEqual(self.placed(), set())
        replacement = self.create(dict(self.WORDS))
        self.assertEqual(self.placed(), {replacement}, 'An inert retired key never blocks or presents')

    def test_a_my_data_rename_of_a_restored_placed_entry_is_refused_too(self):
        from services.entry_policy_service import EntryPolicyConflictError
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.delete(key)
        self.restore(key)
        entry = self.entry(key)
        with self.assertRaises(EntryPolicyConflictError) as renamed:
            self.shared.policy.commit(self.owner, {'request_id': str(uuid4()), 'type': 'edit', 'entry_key': key,
                'expected_content_version': entry['content_version'],
                'values': {'title': 'Plans', 'wording': self.WORDS['wording'], 'classification': 'work'}})
        self.assertEqual(renamed.exception.error_code, 'looking_ahead_rename_unavailable')

    def test_a_stale_live_placement_of_a_deleted_entry_never_counts(self):
        self.setup_shared()
        stale = self.create(dict(self.WORDS))
        policy = self.shared.policy.repository.load_owner(self.owner)
        policy['entries'][stale]['lifecycle'] = 'deleted'  # a delete that never reached the draft prune
        self.shared.policy.repository.save_owner(self.owner, policy)
        self.assertEqual(self.draft_maps()[0], {stale: 'looking_ahead'})
        fresh = self.create(dict(self.WORDS))
        self.assertEqual(self.placed(), {fresh})

    # ---- B3c round 2 (review 4d47364): F1 stale retired copy, m1 port, m2 Guide section, m4 non-shared save

    def routes(self):
        """The real routes (Flask app, fixture stores), with the placement port wired as the fixture's owner will."""
        import json
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        from tests.mvp1_acceptance_support import Mvp1AcceptanceServer
        server = Mvp1AcceptanceServer()
        server.__enter__()
        self.addCleanup(server.__exit__, None, None, None)
        server.shared.draft.placement_claims = server.shared.policy
        owner = 'g-member-a'

        def call(method, path, payload=None):
            request = Request(server.url + path, method=method, headers={
                'Content-Type': 'application/json', 'X-PeerSlate-Request': 'same-origin',
                'Cookie': 'mvp1-synthetic-owner=' + owner},
                data=json.dumps(payload).encode() if payload is not None else None)
            try:
                response = urlopen(request, timeout=10)
            except HTTPError as error:
                response = error
            with response:
                return response.status, json.load(response)

        class Client:
            def create(self, values=None, placed=True):
                payload = {'type': 'create_private_item', 'request_id': str(uuid4()), 'record_key': str(uuid4()),
                           'record_type': 'knowledge', 'values': dict(values or GuideB3cTests.WORDS)}
                if placed:
                    payload['presentation_section'] = 'looking_ahead'
                status, body = call('POST', '/api/resume-drafts/me/commands', payload)
                assert status == 200, (status, body)
                return payload['record_key']

            def policy(self, kind, key, **extra):
                status, body = call('GET', '/api/entry-policy/me/entries/' + key)
                entry = body['entry']
                return call('POST', '/api/entry-policy/me/commands', {'request_id': str(uuid4()), 'type': kind,
                    'entry_key': key, 'expected_content_version': entry['content_version'],
                    'expected_access_revision': entry['access_revision'], **extra})

            def delete(self, key):
                status, body = self.policy('delete', key, dependent_keys=[])
                assert status == 200, (status, body)

            def restore(self, key):
                status, body = self.policy('restore', key)
                assert status == 200, (status, body)
                return body.get('looking_ahead')

            def workspace_placed(self):
                status, body = call('GET', '/api/resume-drafts/me')
                return {row['record_key'] for row in body['items'] if row.get('presentation_section') == 'looking_ahead'}

            def guide(self):
                status, body = call('GET', '/api/resume-intake/me/guide/working-set')
                assert status == 200, (status, body)
                return body

        return Client()

    def test_f1_a_retired_copy_left_by_an_unplaced_restore_never_places_a_later_delete_and_restore(self):
        """The reviewer's six steps through the real routes: A must come back unplaced, and B must reclaim."""
        client = self.routes()
        a = client.create()                                                   # 1. A is placed, then deleted
        client.delete(a)
        b = client.create()                                                   # 2. B is created placed
        self.assertEqual(client.restore(a), 'not_replaced')                   # 3. A comes back unplaced; B holds it
        self.assertEqual(client.workspace_placed(), {b})
        client.delete(b)                                                      # 4. delete B (placed), then A (unplaced)
        client.delete(a)
        self.assertIsNone(client.restore(a), 'A was not placed when last deleted, so the restore says nothing')  # 5.
        self.assertEqual(client.workspace_placed(), set(), 'A comes back unplaced')
        self.assertEqual(client.restore(b), 'replaced', 'B was placed when deleted and Looking Ahead is empty')  # 6.
        self.assertEqual(client.workspace_placed(), {b})

    def entry_flags(self, key):
        entry = self.shared.policy.repository.load_owner(self.owner)['entries'][key]
        return entry.get('looking_ahead_retired'), entry.get('looking_ahead_claim')

    def test_f1_the_flag_follows_the_latest_delete_in_every_order(self):
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.assertEqual(self.entry_flags(key), (None, None))
        self.delete(key)
        self.assertEqual(self.entry_flags(key), (True, None), 'Placed at this delete')
        self.assertEqual(self.restore(key)['looking_ahead'], 'replaced')
        self.assertEqual(self.entry_flags(key), (None, 1), 'The flag is spent; the claim stands in for it')
        self.delete(key)
        self.assertEqual(self.entry_flags(key), (True, None), 'A claimed entry was presented as placed, so it is flagged')
        self.assertEqual(self.restore(key)['looking_ahead'], 'replaced', 'Claimed, deleted, restored: it reclaims')
        other = self.create(dict(self.WORDS), placement=None)
        self.delete(key)
        self.delete(other)
        self.assertEqual(self.entry_flags(other), (None, None), 'An unplaced entry is never flagged')
        self.assertNotIn('looking_ahead', self.restore(other), 'It says nothing')
        self.assertEqual(self.restore(key)['looking_ahead'], 'replaced')
        self.assertEqual(self.placed(), {key})

    def test_f1_a_permanent_delete_or_expiry_keeps_neither_flag_nor_claim(self):
        from datetime import timedelta
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        self.policy('permanently_delete', first)
        self.assertEqual(self.entry_flags(first), (None, None))
        second = self.create(dict(self.WORDS))
        self.delete(second)
        snapshot = self.shared.policy.repository.load_owner(self.owner)
        snapshot['entries'][second]['recover_until'] = self.shared.policy._now() - timedelta(days=1)
        self.shared.policy.repository.save_owner(self.owner, snapshot)
        from services.entry_policy_service import EntryPolicyNotFoundError
        with self.assertRaises(EntryPolicyNotFoundError):
            self.shared.policy.get_entry(self.owner, second)  # the read that sweeps an expired delete
        self.assertEqual(self.shared.policy.repository.load_owner(self.owner)['entries'][second]['lifecycle'], 'permanently_deleted')
        self.assertEqual(self.entry_flags(second), (None, None))

    def test_f1_rule_pins_for_a_stale_flag_a_stale_claim_and_a_missing_retired_copy(self):
        """States no current path produces (a later path or a migration could): none of them may place anything
        or say 'replaced' without a placement (writer mutants W03, W08, W11)."""
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        snapshot = self.shared.policy.repository.load_owner(self.owner)
        snapshot['entries'][key]['looking_ahead_retired'] = True  # a stale flag on an active, placed-by-map entry
        self.shared.policy.repository.save_owner(self.owner, snapshot)
        other = self.create(dict(self.WORDS), placement=None)
        snapshot = self.shared.policy.repository.load_owner(self.owner)
        snapshot['entries'][other]['looking_ahead_retired'] = True  # a stale flag on an active, unplaced entry
        self.shared.policy.repository.save_owner(self.owner, snapshot)
        self.delete(other)
        self.assertEqual(self.entry_flags(other), (None, None), 'A delete of an unplaced entry removes any stale flag')
        self.assertNotIn('looking_ahead', self.restore(other))
        self.delete(key)
        stored = self.shared.draft.repository.load_owner(self.owner)
        stored['presentation_placements_retired'] = {}  # the flag outlives its retired copy
        self.shared.draft.repository.save_owner(self.owner, stored)
        self.assertEqual(self.restore(key)['looking_ahead'], 'not_replaced', 'No retired copy: it cannot be replaced')
        self.assertEqual((self.placed(), self.claims()), (set(), {}), 'And nothing is claimed')
        self.delete(key)
        snapshot = self.shared.policy.repository.load_owner(self.owner)
        snapshot['entries'][key]['looking_ahead_claim'] = 5  # a claim stale on a deleted entry
        snapshot['entries'][key]['looking_ahead_retired'] = True
        self.shared.policy.repository.save_owner(self.owner, snapshot)
        self.policy('permanently_delete', key)
        self.assertEqual(self.entry_flags(key), (None, None), 'A permanent delete erases both')

    def test_m1_an_injected_port_wins_over_the_fallback(self):
        from types import SimpleNamespace
        from services.resume_draft_service import ResumeDraftService
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.delete(key)
        self.assertEqual(self.restore(key)['looking_ahead'], 'replaced')
        self.assertEqual(self.placed(), {key})
        def placed_by(port):
            draft = ResumeDraftService(repository=self.shared.draft.repository, catalog=self.shared.canonical,
                                       placement_claims=port)
            return {row['record_key'] for row in draft.get_workspace(self.owner)['items']
                    if row.get('presentation_section') == 'looking_ahead'}
        self.assertEqual(placed_by(None), {key}, 'TRANSITIONAL: no port falls back to the catalog\'s policy')
        self.assertEqual(placed_by(SimpleNamespace(looking_ahead_claims=lambda owner: {})), set(),
                         'An injected port wins over the fallback, even when it holds no claims')
        self.assertEqual(placed_by(SimpleNamespace(looking_ahead_claims=lambda owner: {key: 1})), {key})
        self.assertEqual(placed_by(self.shared.policy), {key})

    def test_f1_the_flag_is_never_presented_or_published(self):
        import json
        self.setup_shared()
        key = self.create(dict(self.WORDS))
        self.shared.seed_publication(self.owner, [(key, True, False)])
        self.delete(key)
        restored = self.restore(key)
        shown = json.dumps([restored, self.shared.policy.get_entry(self.owner, key), self.shared.policy.list_entries(self.owner),
                            self.shared.publication.owner_preview(self.owner),
                            self.shared.publication.read_publication_basis_for_owner(self.owner),
                            self.shared.draft.get_workspace(self.owner)], default=str)
        self.assertNotIn('looking_ahead_retired', shown)
        self.assertNotIn('looking_ahead_claim', shown)

    def test_m1_transitional_a_draft_without_the_port_gives_the_same_answer_through_its_catalog_policy(self):
        """TRANSITIONAL (manager ruling): until the C14 branch injects the port where it wires the draft, a draft built
        without it reads claims through its catalog's policy, so 8444 keeps placing. Same answer as the port."""
        from services.resume_draft_repository import InMemoryResumeDraftRepository
        from services.resume_draft_service import ResumeDraftService
        from tests.mvp1_acceptance_support import EntryPolicyCanonicalFixture
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        second = self.create(dict(self.WORDS))
        self.delete(second)
        self.assertEqual(self.restore(first)['looking_ahead'], 'replaced')
        self.assertEqual(self.restore(second)['looking_ahead'], 'not_replaced')

        def workspace_placed(draft):
            return {row['record_key'] for row in draft.get_workspace(self.owner)['items']
                    if row.get('presentation_section') == 'looking_ahead'}
        with_port = ResumeDraftService(repository=self.shared.draft.repository, catalog=self.shared.canonical,
                                       placement_claims=self.shared.policy)
        without_port = ResumeDraftService(repository=self.shared.draft.repository, catalog=self.shared.canonical)
        self.assertIsNone(without_port.placement_claims)
        self.assertEqual(workspace_placed(without_port), workspace_placed(with_port))
        self.assertEqual(workspace_placed(without_port), {first})
        # A draft that can place, with neither a port nor a policy behind its catalog, reads no claims and does not fail.
        bare = ResumeDraftService(repository=InMemoryResumeDraftRepository(),
                                  catalog=type('NoPolicyCatalog', (), {'list_items': lambda self, owner: [],
                                                                       'get_item': lambda self, owner, key: None})())
        self.assertEqual(bare._placement_claims(self.owner), {})
        # A placement through the port-less draft is allowed today (the fail-closed flip is deferred until C14 wires the port).
        key = self.create(dict(self.WORDS), placement=None)
        workspace = without_port.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == key)
        self.delete(first)
        without_port.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': key,
            'record_type': 'knowledge', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': dict(self.WORDS), 'presentation_section': 'looking_ahead'})
        self.assertIn(key, workspace_placed(without_port))

    def test_m1_a_replaced_restore_means_the_workspace_presents_the_entry_as_placed(self):
        """The reply and the workspace never disagree, in every state a restore can meet."""
        self.setup_shared()
        first = self.create(dict(self.WORDS))
        self.delete(first)
        second = self.create(dict(self.WORDS))
        plain = self.create({'title': 'Plans', 'wording': 'Fictional words.', 'classification': 'work'}, placement=None)
        self.delete(plain)
        seen = []
        for key in (first, plain):
            seen.append(self.restore(key).get('looking_ahead'))
            self.assertEqual(key in self.placed(), seen[-1] == 'replaced', (key, seen[-1]))
        self.delete(second)
        seen.append(self.restore(second).get('looking_ahead'))
        self.assertEqual(second in self.placed(), seen[-1] == 'replaced')
        self.assertEqual(seen, ['not_replaced', None, 'replaced'], 'Every outcome was exercised')
        self.assertNotIn('presentation_section', self.row(first))

    def test_m2_the_guide_presents_looking_ahead_from_the_placement_only(self):
        client = self.routes()
        title_only = client.create(placed=False)  # titled "Looking Ahead", never placed
        guide = client.guide()
        self.assertEqual([item['item_ref'] for item in guide['non_tab_items']], [], 'A title alone is not Looking Ahead')
        self.assertEqual([item['item_ref'] for item in guide['unplaced']], [title_only], 'Its natural section')
        placed = client.create()
        guide = client.guide()
        self.assertEqual([item['item_ref'] for item in guide['non_tab_items']], [placed])
        self.assertEqual([item['item_ref'] for item in guide['unplaced']], [title_only], 'Never a second Looking Ahead')
        client.delete(placed)
        holder = client.create()
        self.assertEqual(client.restore(placed), 'not_replaced')
        guide = client.guide()
        self.assertEqual([item['item_ref'] for item in guide['non_tab_items']], [holder])
        self.assertEqual({item['item_ref'] for item in guide['unplaced']}, {title_only, placed},
                         'A restored, unplaced entry is not a second Looking Ahead either')

    def test_m4_a_placing_save_on_a_store_without_shared_media_state_drops_the_retired_copy(self):
        from services.resume_draft_repository import InMemoryResumeDraftRepository
        from services.resume_draft_service import ResumeDraftService
        from tests.mvp1_acceptance_support import EntryPolicyCanonicalFixture
        self.setup_shared()
        draft = ResumeDraftService(repository=InMemoryResumeDraftRepository(),
                                   catalog=EntryPolicyCanonicalFixture(self.shared.policy), placement_claims=self.shared.policy)
        self.assertFalse(getattr(draft.repository, 'resume_media_state_present', False), 'The plain, non-shared path')
        key = self.create(dict(self.WORDS), placement=None)
        stored = draft.repository.load_owner(self.owner)
        stored['presentation_placements_retired'] = {key: 'looking_ahead'}
        draft.repository.save_owner(self.owner, stored)
        workspace = draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == key)
        draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': key,
            'record_type': 'knowledge', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': dict(self.WORDS), 'presentation_section': 'looking_ahead'})
        stored = draft.repository.load_owner(self.owner)
        self.assertEqual(stored['presentation_placements'], {key: 'looking_ahead'})
        self.assertEqual(stored.get('presentation_placements_retired') or {}, {}, 'The placing save spends the retired copy')

    # ---- deleting a moved item voids the move (Q3, R2-m1)

    def moved_skill(self):
        self.setup_shared()
        self.service.set_guide_references(self.owner, {'request_id': str(uuid4()), 'kind': 'highlights',
            'item_ref': None, 'references': [self.bullet],
            'expected_working_set_token': self.working()['working_set_token']})
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'A fictional project.'})
        return self.confirm(staged)

    def test_undo_after_deleting_the_moved_item_is_refused_and_never_restores_pruned_links(self):
        confirmed = self.moved_skill()
        self.delete(self.skill)
        self.assertNotIn(self.skill, self.raw_draft()[0], 'Delete voids the move: its overlay is gone')
        before = self.raw_draft()
        with self.assertRaises(ResumeIntakeConflictError) as refused:
            self.undo(confirmed)
        self.assertEqual(refused.exception.error_code, 'conversion_item_missing')
        self.assertEqual(self.raw_draft(), before, 'Nothing changed: no pruned link came back')

    def test_m3_undo_says_the_item_was_deleted_only_when_it_is_gone(self):
        """An overlay a later publish consumed is a stale Undo, not a falsely 'deleted' item."""
        confirmed = self.moved_skill()
        stored = self.shared.draft.repository.load_owner(self.owner)
        stored['items'].pop(self.skill)  # what a publish that consumes the overlay does (after D6c)
        self.shared.draft.repository.save_owner(self.owner, stored)
        before = self.raw_draft()
        with self.assertRaises(ResumeIntakeConflictError) as refused:
            self.undo(confirmed)
        self.assertEqual(refused.exception.error_code, 'stale_undo')
        self.assertEqual(self.raw_draft(), before)

    def test_a_restored_moved_item_is_back_as_its_original_type_and_never_stuck(self):
        confirmed = self.moved_skill()
        self.delete(self.skill)
        self.restore(self.skill)
        item = self.item(self.skill)
        self.assertEqual((item['record_type'], item.get('conversion')), ('skill', None), 'The original type, unmoved')
        before = self.raw_draft()
        with self.assertRaises(ResumeIntakeConflictError) as stale:
            self.undo(confirmed)
        self.assertEqual(stale.exception.error_code, 'stale_undo', 'B3c m3: the item is back, so this is a stale Undo')
        self.assertEqual(self.raw_draft(), before, 'No pruned link comes back')
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == self.skill)
        self.shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()), 'record_key': self.skill,
            'record_type': 'skill', 'expected_draft_version': workspace['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision'],
            'values': {'summary': 'Editable again.'}})
        self.assertEqual(self.row(self.skill)['proposed_values']['summary'], 'Editable again.', 'A save works')
        workspace = self.shared.draft.get_workspace(self.owner)
        row = next(r for r in workspace['items'] if r['record_key'] == self.skill)
        self.shared.draft.commit(self.owner, {'type': 'discard_item', 'request_id': str(uuid4()), 'record_key': self.skill,
            'expected_draft_version': workspace['draft_version'], 'expected_content_token': row['content_token'],
            'expected_access_revision': row['access_revision']})
        staged = self.stage(self.skill, 'project', {'project_name': 'Fictional skill', 'summary': 'Moved again.'})
        self.assertEqual(staged['outcome'], 'staged', 'A new move can start')

    # ---- markers (B3m m1) and the typed-item refusal (B3m m2)

    def test_one_leading_list_marker_is_dropped_only_when_whitespace_follows(self):
        from services.resume_guide_contract import placed_text
        stripped = {'- Led the team': 'Led the team', '– Led the team': 'Led the team', '— Led': 'Led',
                    '• Led': 'Led', '▪ Led': 'Led', '◦ Led': 'Led', '● Led': 'Led', '* Led': 'Led',
                    '1. Led': 'Led', '12) Led': 'Led', '- - Led': '- Led', '• 2. Led': '2. Led'}
        kept = ['-5% cost', '1.5 million users', '–3 days', 'Led the team', '-', '2020 award']
        for text, expected in stripped.items():
            self.assertEqual(placed_text(text), expected, text)
        for text in kept:
            self.assertEqual(placed_text(text), text, text)

    def test_only_a_line_or_a_bullet_can_be_placed(self):
        t = GuideB3mTests('test_an_unplaced_knowledge_line_has_no_missing_essentials')
        t.setUp()
        note = {'record_type': 'knowledge', 'values': {'title': 'Fictional note', 'wording': '- Fictional Pruning'},
                'quote': '- Fictional Pruning', 'outcome': 'new', 'confidence': 'certain', 'presentation_section': 'Unsorted'}
        working = t.organized([t.ROLE, note])
        line = next(row for row in working['unplaced'] if row['record_type'] == 'knowledge')
        before = t.stored()
        with self.assertRaises(ResumeIntakeConflictError) as refused:
            t.place(line, {'section': 'skills'}, working=working)
        self.assertEqual(str(refused.exception), 'Only a line or a bullet can be placed. Nothing changed.')
        self.assertEqual(t.stored(), before)

if __name__ == "__main__":
    unittest.main()
