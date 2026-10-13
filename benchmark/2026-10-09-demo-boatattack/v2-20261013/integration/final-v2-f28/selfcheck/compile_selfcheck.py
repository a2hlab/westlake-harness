#!/usr/bin/env python3
"""One exact planned union and a readonly composition over admitted original R5 inputs.
Never produces observed evidence, execution authority or a signed seal.
"""
import argparse,copy,hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file()).parent)))
V1='7f5b6f996482149ffd958bcdf55981cdc8ac6e69cb17738a2984153421f72780'
FREEZES={'61b0657200000000000000000324012c':'b7c8fe89cd804e4d9c4844704494e374b381030f4fc7b75db9929ffc2a4a8058','5cd1e3dd00000000000000000923012c':'ffa63e4348c4ce15144ea5c8913899b7bfab2332e11469d7db2a86aae501e64d'}
APK='/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk'
APK_SHA='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
R5_BINARY_SHA='64421012ff2bc905970a5d2d0dd72073755b81b6f42f8c182680fc91ef95ef34'
R3_SHA='2537f4422f544b2831388a95968336e933cd00ecd706951deb849cb3b1740b6c'
META=('mode','uid','gid','label')
def need(ok,why):
    if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def path(text,base):
    p=Path(str(text).replace('$WORKSPACES',str(WS)));return p if p.is_absolute() else Path(base)/p
def pin(ref,base):
    need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'typed independent pin required')
    p=path(ref['path'],base).resolve();need(p.is_file() and sha(p)==ref['sha256'],'pin drift: '+str(ref['path']));return p
def pinned(p):
    p=Path(p).resolve();return {'path':'$WORKSPACES/'+str(p.relative_to(WS)) if p.is_relative_to(WS) else str(p),'sha256':sha(p)}
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def dependencies():
    refs=read(HERE/'source-pins.json');need(refs['r5_binary']['sha256']==R5_BINARY_SHA and refs['r3_checker']['sha256']==R3_SHA,'frozen R5/R3 program identities');binary=load(pin(refs['r5_binary'],HERE),'boat_final_r5_binary')
    r3=binary.load_pinned(pin(refs['r3_checker'],HERE),'boat_final_r3_checker',R3_SHA)
    return binary,r3

def inputs(request_path):
    request_path=Path(request_path).resolve();base=request_path.parent;q=read(request_path)
    need(q['schema']=='boat-v2-final-selfcheck-request/v1' and q['execution_enabled'] is False and q.get('signed_by') is None,'disabled unsigned request required')
    serial=q['serial'];need(serial in FREEZES,'board scope')
    sealpath=pin(q['v1_seal'],base);need(q['v1_seal']['sha256']==V1,'original v1 seal pin');seal=read(sealpath)
    freeze=pin(q['provider_freeze'],base);need(q['provider_freeze']['sha256']==FREEZES[serial],'reviewed board-specific provider freeze')
    rows=read(freeze)['files'];programs={}
    for name,ref in q['programs'].items():
        program=pin(ref,base);need(any(x['sha256']==sha(program) and Path(x['path']).name==program.name for x in rows),'program not in provider freeze: '+name);programs[name]=program
    need(set(programs)=={'executor','contract','identity'},'exact provider program roles')
    planpath=pin(q['placement_plan'],base);plan=read(planpath)
    need(plan['serial']==serial and plan.get('synthetic',False) is False,'actual same-board postinstall plan required')
    need(plan['candidate_contract']['sha256']==sha(programs['contract']) and plan['boat_identity_program']['sha256']==sha(programs['identity']) and plan['installer_sha256']==sha(programs['executor']),'provider typed helper pins')
    executor=load(programs['executor'],'boat_final_exact_executor');executor.validate(plan,executor.core_for(plan))
    binary,r3=dependencies();b=q['base'];checked=read(pin(b['selfcheck'],base))
    need(checked['serial']==serial and checked['mode']=='live-readonly' and checked['status']=='PASS' and checked['passed'] is True and checked.get('synthetic') is False,'actual original R5 source')
    proofpath=pin(b['realization'],base)
    if serial.startswith('5cd'):
        need(b['kind']=='activation','5cd activation history required')
        binding=pin(b['activation_binding'],base)
        need(checked['activation']['binding']['sha256']==sha(binding),'actual source activation pin')
        proof,history=r3.admit(binding,sha(binding),True)
        need(sha(proofpath)==history['realization']['sha256'],'actual activated source realization')
    else:
        need(b['kind']=='realization','61b running source required')
        proof=binary.original.realization.verify(proofpath);history=None
        need(checked['realization']['sha256']==sha(proofpath),'actual source realization pin')
    need(proof['parameters']['serial']==serial,'source proof serial')
    # These raw bookended observations are admitted by the unchanged original validators.
    observed=pin(b['observation'],base)
    actual=binary.original.compare(proof,read(observed),observed.parent,serial,checked['current_boot'],True)
    need(actual['passed'] is True and actual['checks']==checked['checks'],'original source R5 raw comparison differs')
    expected={x['target']:x['actual'] for x in checked['checks']}
    need(len(expected)==len(checked['checks'])==940,'complete original940 source')
    need(plan['boot_id']==checked['current_boot'],'postinstall plan/source running boot differ')
    for row in plan['preserved']: # Boat APK/private before-images are independently checked by provider.
        if row['target'] in expected:need(row['before']['sha256']==expected[row['target']],'source vs actual plan preimage drift')
    if q.get('running_parameter_evidence') is not None:
        pin(q['running_parameter_evidence'],base)
        files,dynamic=binary.original.realization.running_files(proof,q['running_parameter_evidence'],base,q['current_boot'])
        need(dynamic['target'] in expected,'dynamic field must already exist')
        expected[dynamic['target']]=files[dynamic['target']]
        proof['v2_parameter_derivation']=dynamic
    return q,plan,seal,proof,expected,binary,history

def compose(q,plan,seal,proof,original,binary):
    """Deterministic content union; callers must admit all inputs first."""
    boat={r['target']:r['sha256'] for r in plan['members']+plan['binds']}
    need(len(plan['members'])==11 and len(plan['binds'])==7 and len(boat)==18,'exact Boat18')
    need(APK not in original and len(original)==940,'original940 excludes Boat')
    expected=dict(original);expected.update(boat);expected[APK]=APK_SHA
    need(len(expected)==954,'mechanical full954 union')
    for t,h in original.items():need(expected[t]==boat.get(t,h),'unapproved old target change')
    planned={'status':'EXPECTED_UNION_NOT_OBSERVED','signed':False,'serial':q['serial'],'inputs':{'v1_seal':q['v1_seal']['sha256'],'plan':q['placement_plan']['sha256']},'base':q['base'],'boat_uid':plan['boat_uid'],'all_expected_sha256':dict(sorted(expected.items())),'unique_objects':len(expected),'parameter_policy':'sameboot independent host/WMS; only original running_files single WL_PARENT_ID derivation; no unknown SHA exemption'}
    if 'v2_parameter_derivation' in proof:planned['parameter_derivation']=proof['v2_parameter_derivation']
    # Project the original groups using the admitted original realization, retaining all nonfile requirements.
    projection={r['source_target']:r['target'] for r in proof['files']}
    candidate=copy.deepcopy(seal);candidate.update(serial=q['serial'],seal_stage='v2',status='candidate/not_sealed',signed_by=None,signature=None)
    groups={g:{projection.get(t,t):original[projection.get(t,t)] for t in entries} for g,entries in seal['files'].items()}
    for target,h in boat.items():
        for group in groups.values():
            if target in group:group[target]=h
        groups['overlays'][target]=h
    candidate['files']=groups
    candidate['packages'].append({'package':'com.Unity3d.BoatAttackDay','version_code':1,'version_name':'0.9','apk_path':APK,'apk_sha256':APK_SHA})
    req=binary.original.seal_checks.requirements(proof);candidate['inventories']=req['inventories']
    candidate['provenance']={'status':'PLANNED_NOT_OBSERVED_NOT_SIGNED','v1_seal':q['v1_seal'],'base':q['base'],'actual_postinstall_plan':q['placement_plan'],'live_verification':'PENDING_FULL_V2_R5','remote_write_operations':0}
    candidate.pop('fingerprints',None) # A new observed runtime fingerprint must come from actual collection.
    for overlay in candidate['overlay_deployments']:
        if overlay['id']=='toutiao-route-b':
            for row in overlay['files']:
                row['target']=projection.get(row['target'],row['target']);row['sha256']=original[row['target']]
            overlay['payload_path']=projection.get(overlay['payload_path'],overlay['payload_path'])
        else:
            overlay.clear();overlay.update(id='boatattack',state='active',package='com.Unity3d.BoatAttackDay',apk_sha256=APK_SHA,version_code=1,version_name='0.9',source=q['placement_plan'],rollback=q['programs']['executor'],admission=None,admission_status='PENDING_SEPARATE_OUTER_ADMISSION',files=[dict(target=t,sha256=h,role='candidate_bind' if t in {r['target'] for r in plan['binds']} else 'candidate_placement') for t,h in sorted(boat.items())])
    binary.original.seal_checks.validate_seal(candidate) # Structural/nonfile schema only; not build_seal/live admission.
    return planned,candidate

def build(request_path,out):
    need(not out.exists(),'fresh output');q,plan,seal,proof,original,binary,history=inputs(request_path)
    planned,candidate=compose(q,plan,seal,proof,original,binary)
    out.mkdir(parents=True);save(out/'planned_selfcheck.json',planned);save(out/'seal-candidate.json',candidate)
    save(out/'groups.expected.json',{k:sorted(v) for k,v in candidate['files'].items()})
    save(out/'overlays.pending.json',{'schema':'demo-overlays/v1','seal_stage':'v2','items':candidate['overlay_deployments'],'status':'PENDING_OUTER_ADMISSION_AND_ACTUAL_CAPTURE'})
    composition={'schema':'boat-v2-r5-composition/v1','status':'candidate/not_sealed','execution_enabled':False,'signed_by':None,'serial':q['serial'],'request':pinned(request_path),'compiler':pinned(Path(__file__)),'planned_selfcheck':pinned(out/'planned_selfcheck.json'),'seal_candidate':pinned(out/'seal-candidate.json'),'source_history_preserved':history is not None,'device_calls':0}
    save(out/'composition.json',composition);return composition

def verified(composition_path):
    composition_path=Path(composition_path).resolve();doc=read(composition_path)
    need(doc['schema']=='boat-v2-r5-composition/v1' and doc['status']=='candidate/not_sealed' and doc['signed_by'] is None and doc['execution_enabled'] is False,'readonly composition only')
    need(pin(doc['compiler'],composition_path.parent)==Path(__file__).resolve(),'composition compiler self pin')
    request=pin(doc['request'],composition_path.parent);q,plan,seal,proof,original,binary,history=inputs(request)
    planned,candidate=compose(q,plan,seal,proof,original,binary)
    sp=pin(doc['seal_candidate'],composition_path.parent);pp=pin(doc['planned_selfcheck'],composition_path.parent)
    need(read(sp)==candidate and read(pp)==planned,'exact union/candidate regeneration mismatch')
    return runtime_view(proof,plan,sp,request,sha(composition_path)),binary,doc

def runtime_view(proof,plan,sp,request,composition_sha):
    proof=copy.deepcopy(proof)
    # Reuse the original parameter template/package and its WID validator, replacing only exact Boat targets.
    rows={r['target']:copy.deepcopy(r) for r in proof['files']}
    for row in rows.values():row['source_target']=row['target']
    for r in plan['members']+plan['binds']:rows[r['target']]={'target':r['target'],'source_target':r['target'],'sha256':r['sha256'],'template_sha256':r['sha256'],'edits':[]}
    proof['files']=list(rows.values());proof['source_identity']=dict(kind='seal',**pinned(sp));proof['source_seal']=pinned(sp)
    proof['request']=pinned(request);proof['proof_sha256']=composition_sha
    need(len(proof['files'])==824,'all824 files plus130 actual packages')
    return proof

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    try:build(a.request,a.out);print('COMPILED_DISABLED_EXPECTED954_NOT_OBSERVED');return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:print('REFUSED: '+str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
