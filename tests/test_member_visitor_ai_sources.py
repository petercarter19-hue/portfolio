import copy
import hashlib
import unittest

from services.member_visitor_ai_sources import build_sources, issue_preview, strict_json, PreviewBinding
from services.resume_publication_contracts import ContractError, UsePurpose, encode_canonical_source


SAVED_TEXT = 'Led a team of 4 in 2021; the pilot may reduce costs.'


def snapshot(*, owner='member-a', preview=False, display=True, ai=True):
    raw = encode_canonical_source({'canonical_type': 'role', 'summary': SAVED_TEXT})
    digest = hashlib.sha256(raw).hexdigest()
    return {
        'schema_version': 1, 'subject_key': owner, 'resume_key': 'resume:' + owner,
        'mode': 'owner_preview' if preview else 'guest', 'profile_revision': '0000000000000001',
        'sharing_enabled': not preview, 'sharing_epoch': 1, 'publication_revision': 1,
        'current_revision': 1, 'reviewed_digest': 'a' * 64, 'draft_revision': 2,
        'draft_digest': 'b' * 64, 'placement_digest': 'c' * 64, 'publication_media': {}, 'media': [],
        'entries': [{
            'owner_key': owner, 'entry_key': 'entry-a', 'canonical_type': 'role',
            'content_version': 3, 'access_revision': 4, 'resume_display': display, 'visitor_ai': ai,
            'lifecycle': 'active', 'canonical_revision': '0000000000000011', 'dependency_versions': ['none'],
            'content_hex': raw.hex(), 'content_sha256': digest, 'current_content_sha256': digest,
            'evidence_version_key': 'saved:entry-a:3', 'evidence_version': 3,
            'codec': 'resume-canonical-source.v1', 'canonical_token': '3',
            'evidence_content_version': 3, 'evidence_access_revision': 4,
            'evidence_display': display, 'evidence_ai': ai,
        }],
    }


class SourceTests(unittest.TestCase):
    def test_complete_media_versions_are_preserved_and_unready_media_denies(self):
        doc=snapshot()
        doc['media']=[{'slot':'story_banner','placement_version':2,'source_kind':'generated_illustration',
            'source_key':'catalog-a','source_revision':'3','asset_version':3,'catalog_revision':'3',
            'content_sha256':'e'*64,'readiness_sha256':'f'*64,'ready':True,'active':True}]
        result=build_sources(doc,slug='member-a')
        self.assertEqual(result.versions.media[0].asset_version,3)
        self.assertNotIn('catalog-a',result.sources[0].content)
        for field in ('ready','active'):
            changed=copy.deepcopy(doc); changed['media'][0][field]=False
            with self.assertRaises(ContractError): build_sources(changed,slug='member-a')
        del doc['media'][0]['readiness_sha256']
        with self.assertRaises(KeyError): build_sources(doc,slug='member-a')

    def test_display_and_ai_are_independent(self):
        for display in (False, True):
            for ai in (False, True):
                with self.subTest(display=display, ai=ai):
                    doc = snapshot(display=display, ai=ai)
                    if ai:
                        result = build_sources(doc, slug='member-a')
                        self.assertEqual(result.sources[0].content.encode(), bytes.fromhex(doc['entries'][0]['content_hex']))
                        self.assertEqual(result.context.purpose, UsePurpose.VISITOR_AI)
                    else:
                        with self.assertRaises(ContractError):
                            build_sources(doc, slug='member-a')

    def test_forbidden_stale_foreign_missing_or_malformed_inputs(self):
        for key, value in [('owner_key','member-b'),('canonical_type','raw_upload'),('canonical_type','pending_proposal'),
                           ('canonical_type','generated_illustration'),('lifecycle','deleted'),
                           ('evidence_access_revision',3),('evidence_content_version',2),('canonical_token','2'),
                           ('current_content_sha256','d'*64),('content_sha256','d'*64),
                           ('visitor_ai',1),('access_revision',None),('content_version',True)]:
            with self.subTest(key=key,value=value):
                doc=snapshot(); doc['entries'][0][key]=value
                with self.assertRaises((ContractError,TypeError,ValueError)):
                    build_sources(doc,slug='member-a')
        for key in ('sharing_epoch','draft_revision','entries','media','draft_digest'):
            doc=snapshot(); del doc[key]
            with self.assertRaises((ContractError,KeyError)):
                build_sources(doc,slug='member-a')
        for key,value in [('sharing_enabled',False),('schema_version',2),('resume_key','resume:member-b')]:
            doc=snapshot(); doc[key]=value
            with self.assertRaises(ContractError): build_sources(doc,slug='member-a')

    def test_preview_selects_saved_bytes_with_proposed_ai_choice_before_sharing(self):
        doc=snapshot(preview=True,ai=False,display=False)
        binding=issue_preview(doc,'member-a',2,(('entry-a',True),))
        result=build_sources(doc,owner='member-a',preview=binding)
        self.assertEqual(result.context.purpose,UsePurpose.OWNER_VISITOR_AI_PREVIEW)
        self.assertEqual(len(result.sources),1)
        self.assertFalse(result.evidence[0].visitor_ai_eligible) # proposed permission is not a saved grant
        with self.assertRaises(ContractError): build_sources(doc,slug='member-a',preview=binding)
        with self.assertRaises(ContractError): issue_preview(doc,'member-b',2,(('entry-a',True),))
        with self.assertRaises(ContractError): issue_preview(doc,'member-a',1,(('entry-a',True),))
        with self.assertRaises(ContractError): issue_preview(doc,'member-a',2,(('foreign',True),))
        with self.assertRaises(ContractError):
            PreviewBinding('member-a',2,(('entry-a',True),),'a'*64,'b'*64,object())

    def test_restriction_invalidates_preview_even_when_choice_proposes_ai(self):
        doc=snapshot(preview=True); binding=issue_preview(doc,'member-a',2,(('entry-a',True),))
        doc['entries'][0]['access_revision']+=1
        with self.assertRaises(ContractError): build_sources(doc,owner='member-a',preview=binding)

    def test_duplicate_members_and_json_keys_fail(self):
        doc=snapshot(); doc['entries'].append(copy.deepcopy(doc['entries'][0]))
        with self.assertRaises(ContractError): build_sources(doc,slug='member-a')
        with self.assertRaises(ContractError): strict_json('{"x":1,"x":2}')
        with self.assertRaises(ContractError): strict_json('{"x":NaN}')
