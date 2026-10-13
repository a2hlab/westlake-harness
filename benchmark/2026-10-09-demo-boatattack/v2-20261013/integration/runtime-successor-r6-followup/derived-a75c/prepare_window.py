"""Offline assemble the actual five-input index and original board_run entry."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ['WORKSPACES']).resolve();MAIN=WS/'westlake-harness'
REL=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013');OUTER=MAIN/REL/'outer'
NEW='f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
OLD='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def ref(p):return '$WORKSPACES/'+str(Path(p).resolve().relative_to(WS))
def pin(p):return dict(path=ref(p),sha256=sha(p))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def build(out):
 out.mkdir(parents=True,exist_ok=False)
 archive=OUTER/'r6-source-review/artifact-archive.json';a=read(archive)
 if a['runtime']['sha256']!=NEW or not a['remote_verified']:raise ValueError('archived f28 source required')
 rt=Path(os.path.expandvars(a['runtime']['path']));hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
 s=load(HERE/'successor.py','r6_compile');s.prepare(argparse.Namespace(main=str(MAIN),runtime=rt,runtime_sha256=NEW,hdc=hdc,out=out/'package'))
 plan=read(out/'package/plan.disabled.json')
 donor=MAIN/REL/'integration/experiment-r5-stock187/interaction_runner.py';src=donor.read_text()
 assert src.count("SERIALS={'5cd1e3dd00000000000000000923012c'}")==1
 stock='18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae';assert src.count(stock)==1
 (out/'interaction_runner.py').write_text(src.replace("SERIALS={'5cd1e3dd00000000000000000923012c'}","SERIALS={'5ea34a4500000000000000001123012c'}").replace(stock,NEW))
 ip=read(MAIN/REL/'integration/experiment-r5-stock187/interaction.plan.disabled.json');ip.update(serial=plan['serial'],uid=plan['boat_uid'],scope='same seven assets; f28 successor, actual5ea UID; original cadence and source-derived coordinates unchanged')
 save(out/'interaction.plan.disabled.json',ip)
 # Reuse the original per-key symlink index and real BMS --resolve-inputs protocol.
 q0=read(OUTER/'r5-experiment-main-r4/request.json');apps=read(Path(os.path.expandvars(q0['popup_manifest'])))
 save(out/'popup-apps.json',apps);index=out/'input-index';index.mkdir();evidence=out/'resolve';evidence.mkdir();results=[];inputs=[]
 for row in apps['apps']:
  root=Path(os.path.expandvars(row['input_root']));source=root/row['key'];meta=source/'app-input.json'
  if not meta.is_file():raise ValueError('real input missing: '+str(meta))
  (index/row['key']).symlink_to(source,target_is_directory=True);inputs.append(dict(path=row['input_root']+'/'+row['key']+'/app-input.json',sha256=sha(meta)))
  argv=[sys.executable,str(MAIN/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--resolve-inputs','--manifest',str(out/'popup-apps.json'),'--input-root',str(index),'--keys',row['key'],'--out',str(evidence/row['key'])]
  now=time.time();r=subprocess.run(argv,capture_output=True);(evidence/(row['key']+'.stdout')).write_bytes(r.stdout);(evidence/(row['key']+'.stderr')).write_bytes(r.stderr)
  results.append(dict(key=row['key'],rc=r.returncode,started=now,finished=time.time()));save(out/'resolve-results.json',results)
  if r.returncode:raise ValueError('actual resolve failed '+row['key'])
 # Exact legal snapshot domain. No /data/westlake-demo source entries.
 snapshot=read(OUTER/'candidate-window3/snapshot-plan.json');known={r['target'] for r in snapshot['recover_layers']}
 for row in plan['binds']:
  if row['target'] not in known:snapshot['recover_layers'].append(dict(target=row['target'],source=row['target'],kind='file'));known.add(row['target'])
 save(out/'snapshot-plan.json',snapshot)
 sys.path.insert(0,str(MAIN/'scripts/lab'));snap=load(MAIN/'scripts/lab/board_state_snapshot.py','r6_actual_snapshot');targets=snap.plan_targets(snapshot,snap.load_recipe())
 save(out/'snapshot-validation.json',dict(targets=len(targets),all_seven=all(r['target'] in known for r in plan['binds']),original_plan_targets=True))
 smoke=read(MAIN/'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json')
 fp=next((OUTER/'fresh128-r4-actual5ea/window-01/runner').rglob('runtime-fingerprint.txt'));lines=fp.read_text().strip().splitlines();assert sum(OLD in s for s in lines)==1
 for row in plan['binds']:
  if row['target'].startswith('/system/'):smoke['probe']['files'][row['target']]=row['sha256']
 smoke['expect']['runtime_fp']=hashlib.sha256('\n'.join(sorted(lines)).encode()).hexdigest()[:12];save(out/'baseline-smoke.json',smoke)
 smoke['expect']['runtime_fp']=hashlib.sha256('\n'.join(sorted(s.replace(OLD,NEW) for s in lines)).encode()).hexdigest()[:12];smoke['probe']['files']['/system/android/lib64/liboh_android_runtime.so']=NEW
 save(out/'candidate-smoke.json',smoke);save(out/'fingerprint-derivation.json',dict(source=pin(fp),before=OLD,after=NEW,files=len(lines)))
 programs={k:v for k,v in q0['programs'].items() if k in ['lock','batch','snapshot','policy','smoke']};programs.update(installer=pin(HERE/'successor.py'),interaction=pin(out/'interaction_runner.py'))
 q=dict(schema='boat-runtime-successor-window/v1',serial=plan['serial'],out=ref(out/'run'),hdc=hdc,plan=pin(out/'package/plan.disabled.json'),programs=programs,popup_keys=q0['popup_keys'],popup_manifest=ref(out/'popup-apps.json'),input_root=ref(index),snapshot_plan=ref(out/'snapshot-plan.json'),baseline_snapshot_plan=ref(out/'snapshot-plan.json'),baseline_smoke=ref(out/'baseline-smoke.json'),interaction_plan=ref(out/'interaction.plan.disabled.json'),static_checkpoint=pin(archive))
 q['input_pins']=inputs+[pin(out/n) for n in ['popup-apps.json','snapshot-plan.json','baseline-smoke.json','candidate-smoke.json','interaction.plan.disabled.json']]+[pin(donor),pin(fp)]
 save(out/'request.json',q)
 tail=['--request',ref(out/'request.json'),'--authorization','$R6_AUTH','--authorization-sha256','$R6_AUTH_SHA'];hook=['python3',ref(HERE/'window_hooks.py')]
 bp=dict(serial=plan['serial'],lane='outer(codex)',entry='91',why='5ea f28 three-source cold-boot comparison; never61b',board='$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md',out=ref(out/'board-run'),execution_enabled=False,window_limit_minutes=30,stop_new_tests_by_minute=20,smoke_spec=ref(out/'candidate-smoke.json'),shards=[],after_lock=hook+['after-lock']+tail,before_unlock=hook+['before-unlock']+tail,offline_precheck=dict(hypothesis='Dedicated SurfaceView requested geometry with main ViewRoot compatibility preserves Boat and five popup controls',evidence=[ref(archive),ref(HERE/'SYNC-T0.md')],result='not-falsified',expect=dict(confirm='Boat geometry/LAP/steering and popup controls plus HW/ZZ',refute='any geometry/control regression: rollback and reject')))
 save(out/'board-run.disabled.json',bp)
 save(out/'authorization.required.json',dict(approved_by=None,request_sha256=sha(out/'request.json'),hook_sha256=sha(HERE/'window_hooks.py'),serial=plan['serial'],origin_boot_id=plan['boot_id'],holder='outer(codex)',started_epoch=None,experiment_expires_epoch=None,rollback_expires_epoch=None,stop_new_tests_epoch=None,allow_candidate_boot=False,allow_rollback_boot=False,static_review=dict(accepted=False,evidence=q['static_checkpoint'])))
 print('DISABLED_BOARD_RUN_PREPARED: actual5 inputs resolved; legal snapshot targets='+str(len(targets)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out)
