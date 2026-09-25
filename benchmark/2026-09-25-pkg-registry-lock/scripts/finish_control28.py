from run25 import *
import hashlib
app,x,y,expected=sys.argv[1:5];r=R/('control-'+app);d=json.loads((r/'device-report.json').read_text());pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
events=[]
def action(c):
 t=time.time();o=dev(c);events.append({'epoch':t,'command':c,'output':o});(r/'actions.json').write_text(json.dumps(events,indent=2));return o
try:
 action('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1)
 action(f'echo i {x} {y} > /data/local/tmp/noice_tap');time.sleep(3)
 n=int(dev('wc -l < '+log).strip());action('echo v > /data/local/tmp/noice_tap');time.sleep(2)
 vt=dev(f'tail -n +{n+1} '+log);(r/'after-vt.txt').write_text(vt)
 matching=[s for s in vt.splitlines() if expected in s and (m:=re.search(r"rect=\[(-?\d+),(-?\d+) ",s)) and 0<=int(m[1])<1200 and 0<=int(m[2])<1920]
 page=bool(matching)
 visual='--visual' in sys.argv
 if visual:
  remote='/data/local/tmp/pkg28-control-after.jpeg'
  action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/'after.jpeg')
  (pathlib.Path(__file__).resolve().parents[1]/'wikipedia-after.jpeg').write_bytes((r/'after.jpeg').read_bytes())
  print('VISUAL_REVIEW_READY',r/'after.jpeg',flush=True)
 action(f'kill -3 {pid}');time.sleep(1)
 raw=dev('cat '+log,120)
 blocks=re.split(r'(?=^".*" (?:daemon )?prio=)',raw,flags=re.M)
 mains=[b for b in blocks if 'at android.app.ActivityThread.main(' in b]
 assert mains,'Missing ActivityThread.main stack'
 ui=int(re.search(r'sysTid=(\d+)',mains[-1])[1])
 start=time.monotonic();ident=None;rows=[]
 while True:
  state=action(f'cat /proc/{pid}/stat; cat /proc/{pid}/task/{ui}/stat; cat /proc/uptime')
  assert state.count(') ')>=2,'process/UI disappeared'
  current=state.splitlines()[0].rsplit(') ',1)[1].split()[19]
  if ident is None:ident=current
  assert current==ident,'PID reused'
  rows.append({'elapsed':time.monotonic()-start,'stat':state})
  (r/'observation.json').write_text(json.dumps(rows,indent=2))
  if rows[-1]['elapsed']>=65:break
  time.sleep(5)
 if visual:
  review=json.loads((r/'visual-verification.json').read_text())
  page=review['verified'] and review['expected_page']==expected and review['sha256']==hashlib.sha256((r/'after.jpeg').read_bytes()).hexdigest()
  matching=['Screenshot manually inspected; see after.jpeg and visual-verification.json']
 collect(r,d)
 text=(r/'child.stderr').read_text(errors='replace')
 fatal=[s for s in text.splitlines() if 'Fatal signal' in s or '[INITCHILD-FAIL]' in s]
 result={'app':app,'child':pid,'ui_tid':ui,'expected_page':expected,'page_after_real_input':page,'visible_matching_lines':matching,'observation_seconds':rows[-1]['elapsed'],'fatal_or_ui_exit':fatal,'fault_files':(r/'fault-paths.txt').read_text().splitlines(),'pass':page and not fatal and not (r/'fault-paths.txt').read_text().strip()}
 (r/'control-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 assert result['pass'],result
finally:
 collect(r,d);stop(d)
