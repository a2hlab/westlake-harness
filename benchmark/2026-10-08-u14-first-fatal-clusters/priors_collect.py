#!/usr/bin/env python3
"""Window-7 PRIORS (cc-t3): for the non-lit keys WITHOUT a U14 observation, first-fatal from the key's MOST RECENT real
observation (reference.json t20 run; version tagged from the path). These are PRIORS, explicitly NOT U14 conclusions.
Also reconciles prior-vs-U14-actual for the 11 keys that DO have a U14 run (lists flips)."""
import importlib.util, json, os, sys
from pathlib import Path
from collections import defaultdict
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import cluster_first_cause as cfc  # noqa
spec = importlib.util.spec_from_file_location('u12cmp', REPO / 'benchmark/2026-10-03-u12-predicted-vs-actual/compare.py')
u12cmp = importlib.util.module_from_spec(spec); spec.loader.exec_module(u12cmp)
import importlib.util as iu
hv = iu.spec_from_file_location('ufc', Path(__file__).resolve().parent / 'collect_u14.py')
ufc = iu.module_from_spec(hv); hv.loader.exec_module(ufc)  # reuse sig_label/fault_lib

WSROOT = REPO.parent
WS = WSROOT / 'westlake-harness-u7-executor'
ref = json.load(open(WS / 'benchmark/2026-10-03-u14-stage-a-plan/inputs/reference.json'))
nonlit = {k: v for k, v in ref['keys'].items() if v.get('verdict') != 'lit'}
u14 = json.load(open(Path(__file__).resolve().parent / 'clusters.json'))
u14rows = u14['rows']
noobs = set(u14['no_u14_observation'].keys())

def resolve(p):
    if not p: return None
    p = p.replace('$WORKSPACES', str(WSROOT))
    pp = Path(p)
    # leaf = dir containing hilog.txt; t20 may be a .jpeg or the key dir
    if pp.suffix in ('.jpeg', '.jpg', '.png'): pp = pp.parent
    if (pp / 'hilog.txt').exists(): return pp
    # search up/down for hilog.txt
    if pp.is_dir():
        for h in pp.rglob('hilog.txt'):
            return h.parent
    return None

def ff_sig(run):
    try:
        ff = u12cmp.first_fatal(run); sig = cfc.cluster_key(ff)
        return ufc.sig_label(sig, run), sig
    except Exception as e:
        return f'analyze-error|{str(e)[:60]}', None

def version_of(p):
    if not p: return 'none'
    for g, lab in [('u10-1-t8-rerun', 'U10.1-T8'), ('u13-stage-a', 'U13'), ('u12-final', 'U12'), ('u11', 'U11')]:
        if g in p: return lab
    return 'other'

priors = {}
for k in sorted(noobs):
    t20 = nonlit[k].get('t20')
    run = resolve(t20)
    ver = version_of(t20)
    if run is None:
        priors[k] = {'version': ver, 'run': None, 'prior_label': 'no-run-found', 'verdict': nonlit[k].get('verdict'),
                     'note': 'last observation path has no readable hilog'}
        continue
    lab, _ = ff_sig(run)
    priors[k] = {'version': ver, 'run': str(run), 'prior_label': lab, 'verdict': nonlit[k].get('verdict')}

# cluster the priors
pc = defaultdict(list)
for k, r in priors.items(): pc[r['prior_label']].append(k)
ranked = sorted(pc.items(), key=lambda kv: -len(kv[1]))

# reconcile: 11 U14-observed keys -> compute their PRIOR too, compare to U14 actual label
flips = []
for k, r in u14rows.items():
    if not r.get('u14_observed'): continue
    t20 = nonlit[k].get('t20'); run = resolve(t20)
    prior_lab = ff_sig(run)[0] if run else 'no-prior'
    u14_lab = r.get('label')
    # normalise signal pid/tid noise already handled; compare kind
    def kind(x): return (x or '').split('|')[0]
    if kind(prior_lab) != kind(u14_lab):
        flips.append({'key': k, 'version': version_of(t20), 'prior': prior_lab, 'u14_actual': u14_lab})

out = {'n_no_u14_obs': len(noobs), 'priors_note': 'PRIORS from each key latest real observation; version-tagged; NOT U14 conclusions',
       'priors_clusters_ranked': [{'label': l, 'count': len(ks), 'keys': sorted(ks)} for l, ks in ranked],
       'priors': priors,
       'reconcile_prior_vs_u14_actual_for_observed_keys': {'flips': flips, 'n_flips': len(flips)}}
Path(__file__).resolve().parent.joinpath('priors-29.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
print('no-obs priors:', len(priors))
for c in out['priors_clusters_ranked']: print(f"{c['count']:2d}  {c['label'][:70]}  :: {', '.join(c['keys'][:5])}")
print('FLIPS (prior vs U14 actual, observed keys):', len(flips))
for f in flips: print('  ', f['key'], '|', f['version'], '| prior', f['prior'][:40], '-> U14', f['u14_actual'][:40])
