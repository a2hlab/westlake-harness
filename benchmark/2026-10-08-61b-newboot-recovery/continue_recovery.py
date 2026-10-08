"""Outer-approved single owned-placeholder cleanup, unchanged smoke/final gates."""
import importlib.util,json,os,sys,subprocess,traceback
from pathlib import Path
W=Path(os.environ['WORKSPACES']);M=W/'westlake-harness';O=Path(sys.argv[1]);TARGET='/system/android/lib64/libicu74compat.so'
p=M/'benchmark/2026-10-03-61b-return/return_61b.py';s=importlib.util.spec_from_file_location('original_recovery',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=json.loads(p.with_name('binding.json').read_text())
if len(sys.argv)>2 and sys.argv[2]=='--remove-one':
 sys.path.insert(0,str(M/'scripts/lab'));import u7_executor as u
 previous=json.loads(m.expand(b['journal'],W).read_text());assert TARGET in previous['plan']['additions'],'not recorded addition'
 op=previous['operations'][30];assert op['target']==TARGET and op['absent'] is True and op['phase']=='bound','wrong owned operation'
 io=u.DeviceIO(m.SERIAL,'cx-t0',O/'cleanup-device');io.guard(os.environ['EXPECTED_BOOT'])
 mounts=io.shell('cat /proc/mounts');mounted=[line for line in mounts.splitlines() if len(line.split())>=2 and line.split()[1]==TARGET];assert not mounted,'placeholder mounted'
 assert not io.mounts().get(TARGET),'mountinfo disagrees'
 got,absent=io.snapshot([TARGET],[TARGET]);assert absent==[] and got=={TARGET:u.EMPTY},'not exact empty placeholder'
 receipt=dict(target=TARGET,addition=True,original_operation=30,original_absent=True,mounted=mounted,before=got,empty_sha256=u.EMPTY)
 m.save(O/'placeholder-guards.json',receipt);print('PLACEHOLDER GUARDS '+json.dumps(receipt),flush=True)
 io.guard(os.environ['EXPECTED_BOOT']);io.remove_placeholder(TARGET)
 got,absent=io.snapshot([TARGET],[TARGET]);assert got=={} and absent==[TARGET],'placeholder not absent after cleanup'
 receipt.update(removed=True,after=got,absent=absent);m.save(O/'placeholder-removed.json',receipt);print('PLACEHOLDER REMOVED '+json.dumps(receipt),flush=True);sys.exit(0)
rec=m.Recorder(O);hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
def held():
 r=rec.run(['bash',M/'scripts/lab/board_note.sh','held',m.SERIAL]);assert r.stdout.decode().strip()==os.environ['EXPECTED_HOLDER'] and not r.stderr,'holder drift'
def boot():
 v,_=m.shell(rec,hdc,'cat /proc/sys/kernel/random/boot_id');assert m.valid_boot(v)==os.environ['EXPECTED_BOOT'],'boot drift'
def run(cmd,timeout=600):
 print('COMMAND',list(map(str,cmd)),flush=True);r=rec.run(cmd,timeout=timeout);print(r.stdout.decode(errors='backslashreplace'),end='',flush=True);print(r.stderr.decode(errors='backslashreplace'),end='',file=sys.stderr,flush=True)
try:
 m.verify_bindings(b,W);held();boot()
 run(m.vm_prefix(W)+['env','EXPECTED_BOOT='+os.environ['EXPECTED_BOOT'],'python3',Path(__file__).resolve(),O,'--remove-one'],120)
 smoke=O/'recovery-smoke';run([sys.executable,M/'scripts/lab/activation_smoke.py','--serial',m.SERIAL,'--lane','cx-t0','--spec',m.expand(b['smoke_spec'],W),'--out',smoke],900);m.strict_smoke(smoke)
 run([sys.executable,m.expand(b['hook'],W),'--verify-base','--serial',m.SERIAL,'--root',O/'final'],600);checked=m.identity(O/'final',b);assert checked['boot_id']==os.environ['EXPECTED_BOOT'],'final boot drift';print('FINAL IDENTITY '+json.dumps(checked),flush=True);print('FINAL PROCESS_VIEW '+(O/'final/process-view.json').read_text(),flush=True)
 runs=list((smoke/'group-0').glob('*/'+m.SERIAL));assert len(runs)==1
 r=rec.run([sys.executable,M/'scripts/lab/run_facts.py',runs[0]],timeout=120);(O/'facts.txt').write_bytes(r.stdout);print(r.stdout.decode(),end='',flush=True)
 held();boot();m.verify_bindings(b,W)
 run(['bash',M/'scripts/lab/board_note.sh','unlock',M/'.octos/boards/app-lighting.md',m.SERIAL,'cx-t0'],120)
 r=rec.run(['bash',M/'scripts/lab/board_note.sh','held',m.SERIAL],required=False);assert r.returncode==1 and not r.stdout and not r.stderr,'unlock ambiguous'
 report=dict(status='restored-verified-unlocked',serial=m.SERIAL,boot_id=os.environ['EXPECTED_BOOT'],identity_assertions=321,unique_paths=319,fingerprints=b['fingerprints'],smoke='PASS',held_exit_code=1,held_stdout='',held_stderr='',screenshot_verdict='outer review required');m.save(O/'result.json',report);print(json.dumps(report,indent=2),flush=True)
except Exception as exc:
 report=dict(status='stopped-requires-outer-review',error=str(exc),unlock_attempted=any('unlock' in r['command'] for r in rec.records),serial=m.SERIAL);m.save(O/'result.json',report);print(json.dumps(report,indent=2),flush=True);traceback.print_exc();sys.exit(1)
