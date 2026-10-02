"""Fill the reviewed draft from exact promoted/base and candidate identities."""
import copy,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[1]
sys.path.insert(0,str(H));import prepare as c
PREFIX='$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-window'
def save(name,value):c.save(H/name,value)
def main():
 comp=json.loads((H/'composition.json').read_text());expect=json.loads((H/'expected.json').read_text());candidate=expect['candidate']
 smoke=json.loads((R/'knowledge/smoke/n11h.json').read_text())
 smoke['_comment']='Executable N11h review candidate: signed U10.1T8 190afedd base, host-only 65cc3535 -> 65ac5089. No boot or JAR changes.'
 smoke['expect']={'runtime_fp':comp['runtime_fp'],'boot_fp':comp['boot_fp']}
 smoke['advisory_fixes']=[f for f in smoke['fixes'] if f.get('conditional')]
 smoke['fixes']=[f for f in smoke['fixes'] if not f.get('conditional')]
 files={p:s for p,s in candidate.items() if p in ['/system/bin/appspawn-x','/system/lib64/appspawn/libwestlake_android_child.z.so','/system/android/framework/oh-adapter-runtime.jar','/system/android/framework/adapter-mainline-stubs.jar','/system/android/framework/oh-adapter-framework.jar'] or Path(p).name in ['libnativeloader.so','libbionic_compat.so']}
 smoke['probe']['files']=files;save('smoke.json',smoke)
 restored=copy.deepcopy(smoke);restored['expect']={'runtime_fp':'d6848fa2c989','boot_fp':'e3806b65a079'};restored['fixes']=[];restored.pop('advisory_fixes')
 restored['probe']['files']['/system/bin/appspawn-x']=c.OLD
 restored['probe']['expect_copies']={'liboh_adapter_bridge.so':2,'liboh_android_runtime.so':2}
 restored['_comment']='Recovery assertion of signed U10.1T8, preserving its accepted two-owner baseline. No N11h markers required.'
 save('restored-smoke.json',restored)
 plan=json.loads((R/'benchmark/2026-10-02-n11h-predictions/plan-n11h-61b.json').read_text())
 plan.pop('_executor_note',None);plan.pop('_shards_note',None);plan['_comment']='Review-only executable plan; outer binding adoption and window approval are required before enabling. All binaries unchanged from the accepted cx-bms build.'
 plan['execution_enabled']=False;plan['approval']='Pending outer review of exact repaired manifest, registry delta and this executable plan.'
 plan['precondition']={'base':'U10.1T8 signed ACK(90) 2026-10-02 17:53:13; current 190afedd','base_bundle_sha256':comp['base_bundle_sha256'],'host_sha256':c.OLD,'identity_assertions':318,'candidate_manifest_sha256':comp['package_manifest_sha256'],'only_change':'/system/bin/appspawn-x','residual_cleanup':'Pre-lock read-only check; if Toutiao remains, dedicated guarded cleanup lock + verify U10.1T8 + unlock precedes experiment lock. Never signal a root parent.'}
 plan['expect']={'base_runtime_fp':'d6848fa2c989','candidate_runtime_fp':comp['runtime_fp'],'boot_fp':comp['boot_fp']}
 plan['package_manifest_sha256']=comp['package_manifest_sha256'];plan['inputs_sha256']=comp['inputs_sha256'];plan['base_bundle_sha256']=comp['base_bundle_sha256']
 plan['out']=PREFIX+'/$N11H_RUN_ID/61b/runner';plan['smoke_spec']=PREFIX+'/smoke.json'
 root=PREFIX+'/$N11H_RUN_ID/61b'
 plan['after_lock']=['python3',PREFIX+'/window_hook.py','--action','apply','--root',root]
 plan['before_unlock']=['python3',PREFIX+'/window_hook.py','--action','finish','--root',root]
 plan['offline_precheck']['evidence']=[PREFIX+'/composition.json',PREFIX+'/registry-delta.json','$WORKSPACES/westlake-harness/benchmark/2026-10-02-n11h-predictions/n11h-predictions.csv','$WORKSPACES/westlake-harness/benchmark/2026-10-02-n11h-predictions/white-rate-prior.md','$WORKSPACES/westlake-harness/benchmark/2026-10-02-u12-sigabrt/observations.json','$WORKSPACES/westlake-harness/benchmark/2026-10-02-n11h-host-owner/evidence/open-candidate.json']
 plan['offline_precheck']['hypothesis']='Only the host owner edge changes: sealed bridge/runtime owners shared before bridge/app loading may reduce each owner to one load-base. Session-miss targets may gain frames; seven AssetManager->GetLongField abort keys may advance if their field-ID/object owners become the same. This is a conditional hypothesis, not a guarantee of UI or JNI initialization.'
 plan['offline_precheck']['expect']['confirm']='Exact U10.1T8 318 baseline; only host65cc->65ac; unchanged boot/JAR/service chain; true resident-check AND inherit rc=0; ART/JVM/bridge/runtime each one load-base; HW/ZZ controls. Per-target fresh maps/logs and outer t20 readout; white-lottery gain requires the predeclared full k/n streak.'
 plan['offline_precheck']['expect']['refute']='Wrong signed base or unregistered exact manifest refuses before LOCK. Missing hard marker / owner lookup failure / bridge or runtime still >1 / control or compat canary confirmed regression -> stop and restore U10.1T8. A target remaining white refutes that target prediction, not automatically a control regression; missing k/n samples remain unknown. AssetManager abort may persist if initialization has an independent defect.'
 orig='$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json'; cv2='$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json'
 sequence=[('compat-primary',['fd-fennec_fdroid','fd-noice','wikipedia','fd-uhabits','fd-k9']),('asset-cv2',['cv2-org-linaro-glmark2','cv2-org-andresoviedo-dddmodel2']),('asset-flutter',['fd-fluffychat','fd-immich','fd-kitchenowl','fd-libre','fd-saber','localsend']),('orig-canaries',['fd-com-amaze-filemanager','fd-libretube','noice','fd-AppManager','fd-app','termux']),('other-cv2',['cv2-ca-vaults-randomlydie','cv2-com-bytehamster-flowitgame','cv2-com-degeder-yam','cv2-com-paultirk-yatoo']),('negative-orig',['x','fd-shatteredpixeldungeon']),('negative-cv2',['cv2-dev-obfusk-jiten-webview'])]
 # Each repeat is its own fresh run; a batch manifest key itself is unique.
 for key,n in [('fd-noice',4),('fd-uhabits',3),('noice',5),('wikipedia',6)]:
  sequence += [(key+'-repeat-'+str(i),[key]) for i in range(2,n+1)]
 shards=[];keys=[]
 (H/'keys').mkdir(exist_ok=True)
 for name,group in sequence:
  iscv2=group[0].startswith('cv2-');assert all(k.startswith('cv2-')==iscv2 for k in group)
  (H/'keys'/f'{name}.txt').write_text('\n'.join(group)+'\n');keys+=group
  shards.append({'name':name,'manifest':cv2 if iscv2 else orig,'input_root':'$WORKSPACES/westlake-inputs/corpus-v2/app-inputs' if iscv2 else '~/a2hlab/app-inputs','keys_file':PREFIX+'/keys/'+name+'.txt'})
 plan['shards']=shards
 plan['policy']['before_unlock']='Unconditional host-only rollback to U10.1T8 65cc3535, full318 + d6848fa2c989/e3806b65a079 + recovery smoke + final assertion. Failure retains the lock. Never return to U9.'
 plan['policy']['budget']='<=30 minutes, cutoff minute20 enforced by master bms_batch. Keys/repeats beyond cutoff are unknown, not passed. This mechanism-first short window cannot promise all 40 launches; later observation windows require outer scheduling. No statistical improvement claim from an incomplete streak.'
 plan['policy']['white_k_of_n']={'fd-noice':'4/4','fd-uhabits':'3/3','noice':'5/5','wikipedia':'6/6','judge':'outer t20, alpha=.05 point-prior; thin prior caveat retained'}
 plan['policy']['compat_canary']='fd-fennec_fdroid: reject newly missing __gnu_strerror_r / compat visibility; compare first fatal to promoted baseline, not assumed t20-lit.'
 plan['policy']['artifact_gates']='Native-only transaction runs production N1/N2/frozen against corrected final native package and signed base; boot/JAR bytes are unchanged and asserted in all318 snapshots. No image rebuild/rebind.'
 save('plan-61b.json',plan);save('key-inventory.json',{'keys':list(dict.fromkeys(keys)),'planned_launches':len(keys),'asset_observations':['fd-fluffychat','fd-immich','fd-kitchenowl','fd-libre','fd-saber','localsend','cv2-org-linaro-glmark2'],'not_measured':'unknown after cutoff','device_io':False})
 print('plan prepared: disabled, 30/20 minutes,',len(set(keys)),'unique keys;',len(keys),'budget-limited launches')
if __name__=='__main__':main()
