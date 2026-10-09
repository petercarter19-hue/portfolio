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

    def test_a_large_upload_on_screen_plus_thirty_saved_items_still_gets_a_turn(self):
        # The tester hit "too much to read" at about 24 saved items while a large uploaded résumé was the review on screen:
        # the upload's own lines were not counted against the room. They are now trimmed, the selected record first.
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
        lines = '\n'.join('Upload line %d describes one more duty with a long enough sentence to count towards the room. ' % n * 2
                          for n in range(330))
        self.upload_document('Experience\nEngineer, Big Upload Employer.\n' + lines, 'Big Upload Employer')
        snapshot = self.intake._load(self.owner)
        canonical = self.assistance._context(self.owner, [], allow_empty=True)
        whole = self.intake._conversation_view(snapshot, canonical)
        self.assertGreater(_json_size(whole), 2 * self.assistance.limits['maximum_input_bytes'])
        self.behavior = lambda ctx: {'response': 'Which detail should change?', 'next_question': '', 'operations': []}
        self.turn('Please add the location Portland to this role.', 'record:' + keys[5])
        sent = self.calls[-1]['context']
        self.assertLess(_json_size(sent), self.assistance.limits['maximum_input_bytes'])
        text = json.dumps(sent, ensure_ascii=False)
        self.assertEqual(text.count('Marker5Start'), 2)          # the selected record is still in full
        self.assertEqual(len([t for t in sent['targets'] if t['target_ref'].startswith('record:')]), 30)
        sent_lines = sum(len(row['units']) for row in sent['materials'])
        self.assertLess(sent_lines, 330)                          # the upload's own lines were trimmed to fit

    def test_many_pending_suggestions_that_each_cite_many_source_lines_shrink_to_fit(self):
        # A large upload leaves many pending suggestions, each carrying a long list of the source lines it cites. Those
        # lists are what filled the room, so the shrunken form must not carry them.
        from services.resume_intake_runtime import model_facing_context, _json_size
        long_text = 'word ' * 300
        refs = [{'source_key': 'source-key-0001', 'unit_id': 'unit-%024d' % n} for n in range(60)]
        targets = [{'target_ref': 'proposal:%d' % n, 'record_type': 'role', 'binding': {'source_key': 'source-key-0001', 'submission_key': 'x' * 36},
                    'source_refs': refs, 'values': {'role_title': 'Role %d' % n, 'employer_name': 'Employer %d' % n, 'summary': long_text},
                    'bullets': {'summary': [{'index': i, 'text': long_text[:200]} for i in range(10)]}, 'excluded_bullets': []}
                   for n in range(40)]
        context = {'canonical': {'draft_version': 1}, 'targets': targets, 'selected_target': None, 'materials': [], 'prior_turns': []}
        self.assertGreater(_json_size(context), 150000)
        packed = model_facing_context(context, budget=60000)
        self.assertLessEqual(_json_size(packed), 60000)
        self.assertEqual([t['values']['role_title'] for t in packed['targets']], ['Role %d' % n for n in range(40)])

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

    def _typed_dates(self, text, record_type, section, values):
        def add(ctx):
            return {'response': 'Review.', 'next_question': '', 'operations': [operation(
                ctx, op='add_content', record_type=record_type, section=section, values=values)]}
        self.behavior = add
        proposal = self.turn(text)['proposals'][0]
        stored = self.intake.repository.load_owner(self.owner)['proposals'][proposal['proposal_key']]
        return proposal['proposed_values'], stored['resume_conversation_v1']

    def test_typed_dates_never_keep_a_month_or_day_the_member_did_not_say(self):
        for record_type, section, extra in (('education', 'Education', {'title': 'BS in Computer Science', 'institution_name': 'Example University'}),
                                            ('role', 'Experience', {'role_title': 'Analyst', 'employer_name': 'Example University'})):
            with self.subTest(record_type=record_type):
                values, context = self._typed_dates(
                    'I was an analyst and earned a BS in Computer Science at Example University, 2012 to May 2016.',
                    record_type, section, {**extra, 'start_date': '2012-03-14', 'end_date': '2016-05-20', 'date_precision': 'day'})
                self.assertEqual((values['start_date'], values['end_date'], values['date_precision']),
                                 ('2012-01-01', '2016-01-01', 'year'))
                self.assertEqual(context['date_note'], 'coarsened')

    def _revise_dates(self, patch_values, statement):
        self.upload_document('Experience' + chr(10) + 'Engineer, Alpha Labs, 2019-2021' + chr(10) + 'Built data pipelines for the planning team.', 'Alpha Labs')
        snapshot = self.intake.repository.load_owner(self.owner)
        pending = next(r for r in snapshot['proposals'].values() if r['state'] == 'pending' and r['record_type'] == 'role')
        # As organizing leaves it: the header line is not in the summary, the dates are held in the fields.
        pending['proposed_values'].update(start_date='2019-01-01', end_date='2021-01-01', date_precision='year', current_role=False,
                                          summary='Built data pipelines for the planning team.')
        self.intake.repository.save_owner(self.owner, snapshot)
        ref = 'proposal:' + pending['proposal_key']
        self.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values=patch_values, section='Experience')]}
        result = self.turn(statement, ref)
        self.last_response, proposals = result['response'], result['proposals']
        if not proposals:
            return None, {}
        proposal = proposals[0]
        stored = self.intake.repository.load_owner(self.owner)['proposals'][proposal['proposal_key']]
        return proposal['proposed_values'], stored.get('resume_conversation_v1', {})

    def _revise_end_date(self, new_end, statement):
        return self._revise_dates({'end_date': new_end}, statement)

    def _assert_more_detail_asks_for_the_start_month(self, patch_values, statement):
        # Tester R4T-5: a new date with more detail than the year-level date left alone is neither dropped nor given an
        # invented month; the Guide asks for the other date's month, and the answer completes the change.
        values, context = self._revise_dates(patch_values, statement)
        self.assertIsNone(values)
        self.assertIn('Which month in 2019 did it start?', self.last_response)
        self.assertNotIn('less detail', self.last_response)

    def test_a_new_exact_day_on_a_year_level_entry_asks_for_the_other_dates_month(self):
        self._assert_more_detail_asks_for_the_start_month({'end_date': '2022-05-20', 'date_precision': 'day'}, 'Change the end date to May 20, 2022.')

    def test_a_new_month_on_a_year_level_entry_asks_for_the_other_dates_month(self):
        self._assert_more_detail_asks_for_the_start_month({'end_date': '2022-05-01', 'date_precision': 'month'}, 'Change the end date to May 2022.')

    def test_a_precision_only_revision_cannot_raise_the_detail_of_dates_stated_as_years(self):
        values, context = self._revise_dates({'date_precision': 'month'}, 'Show the months.')
        # Nothing the member said gives a month, so the revision changes nothing and no new suggestion replaces the earlier one.
        self.assertIsNone(values)

    def test_changing_one_date_keeps_the_other_and_flags_nothing(self):
        values, context = self._revise_end_date('2022-01-01', 'Change the end date to 2022.')
        self.assertEqual((values['start_date'], values['end_date'], values['date_precision']), ('2019-01-01', '2022-01-01', 'year'))
        self.assertNotIn('uncertain_fields', context)

    def test_a_changed_date_with_more_detail_than_the_unchanged_one_asks_for_it(self):
        self._assert_more_detail_asks_for_the_start_month({'end_date': '2022-05-20'}, 'Change the end date to May 2022.')

    def test_a_changed_date_the_member_never_said_leaves_the_earlier_value_in_place(self):
        self.upload_document('Experience' + chr(10) + 'Engineer, Alpha Labs, 2019-2021' + chr(10) + 'Built data pipelines for the planning team.', 'Alpha Labs')
        snapshot = self.intake.repository.load_owner(self.owner)
        pending = next(r for r in snapshot['proposals'].values() if r['state'] == 'pending' and r['record_type'] == 'role')
        pending['proposed_values'].update(start_date='2019-01-01', end_date='2021-01-01', date_precision='year', current_role=False,
                                          summary='Built data pipelines for the planning team.')
        self.intake.repository.save_owner(self.owner, snapshot)
        ref = 'proposal:' + pending['proposal_key']
        self.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2025-01-01'}, section='Experience')]}
        self.turn('Please fix the end date.', ref)
        # Nothing the member said supports 2025, so no revision replaces the earlier value.
        kept = self.intake.repository.load_owner(self.owner)['proposals'][pending['proposal_key']]
        self.assertEqual((kept['state'], kept['proposed_values']['end_date']), ('pending', '2021-01-01'))

    def test_an_entry_is_never_stored_with_dates_and_no_detail(self):
        values, _ = self._typed_dates(
            'I was an Engineer at Alpha Labs from 2012 to 2016.', 'role', 'Experience',
            {'role_title': 'Engineer', 'employer_name': 'Alpha Labs', 'start_date': '2012-01-01', 'end_date': '2016-01-01'})
        self.assertEqual((values['start_date'], values['end_date'], values['date_precision']), ('2012-01-01', '2016-01-01', 'year'))

    def test_a_later_exact_day_cannot_raise_the_detail_of_an_entry_first_stated_as_years(self):
        self._typed_dates(
            'I was an Engineer at Alpha Labs from 2012 to 2016.', 'role', 'Experience',
            {'role_title': 'Engineer', 'employer_name': 'Alpha Labs', 'start_date': '2012-01-01', 'end_date': '2016-01-01'})
        stored = self.intake.repository.load_owner(self.owner)['proposals']
        first = next(row for row in stored.values() if row['state'] == 'pending' and row['record_type'] == 'role')
        ref = 'proposal:' + first['proposal_key']
        self.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2016-05-20', 'date_precision': 'day'}, section='Experience')]}
        proposals = self.turn('Change the end date to May 20, 2016.', ref)['proposals']
        # The start is only known to the year, so the new day cannot be kept; nothing replaces the earlier suggestion.
        self.assertEqual(proposals, [])
        kept = self.intake.repository.load_owner(self.owner)['proposals'][first['proposal_key']]
        self.assertEqual((kept['state'], kept['proposed_values']['start_date'], kept['proposed_values']['date_precision']),
                         ('pending', '2012-01-01', 'year'))

    def test_typed_dates_the_member_states_in_full_are_kept(self):
        values, context = self._typed_dates(
            'I earned a BS in Computer Science at Example University, January 2012 to May 2016.', 'education', 'Education',
            {'title': 'BS in Computer Science', 'institution_name': 'Example University', 'start_date': '2012-01-01',
             'end_date': '2016-05-01', 'date_precision': 'month'})
        self.assertEqual((values['start_date'], values['end_date'], values['date_precision']), ('2012-01-01', '2016-05-01', 'month'))
        self.assertNotIn('date_note', context)

    def test_a_typed_date_whose_year_the_member_never_said_is_left_out_and_flagged(self):
        values, context = self._typed_dates(
            'I earned a BS in Computer Science at Example University.', 'education', 'Education',
            {'title': 'BS in Computer Science', 'institution_name': 'Example University', 'start_date': '2012-01-01',
             'end_date': '2016-05-01', 'date_precision': 'month'})
        self.assertNotIn('start_date', values)
        self.assertNotIn('end_date', values)
        self.assertEqual(sorted(context['uncertain_fields']), ['end_date', 'start_date'])

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

from services.my_data_extraction_adapter import MyDataExtractionAdapter as _DateAdapter, organize_resume_extraction as _organize_resume
from services.resume_onboarding_document_reader import inventory_source


def _complete_resume_candidate(*args, **kwargs):
    from tests.test_resume_onboarding_coverage import complete_resume_candidate
    return complete_resume_candidate(*args, **kwargs)


DATE_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def date_shown(values, current=False):
    """What the review card reads for these dates (the same rules as the page's review and the saved card)."""
    precision = values.get("date_precision")

    def one(value):
        if not value:
            return ""
        year, month, day = value[:4], int(value[5:7]), int(value[8:10])
        if precision == "year":
            return year
        if precision == "month":
            return "%s %s" % (DATE_MONTHS[month - 1], year)
        if precision == "day":
            return "%s %d, %s" % (DATE_MONTHS[month - 1], day, year)
        return year  # no stated detail: only the year is ever claimed
    start, end = one(values.get("start_date")), "Present" if current else one(values.get("end_date"))
    return " – ".join(part for part in (start, end) if part)


# text, the dates the model gave, then the stored (start, end, detail) and what the review shows
DATE_ADD_CASES = {
    "mixed detail": ("I was an Engineer at Alpha Labs from 2012 to May 2016.",
                     {"start_date": "2012-03-14", "end_date": "2016-05-20", "date_precision": "day"},
                     ("2012-01-01", "2016-01-01", "year"), "2012 – 2016"),
    "a lone year": ("I was an Engineer at Alpha Labs in 2016.",
                    {"start_date": "2016-06-15", "date_precision": "day"},
                    ("2016-01-01", None, "year"), "2016"),
    "month to present": ("I am an Engineer at Alpha Labs, from Jan 2019 to present.",
                         {"start_date": "2019-01-01", "date_precision": "month", "current_role": True},
                         ("2019-01-01", None, "month"), "January 2019 – Present"),
    "months named once": ("I was an Engineer at Alpha Labs from June through August 2025.",
                          {"start_date": "2025-06-01", "end_date": "2025-08-01", "date_precision": "month"},
                          ("2025-06-01", "2025-08-01", "month"), "June 2025 – August 2025"),
    "no detail given": ("I was an Engineer at Alpha Labs from 2012 to 2016.",
                        {"start_date": "2012-01-01", "end_date": "2016-01-01"},
                        ("2012-01-01", "2016-01-01", "year"), "2012 – 2016"),
    "a year not in the words": ("I was an Engineer at Alpha Labs.",
                                {"start_date": "2019-03-01", "end_date": "2021-07-01", "date_precision": "month"},
                                (None, None, None), ""),
}
DATE_CREDENTIAL_CASES = {
    "a lone year": ("I earned a CPR certificate from Example Society in 2019.",
                    {"issue_date": "2019-06-11", "issue_date_precision": "day"}, ("2019-01-01", "year")),
    "a month": ("I earned a CPR certificate from Example Society in June 2019.",
                {"issue_date": "2019-06-11", "issue_date_precision": "day"}, ("2019-06-01", "month")),
    "no detail given": ("I earned a CPR certificate from Example Society in 2019.",
                        {"issue_date": "2019-01-01"}, ("2019-01-01", "year")),
}
DATE_ROLE = {"role_title": "Engineer", "employer_name": "Alpha Labs", "current_role": False}


def date_stored(values):
    return (values.get("start_date"), values.get("end_date"), values.get("date_precision"))


class DateTruthTests(unittest.TestCase):
    """One table of date cases, run through every path that stores a suggestion's dates (see the evidence file)."""
    def harness(self):
        harness = ConversationTests("test_a_name_whose_words_are_all_in_the_members_words_is_accepted")
        harness.setUp()
        self.addCleanup(harness.tearDown)
        return harness

    # -- uploaded résumé ---------------------------------------------------------
    def test_every_case_through_organizing_an_upload(self):
        for name, (text, given, stored, display) in DATE_ADD_CASES.items():
            with self.subTest(path="upload", case=name):
                doc = "Experience\n" + text.replace("I was an ", "").replace("I am an ", "")
                units = inventory_source(doc, document=True)
                content = [u for u in units if u["kind"] == "content"]
                raw = _complete_resume_candidate("role", {**DATE_ROLE, **given}, content[0]["text"], content, "Experience")
                draft = _organize_resume({"candidates": [raw]}, text=doc, source_units=units,
                                                   allowed_fields=EDITOR_FIELDS).drafts[0]
                values = draft["values"]
                self.assertEqual(date_stored(values), stored)
                self.assertEqual(date_shown(values, values.get("current_role") is True), display)
                if name == "a year not in the words":
                    self.assertEqual(sorted(draft["uncertain_fields"]), ["end_date", "start_date"])

    def test_credential_dates_through_organizing_an_upload(self):
        for name, (text, given, (issued, detail)) in DATE_CREDENTIAL_CASES.items():
            with self.subTest(path="upload", case=name):
                doc = "Credentials\n" + text.replace("I earned a ", "")
                units = inventory_source(doc, document=True)
                content = [u for u in units if u["kind"] == "content"]
                raw = _complete_resume_candidate("credential", {"name": "CPR certificate", "issuer": "Example Society",
                                                               "completion_status": "completed", **given},
                                                content[0]["text"], content, "Credentials")
                values = _organize_resume({"candidates": [raw]}, text=doc, source_units=units,
                                                    allowed_fields=EDITOR_FIELDS).drafts[0]["values"]
                self.assertEqual((values.get("issue_date"), values.get("issue_date_precision")), (issued, detail))

    # -- typed or recorded Add ---------------------------------------------------
    def typed_add(self, harness, record_type, text, values):
        def extract(*args, **kwargs):
            full = {name: None for name in __import__("services.my_data_extraction_adapter", fromlist=["x"]).EXTRACTION_VALUE_FIELDS[record_type]}
            full.update(values)
            return {"candidates": [{"record_type": record_type, "values": full, "quote": text, "outcome": "new",
                                    "match_reference": None, "confidence": "certain"}]}
        harness.intake._extraction_adapter = _DateAdapter(provider=extract)

        class Plan:
            source_text, kind, dispatch_id = text, "text", None
        drafts, issue, _ = harness.intake._extract_with_adapter(harness.owner, Plan())
        self.assertIsNone(issue)
        return drafts[0]

    def test_every_case_through_the_typed_or_recorded_add(self):
        for name, (text, given, stored, display) in DATE_ADD_CASES.items():
            with self.subTest(path="typed add", case=name):
                draft = self.typed_add(self.harness(), "role", text, {**DATE_ROLE, **given})
                self.assertEqual(date_stored(draft["values"]), stored)
                self.assertEqual(date_shown(draft["values"], draft["values"].get("current_role") is True), display)
                if name == "a year not in the words":
                    self.assertEqual(sorted(draft["uncertain_fields"]), ["end_date", "start_date"])

    def test_credential_dates_through_the_typed_or_recorded_add(self):
        for name, (text, given, (issued, detail)) in DATE_CREDENTIAL_CASES.items():
            with self.subTest(path="typed add", case=name):
                draft = self.typed_add(self.harness(), "credential", text, {
                    "name": "CPR certificate", "issuer": "Example Society", "completion_status": "completed", **given})
                self.assertEqual((draft["values"].get("issue_date"), draft["values"].get("issue_date_precision")), (issued, detail))

    # -- the Guide ---------------------------------------------------------------
    def test_every_case_through_the_guides_add(self):
        for name, (text, given, stored, display) in DATE_ADD_CASES.items():
            with self.subTest(path="guide add", case=name):
                harness = self.harness()
                harness.behavior = lambda ctx, given=given: {"response": "Review.", "next_question": "", "operations": [operation(
                    ctx, op="add_content", record_type="role", section="Experience", values={**DATE_ROLE, **given})]}
                proposal = harness.turn(text)["proposals"][0]
                values = proposal["proposed_values"]
                self.assertEqual(date_stored(values), stored)
                self.assertEqual(date_shown(values, values.get("current_role") is True), display)

    def test_credential_dates_through_the_guides_add(self):
        for name, (text, given, (issued, detail)) in DATE_CREDENTIAL_CASES.items():
            with self.subTest(path="guide add", case=name):
                harness = self.harness()
                harness.behavior = lambda ctx, given=given: {"response": "Review.", "next_question": "", "operations": [operation(
                    ctx, op="add_content", record_type="credential", section="Credentials",
                    values={"name": "CPR certificate", "issuer": "Example Society", "completion_status": "completed", **given})]}
                values = harness.turn(text)["proposals"][0]["proposed_values"]
                self.assertEqual((values.get("issue_date"), values.get("issue_date_precision")), (issued, detail))

    def test_revising_one_end_of_a_range_and_changing_only_the_detail(self):
        rows = {
            "one end changed": ({"end_date": "2022-01-01"}, "Change the end date to 2022.",
                                ("2019-01-01", "2022-01-01", "year")),
            "a new exact day under year detail": ({"end_date": "2022-05-20", "date_precision": "day"},
                                                  "Change the end date to May 20, 2022.", None),
            "detail alone raised": ({"date_precision": "month"}, "Show the months.", None),
            "a date the words never gave": ({"end_date": "2025-01-01"}, "Please fix the end date.", None),
        }
        for name, (patch, statement, stored) in rows.items():
            with self.subTest(path="guide revision", case=name):
                harness = self.harness()
                harness.upload_document("Experience\nEngineer, Alpha Labs, 2019-2021\nBuilt data pipelines for the planning team.", "Alpha Labs")
                snapshot = harness.intake.repository.load_owner(harness.owner)
                pending = next(r for r in snapshot["proposals"].values() if r["state"] == "pending" and r["record_type"] == "role")
                pending["proposed_values"].update(start_date="2019-01-01", end_date="2021-01-01", date_precision="year",
                                                  current_role=False, summary="Built data pipelines for the planning team.")
                harness.intake.repository.save_owner(harness.owner, snapshot)
                ref = "proposal:" + pending["proposal_key"]
                harness.behavior = lambda ctx, patch=patch: {"response": "Updated.", "next_question": "", "operations": [operation(
                    ctx, ref=ref, record_type="role", values=patch, section="Experience")]}
                proposals = harness.turn(statement, ref)["proposals"]
                if stored is None:
                    # Nothing the member said supports a change, or the Guide asks for the other date's detail first
                    # (an exact day beside a year), so nothing replaces the earlier suggestion.
                    self.assertEqual(proposals, [])
                    kept = harness.intake.repository.load_owner(harness.owner)["proposals"][pending["proposal_key"]]
                    self.assertEqual(date_stored(kept["proposed_values"]), ("2019-01-01", "2021-01-01", "year"))
                else:
                    values = proposals[0]["proposed_values"]
                    self.assertEqual(date_stored(values), stored)
                    self.assertEqual(date_shown(values), "%s – %s" % (stored[0][:4], stored[1][:4]))

    def test_revising_a_credential_date_cannot_raise_its_detail(self):
        harness = self.harness()
        harness.behavior = lambda ctx: {"response": "Review.", "next_question": "", "operations": [operation(
            ctx, op="add_content", record_type="credential", section="Credentials",
            values={"name": "CPR certificate", "issuer": "Example Society", "completion_status": "completed",
                    "issue_date": "2019-06-11", "issue_date_precision": "day"})]}
        first = harness.turn("I earned a CPR certificate from Example Society in 2019.")["proposals"][0]
        ref = "proposal:" + first["proposal_key"]
        harness.behavior = lambda ctx: {"response": "Updated.", "next_question": "", "operations": [operation(
            ctx, ref=ref, record_type="credential", values={"issue_date_precision": "day"}, section="Credentials")]}
        proposals = harness.turn("Show the exact day.", ref)["proposals"]
        self.assertEqual(proposals, [])
        kept = harness.intake.repository.load_owner(harness.owner)["proposals"][first["proposal_key"]]
        self.assertEqual((kept["proposed_values"]["issue_date"], kept["proposed_values"]["issue_date_precision"]), ("2019-01-01", "year"))

    def test_approximate_education_dates_keep_only_years_the_words_state(self):
        rows = (("I studied nursing around 2009 to 2013 at Example College.", ("2009-01-01", "2013-01-01", "approximate")),
                ("I studied nursing at Example College.", (None, None, None)))
        for text, expected in rows:
            with self.subTest(text=text):
                harness = self.harness()
                harness.behavior = lambda ctx: {"response": "Review.", "next_question": "", "operations": [operation(
                    ctx, op="add_content", record_type="education", section="Education",
                    values={"title": "Nursing", "institution_name": "Example College", "start_date": "2009-03-01",
                            "end_date": "2013-05-01", "date_precision": "approximate"})]}
                values = harness.turn(text)["proposals"][0]["proposed_values"]
                self.assertEqual(date_stored(values), expected)

    def test_a_month_word_far_from_the_year_by_ordinary_words_is_not_that_months_date(self):
        from services.my_data_extraction_adapter import normalize_dates
        values = {"start_date": "2012-05-01", "date_precision": "month"}
        normalize_dates(values, "May I add that in 2012 I was at Alpha Labs.")
        self.assertEqual(date_stored(values), ("2012-01-01", None, "year"))

    # -- one date changed on a saved, month-level entry (tester round 3, R3-1) -----------------
    def _saved_month_role(self, harness):
        return harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date='2019-01-01',
                            end_date=None, date_precision='month', current_role=True, summary='Ran the morning shift.')

    def _with_saved(self, harness, key, proposal):
        # A suggestion against a saved entry holds only what it changes; this is what the card reads.
        item = next(row for row in harness.intake.draft_service.get_workspace(harness.owner)['items'] if row['record_key'] == key)
        return {**item['values'], **(proposal.get('proposed_values') or {})}

    def _no_change_and_asked(self, harness, result, question, waiting=0):
        # Nothing is lowered without asking: no suggestion is made, the Guide says so, and asks for the missing detail.
        # ``waiting``: suggestions made by earlier turns that stay as they were.
        self.assertEqual(result['proposals'], [])
        self.assertRegex(result['response'], r"^I haven't changed [^.]+ yet\. ")
        self.assertIn(question, result['response'])
        self.assertEqual(len([r for r in harness.intake.repository.load_owner(harness.owner)['proposals'].values()
                              if r['state'] == 'pending']), waiting)

    def test_a_year_only_end_date_on_a_saved_month_level_role_invents_no_month_in_any_shape(self):
        # The model sent the new end date in month shape ("2022-01") with no detail in its change; the rule once skipped
        # that shape, and confirming applied the entry's month detail to it: "January 2022". Review R4c-1: the start's
        # month is not lowered either; the Guide asks, and "years only" in the member's words is their choice.
        for patch in ({'end_date': '2022-01', 'current_role': False}, {'end_date': '2022', 'current_role': False},
                      {'end_date': '2022-01-01', 'current_role': False}, {'end_date': '2022-01-01', 'date_precision': 'month', 'current_role': False},
                      {'end_date': '2022-01-01', 'date_precision': 'year', 'current_role': False}):
            with self.subTest(patch=patch):
                harness = self.harness()
                key = self._saved_month_role(harness)
                ref = 'record:' + key
                harness.behavior = lambda ctx, patch=patch: {'response': 'I changed the end date.', 'next_question': 'What next?',
                    'operations': [operation(ctx, ref=ref, record_type='role', values=patch, section='Experience')]}
                result = harness.turn('At Northwind Bakery, change the end date to 2022.', ref)
                self._no_change_and_asked(harness, result, 'Which month in 2022 did it end?')
                self.assertIn('"It ended in 2022, years only"', result['response'])
                proposal = harness.turn('It ended in 2022, years only.', ref)['proposals'][0]
                stored = harness.intake.repository.load_owner(harness.owner)['proposals'][proposal['proposal_key']]
                values = proposal['proposed_values']
                # The change carries the detail it was stored at, so confirming cannot apply the older month detail.
                self.assertEqual((values['end_date'], values['date_precision']), ('2022-01-01', 'year'))
                self.assertIn('end_date', stored['provided_fields'])
                self.assertIn('date_precision', stored['provided_fields'])
                self.assertIsNone(stored['resume_conversation_v1'].get('date_note'))
                harness.confirm(proposal)
                item = next(row for row in harness.intake.draft_service.get_workspace(harness.owner)['items'] if row['record_key'] == key)
                merged = {**item['values'], **(item.get('proposed_values') or {})}
                self.assertEqual(date_stored(merged), ('2019-01-01', '2022-01-01', 'year'))
                self.assertEqual(date_shown(merged), '2019 – 2022')

    def test_a_year_only_start_date_on_a_month_level_range_is_asked_about_too(self):
        harness = self.harness()
        ref = 'record:' + self._saved_range_role(harness)
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'start_date': '2018'}, section='Experience')]}
        result = harness.turn('The start was 2018.', ref)
        self._no_change_and_asked(harness, result, 'Which month in 2018 did it start?')
        self.assertIn('"It started in March 2018"', result['response'])

    def test_a_month_only_date_beside_an_exact_day_asks_for_the_day(self):
        harness = self.harness()
        key = harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date='2019-08-14',
                           end_date=None, date_precision='day', current_role=True, summary='Ran the morning shift.')
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2022-03', 'current_role': False}, section='Experience')]}
        result = harness.turn('Change the end date to March 2022.', ref)
        self._no_change_and_asked(harness, result, 'Which day in March 2022 did it end?')
        values = harness.turn('It ended in March 2022, months only.', ref)['proposals'][0]['proposed_values']
        self.assertEqual(date_stored(values), ('2019-08-01', '2022-03-01', 'month'))

    def test_the_question_and_both_answers_on_every_revise_path(self):
        # A saved entry (record) and a waiting suggestion (proposal): the lowering change is asked about, never made, and
        # each answer then goes through the same revision and the same rule.
        answers = {'month': ('It ended in March 2022.', {'end_date': '2022-03', 'current_role': False}, ('2019-08-01', '2022-03-01', 'month')),
                   'years only': ('It ended in 2022, years only.', {'end_date': '2022', 'current_role': False}, ('2019-01-01', '2022-01-01', 'year'))}
        for path in ('record', 'proposal'):
            for answer, (words, patch, stored) in answers.items():
                with self.subTest(path=path, answer=answer):
                    harness = self.harness()
                    if path == 'record':
                        key = harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery',
                                           start_date='2019-08-01', end_date=None, date_precision='month', current_role=True,
                                           summary='Ran the morning shift.')
                        ref = 'record:' + key
                    else:
                        harness.behavior = lambda ctx: {'response': 'Review.', 'next_question': '', 'operations': [operation(
                            ctx, op='add_content', record_type='role', section='Experience',
                            values={**DATE_ROLE, 'start_date': '2019-08', 'current_role': True,
                                    'date_precision': 'month'})]}
                        ref = 'proposal:' + harness.turn('I was an Engineer at Alpha Labs from August 2019.')['proposals'][0]['proposal_key']
                    harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
                        ctx, ref=ref, record_type='role', values={'end_date': '2022-01', 'current_role': False}, section='Experience')]}
                    result = harness.turn('Change the end date to 2022.', ref)
                    self.assertEqual(result['proposals'], [])
                    self.assertIn('Which month in 2022 did it end?', result['response'])
                    rows = harness.intake.repository.load_owner(harness.owner)['proposals'].values()
                    self.assertEqual(sum(r['state'] == 'pending' for r in rows), 0 if path == 'record' else 1)
                    harness.behavior = lambda ctx, patch=patch: {'response': 'Updated.', 'next_question': '', 'operations': [
                        operation(ctx, ref=ref, record_type='role', values=patch, section='Experience')]}
                    proposal = harness.turn(words, ref)['proposals'][0]
                    values = self._with_saved(harness, key, proposal) if path == 'record' else proposal['proposed_values']
                    self.assertEqual(date_stored(values), stored)
                    self.assertNotIn('date_note', harness.intake.repository.load_owner(harness.owner)['proposals'][
                        proposal['proposal_key']]['resume_conversation_v1'])

    def test_less_detail_the_members_words_did_not_ask_for_is_never_made(self):
        # The model setting years by itself (here on a change of title) lowers nothing; the member's own words do.
        harness = self.harness()
        key = self._saved_range_role(harness)
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'role_title': 'Shift Lead', 'date_precision': 'year'}, section='Experience')]}
        result = harness.turn('My title was Shift Lead.', ref)
        self._no_change_and_asked(harness, result, 'say "Show only the years"')
        for words in ('Drop the months.', 'Just the years, please.', 'Use years instead.', 'Just show the years.',
                      'Only show years, not the months.'):
            with self.subTest(words=words):
                harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
                    ctx, ref=ref, record_type='role', values={'date_precision': 'year'}, section='Experience')]}
                values = self._with_saved(harness, key, harness.turn(words, ref)['proposals'][0])
                self.assertEqual(date_stored(values), ('2019-01-01', '2021-01-01', 'year'))
        # A length of time is not a choice of detail.
        from services.resume_intake_service import _chooses_less_date_detail
        for words in ('I was there just two years.', 'Only 3 years in that job.', 'I stayed only a few months.'):
            with self.subTest(words=words):
                self.assertFalse(_chooses_less_date_detail(words, 'year') or _chooses_less_date_detail(words, 'month'))

    def test_a_change_to_another_date_after_the_question_never_invents_a_month(self):
        # Review R4c-1 (d): "January 2022" must never appear, whichever way the member answers.
        harness = self.harness()
        key = self._saved_month_role(harness)
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2022', 'current_role': False}, section='Experience')]}
        self._no_change_and_asked(harness, harness.turn('Change the end date to 2022.', ref), 'Which month in 2022 did it end?')
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'start_date': '2019-03'}, section='Experience')]}
        values = self._with_saved(harness, key, harness.turn('The start was March 2019.', ref)['proposals'][0])
        self.assertEqual(date_stored(values), ('2019-03-01', None, 'month'))
        self.assertNotIn('January', date_shown(values, True))
        # Answered with years only first, then the start's month on that card: the Guide asks for the end's month
        # (tester R4T-5), and "March" completes both months; January is never supplied.
        harness = self.harness()
        ref = 'record:' + self._saved_month_role(harness)
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2022', 'current_role': False}, section='Experience')]}
        card = harness.turn('It ended in 2022, years only.', ref)['proposals'][0]
        pref = 'proposal:' + card['proposal_key']
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='role', values={'start_date': '2018-03'}, section='Experience')]}
        self._no_change_and_asked(harness, harness.turn('The start was March 2018.', pref), 'Which month in 2022 did it end?',
                                  waiting=1)
        harness.behavior = lambda ctx: {'response': 'I set it to January.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='role', values={'end_date': '2022-01'}, section='Experience')]}
        result = harness.turn('March', pref)
        values = result['proposals'][0]['proposed_values']
        self.assertEqual(date_stored(values), ('2018-03-01', '2022-03-01', 'month'))
        self.assertIn('March 2018 – March 2022', result['response'])
        self.assertNotIn('January', result['response'])

    def test_a_change_to_something_else_after_the_question_keeps_the_dates_and_the_month_still_answers(self):
        # Review R4c-1 (g): no lowered card exists to carry forward; the entry's months stay, and a month answers.
        harness = self.harness()
        key = harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date='2019-08-01',
                           end_date=None, date_precision='month', current_role=True, summary='Ran the morning shift.')
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2022', 'current_role': False}, section='Experience')]}
        self._no_change_and_asked(harness, harness.turn('Change the end date to 2022.', ref), 'Which month in 2022 did it end?')
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'role_title': 'Shift Lead'}, section='Experience')]}
        card = harness.turn('My title was Shift Lead.', ref)['proposals'][0]
        stored = harness.intake.repository.load_owner(harness.owner)['proposals'][card['proposal_key']]
        self.assertEqual(date_stored(self._with_saved(harness, key, card)), ('2019-08-01', None, 'month'))
        self.assertIsNone(stored['resume_conversation_v1'].get('date_note'))
        pref = 'proposal:' + card['proposal_key']
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='role', values={'end_date': '2022-03', 'current_role': False}, section='Experience')]}
        values = harness.turn('The end month was March 2022.', pref)['proposals'][0]['proposed_values']
        self.assertEqual(date_stored(values), ('2019-08-01', '2022-03-01', 'month'))
        self.assertEqual(values['role_title'], 'Shift Lead')

    def test_a_month_given_for_the_new_end_date_keeps_both_dates_at_months(self):
        harness = self.harness()
        key = self._saved_month_role(harness)
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [
            operation(ctx, ref=ref, record_type='role', values={'end_date': '2022-03', 'current_role': False},
                                    section='Experience')]}
        proposal = harness.turn('At Northwind Bakery, change the end date to March 2022.', ref)['proposals'][0]
        stored = harness.intake.repository.load_owner(harness.owner)['proposals'][proposal['proposal_key']]
        self.assertEqual((proposal['proposed_values']['end_date'], proposal['proposed_values']['date_precision']), ('2022-03-01', 'month'))
        self.assertIsNone(stored['resume_conversation_v1'].get('date_note'))

    def test_every_date_shape_is_read_by_the_rule_on_the_add_paths(self):
        # The same month-shaped value on the Guide's add and the typed Add: read, checked against the words, never skipped.
        harness = self.harness()
        harness.behavior = lambda ctx: {'response': 'Review.', 'next_question': '', 'operations': [operation(
            ctx, op='add_content', record_type='role', section='Experience',
            values={**DATE_ROLE, 'start_date': '2012-03', 'end_date': '2016-05', 'date_precision': 'month'})]}
        values = harness.turn('I was an Engineer at Alpha Labs from 2012 to May 2016.')['proposals'][0]['proposed_values']
        self.assertEqual(date_stored(values), ('2012-01-01', '2016-01-01', 'year'))
        draft = self.typed_add(self.harness(), 'role', 'I was an Engineer at Alpha Labs from 2012 to May 2016.',
                               {**DATE_ROLE, 'start_date': '2012-03', 'end_date': '2016-05', 'date_precision': 'month'})
        self.assertEqual(date_stored(draft['values']), ('2012-01-01', '2016-01-01', 'year'))

    def test_the_month_given_after_the_question_keeps_both_months(self):
        # Review R4-2: the question must be answerable by the month alone.
        for start in ('2019-01-01', '2019-08-01'):
            with self.subTest(start=start):
                harness = self.harness()
                key = harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date=start,
                                   end_date=None, date_precision='month', current_role=True, summary='Ran the morning shift.')
                ref = 'record:' + key
                harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
                    ctx, ref=ref, record_type='role', values={'end_date': '2022-01', 'current_role': False}, section='Experience')]}
                self._no_change_and_asked(harness, harness.turn('At Northwind Bakery, change the end date to 2022.', ref),
                                          'Which month in 2022 did it end?')
                harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
                    ctx, ref=ref, record_type='role', values={'end_date': '2022-03', 'current_role': False}, section='Experience')]}
                values = self._with_saved(harness, key, harness.turn('It ended in March 2022.', ref)['proposals'][0])
                self.assertEqual(date_stored(values), (start, '2022-03-01', 'month'))

    def _saved_range_role(self, harness):
        return harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date='2019-08-01',
                            end_date='2021-06-01', date_precision='month', current_role=False, summary='Ran the morning shift.')

    def _two_turns(self, harness, first_patch, first_words, second_patch, second_words):
        ref = 'record:' + self._saved_range_role(harness)
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values=first_patch, section='Experience')]}
        first = harness.turn(first_words, ref)['proposals'][0]
        pref = 'proposal:' + first['proposal_key']
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='role', values=second_patch, section='Experience')]}
        return first['proposed_values'], harness.turn(second_words, pref)['proposals'][0]['proposed_values']

    def test_a_correction_the_member_made_on_a_card_survives_a_later_change_on_that_card(self):
        # Review R4b-1 (a): a later change on a card never undoes what the member changed on it.
        _, values = self._two_turns(self.harness(), {'start_date': '2019-03'}, 'The start was March 2019, not August.',
                                    {'end_date': '2021-09'}, 'And the end was September 2021.')
        self.assertEqual((values['start_date'], values['end_date'], values['date_precision']), ('2019-03-01', '2021-09-01', 'month'))

    def test_a_years_only_choice_on_a_card_survives_a_later_change_on_that_card(self):
        # Review R4b-1 (b2): the member's own choice of years is kept; a later month on that card is neither undone into
        # months nor dropped: the Guide asks for the other date's month (tester R4T-5), and the card stays as chosen.
        harness = self.harness()
        ref = 'record:' + self._saved_range_role(harness)
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'date_precision': 'year'}, section='Experience')]}
        first = harness.turn('Show only the years.', ref)['proposals'][0]
        self.assertEqual(first['proposed_values']['date_precision'], 'year')
        pref = 'proposal:' + first['proposal_key']
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='role', values={'end_date': '2022-09'}, section='Experience')]}
        self._no_change_and_asked(harness, harness.turn('And the end was September 2022.', pref),
                                  'Which month in 2019 did it start?', waiting=1)
        kept = harness.intake.repository.load_owner(harness.owner)['proposals'][first['proposal_key']]
        self.assertEqual((kept['state'], kept['proposed_values']['date_precision']), ('pending', 'year'))

    def test_a_change_to_something_other_than_dates_that_changes_nothing_does_not_mention_dates(self):
        harness = self.harness()
        ref = 'record:' + self._saved_range_role(harness)
        harness.behavior = lambda ctx: {'response': 'I changed the title.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'role_title': 'Shift Supervisor'}, section='Experience')]}
        result = harness.turn('My title was Shift Supervisor.', ref)
        self.assertIn('Nothing changed', result['response'])
        self.assertNotIn('date', result['response'])

    def test_a_change_that_changes_nothing_is_never_reported_as_made(self):
        harness = self.harness()
        key = harness.seed('role', role_title='Shift Supervisor', employer_name='Northwind Bakery', start_date='2019-01-01',
                           end_date='2021-01-01', date_precision='year', current_role=False, summary='Ran the morning shift.')
        ref = 'record:' + key
        harness.behavior = lambda ctx: {'response': 'I changed the end date.', 'next_question': '', 'operations': [operation(
            ctx, ref=ref, record_type='role', values={'end_date': '2021'}, section='Experience')]}
        result = harness.turn('The end date is 2021.', ref)
        self.assertEqual(result['proposals'], [])
        self.assertIn('Nothing changed', result['response'])

    def test_a_year_the_member_calls_a_start_is_never_made_a_completion(self):
        # Review R4-3, on both add paths: the words decide where a completed program's single year belongs.
        rows = (('I completed an MBA at Emory University. I started it in 2018.', ('2018-01-01', None)),
                ('I began my MBA at Emory University in 2018 and I have finished it.', ('2018-01-01', None)),
                ('I earned an MBA from Emory University in 2018.', (None, '2018-01-01')))
        given = {'title': 'MBA', 'institution_name': 'Emory University', 'education_status': 'completed',
                 'start_date': '2018-01-01', 'date_precision': 'year'}
        for text, (start, end) in rows:
            with self.subTest(path='guide add', text=text):
                harness = self.harness()
                harness.behavior = lambda ctx: {'response': 'Review.', 'next_question': '', 'operations': [operation(
                    ctx, op='add_content', record_type='education', section='Education', values=dict(given))]}
                values = harness.turn(text)['proposals'][0]['proposed_values']
                self.assertEqual((values.get('start_date'), values.get('end_date')), (start, end))
            with self.subTest(path='typed add', text=text):
                draft = self.typed_add(self.harness(), 'education', text, dict(given))
                self.assertEqual((draft['values'].get('start_date'), draft['values'].get('end_date')), (start, end))
                if end:
                    self.assertIn('end_date', draft['provided_fields'])

    def test_a_credential_revision_that_says_active_can_be_confirmed(self):
        # Review R4-5: a status word in a revision becomes the form's choice, so confirming never fails on it.
        harness = self.harness()
        harness.behavior = lambda ctx: {'response': 'Review.', 'next_question': '', 'operations': [operation(
            ctx, op='add_content', record_type='credential', section='Credentials',
            values={'name': 'CPR certification', 'issuer': 'Example Society'})]}
        first = harness.turn('I have a CPR certification from Example Society.')['proposals'][0]
        pref = 'proposal:' + first['proposal_key']
        harness.behavior = lambda ctx: {'response': 'Updated.', 'next_question': '', 'operations': [operation(
            ctx, ref=pref, record_type='credential', values={'completion_status': 'active'}, section='Credentials')]}
        values = harness.turn('It is active.', pref)['proposals'][0]['proposed_values']
        self.assertEqual(values['completion_status'], 'completed')

    def test_padding_a_credential_date_is_not_reported_as_trimmed(self):
        # Review R4-6: "2019" at year detail and "2019-06" at month detail lose nothing.
        for given in ({'issue_date': '2019', 'issue_date_precision': 'year'}, {'issue_date': '2019-06', 'issue_date_precision': 'month'}):
            with self.subTest(given=given):
                harness = self.harness()
                harness.behavior = lambda ctx, given=given: {'response': 'Review.', 'next_question': '', 'operations': [operation(
                    ctx, op='add_content', record_type='credential', section='Credentials',
                    values={'name': 'CPR certification', 'issuer': 'Example Society', 'completion_status': 'completed', **given})]}
                proposal = harness.turn('I earned a CPR certification from Example Society in June 2019.')['proposals'][0]
                stored = harness.intake.repository.load_owner(harness.owner)['proposals'][proposal['proposal_key']]
                self.assertIsNone((stored.get('resume_conversation_v1') or {}).get('date_note'))

    # -- the canonical store -----------------------------------------------------
    def test_the_canonical_editor_keeps_no_detail_the_precision_does_not_carry(self):
        from services.living_resume_editor_service import _role_values
        values = _role_values({"role_title": "Engineer", "employer_name": "Alpha Labs", "start_date": "2012-03-14",
                               "end_date": "2016-05-20", "date_precision": "year"})
        self.assertEqual(date_stored(values), ("2012-01-01", "2016-01-01", "year"))
        # A missing detail is never read as an exact day: the entry is stored as "unknown" and shows no date.
        unknown = _role_values({"role_title": "Engineer", "employer_name": "Alpha Labs", "start_date": "2012-03-14"})
        self.assertEqual(unknown["date_precision"], "unknown")

if __name__ == '__main__': unittest.main()


class CorrectionPathTests(unittest.TestCase):
    """Round 5: correcting by talking, as the tester did it with the live model (R4T-2 to R4T-5).

    The fake model here behaves the way the live one did: it answers a short reply with nothing usable, with only a
    detail change, with the wrong year, or with a change to another entry, and it writes dates in its reply that its own
    change does not hold. Each case must still end in the change the member asked for, on the entry they asked about,
    with words that read exactly like the card.
    """

    def harness(self):
        harness = ConversationTests("test_a_name_whose_words_are_all_in_the_members_words_is_accepted")
        harness.setUp()
        self.addCleanup(harness.tearDown)
        return harness

    def northwind(self, harness, **values):
        return harness.seed('role', **{'role_title': 'Shift Lead', 'employer_name': 'Northwind Bakery', 'start_date': '2019-01-01',
                                       'end_date': '2021-06-01', 'date_precision': 'month', 'current_role': False,
                                       'summary': 'Ran the morning shift.', **values})

    def sangamon(self, harness):
        return harness.seed('role', role_title='Quality Engineer', employer_name='Sangamon Valley Foods', start_date='2018-08-01',
                            end_date='2022-02-01', date_precision='month', current_role=False, summary='Led audits.')

    def say(self, harness, words, operations, ref=None, response='Done.'):
        harness.behavior = lambda ctx: {'response': response, 'next_question': '',
                                        'operations': [build(ctx) for build in operations]}
        return harness.turn(words, ref)

    def merged(self, harness, key, proposal):
        item = next(row for row in harness.intake.draft_service.get_workspace(harness.owner)['items'] if row['record_key'] == key)
        return {**item['values'], **(proposal.get('proposed_values') or {})}

    def ask_about_northwind_end(self, harness, ref):
        result = self.say(harness, 'At Northwind Bakery, change the end date to 2022.', [lambda ctx: operation(
            ctx, ref=ref, values={'end_date': '2022', 'current_role': False})])
        self.assertEqual(result['proposals'], [])
        self.assertIn('Which month in 2022 did it end?', result['response'])
        return result

    def test_the_month_alone_answers_the_guides_question_whatever_the_model_does(self):
        # R4T-3 "March": the live model answered nothing usable. Every shape of model answer still gives March 2022.
        shapes = {
            'no change at all': lambda ref: [],
            'the month in the right year': lambda ref: [lambda ctx: operation(ctx, ref=ref, values={'end_date': '2022-03'})],
            'the wrong year': lambda ref: [lambda ctx: operation(ctx, ref=ref, values={'end_date': '2021-03'})],
            'a detail change only': lambda ref: [lambda ctx: operation(ctx, ref=ref, values={'date_precision': 'month'})],
        }
        for name, model in shapes.items():
            with self.subTest(model=name):
                harness = self.harness()
                key = self.northwind(harness)
                ref = 'record:' + key
                self.ask_about_northwind_end(harness, ref)
                operations = model(ref)
                result = self.say(harness, 'March', operations, response='Updated it to January 2019 – March 2023.')
                self.assertEqual(len(result['proposals']), 1)
                values = self.merged(harness, key, result['proposals'][0])
                self.assertEqual(date_stored(values), ('2019-01-01', '2022-03-01', 'month'))
                self.assertIn('January 2019 – March 2022', result['response'])
                self.assertNotIn('2023', result['response'])

    def test_just_the_years_keeps_the_year_the_member_asked_for(self):
        # R4T-3 "just the years": the live model sent only the detail, so the card kept 2021 while the reply said 2022.
        for words in ('just the years', 'It ended in 2022, years only.'):
            with self.subTest(words=words):
                harness = self.harness()
                key = self.northwind(harness)
                ref = 'record:' + key
                self.ask_about_northwind_end(harness, ref)
                result = self.say(harness, words, [lambda ctx: operation(ctx, ref=ref, values={'date_precision': 'year'})],
                                  response="I'll propose showing years only: 2019–2022.")
                values = self.merged(harness, key, result['proposals'][0])
                self.assertEqual(date_stored(values), ('2019-01-01', '2022-01-01', 'year'))
                self.assertIn('2019 – 2022', result['response'])

    def test_a_change_typed_on_one_card_never_changes_another_entry(self):
        # R4T-2: on Sangamon's card the live model changed Northwind. Nothing is changed there, and the reply says so.
        harness = self.harness()
        northwind, sangamon = self.northwind(harness), self.sangamon(harness)
        self.ask_about_northwind_end(harness, 'record:' + northwind)
        result = self.say(harness, 'It ended in March 2022.', [lambda ctx: operation(
            ctx, ref='record:' + northwind, values={'start_date': '2019-03', 'end_date': '2022-03'})],
            ref='record:' + sangamon, response='March 2019–March 2022, using the start month you supplied earlier.')
        self.assertEqual(result['proposals'], [])
        self.assertIn("I didn't change Shift Lead, Northwind Bakery", result['response'])
        self.assertIn('Quality Engineer, Sangamon Valley Foods', result['response'])
        self.assertNotIn('March 2019', result['response'])
        pending = [r for r in harness.intake.repository.load_owner(harness.owner)['proposals'].values() if r['state'] == 'pending']
        self.assertEqual(pending, [])

    def test_the_card_the_change_was_typed_on_is_the_one_changed(self):
        # The same words on Sangamon's card, with the model on the right entry: only Sangamon changes, and the open
        # question about Northwind is not applied to it.
        harness = self.harness()
        northwind, sangamon = self.northwind(harness), self.sangamon(harness)
        self.ask_about_northwind_end(harness, 'record:' + northwind)
        result = self.say(harness, 'It ended in March 2022.', [lambda ctx: operation(
            ctx, ref='record:' + sangamon, values={'end_date': '2022-03'})], ref='record:' + sangamon)
        self.assertEqual(len(result['proposals']), 1)
        self.assertEqual(result['proposals'][0]['target_key'], sangamon)
        self.assertEqual(date_stored(self.merged(harness, sangamon, result['proposals'][0])), ('2018-08-01', '2022-03-01', 'month'))
        self.assertIn('August 2018 – March 2022', result['response'])

    def test_a_waiting_change_and_its_saved_entry_are_the_same_card(self):
        # A turn from a waiting change to Northwind may revise that change or Northwind itself, never Sangamon.
        harness = self.harness()
        northwind, sangamon = self.northwind(harness), self.sangamon(harness)
        first = self.say(harness, 'My title was Head Baker.', [lambda ctx: operation(
            ctx, ref='record:' + northwind, values={'role_title': 'Head Baker'})])['proposals'][0]
        card = 'proposal:' + first['proposal_key']
        result = self.say(harness, 'Make the title Head Baker and Trainer.', [lambda ctx: operation(
            ctx, ref='record:' + northwind, values={'role_title': 'Head Baker and Trainer'})], ref=card)
        self.assertEqual(len(result['proposals']), 1)
        result = self.say(harness, 'The end was March 2022.', [lambda ctx: operation(
            ctx, ref='record:' + sangamon, values={'end_date': '2022-03'})], ref=card)
        self.assertEqual(result['proposals'], [])
        self.assertIn("I didn't change Quality Engineer, Sangamon Valley Foods", result['response'])

    def test_a_new_month_on_a_years_only_entry_asks_for_the_other_month_and_the_answer_completes_both(self):
        # R4T-5: "the start was March 2019" on a year-level entry was "Nothing changed ... less detail".
        harness = self.harness()
        key = self.northwind(harness, start_date='2019-01-01', end_date='2021-01-01', date_precision='year')
        ref = 'record:' + key
        result = self.say(harness, 'At Northwind Bakery, change the start date to March 2019.', [lambda ctx: operation(
            ctx, ref=ref, values={'start_date': '2019-03'})])
        self.assertEqual(result['proposals'], [])
        self.assertIn('Which month in 2021 did it end?', result['response'])
        self.assertNotIn('less detail', result['response'])
        result = self.say(harness, 'June', [])
        values = self.merged(harness, key, result['proposals'][0])
        self.assertEqual(date_stored(values), ('2019-03-01', '2021-06-01', 'month'))
        self.assertIn('March 2019 – June 2021', result['response'])

    def test_a_month_for_an_entrys_only_date_is_kept(self):
        # A current job at year detail: its only date may take the month the member gives.
        harness = self.harness()
        key = self.northwind(harness, start_date='2019-01-01', end_date=None, date_precision='year', current_role=True)
        result = self.say(harness, 'I started in March 2019.', [lambda ctx: operation(
            ctx, ref='record:' + key, values={'start_date': '2019-03'})])
        values = self.merged(harness, key, result['proposals'][0])
        self.assertEqual((values['start_date'], values['date_precision']), ('2019-03-01', 'month'))
        self.assertIn('March 2019 – Present', result['response'])

    def test_only_a_bare_reply_answers_the_guides_date_question(self):
        # Review R5-1: when in doubt it is not an answer. Whatever is not a bare reply goes to the model as an ordinary
        # turn (here the model changes nothing), and Northwind's end is never touched by it.
        rows = (
            ('March', True, True), ('It ended in March.', True, True), ('just the years', True, True),
            ('It ended in March 2022.', False, True), ('Yes, March.', True, True), ('It ended in March, I think.', True, True),
            ('May I change something else first?', True, False), ('No, the start was in March.', True, False),
            ('I also volunteered at the food bank in March.', False, False), ('Maybe March or April, not sure.', True, False),
            ('Never mind, leave it.', True, False), ('At Lakeside Diner I started in March.', False, False),
            ('No, it ended in March.', True, False), ('March? Or was it April?', True, False),
        )
        for words, on_card, answers in rows:
            with self.subTest(words=words, on_card=on_card):
                harness = self.harness()
                key = self.northwind(harness)
                ref = 'record:' + key
                self.ask_about_northwind_end(harness, ref)
                result = self.say(harness, words, [], ref=ref if on_card else None, response='Okay.')
                if answers:
                    self.assertEqual(len(result['proposals']), 1)
                    values = self.merged(harness, key, result['proposals'][0])
                    self.assertEqual(values['end_date'][:4], '2022')
                    self.assertIn(result['proposals'][0]['proposed_values'].get('date_precision'), {'month', 'year'})
                else:
                    self.assertEqual(result['proposals'], [])
                    self.assertEqual(result['response'], 'Okay.')

    def test_new_words_after_a_question_are_not_taken_for_its_answer(self):
        # Another year, or a long new sentence, closes the question: the model's own reading applies.
        harness = self.harness()
        key = self.northwind(harness)
        ref = 'record:' + key
        self.ask_about_northwind_end(harness, ref)
        result = self.say(harness, 'I also worked at Acme from March 2020.', [])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['response'], 'Done.')
        # And any later turn closes the question: "March" two turns later is not its answer.
        result = self.say(harness, 'March', [])
        self.assertEqual(result['proposals'], [])

    def test_the_reply_about_a_change_is_built_from_the_card(self):
        # R4T-4: whatever the model writes, the words about a change come from the stored suggestion.
        harness = self.harness()
        key = self.northwind(harness)
        result = self.say(harness, 'My title was Head Baker.', [lambda ctx: operation(
            ctx, ref='record:' + key, values={'role_title': 'Head Baker'})], response='I changed your dates to 2018–2024.')
        self.assertEqual(result['response'],
                         'Ready for your review: a change to Head Baker, Northwind Bakery: title “Head Baker”.')
        result = self.say(harness, 'I studied baking at Champlain Culinary Institute from 2012 to 2014.', [lambda ctx: operation(
            ctx, op='add_content', record_type='education', section='Education',
            values={'title': 'Baking', 'institution_name': 'Champlain Culinary Institute', 'start_date': '2012',
                    'end_date': '2014'})], response='Added your degree from 2010.')
        self.assertEqual(result['response'], 'Added for your review: Baking, Champlain Culinary Institute, 2012 – 2014.')
        # A turn that changes nothing keeps the model's own words (a question answered, a clarification asked).
        result = self.say(harness, 'What should I add next?', [], response='You could add a skill next.')
        self.assertEqual(result['response'], 'You could add a skill next.')
