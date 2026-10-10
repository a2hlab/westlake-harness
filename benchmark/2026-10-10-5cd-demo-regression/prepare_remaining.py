#!/usr/bin/env python3
"""Offline continuation plans: count finished regular keys, group by root and shot tier.
Uses the existing demo supervisor/adapter; no board access or runtime mutation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', HERE.parents[2]))

def read(p):
    return json.loads(Path(p).read_text())

def expand(p):
    return Path(os.path.expandvars(str(p).replace('$WORKSPACES', str(WS))))

def portable(p):
    return str(Path(p).resolve()).replace(str(WS), '$WORKSPACES')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--round', type=Path, required=True)
    ap.add_argument('--previous-plan', type=Path, action='append', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--keys-per-window', type=int, default=36)
    a = ap.parse_args()
    if a.out.exists() or not 1 <= a.keys_per_window <= 64:
        raise ValueError('fresh directory and bounded group size required')
    config = read(a.round / 'round.json')
    if config['serial'] != '5cd1e3dd00000000000000000923012c':
        raise ValueError('this continuation is approved only for 5cd')
    apps = read(a.round / 'batch-apps.json')['apps']
    tiers = {r['key']: r['screenshot_seconds'] for r in read(a.round / 'shot-tiers.json')['apps']}
    done = {}
    for path in a.previous_plan:
        p = read(path)
        if p['serial'] != config['serial']:
            raise ValueError('previous plan serial mismatch')
        result = read(expand(p['out']) / 'board-run-result.json')
        if result.get('before_unlock') != 0:
            raise ValueError('previous window did not release through identity verification')
        for shard in p['shards']:
            for f in (expand(p['out']) / shard['name']).glob('*/*/*/record.json'):
                r = read(f)
                if r.get('finished_at') and not r.get('install_only'):
                    if r['key'] in done:
                        raise ValueError('duplicate previous regular key')
                    done[r['key']] = portable(f)
    keys = {r['key'] for r in apps}
    if set(done) - keys:
        raise ValueError('non-canonical previous key')
    pending = [r for r in apps if r['key'] not in done]
    template = read(expand(config['windows'][0]))
    a.out.mkdir(parents=True)
    plans, scheduled = [], []
    for offset in range(0, len(pending), a.keys_per_window):
        selected = pending[offset:offset + a.keys_per_window]
        d = a.out / ('window-%02d' % (len(plans) + 1))
        d.mkdir()
        groups = {}
        for row in selected:
            groups.setdefault((row['input_root'], tiers[row['key']]), []).append(row['key'])
        p = json.loads(json.dumps(template))
        p.update(execution_enabled=False, out=portable(d / 'runner'),
                 why='Enforcing 5cd demo continuation; same APK inputs/state, batched launch-only by root and shot tier', shards=[])
        for i, ((root, tier), members) in enumerate(groups.items()):
            keyfile = d / ('group-%d-t%d.keys' % (i, tier))
            keyfile.write_text('\n'.join(members) + '\n')
            p['shards'].append({'name': 'group-%d-t%d' % (i, tier), 'manifest': portable(a.round / 'batch-apps.json'),
                                'input_root': root, 'keys_file': portable(keyfile)})
            scheduled.extend(members)
        p['demo_ability_pins'] = {k: v for old in config['windows']
            for k, v in read(expand(old)).get('demo_ability_pins', {}).items() if k in {r['key'] for r in selected}}
        p['after_lock'][-1] = portable(d / 'before-identity')
        p['before_unlock'][-1] = portable(d / 'after-identity')
        p['offline_precheck']['evidence'] += [portable(a.out / 'continuation.json')]
        path = d / 'plan.json'
        path.write_text(json.dumps(p, indent=2) + '\n')
        plans.append(portable(path))
    if len(scheduled) != len(set(scheduled)) or set(scheduled) != keys - set(done):
        raise ValueError('continuation coverage mismatch')
    result = {'finished': done, 'pending': scheduled, 'plans': plans, 'serial': config['serial'],
              'state': 'PREPARED_DISABLED', 'slots_enabled': False, 'device_access': False,
              'manifest_sha256': hashlib.sha256((a.round / 'batch-apps.json').read_bytes()).hexdigest()}
    (a.out / 'continuation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'finished': len(done), 'pending': len(pending), 'windows': len(plans), 'device_access': False}))

if __name__ == '__main__':
    main()
