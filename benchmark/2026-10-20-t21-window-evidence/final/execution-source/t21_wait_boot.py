from pathlib import Path
import json,subprocess,time,sys
p=Path(__file__).parent/'t21-5cd-window-01';c=json.loads((p/'context.json').read_text());old,tag=sys.argv[1:];d=p/(tag+'-boot-wait');d.mkdir()
for i in range(12):
 assert time.time()-c['start']<1700
 h=subprocess.run(['bash','scripts/lab/board_note.sh','held',c['serial']],capture_output=True,timeout=5);assert h.returncode==0 and h.stdout.decode().strip()==c['holder']
 a=[c['hdc'],'-t',c['serial'],'shell','cat /proc/sys/kernel/random/boot_id; param get sys.westlake.demo.u13.ready'];(d/f'{i}.argv.json').write_text(json.dumps(a))
 try:r=subprocess.run(a,capture_output=True,timeout=5)
 except subprocess.TimeoutExpired as e:
  (d/f'{i}.stdout').write_bytes(e.stdout or b'');(d/f'{i}.stderr').write_bytes(e.stderr or b'');(d/f'{i}.rc').write_text('timeout');time.sleep(3);continue
 (d/f'{i}.stdout').write_bytes(r.stdout);(d/f'{i}.stderr').write_bytes(r.stderr);(d/f'{i}.rc').write_text(str(r.returncode));lines=r.stdout.decode().splitlines()
 if r.returncode==0 and len(lines)==2 and len(lines[0].strip())==36 and lines[0].strip()!=old and lines[1].strip()=='true':
  v={'boot':lines[0].strip(),'observed_at':time.time()};(p/(tag+'-boot.json')).write_text(json.dumps(v));print(json.dumps(v));break
 time.sleep(3)
else:raise SystemExit('not ready within bounded poll')
