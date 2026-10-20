from pathlib import Path
import json,subprocess,time,sys
from window_paths import WINDOW,context,budget,phase_limit,tag as safe_tag
p=WINDOW;c=context();phase,old,tag=sys.argv[1:];safe_tag(tag);deadline=time.monotonic()+budget(c,phase_limit(phase));d=p/(tag+'-boot-wait');d.mkdir()
for i in range(24):
 assert time.monotonic()<deadline
 h=subprocess.run(['bash',str(Path(c['repo'])/'scripts/lab/board_note.sh'),'held',c['serial']],capture_output=True,timeout=min(5,deadline-time.monotonic()));assert h.returncode==0 and h.stdout.decode().strip()==c['holder']
 a=[c['hdc'],'-t',c['serial'],'shell','cat /proc/sys/kernel/random/boot_id; param get sys.westlake.demo.u13.ready'];(d/f'{i}.argv.json').write_text(json.dumps(a))
 try:r=subprocess.run(a,capture_output=True,timeout=min(5,deadline-time.monotonic()))
 except subprocess.TimeoutExpired as e:
  (d/f'{i}.stdout').write_bytes(e.stdout or b'');(d/f'{i}.stderr').write_bytes(e.stderr or b'');(d/f'{i}.rc').write_text('timeout');time.sleep(max(0,min(3,deadline-time.monotonic())));continue
 (d/f'{i}.stdout').write_bytes(r.stdout);(d/f'{i}.stderr').write_bytes(r.stderr);(d/f'{i}.rc').write_text(str(r.returncode));lines=r.stdout.decode().splitlines()
 if r.returncode==0 and len(lines)==2 and len(lines[0].strip())==36 and lines[0].strip()!=old and lines[1].strip()=='true':
  v={'boot':lines[0].strip(),'observed_at':time.time()};(p/(tag+'-boot.json')).write_text(json.dumps(v));print(json.dumps(v));break
 time.sleep(max(0,min(3,deadline-time.monotonic())))
else:raise SystemExit('not ready within bounded poll')
