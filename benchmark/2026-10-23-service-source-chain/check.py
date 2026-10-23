#!/usr/bin/env python3
"""Local static evidence verifier. No service calls; public copies suffice."""
import argparse, copy, hashlib, json, re, subprocess, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
CARD=Path(__file__).resolve().parent
REV='101781d2eb1097eac5ff57d636af9d7127e5c6e8'
MANIFEST='f471153f4144f82dc35dd3cb1fe0a842937e4301733b6563e3df8f30c07d0e48'
def require(ok,reason):
    if not ok: raise ValueError(reason)
def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(path): return sha(path.read_bytes())
def local(path):
    p=Path(path);require(not p.is_absolute() and '..' not in p.parts,'unsafe reference')
    dest=CARD/p;require(not dest.is_symlink() and dest.is_file(),'missing/non-regular reference '+path)
    return dest

def validate(path):
    r=json.loads(path.read_text());require(r['schema']==1 and r['task']=='T54','schema mismatch')
    refs=r['source_refs'];ids={s['id'] for s in refs};require(len(ids)==len(refs)==34,'source subset incomplete')
    for s in refs:
        b=local(s['path']).read_bytes();require(sha(b)==s['sha256'] and len(b)==s['bytes'],'SOURCE_SHA_DRIFT: '+s['id'])
        require(hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==s['git_blob'],'blob mismatch')
        expected_rev='ef924ea4198befa65a088863d9812b7f872e4bbc' if s['id'].startswith('bms-') and s['path'].startswith('sources/bundle_framework/') else REV
        require(s['revision']==expected_rev,'wrong source lineage')
        require(s['local_patch_member']==(s['id'] in ('bms-installer','bms-build')),'wrong local patch attribution')
        lines=b.decode().splitlines()
        for span in s['ranges']:
            lo,hi=span['lines'];require(1<=lo<=hi<=len(lines),'bad source range')
            require(sha('\n'.join(lines[lo-1:hi]).encode())==span['sha256'],'excerpt drift')
    v=r['version'];manifest=local('provenance/05-exact-manifest.xml').read_bytes()
    require(sha(manifest)==MANIFEST,'manifest drift')
    projects={x.get('name'):dict(x.attrib) for x in ET.fromstring(manifest).findall('project')}
    require(v['component']==projects['ability_ability_runtime'] and v['head']==REV,'wrong revision')
    for f in ('05-exact-manifest.xml','03-source-metadata.stdout','06-local-changes.patch'):
        b=local('provenance/'+f).read_bytes();require(sha(b)==v['intake_pins'][f]['sha256'],'provenance drift '+f)
    require(v['metadata_head_agrees'] and REV in local('provenance/03-source-metadata.stdout').read_text(),'HEAD not recorded')
    require(not v['reviewed_sources_in_patch'] and v['selected_files_checked']==26,'patch coverage mismatch')
    require(v['board_bytes_bound'] is False and v['board_binding_evidence']==[], 'BOARD_BINDING_GAP: source revision is not deployed byte proof')
    for m in r['missing_parts']:
        require(set(m['refs'])<=ids and m['refs'],'unbound gap')
        if 'component' in m:require(m['component']==projects[m['component']['name']],'dependency revision drift')
    bms=r['bms_review'];peer_data=local(bms['peer_path']).read_bytes()
    require(sha(peer_data)==bms['peer_sha256']=='fae9099aa5e34b5cdec4812a8bde677678839c2d2fd02ce38f387ada879247c3','BMS peer drift')
    peer=json.loads(peer_data)
    require(bms['component']==projects['bundlemanager_bundle_framework'] and bms['recorded_head']==bms['component']['revision'],'BMS revision mismatch')
    for f in ('07-bms-metadata','09-bms-changes.patch'):
        require(file_sha(local('provenance/'+f))==bms['input_pins'][f],'BMS lineage drift')
    patch=local('provenance/09-bms-changes.patch').read_text()
    modified=re.findall(r'^diff --git a/(\S+) b/\S+',patch,re.M)
    require(modified==bms['modified_files']==peer['provenance']['patch_changed_files'] and len(modified)==14,'BMS patch scope changed')
    require(bms['selected_modified_refs']==['bms-installer','bms-build'],'modified evidence hidden')
    for id,item in peer['source_evidence'].items():
        ref=next(x for x in refs if x['id']=='bms-'+id)
        require(ref['sha256']==item['sha256'] and ref['source_index_match'] is True,'BMS selected evidence drift')
        require(ref['local_patch_member']==(ref['upstream_path'] in modified),'BMS patch mismatch')
    require(bms['effective_build_arg']=='unknown' and bms['target_effective_privilege_capability']=='unknown' and bms['complete_registration_eligibility']=='unknown','REGISTRATION_GAP: actual config/profile unbound')
    require(bms['findings']==peer['findings'],'BMS qualification changed')
    cap=r['capability']
    require(cap['caller']=='conditional_source_path','caller admission overclaim')
    require(cap['target_registration']=='unknown' and cap['target_runtime_eligibility']=='unknown','REGISTRATION_GAP: no bound BMS conclusion')
    require(cap['bridge_endpoint']=='unknown' and cap['bridge_endpoint_found'] is False,'BRIDGE_GAP: generic transport is not endpoint')
    require(cap['permission_sufficiency']=='unknown' and not r['implementation_ready'] and r['status']=='GAP','PERMISSION_GAP: not READY')
    require(r['runtime_verified'] is False,'unexecuted runtime overclaim')
    paths=r['paths'];require(len(paths)==2,'path bound')
    require(paths[0]['system_app_direct_rejection'] is False and paths[0]['status']=='CONDITIONAL_SOURCE_PATH','ordinary route conclusion changed')
    require(paths[1]['status']=='REJECTED_STOPPED' and paths[1]['js_error']==202,'account rejection lost')
    for p in paths:require(set(p.get('chain',p.get('refs',[])))<=ids,'unbound path')
    for a in r['admission']:require(set(a['refs'])<=ids and a['refs'],'unbound admission')
    signed=r['t53']['signed_manifest'];b=local(signed['path']).read_bytes();require(sha(b)==signed['sha256']=='0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51','signed host member drift')
    require(json.loads(b)['module'].get('extensionAbilities',[])==signed['extension_abilities']==[],'existing host gained extension')
    require(r['t53']['historical_caller_source']['sha256']=='0f1f1e67e94be91a188652bb438e87232d40dfd0a936c16d58086880c5bc245b','historical caller source pin drift')
    obs=r['t53']['caller_observation'];require(obs['status']=='CURRENT_KNOWN_HISTORICAL_SAMPLE_NOT_FRESH' and obs['sample_date']=='2026-10-22','historical caller promoted')
    require(obs['fields']['permissions']==[] and obs['fields']['isSystemApp'] is False,'caller permission claim changed')
    return {'static_report_valid':True,'status':'GAP','source_files':len(refs),'runtime_verified':False,'report_sha256':file_sha(path)}

def logged(argv,out):
    out.mkdir(parents=True,exist_ok=False)
    (out/'argv.json').write_text(json.dumps(argv)+'\n');(out/'start').write_text(str(time.time())+'\n')
    with (out/'stdout').open('wb') as a,(out/'stderr').open('wb') as b:
        try: rc=subprocess.run(argv,stdout=a,stderr=b,timeout=30).returncode
        except subprocess.TimeoutExpired: rc=124
    (out/'end').write_text(str(time.time())+'\n');(out/'rc').write_text(str(rc)+'\n')
    return rc

def self_test(out):
    out.mkdir(parents=True,exist_ok=False);original=CARD/'results.json';pin=file_sha(original);base=json.loads(original.read_text())
    mutations=[]
    bad=copy.deepcopy(base);bad['source_refs'][0]['sha256']='0'*64;mutations.append(('source-sha',bad,'SOURCE_SHA_DRIFT'))
    bad=copy.deepcopy(base);bad['version']['board_bytes_bound']=True;mutations.append(('version-ready',bad,'BOARD_BINDING_GAP'))
    bad=copy.deepcopy(base);bad['status']='READY';bad['implementation_ready']=True;bad['capability']['permission_sufficiency']='complete';mutations.append(('permission-ready',bad,'PERMISSION_GAP'))
    cases=[('positive',original,None)]
    for name,bad,reason in mutations:
        p=out/(name+'.json');p.write_text(json.dumps(bad)+'\n');cases.append((name,p,reason))
    rows=[]
    for mode,flags in [('normal',[]),('optimized',['-O'])]:
        for name,report,reason in cases:
            dest=out/(mode+'-'+name);rc=logged([sys.executable,*flags,str(CARD/'check.py'),'--report',str(report)],dest)
            require((rc==0) if reason is None else (rc!=0 and reason in (dest/'stderr').read_text()),'wrong actual checker result '+mode+'/'+name)
            rows.append({'mode':mode,'case':name,'rc':rc,'expected_reason':reason,'raw':{f:{'sha256':file_sha(dest/f),'bytes':(dest/f).stat().st_size} for f in ('argv.json','start','end','stdout','stderr','rc')}})
    require(pin==file_sha(original),'negative checks changed report')
    result={'static_checker_passed':True,'status':'GAP','positive_reports':2,'negative_rejections':6,'report_sha256':pin,'checker_sha256':file_sha(CARD/'check.py'),'scope':'Public source/report integrity checks only. No production C++ executed and no service requests.','rows':rows}
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,default=CARD/'results.json');ap.add_argument('--self-test',action='store_true');ap.add_argument('--out',type=Path);args=ap.parse_args()
    try:
        if args.self_test:
            require(args.out is not None,'--out required');self_test(args.out)
        else: print(json.dumps(validate(args.report)))
    except (ValueError,KeyError,TypeError,OSError) as e:
        print('REFUSED: '+str(e),file=sys.stderr);sys.exit(1)
