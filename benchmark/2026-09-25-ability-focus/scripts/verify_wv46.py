"""Interactive evidence driver; no automatic acceptance clicks or timeout kills."""
from launch34 import *
import hashlib
base=R/'wv46-verification';base.mkdir(exist_ok=True)
cmd=sys.argv[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def send(p,remote):subprocess.run([H,'-t',S,'file','send',str(p),remote],check=True,timeout=240)
if cmd=='launch':
 name=sys.argv[2];origin='warm-b11';d=json.loads((R/origin/'device-report.json').read_text());runtime=d['runtime']
 assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip(),'live namespace'
 remote=runtime+'/webview-t-lib/libwebview_bionic_shim.so'
 oldhash=dev('sha256sum '+remote).split()[0]
 assert oldhash=='ae6ac82830c2cd143469047c404765cd13b0c38106d2ccfe92596059f8e6b6ea'
 backup='/data/local/tmp/ability38-webview46-original.'+oldhash+'.so'
 dev('cp '+remote+' '+backup);assert dev('sha256sum '+backup).split()[0]==oldhash
 recv(remote,base/'original-shim.so')
 assert sha(base/'original-shim.so')==oldhash
 candidate=pathlib.Path.home()/'a2hlab/ws/out-wv46/patched/libwebview_bionic_shim.so'
 assert sha(candidate)=='ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f'
 send(candidate,remote);dev('chmod 644 '+remote)
 assert dev('sha256sum '+remote).split()[0]==sha(candidate)
 original=R/'ab-config/original-run.sh';send(original,runtime+'/run.sh');dev('chmod 755 '+runtime+'/run.sh')
 (base/'deployment.json').write_text(json.dumps({'board':S,'original_sha256':oldhash,'backup':backup,'candidate':str(candidate),'candidate_sha256':sha(candidate),'target':remote,'run_sha256':sha(original)},indent=2)+'\n')
 dev('power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility')
 sys.argv.append('--warm');r,d=restart(name,origin)
 (r/'wv46-deployment.json').write_bytes((base/'deployment.json').read_bytes());print('LIVE',json.dumps({k:d[k] for k in ('child','parent','runtime','stage')}))
elif cmd=='summarize':
 name=sys.argv[2];r=R/name;d=json.loads((r/'device-report.json').read_text());collect(r,d)
 s=(r/'child.stderr').read_text(errors='replace');counts={k:s.count(k) for k in ['GLES library translated','GrGLInterface creation failed','InitializeGL failure']}
 lifecycle=[x for x in s.splitlines() if x.startswith(('[B47-SLA] ENTRY','[ABILITY38-RESUMED]','[SOURCE-WEBVIEW-CMD]'))]
 (r/'assertions.json').write_text(json.dumps(counts,indent=2)+'\n');(r/'lifecycle.txt').write_text('\n'.join(lifecycle)+'\n');print(json.dumps(counts));print('\n'.join(lifecycle))
elif cmd=='stop':
 name=sys.argv[2];r=R/name;d=json.loads((r/'device-report.json').read_text());collect(r,d);stop(d)
 deployment=json.loads((base/'deployment.json').read_text());send(base/'original-shim.so',deployment['target']);dev('chmod 644 '+deployment['target'])
 assert dev('sha256sum '+deployment['target']).split()[0]==deployment['original_sha256']
