#!/usr/bin/env python3
"""Lottery-key baseline k/n -> Wilson 95% CI + U13 sample-size to judge M1 at alpha=0.05.

Input: a CSV `baselines.csv` with columns key,generation,lit,n  (k=lit of n signed t20 runs).
Output: per (key,generation) Wilson CI; per key pooled baseline p0; and the number of U13 runs
needed so the M1-predicted outcome (all-lit, p1~1.0) rejects H0: rate=p0 at one-sided alpha=0.05
(exact binomial), plus a two-proportion power note for partial effects.
"""
import csv, math, sys
from pathlib import Path

Z = 1.959963985  # 95%

def wilson(k, n):
    if n == 0: return (0.0, 0.0, 1.0)
    p = k / n
    d = 1 + Z*Z/n
    c = (p + Z*Z/(2*n)) / d
    h = Z*math.sqrt(p*(1-p)/n + Z*Z/(4*n*n)) / d
    return (p, max(0, c-h), min(1, c+h))

def min_n_all_lit(p0, alpha=0.05):
    """smallest n s.t. observing n consecutive lit rejects H0:rate=p0 (one-sided), i.e. p0^n <= alpha."""
    if p0 <= 0: return 1
    if p0 >= 1: return None  # cannot distinguish
    return math.ceil(math.log(alpha) / math.log(p0))

def two_prop_n(p0, p1, alpha=0.05, power=0.80):
    """per-group n for one-sided two-proportion test (normal approx)."""
    if p1 <= p0: return None
    za, zb = 1.6448536, 0.8416212  # one-sided 0.05, power 0.80
    pbar = (p0+p1)/2
    num = (za*math.sqrt(2*pbar*(1-pbar)) + zb*math.sqrt(p0*(1-p0)+p1*(1-p1)))**2
    return math.ceil(num / (p1-p0)**2)

def main():
    f = Path(sys.argv[1] if len(sys.argv) > 1 else 'baselines.csv')
    rows = list(csv.DictReader(open(f)))
    bykey = {}
    print("=== per (key, generation) baseline k/n + Wilson 95% CI ===")
    for r in rows:
        k, n = int(r['lit']), int(r['n'])
        p, lo, hi = wilson(k, n)
        print(f"  {r['key']:12} {r['generation']:10} {k}/{n}  p={p:.2f}  95%CI[{lo:.2f},{hi:.2f}]")
        bykey.setdefault(r['key'], [0, 0])
        bykey[r['key']][0] += k; bykey[r['key']][1] += n
    print("\n=== per key: pooled baseline p0 + U13 runs needed (M1 => all-lit, p1~1.0) ===")
    for key, (k, n) in sorted(bykey.items()):
        p, lo, hi = wilson(k, n)
        mn = min_n_all_lit(p) if p < 1 else None
        tp = two_prop_n(p, 0.99) if p < 0.99 else None
        print(f"  {key:12} pooled {k}/{n} p0={p:.2f} CI[{lo:.2f},{hi:.2f}]  "
              f"min_n(all-lit rejects p0, a=.05)={mn}  two-prop n/side(p1=.99,pwr.8)={tp}")
if __name__ == '__main__':
    main()
