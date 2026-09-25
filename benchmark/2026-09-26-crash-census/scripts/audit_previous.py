"""Read-only recount of formal #42 evidence; never connects to a device."""
import argparse
import hashlib
import json
import pathlib
import re

TRIALS = ('formal-base-r1', 'formal-verify-r1', 'formal-speed-r1',
          'formal-speed-r2', 'formal-base-r2', 'formal-verify-r2b',
          'formal-verify-r3', 'formal-speed-r3', 'formal-base-r3')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=pathlib.Path)
    ap.add_argument('output', type=pathlib.Path)
    a = ap.parse_args(); rows = []
    for name in TRIALS:
        p = a.root/name
        report = json.loads((p/'device-report.json').read_text())
        pid = report['child']
        parent = (p/'parent.log').read_text(errors='replace')
        lines = (p/'child.stderr').read_text(errors='replace').splitlines()
        rows.append(dict(trial=name, pid=pid,
            parent_oh_chain_registration=parent.count('ART registered in OHOS special-handler chain'),
            reap_signals=re.findall(r'child '+str(pid)+r' killed by signal (\d+)', parent),
            stderr_fatal=[dict(line=i+1, context=lines[i:i+19]) for i, line in enumerate(lines)
                          if line.startswith('Fatal signal ')],
            faults=(p/'fault-paths.txt').read_text().splitlines(),
            late_faults=(p/'late-fault-paths.txt').read_text().splitlines(),
            hashes={f:hashlib.sha256((p/f).read_bytes()).hexdigest()
                    for f in ('parent.log', 'child.stderr', 'device-report.json')}))
    a.output.write_text(json.dumps(dict(root=str(a.root), trials=rows), indent=2)+'\n')
    print('trials', len(rows), 'native_chain_parents', sum(x['parent_oh_chain_registration'] > 0 for x in rows),
          'signal11', sum('11' in x['reap_signals'] for x in rows),
          'system_reports', sum(bool(x['faults'] or x['late_faults']) for x in rows))

if __name__ == '__main__': main()
