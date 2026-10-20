from pathlib import Path
import json,subprocess,datetime,time,sys,hashlib,shlex
repo=Path.cwd();assert repo.name=='westlake-harness';base=Path(__file__).parent;out=base/'t18-5cd-window-01';serial='5cd1e3dd00000000000000000923012c';hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc';action=sys.argv[1]
def call(tag,argv,timeout=40):
 stem=out/(tag+'-'+str(time.time_ns()));stem.with_suffix('.argv.json').write_text(json.dumps(argv));t=time.time()
 try:r=subprocess.run(argv,capture_output=True,timeout=timeout)
 except subprocess.TimeoutExpired as e:
  stem.with_suffix('.stdout').write_bytes(e.stdout or b'');stem.with_suffix('.stderr').write_bytes(e.stderr or b'');stem.with_suffix('.rc').write_text('timeout');raise
 stem.with_suffix('.stdout').write_bytes(r.stdout);stem.with_suffix('.stderr').write_bytes(r.stderr);stem.with_suffix('.rc').write_text(str(r.returncode));assert r.returncode==0,(tag,r.returncode,r.stderr.decode());return r.stdout.decode()
if action=='acquire':
 out.mkdir(exist_ok=False)
 call('lock',['bash',str(repo/'scripts/lab/board_note.sh'),'lock',str(repo/'.octos/boards/app-lighting.md'),serial,'outer(codex)','T18 5cd R9 plus AudioTrack getter, five files, fresh boot and rollback, 1800s total/600s recovery reserve'])
 holder=call('holder',['bash',str(repo/'scripts/lab/board_note.sh'),'held',serial]).strip();start=datetime.datetime.fromisoformat(holder.split()[2]).timestamp();c=dict(repo=str(repo),serial=serial,hdc=hdc,holder=holder,start=start);(out/'context.json').write_text(json.dumps(c,indent=2));print(json.dumps(c));sys.exit()
c=json.loads((out/'context.json').read_text());held=call('held',['bash',str(repo/'scripts/lab/board_note.sh'),'held',serial]).strip();assert held==c['holder'];age=time.time()-c['start'];assert 0<=age<1800,'window expired'
boot=sys.argv[2];assert len(boot)==36
if action=='shell':
 script=sys.argv[3];s='(set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+'; '+script+'; test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+'; echo T18_SHELL_COMPLETE)';raw=call('shell',[hdc,'-t',serial,'shell',s]);print(raw);assert 'T18_SHELL_COMPLETE' in raw.splitlines(), 'remote shell did not complete'
elif action=='reboot':
 guard=call('boot-guard',[hdc,'-t',serial,'shell','test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+' && echo BOOT_GUARD_OK']);assert guard.strip()=='BOOT_GUARD_OK';print(call('reboot',[hdc,'-t',serial,'target','boot'],20))
elif action=='capture':
 sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
 dest=out/('capture-'+str(time.time_ns()));dest.mkdir();bd=b.Board(serial,hdc,'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',dest/'commands');bd.boot=boot;bd.ready();r=b.capture(bd,'/data/local/tmp/t18-shot-'+str(time.time_ns())+'.jpeg',dest/'screen.jpeg');(dest/'screenshot.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));print(dest)
else:raise ValueError(action)
print('elapsed',time.time()-c['start'])
