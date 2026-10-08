"""Real service/repository conversational contracts with a bounded fixture provider.

These tests prove persistence, targeting and recovery, not live model acceptance.
"""
import copy
import json
import unittest
from uuid import uuid4
from unittest.mock import Mock, patch
from itsdangerous import URLSafeTimedSerializer

from services.resume_intake_runtime import (
    PrivateResumeAssistanceService, SynthesisError, CONVERSATION_SCHEMA,
    CONVERSATION_PROMPT, BoundedPrivateResumeProvider,
)
from services.resume_intake_service import (
    ResumeIntakeConflictError, EDITOR_FIELDS, CONVERSATION_FIELDS,
    CONVERSATION_BULLET_FIELDS, conversation_field_contract,
)
from tests.test_my_data_intake_ai import build_service, add_request
from tests.test_my_data_intake_sources import extracted_pipeline, FakeUpload
from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter


class ContextPorts:
    def __init__(self, catalog):
        self.catalog = catalog
        self.excluded = set()
    def list_items(self, owner):
        return [{**row, 'content_version': 1} for row in self.catalog.list_items(owner)]
    def list_entries(self, owner):
        return [{'entry_key': row['record_key'], 'lifecycle': 'active', 'parent_key': None,
            'private_assistance_excluded': row['record_key'] in self.excluded,
            'content_version': 1, 'access_revision': row['access_revision']} for row in self.list_items(owner)]


def operation(context, *, op='revise_content', ref=None, record_type='role', values=None,
              clears=None, bullets=None, section='Experience', refs=None):
    turn = context['current_turn']
    return {'operation': op, 'target_ref': ref, 'record_type': record_type,
        'values': [{'field': key, 'value': value} for key, value in (values or {}).items()],
        'explicit_clears': clears or [], 'bullet_edits': bullets or [],
        'source_refs': refs or [{'source_key': turn['source_key'], 'unit_id': turn['units'][0]['unit_id']}],
        'presentation_section': section}


def check_conversation_schema(value, rule=CONVERSATION_SCHEMA):
    """Validate every keyword used by this fixed schema; fail closed on additions.

    This bounded witness checker is not a general JSON Schema implementation.
    """
    if set(rule) - {'type', 'enum', 'properties', 'required', 'additionalProperties', 'items'}:
        raise AssertionError('Unimplemented schema keyword')
    types = rule['type'] if isinstance(rule['type'], list) else [rule['type']]
    checks = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
        'string': lambda v: isinstance(v, str), 'number': lambda v: type(v) in (int, float),
        'integer': lambda v: type(v) is int, 'boolean': lambda v: type(v) is bool,
        'null': lambda v: v is None}
    if not any(checks[kind](value) for kind in types):
        raise AssertionError('Schema type mismatch')
    if 'enum' in rule and value not in rule['enum']:
        raise AssertionError('Schema enum mismatch')
    if isinstance(value, dict):
        if set(rule.get('required', [])) - set(value):
            raise AssertionError('Required field missing')
        properties = rule.get('properties', {})
        if rule.get('additionalProperties') is False and set(value) - set(properties):
            raise AssertionError('Unexpected property')
        for key, item in value.items():
            if key in properties:
                check_conversation_schema(item, properties[key])
    if isinstance(value, list) and 'items' in rule:
        for item in value:
            check_conversation_schema(item, rule['items'])


class ConversationTests(unittest.TestCase):
    owner = 'synthetic-conversation-owner'
    def setUp(self):
        self.intake = build_service()
        self.ports = ContextPorts(self.intake.draft_service.catalog)
        self.calls = []
        self.behavior = lambda context: {'response': 'Which detail should change?', 'next_question': '', 'operations': []}
        def provider(**kwargs):
            self.calls.append(copy.deepcopy(kwargs))
            self.assertIs(kwargs['response_schema'], CONVERSATION_SCHEMA)
            return self.behavior(kwargs['context'])
        self.assistance = PrivateResumeAssistanceService(draft_service=self.intake.draft_service,
            catalog=self.ports, policy_repository=self.ports, providers={'interview': provider},
            signer=URLSafeTimedSerializer('fixture-key-' * 5), limits={'maximum_task_bytes': 20000,
                'maximum_input_bytes': 65536, 'maximum_output_bytes': 100000,
                'maximum_field_bytes': 8000, 'proof_max_age_seconds': 900})
    def command(self, statement, ref=None):
        return {'request_id': str(uuid4()), 'expected_draft_version': self.intake.draft_service.get_workspace(self.owner)['draft_version'],
            'statement': statement, 'selected_target': ref, 'source_keys': []}
    def turn(self, statement, ref=None):
        return self.intake.converse(self.owner, self.command(statement, ref), assistance=self.assistance)
    def seed(self, record_type='role', **values):
        if record_type == 'role':
            defaults = {'role_title': 'Engineer', 'employer_name': 'Example Labs', 'location_text': 'Denver',
                'summary': 'Coordinated ten people; I was not their manager.\nA pilot reduced time 32%; not independently verified.',
                'start_date': '2020-01-01', 'end_date': '2026-09-01', 'date_precision': 'month', 'current_role': False}
            defaults.update(values); values = defaults
        result = self.intake.submit(self.owner, add_request(items=[{
            'client_key': 'manual', 'record_type': record_type, 'values': values, 'explicit_clears': []}]))
        return result['results'][0]['record_key']
    def confirm(self, proposal, decision='accept', values=None):
        payload = {'request_id': str(uuid4()), 'proposal_key': proposal['proposal_key'], 'decision': decision}
        if values is not None:
            payload['confirmed_values'] = values
        return self.intake.decide(self.owner, payload)

    def test_actual_empty_and_populated_azure_wire_has_backend_record_field_contract(self):
        from services.ai_foundation.errors import ProviderUnavailableError
        from tests.test_resume_intake_runtime import selected_private_settings
        for populated in (False, True):
            with self.subTest(populated=populated):
                self.setUp()
                if populated:
                    self.seed()
                token = Mock(side_effect=AssertionError('No credential read permitted'))
                transport = Mock()
                transport.post.side_effect = AssertionError('No HTTP permitted')
                bounded = BoundedPrivateResumeProvider('interview', settings=selected_private_settings('interview'),
                    database=None, token_provider=token, transport=transport)
                foundation = bounded._new_provider()
                original_builder, wires = foundation.structured_payload, []
                def build_wire(*args, **kwargs):
                    wire = original_builder(*args, **kwargs)
                    wires.append(wire)
                    return wire
                wire_builder = Mock(side_effect=build_wire)
                foundation.structured_payload = wire_builder
                foundation.respond = Mock(side_effect=AssertionError('No dispatch permitted'))
                bounded._new_provider = lambda: foundation
                self.assistance.providers['interview'] = bounded
                with patch.object(bounded.protections, 'reserve',
                        side_effect=ProviderUnavailableError('Synthetic stop before dispatch')) as reserve:
                    with self.assertRaises(ProviderUnavailableError):
                        self.turn('I am an Engineer at Example Labs.')
                self.assertEqual(wire_builder.call_count, 1)
                request = wire_builder.call_args.args[0]
                wire = wires[0]
                context = json.loads(request.input_text)['context']
                self.assertEqual(bool(context['targets']), populated)
                contract = context['field_contract']
                self.assertEqual(contract, conversation_field_contract())
                self.assertEqual(wire['text']['format']['schema'], CONVERSATION_SCHEMA)
                self.assertIn(CONVERSATION_PROMPT, wire['input'])
                self.assertIn('use only the EXACT value_fields', wire['input'])
                self.assertIn('a role uses role_title', wire['input'])
                self.assertIn('not biography or valid source_refs', wire['input'])
                self.assertNotIn('field_contract', json.dumps(context['materials']))
                for record_type, fields in contract['record_types'].items():
                    expected = set(EDITOR_FIELDS.get(record_type, ()))
                    if record_type == 'knowledge':
                        expected = {'title', 'wording', 'classification'}
                    if record_type == 'credential':
                        expected.add('resume_credential_wording')
                    self.assertEqual(set(fields['value_fields']), expected)
                    self.assertEqual(set(fields['explicit_clear_fields']), expected)
                    self.assertEqual(set(fields['bullet_edit_fields']), expected & CONVERSATION_BULLET_FIELDS)
                reserve.assert_called_once()
                token.assert_not_called()
                transport.post.assert_not_called()
                foundation.respond.assert_not_called()

    def test_field_schema_and_fresh_catalog_use_same_closed_names_without_aliases(self):
        props = CONVERSATION_SCHEMA['properties']['operations']['items']['properties']
        all_fields = set().union(*CONVERSATION_FIELDS.values())
        self.assertEqual(set(props['values']['items']['properties']['field']['enum']), all_fields)
        self.assertEqual(set(props['explicit_clears']['items']['enum']), all_fields)
        self.assertEqual(set(props['bullet_edits']['items']['properties']['field']['enum']), CONVERSATION_BULLET_FIELDS)
        self.assertNotIn('null', props['values']['items']['properties']['value']['type'])
        contract = conversation_field_contract()
        contract['record_types']['role']['value_fields'].append('job_title')
        self.assertNotIn('job_title', conversation_field_contract()['record_types']['role']['value_fields'])
        for field in ('job_title', 'employer', 'resume_credential_wording'):
            self.assertNotIn(field, EDITOR_FIELDS['role'])
        self.assertNotIn('knowledge', EDITOR_FIELDS)
        self.assertNotIn('resume_credential_wording', EDITOR_FIELDS['credential'])
        for field, value in (('job_title','Engineer'), ('role_title',None)):
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                check_conversation_schema({'field':field,'value':value}, props['values']['items'])
        with self.assertRaises(AssertionError):
            check_conversation_schema('job_title', props['explicit_clears']['items'])

    def test_exact_fields_add_and_correct_role_education_skill_and_credential(self):
        cases = [
            ('role', 'Experience', 'Engineer at Example Labs.',
                {'role_title':'Engineer','employer_name':'Example Labs'}, {'location_text':'Boulder'}),
            ('education', 'Education', 'Bachelor at Example University; completed.',
                {'title':'Bachelor','degree_name':'Bachelor','institution_name':'Example University',
                 'education_status':'completed'}, {'field_of_study':'Engineering'}),
            ('skill', 'Skills', 'Python for data analysis.', {'name':'Python'}, {'summary':'Python for reporting.'}),
            ('credential', 'Credentials', 'Example Certificate from Example Board; issued June 1, 2020. I am not licensed.',
                {'name':'Example Certificate','issuer':'Example Board','completion_status':'completed','issue_date':'2020-06-01'},
                {'resume_credential_wording':'Example Certificate from Example Board; issued June 1, 2020. I have not renewed it; I am not licensed.'}),
        ]
        for record_type, section, statement, values, correction in cases:
            with self.subTest(record_type=record_type):
                self.setUp()
                def add(ctx):
                    output = {'response':'Review the supplied words.','next_question':'','operations':[
                        operation(ctx, op='add_content', record_type=record_type, values=values, section=section)]}
                    check_conversation_schema(output)
                    return output
                self.behavior = add
                result = self.turn(statement)
                self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), [])
                proposal = result['proposals'][0]
                approved = self.confirm(proposal)
                key = approved['item']['record_key']
                before = copy.deepcopy(self.intake.draft_service.catalog.list_items(self.owner))
                def revise(ctx):
                    output = {'response':'Review the correction.','next_question':'','operations':[
                        operation(ctx, ref='record:'+key, record_type=record_type, values=correction, section=section)]}
                    check_conversation_schema(output)
                    return output
                self.behavior = revise
                revised = self.turn('Correct this detail: '+str(next(iter(correction.values()))), 'record:'+key)['proposals'][0]
                self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), before)
                self.confirm(revised)
                workspace = self.intake.draft_service.get_workspace(self.owner)
                item = next(row for row in workspace['items'] if row['record_key'] == key)
                effective = {**item['values'], **(item.get('proposed_values') or {})}
                if record_type == 'credential':
                    binding = self.intake.get_workspace(self.owner)['resume_credential_bindings'][0]
                    note = next(row for row in workspace['items'] if row['record_key'] == binding['supplement_key'])
                    self.assertEqual((note.get('proposed_values') or note['values'])['wording'], correction['resume_credential_wording'])
                    self.assertEqual(effective['name'], values['name'])
                else:
                    for name, value in correction.items():
                        self.assertEqual(effective[name], value)

    def test_knowledge_fields_correct_work_and_personal_without_source_catalog_refs(self):
        for section, classification in (('Professional summary','work'), ('My Story','personal')):
            with self.subTest(classification=classification):
                self.setUp()
                key = str(uuid4())
                self.intake.draft_service.catalog.create_private(self.owner, {'record_key':key,
                    'record_type':'knowledge','values':{'title':'Introduction','wording':'Original words.',
                    'classification':classification}})
                wording = 'Corrected words with the limitation intact.'
                self.behavior = lambda ctx: {'response':'Review your words.','next_question':'','operations':[
                    operation(ctx, ref='record:'+key, record_type='knowledge', section=section,
                        values={'title':'Corrected introduction','wording':wording,'classification':classification})]}
                proposal = self.turn('Correct my introduction to '+wording)['proposals'][0]
                check_conversation_schema(self.behavior(self.calls[-1]['context']))
                self.confirm(proposal)
                item = self.intake.draft_service.get_workspace(self.owner)['items'][0]
                self.assertEqual(item['proposed_values']['wording'], wording)
                self.assertEqual(item['proposed_values']['classification'], classification)

    def test_wire_union_does_not_allow_fields_from_another_record_type_in_backend(self):
        for record_type, wrong_field in (('role','title'), ('education','role_title'),
                ('skill','issuer'), ('credential','employer_name'), ('knowledge','current_role')):
            with self.subTest(record_type=record_type):
                self.setUp(); self.seed()
                def invalid(ctx):
                    output = {'response':'Review.','next_question':'','operations':[
                        operation(ctx, op='add_content', record_type=record_type, values={wrong_field:'Incorrect'})]}
                    # A shared schema enum is intentionally a union. The actual
                    # type-specific backend predicate still rejects this name.
                    check_conversation_schema(output)
                    return output
                self.behavior = invalid
                self._assert_failed_diagnostic(self.command('Supplied synthetic content.'),
                    'operation_contract','value_field')

    def test_catalog_keeps_explicit_clear_omission_and_false_distinct(self):
        key = self.seed()
        before = self.intake.draft_service.get_workspace(self.owner)['items'][0]['values']
        self.behavior = lambda ctx: {'response':'Review these changes.','next_question':'','operations':[
            operation(ctx, ref='record:'+key, values={'current_role':False}, clears=['location_text'])]}
        proposal = self.turn('Clear the location; this is not my current role.')['proposals'][0]
        check_conversation_schema(self.behavior(self.calls[-1]['context']))
        self.assertIs(proposal['proposed_values']['current_role'], False)
        self.assertEqual(proposal['explicit_clears'], ['location_text'])
        self.assertNotIn('employer_name', proposal['proposed_values'])
        self.confirm(proposal)
        current = self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']
        self.assertIsNone(current['location_text'])
        self.assertIs(current['current_role'], False)
        self.assertEqual(current['employer_name'], before['employer_name'])

    def test_record_incorrect_and_unknown_field_names_remain_rejected_and_no_retry(self):
        cases = [({'title':'Engineer'}, [], [], 'value_field'),
            ({'job_title':'Engineer'}, [], [], 'value_field'),
            ({}, ['title'], [], 'clear_fields'), ({}, ['job_title'], [], 'clear_fields'),
            ({'resume_credential_wording':'Unrelated wording.'}, [], [], 'value_field'),
            ({}, [], [{'action':'exclude','field':'wording','index':0,
                'expected_text':'Original words.','replacement':None}], 'bullet_edit_shape')]
        for values, clears, bullets, reason in cases:
            with self.subTest(values=values, clears=clears, bullets=bullets):
                self.setUp(); key = self.seed()
                self.behavior = lambda ctx: {'response':'Review.','next_question':'','operations':[
                    operation(ctx, ref='record:'+key, values=values, clears=clears, bullets=bullets)]}
                self._assert_failed_diagnostic(self.command('Correct the Engineer entry.'), 'operation_contract', reason)
        self.setUp(); self.seed()
        def catalog_ref(ctx):
            return {'response':'Review.','next_question':'','operations':[
                operation(ctx, op='add_content', values={'role_title':'Engineer'},
                    refs=[{'source_key':'field_contract','unit_id':'role_title'}])]}
        self.behavior = catalog_ref
        self._assert_failed_diagnostic(self.command('Engineer at Example Labs.'), 'operation_contract', 'source_ref_binding')

    def test_revision_is_durable_and_untouched_fields_remain_after_confirmation(self):
        key = self.seed()
        before = self.intake.draft_service.get_workspace(self.owner)['items'][0]['values']
        self.behavior = lambda ctx: {'response': 'I changed the team size.', 'next_question': '', 'operations': [
            operation(ctx, ref='record:' + key, bullets=[{'action': 'revise', 'field': 'summary', 'index': 0,
                'expected_text': before['summary'].splitlines()[0],
                'replacement': 'Coordinated eight people; I was not their manager.'}])]}
        result = self.turn('It was eight people, not ten.', 'record:' + key)
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner)['items'][0]['values'], before)
        proposal = self.intake.get_workspace(self.owner)['pending_proposals'][0]
        self.assertEqual(proposal, result['proposals'][0])
        self.confirm(proposal)
        item = self.intake.draft_service.get_workspace(self.owner)['items'][0]
        self.assertIn('eight people; I was not their manager', item['proposed_values']['summary'])
        for field in ('location_text', 'start_date', 'end_date', 'date_precision', 'current_role'):
            self.assertEqual(item['proposed_values'][field], before[field])
        self.assertIn('not independently verified', item['proposed_values']['summary'])
        self.assertFalse(item['resume_display']); self.assertFalse(item['visitor_ai'])

    def test_existing_record_repeated_pending_revision_preserves_baseline_and_clears(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response':'Clear location.', 'next_question':'', 'operations':[
            operation(ctx, ref=ctx['selected_target'], clears=['location_text'])]}
        first = self.turn('Clear the location.', 'record:'+key)['proposals'][0]
        self.behavior = lambda ctx: {'response':'Change employer.', 'next_question':'', 'operations':[
            operation(ctx, ref=ctx['selected_target'], values={'employer_name':'Second Labs'})]}
        second = self.turn('Actually use Second Labs.', 'proposal:'+first['proposal_key'])['proposals'][0]
        target = next(row for row in self.calls[-1]['context']['targets'] if row['target_ref']=='proposal:'+first['proposal_key'])
        self.assertIsNone(target['values']['location_text'])
        self.assertIn('not independently verified', target['values']['summary'])
        self.assertEqual(second['explicit_clears'], ['location_text'])
        self.behavior = lambda ctx: {'response':'Use Fort Collins.', 'next_question':'', 'operations':[
            operation(ctx, ref=ctx['selected_target'], values={'location_text':'Fort Collins'})]}
        third = self.turn('Use Fort Collins.', 'proposal:'+second['proposal_key'])['proposals'][0]
        self.assertEqual(third['explicit_clears'], [])
        self.confirm(third)
        values = self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']
        self.assertEqual(values['location_text'], 'Fort Collins')
        self.assertEqual(values['employer_name'], 'Second Labs')
        self.assertEqual(values['start_date'], '2020-01-01')
        self.assertIn('not their manager', values['summary'])

    def test_mixed_unit_permissions_cover_all_pending_and_approved_records_after_reordering(self):
        for approvals in (0, 1, 2):
            with self.subTest(approvals=approvals):
                self.setUp(); secret=self.seed(role_title='Secret Engineer'); public=self.seed(role_title='Public Engineer')
                self.behavior=lambda ctx:{'response':'SecretBase or Boston?', 'next_question':'SecretBase or Boston?', 'operations':[
                    operation(ctx,ref='record:'+secret,values={'location_text':'SecretBase'}),
                    operation(ctx,ref='record:'+public,values={'location_text':'Boston'})]}
                result=self.turn('Change Secret Engineer location to SecretBase and Public Engineer location to Boston.')
                for proposal in result['proposals'][:approvals]: self.confirm(proposal)
                snapshot=self.intake.repository.load_owner(self.owner)
                unit=snapshot['sources'][result['source_key']]['structured_values']['resume_conversation_v1']['source_units'][0]
                self.assertEqual(unit['disposition'],'approved' if approvals==2 else 'pending')
                if approvals==2:self.assertEqual(set(unit['record_keys']),{secret,public})
                snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
                # Exercise legacy reconstruction too, without changing facts.
                for source in snapshot['sources'].values():
                    for unit in (source['structured_values'].get('resume_conversation_v1') or {}).get('source_units') or []:
                        unit.pop('record_keys',None);unit.pop('proposal_keys',None)
                self.intake.repository.save_owner(self.owner,snapshot)
                self.ports.excluded.add(secret)
                self.behavior=lambda ctx:{'response':'Next?', 'next_question':'', 'operations':[]}
                self.turn('What can I add?')
                self.assertNotIn('SecretBase',str(self.calls[-1]['context']))
                self.assertTrue(any(row['target_ref']=='record:'+public for row in self.calls[-1]['context']['targets']))

    def test_mixed_unit_revision_retains_all_dependents_and_separate_permitted_unit_survives(self):
        secret=self.seed(role_title='Secret Engineer');public=self.seed(role_title='Public Engineer')
        self.behavior=lambda ctx:{'response':'Two changes.', 'next_question':'','operations':[
            operation(ctx,ref='record:'+secret,values={'location_text':'SecretBase'}),
            operation(ctx,ref='record:'+public,values={'location_text':'Boston'})]}
        first=self.turn('Change Secret Engineer to SecretBase and Public Engineer to Boston.')
        self.behavior=lambda ctx:{'response':'Revise the secret entry.', 'next_question':'','operations':[
            operation(ctx,ref='proposal:'+first['proposals'][0]['proposal_key'],values={'location_text':'OtherSecretBase'})]}
        revised=self.turn('Actually use OtherSecretBase.')['proposals'][0]
        self.confirm(first['proposals'][1])
        unit=self.intake.repository.load_owner(self.owner)['sources'][first['source_key']]['structured_values']['resume_conversation_v1']['source_units'][0]
        self.assertEqual(unit['disposition'],'pending')
        self.confirm(revised)
        self.behavior=lambda ctx:{'response':'Public detail.', 'next_question':'','operations':[
            operation(ctx,ref='record:'+public,values={'location_text':'Cambridge'})]}
        self.turn('Public Engineer location is Cambridge.')
        self.ports.excluded.add(secret)
        self.behavior=lambda ctx:{'response':'Next?', 'next_question':'','operations':[]}
        self.turn('What next?')
        context=self.calls[-1]['context']
        self.assertNotIn('SecretBase',str(context));self.assertIn('Cambridge',str(context['materials']))

    def test_assistant_question_is_permission_bound_control_and_story_intent_is_server_loaded(self):
        key=self.seed(); question='Was the temporary location Boulder or Denver?'
        self.behavior=lambda ctx:{'response':'Choose the location.', 'next_question':question, 'operations':[]}
        self.turn('Help me finish this entry.')
        self.turn('The first one.')
        context=self.calls[-1]['context']
        self.assertEqual(context['prior_turns'][0]['assistant_control']['question'],question)
        self.assertNotIn(question,str(context['materials']))
        state={'screen':'input','selected_proposal_key':None,'correction_target_key':None,'correction_draft':None,
            'correction_inputs':{},'proposal_drafts':{},'question':'Untrusted client factual prose', 'context':'',
            'guide_hidden':False,'conversation_intent':'story','manual_type':None,'manual_fields':{},'pending_conversation':None}
        self.intake.save_draft(self.owner,{'request_id':str(uuid4()),'expected_version':None,'text':None,
            'items':[],'attachments':[],'guide_state':state})
        self.ports.excluded.add(key);self.turn('What about outside work?')
        context=self.calls[-1]['context']
        self.assertEqual(context['guide_control']['section'],'My Story')
        self.assertNotIn(question,str(context));self.assertNotIn('Untrusted client factual prose',str(context))

    def test_upload_pending_full_context_revision_supersedes_before_approval(self):
        text = 'Experience\nEngineer, Example Labs.\nCoordinated ten people; not their manager.\nA pilot reduced time 32%; not independently verified.'
        self.intake._document_pipeline = extracted_pipeline(text)
        self.intake._extraction_adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}, 'quote': text.split('\n', 1)[1],
            'outcome': 'new', 'confidence': 'certain'}])
        self.intake.submit(self.owner, add_request(attachments=[{'client_key': 'doc', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'resume.txt'}]), files={'doc': FakeUpload('text/plain', text.encode())})
        old = self.intake.get_workspace(self.owner)['pending_proposals'][0]
        self.behavior = lambda ctx: {'response': 'Updated the first role.', 'next_question': '', 'operations': [
            operation(ctx, ref='proposal:' + old['proposal_key'], bullets=[{'action': 'revise', 'field': 'summary',
                'index': 0, 'expected_text': 'Coordinated ten people; not their manager.',
                'replacement': 'Coordinated eight people; not their manager.'}])]}
        result = self.turn('Change the first role to eight people.')
        self.assertIn('A pilot reduced time 32%; not independently verified.', str(self.calls[-1]['context']))
        self.assertEqual(len(self.intake.get_workspace(self.owner)['pending_proposals']), 1)
        with self.assertRaises(ResumeIntakeConflictError): self.confirm(old)
        self.confirm(result['proposals'][0])
        saved = self.intake.draft_service.get_workspace(self.owner)['items'][0]
        self.assertIn('eight people', saved['values']['summary'])
        self.assertIn('not independently verified', saved['values']['summary'])

    def upload_document(self, text, employer):
        self.intake._document_pipeline = extracted_pipeline(text)
        self.intake._extraction_adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': employer}, 'quote': text.split('\n', 1)[1],
            'outcome': 'new', 'confidence': 'certain'}])
        self.intake.submit(self.owner, add_request(attachments=[{'client_key': 'doc', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'resume.txt'}]), files={'doc': FakeUpload('text/plain', text.encode())})

    def test_a_twenty_year_history_of_thirty_saved_items_still_gets_a_turn_with_each_item_read_once(self):
        # The saved items used to be packed about six times over (canonical copy, targets, text twice), so a long career
        # stopped the Guide at about 25 items. Each is now sent once, the selected record first and in full.
        from services.resume_intake_runtime import _json_size
        sentence = 'Led the unit through a staffing change and kept every patient and family informed and safe. '
        keys = []
        for index in range(6):
            keys.append(self.seed('role', role_title='Nurse role %d' % index, employer_name='Hospital %d' % index, location_text='City',
                                  summary='Marker%dStart. ' % index + sentence * 8 + 'Marker%dEnd.' % index,
                                  start_date='2004-01-01', end_date='2008-01-01', date_precision='month', current_role=False))
        for index in range(4):
            self.seed('education', title='Degree %d' % index, institution_name='School %d' % index, education_status='completed',
                      summary='Education text %d. ' % index + sentence * 2, end_date='2011-01-01', date_precision='year')
        for index in range(20):
            self.seed('skill', name='Skill %d' % index, summary='Skill text %d. ' % index + sentence * 2)
        snapshot = self.intake._load(self.owner)
        canonical = self.assistance._context(self.owner, [], allow_empty=True)
        whole = self.intake._conversation_view(snapshot, canonical)
        self.assertGreater(_json_size(whole), self.assistance.limits['maximum_input_bytes'] // 2)
        self.behavior = lambda ctx: {'response': 'Which detail should change?', 'next_question': '', 'operations': []}
        self.turn('Please add the location Portland to this role.', 'record:' + keys[5])
        sent = self.calls[-1]['context']
        text = json.dumps(sent, ensure_ascii=False)
        self.assertLess(len(text.encode('utf-8')), self.assistance.limits['maximum_input_bytes'])
        self.assertEqual(len([t for t in sent['targets'] if t['target_ref'].startswith('record:')]), 30)
        for index in range(5):
            self.assertEqual(text.count('Marker%dStart' % index), 1, index)   # sent once, not once per copy
        self.assertEqual(text.count('Marker5Start'), 2)                       # the selected record: its values and its numbered lines
        self.assertNotIn('sources', sent['canonical'])

    def test_when_the_budget_is_tight_the_selected_record_stays_full_and_the_rest_shrink_to_identity(self):
        from services.resume_intake_runtime import model_facing_context, _json_size
        long_text = 'word ' * 400
        targets = [{'target_ref': 'record:%d' % n, 'record_type': 'role',
                    'values': {'role_title': 'Role %d' % n, 'employer_name': 'Employer %d' % n, 'summary': long_text},
                    'bullets': {'summary': [{'index': 0, 'text': long_text}]}, 'excluded_bullets': []} for n in range(30)]
        context = {'canonical': {'draft_version': 3, 'sources': ['x' * 5000]}, 'targets': targets,
                   'selected_target': 'record:3', 'materials': [], 'prior_turns': []}
        packed = model_facing_context(context, budget=12000)
        self.assertLessEqual(_json_size(packed), 12000)
        by_ref = {t['target_ref']: t for t in packed['targets']}
        self.assertIn('summary', by_ref['record:3']['values'])
        self.assertTrue(by_ref['record:3']['bullets']['summary'])
        self.assertTrue(by_ref['record:29'].get('brief'))
        self.assertEqual(by_ref['record:29']['values']['role_title'], 'Role 29')
        self.assertNotIn('summary', by_ref['record:29']['values'])

    def test_a_turn_reads_the_latest_upload_not_the_whole_workspace(self):
        # A workspace with many earlier unfinished uploads must not make every turn too large:
        # the Guide reads the current batch, and earlier items are left out of the context.
        filler = '\n'.join('Earlier unfinished line %d about warehouse planning and safety.' % n for n in range(120))
        for number in range(12):
            self.upload_document('Experience\nEngineer, Earlier Employer %d.\n%s\nOld marker %d.' % (number, filler, number),
                                 'Earlier Employer %d' % number)
        current = 'Experience\nEngineer, Current Employer.\nCurrent unique duties.'
        self.upload_document(current, 'Current Employer')
        snapshot = self.intake._load(self.owner)
        canonical = self.assistance._context(self.owner, [], allow_empty=True)
        whole = len(json.dumps(self.intake._conversation_view(snapshot, canonical), ensure_ascii=False).encode('utf-8'))
        self.assertGreater(whole, self.assistance.limits['maximum_input_bytes'], 'the fixture must be too large unbounded')
        pending = self.intake.get_workspace(self.owner)['pending_proposals']
        latest = next(row for row in pending if (row['proposed_values'] or {}).get('employer_name') == 'Current Employer')
        self.behavior = lambda ctx: {'response': 'Which detail should change?', 'next_question': '', 'operations': []}
        self.turn('Please add the location Denver to this role.', 'proposal:' + latest['proposal_key'])
        sent = self.calls[-1]['context']
        text = json.dumps(sent, ensure_ascii=False)
        self.assertIn('Current unique duties.', text)
        self.assertNotIn('Old marker', text)
        self.assertNotIn('Earlier Employer', text)
        self.assertLess(len(text.encode('utf-8')), self.assistance.limits['maximum_input_bytes'])

    def test_question_stop_and_ambiguous_remove_never_become_biography(self):
        for statement in ('Remove that.', 'Stop here.', 'What should I include next?'):
            result = self.turn(statement)
            self.assertFalse(result['proposals'])
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner)['items'], [])
        self.assertEqual(len(self.intake.get_workspace(self.owner)['conversation_turns']), 3)

    def test_validated_skip_exposes_replayable_control_and_preserves_pending_review(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Review this location.', 'next_question': '',
            'operations': [operation(ctx, ref='record:' + key, values={'location_text': 'Boulder'})]}
        proposal = self.turn('Change my location to Boulder.')['proposals'][0]
        pending = self.intake.get_workspace(self.owner)['pending_proposals']
        draft = self.intake.draft_service.get_workspace(self.owner)
        def stop(ctx):
            control = operation(ctx, op='skip_topic'); control['source_refs'] = []
            return {'response': 'This exchange can end; your earlier work is kept.',
                'next_question': 'This question must not restart the stopped exchange.', 'operations': [control]}
        self.behavior = stop
        command = self.command("Don't worry about it.", 'proposal:' + proposal['proposal_key'])
        result = self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertIs(result.get('topic_skipped'), True)
        self.assertEqual(result['next_question'], '')
        self.assertEqual(result['proposals'], [])
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], pending)
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner), draft)
        replay = self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertTrue(replay['replayed']); self.assertIs(replay['topic_skipped'], True)
        self.assertEqual(len(self.calls), 2)
        source = self.intake.repository.load_owner(self.owner)['sources'][result['source_key']]
        self.assertIs(source['structured_values']['resume_conversation_v1']['topic_skipped'], True)
        self.behavior = lambda ctx: {'response': 'Which detail?', 'next_question': '', 'operations': []}
        self.assertIs(self.turn('Which detail can I add?')['topic_skipped'], False)

    def test_replay_hydrates_current_revision_and_never_redispatches(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Changed location.', 'next_question': '',
            'operations': [operation(ctx, ref='record:' + key, values={'location_text': 'Boulder'})]}
        command = self.command('Change my location to Boulder.')
        result = self.intake.converse(self.owner, command, assistance=self.assistance)
        self.confirm(result['proposals'][0])
        replay = self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(replay['replayed']); self.assertEqual(replay['proposals'], [])
        altered = {**command, 'statement': 'Different words'}
        with self.assertRaises(SynthesisError): self.intake.converse(self.owner, altered, assistance=self.assistance)

    def test_timeout_reservation_cannot_repeat_paid_call(self):
        self.behavior = lambda ctx: (_ for _ in ()).throw(TimeoutError('synthetic'))
        command = self.command('Help me organize my experience.')
        with self.assertRaises(TimeoutError): self.intake.converse(self.owner, command, assistance=self.assistance)
        with self.assertRaises(SynthesisError): self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])

    def test_source_purge_redacts_dependent_turn_and_replay_cannot_resurrect(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Changed private location.', 'next_question': '',
            'operations': [operation(ctx, ref='record:' + key, values={'location_text': 'Boulder'})]}
        first_command = self.command('Change my location to Boulder.')
        first = self.intake.converse(self.owner, first_command, assistance=self.assistance)
        self.behavior = lambda ctx: {'response': 'I retained Boulder.', 'next_question': '', 'operations': []}
        self.turn('What did I just change?')
        self.intake.purge_source(self.owner, {'request_id': str(uuid4()), 'source_key': first['source_key']})
        snapshot = self.intake.repository.load_owner(self.owner)
        self.assertNotIn('Boulder', str(snapshot))
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])
        with self.assertRaises(SynthesisError): self.intake.converse(self.owner, first_command, assistance=self.assistance)

    def test_canonical_changes_during_call_and_stale_overlay_confirmation_refuse(self):
        key = self.seed()
        def provider(ctx):
            self.intake.draft_service.catalog.bump_access(self.owner, key)
            return {'response': 'Changed.', 'next_question': '', 'operations': [operation(ctx, ref='record:' + key, values={'location_text': 'Boulder'})]}
        self.behavior = provider
        with self.assertRaises(SynthesisError): self.turn('Change location to Boulder.')
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])

    def test_source_purge_redacts_durable_guide_and_refuses_old_autosave_or_purged_bindings(self):
        from services.resume_intake_service import ResumeIntakeValidationError
        key=self.seed()
        self.behavior=lambda ctx:{'response':'Private Boulder remains a suggestion.','next_question':'',
            'operations':[operation(ctx,ref='record:'+key,values={'location_text':'Private Boulder'})]}
        command=self.command('Change my location to Private Boulder.')
        turn=self.intake.converse(self.owner,command,assistance=self.assistance)
        proposal=turn['proposals'][0]['proposal_key']
        state={'screen':'correction','selected_proposal_key':proposal,'correction_target_key':proposal,
            'correction_draft':None,'correction_inputs':{proposal:command['statement']},
            'proposal_drafts':{proposal:{'type':'role','role':{'location_text':'Private Boulder'}}},
            'question':'Private Boulder?','context':'Private Boulder remains a suggestion.',
            'guide_hidden':False,'conversation_intent':None,'manual_type':None,'manual_fields':{},
            'pending_conversation':command,'seen_questions':['Private Boulder?'], 'navigation_history':[
                {'screen':'input','text':'Private Boulder','question':'Private Boulder?','context':'Private Boulder remains a suggestion.',
                    'conversation_intent':None,'selected_proposal_key':proposal}]}
        payload={'request_id':str(uuid4()),'expected_version':None,'text':command['statement'],
            'items':[],'attachments':[],'guide_state':state}
        saved=self.intake.save_draft(self.owner,payload)['draft']
        self.intake.purge_source(self.owner,{'request_id':str(uuid4()),'source_key':turn['source_key']})
        snapshot=self.intake.repository.load_owner(self.owner)
        self.assertNotIn('Private Boulder',str(snapshot))
        current=self.intake.get_draft(self.owner)['draft']
        self.assertEqual(current['guide_state']['navigation_history'],[])
        self.assertGreater(current['version'],saved['version'])
        with self.assertRaises(ResumeIntakeConflictError):self.intake.save_draft(self.owner,payload)
        with self.assertRaises(ResumeIntakeValidationError):
            self.intake.save_draft(self.owner,{**payload,'request_id':str(uuid4()),'expected_version':current['version']})
        self.assertEqual(self.intake.get_draft(self.owner)['draft'],current)

    def test_discard_and_recreate_keeps_monotonic_draft_version_against_old_device(self):
        payload={'request_id':str(uuid4()),'expected_version':None,'text':'Original unsent words.',
            'items':[],'attachments':[]}
        first=self.intake.save_draft(self.owner,payload)['draft']
        self.intake.discard_draft(self.owner,{'request_id':str(uuid4()),'expected_version':first['version']})
        recreated=self.intake.save_draft(self.owner,{**payload,'request_id':str(uuid4()),'text':'Current words.'})['draft']
        self.assertGreater(recreated['version'],first['version'])
        with self.assertRaises(ResumeIntakeConflictError):
            self.intake.save_draft(self.owner,{**payload,'request_id':str(uuid4()),'expected_version':first['version']})
        self.assertEqual(self.intake.get_draft(self.owner)['draft']['text'],'Current words.')

    def test_purge_redacts_latest_interleaved_guide_draft_without_repeating_source_versions(self):
        from tests.test_my_data_drafts import InterleavingResumeIntakeRepository
        import copy
        original = self.intake.repository
        repository = InterleavingResumeIntakeRepository()
        repository.save_owner(self.owner, original.load_owner(self.owner))
        self.intake.repository = repository
        key = self.seed()
        self.behavior = lambda ctx: {'response':'Private Boulder.', 'next_question':'',
            'operations':[operation(ctx,ref='record:'+key,values={'location_text':'Private Boulder'})]}
        command = self.command('Change my location to Private Boulder.')
        turn = self.intake.converse(self.owner,command,assistance=self.assistance)
        proposal = turn['proposals'][0]['proposal_key']
        state = {'screen':'input','selected_proposal_key':proposal,'correction_target_key':None,
            'correction_draft':None,'correction_inputs':{proposal:'Private Boulder'},
            'proposal_drafts':{},'question':'Private Boulder?','context':'Private Boulder.',
            'guide_hidden':False,'conversation_intent':None,'manual_type':'skill',
            'manual_fields':{'resume-intake-skill':'Acknowledged unrelated skill'},
            'pending_conversation':command,'seen_questions':[], 'navigation_history':[]}
        first = self.intake.save_draft(self.owner,{'request_id':str(uuid4()),'text':'Old unrelated words',
            'guide_state':state})['draft']
        # A reentrant same-owner draft ACK occurs at the actual commit boundary.
        # Its unrelated words must survive while its purged proposal copies go.
        newer = {'request_id':str(uuid4()),'expected_version':first['version'],
            'text':'Acknowledged newer unrelated words','guide_state':copy.deepcopy(state)}
        repository.before_next_save = lambda: self.intake.save_draft(self.owner,newer)
        other = 'unrelated-owner'
        self.intake.save_draft(other,{'request_id':str(uuid4()),'text':'Other owner intact'})
        source_version = repository.load_owner(self.owner)['sources'][turn['source_key']]['version']
        purge = {'request_id':str(uuid4()),'source_key':turn['source_key']}
        self.intake.purge_source(self.owner,purge)
        current = self.intake.get_draft(self.owner)['draft']
        self.assertEqual(current['text'],'Acknowledged newer unrelated words')
        self.assertEqual(current['guide_state']['manual_fields']['resume-intake-skill'],'Acknowledged unrelated skill')
        self.assertGreater(current['version'], first['version'] + 1)
        self.assertNotIn('Private Boulder',str(repository.load_owner(self.owner)))
        self.assertEqual(repository.load_owner(self.owner)['sources'][turn['source_key']]['version'],source_version+1)
        self.assertTrue(self.intake.purge_source(self.owner,purge)['replayed'])
        self.assertEqual(self.intake.get_draft(self.owner)['draft'],current)
        self.assertEqual(self.intake.get_draft(other)['draft']['text'],'Other owner intact')
        with self.assertRaises(ResumeIntakeConflictError): self.intake.save_draft(self.owner,newer)

    def test_purge_invalidates_and_redacts_transitively_derived_pending_turns(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response':'Changed private wording.', 'next_question':'', 'operations':[
            operation(ctx, ref='record:' + key, values={'location_text':'Private Boulder'})]}
        first = self.turn('Change location to Private Boulder.')
        self.confirm(first['proposals'][0])
        self.behavior = lambda ctx: {'response':'I retained Private Boulder.', 'next_question':'', 'operations':[
            operation(ctx, ref='record:' + key, values={'summary':'Private Boulder; qualified pilot.'})]}
        second = self.turn('Revise the wording using my private location.')
        self.turn('What did that change?')
        self.intake.purge_source(self.owner, {'request_id':str(uuid4()), 'source_key':first['source_key']})
        snapshot = self.intake.repository.load_owner(self.owner)
        self.assertNotIn('Private Boulder', str(snapshot))
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])
        with self.assertRaises(ResumeIntakeConflictError): self.confirm(second['proposals'][0])
        # Raw-source purge does not delete independently approved canonical facts.
        self.assertIn('Private Boulder', str(self.intake.draft_service.get_workspace(self.owner)['items']))

    def test_private_ai_exclusion_removes_canonical_record_and_approved_original_units(self):
        key = self.seed()
        self.ports.excluded.add(key)
        self.turn('What could I add?')
        self.assertNotIn('Coordinated ten people', str(self.calls[-1]['context']))
        self.assertEqual([t for t in self.calls[-1]['context']['targets'] if t['target_ref'].startswith('record:')], [])

    def test_excluded_credential_limitation_blocks_parent_edit_before_dispatch(self):
        from tests.test_resume_onboarding_coverage import ResumeOnboardingCoverageTests
        intake, owner, proposal, command = ResumeOnboardingCoverageTests().credential_proposal()
        intake.decide(owner,command)
        binding = intake.get_workspace(owner)['resume_credential_bindings'][0]
        ports = ContextPorts(intake.draft_service.catalog)
        ports.excluded.add(binding['supplement_key'])
        assistance = PrivateResumeAssistanceService(draft_service=intake.draft_service,
            catalog=ports,policy_repository=ports,providers={'interview':lambda **kw:self.calls.append(kw)},
            signer=self.assistance.signer,limits=self.assistance.limits)
        snapshot = intake.repository.load_owner(owner)
        view = intake._conversation_view(snapshot,assistance._context(owner,[],allow_empty=True))
        self.assertNotIn('record:'+binding['credential_key'],[t['target_ref'] for t in view['targets']])
        self.assertNotIn('not currently licensed',str(view))
        with self.assertRaises(SynthesisError) as refused:
            intake.converse(owner,{'request_id':str(uuid4()),'expected_draft_version':0,
                'statement':'Correct the issuer.','selected_target':'record:'+binding['credential_key'],
                'source_keys':[]},assistance=assistance)
        self.assertEqual(refused.exception.code,'not_found')
        self.assertEqual(self.calls,[])
        self.assertEqual(intake.repository.load_owner(owner),snapshot)

    def test_bad_target_or_bullet_does_not_partially_supersede_anything(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Changed.', 'next_question': '', 'operations': [
            operation(ctx, ref='record:' + key, bullets=[{'action': 'exclude', 'field': 'summary', 'index': 1,
                'expected_text': 'Not the supplied bullet', 'replacement': None}])]}
        with self.assertRaises(SynthesisError): self.turn('Exclude the second bullet.')
        self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])

    def test_explicit_clear_preserves_unspecified_values_and_false_boolean(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Cleared location.', 'next_question': '',
            'operations': [operation(ctx, ref='record:' + key, values={'current_role': False}, clears=['location_text'])]}
        proposal = self.turn('Clear my location; the role is not current.')['proposals'][0]
        self.assertEqual(proposal['explicit_clears'], ['location_text'])
        self.confirm(proposal)
        item = self.intake.draft_service.get_workspace(self.owner)['items'][0]
        self.assertIsNone(item['proposed_values']['location_text'])
        self.assertFalse(item['proposed_values']['current_role'])
        self.assertEqual(item['proposed_values']['end_date'], '2026-09-01')

    def test_saved_bullet_exclusion_can_be_undone_after_an_unrelated_saved_date_change(self):
        key = self.seed()
        original = self.intake.draft_service.get_workspace(self.owner)['items'][0]['values']
        bullet = original['summary'].splitlines()[1]
        self.behavior = lambda ctx: {'response':'Excluded just the pilot bullet.', 'next_question':'', 'operations':[
            operation(ctx, ref='record:'+key, bullets=[{'action':'exclude','field':'summary','index':1,
                'expected_text':bullet,'replacement':None}])]}
        self.confirm(self.turn('Exclude the pilot bullet.')['proposals'][0])
        self.behavior = lambda ctx: {'response':'Corrected the start month.', 'next_question':'', 'operations':[
            operation(ctx, ref='record:'+key, values={'start_date':'2020-03-01','date_precision':'month'})]}
        self.confirm(self.turn('The start month was March 2020.')['proposals'][0])
        saved = self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']
        self.assertNotIn('pilot',saved['summary'])
        self.assertEqual(saved['start_date'],'2020-03-01')
        self.behavior = lambda ctx: {'response':'Restored only the excluded bullet.', 'next_question':'', 'operations':[
            operation(ctx, ref='record:'+key, bullets=[{'action':'include','field':'summary','index':1,
                'expected_text':bullet,'replacement':None}])]}
        self.confirm(self.turn('Undo the pilot bullet exclusion.')['proposals'][0])
        saved = self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']
        self.assertEqual(saved['summary'],original['summary'])
        self.assertEqual(saved['start_date'],'2020-03-01')
        self.assertEqual(saved['end_date'],original['end_date'])
        snapshot=self.intake.repository.load_owner(self.owner)
        snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
        self.intake.repository.save_owner(self.owner,snapshot)
        view=self.intake._conversation_view(self.intake.repository.load_owner(self.owner),
            self.assistance._context(self.owner,[],allow_empty=True))
        target=next(row for row in view['targets'] if row['target_ref']=='record:'+key)
        self.assertEqual(target['excluded_bullets'],[])
        self.assertEqual(target['values']['summary'],original['summary'])
        self.assertEqual(target['values']['start_date'],'2020-03-01')
        # A legacy history without chronology must not claim a bullet is
        # removed when it is already present in the approved entry.
        for row in snapshot['proposals'].values():
            row['resume_conversation_v1'].pop('decision_order');row['decided_at']=None
        self.intake.repository.save_owner(self.owner,snapshot)
        conflict=next(row for row in self.intake.get_workspace(self.owner)['resume_decision_conflicts'] if row['effect']=='bullets')
        base={'request_id':str(uuid4()),'record_key':key,'effect':'bullets','history_token':conflict['history_token']}
        from services.resume_intake_service import ResumeIntakeValidationError
        incorrect=next(row for row in conflict['choices'] if row['value'])
        with self.assertRaises(ResumeIntakeValidationError):
            self.intake.review_resume_history(self.owner,{**base,'proposal_key':incorrect['proposal_key']})
        correct=next(row for row in conflict['choices'] if not row['value'])
        pending=self.intake.review_resume_history(self.owner,{**base,'proposal_key':correct['proposal_key']})
        self.confirm(pending['proposals'][0])
        view=self.intake._conversation_view(self.intake.repository.load_owner(self.owner),
            self.assistance._context(self.owner,[],allow_empty=True))
        target=next(row for row in view['targets'] if row['target_ref']=='record:'+key)
        self.assertEqual(target['excluded_bullets'],[])
        self.assertEqual(target['values']['summary'],original['summary'])

    def test_whole_record_exclusion_and_explicit_restore_do_not_delete_or_duplicate_canonical_content(self):
        key=self.seed()
        self.behavior=lambda ctx: {'response':'Excluded from the private Resume.','next_question':'','operations':[
            operation(ctx, op='exclude_content', ref='record:'+key)]}
        result=self.confirm(self.turn('Exclude the Engineer role.')['proposals'][0])
        self.assertEqual(result['outcome'],'excluded')
        self.assertEqual(len(self.intake.draft_service.catalog.list_items(self.owner)),1)
        self.assertEqual(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key],True)
        self.assertTrue(next(t for t in self.intake._conversation_view(self.intake.repository.load_owner(self.owner),
            self.assistance._context(self.owner,[],allow_empty=True))['targets'] if t['target_ref']=='record:'+key)['resume_excluded'])
        self.behavior=lambda ctx: {'response':'Restored that same role.','next_question':'','operations':[
            operation(ctx, op='restore_content', ref='record:'+key)]}
        result=self.confirm(self.turn('Restore the Engineer role.')['proposals'][0])
        self.assertEqual(result['outcome'],'restored')
        self.assertEqual(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key],False)
        self.assertFalse(next(t for t in self.intake._conversation_view(self.intake.repository.load_owner(self.owner),
            self.assistance._context(self.owner,[],allow_empty=True))['targets'] if t['target_ref']=='record:'+key)['resume_excluded'])
        self.assertEqual(len(self.intake.draft_service.catalog.list_items(self.owner)),1)

    def saved_inclusion_history(self):
        key=self.seed()
        for op, statement in (('exclude_content','Exclude this Engineer role.'),
                              ('restore_content','Include this Engineer role again.')):
            self.behavior=lambda ctx, op=op:{'response':'Review this choice.','next_question':'','operations':[
                operation(ctx,op=op,ref='record:'+key)]}
            self.confirm(self.turn(statement)['proposals'][0])
        return key

    def test_equal_decision_clocks_and_json_key_reordering_keep_newest_approved_choice(self):
        key=self.saved_inclusion_history()
        snapshot=self.intake.repository.load_owner(self.owner)
        orders=[]
        for row in snapshot['proposals'].values():
            orders.append(row['resume_conversation_v1']['decision_order'])
            row['decided_at']=row['created_at']='2026-10-04T00:00:00+00:00'
        self.assertEqual(sorted(orders),[1,2])
        snapshot=json.loads(json.dumps(snapshot,sort_keys=True))
        snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
        self.intake.repository.save_owner(self.owner,snapshot)
        self.assertFalse(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_decision_conflicts'],[])
        self.behavior=lambda ctx:{'response':'Still included.','next_question':'','operations':[]}
        self.turn('Is the role included?')
        self.assertFalse(next(row for row in self.calls[-1]['context']['targets']
            if row['target_ref']=='record:'+key)['resume_excluded'])
        self.assertEqual(len(self.intake.draft_service.catalog.list_items(self.owner)),1)

    def test_legacy_distinct_acceptance_timestamps_and_explicit_revision_chain_survive_reordering(self):
        key=self.saved_inclusion_history()
        snapshot=self.intake.repository.load_owner(self.owner)
        rows=sorted(snapshot['proposals'].values(),key=lambda row:row['resume_conversation_v1']['decision_order'])
        for index,row in enumerate(rows):
            row['resume_conversation_v1'].pop('decision_order')
            row['decided_at']='2026-10-04T00:00:0'+str(index)+'+00:00'
        snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
        self.intake.repository.save_owner(self.owner,snapshot)
        self.assertFalse(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        # A recorded accepted revision relation supplies chronology even when
        # legacy timestamps are missing; source creation alone never does.
        for row in rows:
            row.pop('decided_at',None);row.pop('created_at',None)
        rows[1]['resume_conversation_v1']['revision_of']=rows[0]['proposal_key']
        self.intake.repository.save_owner(self.owner,snapshot)
        self.assertFalse(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_decision_conflicts'],[])

    def test_ambiguous_legacy_choices_require_current_review_and_explicit_approval_then_survive_restart(self):
        for clock in (None,'2026-10-04T00:00:00+00:00'):
            with self.subTest(clock=clock):
                self.setUp()
                key=self.saved_inclusion_history()
                original=self.intake.draft_service.catalog.list_items(self.owner)
                snapshot=self.intake.repository.load_owner(self.owner)
                for row in snapshot['proposals'].values():
                    row['resume_conversation_v1'].pop('decision_order')
                    row['decided_at']=clock;row['created_at']=clock
                snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
                self.intake.repository.save_owner(self.owner,snapshot)
                workspace=self.intake.get_workspace(self.owner)
                conflict=next(row for row in workspace['resume_decision_conflicts'] if row['effect']=='inclusion')
                self.assertNotIn(key,dict(workspace['resume_excluded_records']))
                with self.assertRaises(ResumeIntakeConflictError) as refused:
                    self.turn('What should change?')
                self.assertEqual(refused.exception.error_code,'history_review_required')
                choice=next(row for row in conflict['choices'] if row['value'] is False)
                command={'request_id':str(uuid4()),'record_key':key,'effect':'inclusion',
                    'history_token':conflict['history_token'],'proposal_key':choice['proposal_key']}
                pending=self.intake.review_resume_history(self.owner,command)
                self.assertTrue(self.intake.get_workspace(self.owner)['resume_decision_conflicts'])
                self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner),original)
                replay=self.intake.review_resume_history(self.owner,command)
                self.assertTrue(replay['replayed']);self.assertEqual(replay['proposals'],pending['proposals'])
                approved=self.confirm(pending['proposals'][0])
                self.assertEqual(approved['outcome'],'reviewed')
                self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner),original)
                durable=json.loads(json.dumps(self.intake.repository.load_owner(self.owner),sort_keys=True))
                durable['proposals']=dict(reversed(list(durable['proposals'].items())))
                from services.resume_intake_repository import InMemoryResumeIntakeRepository
                restarted=InMemoryResumeIntakeRepository();restarted.save_owner(self.owner,durable)
                self.intake.repository=restarted
                self.assertEqual(self.intake.get_workspace(self.owner)['resume_decision_conflicts'],[])
                self.assertFalse(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
                self.assertEqual(self.intake.review_resume_history(self.owner,command)['proposals'],[])
                self.assertEqual(len(self.calls),2)

    def test_section_binding_uses_last_approved_decision_after_key_reordering(self):
        key=str(uuid4())
        self.intake.draft_service.catalog.create_private(self.owner,{'record_key':key,'record_type':'knowledge',
            'values':{'title':'Private introduction','wording':'My complete approved wording.','classification':'work'}})
        for title,section in (('Professional introduction','Professional summary'),('Contact information','Contact details')):
            self.behavior=lambda ctx,title=title,section=section:{'response':'Review the placement.','next_question':'',
                'operations':[operation(ctx,ref='record:'+key,record_type='knowledge',values={'title':title},section=section)]}
            self.confirm(self.turn('Change the title to '+title+'.')['proposals'][0])
        snapshot=self.intake.repository.load_owner(self.owner)
        snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
        self.intake.repository.save_owner(self.owner,snapshot)
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_section_bindings'][key],'Contact details')
        current=self.intake.draft_service.get_workspace(self.owner)['items'][0]
        self.assertEqual(current['proposed_values']['wording'],'My complete approved wording.')

    def test_legacy_review_refuses_changed_record_cross_owner_and_edited_choice_without_losing_truth(self):
        key=self.saved_inclusion_history()
        snapshot=self.intake.repository.load_owner(self.owner)
        for row in snapshot['proposals'].values():
            row['resume_conversation_v1'].pop('decision_order');row['decided_at']=None
        self.intake.repository.save_owner(self.owner,snapshot)
        conflict=next(row for row in self.intake.get_workspace(self.owner)['resume_decision_conflicts'] if row['effect']=='inclusion')
        choice=next(row for row in conflict['choices'] if row['value'] is False)
        command={'request_id':str(uuid4()),'record_key':key,'effect':'inclusion',
            'history_token':conflict['history_token'],'proposal_key':choice['proposal_key']}
        with self.assertRaises(ResumeIntakeConflictError):
            self.intake.review_resume_history('different-owner',command)
        pending=self.intake.review_resume_history(self.owner,command)['proposals'][0]
        duplicate=self.intake.review_resume_history(self.owner,{**command,'request_id':str(uuid4())})
        self.assertEqual(duplicate['proposals'][0]['proposal_key'],pending['proposal_key'])
        from services.resume_intake_service import ResumeIntakeValidationError
        with self.assertRaises(ResumeIntakeValidationError):
            self.confirm(pending,values={'summary':'Changed wording that was not reviewed.'})
        self.intake.draft_service.catalog.bump_access(self.owner,key)
        before=self.intake.draft_service.catalog.list_items(self.owner)
        with self.assertRaises(ResumeIntakeConflictError): self.confirm(pending)
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner),before)
        self.assertTrue(self.intake.get_workspace(self.owner)['resume_decision_conflicts'])

    def test_sql_adapter_does_not_inherit_saved_choice_review_capability(self):
        from services.resume_intake_repository import SqlResumeIntakeRepository
        from services.resume_intake_service import ResumeIntakeUnavailableError
        from unittest.mock import Mock
        database=Mock()
        self.intake.repository=SqlResumeIntakeRepository(database=database)
        with self.assertRaises(ResumeIntakeUnavailableError):
            self.intake.review_resume_history(self.owner,{'request_id':str(uuid4()),'record_key':str(uuid4()),
                'effect':'inclusion','history_token':'a'*64,'proposal_key':str(uuid4())})
        self.assertEqual(database.mock_calls,[])


    def _assert_failed_diagnostic(self, command, stage, reason, code='invalid_output'):
        from services.resume_intake_runtime import conversation_failure_diagnostic
        before = copy.deepcopy(self.intake.draft_service.catalog.list_items(self.owner))
        with self.assertRaises(SynthesisError) as caught:
            self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(caught.exception.code, code)
        expected = {'schema_version': 1, 'stage': stage, 'reason': reason}
        self.assertEqual(conversation_failure_diagnostic(caught.exception), expected)
        snapshot = self.intake.repository.load_owner(self.owner)
        source = next(row for row in snapshot['sources'].values()
            if (row.get('structured_values') or {}).get('resume_conversation_v1', {}).get('request_id') == command['request_id'])
        meta = source['structured_values']['resume_conversation_v1']
        self.assertEqual(meta['turn_state'], 'failed')
        self.assertEqual(meta['failure_diagnostic'], expected)
        self.assertEqual(source['text'], command['statement'])
        self.assertEqual(meta['source_units'][0]['text'], command['statement'])
        self.assertNotIn('response', meta)
        self.assertNotIn('next_question', meta)
        self.assertNotIn('proposal_keys', meta)
        self.assertEqual(snapshot['proposals'], {})
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), before)
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(SynthesisError) as replay:
            self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(replay.exception.code, 'unavailable')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.intake.repository.load_owner(self.owner), snapshot)
        return meta

    def test_diagnostics_distinguish_response_rules_without_retaining_output(self):
        cases = [('shape', {'response': 'MODEL_PRIVATE_MARKER'}, 'invalid_output'),
            ('operations_type', {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':{}}, 'invalid_output'),
            ('operation_count', {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':[{}]*25}, 'invalid_output'),
            ('response_text_type', {'response':None,'next_question':'','operations':[]}, 'invalid'),
            ('response_text_empty', {'response':' ','next_question':'','operations':[]}, 'invalid'),
            ('question_text_type', {'response':'MODEL_PRIVATE_MARKER','next_question':None,'operations':[]}, 'invalid')]
        for reason, output, code in cases:
            with self.subTest(reason=reason):
                self.setUp(); self.seed()
                self.behavior = lambda ctx, output=output: output
                meta = self._assert_failed_diagnostic(self.command('Engineer at Example Labs. OWNER_PRIVATE_MARKER.'),
                    'response_contract', reason, code)
                encoded = json.dumps(meta['failure_diagnostic'])
                self.assertNotIn('MODEL_PRIVATE_MARKER', encoded)
                self.assertNotIn('OWNER_PRIVATE_MARKER', encoded)

    def test_diagnostics_distinguish_operation_rules_and_keep_canonical_truth(self):
        def invalid(ctx, case):
            row = operation(ctx, op='add_content', values={'role_title':'Engineer'})
            if case == 'value_field': row['values'] = [{'field':'PRIVATE_FIELD_MARKER','value':'MODEL_PRIVATE_MARKER'}]
            elif case == 'value_null': row['values'][0]['value'] = None
            elif case == 'value_duplicate': row['values'].append(copy.deepcopy(row['values'][0]))
            elif case == 'source_refs_required': row['source_refs'] = []
            elif case == 'source_ref_binding': row['source_refs'][0]['unit_id'] = 'MODEL_PRIVATE_MARKER'
            elif case == 'presentation_section': row['presentation_section'] = 'MODEL_PRIVATE_MARKER'
            elif case == 'operation_shape': row['private_payload'] = 'MODEL_PRIVATE_MARKER'
            return {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':[row]}
        for reason in ('value_field','value_null','value_duplicate','source_refs_required',
                'source_ref_binding','presentation_section','operation_shape'):
            with self.subTest(reason=reason):
                self.setUp(); self.seed()
                self.behavior = lambda ctx, reason=reason: invalid(ctx, reason)
                meta = self._assert_failed_diagnostic(self.command('Engineer at Example Labs. OWNER_PRIVATE_MARKER.'),
                    'operation_contract', reason)
                self.assertNotIn('PRIVATE_MARKER', json.dumps(meta['failure_diagnostic']))
                self.assertNotIn('private_payload', meta)

    def test_one_sentence_backing_several_new_skills_is_not_pasted_into_each_of_them(self):
        text = 'My main skills are Go, Python and Kafka.'
        def add(ctx):
            return {'response': 'Review the skills.', 'next_question': '', 'operations': [
                operation(ctx, op='add_content', record_type='skill', section='Skills', values={'name': name})
                for name in ('Go', 'Python', 'Kafka')]}
        self.behavior = add
        proposals = self.turn(text)['proposals']
        self.assertEqual([p['proposed_values']['name'] for p in proposals], ['Go', 'Python', 'Kafka'])
        self.assertTrue(all('summary' not in p['proposed_values'] for p in proposals))
        # a single skill from its own sentence still keeps the member's exact words
        self.setUp()
        self.behavior = lambda ctx: {'response': 'Review the skill.', 'next_question': '', 'operations': [
            operation(ctx, op='add_content', record_type='skill', section='Skills', values={'name': 'Go'})]}
        single = self.turn('I use Go every day for services.')['proposals'][0]
        self.assertEqual(single['proposed_values']['summary'], 'I use Go every day for services.')

    def test_a_name_the_member_did_not_write_is_left_empty_and_flagged_not_a_reason_to_discard_the_answer(self):
        # The model brought "Northfield University" in from another message. The member's words only say "the university
        # tutoring center": the answer is kept, that one detail is left for the member, and nothing is invented.
        text = 'From 2024 to 2025 I tutored first-year students in introductory accounting through the university tutoring center.'
        def add(ctx):
            return {'response': 'Review the tutoring role.', 'next_question': '', 'operations': [operation(
                ctx, op='add_content', record_type='role', section='Experience',
                values={'role_title': 'Tutor', 'employer_name': 'Northfield University Tutoring Center'})]}
        self.behavior = add
        result = self.turn(text)
        proposal = result['proposals'][0]
        self.assertEqual(proposal['proposed_values']['role_title'], 'Tutor')
        self.assertNotIn('employer_name', proposal['proposed_values'])
        self.assertEqual(proposal['proposed_values']['summary'], text)
        stored = self.intake.repository.load_owner(self.owner)['proposals'][proposal['proposal_key']]
        self.assertEqual(stored['resume_conversation_v1']['uncertain_fields'], ['employer_name'])

    def test_a_name_assembled_from_scattered_words_is_not_supported(self):
        # "senior" and "director" are both in the sentence, but they are not a title the member wrote.
        text = 'Every week I prepared reports for the senior team and sent them to the director of the bank.'
        def add(ctx):
            return {'response': 'Review the role.', 'next_question': '', 'operations': [operation(
                ctx, op='add_content', record_type='role', section='Experience',
                values={'role_title': 'Senior Director', 'employer_name': 'Senior Bank'})]}
        self.behavior = add
        proposal = self.turn(text)['proposals'][0]
        self.assertNotIn('role_title', proposal['proposed_values'])
        self.assertNotIn('employer_name', proposal['proposed_values'])
        stored = self.intake.repository.load_owner(self.owner)['proposals'][proposal['proposal_key']]
        self.assertEqual(sorted(stored['resume_conversation_v1']['uncertain_fields']), ['employer_name', 'role_title'])

    def test_filler_words_between_the_members_words_and_a_reorder_inside_one_phrase_are_supported(self):
        cases = [('I worked as head of the kitchen at Lakeview Bistro.', 'Head of the Kitchen'),   # in order, filler between
                 ('My skills are pivot tables in Excel, and QuickBooks.', 'Excel pivot tables'),    # reordered inside one phrase
                 ('I was the director of the bank branch for six years.', 'Director of the Bank')]
        for text, name in cases:
            with self.subTest(name=name):
                self.setUp()
                def add(ctx, name=name):
                    return {'response': 'Review.', 'next_question': '', 'operations': [operation(
                        ctx, op='add_content', record_type='skill', section='Skills', values={'name': name})]}
                self.behavior = add
                proposal = self.turn(text)['proposals'][0]
                self.assertEqual(proposal['proposed_values']['name'], name)

    def test_a_name_whose_words_are_all_in_the_members_words_is_accepted(self):
        text = 'My skills are pivot tables in Excel, and QuickBooks.'
        def add(ctx):
            return {'response': 'Review the skill.', 'next_question': '', 'operations': [operation(
                ctx, op='add_content', record_type='skill', section='Skills', values={'name': 'Excel pivot tables'})]}
        self.behavior = add
        proposal = self.turn(text)['proposals'][0]
        self.assertEqual(proposal['proposed_values']['name'], 'Excel pivot tables')
        stored = self.intake.repository.load_owner(self.owner)['proposals'][proposal['proposal_key']]
        self.assertNotIn('uncertain_fields', stored['resume_conversation_v1'])

    def test_diagnostic_failure_after_one_valid_operation_keeps_all_unapproved(self):
        self.seed()
        def output(ctx):
            good = operation(ctx, op='add_content', values={'role_title':'Engineer'})
            bad = operation(ctx, op='add_content', values={'PRIVATE_FIELD_MARKER':'MODEL_PRIVATE_MARKER'})
            return {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':[good,bad]}
        self.behavior = output
        meta = self._assert_failed_diagnostic(self.command('Engineer at Example Labs.'),
            'operation_contract', 'value_field')
        self.assertEqual(meta['source_units'][0]['disposition'], 'unresolved')

    def test_diagnostics_distinguish_canonical_and_authorized_context_changes(self):
        for reason in ('canonical_after_response', 'authorized_context_changed'):
            with self.subTest(reason=reason):
                self.setUp(); key = self.seed()
                def output(ctx):
                    if reason == 'canonical_after_response': self.ports.excluded.add(key)
                    else:
                        snapshot = self.intake.repository.load_owner(self.owner)
                        snapshot['lifecycle_epoch'] += 1
                        self.intake.repository.save_owner(self.owner, snapshot)
                    return {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':[]}
                self.behavior = output
                self._assert_failed_diagnostic(self.command('Engineer at Example Labs.'),
                    'context_revalidation', reason, 'changed')

    def test_arbitrary_exception_diagnostics_are_not_retained_or_returned(self):
        error = SynthesisError('invalid_output')
        error.conversation_diagnostic = {'schema_version':1,'stage':'operation_contract',
            'reason':'MODEL_PRIVATE_MARKER','raw_response':'MODEL_PRIVATE_MARKER'}
        self.behavior = lambda ctx: (_ for _ in ()).throw(error)
        meta = self._assert_failed_diagnostic(self.command('OWNER_PRIVATE_MARKER'),
            'turn_execution', 'unclassified')
        self.assertNotIn('MODEL_PRIVATE_MARKER', json.dumps(meta))

    def test_successful_turn_and_replay_have_no_failure_diagnostic(self):
        command = self.command('What can I add?')
        first = self.intake.converse(self.owner, command, assistance=self.assistance)
        replay = self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(replay['source_key'], first['source_key'])
        self.assertTrue(replay['replayed'])
        self.assertEqual(len(self.calls), 1)
        source = self.intake.repository.load_owner(self.owner)['sources'][first['source_key']]
        self.assertNotIn('failure_diagnostic', source['structured_values']['resume_conversation_v1'])

    def test_failed_diagnostic_source_purge_removes_words_and_still_refuses_replay(self):
        self.behavior = lambda ctx: {'response':'MODEL_PRIVATE_MARKER','next_question':'','operations':{}}
        command = self.command('OWNER_PRIVATE_MARKER')
        self._assert_failed_diagnostic(command, 'response_contract', 'operations_type')
        snapshot = self.intake.repository.load_owner(self.owner)
        source_key = next(key for key, row in snapshot['sources'].items()
            if (row.get('structured_values') or {}).get('resume_conversation_v1', {}).get('request_id') == command['request_id'])
        self.intake.purge_source(self.owner, {'request_id':str(uuid4()), 'source_key':source_key})
        purged = self.intake.repository.load_owner(self.owner)
        self.assertNotIn('OWNER_PRIVATE_MARKER', json.dumps(purged))
        self.assertNotIn('MODEL_PRIVATE_MARKER', json.dumps(purged))
        with self.assertRaises(SynthesisError):
            self.intake.converse(self.owner, command, assistance=self.assistance)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.intake.repository.load_owner(self.owner), purged)


    def recovery_request(self, row):
        return {'request_id': str(uuid4()), 'recovery_key': row['recovery_key'], 'recovery_token': row['recovery_token']}

    def imported_recovery_proposal(self):
        text = 'Experience\nEngineer, Example Labs.\nCoordinated eight people; not their manager.'
        self.intake._document_pipeline = extracted_pipeline(text)
        self.intake._extraction_adapter = DeterministicFakeExtractionAdapter([{'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}, 'quote': text.split('\n', 1)[1],
            'outcome': 'new', 'confidence': 'certain'}])
        self.intake.submit(self.owner, add_request(attachments=[{'client_key': 'doc', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'resume.txt'}]), files={'doc': FakeUpload('text/plain', text.encode())})
        return self.intake.get_workspace(self.owner)['pending_proposals'][0]

    def test_rejected_import_review_replays_without_ai_and_accounts_effective_approved_successor(self):
        original = self.imported_recovery_proposal()
        self.confirm(original, 'reject')
        request = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        first = self.intake.review_excluded_details(self.owner, request)
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), [])
        self.assertEqual(first['proposals'][0]['quote'], original['quote'])
        self.assertEqual(self.intake.review_excluded_details(self.owner, request)['proposals'], first['proposals'])
        parallel = self.intake.review_excluded_details(self.owner, {**request, 'request_id': str(uuid4())})
        self.assertEqual(parallel['proposals'][0]['proposal_key'], first['proposals'][0]['proposal_key'])
        with self.assertRaises(ResumeIntakeConflictError):
            self.intake.review_excluded_details(self.owner, {**request, 'recovery_token': '0' * 64})
        with self.assertRaises(ResumeIntakeConflictError): self.intake.review_excluded_details('another-owner', request)
        self.confirm(first['proposals'][0])
        replay = self.intake.review_excluded_details(self.owner, request)
        self.assertEqual(replay['proposals'][0]['state'], 'accepted')
        self.assertEqual(len(self.intake.draft_service.catalog.list_items(self.owner)), 1)
        snapshot = self.intake.repository.load_owner(self.owner)
        self.assertEqual(snapshot['proposals'][original['proposal_key']]['state'], 'rejected')
        units = self.intake.get_workspace(self.owner)['source_accounting'][0]['source_units']
        accounted = [unit for unit in units if self.intake._source_unit_proposals(snapshot,
            original['provenance']['source_key'], unit)]
        self.assertTrue(accounted)
        self.assertTrue(all(unit['disposition'] == 'approved' for unit in accounted))
        self.assertEqual(self.calls, [])

    def test_pending_unsaved_exclusion_undo_atomically_returns_original_to_pending(self):
        original = self.imported_recovery_proposal()
        self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
            operation(ctx, op='exclude_content', ref='proposal:' + original['proposal_key'])]}
        exclusion = self.turn('Exclude this imported role.')['proposals'][0]
        visible = self.intake.get_workspace(self.owner)['pending_proposals'][0]
        command = {'request_id': str(uuid4()), 'proposal_key': exclusion['proposal_key'], 'decision': 'reject',
            'undo_exclusion_token': visible['undo_exclusion_token']}
        before = self.intake.repository.load_owner(self.owner)
        from services.resume_intake_repository import InMemoryIntakeUnitOfWork, ResumeIntakeStoreUnavailable
        from services.resume_intake_service import ResumeIntakeUnavailableError
        with patch.object(InMemoryIntakeUnitOfWork, 'commit', side_effect=ResumeIntakeStoreUnavailable('fixture failure')):
            with self.assertRaises(ResumeIntakeUnavailableError): self.intake.decide(self.owner, command)
        self.assertEqual(self.intake.repository.load_owner(self.owner), before)
        result = self.intake.decide(self.owner, command)
        restored = result['restored_proposal']
        self.assertEqual(restored['proposed_values'], original['proposed_values'])
        self.assertEqual(restored['quote'], original['quote'])
        self.assertEqual(self.intake.decide(self.owner, command)['restored_proposal']['proposal_key'], restored['proposal_key'])
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), [])
        self.assertEqual(len(self.intake.get_workspace(self.owner)['pending_proposals']), 1)
        self.confirm(restored)
        self.assertEqual(len(self.intake.draft_service.catalog.list_items(self.owner)), 1)
        self.assertEqual(len(self.calls), 1)

    def test_saved_exclusion_review_is_projection_only_and_requires_unchanged_explicit_confirmation(self):
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
            operation(ctx, op='exclude_content', ref='record:' + key)]}
        self.confirm(self.turn('Exclude the Engineer role.')['proposals'][0])
        before = self.intake.draft_service.get_workspace(self.owner)
        row = self.intake.get_workspace(self.owner)['resume_recoverable_details'][0]
        pending = self.intake.review_excluded_details(self.owner, self.recovery_request(row))['proposals'][0]
        self.assertTrue(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner), before)
        self.confirm(pending)
        self.assertFalse(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner), before)
        self.assertEqual(len(self.calls), 1)

    def test_direct_saved_whole_and_bullet_pending_undo_only_rejects_exclusion(self):
        for bullet in (False, True):
            with self.subTest(bullet=bullet):
                self.setUp(); key = self.seed()
                before = self.intake.draft_service.get_workspace(self.owner)
                edits = [{'action': 'exclude', 'field': 'summary', 'index': 1,
                    'expected_text': 'A pilot reduced time 32%; not independently verified.', 'replacement': None}] if bullet else []
                self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
                    operation(ctx, op='revise_content' if bullet else 'exclude_content', ref='record:' + key, bullets=edits)]}
                exclusion = self.turn('Exclude this detail.')['proposals'][0]
                row = self.intake.get_workspace(self.owner)['pending_proposals'][0]
                command = {'request_id': str(uuid4()), 'proposal_key': exclusion['proposal_key'], 'decision': 'reject',
                    'undo_exclusion_token': row['undo_exclusion_token']}
                result = self.intake.decide(self.owner, command)
                self.assertNotIn('restored_proposal', result)
                self.assertEqual(self.intake.draft_service.get_workspace(self.owner), before)
                self.assertEqual(self.intake.get_workspace(self.owner)['pending_proposals'], [])
                self.assertEqual(self.intake.decide(self.owner, command)['proposal_key'], exclusion['proposal_key'])
                self.assertEqual(len(self.calls), 1)

    def test_pending_saved_target_revision_whole_and_bullet_undo_returns_exact_pending_lineage(self):
        for bullet in (False, True):
            with self.subTest(bullet=bullet):
                self.setUp(); key = self.seed()
                before = self.intake.draft_service.get_workspace(self.owner)
                summary = 'Coordinated ten people; I was not their manager.\nA pilot reduced time 32%; not independently verified.\nI wrote a review checklist.'
                self.behavior = lambda ctx: {'response': 'Review checklist and clear.', 'next_question': '', 'operations': [
                    operation(ctx, ref='record:' + key, values={'summary': summary}, clears=['location_text'])]}
                original = self.turn('Add the checklist and clear the location.')['proposals'][0]
                edits = [{'action': 'exclude', 'field': 'summary', 'index': 1,
                    'expected_text': 'A pilot reduced time 32%; not independently verified.', 'replacement': None}] if bullet else []
                self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
                    operation(ctx, op='revise_content' if bullet else 'exclude_content', ref='proposal:' + original['proposal_key'], bullets=edits)]}
                exclusion = self.turn('Exclude this detail.')['proposals'][0]
                row = self.intake.get_workspace(self.owner)['pending_proposals'][0]
                command = {'request_id': str(uuid4()), 'proposal_key': exclusion['proposal_key'], 'decision': 'reject',
                    'undo_exclusion_token': row['undo_exclusion_token']}
                snapshot_before = self.intake.repository.load_owner(self.owner)
                from services.resume_intake_repository import InMemoryIntakeUnitOfWork, ResumeIntakeStoreUnavailable
                from services.resume_intake_service import ResumeIntakeUnavailableError
                with patch.object(InMemoryIntakeUnitOfWork, 'commit', side_effect=ResumeIntakeStoreUnavailable('fixture failure')):
                    with self.assertRaises(ResumeIntakeUnavailableError): self.intake.decide(self.owner, command)
                self.assertEqual(self.intake.repository.load_owner(self.owner), snapshot_before)
                restored = self.intake.decide(self.owner, command)['restored_proposal']
                self.assertEqual(restored['target_key'], key)
                self.assertEqual(restored['proposed_values'], original['proposed_values'])
                self.assertEqual(restored['explicit_clears'], original['explicit_clears'])
                self.assertFalse(restored['resume_conversation_v1']['recovery_review']['as_shown'])
                self.assertEqual(self.intake.draft_service.get_workspace(self.owner), before)
                self.assertEqual(self.intake.decide(self.owner, command)['restored_proposal']['proposal_key'], restored['proposal_key'])
                self.assertEqual(len(self.intake.get_workspace(self.owner)['pending_proposals']), 1)
                snapshot = self.intake.repository.load_owner(self.owner)
                self.assertEqual(snapshot['proposals'][original['proposal_key']]['state'], 'invalidated')
                self.assertEqual(snapshot['proposals'][exclusion['proposal_key']]['state'], 'rejected')
                self.assertEqual(snapshot['proposals'][exclusion['proposal_key']]['superseded_by'], restored['proposal_key'])
                self.confirm(restored)
                saved = self.intake.draft_service.get_workspace(self.owner)['items']
                self.assertEqual(len(saved), 1)
                effective = {**saved[0]['values'], **(saved[0].get('proposed_values') or {})}
                self.assertEqual(effective['summary'], summary)
                self.assertIsNone(effective['location_text'])
                self.assertEqual(len(self.calls), 2)

    def test_pending_target_undo_refuses_changed_source_target_and_interleaved_commit_without_staging(self):
        from services.resume_intake_repository import InMemoryIntakeUnitOfWork
        for change in ('content', 'access', 'source', 'purge', 'commit_lock'):
            with self.subTest(change=change):
                self.setUp(); key = self.seed()
                self.behavior = lambda ctx: {'response': 'Review checklist.', 'next_question': '', 'operations': [
                    operation(ctx, ref='record:' + key, values={'summary': 'I wrote a review checklist.'})]}
                original = self.turn('Add my review checklist.')['proposals'][0]
                self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
                    operation(ctx, op='exclude_content', ref='proposal:' + original['proposal_key'])]}
                exclusion = self.turn('Exclude this role.')['proposals'][0]
                pending = self.intake.get_workspace(self.owner)['pending_proposals'][0]
                command = {'request_id': str(uuid4()), 'proposal_key': exclusion['proposal_key'], 'decision': 'reject',
                    'undo_exclusion_token': pending['undo_exclusion_token']}
                catalog = self.intake.draft_service.catalog
                if change == 'content': catalog.bump_content(self.owner, key)
                elif change == 'access': catalog.bump_access(self.owner, key)
                elif change == 'source':
                    snapshot = self.intake.repository.load_owner(self.owner)
                    snapshot['sources'][original['provenance']['source_key']]['version'] += 1
                    self.intake.repository.save_owner(self.owner, snapshot)
                elif change == 'purge':
                    self.intake.purge_source(self.owner, {'request_id': str(uuid4()),
                        'source_key': original['provenance']['source_key']})
                before = self.intake.repository.load_owner(self.owner)
                original_enter = InMemoryIntakeUnitOfWork.__enter__
                def interleave(unit):
                    catalog.bump_content(self.owner, key)
                    return original_enter(unit)
                with patch.object(InMemoryIntakeUnitOfWork, '__enter__', interleave if change == 'commit_lock' else original_enter):
                    with self.assertRaises(ResumeIntakeConflictError) as refused: self.intake.decide(self.owner, command)
                self.assertIsNone(refused.exception.proposed)
                self.assertEqual(self.intake.repository.load_owner(self.owner), before)
                self.assertEqual(len(catalog.list_items(self.owner)), 1)
                self.assertEqual(len(self.calls), 2)

    def test_duplicate_bullets_restore_exact_history_ordinal_and_preserve_other_exclusions(self):
        key = self.seed(summary='Same literal detail.\nSame literal detail.\nKeep this limitation.')
        self.behavior = lambda ctx: {'response': 'Review two exclusions.', 'next_question': '', 'operations': [
            operation(ctx, ref='record:' + key, bullets=[
                {'action': 'exclude', 'field': 'summary', 'index': 1, 'expected_text': 'Same literal detail.', 'replacement': None},
                {'action': 'exclude', 'field': 'summary', 'index': 0, 'expected_text': 'Same literal detail.', 'replacement': None}])]}
        self.confirm(self.turn('Exclude both repeated details.')['proposals'][0])
        rows = self.intake.get_workspace(self.owner)['resume_recoverable_details']
        self.assertEqual(len(rows), 2)
        # Restore the FIRST original line, which is the SECOND retained row.
        pending = self.intake.review_excluded_details(self.owner, self.recovery_request(rows[1]))['proposals'][0]
        self.assertEqual(pending['proposed_values']['summary'], 'Same literal detail.\nKeep this limitation.')
        self.confirm(pending)
        rows = self.intake.get_workspace(self.owner)['resume_recoverable_details']
        self.assertEqual(len(rows), 1)
        pending = self.intake.review_excluded_details(self.owner, self.recovery_request(rows[0]))['proposals'][0]
        self.confirm(pending)
        values = self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']
        self.assertEqual(values['summary'], 'Same literal detail.\nSame literal detail.\nKeep this limitation.')
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_recoverable_details'], [])
        self.assertEqual(len(self.calls), 1)

    def test_recovery_source_version_and_lifecycle_changes_refuse_before_review_without_text(self):
        for change in ('version', 'epoch'):
            with self.subTest(change=change):
                self.setUp(); original = self.imported_recovery_proposal(); self.confirm(original, 'reject')
                command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
                snapshot = self.intake.repository.load_owner(self.owner)
                if change == 'version': snapshot['sources'][original['provenance']['source_key']]['version'] += 1
                else: snapshot['lifecycle_epoch'] += 1
                self.intake.repository.save_owner(self.owner, snapshot)
                self.assertEqual(self.intake.get_workspace(self.owner)['resume_recoverable_details'], [])
                with self.assertRaises(ResumeIntakeConflictError) as refused:
                    self.intake.review_excluded_details(self.owner, command)
                self.assertIsNone(refused.exception.proposed)
                self.assertEqual(self.intake.repository.load_owner(self.owner), snapshot)

    def test_recovery_parallel_requests_create_one_candidate_and_failed_review_is_atomic(self):
        from concurrent.futures import ThreadPoolExecutor
        from services.resume_intake_repository import InMemoryIntakeUnitOfWork, ResumeIntakeStoreUnavailable
        from services.resume_intake_service import ResumeIntakeUnavailableError
        original = self.imported_recovery_proposal(); self.confirm(original, 'reject')
        command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        before = self.intake.repository.load_owner(self.owner)
        with patch.object(InMemoryIntakeUnitOfWork, 'commit', side_effect=ResumeIntakeStoreUnavailable('fixture failure')):
            with self.assertRaises(ResumeIntakeUnavailableError): self.intake.review_excluded_details(self.owner, command)
        self.assertEqual(self.intake.repository.load_owner(self.owner), before)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.intake.review_excluded_details, self.owner, {**command, 'request_id': str(uuid4())}) for _ in range(2)]
            keys = [future.result()['proposals'][0]['proposal_key'] for future in futures]
        self.assertEqual(keys[0], keys[1]); self.assertEqual(len(self.intake.get_workspace(self.owner)['pending_proposals']), 1)
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), []); self.assertEqual(self.calls, [])

    def test_saved_recovery_target_fences_revalidate_during_review_and_inside_confirm_lock(self):
        from services.resume_intake_repository import InMemoryIntakeUnitOfWork
        key = self.seed()
        self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
            operation(ctx, op='exclude_content', ref='record:' + key)]}
        self.confirm(self.turn('Exclude the Engineer role.')['proposals'][0])
        command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        catalog = self.intake.draft_service.catalog
        catalog.bump_access(self.owner, key)
        with self.assertRaises(ResumeIntakeConflictError): self.intake.review_excluded_details(self.owner, command)
        command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        pending = self.intake.review_excluded_details(self.owner, command)['proposals'][0]
        original_enter = InMemoryIntakeUnitOfWork.__enter__
        def interleave(unit):
            catalog.bump_content(self.owner, key)
            return original_enter(unit)
        with patch.object(InMemoryIntakeUnitOfWork, '__enter__', interleave):
            with self.assertRaises(ResumeIntakeConflictError): self.confirm(pending)
        self.assertTrue(dict(self.intake.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.intake.repository.load_owner(self.owner)['proposals'][pending['proposal_key']]['state'], 'pending')
        self.assertEqual(len(catalog.list_items(self.owner)), 1)

    def test_bullet_recovery_refuses_guessed_placement_after_a_freeform_order_change(self):
        key = self.seed(summary='First.\nSecond.\nThird.')
        self.behavior = lambda ctx: {'response': 'Review exclusion.', 'next_question': '', 'operations': [
            operation(ctx, ref='record:' + key, bullets=[{'action': 'exclude', 'field': 'summary',
                'index': 1, 'expected_text': 'Second.', 'replacement': None}])]}
        self.confirm(self.turn('Exclude Second.')['proposals'][0])
        command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        self.behavior = lambda ctx: {'response': 'Review new order.', 'next_question': '', 'operations': [
            operation(ctx, ref='record:' + key, values={'summary': 'Third.\nFirst.'})]}
        self.confirm(self.turn('Put Third before First.')['proposals'][0])
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_recoverable_details'], [])
        with self.assertRaises(ResumeIntakeConflictError): self.intake.review_excluded_details(self.owner, command)
        self.assertEqual(self.intake.draft_service.get_workspace(self.owner)['items'][0]['proposed_values']['summary'], 'Third.\nFirst.')

    def test_recovery_purge_and_version_fences_refuse_without_returning_original_text(self):
        original = self.imported_recovery_proposal()
        self.confirm(original, 'reject')
        command = self.recovery_request(self.intake.get_workspace(self.owner)['resume_recoverable_details'][0])
        pending = self.intake.review_excluded_details(self.owner, command)['proposals'][0]
        self.intake.purge_source(self.owner, {'request_id': str(uuid4()), 'source_key': original['provenance']['source_key']})
        self.assertEqual(self.intake.get_workspace(self.owner)['resume_recoverable_details'], [])
        self.assertNotIn(original['quote'], json.dumps(self.intake.review_excluded_details(self.owner, command)))
        with self.assertRaises(ResumeIntakeConflictError): self.confirm(pending)
        self.assertEqual(self.intake.draft_service.catalog.list_items(self.owner), [])
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
