from pathlib import Path
import sys
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'final-check','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x);x['r'].mkdir(exist_ok=True)
s=x['dev']('cat /proc/uptime; echo APP_PIDS; pidof com.ss.android.article.news; echo PARENT_PIDS; pidof appspawn-x; echo GUARD; test -f /data/local/tmp/operator45/stop && echo LEGACY_STOP; test -f /data/local/tmp/operator45/fresh48/stop && echo FRESH_STOP; test ! -d /data/local/tmp/operator45/fresh48/lock && echo NO_GUARD_LOCK; echo MEMORY; free -m; echo MAP_COUNT; cat /proc/sys/vm/max_map_count; sha256sum '+x['rt']+'/lib/arm64-v8a/libnpth.so '+x['rt']+'/webview-t-lib/libwebview_bionic_shim.so',10)
(x['r']/'board-state.txt').write_text(s);print(s)
assert not s.split('APP_PIDS\n')[1].split('PARENT_PIDS')[0].strip()
assert not s.split('PARENT_PIDS\n')[1].split('GUARD')[0].strip()
assert all(v in s for v in ['LEGACY_STOP','FRESH_STOP','NO_GUARD_LOCK'])
