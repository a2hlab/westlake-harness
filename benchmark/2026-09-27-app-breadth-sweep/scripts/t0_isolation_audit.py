"""Hash shared LocalSend inputs and a pre-existing other-lane output without writing either."""
import json
import sys
from pathlib import Path
import t0_collect as c

serial, run, phase = sys.argv[1:]
if serial not in c.ALLOWED_SERIALS or phase not in ('before', 'after'):
    raise SystemExit('invalid audit identity')
out = c.capture_ops.isolated_root(Path.home(), run) / serial / 'isolation-audit'
out.mkdir(parents=True, exist_ok=True)
roots = [Path.home() / 'a2hlab/app-inputs/localsend', Path.home() / 'a2hlab/ws/out-broker-wikipedia']
files = {}
for root in roots:
    if not root.is_dir():
        raise SystemExit('missing reference directory: ' + str(root))
    files[str(root)] = {str(p.relative_to(root)): c.sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
result = {'phase': phase, 'serial': serial, 'run_id': run, 'epoch': c.time.time(), 'files': files}
if phase == 'after':
    result['passed'] = json.loads((out / 'before.json').read_text())['files'] == files
c.save(out / (phase + '.json'), result)
print(phase, [len(v) for v in files.values()], result.get('passed', 'recorded'), flush=True)
if result.get('passed') is False:
    raise SystemExit('shared input or other-lane output changed')
