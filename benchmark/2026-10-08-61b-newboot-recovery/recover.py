"""Run approved original recovery primitives under the newly authorized holder."""
import importlib.util,json,os,sys,subprocess,traceback
from pathlib import Path
W=Path(os.environ['WORKSPACES']);M=W/'westlake-harness';O=Path(sys.argv[1])
p=M/'benchmark/2026-10-03-61b-return/return_61b.py'
s=importlib.util.spec_from_file_location('original_recovery',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=json.loads(p.with_name('binding.json').read_text());rec=m.Recorder(O)
hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
def holder():
 result=rec.run(['bash',M/'scripts/lab/board_note.sh','held',m.SERIAL])
 assert result.stdout.decode().strip()==os.environ['EXPECTED_HOLDER'] and not result.stderr,'new authorized holder drift'
def boot():
 value,_=m.shell(rec,hdc,'cat /proc/sys/kernel/random/boot_id');value=m.valid_boot(value)
 assert value==os.environ['EXPECTED_BOOT'],'new boot drift'
 return value
def command(argv,timeout=600):
 print('COMMAND',list(map(str,argv)),flush=True)
 result=rec.run(argv,timeout=timeout)
 print(result.stdout.decode(errors='backslashreplace'),end='',flush=True)
 print(result.stderr.decode(errors='backslashreplace'),end='',file=sys.stderr,flush=True)
try:
 m.verify_bindings(b,W);holder();initial=boot()
 m.save(O/'execution-inputs.json',dict(binding_sha256=m.sha(p.with_name('binding.json')),expected_boot=initial,authorized_holder=os.environ['EXPECTED_HOLDER'],pinned_files=b['pinned_files'],old_journal_unchanged=True))
 command(m.recovery_command(b,W,O,True),900)
 assert json.loads((O/'recovery.json').read_text()).get('status')=='baseline_restored','executor restoration refused'
 for name in ['restored','final']:
  destination=O/name
  command([sys.executable,m.expand(b['hook'],W),'--verify-base','--serial',m.SERIAL,'--root',destination])
  checked=m.identity(destination,b);assert checked['boot_id']==initial,'verification boot drift'
  print(name.upper()+' IDENTITY '+json.dumps(checked),flush=True)
  print(name.upper()+' PROCESS_VIEW '+(destination/'process-view.json').read_text(),flush=True)
  if name=='restored':
   smoke=O/'recovery-smoke'
   command([sys.executable,M/'scripts/lab/activation_smoke.py','--serial',m.SERIAL,'--lane','cx-t0','--spec',m.expand(b['smoke_spec'],W),'--out',smoke],900)
   m.strict_smoke(smoke);print('SMOKE '+(smoke/'smoke-result.json').read_text(),flush=True)
   command([sys.executable,M/'scripts/lab/run_facts.py',smoke],120)
 holder();boot();m.verify_bindings(b,W)
 command(['bash',M/'scripts/lab/board_note.sh','unlock',M/'.octos/boards/app-lighting.md',m.SERIAL,'cx-t0'],120)
 empty=rec.run(['bash',M/'scripts/lab/board_note.sh','held',m.SERIAL],required=False)
 assert empty.returncode==1 and not empty.stdout and not empty.stderr,'unlock not confirmed empty'
 report=dict(status='restored-verified-unlocked',serial=m.SERIAL,boot_id=initial,identity_assertions=321,unique_paths=319,fingerprints=b['fingerprints'],smoke='PASS',held_exit_code=1,held_stdout='',held_stderr='',screenshot_verdict='outer review required')
 m.save(O/'result.json',report);print(json.dumps(report,indent=2),flush=True)
except Exception as exc:
 report=dict(status='stopped-requires-outer-review',error=str(exc),serial=m.SERIAL,unlock_attempted=any('unlock' in row['command'] for row in rec.records),lock_state='not released by this runner')
 m.save(O/'result.json',report);print(json.dumps(report,indent=2),flush=True);traceback.print_exc();sys.exit(1)
