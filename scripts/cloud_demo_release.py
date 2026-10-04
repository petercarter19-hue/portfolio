"""Exact-source restricted demo release. Secrets remain DPAPI/ARM memory only."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
import zipfile

SUBSCRIPTION = 'bd0ecf48-6940-4fd3-9687-3eaf72469d67'
GROUP = 'peerslate'
PLAN = 'peerslate-candidate-community-20260807'
PACKAGE = 'PS-ONBOARDING-CLOUD-DEMO-001'
OWNER = 'session:01a0faaf-5e48-7060-990a-c28989a8d247'
SITES = {'grok': 'peerslate-grok-demo-20261003', 'muse': 'peerslate-muse-demo-20261003'}
MEMBERS = {'grok': 'g-member-a', 'muse': 'g-member-b'}
ARM = 'https://management.azure.com'
ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = '/subscriptions/' + SUBSCRIPTION + '/resourceGroups/' + GROUP + '/providers/Microsoft.Web/'
PLAN_ID = RESOURCE_ROOT + 'serverfarms/' + PLAN

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=True)
    return result.stdout

def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def selected(path):
    if '/' not in path:
        return path.endswith('.py') or path in {'requirements.txt'}
    return (path.startswith(('services/', 'templates/', 'static/', 'tools/local_reviewer/', 'tools/cloud_demo/'))
            or path.startswith(('tests/', 'scripts/')) and path.endswith('.py'))

def package(source, directory):
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('Exact source required')
    directory.mkdir(parents=True, exist_ok=True)
    records = git('ls-tree', '-r', source).decode().splitlines()
    files = []
    for row in records:
        fields, path = row.split('\t', 1)
        mode, kind, blob = fields.split()
        if selected(path):
            if kind != 'blob' or mode not in {'100644', '100755'} or '..' in Path(path).parts:
                raise ValueError('Artifact includes unsafe Git entry')
            files.append((path, blob))
    artifact = directory / (source + '-cloud-demo.zip')
    receipt = directory / (source + '-cloud-demo.json')
    if artifact.exists() or receipt.exists():
        raise ValueError('Frozen artifact already exists; inspect instead of replacing')
    hashes = {}
    total = 0
    reader = subprocess.Popen(['git', '-C', str(ROOT), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        with zipfile.ZipFile(artifact, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path, blob in files:
                reader.stdin.write((blob + '\n').encode())
                reader.stdin.flush()
                line = reader.stdout.readline().decode().split()
                if len(line) != 3 or line[:2] != [blob, 'blob']:
                    raise ValueError('Git blob stream mismatch')
                size = int(line[2])
                total += size
                if total > 200_000_000:
                    raise ValueError('Artifact exceeds declared source budget')
                raw = reader.stdout.read(size)
                if len(raw) != size or reader.stdout.read(1) != b'\n':
                    raise ValueError('Incomplete Git blob')
                target = 'source/' + path
                archive.writestr(zipfile.ZipInfo(target, date_time=(1980,1,1,0,0,0)), raw, compress_type=zipfile.ZIP_DEFLATED)
                hashes[target] = {'sha256': sha(raw), 'git_blob': blob, 'source_path': path}
            requirements = git('show', source + ':requirements.txt') + b'\n' + git('show', source + ':tools/cloud_demo/requirements.txt')
            archive.writestr(zipfile.ZipInfo('requirements.txt',date_time=(1980,1,1,0,0,0)), requirements,compress_type=zipfile.ZIP_DEFLATED)
            hashes['requirements.txt'] = {'sha256': sha(requirements), 'derived': 'Exact source requirements plus dedicated pinned waitress overlay'}
    finally:
        reader.stdin.close()
        reader.wait(timeout=10)
    manifest = {'schema_version': 1, 'package': PACKAGE, 'source_sha': source,
                'created_at': now(), 'artifact': str(artifact.resolve()),
                'artifact_sha256': sha(artifact.read_bytes()), 'artifact_bytes': artifact.stat().st_size,
                'files': hashes, 'source_bytes': total,
                'private_pc_content_copied': False, 'credentials_in_artifact': False,
                'startup': 'python -u source/tools/cloud_demo/wsgi.py'}
    write_new(receipt, manifest)
    print(json.dumps({'result':'packaged','manifest':str(receipt),'source':source,'bytes':manifest['artifact_bytes'],'files':len(hashes)}))

def load_manifest(path, *, accepted=False):
    value = json.loads(path.read_bytes())
    if value.get('schema_version') != 1 or value.get('package') != PACKAGE or not re.fullmatch('[0-9a-f]{40}', value.get('source_sha','')):
        raise ValueError('Invalid release manifest')
    if value.get('startup') != 'python -u source/tools/cloud_demo/wsgi.py':
        raise ValueError('Dedicated accepted startup required')
    artifact = Path(value['artifact'])
    if not artifact.is_file() or artifact.is_symlink() or sha(artifact.read_bytes()) != value['artifact_sha256']:
        raise ValueError('Frozen artifact changed')
    with zipfile.ZipFile(artifact) as archive:
        expected = {'source/'+row.split('\t',1)[1] for row in git('ls-tree','-r',value['source_sha']).decode().splitlines()
                    if selected(row.split('\t',1)[1])} | {'requirements.txt'}
        if set(value['files']) != expected:
            raise ValueError('Complete selected source inventory required')
        if set(archive.namelist()) != set(value['files']) or len(archive.namelist()) != len(value['files']):
            raise ValueError('Artifact entries differ')
        for name, record in value['files'].items():
            if sha(archive.read(name)) != record['sha256']:
                raise ValueError('Artifact file changed')
            if 'source_path' in record:
                if name != 'source/'+record['source_path']:
                    raise ValueError('Artifact source path binding differs')
                raw = git('show', value['source_sha'] + ':' + record['source_path'])
                if sha(raw) != record['sha256']:
                    raise ValueError('Artifact is not exact Git source')
            elif name != 'requirements.txt':
                raise ValueError('Missing exact Git file binding')
        required = git('show',value['source_sha']+':requirements.txt') + b'\n' + git('show',value['source_sha']+':tools/cloud_demo/requirements.txt')
        if archive.read('requirements.txt') != required:
            raise ValueError('Dependency overlay differs from accepted source')
    if accepted:
        git('fetch', 'origin', '--prune')
        git('merge-base', '--is-ancestor', value['source_sha'], 'origin/main')
        receipt_path = 'docs/governance/lane_claims/receipts/' + PACKAGE + '.json'
        reviewed = json.loads(git('show', value['source_sha'] + ':' + receipt_path))
        if reviewed.get('result') != 'pass' or reviewed.get('review_type') != 'independent':
            raise ValueError('Accepted independent source review required')
        for path in ('tools/cloud_demo/runtime.py', 'tools/cloud_demo/wsgi.py', 'scripts/cloud_demo_release.py'):
            if git('show', reviewed['candidate_sha'] + ':' + path) != git('show', value['source_sha'] + ':' + path):
                raise ValueError('Accepted source differs from independent candidate')
        if git('show', value['source_sha'] + ':scripts/cloud_demo_release.py').replace(b'\r\n',b'\n') != Path(__file__).read_bytes().replace(b'\r\n',b'\n'):
            raise ValueError('Running operator is not accepted source')
    return value

def bind_accepted(source, manifest_path):
    if not re.fullmatch('[0-9a-f]{40}',source):
        raise ValueError('Exact accepted source required')
    previous = load_manifest(manifest_path)
    value = dict(previous,source_sha=source,artifact_origin_source=previous['source_sha'],
                 accepted_binding_at=now())
    target = manifest_path.parent / (source+'-cloud-demo.json')
    write_new(target,value)
    try:
        load_manifest(target,accepted=True)
    except Exception:
        # Keep failed binding as evidence; never overwrite it or call it accepted.
        raise
    print(json.dumps({'result':'accepted-byte-equivalence','manifest':str(target),
        'source_sha':source,'artifact_origin_source':previous['source_sha'],
        'artifact_sha256':value['artifact_sha256'],'zip_duplicated':False}))

class Arm:
    def __init__(self):
        result = subprocess.run([shutil.which('az.cmd') or 'az', 'account','get-access-token',
            '--subscription',SUBSCRIPTION,'--resource',ARM,'-o','json'],capture_output=True,text=True,check=False)
        if result.returncode:
            raise RuntimeError('Existing Azure credential unavailable; no token output')
        self.token = json.loads(result.stdout)['accessToken']

    def request(self, path, body=None, method='GET'):
        request = urllib.request.Request(ARM + path + '?api-version=2024-11-01',
            data=None if body is None else json.dumps(body).encode(),method=method,
            headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            if error.code == 404 and method == 'GET':
                return None
            raise RuntimeError('ARM '+method+' refused: HTTP '+str(error.code)) from None

    def verify_plan(self):
        plan = self.request(PLAN_ID)
        if (not plan or plan['id'].lower() != PLAN_ID.lower() or plan['sku']['name'] != 'B1'
                or plan['sku']['capacity'] != 1 or plan['properties'].get('reserved') is not True):
            raise ValueError('Existing one-instance Linux B1 plan required; no scaling/new plan')
        candidate = self.request(RESOURCE_ROOT+'sites/peerslate-candidate')
        production = self.request(RESOURCE_ROOT+'sites/peerslate-pete')
        if not candidate or candidate['properties']['state'] != 'Stopped' or candidate['properties']['serverFarmId'].lower() != PLAN_ID.lower():
            raise ValueError('Stopped candidate must remain intact')
        if not production or production['properties']['serverFarmId'].lower() == PLAN_ID.lower():
            raise ValueError('Production boundary differs from expected')
        return {'observed_at':now(),'plan_id':PLAN_ID,'sku':plan['sku'],
                'candidate_state':candidate['properties']['state'], 'production_state':production['properties']['state']}

def check_site(site, target):
    if not site or site['name'] != SITES[target] or site['tags'].get('peerslatePackage') != PACKAGE or site['tags'].get('peerslateWriter') != OWNER:
        raise ValueError('Site ownership differs; do not adopt')
    if site['properties']['serverFarmId'].lower() != PLAN_ID.lower():
        raise ValueError('Site is on an unexpected plan')
    return site

class Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]

def dpapi(raw, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Owner-local Windows secure credential delivery required')
    memory = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    source, result = Blob(len(raw), memory), Blob()
    crypt = ctypes.windll.crypt32
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), wintypes.LPVOID if decrypt else wintypes.LPCWSTR,
                         ctypes.POINTER(Blob), wintypes.LPVOID, wintypes.LPVOID,
                         wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if decrypt:
        ok = function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result))
    else:
        ok = function(ctypes.byref(source), 'PeerSlate fictional cloud demo', None, None, None, 1, ctypes.byref(result))
    if not ok:
        raise RuntimeError('Windows protected credential operation failed')
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes, free.restype = [wintypes.HLOCAL], wintypes.HLOCAL
        free(result.pbData)

def vault_path():
    directory = Path(os.environ['LOCALAPPDATA']) / 'PeerSlate' / 'CloudDemo' / PACKAGE
    if any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (directory,*directory.parents)):
        raise ValueError('Credential destination contains a link')
    directory.mkdir(parents=True, exist_ok=True)
    identity = subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,check=True).stdout
    sid = re.search(r'S-1-5-[0-9-]+',identity).group()
    acl = subprocess.run(['icacls',str(directory),'/inheritance:r','/grant:r',sid+':(OI)(CI)F',
                          '*S-1-5-18:(OI)(CI)F'],capture_output=True,text=True,check=False)
    if acl.returncode:
        raise RuntimeError('Secure credential directory ACL failed')
    return directory / 'credentials.dpapi'

def credentials(target, site):
    path = vault_path()
    entries = json.loads(dpapi(path.read_bytes(), True)) if path.exists() else {}
    origin = 'https://' + site['properties']['defaultHostName']
    if not re.fullmatch(r'https://[a-z0-9.-]+\.azurewebsites\.net', origin):
        raise ValueError('Supported platform HTTPS hostname required')
    if target not in entries:
        from werkzeug.security import generate_password_hash
        password = secrets.token_urlsafe(32)
        owner = MEMBERS[target]
        entries[target] = {'origin':origin, 'username':target+'-demo', 'password':password,
            'password_hash':generate_password_hash(password,method='scrypt'),
            'signing_key':secrets.token_hex(32), 'owner':owner,
            'namespace':sha((origin+'\0'+owner).encode())}
        temporary = path.with_suffix('.writing')
        with temporary.open('xb') as stream:
            stream.write(dpapi(json.dumps(entries).encode()))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    if entries[target]['origin'] != origin:
        raise ValueError('Credential/site binding differs')
    return entries[target]

def deploy(manifest_path, target):
    release = load_manifest(manifest_path, accepted=True)
    evidence = manifest_path.parent
    intent = evidence / ('DEPLOY_INTENT_'+target+'_'+release['source_sha']+'.json')
    if intent.exists():
        raise ValueError('Existing deployment attempt; inspect its exact operation, never replay')
    arm = Arm()
    plan = arm.verify_plan()
    site_path = RESOURCE_ROOT+'sites/'+SITES[target]
    site = arm.request(site_path)
    if site:
        check_site(site,target)
    write_new(intent,{'target':target,'site':SITES[target],'source_sha':release['source_sha'],
        'artifact_sha256':release['artifact_sha256'],'requested_at':now(),'plan':plan,
        'scope':'Restricted fictional demo only; no production/candidate/state/reset/provider action'})
    if not site:
        site = arm.request(site_path,{'location':'Central US','kind':'app,linux',
            'tags':{'peerslatePackage':PACKAGE,'peerslateWriter':OWNER},
            'properties':{'serverFarmId':PLAN_ID,'httpsOnly':True,'enabled':False,
                'clientAffinityEnabled':False,'siteConfig':{'linuxFxVersion':'PYTHON|3.12',
                'appCommandLine':release['startup'],'numberOfWorkers':1,'alwaysOn':False,
                'ftpsState':'Disabled','minTlsVersion':'1.2','http20Enabled':True}}},'PUT')
    check_site(site,target)
    arm.request(site_path+'/stop',{},'POST')
    secure = credentials(target,site)
    settings = {'DEMO_ORIGIN':secure['origin'],'DEMO_USERNAME':secure['username'],
        'DEMO_PASSWORD_HASH':secure['password_hash'],'DEMO_SIGNING_KEY':secure['signing_key'],
        'DEMO_OWNER':secure['owner'],'DEMO_NAMESPACE':secure['namespace'],
        'DEMO_DATA':'/home/peerslate-fictional-demo','DEMO_SOURCE_SHA':release['source_sha'],
        'SCM_DO_BUILD_DURING_DEPLOYMENT':'true','WEBSITES_PORT':'8000',
        'WEBSITES_ENABLE_APP_SERVICE_STORAGE':'true','PYTHONDONTWRITEBYTECODE':'1'}
    arm.request(site_path+'/config/appsettings',{'properties':settings},'PUT')
    config = arm.request(site_path+'/config/web',{'properties':{'linuxFxVersion':'PYTHON|3.12',
        'appCommandLine':release['startup'],'numberOfWorkers':1,'alwaysOn':False,
        'ftpsState':'Disabled','minTlsVersion':'1.2','http20Enabled':True}},'PUT')
    if config['properties']['appCommandLine'] != release['startup'] or config['properties']['numberOfWorkers'] != 1:
        raise ValueError('Dedicated startup/one worker setting not applied')
    # Azure CLI owns supported ZipDeploy authentication; no secrets in argv.
    result = subprocess.run([shutil.which('az.cmd') or 'az','webapp','deploy',
        '--subscription',SUBSCRIPTION,'--resource-group',GROUP,'--name',SITES[target],
        '--type','zip','--src-path',release['artifact'],'--restart','false',
        '--track-status','false','--async','true','-o','json'],capture_output=True,text=True,timeout=900)
    try:
        remote = json.loads(result.stdout) if result.stdout.strip() else {}
    except ValueError:
        remote = {}
    safe = {'target':target,'source_sha':release['source_sha'],'artifact_sha256':release['artifact_sha256'],
        'recorded_at':now(),'returncode':result.returncode,
        'deployment':{k:remote.get(k) for k in ('id','status','status_text','start_time','end_time')},
        'origin':secure['origin'],'credentials_destination':str(vault_path()),
        'cloud_browser_connection':'unproven','no_private_pc_copy':True,'provider_calls':0}
    write_new(evidence / ('DEPLOY_REQUEST_'+target+'_'+release['source_sha']+'.json'),safe)
    if result.returncode:
        raise RuntimeError('Deployment command did not confirm acceptance. Inspect the recorded operation; do not replay.')
    # Start only after supported build completion is separately verified.
    print(json.dumps(safe))

def deployment_status(target):
    result = subprocess.run([shutil.which('az.cmd') or 'az','webapp','log','deployment','list',
        '--subscription',SUBSCRIPTION,'--resource-group',GROUP,'--name',SITES[target],'-o','json'],
        capture_output=True,text=True,timeout=60)
    if result.returncode:
        raise RuntimeError('Deployment status unavailable; no start/replay')
    value = json.loads(result.stdout)
    return value if isinstance(value,list) else value.get('value',[])

def operate(target, action, manifest_path=None):
    arm = Arm()
    arm.verify_plan()
    path = RESOURCE_ROOT+'sites/'+SITES[target]
    site = check_site(arm.request(path),target)
    if action == 'deployment-status':
        entries = deployment_status(target)
        print(json.dumps([{'id':r.get('id'),'status':r.get('status'),
            'complete':r.get('complete'),'start_time':r.get('start_time'),
            'end_time':r.get('end_time')} for r in entries]))
    elif action == 'inspect':
        print(json.dumps({'site':site['name'],'origin':'https://'+site['properties']['defaultHostName'],
            'state':site['properties']['state'],'httpsOnly':site['properties']['httpsOnly'],
            'plan':site['properties']['serverFarmId']}))
    else:
        if action in {'start','restart'}:
            if manifest_path is None:
                raise ValueError('Exact accepted manifest required before start/restart')
            release = load_manifest(manifest_path,accepted=True)
            attempt = manifest_path.parent / ('DEPLOY_REQUEST_'+target+'_'+release['source_sha']+'.json')
            intent = manifest_path.parent / ('DEPLOY_INTENT_'+target+'_'+release['source_sha']+'.json')
            observed = json.loads(attempt.read_bytes())
            requested = json.loads(intent.read_bytes())
            if (observed['returncode'] != 0 or observed['artifact_sha256'] != release['artifact_sha256']
                    or observed.get('target') != target or observed.get('source_sha') != release['source_sha']
                    or requested.get('target') != target or requested.get('source_sha') != release['source_sha']
                    or requested.get('artifact_sha256') != release['artifact_sha256']):
                raise ValueError('Successful exact deployment request required')
            known = observed['deployment'].get('id')
            if not isinstance(known, str) or not known.strip():
                raise ValueError('Exact remote deployment ID unavailable; inspect the recorded operation, do not infer or replay')
            entries = deployment_status(target)
            matches = [row for row in entries if row.get('id') == known]
            if len(matches) != 1 or matches[0].get('status') != 4 or not matches[0].get('complete'):
                raise ValueError('Unique completed successful build for exact attempt required')
            settings = arm.request(path+'/config/appsettings/list',{},'POST')['properties']
            if settings.get('DEMO_SOURCE_SHA') != release['source_sha'] or settings.get('DEMO_OWNER') != MEMBERS[target]:
                raise ValueError('Actual site source/owner binding differs')
        arm.request(path+'/'+action,{},'POST')
        print(json.dumps({'site':site['name'],'requested_action':action,'recorded_at':now()}))

def show_credentials(target):
    path = vault_path()
    entry = json.loads(dpapi(path.read_bytes(),True))[target]
    import tkinter as tk
    root = tk.Tk()
    root.title('PeerSlate fictional demo credentials')
    for label,key in (('Site','origin'),('Account','username'),('Password','password')):
        tk.Label(root,text=label).pack()
        value = tk.Entry(root,width=75,show='*' if key=='password' else '')
        value.insert(0,entry[key])
        value.pack()
        def copy(text=entry[key]):
            root.clipboard_clear()
            root.clipboard_append(text)
        tk.Button(root,text='Copy '+label,command=copy).pack()
    tk.Label(root,text='Fictional demo only. Paste sign-in directly in the receiving browser.').pack()
    root.mainloop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['package','validate','bind-accepted','deploy','inspect','deployment-status','start','stop','restart','show-credentials'])
    parser.add_argument('--source')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--target',choices=SITES)
    args = parser.parse_args()
    if args.mode=='package':
        package(args.source,args.output)
    elif args.mode=='validate':
        manifest = load_manifest(args.manifest)
        print(json.dumps({'result':'pass','source_sha':manifest['source_sha'],'artifact_sha256':manifest['artifact_sha256']}))
    elif args.mode=='bind-accepted':
        bind_accepted(args.source,args.manifest)
    elif args.mode=='deploy':
        deploy(args.manifest,args.target)
    elif args.mode=='show-credentials':
        show_credentials(args.target)
    else:
        operate(args.target,args.mode,args.manifest)

if __name__=='__main__':
    main()
