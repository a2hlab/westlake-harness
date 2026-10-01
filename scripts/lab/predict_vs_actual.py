#!/usr/bin/env python3
"""Write a per-key prediction before a full sweep; after the sweep, compare it with the signed result.

    predict_vs_actual.py predict --baseline <outer-signoff.json> --clusters <clusters.json> --include n10b,j10b \\
        [--cover cluster=fix ...] [--observed key=verdict:reason ...] [--out predictions.csv]
    predict_vs_actual.py compare --predictions predictions.csv --actual <new outer-signoff.json> [--json out.json]

Why (user rule 2026-10-01): a full sweep is only informative against a prediction written before it. Rules:
  * baseline lit -> "lit" (a fix must not take it down); a flaky key (knowledge/gates/flaky-keys.json) -> "flaky";
  * a non-lit key whose death cluster is covered by an included fix -> "lit?" (passes that wall; the next wall is
    unknown, so a miss here is a wall the scanner did not see);
  * --observed overrides from a window that already ran the fix on the key (e.g. acrylic=lit:N10b r3);
  * everything else keeps its baseline verdict.
compare classes each key: hit, regression (baseline lit, now not), missed-wall (predicted lit?, not lit -> feed the
scanner), unexpected-lit (predicted not lit, now lit -> find which fix did it), flaky. Exit 1 if any regression.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FLAKY = REPO / 'knowledge/gates/flaky-keys.json'
LIT = {'lit'}


def verdicts(signoff):
    d = json.loads(Path(signoff).read_text())
    keys = d['keys']
    return {e['key']: e['verdict'] for e in keys} if isinstance(keys, list) else {k: v['verdict'] for k, v in keys.items()}


def predict(baseline, clusters, include, cover, observed, flaky):
    by_key, covered = {}, {}
    for c in clusters['clusters']:
        fixes = {f for f, why in (c.get('coverage') or {}).items() if why}
        fixes |= {f for cl, f in cover if cl == c['name']}
        for k in c['keys']:
            by_key[k] = c['name']
            covered[k] = sorted(fixes & include)
    rows = []
    for key, v in sorted(baseline.items()):
        if key in observed:
            pred, why = observed[key]
        elif key in flaky:
            pred, why = 'flaky', 'flaky-keys.json: repeat rate, not one run'
        elif v in LIT:
            pred, why = 'lit', 'baseline lit; must stay lit'
        elif covered.get(key):
            pred, why = 'lit?', f'cluster {by_key[key]} covered by {"+".join(covered[key])}; next wall unknown'
        else:
            pred, why = v, f'cluster {by_key.get(key, "-")} not covered'
        rows.append({'key': key, 'baseline': v, 'cluster': by_key.get(key, ''),
                     'covered_by': '+'.join(covered.get(key, [])), 'prediction': pred, 'reason': why})
    return rows


def compare(pred_rows, actual):
    out = []
    for r in pred_rows:
        a = actual.get(r['key'])
        p, b = r['prediction'], r['baseline']
        if a is None:
            cls = 'missing'
        elif p == 'flaky':
            cls = 'flaky'
        elif b in LIT and a not in LIT:
            cls = 'regression'
        elif p == 'lit?' and a not in LIT:
            cls = 'missed-wall'
        elif p not in ('lit', 'lit?') and a in LIT:
            cls = 'unexpected-lit'
        elif (p in ('lit', 'lit?')) == (a in LIT):
            cls = 'hit'
        else:
            cls = 'miss'
        out.append(dict(r, actual=a, result=cls))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('predict')
    p.add_argument('--baseline', required=True)
    p.add_argument('--clusters', required=True)
    p.add_argument('--include', required=True, help='comma-separated fix ids in the new state')
    p.add_argument('--cover', action='append', default=[], help='cluster=fix (coverage the cluster file lacks)')
    p.add_argument('--observed', action='append', default=[], help='key=verdict:reason (from a window already run)')
    p.add_argument('--out', default='-')
    c = sub.add_parser('compare')
    c.add_argument('--predictions', required=True)
    c.add_argument('--actual', required=True)
    c.add_argument('--json')
    args = ap.parse_args(argv)
    if args.cmd == 'predict':
        flaky = {k['key'] for k in json.loads(FLAKY.read_text())['keys']} if FLAKY.exists() else set()
        observed = {}
        for o in args.observed:
            k, rest = o.split('=', 1)
            v, _, why = rest.partition(':')
            observed[k] = (v, why or 'observed in a window')
        rows = predict(verdicts(args.baseline), json.loads(Path(args.clusters).read_text()),
                       set(args.include.split(',')), [tuple(x.split('=', 1)) for x in args.cover], observed, flaky)
        fh = sys.stdout if args.out == '-' else open(args.out, 'w', newline='')
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
        counts = {}
        for r in rows:
            counts[r['prediction']] = counts.get(r['prediction'], 0) + 1
        print(f'predicted: {counts}', file=sys.stderr)
        return 0
    rows = list(csv.DictReader(open(args.predictions)))
    out = compare(rows, verdicts(args.actual))
    counts = {}
    for r in out:
        counts[r['result']] = counts.get(r['result'], 0) + 1
    print(f'compare: {counts}')
    for r in out:
        if r['result'] in ('regression', 'missed-wall', 'unexpected-lit', 'miss'):
            print(f"  {r['result']:15s} {r['key']:45s} predicted {r['prediction']:6s} actual {r['actual']}  ({r['cluster']})")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return 1 if counts.get('regression') else 0


if __name__ == '__main__':
    sys.exit(main())
