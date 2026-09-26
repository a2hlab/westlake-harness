from pathlib import Path
import sys
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'final-check','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x);x['r'].mkdir(exist_ok=True)
s=x['dev']('cat /proc/uptime; echo APP_PIDS; pidof com.ss.android.article.news; echo PARENT_PIDS; pidof appspawn-x; echo GUARD; test -f /data/local/tmp/operator45/stop && echo LEGACY_STOP; test -f /data/local/tmp/operator45/fresh48/stop && echo FRESH_STOP; test ! -d /data/local/tmp/operator45/fresh48/lock && echo NO_GUARD_LOCK; echo MEMORY; free -m; echo MAP_COUNT; cat /proc/sys/vm/max_map_count; sha256sum '+x['rt']+'/lib/arm64-v8a/libnpth.so '+x['rt']+'/webview-t-lib/libwebview_bionic_shim.so',10)
(x['r']/'board-state.txt').write_text(s);print(s)
assert not s.split('APP_PIDS\n')[1].split('PARENT_PIDS')[0].strip()
assert not s.split('PARENT_PIDS\n')[1].split('GUARD')[0].strip()
assert all(v in s for v in ['LEGACY_STOP','FRESH_STOP','NO_GUARD_LOCK'])

import json
expected=json.loads((x['R']/'deployment/boot-manifest.json').read_text())['expected']
expected.update(json.loads((x['R']/'deployment/patches.json').read_text())['expected'])
expected.update(json.loads((x['R']/'deployment/engines.json').read_text())['expected'])
expected['lib/arm64-v8a/libnpth.so']='9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107'
expected['webview-t-lib/libwebview_bionic_shim.so']='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'
expected['run.sh']='ffb324e4a6950d53d4bf991ba93f1be9e2592780c92ddcf70467e3c3bf429e15'
h=x['dev']('sha256sum '+' '.join(x['rt']+'/'+n for n in expected),20)
(x['r']/'final-component-hashes.txt').write_text(h)
for n,v in expected.items():assert v+'  '+x['rt']+'/'+n in h,n
print('FINAL_COMPONENTS_VERIFIED',len(expected))
