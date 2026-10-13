"""Catalog-shape guard on the actual synthetic server used by private 8444.

All state and providers are fake; this is neither SQL nor real-site proof.
"""
import unittest
from uuid import uuid4

from tests.mvp1_acceptance_support import Mvp1AcceptanceServer


class Mvp1CatalogShapeTests(unittest.TestCase):
    def setUp(self):
        self.server=Mvp1AcceptanceServer().__enter__()
        self.addCleanup(self.server.__exit__,None,None,None)
        self.owner='g-member-a'
        self.role_key,self.bullet_key,self.knowledge_key=(str(uuid4()) for _ in range(3))
        self.inputs={
            self.role_key:('role',None,{'role_title':'Engineer','employer_name':'Fictional Acorn Works'}),
            self.bullet_key:('accomplishment',self.role_key,{'wording':'Reviewed 12 fictional records.'}),
            self.knowledge_key:('knowledge',None,{'title':'A fictional story',
                'wording':'Helped at a community event.','classification':'personal'})}
        for key,(kind,parent,values) in self.inputs.items():
            self.server.shared.canonical.create_private(self.owner,{'command_id':str(uuid4()),'record_key':key,
                'record_type':kind,'parent_key':parent,'values':values})

    def test_every_consumed_catalog_field_survives_the_8444_adapter(self):
        catalog=self.server.shared.canonical
        rows={row['record_key']:row for row in catalog.list_items(self.owner)}
        self.assertEqual(set(rows),set(self.inputs))
        for key,(kind,parent,values) in self.inputs.items():
            expected={'record_key':key,'record_type':kind,'parent_key':parent,
                'content_version':1,'content_token':'0000000000000001','access_revision':1,
                'values':values,'editable':True,'blocked_reason':None,'save_mode':'canonical',
                'resume_display':False,'visitor_ai':False,'private_assistance_excluded':False,
                'publication_eligible':True}
            for field,value in expected.items():
                with self.subTest(record_type=kind,field=field):
                    self.assertIn(field,rows[key])
                    self.assertIs(type(rows[key][field]),type(value))
                    self.assertEqual(rows[key][field],value)
        self.assertEqual(catalog.list_items('g-member-b'),[])
        self.assertIsNone(catalog.get_item('g-member-b',self.bullet_key))
        # The real knowledge schema carries classification, not a fabricated section.
        self.assertNotIn('presentation_section',rows[self.knowledge_key]['values'])

    def test_actual_draft_save_keeps_original_values_and_exposes_the_overlay(self):
        draft=self.server.shared.draft
        before=draft.get_workspace(self.owner)
        current=next(row for row in before['items'] if row['record_key']==self.role_key)
        changed={'summary':'A new private fictional detail.'}
        draft.commit(self.owner,{'type':'save_item','request_id':str(uuid4()),'record_key':self.role_key,
            'record_type':'role','expected_draft_version':before['draft_version'],
            'expected_content_token':current['content_token'],'expected_access_revision':current['access_revision'],
            'values':changed})
        after=draft.get_workspace(self.owner)
        item=next(row for row in after['items'] if row['record_key']==self.role_key)
        # Draft saves merge the patch with canonical values and normalize the
        # complete role editor shape; the original catalog stays unchanged.
        proposed={'role_title':'Engineer','employer_name':'Fictional Acorn Works',
                  'summary':'A new private fictional detail.','location_text':None,
                  'employment_type':None,'start_date':None,'end_date':None,
                  'date_precision':'unknown','current_role':False}
        expected={'has_draft':True,'proposed_values':proposed,'values':self.inputs[self.role_key][2],
                  'content_token':'0000000000000001','access_revision':1}
        for field,value in expected.items():
            with self.subTest(field=field):
                self.assertIs(type(item[field]),type(value))
                self.assertEqual(item[field],value)
        self.assertEqual(after['draft_version'],before['draft_version']+1)
        self.assertEqual(self.server.shared.canonical.get_item(self.owner,self.role_key)['values'],self.inputs[self.role_key][2])


if __name__=='__main__':
    unittest.main()
