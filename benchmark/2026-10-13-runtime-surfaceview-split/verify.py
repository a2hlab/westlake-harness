"""Read-only artifact/receipt verification. Does not rebuild or rerun the host experiment."""
import hashlib,importlib.util,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def checked(ref):
    p=Path(ref['path'].replace('$WORKSPACES',str(WS)));need(p.is_file() and sha(p)==ref['sha256'],'artifact/source pin drift: '+str(p));return p
def verify():
    offline=json.loads((HERE/'evidence/offline/results.json').read_text());source=HERE/'source/android_graphics_compat_shim.cpp';need(sha(source)==offline['source_sha256']=='c208788a90ee19ad891af5cbe6fb8d7b29f339467ece084255d168dab45d1aef','exact candidate source')
    cases=offline['cases'];need(set(cases)=={'dedicated-child','popup-main','named-child-fallback','boat-main-counterexample','child-and-main-unavailable','no-session'},'actual function branch coverage')
    for name,r in cases.items():
        raw=json.loads((HERE/'evidence/offline'/(name+'.stdout.txt')).read_text());need(raw==r,'raw offline case differs')
        receipt=json.loads((HERE/'evidence/offline'/(name+'.receipt.json')).read_text());need(receipt['rc']==0 and sha(HERE/'evidence/offline'/(name+'.stdout.txt'))==receipt['stdout_sha256'],'actual function rc/SHA')
        need(r['update_writes']==r['after_seed_writes']==r['after_zero_writes'],'seed/width0 write regression')
    need(cases['dedicated-child']['child']==[1920,1200] and cases['dedicated-child']['main_writes']==0,'dedicated child geometry')
    need(cases['named-child-fallback']['main']==[1200,1920] and cases['named-child-fallback']['child_writes']==0,'name alone/fallback geometry')
    need(cases['boat-main-counterexample']['main']==[1200,1920],'main-layer counterexample retained')
    location=json.loads((HERE/'evidence/build-location.json').read_text());receipt=json.loads(checked(location).read_text());need(receipt['status']=='BUILT_ABI_PASS_NOT_RUNTIME_OR_UI_ACCEPTED' and receipt['device_calls']==0 and receipt['execution_enabled'] is False,'actual completed offline build required')
    build=[s for s in receipt['steps'] if s['argv'][0]=='/bin/bash'];need(len(build)==1 and build[0]['rc']==0,'original build rc0 required')
    for step in receipt['steps']:checked(step['stdout']);checked(step['stderr']);need(step['rc']==0,'build step failure')
    for key in ['source_patch','original_source_archive','prepare','clang','preparation','build_log','candidate','baseline','ABI_tool','candidate_source_recipe_archive']:checked(receipt[key])
    for ref in receipt['scripts'].values():checked(ref)
    for stage in ['closure_before','closure_after']:
        need(receipt[stage]['all_match'] is True,'complete source closure drift');inventory=json.loads(checked(receipt[stage]['inventory']).read_text());need(receipt[stage]['files']==len(inventory['files']),'source closure denominator')
    recorded_source=Path(receipt['source']['path'].replace('$WORKSPACES',str(WS)))
    need(receipt['source']['sha256']==sha(source),'landed candidate differs from the actually built source')
    recipe=checked(receipt['scripts']['recipe.sh']).read_text();need(recipe.count(str(recorded_source))==1,'single original build TU anchor')
    for flag in receipt['strict_link_flags']:need(flag in recipe,'strict link flag missing')
    spec=importlib.util.spec_from_file_location('original_ABI_check',checked(receipt['ABI_tool']));gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    abi=gate.verify(checked(receipt['candidate']),checked(receipt['baseline']));need(abi['exports_before']==abi['exports_after']==787 and not abi['added'] and not abi['removed'] and not abi['new_undefined'],'787 ABI exact')
    need(not receipt['ABI']['attribute_drift'] and len(abi['registrars'])==4,'actual GLOBAL registrars')
    predicted=json.loads((HERE/'predictions.json').read_text());need(predicted['status']=='OFFLINE_GEOMETRY_PREDICTIONS_NOT_RUNTIME_OR_UI_PASS','prediction must not claim UI')
    need(any(r['key']=='BoatMainViewRoot' and 'not Boat-equivalent' in r['counterexample'] for r in predicted['rows']),'main ViewRoot AB counterexample')
    return {'status':'OFFLINE_SOURCE_BUILD_ABI_VERIFIED_NOT_RUNTIME_ACCEPTANCE','candidate':receipt['candidate'],'build_receipt':location,'exports':787,'registrars':4,'source_inputs':receipt['closure_after']['files'],'device_calls':0}
if __name__=='__main__':print(json.dumps(verify()))
