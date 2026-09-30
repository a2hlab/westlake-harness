#!/usr/bin/env python3
"""Prepare four offline slots; an unregistered fourth board remains unassigned."""
import argparse
import csv
import json
from pathlib import Path
import sys
from shard_plan import balance, historical_costs, sha
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths


def make_plan(workspaces, fourth_serial=None):
    oh = lab_paths.boards('oh')
    if fourth_serial is not None and fourth_serial not in oh:
        raise ValueError('fourth serial must be an explicitly registered OH board')
    labels = ['5ea', '5cd', '61b']
    serials = [next((s for s, label in oh.items() if label == name), None) for name in labels]
    if not all(serials):
        raise ValueError('missing one of the three original OH whitelist entries')
    if fourth_serial in serials:
        raise ValueError('fourth serial duplicates a first-three board')
    known = json.loads((HERE.parent / 'freeze-v1/predictions.json').read_text())
    if isinstance(known, dict):
        known = known['keys']
    keys = [r['key'] if isinstance(r, dict) else r for r in known]
    apps_path = ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch/apps.json'
    apps = json.loads(apps_path.read_text())['apps']
    bykey = {r['key']: r for r in apps}
    entries = [bykey[k] for k in keys]
    if len(entries) != 66 or len(set(keys)) != 66:
        raise ValueError('require exactly 66 distinct cohort keys')
    source = workspaces / 'westlake-harness/benchmark/2026-09-30-j3-u3-sweep/runs'
    histories = [source / ('j3-' + label) for label in ['5ea', '61b']]
    costs, sources = historical_costs(entries, histories)
    # Portable evidence references, retaining exact input hashes.
    for item in sources:
        item['path'] = str(Path(item['path']).relative_to(workspaces))
    for row in costs:
        for sample in row['samples']:
            sample['source'] = str(Path(sample['source']).relative_to(workspaces))
    slots = list(zip(['A-5ea', 'B-5cd', 'C-61b', 'D-fourth'], serials + [fourth_serial]))
    shards = balance(costs, slots)
    for shard in shards:
        shard['assignment'] = 'registered_oh' if shard['serial'] else 'pending_fourth_oh_serial'
    return dict(schema='four-shards-v1', expected_keys=keys,
                expected_apk_sha256={e['key']: e.get('apk_sha256') for e in entries},
                cohort_manifest=str(apps_path.relative_to(ROOT)), cohort_manifest_sha256=sha(apps_path),
                historical_sources=sources, costs=costs, shards=shards,
                estimate_scope='J3 sequential completion intervals; equal-speed boards assumed. Unclicked/missing/new-APK samples use cohort median. Not a measured future runtime.',
                fourth_board='unassigned' if fourth_serial is None else fourth_serial,
                identity_revision='Subway uses current explicit ffd32287 cohort revision; old observations stay pinned to old bytes.',
                merge_note='The historical shard/merge_facts.py accepts exactly three shards; do not feed this plan into it. This dispatch delivers four keys files only.')


def write_plan(plan, out):
    if out.exists():
        raise ValueError('use a fresh output directory')
    out.mkdir(parents=True)
    for shard in plan['shards']:
        name = 'keys-' + shard['name'] + '.txt'
        (out / name).write_text('\n'.join(shard['keys']) + '\n')
        shard.update(keys_file=name, keys_sha256=sha(out / name))
    (out / 'shards.json').write_text(json.dumps(plan, indent=2) + '\n')
    with (out / 'costs.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=['key', 'estimated_seconds', 'basis'])
        writer.writeheader()
        writer.writerows({k: row[k] for k in writer.fieldnames} for row in plan['costs'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fourth-serial')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    plan = make_plan(lab_paths.workspaces(), a.fourth_serial)
    write_plan(plan, a.out)
    print(json.dumps([dict(name=s['name'], keys=len(s['keys']), estimated_seconds=s['estimated_seconds'], assignment=s['assignment']) for s in plan['shards']]))

if __name__ == '__main__':
    main()
