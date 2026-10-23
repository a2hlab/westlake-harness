#!/usr/bin/env python3
"""Verify only local source pins and static report boundaries. Never call a service."""
import argparse,copy,hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def require(ok,reason):
    if not ok:raise ValueError(reason)
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def sha(p):return sha_bytes(p.read_bytes())
def roots():
    ws=Path(os.environ.get('WORKSPACES',str(ROOT.parents[2])))
    return {'main':ws/'westlake-harness','workspace':ws,'home':Path.home(),'sdk':Path(os.environ.get('T53_OH_SDK','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony')),'packet':ROOT}
def locate(row):
    p=Path(row['path']);require(not p.is_absolute() and '..' not in p.parts,'unsafe source locator')
    require(row['root'] in roots(),'unknown source root')
    return roots()[row['root']]/p

def validate(path,require_ready=False):
    report=json.loads(path.read_text())
    require(report['schema']==1 and report['task']=='T53','wrong report schema')
    require(report['runtime_capability']=='unknown','runtime capability overclaim')
    require(all(v==0 for v in report['actions'].values()),'action outside static scope')
    refs=report['source_refs'];byid={r['id']:r for r in refs}
    require(len(byid)==len(refs) and len(refs)>0,'duplicate/missing refs')
    for ref in refs:
        b=locate(ref).read_bytes()
        require(sha_bytes(b)==ref['sha256'],'source SHA drift: '+ref['id'])
        require(len(b)==ref['bytes'],'source size drift: '+ref['id'])
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==ref['computed_git_blob'],'blob drift: '+ref['id'])
        lines=b.decode().splitlines();start,end=ref['lines']
        require(1<=start<=end<=len(lines),'source range invalid: '+ref['id'])
        require(sha_bytes('\n'.join(lines[start-1:end]).encode())==ref['excerpt_sha256'],'source excerpt drift: '+ref['id'])
    def linked(ids):
        require(all(id in byid for id in ids),'unknown reference')
    missing={m['id']:m for m in report['missing_parts']}
    require(len(missing)==len(report['missing_parts']),'duplicate gaps')
    for m in missing.values():
        require(m['status'] in ('missing_local_source','unverified_binding') and m['needed'],'gap status missing')
        linked(m['basis_refs']);require(m['basis_refs'],'gap provenance missing')
        if m['local_path']:
            require(m['local_root']=='workspace','wrong gap root')
            require(not (roots()['workspace']/m['local_path']).exists(),'missing source now exists; revise: '+m['id'])
            require(m['observed_exists'] is False,'unobserved absence')
    candidates=report['candidates'];require(1<=len(candidates)<=3,'candidate bound violated')
    for c in candidates:
        require(c['status'] in ('GAP','READY'),'candidate status invalid')
        require(c['runtime_capability']=='unknown','unexecuted runtime marked ready')
        linked(c['source_refs']);require(c['existing_implementation'],'implementation scope absent')
        for side in ('client','server'):
            perm=c['caller_requirements'][side];linked(perm['refs'])
            require(perm['status'] in ('missing','partial','complete'),'permission status invalid')
            if c['status']=='READY':
                require(perm['status']=='complete' and perm['refs'],'permission_evidence_missing: '+c['id']+'/'+side)
                require(any(byid[id]['kind']=='implementation' for id in perm['refs']),'permission implementation absent')
        for name in ('client','server','registration','build'):
            role=c[name];linked(role['refs']);require(role['status'] in ('missing','partial','complete'),'role status invalid')
            if c['status']=='READY':
                require(role['status']=='complete' and role['refs'],'incomplete READY '+name)
                require(any(byid[id]['kind']!='declaration' for id in role['refs']),'declaration-only READY')
        require(all(id in missing for id in c['missing_parts']),'unknown candidate gap')
        if c['status']=='GAP':require(c['missing_parts'],'GAP without explicit missing component')
        else:require(not c['missing_parts'],'READY still has unresolved gaps')
    ready=any(c['status']=='READY' for c in candidates)
    require(report['implementation_ready']==ready and report['status']==('READY' if ready else 'GAP'),'report readiness inconsistent')
    signed=report['signed_host_manifest'];member=locate(byid[signed['source_ref']]).read_bytes()
    for container in signed['containers']:
        p=locate(container);require(sha(p)==container['sha256'],'signed container drift')
        with zipfile.ZipFile(p) as z:payload=z.read(container['member'])
        require(payload==member and sha_bytes(payload)==container['member_sha256'],'signed module drift')
    metadata=json.loads(member);mod=metadata['module']
    require(signed['registered_abilities']==[a['name'] for a in mod['abilities']],'ability registration mismatch')
    require(signed['registered_extension_abilities']==[a['name'] for a in mod.get('extensionAbilities',[])],'extension registration mismatch')
    require(signed['request_permissions']==[p['name'] for p in mod['requestPermissions']],'host permission mismatch')
    observed=report['caller_observation']
    require(observed['status']=='CURRENT_KNOWN_HISTORICAL_SAMPLE_NOT_FRESH' and observed['sample_date']=='2026-10-22','caller sample promoted to fresh authority')
    bm_text=locate(byid[observed['source_ref']]).read_text()
    application=json.JSONDecoder().raw_decode(bm_text[bm_text.index('{'):])[0]['applicationInfo']
    require(observed['fields']=={k:application[k] for k in ('appPrivilegeLevel','isSystemApp','accessTokenId','uid','appProvisionType','permissions')},'actual caller evidence mismatch')
    require(observed['fields']['permissions']==[] and observed['fields']['isSystemApp'] is False,'caller capability drift; re-review required')
    receipt=json.loads(locate(byid['t32-receipt']).read_text())
    require(receipt['members']['module.json']['after_sha256']==sha_bytes(member),'T32 receipt mismatch')
    require(sha(locate(byid['entry']))==sha(locate(byid['vm-entry'])),'entry equality drift')
    require(sha(locate(byid['spawn-client']))==sha(locate(byid['historical-client'])),'client build source mismatch')
    if require_ready:require(ready,'READY_DENIED: missing same-version service/permission/registration binding')
    return {'valid_static_report':True,'status':report['status'],'implementation_ready':ready,'runtime_capability':'unknown','source_refs':len(refs),'candidates':len(candidates),'report_sha256':sha(path)}

def logged(argv,out):
    out.mkdir(parents=True,exist_ok=False)
    (out/'argv.json').write_text(json.dumps(argv)+'\n');(out/'start').write_text(str(time.time())+'\n')
    with (out/'stdout').open('wb') as a,(out/'stderr').open('wb') as b:
        try:rc=subprocess.run(argv,stdout=a,stderr=b,timeout=30).returncode
        except subprocess.TimeoutExpired:rc=124
    (out/'end').write_text(str(time.time())+'\n');(out/'rc').write_text(str(rc)+'\n');return rc

def self_test(out):
    out.mkdir(parents=True,exist_ok=False);source=ROOT/'results.json';before=sha(source)
    original=json.loads(source.read_text());bad=copy.deepcopy(original);bad['source_refs'][0]['sha256']='0'*64
    (out/'bad-sha.json').write_text(json.dumps(bad)+'\n')
    bad=copy.deepcopy(original);bad['status']='READY';bad['implementation_ready']=True;bad['candidates'][0]['status']='READY'
    # Preserve the actual lack of server permission evidence; a READY label must fail.
    bad['candidates'][0]['caller_requirements']['client']={'status':'complete','refs':['entry','signed-module']}
    bad['candidates'][0]['caller_requirements']['server']={'status':'complete','refs':[]}
    (out/'missing-permission.json').write_text(json.dumps(bad)+'\n')
    rows=[]
    for mode,flags in [('normal',[]),('optimized',['-O'])]:
        for case,report,extra,want in [('positive',source,[],None),('bad-sha',out/'bad-sha.json',[],'source SHA drift'),('missing-permission',out/'missing-permission.json',[],'permission_evidence_missing'),('gap-ready',source,['--require-ready'],'READY_DENIED')]:
            dest=out/(mode+'-'+case);argv=[sys.executable,*flags,str(ROOT/'check.py'),'--report',str(report),*extra]
            rc=logged(argv,dest)
            require((rc==0) if want is None else (rc!=0 and want in (dest/'stderr').read_text()),'wrong actual checker outcome: '+mode+'/'+case)
            rows.append({'mode':mode,'case':case,'rc':rc,'raw':{n:{'sha256':sha(dest/n),'size':(dest/n).stat().st_size} for n in ('argv.json','start','end','stdout','stderr','rc')}})
    require(sha(source)==before,'negative checks changed report')
    result={'checker_passed':True,'implementation_ready':False,'runtime_capability':'unknown','positive_valid_gap_reports':2,'negative_ready_refusals':6,'report_sha256':before,'rows':rows}
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'checker_passed':True,'status':'GAP','positives':2,'negatives':6}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=ROOT/'results.json');p.add_argument('--require-ready',action='store_true');p.add_argument('--self-test',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
    if a.self_test:self_test((a.out or ROOT/'.private'/('check-'+str(time.time_ns()))).resolve())
    else:print(json.dumps(validate(a.report,a.require_ready)))
