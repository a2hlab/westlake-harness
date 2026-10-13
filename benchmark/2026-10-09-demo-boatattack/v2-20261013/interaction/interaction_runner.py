#!/usr/bin/env python3
"""Exact Boat evidence only; default preview, no deploy/reboot/install/repair."""
import argparse,hashlib,importlib.util,json,os,re,shlex,time,uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',HERE.parents[4])).resolve()
SERIALS={'5ea34a4500000000000000001123012c','5cd1e3dd00000000000000000923012c','61b0657200000000000000000324012c'}
PKG='com.Unity3d.BoatAttackDay';ABILITY='com.unity3d.player.UnityPlayerActivity'
TOUCHES=[('accelerate','uinput -T -d 1740 1100 -i 9000 -u 1740 1100'),('left','uinput -T -m 220 1000 70 1000 -k 5000 700'),('accelerate','uinput -T -d 1740 1100 -i 9000 -u 1740 1100'),('right','uinput -T -m 220 1000 370 1000 -k 5000 700'),('reset','uinput -T -c 1440 1100 200')]
ASSETS={'/system/android/lib64/liboh_android_runtime.so':'18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae','/system/android/lib64/liboh_adapter_bridge.so':'8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e','/system/android/framework/oh-adapter-runtime.jar':'6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852'}
for name,sha in {'libunity.so':'1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac','libil2cpp.so':'f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746','libwestlake_bionic_signal_box.so':'7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da'}.items():ASSETS['/data/app/el1/bundle/public/'+PKG+'/android/lib/arm64-v8a/'+name]=sha
DONORS={'rehearsal':('westlake-harness-t3/benchmark/2026-10-11-boat-autostart-seal/rehearsal_runner.py','39e18712c342ba29312d07fd631fbca8a2541efe780a901e86b0741d6d2b3ff7'),'keeper':('westlake-harness-t3/benchmark/2026-10-11-boat-window9/onscreen_keeper.sh','a55ebc4c50092a59dc0a0cf2c68ed91312d034fd619d388451a0c7170937c83d'),'batch':('westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py','f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c')}

def need(ok,why):
 if not ok:raise ValueError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,indent=2)+'\n')
def donors():
 found={}
 for key,(relative,digest) in DONORS.items():
  p=WS/relative;need(p.is_file() and sha(p)==digest,'donor drift: '+key);found[key]=p
 return found
def admit(plan,auth,plan_sha):
 need(plan.get('execution_enabled') is True,'preview plan is disabled')
 need(plan.get('serial') in SERIALS and re.fullmatch(r'[0-9a-f-]{36}',plan.get('boot_id','')),'serial/boot missing')
 need(re.fullmatch(r'[A-Za-z0-9_.()_-]+',plan.get('owner','')),'exact owner missing')
 need(type(plan.get('uid')) is int and plan['uid']>10000,'actual BMS uid missing')
 need(60<=plan.get('max_runtime_seconds',0)<=240,'bounded duration required')
 need(auth.get('approved_by')=='outer(codex)' and auth.get('action')=='boat-interaction','outer action missing')
 need(auth.get('plan_sha256')==plan_sha and auth.get('runner_sha256')==sha(__file__),'authorization pins differ')
 need(auth.get('serial')==plan['serial'] and auth.get('owner')==plan['owner'] and auth.get('boot_id')==plan['boot_id'],'authorization identity differs')
 need(type(auth.get('expires_epoch')) in (int,float) and auth['expires_epoch']>time.time(),'authorization expired')
 need(auth.get('spare_board_authorized') is True,'separate spare-board window required')
 need(Path(plan.get('hdc','')).is_file(),'explicit local HDC missing')

def jpeg_size(path):
 data=Path(path).read_bytes();need(data[:2]==b'\xff\xd8','screenshot not JPEG');i=2
 while i<len(data):
  need(data[i]==255,'bad JPEG marker');i+=1
  while i<len(data) and data[i]==255:i+=1
  marker=data[i];i+=1
  if marker in (0xD8,0xD9):continue
  n=int.from_bytes(data[i:i+2],'big');need(n>=2,'bad JPEG segment')
  if marker in (0xC0,0xC1,0xC2):return int.from_bytes(data[i+5:i+7],'big'),int.from_bytes(data[i+3:i+5],'big')
  i+=n
 raise ValueError('JPEG dimensions missing')

def target_window(dump,pid):
 rows=[]
 for line in dump.splitlines():
  x=line.split()
  if len(x)<16 or not all(re.fullmatch(r'-?\d+',x[j]) for j in [1,2,3,7]):continue
  if int(x[2])!=pid or not PKG.startswith(x[0]) or len(x[0])<12:continue
  need(x[9]=='[' and x[14]==']','WMS target geometry malformed')
  geometry=list(map(int,x[10:14]));need(geometry==[0,0,1920,1200],'target window geometry differs')
  rows.append({'name':x[0],'pid':pid,'window_id':int(x[3]),'zorder':int(x[7]),'geometry':geometry})
 need(len(rows)==1,'unique Boat-owned target window not observed')
 match=re.search(r'(?m)^Focus window:\s*(\d+)\s*$',dump)
 rows[0]['focus_matches']=bool(match and int(match[1])==rows[0]['window_id'])
 # ZOrd/focus are advisory: historical window9 has actual game while target ZOrd=-1.
 return rows[0]

def proc_identity(board,pid,uid):
 _,raw=board.shell('cat /proc/%d/stat'%pid);part=raw.rsplit(') ',1)[1].split();need(len(part)>19,'short proc stat')
 need(part[0] not in ('Z','X'),'child exited');ppid=int(part[1]);birth=int(part[19])
 _,status=board.shell('cat /proc/%d/status'%pid);m=re.search(r'(?m)^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',status)
 need(m and tuple(map(int,m.groups()))==(uid,uid,uid,uid),'child UID mismatch')
 _,parent_exe=board.shell('readlink /proc/%d/exe'%ppid);need(parent_exe.strip()=='/system/bin/appspawn-x','not system Boat parent')
 _,parent_stat=board.shell('cat /proc/%d/stat'%ppid);parent_birth=int(parent_stat.rsplit(') ',1)[1].split()[19])
 return {'pid':pid,'birth':birth,'ppid':ppid,'parent_birth':parent_birth,'uid':uid}

def run(plan,out,found,authority=None):
 # Import original rehearsal to obtain its exact B.Board/B.capture/parse_bundle path; no seal/unseal or raw helper called.
 old_workspace=os.environ.get('WORKSPACES');os.environ['WORKSPACES']=str(WS)
 spec=importlib.util.spec_from_file_location('boat_rehearsal_donor',found['rehearsal']);R=importlib.util.module_from_spec(spec)
 try:spec.loader.exec_module(R)
 finally:
  if old_workspace is None:os.environ.pop('WORKSPACES',None)
  else:os.environ['WORKSPACES']=old_workspace
 B=R.B
 b=B.Board(plan['serial'],plan['hdc'],str(WS/'westlake-inputs/tools/board_note.sh'),plan['owner'],out/'commands')
 remote='/data/local/tmp/boat-interaction-'+uuid.uuid4().hex;start=time.monotonic();identity=None;dir_inode=None;cleanup_deadline=None
 # Bound every donor transport call, including ready(), capture() and receive().
 original_command=b.command
 def bounded_command(argv,timeout=60):
  deadline=cleanup_deadline if cleanup_deadline is not None else start+plan['max_runtime_seconds']
  remaining=deadline-time.monotonic();need(remaining>0,'transport budget exhausted')
  return original_command(argv,min(timeout,remaining))
 b.command=bounded_command
 rec={'schema':'boat-interaction-evidence/v1','serial':plan['serial'],'boot_id':plan['boot_id'],'owner':plan['owner'],'status':'STARTING','images':{},'inputs':[],'cleanup':{},'accepted':False,'runtime_changes':False}
 def context(cleanup=False):
  if cleanup:
   need(cleanup_deadline is not None and time.monotonic()<cleanup_deadline,'cleanup deadline reached')
  else:
   need(time.monotonic()-start<plan['max_runtime_seconds'],'interaction deadline reached')
   need(authority is None or time.time()<authority['expires_epoch'],'window authority expired')
  b.ready();need(b.boot.strip()==plan['boot_id'],'boot changed')
 def guard():
  context();now=proc_identity(b,identity['pid'],plan['uid']);need(now==identity,'child PID/birth/parent changed');return now
 def shot(tag,cleanup=False):
  context(cleanup);p=out/(tag+'.jpeg');info=B.capture(b,remote+'/'+tag+'.jpeg',p);info['elapsed_seconds']=time.monotonic()-start
  if 'click_monotonic' in rec:info['since_icon_click_seconds']=time.monotonic()-rec['click_monotonic']
  rec['images'][tag]=info;save(out/'record.json',rec)
  info['dimensions']=jpeg_size(p);save(out/'record.json',rec)
 def window(tag):
  guard();_,dump=b.shell("hidumper -s WindowManagerService -a '-a'");(out/('wms-'+tag+'.txt')).write_text(dump);return target_window(dump,identity['pid'])
 def child_view():
  guard();seen={}
  for target,want in ASSETS.items():
   _,text=b.shell('sha256sum '+shlex.quote('/proc/%d/root'%identity['pid']+target));tokens=text.split();seen[target]=tokens[0] if tokens else None
  save(out/'child-view.json',seen);need(seen==ASSETS,'child-view stock187/adapter8ab/JAR633/private3 mismatch')
 try:
  context();_,text=b.shell('bm dump -n '+PKG);(out/'bundle.txt').write_text(text);bundle=B.parse_bundle(text,PKG);need(bundle['uid']==plan['uid'],'installed Boat UID differs')
  _,text=b.shell('sha256sum /data/app/el1/bundle/public/'+PKG+'/android/base.apk');need(text.split()[0]=='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444','installed APK differs')
  b.shell('mkdir -m 700 '+remote);b.shell('printf %s '+shlex.quote(plan['owner'])+' > '+remote+'/owner');_,dir_inode=b.shell('stat -c %d:%i '+remote);dir_inode=dir_inode.strip()
  b.send(found['keeper'],remote+'/keeper.sh');_,readback=b.shell('sha256sum '+remote+'/keeper.sh');need(readback.split()[0]==DONORS['keeper'][1],'keeper transfer mismatch')
  b.shell('KDIR='+remote+' INTERVAL=5 nohup sh '+remote+'/keeper.sh > '+remote+'/keeper-transport.log 2>&1 < /dev/null &')
  rec['launch_method']='desktop';B.desktop_launch(b,{'package':PKG,'launch_activity':bundle.get('desktop_activity') or ABILITY},remote,out,rec);time.sleep(max(0,12-(time.monotonic()-rec['click_monotonic'])))
  context();_,ps=b.shell('ps -A -o PID,PPID,UID,NAME');(out/'ps-launch.txt').write_text(ps)
  candidates=[]
  for row in B.processes(ps):
   if row['uid']==plan['uid']:
    try:candidates.append(proc_identity(b,row['pid'],plan['uid']))
    except ValueError:pass
  need(len(candidates)==1,'unique Boat child not ready');identity=candidates[0];rec['child']=identity;child_view()
  for t in (15,30,45):
   time.sleep(max(0,t-(time.monotonic()-rec['click_monotonic'])));shot('t'+str(t))
   try:rec['images']['t'+str(t)]['target_window']=window('t'+str(t))
   except Exception as e:rec['images']['t'+str(t)]['wms_diagnostic_error']=str(e)
   save(out/'record.json',rec)
  for n,(name,cmd) in enumerate(TOUCHES,1):
   shot('touch-%d-before'%n);rec['target_window']=window('touch-%d'%n);need(rec['target_window']['focus_matches'],'input target focus unconfirmed; refuse touch, preserve capture');need(rec['images']['touch-%d-before'%n]['dimensions']==(1920,1200),'pre-touch screenshot geometry differs')
   guard();rc,text=b.shell(cmd,required=False);row={'index':n,'name':name,'command':cmd,'injection_rc':rc,'response':text,'visual_response':'pending_human'};rec['inputs'].append(row);save(out/'record.json',rec);need(rc==0,'input command failed');time.sleep(2 if n==5 else 0);guard();shot('touch-%d-after'%n)
  child_view();rec['status']='CAPTURED_PENDING_HUMAN'
 except Exception as error:
  rec['status']='FAILED_EVIDENCE_RETAINED';rec['error']=str(error)
 finally:
  cleanup_deadline=time.monotonic()+90
  # No cold_stop, process signal, uninstall, runtime mount, reset logs or repair. Retain originals even after failure.
  for name,command in [('hilog-final','hilog -x'),('ps-final','ps -A -o PID,PPID,UID,NAME'),('faultlog-list','ls -lt /data/log/faultlog/faultlogger 2>/dev/null')]:
   try:context(True);_,raw=b.shell(command,required=False,timeout=max(1,min(45,cleanup_deadline-time.monotonic())));(out/(name+'.txt')).write_text(raw)
   except Exception as e:rec['cleanup'][name+'_error']=str(e)
  try:shot('final',cleanup=True)
  except Exception as e:rec['cleanup']['final_capture_error']=str(e)
  if dir_inode:
   try:
    context(True);_,actual=b.shell('stat -c %d:%i '+remote);_,owner=b.shell('cat '+remote+'/owner');need(actual.strip()==dir_inode and owner==plan['owner'],'keeper directory owner changed')
    # Only this fresh keeper's cooperative stop. Never pid/name-based kill.
    b.shell('touch '+remote+'/keeper.stop');rec['cleanup']['keeper_stop_requested']=True
   except Exception as e:rec['cleanup']['keeper_stop_error']=str(e)
  rec['elapsed_seconds']=time.monotonic()-start;save(out/'record.json',rec)
 return 0 if rec['status']=='CAPTURED_PENDING_HUMAN' else 2

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--authorization',type=Path);p.add_argument('--authorization-sha256');a=p.parse_args();plan=json.loads(a.plan.read_text());found=donors()
 if not a.execute:print(json.dumps({'status':'PREVIEW_ONLY','plan_sha256':sha(a.plan),'runner_sha256':sha(__file__),'touches':TOUCHES,'child_view':ASSETS,'board_commands':0,'requires':'separate root spare-window auth; staged overlay/APK/sandbox already in place'},indent=2));return 0
 need(a.authorization is not None and sha(a.authorization)==a.authorization_sha256,'explicit authorization pin required');auth=json.loads(a.authorization.read_text());admit(plan,auth,sha(a.plan));need(not a.out.exists() and not a.out.is_symlink() and a.out.parent.is_dir(),'fresh output required');a.out.mkdir();return run(plan,a.out,found,auth)
if __name__=='__main__':raise SystemExit(main())
