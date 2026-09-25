"""Fresh OH consent CPU profile; separate from all latency samples."""
from launch34 import *
name=sys.argv[1];origin=next(x.split('=',1)[1] for x in sys.argv if x.startswith('--origin='))
dev('power-shell dump -t; power-shell wakeup');dev('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1);dev('uinput -T -d 1150 1140 -u 1150 1140')
r,d=restart(name,origin);pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr';runtime=d['runtime']
def action(c,kind='observe',timeout=120):
 out=dev(c,timeout)
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps({'epoch':time.time(),'kind':kind,'command':c,'output':out})+'\n')
 return out
def shot(label):
 action('snapshot_display -f /data/local/tmp/ability38-profile.jpeg >/dev/null');recv('/data/local/tmp/ability38-profile.jpeg',r/(label+'.jpeg'))
print('CPU_PROFILE_LAUNCHED',name,pid,flush=True)
try:
 time.sleep(100)
 shot('consent-before')
 early=action('cat '+log)
 tid=int(re.search(r'\[TOUCH21-POLL\] enter now=\d+ tid=(\d+)',early)[1])
 (r/'main-thread.json').write_text(json.dumps({'pid':pid,'tid':tid,'identification':'first ActivityThread MessageQueue nativePollOnce; corroborate launch callchain and -4 nice'}))
 (r/'main-stat-before.txt').write_text(action(f'cat /proc/uptime; cat /proc/{pid}/task/{tid}/stat; getconf CLK_TCK'))
 (r/'maps-before.txt').write_text(action(f'cat /proc/{pid}/maps'))
 (r/'tasks-before.txt').write_text(action(f'cat /proc/{pid}/task/*/stat'))
 command=f'echo CONSENT_BEFORE; cat /proc/uptime; uinput -T -d 600 1273 -u 600 1273; echo PROFILE_BEFORE; cat /proc/uptime; /bin/hiperf record -p {pid} -d 10 -f 400 -e sw-task-clock -s dwarf,16384 --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 -o /data/local/tmp/ability38-cpu.data; echo PROFILE_RC=$?; echo PROFILE_AFTER; cat /proc/uptime'
 (r/'record.txt').write_text(action(command,'CPU_PROFILE_NOT_LATENCY',120))
 (r/'main-stat-after.txt').write_text(action(f'cat /proc/uptime; cat /proc/{pid}/task/{tid}/stat'))
 (r/'tasks-after.txt').write_text(action(f'cat /proc/{pid}/task/*/stat'))
 action('echo T > /data/local/tmp/noice_tap');time.sleep(1)
 shot('after-profile')
 recv('/data/local/tmp/ability38-cpu.data',r/'perf.data')
 (r/'report-all.txt').write_text(action(f'/bin/hiperf report -i /data/local/tmp/ability38-cpu.data --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 --sort tid,comm,dso,func --limit-percent 0',timeout=180))
 (r/'report-stacks.txt').write_text(action(f'/bin/hiperf report -i /data/local/tmp/ability38-cpu.data --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 --sort tid,comm,dso,func -s --limit-percent 0.1',timeout=180))
 (r/'report-main.txt').write_text(action(f'/bin/hiperf report -i /data/local/tmp/ability38-cpu.data --symbol-dir /data/local/tmp/a2hlab-framework-ability38-v7 --tids {tid} --sort tid,comm,dso,func --limit-percent 0',timeout=180))
 print('CPU_PROFILE_COLLECTED',name,flush=True)
finally:
 collect(r,d);stop(d)
