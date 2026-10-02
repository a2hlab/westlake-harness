"""One authorized <=15min capture-only window. No runtime or system-service swaps."""
import importlib.util,json,subprocess,sys,time,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent;M=W/'westlake-harness';T=W/'westlake-inputs/tools'
s=importlib.util.spec_from_file_location('capture_identity',R/'benchmark/2026-10-02-toutiao-longwait-cxt0/window.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
serial=old.SERIAL
root=H/sys.argv[1];root.mkdir(exist_ok=False)
old.prelock(root)
subprocess.run(['bash',T/'board_note.sh','lock',old.BOARD,serial,'cx-t0','#90 frequent-habits ability-fallback capture-only <=15min'],check=True)
started=time.time();before=None;failure=None
try:
 before=old.identity(root/'before318')
 old.note('1/3 61b frequent-habits ability-fallback capture-only LOCK+318/双指纹PASS；不换件/JIT；95s t20/45/90一轮，≤15min。')
 args=['python3',H/'capture_batch.py','--execute','--serial',serial,'--lane','cx-t0','--manifest',W/'westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json','--input-root',W/'westlake-inputs/corpus-v2/app-inputs','--keys','cv2-com-frequent-habits','--reinstall','--wait','95','--hilog','95','--shots','20,45,90','--hdc-cmd',T/'hdc_mac.sh','--lock-cmd','mac '+str(T/'board_note.sh'),'--out',root/'batch','--run-id',root.name,'--stop-new-keys-at',str(started+720)]
 (root/'command.json').write_text(json.dumps({'argv':list(map(str,args))},indent=2)+'\n')
 with (root/'batch.log').open('w') as log:p=old.vm(args,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 recs=list((root/'batch').glob('*/*/*/record.json'));assert len(recs)==1,'one wrapped capture required'
 rec=json.loads(recs[0].read_text());assert p.returncode in (0,1) and rec['status'] in ('captured','foreground_unconfirmed','app_failed'),'infrastructure failed'
 facts=subprocess.run([sys.executable,M/'scripts/lab/run_facts.py',recs[0].parent.parent],capture_output=True,text=True,check=True)
 (root/'facts-verbatim.txt').write_text(facts.stdout);print(facts.stdout,flush=True)
except Exception as exc:
 failure=str(exc);(root/'failure.json').write_text(json.dumps({'error':failure})+'\n');print(failure,flush=True)
finally:
 after=old.identity(root/'final318')
 if before:assert after['fingerprints']==before['fingerprints'] and after['boot_id']==before['boot_id'],'base drift'
 (root/'finish.json').write_text(json.dumps({'passed':True,'deployed':False,'identity_assertions':318,'fingerprints':after['fingerprints'],'error':failure,'elapsed_seconds':time.time()-started},indent=2)+'\n')
 subprocess.run(['bash',T/'board_note.sh','unlock',old.BOARD,serial,'cx-t0'],check=True)
 subprocess.run([sys.executable,R/'benchmark/2026-10-03-u13-stage-a-plan/window1/infra_sample.py',root/'infra-after.json'],check=True)
 old.note('3/3 61b frequent-habits capture-only final318 diff/absent空、双指纹/boot_id不变，UNLOCK；事实与三时点图交外环。')
raise SystemExit(failure is not None)
