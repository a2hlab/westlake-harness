#!/usr/bin/env python3
"""Offline v3c composition. Reuses pinned prepare/loader; never deploys."""
import argparse,copy,csv,hashlib,json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'tools'))
from deploy_generation import load_package,replacement_source,save,sha,validate_replacement
from prepare_generation_replacement import prepare
ALIASES=('libapp_native_loader.so','libwestlake_android_runtime_provider.so')

def pin(path,expected):
    if sha(path)!=expected:raise ValueError('input SHA changed: '+str(path))

def mounted_source(m,target):
    for row in sorted(m['mounts'],key=lambda r:len(r['target']),reverse=True):
        if target==row['target'] or target.startswith(row['target']+'/'):
            return row['source']+target[len(row['target']):]
    raise ValueError('target has no mount: '+target)

def audit(m):
    for target,expected in m['live_hashes'].items():
        source=mounted_source(m,target)
        if m['files'].get(source)!=expected:raise ValueError('live hash / fresh-mount mismatch: '+target)
    route='/system/lib64/westlake/route-a/'+m['generation']+'/'
    for name in ALIASES:
        values=[m['files']['payload/'+p+'/'+name] for p in ['android/lib64','route']]
        values += [m['live_hashes'][p+name] for p in ['/system/android/lib64/',route]]
        if len(set(values))!=1:raise ValueError('split alias: '+name)
    return True

def parse_fingerprint(path):
    out={}
    for line in Path(path).read_text().splitlines():
        h,p=line.split(None,1)
        if len(h)!=64:raise ValueError('invalid fingerprint')
        if p in out:raise ValueError('duplicate fingerprint path')
        out[p]=h
    return out

def board_report(key,b,candidate,m,inputs):
    old=json.loads((HERE/b['manifest_snapshot']).read_text())
    observed=parse_fingerprint(HERE/b['fingerprint_snapshot'])
    pin(HERE/b['manifest_snapshot'],b['package_sha256'])
    pin(HERE/b['fingerprint_snapshot'],b['fingerprint_sha256'])
    # Validate recorded resident except the explicitly external Java overlay.
    jar='/system/android/framework/oh-adapter-runtime.jar'
    conflicts=[p for p,h in old['live_hashes'].items() if p!=jar and p in observed and observed[p]!=h]
    missing_evidence=[p for p in old['live_hashes'] if p not in observed]
    changes=[]
    for a in inputs['artifacts']:
        targets=['/system/bin/appspawn-x'] if a['name']=='appspawn-x' else ['/system/android/lib64/'+a['name']]
        if a['name'] in ALIASES:targets.insert(0,'/system/lib64/westlake/route-a/'+m['generation']+'/'+a['name'])
        for target in targets:
            before=observed.get(target)
            # Inventory + recorded manifest agree on absence; no fresh board probe is claimed.
            mode='keep' if before==a['sha256'] else 'replace' if before else 'add'
            changes.append(dict(name=a['name'],target=target,before_sha256=before,after_sha256=a['sha256'],action=mode,evidence='recorded fingerprint' if before else 'absent in recorded fingerprint and resident manifest',observed_now=False))
    for name in ALIASES:
        # Prove the existing one-file validator rejects a coherent alias transition.
        proposed=copy.deepcopy(old)
        a=next(a for a in inputs['artifacts'] if a['name']==name)
        proposed['files']['payload/route/'+name]=a['sha256']
        for prefix in ['/system/android/lib64/','/system/lib64/westlake/route-a/'+m['generation']+'/']:
            proposed['live_hashes'][prefix+name]=a['sha256']
        try:validate_replacement(old,proposed,'/system/android/lib64/'+name)
        except ValueError as error:
            alias_error=str(error)
            break
    else:alias_error=None
    new_files=[p for p in m['files'] if p.startswith('payload/android/') and p not in old['files']]
    cmd=[sys.executable,str(HERE/'tools/deploy_generation.py'),b['serial'],str(candidate),'--dry-run','--lane','cx-bms']
    proc=subprocess.run(cmd,text=True,capture_output=True,check=True)
    result=json.loads(proc.stdout)
    if result.get('device_io') is not False or not result.get('passed'):raise ValueError('unexpected dry-run result')
    save(HERE/'evidence'/('dry-run-'+key+'.json'),dict(command=cmd,stdout=result,stderr=proc.stderr))
    modified=[x for x in changes if x['action']!='keep']
    blockers=[dict(id='new-link-provenance',reason='39c2cfe9/d1a1961d artifact hashes verified, but exact new static-link recipe/commit not yet supplied; inherited recipe does not reproduce the new link.',source='inputs.json'),dict(id='jar-selection',reason='Bundled r8b is inherited only; rollout needs outer-selected Java namespace JAR with HTML load disabled. No such JAR is selected by this assembly.',source='evidence/outer-steering.txt'),dict(id='alias-transaction',reason=alias_error,source='tools/deploy_generation.py:111-115',effect='No supported sequence of existing --replace calls can converge route and Android aliases to this coherent manifest.'),dict(id='full-deploy-absent-before-hash',reason='deploy() hashes every future payload/android file before activation, including additions absent on recorded resident.',source='tools/deploy_generation.py:337',paths=new_files,effect='Conditional: fresh whole-package dry-run does not exercise this device preflight. After resident rollback, underlying availability is unknown; validate absent-file handling and rollback before choosing full activation.',classification='conditional')]
    return dict(serial=b['serial'],recorded_package=b['package'],recorded_manifest_sha256=b['package_sha256'],fingerprint_sha256=b['fingerprint_sha256'],fingerprint_short=hashlib.sha256((HERE/b['fingerprint_snapshot']).read_text().strip().encode()).hexdigest()[:12],recorded_live_conflicts=conflicts,missing_recorded_live_evidence=missing_evidence,jar_overlay_sha256=observed.get(jar),payload_jar_sha256=m['live_hashes'][jar],changes=changes,changed_live_paths=len(modified),changed_components=len({x['name'] for x in modified}),adds=sum(x['action']=='add' for x in changes),replaces=sum(x['action']=='replace' for x in changes),package_dry_run_passed=True,device_io=False,board_readiness='unknown',executable_incremental_steps=None,full_activation_phases_if_deployer_support_is_added=['suspend external JAR overlay','rollback resident owned generation including singles','activate coherent v3c package with absence-aware preflight/rollback','apply outer-selected Java namespace JAR and verify'],blockers=blockers)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=HERE/'candidate');a=ap.parse_args()
    candidate=a.out.resolve();inputs=json.loads((HERE/'inputs.json').read_text());base=Path(inputs['base'])
    if candidate.exists():raise ValueError('refuse to overwrite candidate: '+str(candidate))
    for name,h in inputs['tools'].items():pin(HERE/'tools'/name,h)
    pin(base/'package.json',inputs['base_manifest_sha256']);old=load_package(base)
    for x in inputs['artifacts']:pin(Path(x['path']),x['sha256'])
    work=HERE/'work';work.mkdir(exist_ok=False)
    current=base;chain=[]
    for x in sorted(inputs['artifacts'],key=lambda x:x['order']):
        name=x['name'];m=load_package(current)
        if name=='appspawn-x':target='/system/bin/appspawn-x'
        elif name in ALIASES:target='/system/lib64/westlake/route-a/'+m['generation']+'/'+name
        else:target='/system/android/lib64/'+name
        source=('payload/runtime/appspawn-x' if name=='appspawn-x' else 'payload/route/'+name if name in ALIASES else 'payload/android/lib64/'+name)
        adding=source not in m['files']
        if m['files'].get(source)==x['sha256']:
            chain.append(dict(name=name,target=target,action='retain',sha256=x['sha256']));continue
        out=work/(str(len(chain)).zfill(2)+'-'+name)
        prepare(current,target,Path(x['path']),x['sha256'],out,adding=adding)
        chain.append(dict(name=name,target=target,action='add' if adding else 'replace',sha256=x['sha256'],package_manifest_sha256=sha(out/'package.json')))
        current=out
    shutil.copytree(current,candidate)
    m=load_package(candidate)
    # Coherent final package, NOT a --replace intermediate: mirrors two physical
    # payload copies and both live paths. Existing mounts remain unchanged.
    route='/system/lib64/westlake/route-a/'+m['generation']+'/'
    for name in ALIASES:
        h=m['files']['payload/route/'+name]
        shutil.copyfile(candidate/'payload/route'/name,candidate/'payload/android/lib64'/name)
        m['files']['payload/android/lib64/'+name]=h
        m['live_hashes'][route+name]=h;m['live_hashes']['/system/android/lib64/'+name]=h
    m['variant']='v3c-candidate-java-namespace'
    m['manifest_route']='B87 + retained network host + B91 CE + B92 ANL/provider aliases + B86/B93 TLS+gapfill; HTML excluded; external JAR required; untested on device'
    provenance=dict(inputs_sha256=sha(HERE/'inputs.json'),base_manifest_sha256=inputs['base_manifest_sha256'],artifacts=inputs['artifacts'],excluded=inputs['excluded'],assembly_chain=chain,device_io=False)
    save(candidate/'receipts/V3C_ASSEMBLY.json',provenance)
    m['files']['receipts/V3C_ASSEMBLY.json']=sha(candidate/'receipts/V3C_ASSEMBLY.json')
    audit(m);save(candidate/'package.json',m);load_package(candidate)
    reports={key:board_report(key,b,candidate,m,inputs) for key,b in inputs['boards'].items()}
    rows=[dict(board=k,**r) for k,b in reports.items() for r in b['changes']]
    with (HERE/'board-deltas.csv').open('w') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    with (HERE/'artifacts.csv').open('w') as f:
        wr=csv.DictWriter(f,fieldnames=['name','sha256','path','source_commits','source_paths','recipe','recipe_sha256']);wr.writeheader()
        for x in inputs['artifacts']:wr.writerow({k:';'.join(x[k]) if isinstance(x[k],list) else x[k] for k in wr.fieldnames})
    result=dict(status='offline_assembly_verified_rollout_blocked',r2='offline package hashes and dry-runs verified; runtime effect unverified',candidate=str(candidate),requested_output='/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate',external_output_written=False,package_manifest_sha256=sha(candidate/'package.json'),file_count=len(m['files']),base_manifest_sha256=inputs['base_manifest_sha256'],assembly_chain=chain,boards=reports,board_operations=0,commit=None,commit_note='git metadata is read-only; outer reviewer commits',changed_package_files=[p for p,h in m['files'].items() if old['files'].get(p)!=h])
    save(HERE/'results.json',result);save(HERE/'candidate-package.json',m)
    print(json.dumps({k:result[k] for k in ['status','package_manifest_sha256','file_count','board_operations']},indent=2))
    print(json.dumps({k:{q:b[q] for q in ['changed_live_paths','changed_components','adds','replaces','recorded_live_conflicts','package_dry_run_passed','executable_incremental_steps']} for k,b in reports.items()},indent=2))
if __name__=='__main__':main()
