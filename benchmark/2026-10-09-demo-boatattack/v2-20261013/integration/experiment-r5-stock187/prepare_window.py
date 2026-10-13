"""Offline render of concrete original board_run hooks and all fixed tool inputs.
Root supplies only a separate reviewed authorization/current window timestamps.
"""
import argparse,hashlib,json,os,sys,copy,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file()).parent)))
MAIN=WS/'westlake-harness';REL=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013');OUTER=MAIN/REL/'outer'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return '$WORKSPACES/'+str(p.resolve().relative_to(WS))
def pin(p):return {'path':ref(p),'sha256':sha(p)}
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def build(out):
 if out.exists():raise ValueError('fresh output required')
 out.mkdir(parents=True);sys.path.insert(0,str(HERE/'provider'));import prepare
 capture=OUTER/'5cd-v2-postinstall-capture/capture.json';plan=prepare.build(capture,out/'package')
 pp=out/'package/plan.disabled.json';manifest=OUTER/'fresh128-r4-actual5ea/batch-apps.json';apps=read(manifest)['apps']
 keys=['fd-seal','cv2-com-edward-studytracker','cv2-io-github-jdanders-dropcount','cv2-com-nicue-onetwo','cv2-com-trianguloy-clipboardeditor']
 rows=[json.loads(json.dumps(r).replace('$HOME/','$MAC_HOME/')) for r in apps if r['key'] in keys];assert len(rows)==5
 save(out/'popup-apps.json',{'apps':rows})
 index=out/'input-index';index.mkdir();input_pins=[];resolved=[]
 artifacts=out/'.artifacts';artifacts.mkdir()
 for r in rows:
  source=Path(os.path.expandvars(r['input_root'].replace('$WORKSPACES',str(WS))))/r['key']
  if not (source/'app-input.json').is_file():raise ValueError('missing actual app-input '+r['key'])
  (index/r['key']).symlink_to(source,target_is_directory=True)
  meta=source/'app-input.json';meta_ref={'path':r['input_root']+'/'+r['key']+'/app-input.json','sha256':sha(meta)};input_pins.append(meta_ref)
  argv=[sys.executable,str(MAIN/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--resolve-inputs','--manifest',str(out/'popup-apps.json'),'--input-root',str(index),'--keys',r['key'],'--out',str(artifacts/r['key'])]
  started=time.time();result=subprocess.run(argv,capture_output=True);(artifacts/(r['key']+'.stdout')).write_bytes(result.stdout);(artifacts/(r['key']+'.stderr')).write_bytes(result.stderr)
  resolved.append({'key':r['key'],'rc':result.returncode,'started':started,'finished':time.time(),'input_metadata':meta_ref,'source_root':r['input_root'],'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),'command':['python3','benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py','--resolve-inputs','--manifest',ref(out/'popup-apps.json'),'--input-root',ref(index),'--keys',r['key'],'--out',ref(artifacts/r['key'])]})
  save(out/'resolve-inputs.json',{'device_calls':0,'results':resolved})
  if result.returncode:raise ValueError('actual resolve-inputs failed '+r['key'])
 save(out/'snapshot-plan.json',read(OUTER/'candidate-window3/snapshot-plan.json'))
 base_smoke=MAIN/'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json';smoke=read(base_smoke)
 fp=next((OUTER/'fresh128-r4-actual5ea/window-01/runner').rglob('runtime-fingerprint.txt'));old=fp.read_text().strip().splitlines()
 needle='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354';stock='18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae'
 assert sum(needle in l for l in old)==1
 lines=sorted(l.replace(needle,stock) for l in old);smoke['expect']['runtime_fp']=hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:12]
 for r in plan['binds']:
  if r['target'].startswith('/system/'):smoke['probe']['files'][r['target']]=r['sha256']
 save(out/'candidate-smoke.json',smoke);save(out/'runtime-fingerprint-derivation.json',{'source':pin(fp),'only_replacement':{'before':needle,'after':stock},'expected':smoke['expect']['runtime_fp'],'files':len(lines)})
 # Snapshot the exact existing56 layers plus every candidate target and RouteB control preimage.
 snapshot=read(out/'snapshot-plan.json');known={r['target'] for r in snapshot['recover_layers']}
 for r in plan['members']+plan['binds']:
  if r['target'] not in known:snapshot['recover_layers'].append({'target':r['target'],'source':r['target'],'kind':'file'});known.add(r['target'])
 # Restored source files are absent after rollback; use original snapshot inventory for baseline return.
 save(out/'snapshot-plan.json',snapshot);save(out/'baseline-snapshot-plan.json',read(OUTER/'candidate-window3/snapshot-plan.json'))
 program_paths={'installer':HERE/'provider/installer.py','interaction':HERE/'interaction_runner.py','lock':WS/'westlake-inputs/tools/board_note.sh','r5':MAIN/'benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py','batch':MAIN/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py','snapshot':MAIN/'scripts/lab/board_state_snapshot.py','policy':MAIN/'scripts/lab/sepolicy_gate.py','smoke':MAIN/'scripts/lab/activation_smoke.py'}
 runout=out/'run';q={'schema':'boat-r5-window/v1','serial':plan['serial'],'out':ref(runout),'hdc':plan['hdc'],'plan':pin(pp),'programs':{n:pin(p) for n,p in program_paths.items()},'activation_binding':pin(MAIN/'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/activation-binding.5cd.json'),'popup_manifest':ref(out/'popup-apps.json'),'popup_keys':keys,'input_root':ref(index),'snapshot_plan':ref(out/'snapshot-plan.json'),'baseline_snapshot_plan':ref(out/'baseline-snapshot-plan.json'),'baseline_smoke':ref(base_smoke),'interaction_plan':ref(HERE/'interaction.plan.disabled.json')}
 q['static_checkpoint']=pin(HERE/'static-checkpoint.json')
 q['foreground_source']=pin(OUTER/'5cd-v2-preinstall-window/recover_foreground.py')
 q['input_pins']=input_pins+[pin(p) for p in [out/'popup-apps.json',out/'snapshot-plan.json',out/'baseline-snapshot-plan.json',base_smoke,HERE/'interaction.plan.disabled.json',out/'candidate-smoke.json']]
 save(out/'request.json',q)
 hook=['python3',ref(HERE/'window_hooks.py')];tail=['--request',ref(out/'request.json'),'--authorization','$R5_AUTH','--authorization-sha256','$R5_AUTH_SHA']
 bp={'serial':plan['serial'],'lane':'outer(codex)','entry':'91','why':'R5 stock187/ADC popup and Boat bounded experiment; never61b','board':'$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md','out':ref(out/'board-run'),'execution_enabled':False,'window_limit_minutes':30,'stop_new_tests_by_minute':20,'smoke_spec':ref(out/'candidate-smoke.json'),'shards':[], 'after_lock':hook+['after-lock']+tail,'before_unlock':hook+['before-unlock']+tail,'offline_precheck':{'hypothesis':'Remove global947 BBQ geometry only; preserve stock187 and original ADC Boat handoff. This pair is unmeasured.','evidence':[ref(HERE/'derivation.json'),ref(HERE/'popup-evidence.json')],'result':'not-falsified','expect':{'confirm':'three popup control sets restored plus original Boat LAP/heading/HUD; HW/ZZ controls unchanged','refute':'any lost controls or Boat stretch/noLAP/noheading: restore baseline and reject'}}}
 save(out/'board-run.disabled.json',bp)
 save(out/'authorization.required.json',{'approved_by':None,'request_sha256':sha(out/'request.json'),'hook_sha256':sha(HERE/'window_hooks.py'),'serial':plan['serial'],'origin_boot_id':plan['boot_id'],'holder':'outer(codex)','started_epoch':None,'experiment_expires_epoch':None,'rollback_expires_epoch':None,'stop_new_tests_epoch':None,'allow_candidate_boot':False,'allow_rollback_boot':False,'static_review':{'accepted':False,'evidence':q['static_checkpoint']},'limit':'root explicitly authorizes one candidate boot plus one baseline-return boot; stop new tests20min/window30min; no61b'})
 return bp
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out);print('CONCRETE_BOARD_RUN_RENDERED_DISABLED; zero device calls')
