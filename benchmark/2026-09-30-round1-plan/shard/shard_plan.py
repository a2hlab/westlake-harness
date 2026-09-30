#!/usr/bin/env python3
"""Offline, deterministic LPT sharding using recorded serial-run timing proxies."""
import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_KEYS = HERE.parent/'freeze-v1/predictions.json'
BOARDS = [('A-5ea','5ea34a4500000000000000001123012c'),
          ('B-5cd','5cd1e3dd00000000000000000923012c'),
          ('C-61b','61b0657200000000000000000324012c')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def cohort(path):
    if path.suffix == '.json':
        data=json.loads(path.read_text())
        if isinstance(data,dict):data=data['keys']
        rows=[{'key':r} if isinstance(r,str) else r for r in data]
    else:rows=[{'key':k.strip()} for k in path.read_text().splitlines() if k.strip()]
    keys=[r['key'] for r in rows]
    if len(set(keys))!=len(keys) or not keys:raise ValueError('empty or duplicate key list')
    if any(not k or '/' in k or k in ('.','..') or any(c.isspace() for c in k) for k in keys):
        raise ValueError('unsafe key')
    return rows


def run_base(path):
    if (path/'baseline.json').is_file() or list(path.glob('*/record.json')):return path
    candidates=[p for p in path.iterdir() if p.is_dir() and ((p/'baseline.json').is_file() or list(p.glob('*/record.json')))] if path.exists() else []
    if len(candidates)!=1:raise ValueError('provide one explicit serial run directory: '+str(path))
    return candidates[0]


def historical_costs(entries, histories, fallback=60.0):
    expected={r['key']:r.get('apk_sha256') for r in entries};samples={k:[] for k in expected};sources=[]
    for history in histories:
        base=run_base(history);summary=base/'summary.json'
        if not summary.is_file():raise ValueError('ordered summary.json required for historical timing')
        records=json.loads(summary.read_text())['records'];previous=None;seen=set()
        sources.append({'path':str(summary.resolve()),'sha256':sha(summary)})
        for r in records:
            key=r['key']
            if key in seen:raise ValueError('duplicate historical key: '+key)
            seen.add(key);end=r.get('finished_at');start=r.get('clicked_at')
            valid=isinstance(end,(int,float)) and math.isfinite(end)
            same=previous and (r.get('serial'),r.get('boot_id'))==(previous.get('serial'),previous.get('boot_id'))
            prior_end=previous.get('finished_at') if same else None
            delta=end-prior_end if valid and isinstance(prior_end,(int,float)) and math.isfinite(prior_end) else None
            matches=key in expected and (not expected[key] or expected[key]==r.get('apk_sha256'))
            if matches:
                measured=delta is not None and delta>0 and r.get('clicked') is True
                samples[key].append(dict(source=str(summary.resolve()),source_sha256=sha(summary),
                    observed_interval_s=delta,post_click_s=end-start if valid and isinstance(start,(int,float)) and end>=start else None,
                    cost_s=delta if measured else None,
                    method='serial completion interval including inter-app/setup overhead' if measured else 'unmeasured first interval, clock discontinuity, or prelaunch failure'))
            previous=r if valid else None
    observed=[s['cost_s'] for values in samples.values() for s in values if s['cost_s'] is not None]
    default=statistics.median(observed) if observed else fallback
    if not math.isfinite(default) or default<=0:raise ValueError('positive fallback required')
    costs=[]
    for r in entries:
        values=samples[r['key']];measured=[s['cost_s'] for s in values if s['cost_s'] is not None]
        cost=statistics.median(measured) if measured else default
        costs.append(dict(key=r['key'],apk_sha256=r.get('apk_sha256'),estimated_seconds=round(cost,6),
                          basis='historical_completion_interval' if measured else 'cohort_median_fallback',samples=values))
    return costs,sources


def balance(costs, boards=BOARDS):
    if not boards:raise ValueError('no boards')
    if len({r['key'] for r in costs})!=len(costs):raise ValueError('duplicate costs')
    if any(not math.isfinite(r['estimated_seconds']) or r['estimated_seconds']<=0 for r in costs):raise ValueError('nonpositive/nonfinite cost')
    # Equal key counts where possible, then longest job to the least-loaded board.
    size,extra=divmod(len(costs),len(boards))
    shards=[dict(name=name,serial=serial,capacity=size+(i<extra),keys=[],estimated_seconds=0.0) for i,(name,serial) in enumerate(boards)]
    for row in sorted(costs,key=lambda r:(-r['estimated_seconds'],r['key'])):
        target=min((s for s in shards if len(s['keys'])<s['capacity']),key=lambda s:(s['estimated_seconds'],len(s['keys']),s['name']))
        target['keys'].append(row['key']);target['estimated_seconds']+=row['estimated_seconds']
    for s in shards:s['estimated_seconds']=round(s['estimated_seconds'],6)
    return shards


def main():
    p=argparse.ArgumentParser();p.add_argument('--keys',type=Path,default=DEFAULT_KEYS)
    p.add_argument('--history',type=Path,action='append',required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expected-count',type=int,default=66);a=p.parse_args()
    entries=cohort(a.keys)
    if len(entries)!=a.expected_count:raise ValueError('unexpected cohort size')
    if a.out.exists():raise ValueError('use a fresh output directory')
    costs,sources=historical_costs(entries,a.history);shards=balance(costs)
    a.out.mkdir(parents=True)
    for s in shards:
        name='keys-'+s['name']+'.txt';(a.out/name).write_text('\n'.join(s['keys'])+'\n');s['keys_file']=name;s['keys_sha256']=sha(a.out/name)
    result=dict(schema='u1-three-shards-v1',cohort=str(a.keys.resolve()),cohort_sha256=sha(a.keys),
        expected_keys=[r['key'] for r in entries],expected_apk_sha256={r['key']:r.get('apk_sha256') for r in entries},
        historical_sources=sources,costs=costs,shards=shards,
        estimate_scope='Previous serial completion intervals are approximate per-key service costs, including setup/overhead. First key, prelaunch failures and unmatched APKs use cohort median; no file mtimes. Equal-speed boards assumed; no actual U1 duration claim.',
        script_sha256=sha(Path(__file__)))
    dump(a.out/'shards.json',result)
    with (a.out/'costs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=['key','estimated_seconds','basis']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in costs)
    print(json.dumps([{'name':s['name'],'keys':len(s['keys']),'estimated_seconds':s['estimated_seconds']} for s in shards],indent=2))


if __name__=='__main__':main()
