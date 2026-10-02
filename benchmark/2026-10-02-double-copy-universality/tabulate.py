#!/usr/bin/env python3
"""Bridge/runtime copy counts per key on the U10.1T8 stage-A runs, grouped by the outer-signed verdict.

Inputs: n11h_readout.py --json output for each stage-A board-level run (pass the readout JSON files), the signed
U10.1T8 baseline and the candidate first-fatal cluster table. Output: per-key CSV on stdout-adjacent file + counts.
"""
import collections, csv, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SIG = json.loads((REPO / 'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json').read_text())['keys']
CL = json.loads((REPO / 'benchmark/2026-10-02-candidate-first-fatal-clusters/clusters.json').read_text())
WHITE = set(CL[0]['keys'])  # no-observed-termination = the white-window cluster


def main(readouts, out_csv):
    rows = {}
    for f in readouts:
        d = json.loads(Path(f).read_text())
        items = d if isinstance(d, list) else d.get('keys') or d.get('rows') or []
        if isinstance(items, dict):
            items = [dict(key=k, **v) for k, v in items.items()]
        for r in items:
            rows[r['key']] = r
    tab = collections.Counter()
    with open(out_csv, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'group', 'signed_verdict', 'bridge_copies', 'runtime_copies', 'assetmanager_abort', 'run_dir'])
        for k in sorted(rows):
            r = rows[k]
            v = SIG.get(k, {}).get('verdict', 'unsigned')
            grp = 'lit' if v.startswith('lit') else ('white-cluster' if k in WHITE else 'other')
            lb = r.get('load_bases') or {}
            snap = lb.get('t5') or lb.get('t20') or (next(iter(lb.values())) if lb else {})
            br, rt = snap.get('liboh_adapter_bridge.so'), snap.get('liboh_android_runtime.so')
            am = any((r.get('assetmanager') or {}).values())
            run = str(r.get('dir', '')).replace(str(REPO.parent) + '/', '$WORKSPACES/')
            w.writerow([k, grp, v, br, rt, am, run])
            tab[(grp, br, rt, am)] += 1
    for (grp, br, rt, am), n in sorted(tab.items(), key=str):
        print(f'{grp:<14} bridge={br} runtime={rt} assetmanager_abort={am}: {n}')


if __name__ == '__main__':
    main(sys.argv[2:], sys.argv[1])
