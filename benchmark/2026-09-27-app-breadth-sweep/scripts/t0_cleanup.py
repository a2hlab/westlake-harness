"""Cleanup only a finished run's exact recorded paths after evidence export."""
import json
import sys
from pathlib import Path
import t0_collect as c
import t0_evidence as evidence

serial, run = sys.argv[1:]
if serial not in c.ALLOWED_SERIALS:
    raise SystemExit('invalid serial')
c.SERIAL = serial
base = c.capture_ops.isolated_root(Path.home(), run) / serial
out = base / 'cleanup'
out.mkdir(exist_ok=False)
b = c.Board(out)
protected = 'ls -ld /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf* /data/local/tmp/a2hlab-app-c91d26bf* 2>/dev/null'
protected_hashes = 'for p in /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf* /data/local/tmp/a2hlab-app-c91d26bf*; do if [ -d "$p" ]; then find "$p" -type f -exec sha256sum {} \\;; fi; done'
_, before = b.shell(protected, required=False)
(out / 'protected-before.txt').write_text(before)
_, hashes_before = b.shell(protected_hashes, timeout=120)
(out / 'protected-hashes-before.txt').write_text(hashes_before)
paths = []
for report in base.glob('*/probe/device-report.json'):
    state = json.loads(report.read_text())
    saved = Path(__file__).resolve().parents[3] / 'benchmark/2026-09-28-blocker-triage/runs' / run / serial / report.parent.parent.name / 'triage.json'
    if not saved.exists():
        raise SystemExit('refuse cleanup before export: ' + str(report))
    current = report.parent.parent / 'triage.json'
    if c.sha(saved) != c.sha(current):
        raise SystemExit('refuse cleanup with stale exported triage: ' + str(report))
    if not (saved.parent / 'stderr-provenance.json').exists():
        raise SystemExit('refuse cleanup without archived current child stderr provenance: ' + str(report))
    if state.get('runtime') and state.get('stage'):
        paths.extend(evidence.cleanup_paths(state['runtime'], state['stage']))
b.shell('aa force-stop org.westlake.imehost', required=False)
b.shell("pkill -f '[a]ppspawn-x'", required=False)
for path in paths:
    b.shell('rm -rf ' + c.shlex.quote(path))
_, after = b.shell(protected, required=False)
(out / 'protected-after.txt').write_text(after)
_, hashes_after = b.shell(protected_hashes, timeout=120)
(out / 'protected-hashes-after.txt').write_text(hashes_after)
c.save(out / 'cleanup.json', {'serial': serial, 'run_id': run, 'removed_exact_paths': paths,
       'protected_paths_present': bool(before.strip()), 'protected_listing_unchanged': before == after,
       'protected_contents_unchanged': sorted(hashes_before.splitlines()) == sorted(hashes_after.splitlines())})
print(serial, 'cleaned exact paths:', len(paths), 'protected listing unchanged:', before == after)
if before != after or sorted(hashes_before.splitlines()) != sorted(hashes_after.splitlines()):
    raise SystemExit('protected evidence changed during cleanup')
