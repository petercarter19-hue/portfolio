import unittest
from services.ai_foundation.contracts import AnswerClaim,AnswerKind,AnswerState,Citation,GroundedAnswer
from services.ai_foundation.gateway import AIFoundationGateway
from services.ai_foundation.errors import ProviderUnavailableError
from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
from services.member_visitor_ai_service import MemberVisitorAiService,ResultState,SupportVerdict
from tests.test_member_visitor_ai_repository import SnapshotDatabase,Identity
from tests.test_member_visitor_ai_sources import snapshot,SAVED_TEXT


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
