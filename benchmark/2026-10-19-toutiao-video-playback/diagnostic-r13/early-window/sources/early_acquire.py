from pathlib import Path
import sys,os,json,time,subprocess,shlex
repo=Path.cwd();base=Path.home()/'.local/share/westlake/toutiao-resume-20261020'
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
sys.path.insert(0,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13'));from core import *
boot=sys.argv[1];out=base/'r13-early-readiness';out.mkdir(exist_ok=False)
board=b.Board(SERIAL,'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=boot;board.ready()
a=json.loads((base/'r13-admission-template.json').read_text());deadline=time.monotonic()+30;chosen=None;ident=None
def read(c):
 remaining=deadline-time.monotonic();need(remaining>0,'readiness deadline');return board.shell(c,timeout=remaining)[1]
try:
 while time.monotonic()<deadline:
  ps=read('ps -A -o PID,PPID,UID,NAME');rows=[l.split() for l in ps.splitlines() if len(l.split())==4 and l.split()[2]=='20011206' and l.split()[3]=='id.article.news']
  need(len(rows)<=1,'ambiguous business children')
  if rows:
   child=int(rows[0][0]);parent=int(rows[0][1]);cs=stat_fields(read('cat /proc/%d/stat'%child));pss=stat_fields(read('cat /proc/%d/stat'%parent));current=(parent,pss['birth'],child,cs['birth'])
   if chosen is None:chosen=current
   need(chosen==current,'child identity changed');need(cs['ppid']==parent,'parent mismatch')
   status=read('cat /proc/%d/status'%child);need('\nTracerPid:\t0\n' in status,'tracer')
   maps=parse_maps(read('cat /proc/%d/maps'%child))
   if all(any(r['path']==m['remote_path'] for r in maps) for m in a['modules'].values()):
    for pid in [parent,child]:need(read('sha256sum /proc/%d/exe'%pid).split()[0]==EXE_SHA,'exe')
    inst={}
    for role,m in a['modules'].items():
     p='/proc/%d/root%s'%(child,m['remote_path']);need(read('sha256sum '+p).split()[0]==m['sha256'],'moduleSHA '+role);m['device'],m['inode']=map(int,read('stat -L -c %d:%i '+p).strip().split(':'));inst[role]=biases(maps,m)
    need(len(inst['player'])==1,'ambiguous player');need(time.monotonic()<deadline,'readiness deadline after modules');ident={'boot':boot,'parent':parent,'parent_birth':pss['birth'],'child':child,'child_birth':cs['birth'],'instances':inst};(out/'ready.json').write_text(json.dumps(ident,indent=2));break
  elif chosen is not None:raise Refuse('selected child disappeared')
  time.sleep(1)
 need(ident is not None and time.monotonic()<deadline,'one-child readiness deadline')
 cmd=[sys.executable,str(base/'r13_early_outer.py'),'attach',boot,*map(str,chosen)]
 with (out/'attach.stdout').open('wb') as so,(out/'attach.stderr').open('wb') as se:p=subprocess.run(cmd,stdout=so,stderr=se,timeout=35)
 (out/'attach.rc').write_text(str(p.returncode));need(p.returncode==0,'attach failed')
 cmd=[sys.executable,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/observe.py'),'--admission',str(base/'r13-early-admission.json'),'--port','5039','--out',str(base/'r13-early-observer'),'--execute']
 with (out/'observe.stdout').open('wb') as so,(out/'observe.stderr').open('wb') as se:p=subprocess.run(cmd,stdout=so,stderr=se,timeout=165)
 (out/'observe.rc').write_text(str(p.returncode));print('observer rc',p.returncode);need(p.returncode==0,'observer did not complete event budget; outer restoration required')
except Exception as e:
 (out/'failure.json').write_text(json.dumps({'error':str(e),'chosen':chosen,'time':time.time(),'requires_outer_restore':True},indent=2));raise
