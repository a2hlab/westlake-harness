#!/usr/bin/env python3
"""Run on the VM: sequential, locked 5ea desktop launch observation only."""
import json,sys,time,shlex
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'batch'))
import bms_batch as b
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/lab'));import lab_paths  # <repo>/scripts/lab
SERIAL='5ea34a4500000000000000001123012c'
RUN='spawn-ab-20260928T1828'
out=Path.home()/'a2hlab/board'/RUN
out.mkdir(parents=True,exist_ok=False)
board=b.Board(SERIAL,str(lab_paths.tools()/'hdc_mac.sh'),'mac '+str(lab_paths.tools()/'board_note.sh'),'cx-t0',out/'commands')
board.ready()
identity="cat /proc/sys/kernel/random/boot_id; sha256sum /system/bin/appspawn-x /system/lib64/appspawn/libwestlake_android_child.z.so /system/android/framework/oh-adapter-runtime.jar /system/android/lib64/liboh_android_runtime.so; ps -A -o PID,PPID,UID,NAME"
_,before=board.shell(identity);(out/'identity-before.txt').write_text(before)
_,mounts=board.shell('cat /proc/self/mountinfo');(out/'shell-mountinfo.txt').write_text(mounts)
results=[]
for key,pkg in [('helloworld','com.example.helloworld'),('wikipedia','org.wikipedia')]:
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
sleep 1
snapshot_display -f {remote}/t1.jpeg > {remote}/snapshot1.txt 2>&1
sleep 14
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
 for name in ['hilog-clear.txt','hilog.txt','timeline.txt','click-before.txt','click-after.txt','t1.jpeg','final.jpeg','snapshot1.txt','snapshot-final.txt']:
  board.receive(remote+'/'+name,d/name)
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
