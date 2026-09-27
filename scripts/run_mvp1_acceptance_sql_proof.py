"""G-only isolated proof. Plan is read-only; execution needs a fresh exact decision.

Reuse E's unchanged pinned runtime, offline wheel verification and identity-bound
cleanup. Resource names are explicitly inherited, while invocation custody and
G authorization are new. No E SQL execution authorization is accepted here.
Queue/environment consistency is not independent authentication of Pete.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import sys
import tempfile
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from services import resume_publication_adapters as runtime_tools

PROOF_ID='ps-mvp1-g-sql-proof-20260926-01'
G_FILES=(
    'scripts/run_mvp1_acceptance_sql_proof.py','scripts/configure_mvp1_acceptance_sql_authority.py',
    'azure-pipelines-mvp1-acceptance-sql-proof.yml',
    'services/member_visitor_ai_sources.py','services/member_visitor_ai_repository.py','services/member_visitor_ai_service.py',
    'tests/__init__.py','tests/test_mvp1_acceptance_sql_engine.py','tests/test_member_visitor_ai_sources.py',
    'tests/test_member_visitor_ai_repository.py','tests/test_member_visitor_ai_service.py',
)


def source_manifest():
    manifest=runtime_tools.source_manifest(ROOT)
    for relative in G_FILES:
        path=ROOT/relative
        if path.is_symlink() or not path.is_file(): raise ValueError('missing/untrusted proof source: '+relative)
        manifest[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    # Include the actual production adapters used by the integrated oracle,
    # including their local Python dependencies. Never package host state.
    for path in sorted((ROOT/'services').rglob('*.py')):
        if path.is_symlink(): raise ValueError('untrusted service source')
        manifest[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def migration_closure(root):
    document=json.loads((root/'SQL FIles/Migrations/registry.json').read_text(encoding='utf-8'))
    by_id={item['id']:item for item in document['migrations']}
    ordered=[]; seen=set(); visiting=set()
    def visit(key):
        if key in seen: return
        if key in visiting or key not in by_id: raise ValueError('invalid migration dependency: '+key)
        visiting.add(key)
        item=by_id[key]
        for dependency in item['requires']: visit(dependency)
        visiting.remove(key); seen.add(key)
        ordered.append({name:item[name] for name in ('id','forward','rollback')})
    visit('PS-RESUME-IDENTITY-001')
    return ordered


def plan():
    from tests.test_mvp1_acceptance_sql_engine import ENGINE_CASES
    return {
        'proof_id':PROOF_ID,'status':'proposal_not_executed','production_authority':False,
        'source_manifest':source_manifest(),'source_manifest_digest':runtime_tools.manifest_digest(source_manifest()),
        'dependency_closure':migration_closure(ROOT),
        'added_migration':'PS-RESUME-IDENTITY-001','engine_cases':list(ENGINE_CASES),
        'sql_image':runtime_tools.SQL_IMAGE,'client_image':runtime_tools.CLIENT_IMAGE,
        'resources':{'network':runtime_tools.PROOF_NETWORK,'sql':runtime_tools.PROOF_SQL_CONTAINER,
                     'client':runtime_tools.PROOF_CLIENT_CONTAINER,'baked_image':runtime_tools.PROOF_CLIENT_IMAGE_NAME},
        'databases':[runtime_tools.PROOF_EMPTY_DATABASE,runtime_tools.PROOF_POPULATED_DATABASE],
        'limits':{'sql_memory':'3g','sql_cpus':'2','client_memory':'1g','client_cpus':'1',
                  'job_seconds':2700,'oracle_seconds':1800,'cleanup_seconds':300},
        'topology':{'internal_network':True,'host_ports':False,'mounts':False,'docker_socket':False},
        'reuse':'unchanged E runtime and pinned 18-wheel dependency lock; new G entrypoint and new invocation custody',
        'authority':'fresh dispatcher-verified exact source, plan and one-run decision required; never reuse E or F decisions',
    }


class AcceptanceRuntime(runtime_tools.IsolatedDockerCliRuntime):
    """Only replace the isolated Python oracle entrypoint; all safety checks stay inherited."""
    def _docker(self,args,extra_env=None,timeout=None):
        args=list(args)
        old='scripts/run_resume_publication_sql_proof.py'
        if args and args[0]=='exec' and old in args:
            index=args.index(old)
            # The inherited source verifier passes this path as data to python -c.
            # It must hash the unchanged E file, not select or execute the G entrypoint.
            source_hash_argument=(len(args)==6 and index==5
                and args[:4]==['exec',runtime_tools.PROOF_CLIENT_CONTAINER,'python','-c'])
            if not source_hash_argument:
                if args[index-2:index]!=['python','-B'] or args[index+1:index+2]!=['--in-client-oracles']:
                    raise runtime_tools.EngineProofError('unexpected_client_entrypoint')
                args[index]='scripts/run_mvp1_acceptance_sql_proof.py'
        return super()._docker(args,extra_env=extra_env,timeout=timeout)


def write_evidence(path,result):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def authorized(source,authorization):
    return bool(re.fullmatch(r'[0-9a-f]{40}',source or '') and authorization
        and os.environ.get('PEERSLATE_MVP1_ACCEPTANCE_EXECUTE')=='authorized'
        and os.environ.get('PEERSLATE_MVP1_ACCEPTANCE_AUTHORIZATION_REF')==authorization
        and os.environ.get('PEERSLATE_MVP1_ACCEPTANCE_EXPECTED_SHA')==source)


def inner(source,path):
    result={'proof_id':PROOF_ID,'source_sha':source,'status':'fail','cases':{},'diagnostics':{}}
    try:
        if (platform.system()!='Linux' or os.environ.get('PEERSLATE_RESUME_PUBLICATION_SQL_HOST')!=runtime_tools.PROOF_SQL_CONTAINER
            or os.environ.get('PEERSLATE_RESUME_PUBLICATION_CHECKOUT_SHA')!=source
            or not re.fullmatch(r'[0-9a-f]{40}',source)):
            raise ValueError('isolated client context required')
        runtime_tools.refuse_client_supplied_dsn(os.environ.get('PEERSLATE_RESUME_PUBLICATION_SQL_DSN',''))
        from tests.test_mvp1_acceptance_sql_engine import run_engine_contracts
        run_engine_contracts(runtime_tools.connect_from_client_environment,ROOT,result['cases'],result['diagnostics'])
        result['status']='pass'
    except Exception as error:
        result['error']=runtime_tools.sanitize_proof_error(error,(os.environ.get('MSSQL_SA_PASSWORD',''),))
    write_evidence(path,result)
    return 0 if result['status']=='pass' else 1


def execute(source,authorization,path):
    # No resources, wheel downloads or SQL before this refusal boundary.
    if not authorized(source,authorization):
        write_evidence(path,{'proof_id':PROOF_ID,'status':'refused','reason':'fresh_exact_authorization_required'})
        return 3
    if platform.system()!='Linux' or platform.machine().lower() not in {'x86_64','amd64'}:
        write_evidence(path,{'proof_id':PROOF_ID,'status':'refused','reason':'reviewed_linux_host_required'})
        return 3
    result={'proof_id':PROOF_ID,'source_sha':source,'authorization_ref':authorization,
            'status':'fail','proof_status':'fail','cleanup_status':'not_attempted'}
    owned=[]; runtime=None; handlers={}
    cancelled=False
    def cancel(*_):
        nonlocal cancelled
        if not cancelled:
            cancelled=True
            raise runtime_tools.EngineProofError('proof_cancelled')
    try:
        runtime_tools.assert_reviewed_source(source,ROOT)
        runtime_tools.refuse_client_supplied_dsn(os.environ.get('PEERSLATE_RESUME_PUBLICATION_SQL_DSN',''))
        for sig in (signal.SIGTERM,signal.SIGINT): handlers[sig]=signal.signal(sig,cancel)
        runtime=AcceptanceRuntime(); runtime.invocation_marker=PROOF_ID+'.'+uuid4().hex
        manifest=source_manifest()
        result['source_manifest']=manifest
        result['source_manifest_digest']=runtime_tools.manifest_digest(manifest)
        result['plan']=plan()
        acquired=runtime_tools.acquire_isolated_sql_runtime(runtime,source_root=ROOT,owned=owned,expected_manifest=manifest)
        result['acquisition']=acquired
        payload=runtime.run_client_oracles(source_sha=source)
        result['oracles']=payload
        from tests.test_mvp1_acceptance_sql_engine import ENGINE_CASES
        if (payload.get('proof_id')!=PROOF_ID or payload.get('source_sha')!=source or payload.get('status')!='pass'
            or payload.get('client_exit',0)!=0 or payload.get('cases')!={name:'pass' for name in ENGINE_CASES}):
            raise runtime_tools.EngineProofError('incomplete_G_engine_evidence')
        result['proof_status']='pass'
    except Exception as error:
        result['error']=runtime_tools.sanitize_proof_error(error,(getattr(runtime,'_sql_password',''),))
    finally:
        result['acquired_resources']=owned
        try:
            if runtime is not None:
                result['cleanup']=runtime_tools.cleanup_owned_resources(runtime,owned)
                result['cleanup_status']=result['cleanup'].get('status','fail')
        except Exception as error:
            result['cleanup_status']='fail'
            result['cleanup_error']=runtime_tools.sanitize_proof_error(error,(getattr(runtime,'_sql_password',''),))
        finally:
            for sig,previous in handlers.items(): signal.signal(sig,previous)
        result['status']='pass' if result['proof_status']=='pass' and result['cleanup_status']=='pass' else 'fail'
        write_evidence(path,result)
    return 0 if result['status']=='pass' else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--plan',action='store_true'); mode.add_argument('--execute',action='store_true')
    mode.add_argument('--in-client-oracles',action='store_true')
    parser.add_argument('--source-sha',default=''); parser.add_argument('--authorization-ref',default='')
    parser.add_argument('--evidence',type=Path,default=Path(tempfile.gettempdir())/'mvp1-acceptance-proof.json')
    args=parser.parse_args(argv)
    if args.in_client_oracles: return inner(args.source_sha,args.evidence)
    if args.execute: return execute(args.source_sha,args.authorization_ref,args.evidence)
    print(json.dumps(plan(),indent=2,sort_keys=True)); return 0


if __name__=='__main__': raise SystemExit(main())
