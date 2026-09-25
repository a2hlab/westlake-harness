"""VM-only, board5ea manual media article validation; no automatic app kills on observation."""
from launch34 import *
import hashlib
root=pathlib.Path(__file__).resolve().parents[1]
base=R/'mc46-verification';base.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def send(p,target):subprocess.run([H,'-t',S,'file','send',str(p),target],check=True,timeout=240)
def clean(origin):
 r=R/origin;d=json.loads((r/'device-report.json').read_text());collect(r,d)
 for p in dev('pidof '+PKG).split():
  st=dev('cat /proc/'+p+'/stat; cat /proc/'+p+'/mountinfo')
  (r/('cleanup-'+p+'.txt')).write_text(st)
  assert pathlib.Path(d['runtime']).name in st,'foreign runtime'
  dev('kill -9 '+p)
 stop(d)
 return d
cmd,name=sys.argv[1:3]
if cmd=='clean':
 clean(name);print('CLEANED; patched libraries retained',flush=True)
elif cmd in ('deploy','deploy-npth','deploy-tt','restart'):
 origin=sys.argv[3];d=clean(origin);target=d['runtime']+'/liboh_adapter_bridge.so'
 if cmd=='deploy':
  oldhash=dev('sha256sum '+target).split()[0]
  assert oldhash=='e4ab5de64d20b8da6c7f388a7d5f5efd536f2962bb3913975e89ce824300c45a'
  backup='/data/local/tmp/ability38-mc46-original.'+oldhash+'.so'
  dev('cp '+target+' '+backup);recv(target,base/'original-bridge.so')
  assert sha(base/'original-bridge.so')==oldhash==dev('sha256sum '+backup).split()[0]
  p=pathlib.Path.home()/'a2hlab/ws/out-mc46/patched/liboh_adapter_bridge.so'
  assert sha(p)=='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
  send(p,target);dev('chmod 644 '+target)
  assert dev('sha256sum '+target).split()[0]==sha(p)
  shim=dev('sha256sum '+d['runtime']+'/webview-t-lib/libwebview_bionic_shim.so').split()[0]
  assert shim=='ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f'
  (base/'deployment.json').write_text(json.dumps({'board':S,'target':target,'backup':backup,'original_sha256':oldhash,'candidate':str(p),'candidate_sha256':sha(p),'shim_sha256':shim},indent=2)+'\n')
 if cmd=='deploy-npth':
  target=d['runtime']+'/lib/arm64-v8a/libnpth.so';oldhash=dev('sha256sum '+target).split()[0]
  assert oldhash=='10641147b4c2a551e48162fa07f08776642147abc443d014756b909b6236076f'
  backup='/data/local/tmp/ability38-npth46-original.'+oldhash+'.so'
  dev('cp '+target+' '+backup);recv(target,base/'original-npth.so')
  assert sha(base/'original-npth.so')==oldhash==dev('sha256sum '+backup).split()[0]
  p=pathlib.Path.home()/'a2hlab/ws/out-npth46/libnpth.so'
  assert sha(p)=='8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af'
  send(p,target);dev('chmod 644 '+target);assert dev('sha256sum '+target).split()[0]==sha(p)
  (base/'npth-deployment.json').write_text(json.dumps({'board':S,'target':target,'backup':backup,'original_sha256':oldhash,'candidate':str(p),'candidate_sha256':sha(p)},indent=2)+'\n')
 checks={n:dev('sha256sum '+d['runtime']+'/'+n).split()[0] for n in ['liboh_adapter_bridge.so','webview-t-lib/libwebview_bionic_shim.so','lib/arm64-v8a/libnpth.so']}
 assert checks['liboh_adapter_bridge.so']=='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
 assert checks['webview-t-lib/libwebview_bionic_shim.so']=='ecc7b12c3591c979f3d9aece5bb1d414acc04d01d2c500a88364525082f9df9f'
 if cmd=='deploy-tt':
  target=d['runtime']+'/run.sh';original=base/'pre-tt-run.sh';recv(target,original)
  before=sha(original);backup='/data/local/tmp/ability38-tt46-original.'+before+'.sh';dev('cp '+target+' '+backup)
  assert dev('sha256sum '+backup).split()[0]==before
  helper=pathlib.Path('/Users/zhaoyue/orca/workspaces/westlake-harness-triage46/benchmark/2026-09-26-toutiao-crash-triage/scripts/apply_tt_targets.py')
  targets='libttcrypto.so,libttboringssl.so,libdelta.so,liblynxsecurity.so';patched=base/'tt-run.sh'
  subprocess.run([sys.executable,str(helper),str(original),str(patched),targets],check=True)
  repeated=base/'tt-run-again.sh';subprocess.run([sys.executable,str(helper),str(patched),str(repeated),targets],check=True)
  assert repeated.read_bytes()==patched.read_bytes()
  send(patched,target);dev('chmod 755 '+target);assert dev('sha256sum '+target).split()[0]==sha(patched)
  (base/'tt-deployment.json').write_text(json.dumps({'target':target,'backup':backup,'original_sha256':before,'candidate_sha256':sha(patched),'helper':str(helper),'helper_sha256':sha(helper),'added_targets':targets.split(','),'idempotent':True},indent=2)+'\n')
 dev('power-shell timeout -o 86400000; power-shell wakeup')
 profile_backup=None
 if '--fresh-preserved' in sys.argv:
  assert re.fullmatch(r'[a-zA-Z0-9-]+',name)
  profile_backup=d['runtime']+'/profile-backups/'+name
  assert not dev('ls -d '+profile_backup+' 2>/dev/null').strip()
  dev('mkdir -p '+profile_backup)
  for part in ('app-data','data','webview-t-data'):
   dev('if [ -d '+d['runtime']+'/'+part+' ]; then mv '+d['runtime']+'/'+part+' '+profile_backup+'/'+part+'; fi')
 sys.argv.append('--warm');r,d=restart(name,'warm-b11')
 (r/'deployment.json').write_bytes((base/'deployment.json').read_bytes())
 (r/'library-hashes.json').write_text(json.dumps(checks,indent=2)+'\n')
 if (base/'npth-deployment.json').exists():(r/'npth-deployment.json').write_bytes((base/'npth-deployment.json').read_bytes())
 if (base/'tt-deployment.json').exists():(r/'tt-deployment.json').write_bytes((base/'tt-deployment.json').read_bytes())
 (r/'native-targets-live.txt').write_text(dev('strings /proc/'+str(d['child'])+'/environ | grep WESTLAKE_ANDROID_NATIVE_TARGETS'))
 if profile_backup:(r/'fresh-profile.json').write_text(json.dumps({'fresh':True,'preserved_at':profile_backup,'reason':'Repeated pre-article startup exits in existing warm data; original directories retained.'},indent=2)+'\n')
 print('LIVE',d['child'],d['parent'],flush=True)
elif cmd=='observe':
 r=R/name;d=json.loads((r/'device-report.json').read_text());label=sys.argv[3];x,y=map(int,sys.argv[4:6]);pid=str(d['child'])
 def action(c):
  o=dev(c)
  with (r/(label+'-actions.jsonl')).open('a') as f:f.write(json.dumps({'epoch':time.time(),'command':c,'output':o})+'\n')
  return o
 def shot(tag):
  remote='/data/local/tmp/mc46.jpeg';action('cat /proc/uptime; snapshot_display -f '+remote+' >/dev/null; cat /proc/uptime')
  recv(remote,r/(label+'-'+tag+'.jpeg'));p=root/'preview'/name/(label+'-'+tag+'.jpeg');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/(label+'-'+tag+'.jpeg')).read_bytes())
 shot('before')
 log=d['runtime']+'/private-tmp/adapter_child_'+pid+'.stderr'
 start_line=int(dev('wc -l < '+log).strip())
 (r/(label+'-start-line.json')).write_text(json.dumps({'line':start_line})+'\n')
 (r/(label+'-input.txt')).write_text(action(f'echo INPUT_BEFORE; cat /proc/uptime; uinput -T -d {x} {y} -u {x} {y}; echo INPUT_AFTER; cat /proc/uptime'))
 begin=time.monotonic();pending=[15,90,125]
 while True:
  st=action('cat /proc/uptime; cat /proc/'+pid+'/stat 2>/dev/null')
  tasks=dev('for p in $(pidof '+PKG+'); do cat /proc/$p/stat /proc/$p/task/*/stat 2>/dev/null; done')
  with (r/(label+'-task-stats.jsonl')).open('a') as f:f.write(json.dumps({'epoch':time.time(),'tasks':tasks})+'\n')
  if ') ' not in st:print('EXIT_DURING_OBSERVATION',flush=True);break
  elapsed=time.monotonic()-begin
  if pending and elapsed>=pending[0]:
   deadline=pending.pop(0);shot('after'+str(deadline));print('SHOT',deadline,flush=True)
  if elapsed>=125:break
  time.sleep(3)
 collect(r,d)
 window='\n'.join((r/'child.stderr').read_text(errors='replace').splitlines()[start_line:])+'\n'
 (r/(label+'-window.stderr')).write_text(window)
 print('OBSERVATION_COMPLETE',flush=True)
elif cmd=='summary':
 r=R/name;d=json.loads((r/'device-report.json').read_text());collect(r,d);s=(r/'child.stderr').read_text(errors='replace');lines=s.splitlines()
 counts={'getOwnCodecInfo_no_implementation':sum('No implementation' in l and 'getOwnCodecInfo' in l for l in lines),'UnsatisfiedLinkError':s.count('UnsatisfiedLinkError'),'FATAL_lines':sum('FATAL' in l for l in lines if len(l)<3000),'SIGTRAP':s.count('Fatal signal 5'),'video_initialization_failed':s.count('Failed to initialize video/'),'GLES_translation':s.count('GLES library translated'),'GrGLInterface_failure':s.count('GrGLInterface creation failed'),'InitializeGL_failure':s.count('InitializeGL failure')}
 (r/'assertions.json').write_text(json.dumps(counts,indent=2)+'\n')
 markers=[l for l in lines if l.startswith(('[B47-SLA] ENTRY','[ABILITY38-RESUMED]')) or (len(l)<3000 and any(k in l for k in ['Failed to initialize video/','No implementation','UnsatisfiedLinkError','FATAL','Fatal signal']))]
 (r/'lifecycle-errors.txt').write_text('\n'.join(markers)+'\n');print(json.dumps(counts));print('\n'.join(markers)[-10000:])
