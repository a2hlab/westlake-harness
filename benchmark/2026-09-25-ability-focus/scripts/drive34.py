from common34 import *
name,op=sys.argv[1:3];r=R/name;d=json.loads((r/'device-report.json').read_text());log=d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'
def action(c):
 t=time.time();out=dev(c)
 with (r/'manual-actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':t,'command':c,'output':out})+'\n')
 return out
if op=='shell':print(action(sys.argv[3]))
elif op=='shot':
 label=sys.argv[3];remote='/data/local/tmp/focus34-manual.jpeg';action('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/(label+'.jpeg'))
 p=pathlib.Path(__file__).resolve().parents[1]/'preview'/name/(label+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'.jpeg')).read_bytes());print(p)
elif op=='vt':
 n=int(dev('wc -l < '+log).strip());action('echo v > /data/local/tmp/noice_tap');time.sleep(1);raw=dev(f'tail -n +{n+1} '+log);(r/'manual-vt.txt').write_text(raw);print('\n'.join(x for x in raw.splitlines() if x.startswith('VT')))
elif op=='maps':(r/'maps.txt').write_text(action('cat /proc/'+str(d['child'])+'/maps'))
elif op=='collect':collect(r,d)
elif op=='stop':(r/'stop-request').write_text('requested by codex-2 after evidence collection\n')
