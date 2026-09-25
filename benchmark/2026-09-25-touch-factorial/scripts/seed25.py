from run25 import *
seedpath='/data/local/tmp/touch25-reuse-seed.tar'
manifest=R/'reuse-seed.json'
if sys.argv[1]=='save':
 origin=R/sys.argv[2];d=json.loads((origin/'device-report.json').read_text())
 runtime=d['runtime'];cmd=f'cd {runtime} && tar -cf {seedpath} app-data data webview-t-data'
 print(dev(cmd,180));hashline=dev('sha256sum '+seedpath)
 manifest.write_text(json.dumps({'origin':str(origin),'runtime':runtime,'sha256':hashline.split()[0],'contents':['app-data','data','webview-t-data']},indent=2))
 recv(seedpath,R/'reuse-seed.tar')
 print(hashline)
else:
 mode,rep=sys.argv[1:];meta=json.loads(manifest.read_text());origin=pathlib.Path(meta['origin']);d=json.loads((origin/'device-report.json').read_text());runtime=d['runtime']
 # The seed's parent and child were collected/stopped before snapshot creation.
 stop(d)
 assert dev('sha256sum '+seedpath).split()[0]==meta['sha256']
 print(dev(f'cd {runtime} && rm -rf app-data data webview-t-data && tar -xf {seedpath}',180))
 network(mode=='offline')
 rows=[json.loads(l) for l in (origin/'commands.jsonl').read_text().splitlines()]
 c=next(x['command'] for x in rows if x['command'].startswith('nohup ') and 'source_app_namespace' in x['command'])
 reply=dev(c);parent=int(reply.strip())
 for _ in range(60):
  if 'READY' in dev('if [ -S '+d['socket']+' ]; then echo READY; fi'):break
  time.sleep(.5)
 # Socket can survive the killed parent; allow the restarted listener to initialize.
 time.sleep(2)
 r,d2=launch(f'{mode}-seeded-{rep}',origin);d2['parent']=parent
 (r/'device-report.json').write_text(json.dumps(d2,indent=2));(r/'seed.json').write_text(json.dumps(meta,indent=2))
 try:
  measure(r,d2,False)
 finally:
  collect(r,d2);stop(d2);network(False)
