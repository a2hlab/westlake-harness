#!/usr/bin/env python3
"""Local-only5cd handoff assembly. Does not invent an installed UID or execute a device command."""
import argparse,copy,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'provider'))
import candidate_contract as c
import source_5cd
import prepare

def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--apk',type=Path,required=True);a=ap.parse_args()
    c.need(not a.out.exists(),'fresh offline output');data=source_5cd.validate_sources();refs=data['refs'];original=c.read(c.pinned(refs['preinstall_capture']))
    c.need(original['serial']==c.SERIAL and original['boot_before']==original['boot_after']==data['current_boot'] and original['complete'] is False,'current5cd preinstall scope')
    a.out.mkdir(parents=True)
    # Invoke the same compiler from this sibling. Its output program pins follow the actual checkout.
    result=subprocess.run([sys.executable,str(HERE/'entry/prepare_request.py'),'--capture',str(c.pinned(refs['preinstall_capture'])),'--apk',str(a.apk),'--out',str(a.out/'preinstall-disabled')],capture_output=True,text=True)
    (a.out/'request-build.stdout.txt').write_text(result.stdout);(a.out/'request-build.stderr.txt').write_text(result.stderr);c.need(result.returncode==0,'disabled request assembly failed')
    save(a.out/'candidate.blueprint.json',prepare.blueprint())
    cap=copy.deepcopy(original);cap.update(schema='boat-5cd-capture/v1',complete=False,boat_uid=None)
    # Exact5cd487 targets come from its admitted prepared plan. Never translate61b paths by string replacement.
    files={t:dict(exists=True,sha256=h,**data['metadata'][t]) for t,h in data['protected'].items()}
    _,_,_,old=c.sources()
    for t in [c.CFG,c.BOAT_APK]+[r['target'] for r in old['binds']]:
        files[t]=dict(exists=True,sha256=data['all940'][t],**data['metadata'][t]) if t in data['all940'] else original['files'][t]
    cap['files']=files
    cap['source_projection']={'preinstall':refs['preinstall_capture'],'full940':refs['full_readonly'],'historical_activation_binding':refs['activation_binding']}
    cap['pending']=['NOT a postinstall capture: Boat BMS UID, exact APK and empty signal target remain missing','outer must recapture all497 targets/319/three directories/root absence and BMS boot triplets after installation','all SHA/meta/raw pins must refer to the new actual capture; do not flip complete on this projection']
    save(a.out/'postinstall-capture.required.json',cap)
    main=Path(os.environ['WORKSPACES'])/'westlake-harness'
    r5=main/'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py'
    hdc=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
    pending={'path':'PENDING_FRESH_POSTINSTALL_REVIEW','sha256':'PENDING'}
    recipe={'schema':'boat-v2-staged-restore/v1','phase':'placement','serial':c.SERIAL,'boot_id':data['current_boot'],'execution_enabled':False,'signed_by':None,
            'route_b':{'mode':'verify-existing','entry':c.pin(r5),'realization':refs['realization'],'activation_binding':refs['activation_binding'],'hdc':c.pin(hdc)},
            'boat':{'seal':pending,'deployment':pending,'program':c.pin(HERE/'provider/boat_provider.py')}}
    save(a.out/'placement.recipe.pending.json',recipe)
    oldrefs=c.read(HERE.parent/'final-v2-candidate-r2/source-pins.json');oldchecked=c.read(c.pinned(oldrefs['selfcheck']));oldchecks={r['target']:r['actual'] for r in oldchecked['checks']}
    target_changes={'only_61b':sorted(set(oldchecks)-set(data['all940'])),'only_5cd':sorted(set(data['all940'])-set(oldchecks)),
                    'same_path_changed_sha':[{'target':t,'61b_sha256':oldchecks[t],'5cd_sha256':data['all940'][t]} for t in sorted(set(oldchecks)&set(data['all940'])) if oldchecks[t]!=data['all940'][t]]}
    save(a.out/'exact-delta.json',{'status':'OFFLINE_SOURCE_DIFFERENCE_NOT_REHEARSAL','sources':refs,'serial':c.SERIAL,'host_uid':20011300,'host_gid':20011300,'control_root':data['control_root'],'placement_boot':data['placement_boot'],'current_boot':data['current_boot'],'historical_independent_WID':data['historical_observed_window_id'],'WID_policy':'do not assign this historical29 at a future boot; r5 must collect independent current host/WMS evidence','objects':{'source940':len(data['all940']),'protected_route_and_hap':len(data['protected']),'required_postinstall_files':len(files),'placement_members':11,'cold_boot_binds':7},'path_and_byte_differences':target_changes,'source_940_scope':'hash and metadata inventory; not new execution of R5 nonfile/host gates','provider_disabled':True,'device_calls':0})
    save(a.out/'assembly.json',{'status':'DISABLED_PENDING_POSTINSTALL_CAPTURE','serial':c.SERIAL,'source_boot':data['current_boot'],'input_apk':c.pin(a.apk),'device_calls':0,'restored':False,'signed':False})
    print('5CD_DISABLED_HANDOFF: full940 source / exact487+HAP / pending actual Boat UID; zero device calls')
if __name__=='__main__':main()
