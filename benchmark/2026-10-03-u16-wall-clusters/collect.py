#!/usr/bin/env python3
"""U16 wall clusters, step 1: first fatal of every non-lit key in the U13 stage-A runner records.

    collect.py [--out-dir .]   -> per-run.json, population.json

Population   the keys of the 219 U13 stage-A runner records (benchmark/2026-10-03-u13-stage-a-decision/
             selftest-u13-stage-a.json; activation-smoke controls helloworld / zigzag / probe excluded) that have no
             lit run in any of the four window sign-offs (window{1..4}-signoff/outer-signoff.json). Two sign-off
             schemas: windows 1-3 give runs / lit_runs / verdicts per key, window 4 gives one `verdict`.
Runs         every runner record of the key (a key can have more than one run); each row is one run.
Signatures   imported from benchmark/2026-10-03-u13-first-fatal-clusters/collect.py, which imports
             2026-10-03-u12-predicted-vs-actual/compare.py (first_fatal.py + cluster_first_cause.cluster_key for the
             terminal, the earliest WALL line before it, bind_status semantics, dlopen_failures --near-fatal 3).
"""
import argparse
import collections
import glob
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import dlopen_failures  # noqa: E402
import lab_paths  # noqa: E402

spec = importlib.util.spec_from_file_location('u13ff', REPO / 'benchmark/2026-10-03-u13-first-fatal-clusters/collect.py')
u13ff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u13ff)
cfc, u12cmp = u13ff.cfc, u13ff.u12cmp

WS = lab_paths.workspaces()
SELFTEST = REPO / 'benchmark/2026-10-03-u13-stage-a-decision/selftest-u13-stage-a.json'
SIGNOFFS = sorted(glob.glob(str(REPO / 'benchmark/2026-10-03-u13-stage-a-plan/window*-signoff/outer-signoff.json')))
CONTROLS = {'helloworld', 'zigzag', 'probe', None}


def verdicts():
    v = collections.defaultdict(lambda: {'runs': 0, 'lit_runs': 0, 'verdicts': [], 'reference': set(), 'boards': set(),
                                         'windows': []})
    for f in SIGNOFFS:
        w = Path(f).parent.name.replace('-signoff', '')
        for k, e in json.loads(Path(f).read_text())['keys'].items():
            x = v[k]
            if 'verdict' in e:                      # window 4 schema
                x['runs'] += 1
                x['lit_runs'] += e['verdict'] == 'lit'
                x['verdicts'].append(e['verdict'])
            else:
                x['runs'] += e.get('runs', 0)
                x['lit_runs'] += e.get('lit_runs', 0)
                x['verdicts'] += e.get('verdicts', [])
            x['reference'].add(e.get('reference'))
            x['boards'].add(e.get('board'))
            x['windows'].append(w)
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    out = Path(ap.parse_args().out_dir)
    sel = json.loads(SELFTEST.read_text())['runs']
    runs = collections.defaultdict(list)
    for r in sel:
        runs[r.get('key')].append(Path(r['record']).parent)
    v = verdicts()
    unsigned = sorted(k for k in runs if k not in CONTROLS and k not in v)
    pop = {k: v[k] for k in sorted(runs) if k not in CONTROLS and k in v and v[k]['lit_runs'] == 0}
    (out / 'population.json').write_text(json.dumps({
        'records': len(sel), 'keys': len([k for k in runs if k not in CONTROLS]), 'unsigned_keys': unsigned,
        'non_lit': {k: {'runs_signed': e['runs'], 'verdicts': e['verdicts'], 'reference': sorted(map(str, e['reference'])),
                        'boards': sorted(map(str, e['boards'])), 'windows': e['windows'], 'runner_records': len(runs[k])}
                    for k, e in pop.items()}}, indent=1) + '\n')
    rows = []
    for key in pop:
        for d in sorted(runs[key]):
            text = (d / 'hilog.txt').read_text(errors='replace') if (d / 'hilog.txt').exists() else ''
            ff = u12cmp.first_fatal(d)
            sig = cfc.cluster_key(ff)
            bind, bind_cause = u13ff.bind_of(d, text)
            wall = bind_cause if bind == 'bind_failed' and bind_cause else u12cmp.earliest_wall(d, ff)
            near = [r['lib'] for r in dlopen_failures.scan([d], near_fatal_seconds=3) if r.get('near_fatal_keys')]
            rows.append({'key': key, 'verdicts': pop[key]['verdicts'], 'reference': sorted(map(str, pop[key]['reference'])),
                         'board': d.parent.name[:8], 'runtime_jar': u13ff.jar_of(d), 'has_hilog': bool(text),
                         'terminal': u12cmp.norm(sig), 'terminal_kind': sig['kind'],
                         'terminal_cause': (sig['cause'] or '')[:240], 'terminal_frame': (sig.get('first_frame') or '')[:200],
                         'signal_thread': u12cmp.signal_thread(d, ff), 'wall': wall, 'wall_norm': u12cmp.wnorm(wall),
                         'wall_source': 'bind_failed_cause' if bind == 'bind_failed' and bind_cause else 'earliest_wall',
                         'bind': bind, 'near_fatal_dlopen': near, 'facts': u12cmp.run_facts_line(d, key),
                         'run': str(d).replace(str(WS), '$WORKSPACES')})
            print(key, bind, sig['kind'], (sig['cause'] or '')[:70], '|', wall[:90], file=sys.stderr)
    (out / 'per-run.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')
    print(f'population {len(pop)} keys, {len(rows)} runs; unsigned {unsigned}', file=sys.stderr)


if __name__ == '__main__':
    main()
