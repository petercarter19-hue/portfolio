import unittest
from services.ai_foundation.contracts import AnswerClaim,AnswerKind,AnswerState,Citation,GroundedAnswer
from services.ai_foundation.gateway import AIFoundationGateway
from services.ai_foundation.errors import ProviderUnavailableError
from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
from services.member_visitor_ai_service import MemberVisitorAiService,ResultState,SupportVerdict
from tests.test_member_visitor_ai_repository import SnapshotDatabase,Identity
from tests.test_member_visitor_ai_sources import snapshot,SAVED_TEXT
from services.member_visitor_ai_service import (
    ApprovedMemberName, CitationTicketStore, OperationalRefusal,
    SingleProcessVisitorProtections, VisitorAiRuntime, VisitorOperationalLimits,
)
from services.resume_publication_contracts import ReadState, UsePurpose


class SyntheticProvider:
    def __init__(self,*,claim=SAVED_TEXT,summary=None,hook=lambda:None):
        self.claim=claim; self.summary=summary; self.hook=hook; self.seen=[]
    def answer(self,request,sources):
        self.seen.append((request,sources)); self.hook()
        source=sources[0]; start=source.content.index(SAVED_TEXT)
        cite=Citation('c1',source.source_version_key,start,start+len(SAVED_TEXT),SAVED_TEXT)
        return GroundedAnswer('a',AnswerState.SUPPORTED,self.summary or self.claim,
            (AnswerClaim('c1',self.claim,AnswerKind.EVIDENCE,AnswerState.SUPPORTED,(cite,)),))


class SyntheticSupportCatalogue:
    """Bounded semantic oracle for this fixture, not a production entailment model.

    Only this exact meaning is accepted: leadership, four people, 2021, and
    uncertain prospective savings. A matching quote with a different claim,
    an unjustified summary, or stronger certainty is rejected.
    """
    def __init__(self,hook=lambda:None): self.hook=hook
    def validate(self,request,sources,answer):
        self.hook()
        accepted={SAVED_TEXT,'In 2021, led four people in a pilot with possible cost savings.'}
        return (SupportVerdict.SUPPORTED if answer.summary in accepted and all(c.text in accepted for c in answer.claims)
                else SupportVerdict.UNSUPPORTED)


def stack(provider=None,support=None,doc=None):
    db=SnapshotDatabase(doc or snapshot()); repo=SqlMemberVisitorAiRepository(db,identity=Identity())
    provider=provider or SyntheticProvider()
    service=MemberVisitorAiService(repo,repo,AIFoundationGateway(provider),support=support)
    return db,repo,provider,service


class ServiceTests(unittest.TestCase):
    def test_actual_question_exact_sources_sixth_question_and_safe_citations(self):
        db,repo,provider,service=stack(support=SyntheticSupportCatalogue(),doc=snapshot(display=False))
        for i in range(6):
            result=service.ask_guest(slug='member-a',question='What happened in 2021?',request_id=str(i))
            self.assertEqual(result.state,ResultState.SUPPORTED)
        self.assertEqual(provider.seen[-1][0].question,'What happened in 2021?')
        self.assertEqual(provider.seen[-1][1],repo.load_guest('member-a').sources)
        self.assertEqual(result.citations[0].excerpt,SAVED_TEXT)
        self.assertNotIn('entry-a',repr(result))
        self.assertEqual(len(provider.seen),6)

    def test_quote_match_does_not_establish_wrong_meaning_dates_quantities_or_certainty(self):
        for claim in ('Was a team member in 2021.','Led a team of 4 in 2022.',
                      'Led a team of 40 in 2021.','The pilot reduced costs.',
                      'Led a team of 4 in 2021; the pilot will reduce costs.'):
            with self.subTest(claim=claim):
                _,_,_,service=stack(SyntheticProvider(claim=claim),SyntheticSupportCatalogue())
                result=service.ask_guest(slug='member-a',question='What is established?',request_id='x')
                self.assertEqual(result.state,ResultState.UNSUPPORTED)
                self.assertEqual(result.citations,())
        _,_,_,service=stack(SyntheticProvider(summary='The pilot saved $1 million.'),SyntheticSupportCatalogue())
        self.assertEqual(service.ask_guest(slug='a',question='Results?',request_id='x').state,ResultState.UNSUPPORTED)

    def test_supported_paraphrase_requires_semantic_adapter_and_missing_adapter_is_honest(self):
        _,_,_,service=stack(SyntheticProvider(claim='In 2021, led four people in a pilot with possible cost savings.'),SyntheticSupportCatalogue())
        self.assertEqual(service.ask_guest(slug='a',question='Results?',request_id='x').state,ResultState.SUPPORTED)
        _,_,_,service=stack()
        self.assertEqual(service.ask_guest(slug='a',question='Results?',request_id='x').state,ResultState.UNAVAILABLE)

    def test_mutation_during_generation_and_validation_releases_no_answer_or_citations(self):
        mutations=[lambda d:d.update(sharing_enabled=False),lambda d:d.update(sharing_epoch=2),
                   lambda d:d.update(publication_revision=2,current_revision=2),lambda d:d.update(draft_revision=3),
                   lambda d:d.update(draft_digest='d'*64),lambda d:d.update(placement_digest='d'*64),
                   lambda d:d.update(publication_media={'changed':True}),
                   lambda d:d['entries'][0].update(access_revision=5),lambda d:d['entries'][0].update(content_version=4),
                   lambda d:d['entries'][0].update(canonical_revision='0000000000000012'),
                   lambda d:d['entries'][0].update(current_content_sha256='e'*64),
                   lambda d:d['entries'][0].update(dependency_versions=['changed']),
                   lambda d:d['entries'][0].update(visitor_ai=False)]
        for phase in ('generation','validation'):
            for i,mutate in enumerate(mutations):
                with self.subTest(phase=phase,mutation=i):
                    db,repo,provider,service=stack(support=SyntheticSupportCatalogue())
                    hook=lambda:mutate(db.document)
                    if phase=='generation': provider.hook=hook
                    else: service.support=SyntheticSupportCatalogue(hook)
                    result=service.ask_guest(slug='a',question='What happened?',request_id='x')
                    self.assertEqual(result.state,ResultState.RETRYABLE)
                    self.assertEqual(result.citations,())
                    self.assertNotIn(SAVED_TEXT,result.text)

    def test_unavailable_recheck_and_provider_failure_preserve_question(self):
        db,repo,provider,service=stack(support=SyntheticSupportCatalogue())
        provider.hook=lambda:setattr(db,'fail',True)
        result=service.ask_guest(slug='a',question='My exact question?',request_id='x')
        self.assertEqual(result.state,ResultState.RETRYABLE)
        self.assertEqual(result.question,'My exact question?'); self.assertEqual(result.citations,())
        def fail(): raise ProviderUnavailableError('synthetic outage')
        _,_,_,service=stack(SyntheticProvider(hook=fail),SyntheticSupportCatalogue())
        result=service.ask_guest(slug='a',question='Question?',request_id='x')
        self.assertEqual(result.state,ResultState.RETRYABLE)
        self.assertNotIn('Pete',result.text)

    def test_unknown_and_ambiguous_provider_prose_never_leaks_hidden_fact_existence(self):
        for state,expected in ((AnswerState.NOT_ESTABLISHED,ResultState.UNSUPPORTED),(AnswerState.AMBIGUOUS,ResultState.AMBIGUOUS)):
            class BoundaryProvider:
                def answer(self,*args): return GroundedAnswer('x',state,'Hidden private secret exists.')
            _,_,_,service=stack(BoundaryProvider(),SyntheticSupportCatalogue())
            result=service.ask_guest(slug='a',question='Question?',request_id='x')
            self.assertEqual(result.state,expected); self.assertNotIn('secret',result.text)

    def test_preview_has_distinct_product_context_and_is_invalidated_by_draft_change(self):
        db,repo,provider,service=stack(support=SyntheticSupportCatalogue(),doc=snapshot(preview=True,ai=False))
        binding=repo.prepare_preview(expected_draft_revision=2,choices=(('entry-a',True),))
        result=service.ask_preview(binding=binding,question='Question?',request_id='x')
        self.assertEqual(result.state,ResultState.SUPPORTED)
        self.assertEqual(provider.seen[0][0].product,'member_visitor_ai_preview')
        db.document['draft_revision']=3
        result=service.ask_preview(binding=binding,question='Question?',request_id='y')
        self.assertEqual(result.state,ResultState.UNAVAILABLE); self.assertEqual(len(provider.seen),1)


class CitationAndNameTests(unittest.TestCase):
    def _stack(self, **kwargs):
        db, repo, provider, service = stack(support=SyntheticSupportCatalogue(), **kwargs)
        service.citations = CitationTicketStore(capacity=20, lifetime_seconds=120)
        return db, repo, provider, service

    def _ask(self, service):
        return service.ask_guest(slug='member-a', question='What happened?', request_id='citation')

    def test_each_access_checks_current_exact_excerpt_and_never_calls_provider(self):
        mutations = [lambda d:d.update(sharing_enabled=False), lambda d:d.update(sharing_epoch=2),
                     lambda d:d['entries'][0].update(visitor_ai=False),
                     lambda d:d['entries'][0].update(lifecycle='deleted'),
                     lambda d:d['entries'][0].update(access_revision=5),
                     lambda d:d['entries'][0].update(current_content_sha256='f'*64),
                     lambda d:d.update(profile_revision='changed'),
                     lambda d:d.update(entries=[])]
        for mutate in mutations:
            db, repo, provider, service = self._stack(doc=snapshot(display=False))
            result = self._ask(service)
            handle = result.citations[0].handle
            self.assertRegex(handle, r'^[A-Za-z0-9_-]{43}$')
            self.assertIsNone(service.read_citation(handle, slug='other'))
            self.assertIsNone(service.read_citation(handle, owner_preview=True))
            citation = service.read_citation(handle, slug='member-a')
            self.assertEqual(citation.excerpt, SAVED_TEXT)
            self.assertEqual(citation.label, 'Approved saved information')
            self.assertNotIn('entry-a', repr(citation))
            mutate(db.document)
            self.assertIsNone(service.read_citation(handle, slug='member-a'))
            self.assertEqual(len(provider.seen), 1)

    def test_preview_citation_requires_same_authenticated_owner_and_candidate(self):
        db, repo, provider, service = self._stack(doc=snapshot(preview=True, ai=False))
        binding = repo.prepare_preview(expected_draft_revision=2, choices=(('entry-a',True),))
        result = service.ask_preview(binding=binding, question='Question?', request_id='preview')
        handle = result.citations[0].handle
        self.assertIsNone(service.read_citation(handle, slug='member-a'))
        self.assertEqual(service.read_citation(handle, owner_preview=True).excerpt, SAVED_TEXT)
        repo.identity.owner = 'member-b'
        self.assertIsNone(service.read_citation(handle, owner_preview=True))
        repo.identity.owner = 'member-a'
        db.document['draft_revision'] += 1
        self.assertIsNone(service.read_citation(handle, owner_preview=True))

    def test_citation_final_race_unavailable_and_expiry_are_neutral(self):
        db, repo, provider, service = self._stack()
        now = [0]
        service.citations = CitationTicketStore(capacity=1, lifetime_seconds=10, clock=lambda: now[0])
        first = self._ask(service).citations[0].handle
        second = self._ask(service).citations[0].handle
        self.assertIsNone(service.read_citation(first, slug='member-a'))
        original = repo.recheck
        def raced(bundle):
            db.document['sharing_epoch'] += 1
            return original(bundle)
        repo.recheck = raced
        self.assertIsNone(service.read_citation(second, slug='member-a'))
        repo.recheck = original
        third = self._ask(service).citations[0].handle
        now[0] = 10
        self.assertIsNone(service.read_citation(third, slug='member-a'))
        self.assertIsNone(service.read_citation('../entry-a', slug='member-a'))
        db.fail = True
        self.assertIsNone(service.read_citation(second, slug='member-a'))

    def test_full_codec_or_sibling_metadata_cannot_be_exposed_as_excerpt(self):
        class WholeSourceProvider:
            def answer(self, request, sources):
                source = sources[0]
                cite = Citation('c1', source.source_version_key, 0, len(source.content), source.content)
                return GroundedAnswer('a', AnswerState.SUPPORTED, SAVED_TEXT,
                    (AnswerClaim('c1', SAVED_TEXT, AnswerKind.EVIDENCE, AnswerState.SUPPORTED, (cite,)),))
        _, _, _, service = self._stack(provider=WholeSourceProvider())
        result = self._ask(service)
        self.assertEqual(result.state, ResultState.UNSUPPORTED)
        self.assertEqual(result.citations, ())

    def test_name_requires_explicit_matching_current_publication_authority(self):
        db, repo, _, service = self._stack()
        self.assertIsNone(service.approved_guest_name('member-a'))
        class Names:
            owner = 'member-a'
            state = ReadState.CURRENT
            def read_approved(self, context):
                return ApprovedMemberName(self.owner, UsePurpose.VISITOR_AI, 'María del Carmen Li', 'v7')
            def recheck(self, context, name): return self.state
        names = service.names = Names()
        self.assertEqual(service.approved_guest_name('member-a'), 'María del Carmen Li')
        names.owner = 'member-b'
        self.assertIsNone(service.approved_guest_name('member-a'))
        names.owner = 'member-a'; names.state = ReadState.DENIED
        self.assertIsNone(service.approved_guest_name('member-a'))
        names.state = ReadState.CURRENT; db.fail = True
        self.assertIsNone(service.approved_guest_name('member-a'))


def operational_limits(**overrides):
    values = dict(maximum_request_bytes=16000, maximum_question_characters=4000,
                  concurrent_requests=2, timeout_seconds=1, window_seconds=60,
                  requests_per_client_window=20, maximum_clients=100,
                  cost_units_per_request=2, aggregate_cost_units_per_window=100)
    values.update(overrides)
    return VisitorOperationalLimits(**values)


class OperationalTests(unittest.TestCase):
    def test_sixth_question_eligible_and_rate_cost_and_window_are_independent(self):
        now = [0]
        port = SingleProcessVisitorProtections(clock=lambda: now[0])
        runtime = VisitorAiRuntime(operational_limits(requests_per_client_window=6), port, scope='single_process')
        try:
            for i in range(6):
                self.assertEqual(runtime.run(lambda:i, client_key='a'), i)
            with self.assertRaises(OperationalRefusal): runtime.run(lambda:99, client_key='a')
            self.assertEqual(runtime.run(lambda:'other', client_key='b'), 'other')
            now[0] = 60
            self.assertEqual(runtime.run(lambda:'again', client_key='a'), 'again')
        finally: runtime.close()
        runtime = VisitorAiRuntime(operational_limits(aggregate_cost_units_per_window=2),
                                   SingleProcessVisitorProtections(), scope='single_process')
        try:
            def fail(): raise ValueError('provider failed after starting')
            with self.assertRaises(ValueError): runtime.run(fail, client_key='a')
            with self.assertRaises(OperationalRefusal): runtime.run(lambda:1, client_key='b')
        finally: runtime.close()

    def test_timeout_keeps_slot_until_work_really_finishes(self):
        import threading
        started, release, finished = threading.Event(), threading.Event(), threading.Event()
        runtime = VisitorAiRuntime(operational_limits(concurrent_requests=1, timeout_seconds=.02),
                                   SingleProcessVisitorProtections(), scope='single_process')
        def blocked():
            started.set(); release.wait(2); finished.set(); return 1
        try:
            with self.assertRaises(OperationalRefusal): runtime.run(blocked, client_key='a')
            self.assertTrue(started.is_set()); self.assertFalse(finished.is_set())
            with self.assertRaises(OperationalRefusal): runtime.run(lambda:2, client_key='b')
        finally:
            release.set(); runtime.close()
        self.assertTrue(finished.is_set())

    def test_missing_distributed_accounting_never_falls_back_to_local(self):
        with self.assertRaises(ValueError):
            VisitorAiRuntime(operational_limits(), SingleProcessVisitorProtections(), scope='distributed')
        class Unavailable:
            scope='distributed'
            def reserve(self, *args): raise OSError('counter unavailable')
            def finish(self, lease): self.fail = True
            def release(self, lease): self.fail = True
        runtime = VisitorAiRuntime(operational_limits(), Unavailable(), scope='distributed')
        try:
            with self.assertRaises(OperationalRefusal) as caught:
                runtime.run(lambda:self.fail('provider must not run'), client_key='a')
            self.assertTrue(caught.exception.unavailable)
        finally: runtime.close()


# Selected model/private assistance integration regressions; fixtures only.
class PublicContractTests(unittest.TestCase):
    def test_both_native_low_phases_have_distinct_strict_schema(self):
        from services.member_visitor_ai_service import (
            _VisitorFoundryAnswer, _VisitorFoundrySupport, _REQUEST_DEADLINE,
        )
        from services.ai_foundation.azure_foundry import SpendLedger, LunaPriceSchedule
        from services.ai_foundation.contracts import AIRequest, Purpose, Audience
        from services.ai_foundation.codec import MEMBER_VISITOR_ANSWER_SCHEMA, MEMBER_VISITOR_SUPPORT_SCHEMA
        request = AIRequest('fiction-request', 'member_visitor_ai', Purpose.EVIDENCE_FINDER,
                            Audience.PUBLIC, 'fiction-subject', 'What is shared?')
        for kind, schema in [(_VisitorFoundryAnswer, MEMBER_VISITOR_ANSWER_SCHEMA),
                             (_VisitorFoundrySupport, MEMBER_VISITOR_SUPPORT_SCHEMA)]:
            from tests.test_resume_intake_runtime import SelectedPrivateTransport
            payload = ({'answer_id': 'fixture', 'state': 'not_established',
                        'summary': 'No supplied information establishes an answer.', 'claims': [],
                        'follow_up_questions': [], 'handoff': None, 'model_name': None,
                        'prompt_contract_version': None} if kind is _VisitorFoundryAnswer else
                       {'verdict': 'unsupported', 'summary_supported': False, 'claims': []})
            transport = SelectedPrivateTransport(payload=payload)
            provider = kind(endpoint='https://fixture.openai.azure.com', deployment='gpt-6-luna',
                token_provider=lambda: 'fiction-token', transport=transport,
                price_schedule=LunaPriceSchedule(), spend_ledger=SpendLedger(hard_cap_micro_usd=1000000, max_calls=1),
                maximum_input_tokens=66560, maximum_input_bytes=65536, maximum_output_tokens=700,
                answer_reasoning_effort='low', answer_json_schema=MEMBER_VISITOR_ANSWER_SCHEMA)
            provider.answer(request, ())
            wire = transport.calls[0]['json']
            self.assertEqual(wire['reasoning'], {'effort': 'low'})
            self.assertTrue(wire['text']['format']['strict'])
            self.assertEqual(wire['text']['format']['schema'], schema)


class VisitorExactQuoteSpanTests(unittest.TestCase):
    """The visitor adapter fixes only positions; the shared grounding stays strict."""
    def request(self):
        from services.ai_foundation.contracts import AIRequest, Audience, Purpose
        return AIRequest('fixture-span', 'member_visitor_ai', Purpose.PUBLIC_PROFILE_ANSWER,
                         Audience.PUBLIC, 'fixture-member', 'What is established?')

    def source(self, content, key='fixture-source-v1'):
        from services.ai_foundation.contracts import SourceVersion
        request = self.request()
        return SourceVersion.approved(source_version_key=key, source_key=key, version=1,
            subject_key=request.subject_key, title='Fictional approved information', content=content,
            allowed_audiences=frozenset({request.audience}), allowed_purposes=frozenset({request.purpose}))

    def payload(self, excerpt='Led four people.', start=0, end=1, key='fixture-source-v1'):
        return {'answer_id': 'fixture-answer', 'state': 'supported', 'summary': 'Led four people.',
            'claims': [{'claim_id': 'fixture-claim', 'text': 'Led four people.', 'kind': 'evidence',
                        'state': 'supported', 'limitation': None, 'citations': [{
                            'claim_id': 'fixture-claim', 'source_version_key': key,
                            'start': start, 'end': end, 'excerpt': excerpt}]}],
            'follow_up_questions': [], 'handoff': None, 'model_name': None,
            'prompt_contract_version': 'fixture-contract'}

    def derive(self, payload, sources, request=None):
        from copy import deepcopy
        from unittest.mock import patch
        from services.ai_foundation.azure_foundry import AzureFoundryResponsesProvider
        from services.member_visitor_ai_service import _VisitorFoundryAnswer
        original = deepcopy(payload)
        with patch.object(AzureFoundryResponsesProvider, 'answer', return_value=payload) as provider:
            answer = _VisitorFoundryAnswer.__new__(_VisitorFoundryAnswer).answer(request or self.request(), sources)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(provider.call_args.args, (request or self.request(), tuple(sources)))
        self.assertEqual(payload, original)
        return answer

    def test_unique_unicode_quote_changes_only_positions_and_passes_generic_grounding(self):
        from dataclasses import replace
        from services.ai_foundation.codec import parse_grounded_answer
        from services.ai_foundation.citation_validator import validate_grounded_answer
        quote = 'Café 😀 led four people.'
        source = self.source('É\n' + quote + '\nEnd.')
        payload = self.payload(quote, 1, 1 + len(quote))
        original = parse_grounded_answer(payload)
        answer = self.derive(payload, (source,))
        citation = answer.claims[0].citations[0]
        self.assertEqual((citation.start, citation.end), (2, 2 + len(quote)))
        expected = replace(original, claims=(replace(original.claims[0], citations=(
            replace(original.claims[0].citations[0], start=2, end=2 + len(quote)),)),))
        self.assertEqual(answer, expected)
        self.assertEqual(validate_grounded_answer(self.request(), (source,), answer), answer)

    def test_valid_unique_and_selected_repeated_occurrences_remain_exactly_unchanged(self):
        from services.ai_foundation.codec import parse_grounded_answer
        from services.ai_foundation.citation_validator import validate_grounded_answer
        quote = 'Led four people.'
        for content, start in [(quote, 0), (quote + ' / ' + quote, len(quote) + 3)]:
            with self.subTest(content=content):
                payload = self.payload(quote, start, start + len(quote))
                source = self.source(content)
                answer = self.derive(payload, (source,))
                self.assertEqual(answer, parse_grounded_answer(payload))
                validate_grounded_answer(self.request(), (source,), answer)

    def test_wrong_span_refuses_absent_ambiguous_overlapping_or_changed_literal_text(self):
        from services.ai_foundation.errors import GroundingValidationError
        cases = [('Led four people. / Led four people.', 'Led four people.'),
                 ('aaaa', 'aaa'), ('Led four people.', 'led four people.'),
                 ('Led  four people.', 'Led four people.'), ('Café', 'Cafe\u0301'),
                 ('Other text', 'Led four people.')]
        for content, quote in cases:
            with self.subTest(content=content, quote=quote), self.assertRaises(GroundingValidationError):
                self.derive(self.payload(quote), (self.source(content),))

    def test_named_version_never_searches_other_supplied_source(self):
        from services.ai_foundation.errors import GroundingValidationError
        for key in ['absent-version', 'fixture-source-v1']:
            with self.subTest(key=key), self.assertRaises(GroundingValidationError):
                self.derive(self.payload(key=key), (self.source('No matching text'),
                            self.source('Led four people.', 'other-version')))

    def test_authorization_refuses_before_provider_dispatch(self):
        from dataclasses import replace
        from unittest.mock import patch
        from services.ai_foundation.azure_foundry import AzureFoundryResponsesProvider
        from services.ai_foundation.contracts import Audience, Purpose
        from services.ai_foundation.errors import SourceAuthorizationError
        from services.member_visitor_ai_service import _VisitorFoundryAnswer
        source = self.source('Led four people.')
        for sources in [(replace(source, subject_key='another-member'),),
                        (replace(source, allowed_audiences=frozenset({Audience.OWNER})),),
                        (replace(source, allowed_purposes=frozenset({Purpose.EVIDENCE_FINDER})),),
                        (replace(source, content=source.content + ' Changed'),), (source, source)]:
            with self.subTest(sources=sources), patch.object(AzureFoundryResponsesProvider, 'answer') as provider:
                with self.assertRaises(SourceAuthorizationError):
                    _VisitorFoundryAnswer.__new__(_VisitorFoundryAnswer).answer(self.request(), sources)
                provider.assert_not_called()

    def test_closed_codec_refuses_malformed_contract_before_derivation(self):
        from services.ai_foundation.errors import AnswerContractError
        mutations = [lambda p: p.update(unknown=True), lambda p: p['claims'][0].update(unknown=True),
                     lambda p: p['claims'][0]['citations'][0].update(excerpt=''),
                     lambda p: p['claims'][0]['citations'][0].update(start=True),
                     lambda p: p['claims'][0]['citations'][0].update(end='16'),
                     lambda p: p['claims'][0]['citations'][0].update(claim_id='another-claim')]
        for mutate in mutations:
            payload = self.payload(); mutate(payload)
            with self.subTest(payload=payload), self.assertRaises(AnswerContractError):
                self.derive(payload, (self.source('Led four people.'),))

    def test_duplicate_citations_remain_refused_by_generic_grounding(self):
        from copy import deepcopy
        from services.ai_foundation.errors import GroundingValidationError
        from services.ai_foundation.citation_validator import validate_grounded_answer
        payload = self.payload()
        payload['claims'][0]['citations'].append(deepcopy(payload['claims'][0]['citations'][0]))
        source = self.source('Prefix Led four people.')
        answer = self.derive(payload, (source,))
        with self.assertRaises(GroundingValidationError):
            validate_grounded_answer(self.request(), (source,), answer)

    def service_provider(self, excerpt=SAVED_TEXT, summary=SAVED_TEXT):
        outer = self
        class Provider:
            seen = []
            def answer(self, request, sources):
                self.seen.append((request, sources))
                payload = outer.payload(excerpt, key=sources[0].source_version_key)
                payload['summary'] = summary; payload['claims'][0]['text'] = summary
                return outer.derive(payload, sources, request)
        return Provider()

    def test_derived_factual_excerpt_preserves_service_support_and_revoked_citation_access(self):
        provider = self.service_provider()
        db, repo, _, service = stack(provider, SyntheticSupportCatalogue())
        service.citations = CitationTicketStore(capacity=2, lifetime_seconds=120)
        result = service.ask_guest(slug='member-a', question='What happened?', request_id='fixture')
        self.assertEqual(result.state, ResultState.SUPPORTED)
        self.assertEqual(len(provider.seen), 1)
        handle = result.citations[0].handle
        self.assertEqual(service.read_citation(handle, slug='member-a').excerpt, SAVED_TEXT)
        db.document['entries'][0]['visitor_ai'] = False
        self.assertIsNone(service.read_citation(handle, slug='member-a'))
        self.assertEqual(len(provider.seen), 1)

    def test_derived_quotes_do_not_bypass_semantics_or_currentness(self):
        provider = self.service_provider(summary='The pilot saved $1 million.')
        _, _, _, service = stack(provider, SyntheticSupportCatalogue())
        result = service.ask_guest(slug='member-a', question='Results?', request_id='fixture')
        self.assertEqual(result.state, ResultState.UNSUPPORTED); self.assertEqual(result.citations, ())
        provider = self.service_provider()
        db, _, _, service = stack(provider, SyntheticSupportCatalogue())
        service.support = SyntheticSupportCatalogue(lambda: db.document.update(sharing_enabled=False))
        result = service.ask_guest(slug='member-a', question='Results?', request_id='fixture')
        self.assertEqual(result.state, ResultState.RETRYABLE); self.assertEqual(result.citations, ())

    def test_derived_metadata_and_cross_field_quotes_remain_unsupported(self):
        db, repo, _, _ = stack()
        source = repo.load_guest('member-a').sources[0]
        metadata = '14:canonical_typeS4:role'
        start = source.content.index(SAVED_TEXT)
        cross_field = source.content[start - 1:start + 5]
        class AlwaysSupported:
            def validate(self, *args): return SupportVerdict.SUPPORTED
        for quote in [metadata, cross_field]:
            with self.subTest(quote=quote):
                provider = self.service_provider(excerpt=quote)
                _, _, _, service = stack(provider, AlwaysSupported())
                result = service.ask_guest(slug='member-a', question='Results?', request_id='fixture')
                self.assertEqual(result.state, ResultState.UNSUPPORTED)
                self.assertEqual(result.citations, ())
