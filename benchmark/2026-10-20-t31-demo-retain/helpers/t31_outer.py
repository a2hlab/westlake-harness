from pathlib import Path
import json,subprocess,datetime,time,sys,shlex,uuid
from window_paths import BASE,WINDOW,SERIAL,live,context,budget,load,sha,phase_limit
repo,d=live();action=sys.argv[1];out=WINDOW;hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
c=None;deadline=None

def call(label,argv,timeout=40):
    if deadline is not None:
        left=deadline-time.monotonic();assert left>0,'window phase deadline';timeout=min(timeout,left)
    stem=out/(label+'-'+str(time.time_ns()));stem.with_suffix('.argv.json').write_text(json.dumps(argv))
    try:r=subprocess.run(argv,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as e:
        stem.with_suffix('.stdout').write_bytes(e.stdout or b'');stem.with_suffix('.stderr').write_bytes(e.stderr or b'');stem.with_suffix('.rc').write_text('timeout');raise
    stem.with_suffix('.stdout').write_bytes(r.stdout);stem.with_suffix('.stderr').write_bytes(r.stderr);stem.with_suffix('.rc').write_text(str(r.returncode));assert r.returncode==0,(label,r.returncode,r.stderr.decode());return r.stdout.decode()
if action=='acquire':
    out.mkdir(exist_ok=False)
    call('lock',['bash',str(repo/'scripts/lab/board_note.sh'),'lock',str(repo/'.octos/boards/app-lighting.md'),SERIAL,'inner(cx-seal)','T31 5cd final playback/recoverable retention, six states, 1800s total/1200s experiment/600s restore'])
    holder=call('holder',['bash',str(repo/'scripts/lab/board_note.sh'),'held',SERIAL]).strip();start=datetime.datetime.fromisoformat(holder.split()[2]).timestamp()
    names=list(load(d/'reuse-index.json')['selfpins'].values())+['admission.template.json']
    c=dict(purpose="T31_FINAL_ACCEPTANCE",repo=str(repo),serial=SERIAL,hdc=hdc,holder=holder,start=start,deploy=str(d),data_pins={n:sha(d/n) for n in names})
    (out/'context.json').write_text(json.dumps(c,indent=2));print(json.dumps(c));sys.exit()
c=context();phase=sys.argv[2];recovery=phase_limit(phase);deadline=time.monotonic()+budget(c,recovery)
held=call('held',['bash',str(repo/'scripts/lab/board_note.sh'),'held',SERIAL]).strip();assert held==c['holder']
boot=sys.argv[3];assert str(uuid.UUID(boot))==boot
if action=='shell':
    script=sys.argv[4];s='(set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+'; '+script+'; test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+'; echo T31_SHELL_COMPLETE)'
    raw=call('shell',[hdc,'-t',SERIAL,'shell',s]);print(raw);assert 'T31_SHELL_COMPLETE' in raw.splitlines()
elif action=='reboot':
    raw=call('boot-guard',[hdc,'-t',SERIAL,'shell','test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot)+' && echo BOOT_GUARD_OK']);assert raw.strip()=='BOOT_GUARD_OK'
    print(call('reboot',[hdc,'-t',SERIAL,'target','boot'],20))
elif action=='capture':
    sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
    class Board(b.Board):
        def command(self,argv,timeout=60):
            left=deadline-time.monotonic();assert left>0;return super().command(argv,min(timeout,left))
    dest=out/('capture-'+str(time.time_ns()));dest.mkdir();bd=Board(SERIAL,hdc,'bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'inner(cx-seal)',dest/'commands');bd.boot=boot;bd.ready()
    rc,h=bd.command(bd.lock+['held',SERIAL],5);assert rc==0 and h.strip()==c['holder']
    result=b.capture(bd,'/data/local/tmp/t31-shot-'+str(time.time_ns())+'.jpeg',dest/'screen.jpeg');(dest/'screenshot.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));print(dest)
else:raise ValueError(action)
print('elapsed',time.time()-c['start'])
