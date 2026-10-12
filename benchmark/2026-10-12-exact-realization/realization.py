#!/usr/bin/env python3
"""Offline exact realization over the immutable reviewed v6 restoration recipe.

No device transport lives here. A candidate fingerprint is never a demo seal.
Placement uses audited WID=0; only independent running observation derives WID.
"""
import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile

HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
SHA=re.compile(r'[0-9a-f]{64}\Z')
PROVIDER_SHA='340adc46c2b05efb1ffcaadf9938b2a1c4dad7979d8f49132c726408a97d846e'
BINDING_SHA='ee8e74ef3982c25d21c3cf3adee5fccb9ee784d3c06aeefa12ad63a1cbfdef95'
MANIFEST_SHA='f2d0ae4776be5d07f1145104908594eadce70c4b6aa93cbb21b302f187ddeaad'
EXECUTOR_SHA='496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d'
DECLARATION={'baseline':319,'controls':24,'runtime':460,'stage':3}

def need(ok,why):
    if not ok:raise ValueError(why)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bytes_sha(b):return hashlib.sha256(b).hexdigest()
def read(p):
    def unique(pairs):
        result={}
        for k,v in pairs:
            need(k not in result,'duplicate JSON field: '+k);result[k]=v
        return result
    return json.loads(Path(p).read_text(),object_pairs_hook=unique)
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def resolve(s,base):
    need(isinstance(s,str) and s,'missing path')
    if s.startswith('$WORKSPACES/'):return WS/s[len('$WORKSPACES/'):]
    p=Path(s);return p if p.is_absolute() else Path(base)/p
def pin(ref,base):
    need(isinstance(ref,dict) and SHA.fullmatch(str(ref.get('sha256',''))),'typed SHA pin missing')
    p=resolve(ref.get('path'),base)
    need(p.is_file() and not p.is_symlink() and digest(p)==ref['sha256'],'missing/drifted input: '+str(p))
    return p.resolve()
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def helper_pins():
    return {name:digest(HERE/name) for name in ('observations.py','seal_checks.py','sameboard.py')}

def source_identity(ref,base):
    path=pin(ref,base);obj=read(path)
    need(ref.get('kind') in {'candidate-fingerprint','seal'},'source identity kind')
    if ref['kind']=='candidate-fingerprint':
        need(obj.get('schema')=='exact-source-fingerprint/v1' and obj.get('status')=='candidate/not_sealed','candidate must remain explicitly not_sealed')
        need(obj.get('declaration')==DECLARATION,'complete source declaration required')
        rows=obj.get('files');need(isinstance(rows,list) and rows,'source files missing')
        targets={}
        counts={k:0 for k in DECLARATION}
        for row in rows:
            t=row.get('target');need(isinstance(t,str) and t.startswith('/') and '..' not in t.split('/'),'source target path')
            need(t not in targets and SHA.fullmatch(str(row.get('sha256',''))),'duplicate/invalid source target: '+t)
            groups=row.get('groups');need(isinstance(groups,list) and groups and len(groups)==len(set(groups)) and set(groups)<=set(counts),'source groups: '+t)
            for g in groups:counts[g]+=1
            provenance=row.get('provenance',{});need(provenance.get('kind') in {'measured','reviewed-template'},'source provenance: '+t)
            pin(provenance.get('evidence'),path.parent)
            if 'source' in row:need(digest(pin(row['source'],path.parent))==row['sha256'],'source content pin: '+t)
            targets[t]=row
        need(counts==DECLARATION,'source declaration/count mismatch')
    else:
        import seal_checks
        seal_checks.validate_seal(obj)
        groups=obj.get('files');need(isinstance(groups,dict) and groups,'seal files missing')
        targets={}
        for entries in groups.values():
            for t,h in entries.items():
                need(isinstance(t,str) and t.startswith('/') and '..' not in t.split('/') and re.fullmatch(r'/[A-Za-z0-9_./:+@-]+',t),'unsafe seal target')
                need(SHA.fullmatch(str(h)),'seal member SHA')
                need(t not in targets or targets[t]['sha256']==h,'conflicting seal file')
                targets[t]={'target':t,'sha256':h}
    return path,obj,targets

def exact_numeric(raw,pattern,value,label):
    matches=list(re.finditer(pattern,raw,re.M));need(len(matches)==1,label+' must have exactly one known assignment')
    m=matches[0];a,z=m.span(1);old=raw[a:z];new=str(value).encode()
    return raw[:a]+new+raw[z:],{'parameter':label,'offset':a,'old_hex':old.hex(),'new_hex':new.hex()}

def render_runtime(raw,name,uid,gid,wid):
    edits=[];data=raw
    if name=='run.sh':
        data,e=exact_numeric(data,rb'^export ASX_RUNTIME_OWNER_UID=([0-9]+)$',uid,'host_uid');edits.append(e)
        data,e=exact_numeric(data,rb'^export WL_PARENT_ID=([0-9]+)$',wid,'window_id');edits.append(e)
    elif name=='prepare_jit50.sh':
        data,e=exact_numeric(data,rb'^app_uid=([0-9]+)$',uid,'host_uid');edits.append(e)
    elif name=='preseed_metasec48.sh':
        data,e=exact_numeric(data,rb'^APP_UID48="\$\{3:-([0-9]+)\}"$',uid,'host_uid');edits.append(e)
    elif name=='request.bin':
        need(len(data)==672,'request.bin must have 672 bytes')
        buf=bytearray(data)
        for pos,n,label in [(312,uid,'host_uid'),(316,gid,'host_gid')]:
            old=bytes(buf[pos:pos+4]);new=struct.pack('<I',n);buf[pos:pos+4]=new
            edits.append({'parameter':label,'offset':pos,'old_hex':old.hex(),'new_hex':new.hex(),'encoding':'uint32-le'})
        data=bytes(buf)
    return data,edits

def spans(a,b):
    # This records the already-reviewed v6 recipe, not a permissive patch input.
    return [{'source_start':i,'source_end':j,'target_start':k,'target_end':l,
             'old_hex':a[i:j].hex(),'new_hex':b[k:l].hex()}
            for op,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if op!='equal']

def upstream(p,b,base):
    """Exact source objects consumed by the fixed v6 recipe (no new discovery)."""
    result={}
    cp=p.pin(b['composition_update']['plan'],base);cr=cp.parent
    for row in read(cp)['members']:
        src=cr/row['source'].removeprefix('$PACKAGE/')
        need(digest(src)==row['sha256'],'composed source drift '+row['target'])
        result[row['target']]=(src,'controls')
    for row in read(p.pin(b['runtime_archive'],base))['files']:
        result[row['target']]=(p.pin({'path':row['source'],'sha256':row['sha256']},base),'runtime')
    for row in b['extra_runtime_files']:
        result[row['target']]=(p.pin(row['source'],base),'runtime')
    for row in b['stage_files']:
        result[row['target']]=(p.pin(row['source'],base),'stage')
    # Original archive scripts are templates with a different historical UID.
    # The independently captured current61b scripts bind the source fingerprint.
    for row in read(p.pin(b['observation_provenance']['live_scripts'],base))['files']:
        need(row['target'] in result and Path(row['target']).name in {'run.sh','prepare_jit50.sh','preseed_metasec48.sh'},'unexpected live script')
        result[row['target']]=(p.pin({'path':row['source'],'sha256':row['sha256']},base),'runtime')
    need(len(result)==487,'upstream route target set incomplete')
    return result

def identity_boot(identity):
    top=identity.get('boot_id');captured=identity.get('provenance',{}).get('capture_boot_id')
    need(not(top and captured) or top==captured,'conflicting source boot identity')
    return top or captured

def validate_source_rows(request,base,identity_path,identity,rows,original_sources):
    """Allow exactly one observed source WID variation; all other bytes stay exact."""
    import observations
    sources=dict(original_sources);receipt=[]
    for target,(src,group) in original_sources.items():
        need(target in rows,'source fingerprint missing route target: '+target)
        row=rows[target]
        if 'groups' in row:need(group in row['groups'],'source role mismatch: '+target)
        if row['sha256']==digest(src):continue
        need(Path(target).name=='run.sh' and group=='runtime','source snapshot/template differs: '+target)
        source_ref=request.get('source_files',{}).get(target,row.get('source'))
        actual=pin(source_ref,base if target in request.get('source_files',{}) else identity_path.parent)
        need(digest(actual)==row['sha256'],'source run.sh bytes differ from identity')
        ref=request.get('source_parameter_evidence');obs_path=pin(ref,base);claimed=read(obs_path)
        expected={'serial':identity['serial'],'boot_id':identity_boot(identity),
                  'host_uid':20011206,'host_gid':20011206,
                  'control_root':'/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview',
                  'window_id':claimed.get('window_id')}
        validated=observations.validate(ref,base,expected,'running')
        raw=src.read_bytes();live=actual.read_bytes()
        rendered,edit=exact_numeric(raw,rb'^export WL_PARENT_ID=([0-9]+)$',validated['window_id'],'window_id')
        # A second assignment is always rejected, including a byte-identical value.
        exact_numeric(live,rb'^export WL_PARENT_ID=([0-9]+)$',validated['window_id'],'window_id')
        need(rendered==live,'source run.sh differs beyond independently observed single WID: '+target)
        sources[target]=(actual,group)
        receipt.append({'target':target,'template_sha256':digest(src),'source_snapshot_sha256':digest(actual),
                        'source_boot_id':identity_boot(identity),'parameter_evidence':validated,'edit':edit})
    return sources,receipt


def compile_request(request_path,out):
    import observations
    request_path=Path(request_path).resolve();base=request_path.parent;r=read(request_path)
    need(r.get('schema')=='exact-realization-request/v1' and r.get('phase') in {'placement','running'},'placement/running request required')
    need(r.get('execution_enabled') is False,'compiler cannot enable execution')
    approval=read(pin(r['user_approval'],base))
    need(approval.get('status')=='APPROVED' and approval.get('approved_by')=='user','user approval absent')
    v=r['v6'];provider=pin(v['provider'],base);binding_path=pin(v['binding'],base);manifest_path=pin(v['manifest'],base)
    need(digest(provider)==PROVIDER_SHA and digest(binding_path)==BINDING_SHA and digest(manifest_path)==MANIFEST_SHA,'unreviewed v6 baseline')
    p=load(provider,'exact_frozen_v6');b=read(binding_path);params=r['parameters']
    if r['phase']=='running':
        import sameboard
        identity_path,identity,source_rows=source_identity(r['source_identity'],base)
        need(params.get('serial')==identity.get('serial')==p.OLD_SERIAL,'same-board original61b identity required')
        seal_ref=r.get('source_seal')
        if r['source_identity']['kind']=='seal':need(seal_ref=={k:v for k,v in r['source_identity'].items() if k!='kind'},'original seal separately pinned')
        else:need(seal_ref is None,'candidate cannot masquerade as a seal')
        original_sources,normalization=validate_source_rows(r,base,identity_path,identity,source_rows,upstream(p,b,binding_path.parent))
        observation=observations.validate(r['parameter_evidence'],base,params,'running')
        proof=sameboard.compile_sameboard(request_path,out,identity_path,identity,source_rows,observation)
        proof['helper_program_sha256']=helper_pins()
        proof['source_window_normalization']=normalization
        write(Path(out)/'realization.json',proof);return proof
    for name,key in [('serial','serial'),('host_uid','host_uid'),('control_root','attempt_root')]:
        need(params.get(name)==b[key],'parameter differs from captured v6 binding: '+name)
    need(params.get('boot_id')==b['boot_id'],'placement boot differs from actual preimage binding')
    need(params.get('host_gid')==params['host_uid'],'v6 requires independently proved GID==UID')
    need(params.get('window_id') is None,'placement WID must be null; audited template is zero')
    observation=observations.validate(r['parameter_evidence'],base,params,'placement')
    identity_path,identity,source_rows=source_identity(r['source_identity'],base)
    need(identity.get('serial')==p.OLD_SERIAL,'source identity is not original61b')
    seal_ref=r.get('source_seal')
    if r['source_identity']['kind']=='seal':need(seal_ref=={k:v for k,v in r['source_identity'].items() if k!='kind'},'original seal must be separately pinned')
    if seal_ref:
        original=pin(seal_ref,base);need(read(original).get('schema')=='demo-seal/v1','source seal schema')
        need(r['source_identity']['kind']=='seal' and digest(original)==digest(identity_path),'seal/fingerprint ambiguity')
    original_sources,normalization=validate_source_rows(r,base,identity_path,identity,source_rows,upstream(p,b,binding_path.parent))
    out=Path(out).resolve();need(not out.exists(),'fresh realization output required')
    # Validate and rebuild in temporary storage. A rejection never leaves a
    # partially trusted public package/authorization behind.
    with tempfile.TemporaryDirectory(prefix='exact-v6-') as td:
        package=Path(td)/'package';p.compile_package(binding_path,package)
        need(digest(package/'manifest.json')==MANIFEST_SHA,'v6 reconstruction differs from immutable baseline')
        plan=read(package/'plan.json');need(len(plan['members'])==487,'route package incomplete')
        need(digest(package/'executor.py')==EXECUTOR_SHA,'executor drift')
        files=[];mapped=set()
        for m in plan['members']:
            target=m['target'];origin=target.replace(b['attempt_root'],p.OLD_ROOT,1)
            src,role=original_sources[origin];raw=src.read_bytes();rendered=(package/m['source'].removeprefix('$PACKAGE/')).read_bytes()
            basename=Path(origin).name
            if role in {'runtime','stage'}:
                expected,edits=render_runtime(raw,basename,params['host_uid'],params['host_gid'],0)
                need(expected==rendered,'unapproved bytes beyond runtime parameters: '+target)
                inheritance=[]
            else:
                # Fixed v6 includes reviewed target-preimage guards and disabled
                # startup policy. These are not new whitelist parameter edits.
                # Reproduction against the hard-pinned manifest is mandatory.
                edits=[];inheritance=spans(raw,rendered) if raw!=rendered else []
            files.append({'target':target,'source_target':origin,'source_snapshot_sha256':source_rows[origin]['sha256'],
                'template_sha256':digest(src),'reviewed_v6_template_sha256':bytes_sha(rendered),
                'generator_sha256':digest(HERE/'realization.py'),'v6_generator_sha256':PROVIDER_SHA,
                'source_identity_sha256':digest(identity_path),'source_seal_sha256':seal_ref['sha256'] if seal_ref else None,
                'sha256':bytes_sha(rendered),'source':m['source'],'parameters':params,'parameter_evidence_sha256':r['parameter_evidence']['sha256'],
                'edits':edits,'inherited_v6_recipe_spans':inheritance,'before':m['before'],'after':m['after']})
            mapped.add(origin)
        # The complete candidate baseline remains exact, never wildcard-excluded.
        for target,row in source_rows.items():
            if target not in mapped:
                files.append({'target':target,'source_target':target,'template_sha256':row['sha256'],'sha256':row['sha256'],
                    'generator_sha256':digest(HERE/'realization.py'),'source_identity_sha256':digest(identity_path),
                    'source_seal_sha256':seal_ref['sha256'] if seal_ref else None,'edits':[],'inherited_v6_recipe_spans':[]})
        need(len({x['target'] for x in files})==len(files),'target projection collides')
        proof={'schema':'exact-realization/v1','status':'candidate/not_sealed','phase':'placement','execution_enabled':False,
            'request':{'path':str(request_path),'sha256':digest(request_path)},'source_identity':r['source_identity'],'source_seal':seal_ref,
            'generator':{'path':str(HERE/'realization.py'),'sha256':digest(HERE/'realization.py')},
            'observation_validator':{'path':str(HERE/'observations.py'),'sha256':digest(HERE/'observations.py')},
            'parameters':params,'parameter_evidence':observation,'v6':v,'plan_sha256':digest(package/'plan.json'),
            'executor_sha256':EXECUTOR_SHA,'prepared_manifest_sha256':MANIFEST_SHA,'files':sorted(files,key=lambda x:x['target']),
            'helper_program_sha256':helper_pins(),'source_window_normalization':normalization,'route_targets':487,'template_window_id':0,'dynamic_field':'run.sh:single export WL_PARENT_ID',
            'signature':None,'device_calls':0,'inherited_baseline_note':'v6 reviewed target-preimage/disabled-startup recipe is retained, not added to the parameter whitelist'}
        out.mkdir(parents=True);shutil.copytree(package,out/'package')
        write(out/'realization.json',proof)
    return proof

def verify(path):
    path=Path(path).resolve();proof=read(path)
    need(proof.get('schema')=='exact-realization/v1' and proof.get('status')=='candidate/not_sealed','realization schema/status')
    need(digest(pin(proof['generator'],path.parent))==digest(HERE/'realization.py'),'generator self pin')
    need(proof.get('helper_program_sha256')==helper_pins(),'common helper program drift')
    pin(proof['observation_validator'],path.parent)
    if proof.get('purpose')=='same-board-selfcheck':
        need(digest(pin(proof['sameboard_generator'],path.parent))==digest(HERE/'sameboard.py'),'sameboard generator drift')
    req=pin(proof['request'],path.parent)
    with tempfile.TemporaryDirectory(prefix='exact-reverify-') as td:
        expected=compile_request(req,Path(td)/'replayed')
        need(expected==proof,'realization proof differs from exact regeneration')
    package=path.parent/'package';manifest=read(package/'manifest.json')
    need(digest(package/'manifest.json')==proof['prepared_manifest_sha256'],'prepared manifest SHA')
    for row in manifest['files']:
        f=package/row['path'];need(f.is_file() and digest(f)==row['sha256'] and f.stat().st_size==row['bytes'],'prepared file drift: '+row['path'])
    proof=copy.deepcopy(proof);proof['package']=package;proof['proof_path']=path;proof['proof_sha256']=digest(path)
    return proof

def running_files(proof,observation_ref,base,current_boot):
    import observations
    params=copy.deepcopy(proof['parameters']);params['boot_id']=current_boot
    params['window_id']=read(pin(observation_ref,base)).get('window_id')
    obs=observations.validate(observation_ref,base,params,'running')
    rows=[r for r in proof['files'] if r.get('source')=='$PACKAGE/runtime/run.sh'];need(len(rows)==1,'unique run.sh target required')
    row=rows[0];raw=(proof['package']/'runtime/run.sh').read_bytes()
    need(bytes_sha(raw)==row['sha256'],'run.sh template drift')
    data,edit=exact_numeric(raw,rb'^export WL_PARENT_ID=([0-9]+)$',obs['window_id'],'window_id')
    files={x['target']:x['sha256'] for x in proof['files']};files[row['target']]=bytes_sha(data)
    return files,{'schema':'exact-running-realization/v1','placement_proof_sha256':proof['proof_sha256'],
        'source_identity':proof['source_identity'],'source_seal':proof['source_seal'],'current_boot':current_boot,
        'parameter_evidence':obs,'target':row['target'],'template_sha256':bytes_sha(raw),'edits':[edit],
        'sha256':bytes_sha(data),'generator_sha256':digest(HERE/'realization.py'),'device_write_operations':0}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='action',required=True)
    c=sub.add_parser('compile');c.add_argument('--request',required=True,type=Path);c.add_argument('--out',required=True,type=Path)
    c=sub.add_parser('verify');c.add_argument('--realization',required=True,type=Path)
    c=sub.add_parser('window');c.add_argument('--realization',required=True,type=Path);c.add_argument('--observation',required=True,type=Path);c.add_argument('--observation-sha256',required=True);c.add_argument('--boot-id',required=True);c.add_argument('--out',required=True,type=Path)
    a=ap.parse_args(argv)
    try:
        if a.action=='compile':r=compile_request(a.request,a.out);result={'status':r['status'],'realization_sha256':digest(a.out/'realization.json'),'device_calls':0}
        elif a.action=='window':
            proof=verify(a.realization);need(not a.out.exists(),'fresh window output required')
            files,receipt=running_files(proof,{'path':str(a.observation),'sha256':a.observation_sha256},Path.cwd(),a.boot_id)
            raw=(proof['package']/'runtime/run.sh').read_bytes()
            data,_=exact_numeric(raw,rb'^export WL_PARENT_ID=([0-9]+)$',receipt['parameter_evidence']['window_id'],'window_id')
            need(bytes_sha(data)==receipt['sha256'],'window derivation differs')
            a.out.mkdir(parents=True);(a.out/'run.sh').write_bytes(data)
            receipt['files']=files;receipt['status']='DERIVED_NOT_DEPLOYED';write(a.out/'receipt.json',receipt)
            result={'status':receipt['status'],'run_sha256':receipt['sha256'],'device_calls':0}
        else:r=verify(a.realization);result={'status':'EXACT_OFFLINE_MATCH','realization_sha256':r['proof_sha256'],'device_calls':0}
        print(json.dumps(result));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('REJECT '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
