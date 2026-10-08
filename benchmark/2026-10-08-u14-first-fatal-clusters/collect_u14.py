#!/usr/bin/env python3
"""U14 first-fatal collection (cc-t3): per non-lit key, its ACTUAL U14 window1-6 candidate-runner first-fatal.
Source = U14 window{1..6} non-smoke runner (movers/lit-regression/lottery/unlit) <key>/hilog.txt, latest window.
Signature = cluster_first_cause.cluster_key(compare.first_fatal(run_dir)). No recovery-smoke, no U13 comparison.
Keys with no U14 non-smoke run -> no_u14_observation + the reference's last-observation path (not inferred)."""
import importlib.util, json, sys
from pathlib import Path
from collections import defaultdict
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import cluster_first_cause as cfc  # noqa
spec = importlib.util.spec_from_file_location('u12cmp', REPO / 'benchmark/2026-10-03-u12-predicted-vs-actual/compare.py')
u12cmp = importlib.util.module_from_spec(spec); spec.loader.exec_module(u12cmp)
WS = REPO.parent / 'westlake-harness-u7-executor'  # sibling worktree; no hardcoded user path
U14 = WS / 'benchmark/2026-10-03-u14-stage-a-plan'
ref = json.load(open(U14 / 'inputs/reference.json'))
nonlit = {k: v for k, v in ref['keys'].items() if v.get('verdict') != 'lit'}

SHARDS = ('movers', 'lit-regression', 'lottery', 'unlit-original', 'unlit')
def find_run(key):
    cands = []
    for w in range(1, 7):
        for shard in SHARDS:
            for d in U14.glob(f'window{w}/u14-*/*/runner/{shard}-{key}-*/*/*/{key}'):
                if (d / 'hilog.txt').exists():
                    cands.append((w, str(d), d))
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], x[1]))
    return cands[-1][2]

import re as _re
def fault_lib(run_dir):
    """For a signal: the crashing library basename (+ symbol) from the #00/#01 fault frame — normalises SIGSEGV clusters."""
    try:
        txt = (run_dir / 'hilog.txt').read_text(errors='replace')
    except Exception:
        return None
    for m in _re.finditer(r'#0[0-2] pc [0-9a-f]+ \S*/(lib[^/()]+\.so)(?:\(([^)]*)\))?', txt):
        lib = m.group(1)
        if lib.startswith('ld-musl'):
            sym = m.group(2) or ''
            return f"{lib}:{sym.split('+')[0]}" if sym else lib
        return lib  # first app/so fault frame
    return None

def sig_label(sig, run_dir=None):
    if not isinstance(sig, dict):
        return str(sig)
    kind = sig.get('kind') or 'unknown'
    if kind == 'signal' and run_dir is not None:
        fl = fault_lib(run_dir)
        return f"signal-SIGSEGV|{fl or 'unknown-frame'}"
    detail = sig.get('cause') or ''
    return f"{kind}|{str(detail)[:70]}"

rows = {}
for key, meta in sorted(nonlit.items()):
    d = find_run(key)
    if d is None:
        rows[key] = {'u14_observed': False, 'verdict': meta.get('verdict'),
                     'last_observation': meta.get('t20') or meta.get('source') or '(none)'}
        continue
    try:
        ff = u12cmp.first_fatal(d)
        sig = cfc.cluster_key(ff)
    except Exception as e:
        ff, sig = None, {'kind': 'analyze-error', 'detail': str(e)[:120]}
    rows[key] = {'u14_observed': True, 'verdict': meta.get('verdict'), 'run': str(d),
                 'terminal_sig': sig, 'label': sig_label(sig, d),
                 'ff_brief': {k: ff.get(k) for k in ('terminal', 'bind_status', 'first_fatal_line', 'reason')} if isinstance(ff, dict) else None}

clusters = defaultdict(list)
noobs = {}
for key, r in rows.items():
    if r['u14_observed']:
        clusters[r['label']].append(key)
    else:
        noobs[key] = r
ranked = sorted(clusters.items(), key=lambda kv: -len(kv[1]))
out = {'n_nonlit': len(nonlit), 'n_observed': sum(1 for r in rows.values() if r['u14_observed']),
       'n_no_u14_obs': len(noobs),
       'clusters_ranked': [{'label': lab, 'keys': sorted(ks), 'count': len(ks)} for lab, ks in ranked],
       'no_u14_observation': noobs, 'rows': rows}
Path(__file__).resolve().parent.joinpath('clusters.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(f"non-lit={len(nonlit)} observed={out['n_observed']} no_obs={len(noobs)}")
print("=== clusters ranked ===")
for c in out['clusters_ranked']:
    print(f"{c['count']:2d}  {c['label'][:75]}  :: {', '.join(c['keys'][:6])}{'…' if c['count']>6 else ''}")
print("=== no U14 observation ===", ', '.join(sorted(noobs)))
