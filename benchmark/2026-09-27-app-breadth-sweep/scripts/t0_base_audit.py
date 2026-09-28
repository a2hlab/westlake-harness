"""Read-only deployed framework/host audit, before and after a control/shard run."""
import json
import sys
from pathlib import Path
import t0_collect as c

serial, run, phase = sys.argv[1:]
if serial not in c.ALLOWED_SERIALS or phase not in ('before', 'after') or not c.re.fullmatch(r'[a-zA-Z0-9_-]+', run):
    raise SystemExit('invalid identity')
c.SERIAL = serial
out = Path.home() / 'a2hlab/ws' / ('out-appsweep-t0-' + run) / serial / 'base-audit'
out.mkdir(parents=True, exist_ok=True)
p = Path.home() / 'a2hlab/board' / serial / ('framework-2' if serial.startswith('5ea') else 'framework-1') / 'device-report.json'
fw = json.loads(p.read_text())
expected = {fw['stage'] + '/' + k: v['sha256'] for k, v in fw['files'].items()}
expected['/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'] = '8cfa5bb1eb1a26fa69dbfd5618cecf0aefb282f6035aa9af24dcb9f96eb81267'
b = c.Board(out)
actual = {}
paths = sorted(expected)
receipts = []
for i in range(0, len(paths), 25):
    _, raw = b.shell('sha256sum ' + ' '.join(c.shlex.quote(p) for p in paths[i:i + 25]))
    receipts.append(raw)
    for line in raw.splitlines():
        digest, path = line.split(None, 1)
        actual[path] = digest
result = {'serial': serial, 'phase': phase, 'run_id': run, 'time': c.time.time(),
          'framework_report_sha256': c.sha(p), 'expected': expected, 'actual': actual,
          'passed': actual == expected}
c.save(out / (phase + '.json'), result)
(out / (phase + '.txt')).write_text('\n'.join(receipts))
print(serial, phase, len(actual), result['passed'], flush=True)
raise SystemExit(0 if result['passed'] else 2)
