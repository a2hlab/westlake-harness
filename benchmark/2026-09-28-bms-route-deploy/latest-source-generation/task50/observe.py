#!/usr/bin/env python3
"""Run on the VM: sequential, locked 5ea desktop launch observation only."""
import json,sys,time,shlex,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent.parent/'batch'))
import bms_batch as b
SERIAL='5ea34a4500000000000000001123012c'
parser=argparse.ArgumentParser()
parser.add_argument('--run',default='b6-musl-fixed-5ea')
parser.add_argument('--case',action='append',help='key:package; defaults to Wikipedia and HelloWorld')
args=parser.parse_args()
RUN=args.run
DEPLOY=json.loads((ROOT/'deployment.json').read_text())
assert not DEPLOY.get('rolled_back')
GEN=DEPLOY['generation']
PARENT=DEPLOY['parent_pid']
if not all(c.isalnum() or c in '-_' for c in RUN):raise ValueError('invalid run id')
out=Path.home()/'a2hlab/board'/RUN
out.mkdir(parents=True,exist_ok=False)
board=b.Board(SERIAL,str(Path(__file__).resolve().parents[4].parent/'westlake-inputs/tools/hdc_mac.sh'),'mac '+str(Path(__file__).resolve().parents[4].parent/'westlake-inputs/tools/board_note.sh'),'cx-t0',out/'commands')
board.ready()
identity=f"cat /proc/sys/kernel/random/boot_id; sha256sum /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so /system/android/framework/oh-adapter-runtime.jar /system/android/lib64/liboh_android_runtime.so /system/android/framework/framework.jar /system/android/framework/arm64/boot-framework.oat /system/lib64/westlake/route-a/{GEN}/libsigchain.so; ps -A -o PID,PPID,UID,NAME"
_,before=board.shell(identity);(out/'identity-before.txt').write_text(before)
_,mounts=board.shell('cat /proc/self/mountinfo');(out/'shell-mountinfo.txt').write_text(mounts)
results=[]
for key,pkg in ([x.split(':',1) for x in args.case] if args.case else [('wikipedia','org.wikipedia'),('helloworld','com.example.helloworld')]):
 d=out/key;d.mkdir();remote='/data/local/tmp/'+RUN+'/'+key
 board.shell('mkdir -p '+remote)
 _,bundle=board.shell('bm dump -n '+pkg);(d/'bundle.txt').write_text(bundle)
 parsed=b.parse_bundle(bundle,pkg);uid=parsed['uid']
 rec={'key':key,'package':pkg,'serial':SERIAL,'boot_id':board.boot,'bms':parsed,'clicked':False,'started_at':time.time()}
 _,paths=board.shell('ls -laZ /data/app/android/'+pkg+' /data/app/el1/bundle/public/'+pkg+'/android; find /data/app/android/'+pkg+' -maxdepth 3 -type f 2>/dev/null; true')
 (d/'paths-before.txt').write_text(paths)
 _,faults=board.shell('ls -l /data/log/faultlog/faultlogger /data/log/faultlog/temp 2>/dev/null; true');(d/'faults-before.txt').write_text(faults)
 _,flist=board.shell('find /data/log/faultlog -maxdepth 2 -type f 2>/dev/null; true');old=set(flist.splitlines())
 if not b.cold_stop(board,pkg,uid,d):raise RuntimeError('cold stop not proven')
 original=board.shell
 def launch_hook(command,required=True,timeout=60):
  if command.startswith('uitest uiInput click ') and rec.get('selected_icon'):
   script=f'''hilog -r > {remote}/hilog-clear.txt 2>&1
hilog > {remote}/hilog.txt 2>&1 &
hilog_pid=$!
(
 n=0
 while [ "$n" -lt 180 ]; do
  read up unused < /proc/uptime
  echo "T $up"
  ps -A -o PID,PPID,UID,NAME | while read p pp u name; do
   if [ "$u" = "{uid}" ]; then
    echo "P $p $pp $u $name"
    if [ "$pp" = "{PARENT}" ] && [ ! -e {remote}/child-proof-$p.started ]; then
     touch {remote}/child-proof-$p.started
     (cat /proc/$p/maps > {remote}/child-proof-$p.maps; sha256sum /proc/$p/exe /proc/$p/root/system/lib64/appspawn/libwestlake_android_child.z.so /proc/$p/root/system/android/lib64/liboh_adapter_bridge.so /proc/$p/root/system/android/lib64/liboh_android_runtime.so /proc/$p/root/system/android/framework/framework.jar /proc/$p/root/system/android/framework/arm64/boot-framework.oat /proc/$p/root/system/android/framework/oh-adapter-runtime.jar /proc/$p/root/system/lib64/westlake/route-a/{GEN}/libsigchain.so > {remote}/child-proof-$p.sha256) &
     (
      j=0
      while [ "$j" -lt 100 ] && [ -d /proc/$p ]; do
       if grep -q 'libsigchain.so' /proc/$p/maps; then
        cat /proc/$p/maps > {remote}/child-proof-$p.late-maps
        sha256sum /proc/$p/exe /proc/$p/root/system/lib64/appspawn/libwestlake_android_child.z.so /proc/$p/root/system/lib64/westlake/route-a/{GEN}/libart.so /proc/$p/root/system/lib64/westlake/route-a/{GEN}/libsigchain.so > {remote}/child-proof-$p.late-sha256
        break
       fi
       j=$((j+1))
       sleep 0.01
      done
     ) &
    fi
    cat /proc/$p/stat 2>/dev/null
   fi
  done
  n=$((n+1))
  sleep 0.1
 done
) > {remote}/timeline.txt 2>&1 &
sampler_pid=$!
cat /proc/uptime > {remote}/click-before.txt
{command}
cat /proc/uptime > {remote}/click-after.txt
sleep 3
snapshot_display -f {remote}/t3.jpeg > {remote}/snapshot3.txt 2>&1
sleep 12
snapshot_display -f {remote}/final.jpeg > {remote}/snapshot-final.txt 2>&1
kill "$sampler_pid" "$hilog_pid" 2>/dev/null
wait "$sampler_pid" 2>/dev/null
wait "$hilog_pid" 2>/dev/null
true'''
   return original(script,required=required,timeout=65)
  return original(command,required=required,timeout=timeout)
 board.shell=launch_hook
 try:b.desktop_launch(board,{'package':pkg,'launch_activity':parsed['desktop_activity']},remote,d,rec)
 finally:board.shell=original
 for name in ['hilog-clear.txt','hilog.txt','timeline.txt','click-before.txt','click-after.txt','t3.jpeg','final.jpeg','snapshot3.txt','snapshot-final.txt']:
  board.receive(remote+'/'+name,d/name)
 _,proofs=board.shell('find '+remote+' -maxdepth 1 -name \"child-proof-*\" -type f');
 for proof in proofs.splitlines():
  if proof.startswith(remote+'/child-proof-'):board.receive(proof,d/Path(proof).name)
 _,ps=board.shell('ps -A -o PID,PPID,UID,NAME');(d/'processes-after.txt').write_text(ps)
 target=[r for r in b.processes(ps) if r['uid']==uid];rec['pids_after']=[r['pid'] for r in target]
 for row in target:
  for file in ['mountinfo','maps','status']:
   _,text=board.shell(f'cat /proc/{row["pid"]}/{file}',required=False);(d/f'child-{row["pid"]}-{file}.txt').write_text(text)
 _,faults=board.shell('ls -l /data/log/faultlog/faultlogger /data/log/faultlog/temp 2>/dev/null; true');(d/'faults-after.txt').write_text(faults)
 _,flist=board.shell('find /data/log/faultlog -maxdepth 2 -type f 2>/dev/null; true');new=set(flist.splitlines())-old
 rec['new_faults']=sorted(new)
 for file in sorted(new):
  if file.startswith('/data/log/faultlog/'):
   _,txt=board.shell('cat '+shlex.quote(file),required=False);(d/('fault-'+Path(file).name+'.txt')).write_text(txt)
 rec['finished_at']=time.time();b.save(d/'record.json',rec);results.append(rec)
 print(key,rec['pids_after'],rec['new_faults'],flush=True)
_,after=board.shell(identity);(out/'identity-after.txt').write_text(after)
b.save(out/'results.json',{'serial':SERIAL,'boot_id':board.boot,'trials':results})
print(out,flush=True)
