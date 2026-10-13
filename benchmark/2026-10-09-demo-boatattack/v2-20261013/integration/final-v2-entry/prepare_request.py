#!/usr/bin/env python3
"""Build a disabled preinstall request from real readonly preinstall evidence and the original APK."""
import argparse,json,os
from pathlib import Path
import prepare_boat as p
r=p.r
HERE=Path(__file__).resolve().parent

def portable(path):
    path=Path(path).resolve();ws=Path(os.environ['WORKSPACES']).resolve()
    return '$WORKSPACES/'+str(path.relative_to(ws)) if path.is_relative_to(ws) else str(path)
def pin(path):return {'path':portable(path),'sha256':r.sha(path)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',type=Path,required=True);ap.add_argument('--apk',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    c=r.read(a.capture);r.need(c['serial']==r.SERIAL and c['boot_before']==c['boot_after'] and c['complete'] is False and c['boat_uid'] is None and c['boat_registered'] is False,'real preinstall pending snapshot required')
    r.need(r.sha(a.apk)==p.APK_SHA,'original APK pin')
    for name,h in p.STOCK.items():r.need(c['files'][p.LIBDIR+'/'+name]==dict(exists=True,sha256=h,**p.META),'actual existing stock preimage')
    r.need(c['files'][p.APK]==c['files'][p.SIGNAL]=={'exists':False},'only APK/placeholder missing facts')
    r.need(not a.out.exists(),'fresh output');a.out.mkdir(parents=True);inputs=a.out/'input/boatattack';inputs.mkdir(parents=True)
    r.save(inputs/'app-input.json',{'application':{'package':p.PACKAGE,'launch_activity':'com.unity3d.player.UnityPlayerActivity'},'apk_sha256':p.APK_SHA,'source_apk':os.path.relpath(a.apk.resolve(),inputs.resolve()),'native_libraries':{}})
    main=Path(os.environ['WORKSPACES'])/'westlake-harness'
    request={'schema':'boat-missing-preinstall/v1','execution_enabled':False,'serial':r.SERIAL,'boot_id':c['boot_before'],'preinstall_snapshot':pin(a.capture),
             'executor':pin(main/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'identity_program':pin(HERE.parent/'final-v2-candidate-r2/boat_identity.py'),
             'app':{'key':'boatattack','package':p.PACKAGE,'apk_sha256':p.APK_SHA,'launch_activity':'com.unity3d.player.UnityPlayerActivity'},'input_root':portable(a.out/'input'),
             'transport':{'hdc_cmd':'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','lock_cmd':'bash '+str(main/'scripts/lab/board_note.sh').replace(str(main.parent),'$WORKSPACES'),'lane':'PENDING_REAL_LOCK_HOLDER'}}
    r.save(a.out/'request.disabled.json',request)
    r.save(a.out/'recipe.disabled.json',{'schema':'boat-v2-staged-restore/v1','phase':'preinstall','serial':r.SERIAL,'boot_id':c['boot_before'],'signed_by':None,'execution_enabled':False,'preinstall':{'program':pin(HERE/'prepare_boat.py'),'request':pin(a.out/'request.disabled.json')}})
    print('PREINSTALL_DISABLED; no device calls; postinstall capture remains required')
if __name__=='__main__':main()
