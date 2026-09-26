from pathlib import Path
import sys,json,time
op=sys.argv[1];args=sys.argv[2:];p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'validation','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];F='/data/local/tmp/operator45/selfheal48'
if op=='start':
 assert not dev('pidof com.ss.android.article.news appspawn-x',5).strip()
 print(dev('test ! -d '+F+'/lock || exit 9; rm -f '+F+'/stop; nohup /system/bin/sh '+F+'/watchdog.sh >'+F+'/guardian.log 2>&1 </dev/null & echo $!',5))
elif op=='status':
 s=dev('cat /proc/uptime; cat '+F+'/state '+F+'/instance.txt; echo APP_PIDS; pidof com.ss.android.article.news; echo PARENT_PIDS; pidof appspawn-x; tail -12 '+F+'/events.log; tail -3 '+F+'/metrics.log; tail -4 '+F+'/ui.log; tail -3 '+F+'/guardian.log',8)
 (r/('status-'+str(int(time.time()))+'.txt')).write_text(s);print(s)
elif op=='shot':x['shot'](args[0],8)
elif op in ('input','swipe','refresh','kill-test','crash-test'):
 s=dev('cat '+F+'/instance.txt',5);d=dict(l.split('=',1) for l in s.splitlines());st=x['state'](d['child']);assert st and st['alive'] and st['birth']==d['birth']
 if op=='input':
  assert len(args)==2 and all(a.isdigit() for a in args);cmd='uinput -T -d '+' '.join(args)+' -u '+' '.join(args)
 elif op=='swipe':cmd='uinput -T -m 600 1550 600 450 500'
 elif op=='refresh':cmd='uinput -T -m 600 500 600 1550 500'
 else:cmd=('kill -11 ' if op=='crash-test' else 'kill -9 ')+d['child']
 out=dev('cat /proc/uptime; '+cmd,5);record={'op':op,'instance':d,'output':out,'epoch':time.time(),'command':cmd}
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
 print(json.dumps(record))
elif op=='probe':
 d=dict(l.split('=',1) for l in dev('cat '+F+'/instance.txt',5).splitlines());pid=d['child'];s=dev("grep -E '^\\[B47-SLA\\] ENTRY|^\\[ABILITY38-RESUMED\\]|^Fatal signal|J_invokeStaticMain_main_threw|Layout: -79' "+x['rt']+'/private-tmp/adapter_child_'+pid+'.stderr | tail -30',10);(r/(args[0]+'-lifecycle.txt')).write_text(s);print(s)
elif op=='cleanup':
 assert 'STOPPED' in dev('test -f '+F+'/stop && test ! -d '+F+'/lock && echo STOPPED',5)
 d=dict(l.split('=',1) for l in dev('cat '+F+'/instance.txt',5).splitlines());print(x['cleanup'](d['parent'],d['child']))
elif op=='stop':print(dev('touch '+F+'/stop /data/local/tmp/operator45/stop /data/local/tmp/operator45/fresh48/stop',5))
else:raise SystemExit(op)
