"""Offline only: derive actual5ea R6 expected files and reuse unchanged128 driver."""
import argparse,copy,json
from pathlib import Path
import candidate_identity as c
import compile_candidate as compiler
import run_candidate_post_reboot as driver
MANIFEST_SHA='7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933'
TIERS_SHA='0cbe939161fcf3ca1d4c53933016feb36f75ca8226205110da9ee3129d6c07b2'
INDEX_SHA='38b70b09d66f0e11b6e738b6e504f07c2ac8a4c9b564c38cfef7f60d41c62275'
DRIVER_SHA='7cc72083f31bc4d8c7d5e10ebd61cc616cf93a0132617b5debeabb08d278a147'
def prepare(path,out):
    q=c.read(path);c.need(q['schema']=='r6-full128-disabled-request/v1' and q['execution_enabled'] is False,'disabled request required');c.need(not out.exists(),'fresh output required')
    old=c.read(c.pinned(q['original_r4_proof']));round=c.read(c.pinned(q['original5ea_round']));c.need(round['serial']==old['serial']==c.SPARE and round['apps']==128 and len(round['windows'])==8,'actual5ea128 round origin')
    refs=round['bindings'];c.need(refs['candidate_proof']==q['original_r4_proof'],'actual5ea originalproof round binding')
    for key,sha in [('manifest',MANIFEST_SHA),('tiers',TIERS_SHA),('install_index',INDEX_SHA),('driver',DRIVER_SHA)]:c.need(refs[key]['sha256']==sha and c.sha(c.pinned(refs[key]))==sha,'actual5ea canonical '+key+' pin')
    successor=c.read(c.pinned(q['successor_plan']));program=c.pinned(q['successor_program']);c.need(successor['executor']==q['successor_program'],'final successor plan/executor not synchronized')
    req=copy.deepcopy(c.read(c.pinned(old['request'])))
    req.update(original_r4_proof=q['original_r4_proof'],successor_plan=q['successor_plan'],successor_program=q['successor_program'],artifact_archive=q['artifact_archive'],successor_freeze=q['successor_freeze'])
    new={r['target']:r for r in successor['members']};c.need(set(new)=={c.OWN+'/sources/liboh_android_runtime.so',c.OWN+'/binds.tsv',c.OWN+'/worker.sh'},'exact three successor controls')
    for row in req['additional_files']:
        if row['target'] in new:
            r=new[row['target']];row['sha256']=r['sha256'];row['source']=c.pin(c.expand(r['source']))
    # Reject all source/plan failures before creating any successful output.
    wanted={**c.read(c.pinned(req['baseline']))['expected'],**c.CHANGES}
    wanted.update({r['target']:r['sha256'] for r in req['additional_files']})
    c.need(set(wanted)==set(old['expected']),'complete original expected membership')
    out.mkdir(parents=True);request_path=out/'identity-request.json';request_path.write_text(json.dumps(req,indent=2)+'\n');req['_request_path']=request_path
    proof=compiler.build(req,out/'identity')
    driver.prepare(c.pinned(refs['manifest']),c.pinned(refs['tiers']),c.pinned(refs['install_index']),out/'round',successor['boot_id'],out/'identity/smoke.json',serial=c.SPARE,candidate_proof=out/'identity/candidate-proof.json',candidate_sha=c.sha(out/'identity/candidate-proof.json'))
    delta={t:{'before':old['expected'][t],'after':h} for t,h in proof['expected'].items() if h!=old['expected'][t]}
    result={'status':'PREPARED_DISABLED_PENDING_ACTUAL_NEWBOOT_AND_ROOT_AB_ADMISSION','execution_enabled':False,'device_calls':0,'original_r4_proof':q['original_r4_proof'],'successor_plan':q['successor_plan'],'proof':c.pin(out/'identity/candidate-proof.json'),'round':c.pin(out/'round/round.json'),'inventory':{'original':len(c.read(c.pinned(proof['baseline']))['expected']),'sha_objects':len(proof['expected']),'unchanged_from_r4':len(proof['expected'])-len(delta),'changed_from_r4':len(delta),'typed_absences':proof['absent_files'],'apps':128,'windows':8,'tiers':{'10':121,'20':7}},'delta':delta,'pending':['fresh actual newboot all337/RouteB ABSENT/runtime/boot/parent/version readback','original exact input resolution/records/collect and root actual AB approval; no historical screenshot reuse']}
    (out/'preview.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(prepare(a.request.resolve(),a.out.resolve())));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print('REFUSED: '+str(e));return 2
if __name__=='__main__':raise SystemExit(main())
