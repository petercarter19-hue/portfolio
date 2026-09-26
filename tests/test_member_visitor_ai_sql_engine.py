"""Real SQL F oracles, called only by the separately authorized isolated runner.

Normal unittest discovery does not open SQL. The fixture provider/support
catalogue is synthetic; persistence and final fences use the real adapter.
"""
from pathlib import Path
import json
from uuid import uuid4

from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
from services.member_visitor_ai_sources import SourcesUnavailable
from services.member_visitor_ai_service import MemberVisitorAiService, ResultState
from services.ai_foundation.gateway import AIFoundationGateway
from services.resume_publication_contracts import ReadState
from services import resume_publication_adapters as proof
from tests.test_member_visitor_ai_service import SyntheticProvider, SyntheticSupportCatalogue
from tests.test_member_visitor_ai_sources import SAVED_TEXT

ENGINE_CASES = (
    'forward_verify_rollback_reapply', 'two_member_isolation', 'display_ai_matrix',
    'exact_committed_bytes_and_question', 'owner_preview_before_sharing',
    'preview_candidate_restriction', 'application_principal_boundary',
    'generation_sharing_race', 'validation_access_race', 'generation_canonical_race',
    'validation_draft_race', 'generation_evidence_race', 'media_dependency_race',
    'malformed_manifest_denied', 'populated_reader_rollback_preserves_data',
)


def run_engine_contracts(connect, root: Path, cases: dict):
    def check(condition, name):
        if not condition: raise AssertionError(name)
    def case(name, action):
        try: action()
        except Exception as error: raise RuntimeError('F oracle ' + name + ': ' + str(error)) from error
        cases[name]='pass'
    def sql(connection, query, params=()):
        cursor=connection.cursor()
        try:
            cursor.execute(query,params)
            return proof._fetch_procedure_result_sets(cursor)
        finally: cursor.close()
    migration=root/'SQL FIles/Migrations/proposed/PS-VISITOR-AI-001_readers.sql'
    rollback=root/'SQL FIles/Migrations/proposed/PS-VISITOR-AI-001_readers_rollback.sql'
    verify=root/'SQL FIles/Verification/PS-VISITOR-AI-001_readers_verify.sql'
    connection=connect(proof.PROOF_EMPTY_DATABASE)
    try:
        def lifecycle():
            for item in proof.resolve_publication_migration_closure(root):
                proof.apply_sql_file(connection,root/item['forward'])
            for file in (migration,verify,rollback,migration,verify,migration,verify):
                proof.apply_sql_file(connection,file)
        case('forward_verify_rollback_reapply',lifecycle)
    finally: connection.close()
    connection=connect(proof.PROOF_POPULATED_DATABASE)
    mutator=connect(proof.PROOF_POPULATED_DATABASE)
    try:
        for item in proof.resolve_publication_migration_closure(root):
            proof.apply_sql_file(connection,root/item['forward'])
        proof.apply_sql_file(connection,migration)
        owner=proof.seed_publication_owner(connection)['user_key']
        other=proof.seed_second_proof_owner(connection)
        def command(**payload):
            return proof.execute_procedure(mutator,'usp_CommitResumePublicationCommandForOwner',
                [('@UserKey',owner),('@RequestId',str(uuid4())),('@CommandJson',json.dumps(payload))])
        def state(): return proof.capture_publication_state(mutator)
        def permission(display=True,ai=True):
            command(type='change_permissions',entry_key=proof.PROOF_ENTRY_KEY,
                    expected_access_revision=state()['access_revision'],
                    permissions={'resume_display':display,'visitor_ai':ai,'private_assistance_excluded':True})
        def publish(media=None):
            command(type='publish',slug='f-proof-member',reviewed_digest='a'*64,media=media or {})
        before=state()
        proof.correct_publication_wording(mutator,owner,str(uuid4()),SAVED_TEXT,
            expected_content_version=before['content_version'],expected_access_revision=before['access_revision'])
        sql(mutator,"INSERT dbo.resume_drafts(owner_profile_id) SELECT profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id=p.user_id WHERE u.user_key=? AND NOT EXISTS(SELECT 1 FROM dbo.resume_drafts d WHERE d.owner_profile_id=p.profile_id)",(owner,))
        class Identity:
            def current_owner_key(self): return owner
        repository=SqlMemberVisitorAiRepository(proof.ProofDatabaseAdapter(connection),identity=Identity())
        def denied(fn):
            try: fn()
            except SourcesUnavailable: return
            raise AssertionError('ineligible source accepted')
        def isolation():
            permission(); publish()
            bundle=repository.load_guest('f-proof-member')
            check({s.subject_key for s in bundle.sources}=={owner},'wrong subject')
            class Other:
                def current_owner_key(self): return other
            foreign=SqlMemberVisitorAiRepository(proof.ProofDatabaseAdapter(connection),identity=Other())
            denied(lambda:foreign.prepare_preview(expected_draft_revision=0,choices=((proof.PROOF_ENTRY_KEY,True),)))
            denied(lambda:repository.load_guest('unpublished-other'))
        case('two_member_isolation',isolation)
        def matrix():
            for display in (False,True):
                for ai in (False,True):
                    permission(display,ai); publish()
                    bundle=repository.load_guest('f-proof-member')
                    check(len(bundle.sources)==int(ai),'display substituted for AI permission')
        case('display_ai_matrix',matrix)
        def supported(provider=None,support=None):
            provider=provider or SyntheticProvider()
            service=MemberVisitorAiService(repository,repository,AIFoundationGateway(provider),
                support=support or SyntheticSupportCatalogue())
            return service.ask_guest(slug='f-proof-member',question='What happened in 2021?',request_id=str(uuid4()))
        def exact():
            permission(False,True); publish()
            provider=SyntheticProvider(); answer=supported(provider)
            check(answer.state is ResultState.SUPPORTED,'real service did not answer')
            check(provider.seen[0][0].question=='What happened in 2021?','question lost')
            row=proof.execute_procedure(connection,'usp_GetMemberVisitorAiBySlug',[('@ProfileSlug','f-proof-member')])[0]
            doc=json.loads(row['snapshot_json']); source=provider.seen[0][1][0]
            check(source.content.encode('utf-8')==bytes.fromhex(doc['entries'][0]['content_hex']),'wrong evidence bytes')
            check(source.content_sha256==doc['entries'][0]['content_sha256'],'wrong digest')
            tx=sql(connection,'SELECT @@TRANCOUNT transaction_count')
            check(tx[-1][0]['transaction_count']==0,'reader retained transaction')
        case('exact_committed_bytes_and_question',exact)
        def preview():
            command(type='sharing_off'); permission(False,False)
            doc=json.loads(proof.execute_procedure(connection,'usp_GetMemberVisitorAiPreviewForOwner',[('@UserKey',owner)])[0]['snapshot_json'])
            binding=repository.prepare_preview(expected_draft_revision=doc['draft_revision'],choices=((proof.PROOF_ENTRY_KEY,True),))
            service=MemberVisitorAiService(repository,repository,AIFoundationGateway(SyntheticProvider()),support=SyntheticSupportCatalogue())
            result=service.ask_preview(binding=binding,question='What happened?',request_id=str(uuid4()))
            check(result.state is ResultState.SUPPORTED,'preview unavailable before sharing')
            denied(lambda:repository.load_guest('f-proof-member'))
            return binding
        binding=[]
        case('owner_preview_before_sharing',lambda:binding.append(preview()))
        case('preview_candidate_restriction',lambda:(permission(False,False),denied(lambda:repository.load_preview(binding[0]))))
        permission(); publish()
        def principal():
            sql(connection,"IF DATABASE_PRINCIPAL_ID('peerslate_app') IS NULL CREATE USER peerslate_app WITHOUT LOGIN; GRANT EXECUTE ON dbo.usp_GetMemberVisitorAiBySlug TO peerslate_app; GRANT EXECUTE ON dbo.usp_GetMemberVisitorAiPreviewForOwner TO peerslate_app;")
            # The raw adapter raises ValueError; prove the actual SQL permission
            # denial independently and retain authorized wrapper evidence.
            proof._effective_principal(connection,'peerslate_app',lambda:check(len(repository.load_guest('f-proof-member').sources)==1,'app wrapper denied'))
            def internal_denial():
                try: proof.execute_procedure(connection,'usp_MemberVisitorAiSnapshotInternal',[('@UserKey',owner),('@OwnerPreview',True)])
                except Exception as error:
                    check('permission' in str(error).lower() or '229' in str(error),'wrong internal denial')
                else: raise AssertionError('internal helper executable')
            proof._effective_principal(connection,'peerslate_app',internal_denial)
        case('application_principal_boundary',principal)
        def race(mutate,validation=False):
            permission(); publish()
            provider=SyntheticProvider(hook=(lambda:None) if validation else mutate)
            support=SyntheticSupportCatalogue(mutate if validation else lambda:None)
            answer=supported(provider,support)
            check(answer.state is ResultState.RETRYABLE and not answer.citations and SAVED_TEXT not in answer.text,'late mutation leaked answer')
        case('generation_sharing_race',lambda:race(lambda:command(type='sharing_off')))
        case('validation_access_race',lambda:race(lambda:permission(False,False),True))
        case('generation_canonical_race',lambda:race(lambda:sql(mutator,"UPDATE dbo.career_chapters SET summary=summary+N' changed',approved_wording=NULL WHERE chapter_key=?",(proof.PROOF_ENTRY_KEY,))))
        # Restore through the accepted canonical command for later cases.
        s=state(); proof.correct_publication_wording(mutator,owner,str(uuid4()),SAVED_TEXT,expected_content_version=s['content_version'],expected_access_revision=s['access_revision'])
        case('validation_draft_race',lambda:race(lambda:sql(mutator,'UPDATE dbo.resume_drafts SET draft_version=draft_version+1'),True))
        case('generation_evidence_race',lambda:race(lambda:sql(mutator,"UPDATE dbo.resume_publication_evidence SET content_sha256=REPLICATE('d',64) WHERE evidence_id=(SELECT MAX(evidence_id) FROM dbo.resume_publication_evidence)")))
        def media_race():
            asset='12121212-1212-4212-8212-121212121212'
            sql(mutator,"INSERT dbo.resume_catalog_assets(asset_id,asset_version,content_sha256,label,category,tags,width,height,origin,lifecycle) VALUES(?,1,REPLICATE('e',64),N'Proof art',N'proof',N'proof',800,600,N'generated_illustration',N'active')",(asset,))
            permission(); publish({'story_banner':{'active':True,'source_kind':'generated_illustration','source_key':asset,'asset_version':1,'content_sha256':'e'*64}})
            provider=SyntheticProvider(hook=lambda:sql(mutator,"UPDATE dbo.resume_catalog_assets SET lifecycle=N'withdrawn',withdrawn_at_utc=SYSUTCDATETIME() WHERE asset_id=?",(asset,)))
            answer=supported(provider)
            check(answer.state is ResultState.RETRYABLE and not answer.citations,'withdrawn media fence failed')
        case('media_dependency_race',media_race)
        permission(); publish()
        def malformed():
            sql(mutator,"UPDATE r SET visitor_ai_json=N'{\"foreign\":{}}' FROM dbo.resume_publication_revisions r JOIN dbo.resume_sharing_state s ON s.owner_profile_id=r.owner_profile_id AND s.current_revision=r.publication_revision WHERE s.public_slug=N'f-proof-member'")
            denied(lambda:repository.load_guest('f-proof-member'))
        case('malformed_manifest_denied',malformed)
        publish()
        def populated_rollback():
            before=state(); proof.apply_sql_file(connection,rollback)
            check(state()==before,'reader rollback changed canonical/publication state')
            proof.apply_sql_file(connection,migration); proof.apply_sql_file(connection,verify)
            check(repository.load_guest('f-proof-member').sources,'reapplied reader unavailable')
        case('populated_reader_rollback_preserves_data',populated_rollback)
        check(set(cases)==set(ENGINE_CASES) and all(v=='pass' for v in cases.values()),'missing F oracle')
    finally:
        mutator.close(); connection.close()
