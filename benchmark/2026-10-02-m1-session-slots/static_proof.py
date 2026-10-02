#!/usr/bin/env python3
"""Static proof for the M1 per-session slot fix, from real hilogs only.

    static_proof.py [--out proof.json]

For every run (the 11 outer-signed paired runs in ../2026-10-02-white-vs-lit/pairs.json and the 133 U10.1T8 runs of
white-vs-lit population.groups()), replay the app process's window-lookup events in order:
  publish   `createSession: published process window target session=N`      -> last_published = N, published += {N}
  lookup    `[IPC] ENTER WMClient.getOhNativeWindow session=N` that is answered `unknown sessionId=N` (the local
            sessions_ map of the bridge copy the compat shim resolved is empty for N), then either
              rescued  `BBQ.update: sessionId=N → OHNativeWindow=`  (readProcessWindowTarget hit: N == last published)
              empty    `BBQ.update: getOhNativeWindow(sessionId=N) returned null`
Claims checked (each a count over all lookups):
  a) every `empty` lookup asks for a session that was published but is NOT the last published one at that moment;
     every `rescued` one asks for the last published one  (= the single slot explains every outcome)
  b) a run that publishes exactly one session only ever looks up that session: under per-session slots the read
     returns the same pointer the single slot returns (no-op)
  c) sessions published per process: max / distribution (the per-session variables a run would create)
Under the fix, outcome(lookup) = rescued iff N was published at all; the lookups whose outcome changes are listed.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WVL = HERE.parent / '2026-10-02-white-vs-lit'
sys.path.insert(0, str(WVL))
import population  # noqa: E402
import templates  # noqa: E402

PUB = re.compile(r'createSession: published process window target session=(\d+)')
ENTER = re.compile(r'\[IPC\] ENTER WMClient\.getOhNativeWindow session=(\d+)')
UNKNOWN = re.compile(r'getOhNativeWindow: unknown sessionId=(\d+)')
RESCUED = re.compile(r'BBQ\.update: sessionId=(\d+) → OHNativeWindow=')
NULL = re.compile(r'BBQ\.update: getOhNativeWindow\(sessionId=(\d+)\) returned null')


def replay(run):
    t = templates.extract(run)
    pids = set(t['app_pids'])
    last, published, pending = None, [], {}
    lookups = []
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'AppSpawnXJava' in line or ('getOhNativeWindow' not in line and 'BBQ.update' not in line
                                       and 'published process window target' not in line):
            continue
        m = templates.LINE.match(line)
        if not m or int(m.group(7)) not in pids:
            continue
        msg, tid = m.group(11), m.group(8)
        p = PUB.search(msg)
        if p:
            last = int(p.group(1))
            if last not in published:
                published.append(last)
            continue
        u = UNKNOWN.search(msg)
        if u:
            pending[tid] = int(u.group(1))
            continue
        r = RESCUED.search(msg) or NULL.search(msg)
        if r and pending.get(tid) == int(r.group(1)):
            n = pending.pop(tid)
            lookups.append({'session': n, 'outcome': 'rescued' if RESCUED.search(msg) else 'empty',
                            'last_published': last, 'published_before': n in published})
    return {'published': published, 'lookups': lookups}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'proof.json'))
    a = ap.parse_args()
    ws = str(templates.lab_paths.workspaces())
    runs = [(r['key'], 'pair-' + r['label'], r['run'].replace('$WORKSPACES', ws))
            for r in json.loads((WVL / 'pairs.json').read_text())['runs']]
    runs += [(k, g, run) for k, g, v, run in population.groups()]
    per_run, a_bad, a_n, changed = [], [], 0, []
    b_single, b_bad = 0, []
    sessions_hist = collections.Counter()
    for key, group, run in runs:
        rp = replay(run)
        sessions_hist[len(rp['published'])] += 1
        for lk in rp['lookups']:
            a_n += 1
            consistent = (lk['outcome'] == 'rescued') == (lk['session'] == lk['last_published'])
            if not consistent or (lk['outcome'] == 'empty' and not lk['published_before']):
                a_bad.append((key, group, lk))
            after = 'rescued' if lk['published_before'] else 'empty'
            if after != lk['outcome']:
                changed.append({'key': key, 'group': group, 'session': lk['session'], 'before': lk['outcome'],
                                'after': after, 'last_published': lk['last_published']})
        if len(rp['published']) == 1:
            b_single += 1
            if any(lk['session'] != rp['published'][0] or lk['outcome'] != 'rescued' for lk in rp['lookups']):
                b_bad.append((key, group, rp))
        per_run.append({'key': key, 'group': group, 'published': rp['published'],
                        'lookups': [f"{lk['session']}:{lk['outcome']}(last={lk['last_published']})" for lk in rp['lookups']]})
    out = {'runs': len(runs), 'lookups': a_n,
           'a_violations': len(a_bad), 'b_single_session_runs': b_single, 'b_violations': len(b_bad),
           'c_sessions_published_per_run': dict(sorted(sessions_hist.items())),
           'changed_by_fix': changed, 'per_run': per_run}
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(f"runs {len(runs)}, misses-then-outcome lookups {a_n}")
    print(f"a) outcome == (requested session is the last published): violations {len(a_bad)}")
    for x in a_bad[:5]:
        print('   ', x)
    print(f"b) single-session runs {b_single}: lookups not (that session, rescued): {len(b_bad)}")
    print(f"c) sessions published per run: {dict(sorted(sessions_hist.items()))}")
    print(f"lookups whose outcome the per-session slot changes: {len(changed)}")
    by = collections.Counter((c['group'], c['before'], c['after']) for c in changed)
    for k, v in sorted(by.items()):
        print(f'   {k}: {v}')
    print('   keys:', sorted({(c['key'], c['group']) for c in changed}))
    return 0 if not a_bad and not b_bad else 1


if __name__ == '__main__':
    sys.exit(main())
