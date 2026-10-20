#!/usr/bin/env python3
"""Actual T29 data/ref closure and pre-Board refusal only; no transaction replay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
P = Path(__file__).resolve().parent
EXECUTOR = '693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb'
SELF_PINS = {'executor_sha256':'executor.py','parameters_sha256':'parameters.json',
 'source_pins_sha256':'executor-source-pins.json','readonly_inputs_sha256':'readonly-inputs.json',
 'bridge_candidate_sha256':'bridge-candidate.json','shim_candidate_sha256':'shim-candidate.json',
 'three_slot_requirements_sha256':'three-slot-admission.json',
 'bridge_binding_requirements_sha256':'bridge-binding-pending.json'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text())
def save(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def validate(root, roots):
    sources=[]
    def resolve(ref):
        path=Path(ref['path'])
        assert not path.is_absolute() and '..' not in path.parts
        hits=[r/path for r in roots if (r/path).is_file() and sha(r/path)==ref['sha256']]
        assert hits, 'missing exact source: '+str(path)
        if 'bytes' in ref: assert hits[0].stat().st_size==ref['bytes']
        sources.append(ref)
        return hits[0]
    assert sha(root/'executor.py')==EXECUTOR
    for item in load(root/'unchanged-pins.json'):
        assert sha(root/item['file'])==item['sha256']
        assert (root/item['file']).read_bytes()==resolve({'path':item['donor'],'sha256':item['sha256']}).read_bytes()
    for row in load(root/'pending-history.json')['files']:
        assert sha(root/'history-pending'/row['path'])==row['sha256']
    params=load(root/'parameters.json'); old=load(root/'donor-t28-parameters.json')
    assert len(params['artifacts'])==6 and params['artifacts'][:4]==old['artifacts'][:4]
    for key in ('serial','uid','desktop_uid','runtime','cfg_path','cfg_sha256','apk_sha256','runtime_exe_sha256','run_derivation'):
        assert params[key]==old[key],key
    assert params['historical_identity_only']=={} and params['approved_by'] is None
    inspect=load(root/'candidate-inspection.json')
    assert inspect['device_calls']==0 and inspect['commands_rc']==[0,0]
    candidates={}
    for index,role in ((4,'bridge'),(5,'shim')):
        c=load(root/(role+'-candidate.json')); candidates[role]=c
        assert c['path']==old['artifacts'][index]['path'] and c['before_sha256']==old['artifacts'][index]['before_sha256']
        assert params['artifacts'][index]['path']==c['path'] and params['artifacts'][index]['before_sha256']==c['before_sha256']
        assert c['build_status']=='PRODUCTION_BUILD_VERIFIED' and c['production_refs']
        assert {'sha256':c['after_sha256'],'bytes':c['after_bytes']}==inspect['artifacts'][role+'.so']
        assert c['after_sha256']!=c['before_sha256'] and c['after_bytes']>0
        assert params['artifacts'][index]['after_sha256']==c['after_sha256']
        assert params['artifacts'][index]['after_bytes']==c['after_bytes']
        for ref in c['production_refs']: resolve(ref)
    assert candidates['bridge']['production_refs']==candidates['shim']['production_refs']
    refs=candidates['bridge']['production_refs']
    def ref_named(suffix):
        rows=[r for r in refs if r['path'].endswith(suffix)]; assert len(rows)==1,suffix
        return load(resolve(rows[0]))
    prod=ref_named('/production-01/results.json'); receipt=ref_named('/receipt.public.json')
    assert prod['status']=='OFFLINE_OBSERVATION_CANDIDATE_NOT_DEPLOY_AUTHORIZED'
    assert prod['commands']==22 and prod['all_rc_zero'] is True
    assert len(receipt['commands'])==22 and all(x['rc']==0 for x in receipt['commands'])
    for role,c in candidates.items():
        assert prod['artifacts'][role+'.so']==inspect['artifacts'][role+'.so']==receipt['outputs'][role+'.so']
    assert prod['bridge_abi']['equal'] and prod['shim_abi']['equal']
    assert prod['jni']['name_signature_function_symbol_equal'] is True
    assert prod['shim_exports']==inspect['shim_exports']
    owner=ref_named('/owner-bindings.json')
    assert owner['bridge_sha256']==candidates['bridge']['after_sha256']
    assert owner['offsets']==inspect['owner_offsets']
    binding=load(root/'bridge-binding-pending.json')
    assert binding['bridge_sha256']==candidates['bridge']['after_sha256'] and binding['shim_sha256']==candidates['shim']['after_sha256']
    assert binding['owner_offsets'] | binding['owner_slots']==owner['offsets']
    assert binding['actual_provider_instance_receipt'] is None
    for field in ('public_binding_receipt','consumer_jni_and_got_receipt'): resolve(binding[field])
    slots=load(root/'three-slot-admission.json')
    assert slots['candidate_sha256']==candidates['shim']['after_sha256']
    assert slots['player_sha256']==params['artifacts'][3]['after_sha256']
    assert [(s['symbol'],s['player_slot']) for s in slots['slots']]==[
      ('ANativeWindow_setBuffersGeometry','0x472048'),('ANativeWindow_lock','0x472490'),('ANativeWindow_unlockAndPost','0x472760')]
    for s in slots['slots']:
        assert s['candidate_export_offset']==inspect['shim_exports'][s['symbol']]
        assert s['actual_slot_value'] is None and s['matched'] is False
    ad=load(root/'admission.template.json')
    for field in ('approved_by','boot','holder','window_start','parent_mnt','origin_apply_plan_sha256','bridge_metadata','shim_metadata','fresh_three_slot_receipt_sha256'):
        assert ad[field] is None,field
    assert ad['host']=={'pid':None,'birth':None,'uid':20011300} and ad['recovery_no_parent'] is False
    for field,file in SELF_PINS.items(): assert ad[field]==sha(root/file),field
    assert ad['providers']==load(root/'readonly-inputs.json')['providers']
    # Independent peer is mandatory for the explicit original-object mismatch.
    peer=load(resolve(load(root/'production-peer-ref.json')))
    assert peer['status']=='OFFLINE_PRODUCTION_STATIC_PEER_PASS', 'independent production peer not accepted'
    assert peer['bridge.so']==inspect['artifacts']['bridge.so']
    assert peer['shim.so']==inspect['artifacts']['shim.so']
    assert peer['exact_owner']['offsets']==owner['offsets'] and peer['shim_exports']==inspect['shim_exports']
    comparison=ref_named('/baseline-object-comparison.json')
    assert set(comparison)==set(receipt['consumer_original_objects'])
    for name,row in comparison.items():
        original=receipt['consumer_original_objects'][name]
        assert row['old_sha256']==original['historical'] and row['new_sha256']==original['rebuilt']
        assert row['entire_object_equal_except_comment'] is True and row['different_bytes']==38
        assert len(row['section_differences'])==1
        assert row['section_differences'][0]['section']=='.comment' and row['section_differences'][0]['alloc'] is False
    for row in ref_named('/production-01/manifest.json'): resolve(row)
    return sources

def sentinels(root, roots, out, sources):
    view=out/'receipt-view'
    for ref in sources:
        src=next(r/ref['path'] for r in roots if (r/ref['path']).is_file() and sha(r/ref['path'])==ref['sha256'])
        dest=view/ref['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    runs=[]
    for mode in ('preflight','apply','rollback'):
      for execute in (False,True):
        argv=[sys.executable,str(root/'executor.py'),mode]
        if execute:
            argv+=['--execute','--boot','OFFLINE_SENTINEL','--parent','1','--birth','1','--hdc','/NONEXISTENT_T29_NO_DEVICE','--holder','OFFLINE_SENTINEL','--out',str(out/'never-device'),'--repo',str(view),'--inputs',str(out),'--admission',str(root/'admission.template.json'),'--start','1']
        r=subprocess.run(argv,capture_output=True,timeout=10)
        name=mode+('-execute-sentinel' if execute else '-preview')
        save(out/(name+'.argv.json'),argv);(out/(name+'.stdout')).write_bytes(r.stdout);(out/(name+'.stderr')).write_bytes(r.stderr);(out/(name+'.rc')).write_text(str(r.returncode)+'\n')
        if execute:
            assert r.returncode!=0 and b'TypeError' in r.stderr and b'shim_metadata' in r.stderr,r.stderr
            assert b'bms_batch' not in r.stderr and not (out/'never-device').exists()
        else: assert r.returncode==0 and json.loads(r.stdout)['device_calls']==0
        runs.append({'name':name,'rc':r.returncode,'expected':'fresh metadata refusal before Board' if execute else 'preview'})
    return runs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,action='append',required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/'))
    sources=validate(P,a.source_root);a.out.mkdir(parents=True,exist_ok=False)
    runs=sentinels(P,a.source_root,a.out,sources)
    result={'status':'STATIC_DATA_VERIFIED_NOT_ADMISSION','sources':sources,'runs':runs,'device_calls':0,'transaction_tests_rerun':False,'live_three_slots':'UNKNOWN','approved_by':None,'executor_sha256':sha(P/'executor.py')}
    save(a.out/'results.json',result);print(json.dumps(result))
if __name__=='__main__':main()
