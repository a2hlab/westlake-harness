from pathlib import Path
import sys,json,time
op=sys.argv[1];args=sys.argv[2:];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'guardian-test','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];F='/data/local/tmp/operator45/fresh48'
if op=='start':
 s=dev('pidof com.ss.android.article.news appspawn-x',5);assert not s.strip(),s
 s=dev('test ! -d '+F+'/lock || exit 9; rm -f '+F+'/stop; nohup /system/bin/sh '+F+'/fresh-watchdog.sh > '+F+'/guardian.log 2>&1 </dev/null & echo $!',5);(r/'guardian.pid').write_text(s);print(s)
elif op=='status':
 s=dev('cat /proc/uptime; cat '+F+'/state '+F+'/instance.txt; echo APP_PIDS; pidof com.ss.android.article.news; echo PARENT_PIDS; pidof appspawn-x; tail -8 '+F+'/events.log; tail -4 '+F+'/ui.log; tail -5 '+F+'/guardian.log',5);(r/'status-latest.txt').write_text(s);print(s)
elif op=='shot':
 x['shot'](args[0],5)
elif op in ('input','kill-test'):
 s=dev('cat '+F+'/instance.txt',5);d=dict(l.split('=',1) for l in s.splitlines());st=x['state'](d['child']);assert st and st['alive'] and st['birth']==d['birth']
 if op=='input':
  assert len(args)==2 and all(a.isdigit() for a in args);cmd='uinput -T -d '+' '.join(args)+' -u '+' '.join(args)
 else:cmd='kill -9 '+d['child']
 out=dev('cat /proc/uptime; '+cmd,5);record={'op':op,'instance':d,'output':out,'epoch':time.time(),'command':cmd}
 with (r/'actions.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
 print(json.dumps(record))
elif op=='stop':
 print(dev('touch '+F+'/stop /data/local/tmp/operator45/stop',5))
else:raise SystemExit(op)
