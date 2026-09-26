from pathlib import Path
import sys,time
label=sys.argv[1];p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'validation','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];F='/data/local/tmp/operator45/selfheal48'
s=dev('cat /proc/uptime; cat '+F+'/state '+F+'/instance.txt; echo PROC_COUNTS; for p in $(pidof com.ss.android.article.news appspawn-x); do cat /proc/$p/stat; grep -E "^(Name|State|Pid|PPid|VmRSS):" /proc/$p/status; done; echo MEMORY; free -m; cat /proc/sys/vm/max_map_count; echo STOPS; ls -l /data/local/tmp/operator45/stop /data/local/tmp/operator45/fresh48/stop; echo LOCK; cat '+F+'/lock/owner; echo SECOND_GUARD; /system/bin/sh '+F+'/watchdog.sh; echo second_guard_rc=$?; echo PROFILES; ls -ld '+x['rt']+'/operator-selfheal-*; echo GUARD_SHA; sha256sum '+F+'/watchdog.sh',10)
(r/(label+'-audit.txt')).write_text(s);print(s)
