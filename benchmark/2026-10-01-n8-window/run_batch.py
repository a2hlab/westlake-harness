"""Run master batch using a pinned, merged-input manifest."""
import argparse,os,shlex,subprocess,sys,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('keys');p.add_argument('--controls',action='store_true');a=p.parse_args()
TARGETS=['localsend','fd-immich','fd-fluffychat','fd-kitchenowl','fd-libre','fd-saber','firefox','fd-fennec_fdroid','mcdonalds','fd-im-vector-app','aegis','fd-catima','ooniprobe','fd-auxio','fd-calendar','markor']
serial='61b0657200000000000000000324012c'
if a.run in ['n8-'+k for k in TARGETS] and a.run!='n8-localsend':
 r=H/'runs/n8-targets'/serial/a.keys/'record.json'
 d=json.loads(r.read_text())
 assert d.get('finished_at') and len([x for x in d.get('screenshots',[]) if x.get('captured')])==2,'incomplete grouped result'
 print('Already captured in n8-targets: '+a.keys);raise SystemExit(0)
grouped=a.run=='n8-localsend'
if grouped:a.run='n8-targets';a.keys=','.join(TARGETS)
cmd=[sys.executable,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial','61b0657200000000000000000324012c','--lane','cx-t0','--hdc-cmd',str(R/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'--lock-cmd','mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),'--out',str(H/'runs'),'--run-id',a.run,'--hilog','20','--shots','5,20','--focus-check','--keys',a.keys]
if a.controls:cmd+=['--manifest',str(R/'benchmark/2026-09-30-n3-61b/controls.json'),'--input-root',str(lab_paths.workspaces()/'westlake-b90-controls-inputs'),'--launch-only']
else:cmd+=['--manifest',str(H/'manifest.json'),'--input-root',str(H/'inputs'),'--launch-only' if a.run.startswith('n8-u5') else '--reinstall']
if not grouped:os.execv(sys.executable,cmd)
rc=subprocess.call(cmd)
index={}
for key in TARGETS:
 run=H/'runs'/('n8-'+key);target=H/'runs/n8-targets'/serial/key/'record.json'
 if target.exists():
  run.symlink_to('n8-targets',target_is_directory=True);index['n8-'+key]='n8-targets/'+serial+'/'+key
(H/'grouped-run-aliases.json').write_text(json.dumps(index,indent=2)+'\n')
raise SystemExit(rc)
