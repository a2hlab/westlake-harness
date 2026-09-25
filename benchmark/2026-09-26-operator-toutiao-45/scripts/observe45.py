from board45 import *
name,op=sys.argv[1:3];r=R/name;d=json.loads((r/'device-report.json').read_text());log=d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'
root=pathlib.Path(__file__).resolve().parents[1]
def action(c):
 out=dev(c)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'command':c,'output':out})+'\n')
 return out
if op=='shell':
 if 'uinput' in sys.argv[3]:
  state=action('cat /proc/'+str(d['child'])+'/stat 2>/dev/null')
  assert ') ' in state and state.rsplit(') ',1)[1].split()[0]!='Z','bound app exited; inspect new screen before input'
  active=action('if [ ! -e /data/local/tmp/operator45/stop ]; then cat /data/local/tmp/operator45/child.pid; fi').strip()
  assert not active or active==str(d['child']),'guardian changed instance; rebind and inspect before input'
 print(action(sys.argv[3]))
if op=='vt':
 n=int(action('wc -l < '+log).strip());action('echo v > /data/local/tmp/noice_tap');time.sleep(.8);raw=action(f'tail -n +{n+1} '+log);(r/(sys.argv[3]+'.txt')).write_text(raw);print('\n'.join(x for x in raw.splitlines() if x.startswith('VT')))
if op=='shot':
 label=sys.argv[3];remote='/data/local/tmp/operator45.jpeg';action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/(label+'.jpeg'));p=root/'preview'/name/(label+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'.jpeg')).read_bytes());print(p)
if op=='collect':
 for key,path in [('child.stderr',log),('parent.log',d['stage']+'/parent.log')]:recv(path,r/key)
