#!/usr/bin/env python3
"""Summarize saved read-only inventories, preserving unknowns and mapping gaps."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import collect

HERE = Path(__file__).resolve().parent

def coverage(board, path):
    if board.get('status') == 'blocked':
        return 'unavailable'
    if path in board.get('files', {}):
        return 'observed'
    if path in collect.SINGLES:
        return 'missing_or_read_failed'
    tree = next((t for t in board.get('trees', []) if path.startswith(t['root'] + '/')), None)
    return 'absent' if tree and tree['complete'] else 'unavailable'

def compare(boards):
    by_serial = {b['serial']: b for b in boards}
    paths = sorted(set(collect.SINGLES + [r+'/' for r in collect.ROOTS]) | {p for b in boards for p in b.get('files', {})})
    rows = []
    for path in paths:
        if path.endswith('/') and any(p.startswith(path) and p != path for p in paths):
            continue
        values = {s: {'sha256': by_serial.get(s, {}).get('files', {}).get(path), 'status': coverage(by_serial.get(s, {'status': 'blocked'}), path)} for s in collect.SERIALS}
        shas = [v['sha256'] for v in values.values()]
        known = all(v['status'] in {'observed', 'absent'} for v in values.values())
        verdict = 'equal' if all(shas) and len(set(shas)) == 1 else 'different' if known else 'incomplete'
        rows.append({'path': path, 'verdict': verdict, 'boards': values})
    return rows

def derive_role(comm, maps, ppid, parent_pids):
    apk = '/data/app/el1/bundle/public/com.example.helloworld/android/base.apk'
    has_apk = any(line.split()[-1] == apk for line in maps.splitlines() if line.split())
    if comm == 'com.example.hel' and has_apk and ppid in parent_pids:
        return 'helloworld'
    if ppid in parent_pids and comm != 'appspawn-x':
        return 'other_app_child'
    return None

def resolve_roles(boards, collection):
    for board in boards:
        parent_pids = {p['pid'] for p in board['processes'] if p['role'] == 'appspawn' and p['ppid'] == 1}
        for proc in board['processes']:
            prefix = collection.parent / board['serial'][:8] / f"{proc['role']}-{proc['pid']}"
            stat_path = Path(str(prefix) + '-stat-before.json')
            maps_path = Path(str(prefix) + '-maps.json')
            if not stat_path.exists() or not maps_path.exists():
                continue
            stat = json.loads(stat_path.read_text())['stdout']
            maps = json.loads(maps_path.read_text())['stdout']
            comm = stat[stat.find('(')+1:stat.rfind(')')]
            role = derive_role(comm, maps, proc['ppid'], parent_pids)
            if role:
                proc['original_role'] = proc['role']
                proc['role'] = role
                proc['role_evidence'] = {'comm': comm, 'parent_pid': proc['ppid'],
                    'stat_file': str(stat_path), 'maps_file': str(maps_path),
                    'maps_file_sha256': hashlib.sha256(maps_path.read_bytes()).hexdigest(),
                    'apk_map_lines': [i for i, line in enumerate(maps.splitlines(), 1) if '/com.example.helloworld/android/base.apk' in line]}

def add_supplement(boards, path):
    supplement = json.loads(path.read_text())
    board = next(b for b in boards if b['serial'] == supplement['serial'])
    if not board.get('stable_boot') or not (board['boot_before'] == supplement['boot_before'] == supplement['boot_after']):
        raise ValueError('supplement is from a different or unstable boot')
    proc = supplement['process']
    parent_pids = {p['pid'] for p in board['processes'] if p['role'] == 'appspawn'}
    raw_maps = json.loads((path.parent / f"helloworld-{proc['pid']}-maps.json").read_text())['stdout']
    raw_stat = json.loads((path.parent / f"helloworld-{proc['pid']}-stat-before.json").read_text())['stdout']
    comm = raw_stat[raw_stat.find('(')+1:raw_stat.rfind(')')]
    if derive_role(comm, raw_maps, proc['ppid'], parent_pids) != 'helloworld':
        raise ValueError('supplement does not establish HelloWorld child identity')
    if not proc['stable_process'] or not proc['stable_maps'] or proc['unverified_files']:
        raise ValueError('supplement process/mappings incomplete')
    for f in proc['files']:
        if f['path'] in board['files'] and f['sha256'] != board['files'][f['path']]:
            raise ValueError('supplement mapped file differs from original snapshot: ' + f['path'])
    proc['supplement_source'] = str(path)
    board['processes'].append(proc)

def disk_complete(board):
    return (bool(board.get('stable_boot')) and len(board.get('trees', [])) == len(collect.ROOTS)
            and all(t['complete'] for t in board['trees'])
            and all(p in board['files'] for p in collect.SINGLES)
            and not board.get('critical_changed') and not board.get('critical_missing'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collection', type=Path)
    parser.add_argument('--supplement', type=Path, action='append', default=[])
    args = parser.parse_args()
    source = json.loads(args.collection.read_text())
    boards = source['boards']
    if len(boards) != 3 or {b['serial'] for b in boards} != set(collect.SERIALS):
        raise ValueError('collection must contain exactly the three allowlisted boards')
    resolve_roles(boards, args.collection)
    for supplement in args.supplement:
        add_supplement(boards, supplement)
    for board in boards:
        board['raw_collector_status'] = board['status']
        roles = {p['role'] for p in board['processes'] if p['stable_process'] and p['maps_nonempty'] and p.get('stable_maps') and not p['unverified_files']}
        board['missing_process_roles'] = sorted({'appspawn', 'helloworld'} - roles)
        board['disk_complete'] = disk_complete(board)
        board['status'] = 'captured' if board['disk_complete'] and not board['missing_process_roles'] else 'partial' if board['files'] else 'blocked'
    rows = compare(boards)
    pins = json.loads((HERE/'reference-pins.json').read_text())['pins']
    for row in rows:
        row['reference'] = pins.get(row['path'])
    profile_matches = {b['serial']: {path: ('match' if b['files'].get(path) == pin['sha256'] else 'different_profile' if path in b['files'] else 'unavailable') for path, pin in pins.items()} for b in boards}
    mapped = []
    for board in boards:
        for proc in board.get('processes', []):
            for f in proc['files']:
                mapped.append({'serial': board['serial'], 'pid': proc['pid'], 'role': proc['role'], 'stable_process': proc['stable_process'], **f})
    gaps = []
    for board in boards:
        if board['status'] != 'captured':
            gaps.append(f"{board['serial']}: {board['status']}; missing_roles={board['missing_process_roles']}; disk_complete={board['disk_complete']}")
        for proc in board.get('processes', []):
            if proc['unverified_files']:
                gaps.append(f"{board['serial']} {proc['role']} pid={proc['pid']}: {proc['unverified_files']} unverified mappings")
    result = {'task': 64, 'collection_path': str(args.collection.resolve()),
              'collection_sha256': hashlib.sha256(args.collection.read_bytes()).hexdigest(),
              'supplements': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in args.supplement],
              'complete': not gaps, 'gaps': gaps,
              'disk_parity_equal': all(r['verdict'] == 'equal' for r in rows),
              'process_coverage': {role: sum(any(p['role'] == role for p in b['processes']) for b in boards) for role in ['appspawn', 'helloworld', 'foundation']},
              'counts': {v: sum(r['verdict'] == v for r in rows) for v in ['equal', 'different', 'incomplete']},
              'boards': boards, 'file_comparison': rows, 'mapped_comparison': mapped, 'reference_profile_matches': profile_matches,
              'r2': {'disk_hash_inventory': 'verified' if all(b['disk_complete'] for b in boards) else 'unverified', 'read_only_collection': 'verified' if not gaps else 'partially' if any(b['files'] for b in boards) else 'unverified',
                     'three_board_process_coverage': 'verified' if not gaps else 'partially', 'device_alignment': 'unverified'}}
    (HERE/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    with (HERE/'file-parity.csv').open('w') as f:
        w=csv.writer(f)
        w.writerow(['path','verdict',*[s[:8] for s in collect.SERIALS],'historical_reference_sha256','reference_scope'])
        for row in rows:
            w.writerow([row['path'], row['verdict'], *[row['boards'][s]['sha256'] or row['boards'][s]['status'] for s in collect.SERIALS], (row['reference'] or {}).get('sha256','not_pinned'), (row['reference'] or {}).get('scope','byte difference requires component review')])
    with (HERE/'mapped-parity.csv').open('w') as f:
        cols=['serial','role','pid','path','device','inode','identity','sha256','root_sha256','mapped_sha256']
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); w.writeheader();w.writerows(mapped)
    md=['# Collected file differences', '', 'Full hashes: [file-parity.csv](file-parity.csv); actual objects: [mapped-parity.csv](mapped-parity.csv).', '', '| Path | 5ea | 5cd | 61b | Verdict |', '|---|---|---|---|---|']
    for r in rows:
        if r['verdict']=='equal': continue
        cells=[v['sha256'][:12] if v['sha256'] else v['status'] for v in r['boards'].values()]
        md.append('| '+ ' | '.join([r['path'],*cells,r['verdict']])+' |')
    md+=['',f"Equal: {result['counts']['equal']}; different: {result['counts']['different']}; incomplete: {result['counts']['incomplete']}. Unavailable is not equal and is not a confirmed missing file."]
    (HERE/'DIFFERENCES.md').write_text('\n'.join(md)+'\n')
    print(json.dumps({'counts': result['counts'],'complete':result['complete'],'gaps':gaps},indent=2))

if __name__ == '__main__':
    main()
