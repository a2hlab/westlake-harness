#!/usr/bin/env python3
"""Same app, same state, one run lit and one white: which hilog templates only the white run has, and the reverse.

    pair_diff.py [--out pair-diff.csv] [--top 40]

Pairs: every (lit run, white run) of one key and one state in pairs.json (outer-signed t20 per run): 7 pairs over
4 keys. Templates: templates.py (window = launch-3 s .. min(t20, hilog end); scope app/sys). For each template:
  white_only_pairs  number of pairs whose white run has it and whose lit run does not
  lit_only_pairs    the reverse
  keys_w / keys_l   distinct keys among those pairs
Ranked by (keys, pairs). A template counts once per run (presence), never by line count.
"""
import argparse
import collections
import csv
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402
import templates  # noqa: E402

WS = str(lab_paths.workspaces())


def load_pairs():
    runs = json.loads((HERE / 'pairs.json').read_text())['runs']
    groups = collections.defaultdict(lambda: {'lit': [], 'white': []})
    for r in runs:
        groups[(r['key'], r['state'])][r['label']].append(r['run'].replace('$WORKSPACES', WS))
    pairs = []
    for (key, state), g in sorted(groups.items()):
        for lit, white in itertools.product(g['lit'], g['white']):
            pairs.append((key, state, lit, white))
    return pairs


def sets(run):
    t = templates.extract(run)
    return {('app', k) for k in t['app']} | {('sys', k) for k in t['sys']}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'pair-diff.csv'))
    ap.add_argument('--top', type=int, default=40)
    a = ap.parse_args()
    pairs = load_pairs()
    cache = {}
    w_only, l_only = collections.defaultdict(list), collections.defaultdict(list)
    for key, state, lit, white in pairs:
        L = cache.setdefault(lit, sets(lit))
        Wt = cache.setdefault(white, sets(white))
        for t in Wt - L:
            w_only[t].append(key)
        for t in L - Wt:
            l_only[t].append(key)
    rows = []
    for t in set(w_only) | set(l_only):
        rows.append({'scope': t[0], 'template': t[1], 'white_only_pairs': len(w_only[t]), 'keys_w': len(set(w_only[t])),
                     'lit_only_pairs': len(l_only[t]), 'keys_l': len(set(l_only[t])),
                     'which_w': ' '.join(sorted(set(w_only[t]))), 'which_l': ' '.join(sorted(set(l_only[t])))})
    rows.sort(key=lambda r: (-max(r['keys_w'], r['keys_l']), -max(r['white_only_pairs'], r['lit_only_pairs']), r['template']))
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(r for r in rows if max(r['white_only_pairs'], r['lit_only_pairs']) >= 2)
    print(f'{len(pairs)} pairs over {len({p[0] for p in pairs})} keys; {len(rows)} templates differ in >= 1 pair')
    for side, col, kcol in (('WHITE-ONLY', 'white_only_pairs', 'keys_w'), ('LIT-ONLY', 'lit_only_pairs', 'keys_l')):
        best = sorted((r for r in rows if r[col] > 0 and r[col] > r['lit_only_pairs' if side == 'WHITE-ONLY' else 'white_only_pairs']),
                      key=lambda r: (-r[kcol], -r[col], r['template']))[:a.top]
        print(f'== {side} (pairs/keys; opposite-direction pairs in brackets)')
        for r in best:
            opp = r['lit_only_pairs'] if side == 'WHITE-ONLY' else r['white_only_pairs']
            print(f"{r[col]}/{len(pairs)} pairs {r[kcol]}/4 keys [{opp}] {r['scope']:3} {r['template'][:150]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
