"""Read-only inventory of known demo writers and stop markers."""
import json
import re
import sys
from pathlib import Path
import t0_collect as c

serial, run = sys.argv[1:]
if serial not in c.ALLOWED_SERIALS:
    raise SystemExit('invalid serial')
c.SERIAL = serial
out = c.capture_ops.isolated_root(Path.home(), run) / serial / 'interference-audit'
out.mkdir(parents=True, exist_ok=True)
b = c.Board(out)
_, processes = b.shell('ps -ef')
names = re.compile(r'/(?:open_broker|onscreen_keeper|watchdog|guardian)\.sh(?:\s|$)')
matches = [line for line in processes.splitlines() if names.search(line)]
paths = ['/data/local/tmp/persist-demo/broker.stop', '/data/local/tmp/operator45/keeper.stop',
         '/data/local/tmp/operator45/stop', '/data/local/tmp/operator45/selfheal48/stop',
         '/data/local/tmp/operator45/fresh48/stop']
markers = {}
for path in paths:
    rc, _ = b.shell('test -f ' + c.shlex.quote(path), required=False)
    markers[path] = rc == 0
rc, configs = b.shell("grep -l -E 'a2hlab|operator45|persist-demo|onscreen_keeper' /system/etc/init/*.cfg /vendor/etc/init/*.cfg 2>/dev/null", required=False)
result = {'serial': serial, 'run_id': run, 'epoch': c.time.time(), 'active_demo_writers': matches,
          'stop_markers': markers, 'matching_init_configs': configs.splitlines(), 'init_scan_rc': rc,
          'passed': not matches and rc == 1,
          'scope': 'known demo script process names and system/vendor init .cfg references; no OS autostart in persist_demo.sh'}
c.save(out / 'inventory.json', result)
print(json.dumps(result), flush=True)
