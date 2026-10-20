import pathlib,subprocess,json,datetime,sys,time,hashlib
b=pathlib.Path(__file__).parent;d=b/'t15-5cd-range-window-02';d.mkdir(exist_ok=False);repo=pathlib.Path.cwd();assert repo.name=='westlake-harness';serial='5cd1e3dd00000000000000000923012c'
def run(tag,a,timeout=20):
 (d/(tag+'.argv.json')).write_text(json.dumps(a));r=subprocess.run(a,capture_output=True,timeout=timeout);(d/(tag+'.stdout')).write_bytes(r.stdout);(d/(tag+'.stderr')).write_bytes(r.stderr);(d/(tag+'.rc')).write_text(str(r.returncode));return r
r=run('lock',['bash',str(repo/'scripts/lab/board_note.sh'),'lock',str(repo/'.octos/boards/app-lighting.md'),serial,'outer(codex)','T15 fixed-range read; verified current lock-helper pin;300s noUI/no runtime']);assert r.returncode==0
h=run('held',['bash',str(repo/'scripts/lab/board_note.sh'),'held',serial]).stdout.decode().strip();start=datetime.datetime.fromisoformat(h.split()[2]).timestamp();(d/'context.json').write_text(json.dumps(dict(holder=h,start=start,serial=serial)))
try:
 a=[sys.executable,str(repo/'benchmark/2026-10-20-t14-fixed-range-read/read_range.py'),'--execute','--repo',str(repo),'--profile',str(b/'t14-5cd-window-01/profile.json'),'--out',str(d/'range'),'--hdc','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','--holder',h,'--start',str(start),'--timeout','180'];r=run('outer',a,210);print(r.stdout.decode(),r.stderr.decode(),'outer_rc',r.returncode)
finally:
 r=run('unlock',['bash',str(repo/'scripts/lab/board_note.sh'),'unlock',str(repo/'.octos/boards/app-lighting.md'),serial,'outer(codex)']);assert r.returncode==0
 r=run('held-after',['bash',str(repo/'scripts/lab/board_note.sh'),'held',serial]);assert not r.stdout.strip();(d/'close.json').write_text(json.dumps(dict(closed_at=time.time(),duration_seconds=time.time()-start,lock_released=True,no_power_or_UI=True),indent=2));print((d/'close.json').read_text())
