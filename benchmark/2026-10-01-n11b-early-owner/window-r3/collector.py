"""Continuous guarded hilog plus near-launch proc/fault snapshots; no native changes."""
import argparse,importlib.util,json,os,shlex,subprocess,sys,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths
SERIAL='61b0657200000000000000000324012c'
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def run(root):
 root.mkdir(parents=True,exist_ok=True)
 source=lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
 spec=importlib.util.spec_from_file_location('trusted_n11b_collector',source);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 hdc=shutil_which_hdc();board=b.Board(SERIAL,hdc,str(lab_paths.tools()/'board_note.sh'),'cx-t0',root/'commands');board.ready()
 board.shell('hilog -G 16M; hilog -p off; hilog -r')
 _,settings=board.shell('hilog -g; param get hilog.private.on; date; cat /proc/uptime')
 (root/'hilog-settings.txt').write_text(settings)
 if settings.count('16.0M')<3:raise RuntimeError('three hilog buffers not 16M')
 remote='/data/local/tmp/n11b-r3-collector-'+uuid.uuid4().hex
 board.shell('mkdir '+remote)
 watcher=r'''stop=$1
seen=' '
known=" $(ls /data/log/faultlog/faultlogger 2>/dev/null) "
i=0
printf 'WATCH_BEGIN epoch=%s pid=%s\n' "$(date +%s)" "$$"
while [ ! -e "$stop" ] && [ "$i" -lt 36000 ]; do
 for p in $(pidof appspawn-x); do
  case "$seen" in *" $p "*) fresh=0;; *) fresh=1;seen="$seen$p ";; esac
  if [ "$fresh" = 1 ] || [ $((i % 20)) = 0 ]; then
   printf '\nMAPS_BEGIN pid=%s epoch=%s uptime=%s fresh=%s\n' "$p" "$(date +%s)" "$(cat /proc/uptime)" "$fresh"
   cat /proc/$p/status /proc/$p/stat /proc/$p/maps 2>&1
   printf 'MAPS_END pid=%s\n' "$p"
  fi
 done
 if [ $((i % 20)) = 0 ]; then
  for f in /data/log/faultlog/faultlogger/*; do
   [ -f "$f" ] || continue
   n=${f##*/}
   case "$known" in *"$n"*) continue;; esac
   known="$known $n "
   printf '\nFAULT_BEGIN file=%s epoch=%s\n' "$f" "$(date +%s)"
   cat "$f"
   printf 'FAULT_END file=%s\n' "$f"
  done
 fi
 i=$((i+1))
 sleep 0.05
done
printf 'WATCH_END epoch=%s\n' "$(date +%s)"
'''
 script=root/'watch.sh';script.write_text(watcher);board.send(script,remote+'/watch.sh')
 processes=[];files=[];start=time.time()
 try:
  for name,command in [('hilog','hilog -v time'),('proc-fault','sh '+shlex.quote(remote+'/watch.sh')+' '+shlex.quote(remote+'/stop'))]:
   fh=(root/(name+'.txt')).open('wb');err=(root/(name+'.stderr.txt')).open('wb');files += [fh,err]
   proc=subprocess.Popen([hdc,'-t',SERIAL,'shell',command],stdout=fh,stderr=err);processes.append(proc)
  time.sleep(2)
  if any(p.poll() is not None for p in processes):raise RuntimeError('continuous capture transport exited before launch')
  save(root/'ready.json',{'started_epoch':start,'boot_id':board.boot,'remote':remote,'pids':[p.pid for p in processes],'hilog_reset_before_launch':True})
  while not (root/'stop.flag').exists() and time.time()-start<1800:
   if any(p.poll() is not None for p in processes):raise RuntimeError('capture transport exited during evidence interval')
   time.sleep(.2)
 finally:
  # Stop only this collector's private watcher; preserve every evidence file.
  try:board.shell(': > '+remote+'/stop')
  except Exception as exc:(root/'stop-error.txt').write_text(str(exc))
  time.sleep(.3)
  for proc in processes:
   if proc.poll() is None:proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
  for fh in files:fh.close()
  save(root/'done.json',{'started_epoch':start,'finished_epoch':time.time(),'boot_id':board.boot,'returncodes':[p.returncode for p in processes]})
def shutil_which_hdc():
 import shutil
 value=shutil.which('hdc')
 if not value:raise RuntimeError('Mac DevEco hdc unavailable')
 return value
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
 try:run(a.root)
 except Exception as exc:
  if not (a.root/'done.json').exists():save(a.root/'done.json',{'failed_before_stream_start':True,'error':str(exc),'finished_epoch':time.time()})
  raise
