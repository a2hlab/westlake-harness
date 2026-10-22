#!/usr/bin/env python3
"""Local byte assembly only; never source input or invoke a device tool."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import sys

CARD = Path(__file__).resolve().parent
ROOT = '/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012'
MODIFIED = ('watchdog.sh', 'route-b-owner.sh', 'entry.sh', 'members.tsv',
            'startup.env', 'startup.expected.sha256')
INPUTS = set(MODIFIED) | {'boot-entry.sh', 'config-common.sh', '01_westlake_u13_toutiao.cfg'}
KEYS = {'STARTUP_APPROVED_BY', 'STARTUP_ENABLED', 'STARTUP_SERIAL', 'STARTUP_OLD_STOP_SHA',
        'STARTUP_MEMBERS_SHA', 'STARTUP_JIT_SHA', 'STARTUP_NAMESPACE_SHA',
        'STARTUP_START_PARENT_SHA', 'STARTUP_HOST_SPAWN_SHA', 'STARTUP_REQUEST_SHA',
        'STARTUP_DECODER_SHA', 'STARTUP_PROBE_SHA', 'STARTUP_TAP_WAIT_POLICY'}

class Refuse(Exception):
    pass

def need(ok, message):
    if not ok:
        raise Refuse(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_regular(path):
    need(path.is_file() and not path.is_symlink(), 'not a regular input: ' + str(path))
    return path.read_bytes()

def parse_startup(data):
    result = {}
    for line in data.decode('ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r"(STARTUP_[A-Z_]+)='([A-Za-z0-9_().-]+)'", line)
        need(match is not None, 'unknown startup syntax')
        key, value = match.groups()
        need(key in KEYS and key not in result, 'unknown/duplicate startup key')
        result[key] = value
    need(set(result) == KEYS, 'startup key set differs')
    return result

def replace_once(data, old, new):
    need(data.count(old) == 1, 'replacement not unique')
    return data.replace(old, new, 1)


def validate_lock(lock, source_dir):
    need(lock.get('schema') == 'T51-owned-exit-fix-package-v1', 'wrong card lock (T51 required)')
    need(lock.get('status') == 'ACCEPTED_FOR_OFFLINE_PACKAGING', 'T50 outer acceptance pending')
    need(isinstance(lock.get('t50_commit'), str) and re.fullmatch(r'[0-9a-f]{40}', lock['t50_commit']), 'source commit missing')
    need(isinstance(lock.get('outer_acceptance'), dict), 'acceptance reference missing')
    need({'watchdog.sh', 'route-b-owner.sh'} <= set(lock.get('sources', {})), 'two accepted source pins required')
    need({'source_git', 'recipe', 'raw_execution_index', 'outer_acceptance'} <= set(lock.get('provenance', {})), 'provenance chain incomplete')
    for name, pin in lock['sources'].items():
        need(Path(name).name == name, 'source name is not a basename')
        data = read_regular(source_dir / name)
        need(sha(data) == pin['sha256'] and len(data) == pin['bytes'], 'accepted source pin mismatch: ' + name)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        need(pin.get('git_blob') == blob, 'source Git blob mismatch: ' + name)
    for role, pin in lock['provenance'].items():
        path = Path(pin['path'])
        need(not path.is_absolute() and '..' not in path.parts, 'provenance path outside source directory')
        need(sha(read_regular(source_dir / path)) == pin['sha256'], 'provenance SHA mismatch: ' + role)
    need(lock['outer_acceptance'] == lock['provenance']['outer_acceptance'], 'acceptance reference mismatch')
    acceptance = json.loads(read_regular(source_dir / lock['outer_acceptance']['path']))
    need(acceptance.get('acceptance') == 'offline owned recovery fix accepted; no device acceptance', 'wrong acceptance scope')
    for name in ('watchdog.sh', 'route-b-owner.sh'):
        need(acceptance['candidate'][name] == lock['sources'][name]['sha256'], 'acceptance/source mismatch')

def validate_members(lock, rows):
    data = read_regular(CARD / 'inputs/member-records.json')
    need(sha(data) == lock['member_records_sha256'], 'member record SHA mismatch')
    records = json.loads(data)
    need(records['board'] == '5cd1e3dd00000000000000000923012c', 'member record board mismatch')
    members = records['members']
    need(len(members) == 13 and len({r['member'] for r in members}) == 13, 'member record set mismatch')
    byname = {r['member']: r for r in members}
    need(set(byname) == {r[1] for r in rows}, 'manifest/member records differ')
    for h, name, mode, line in rows:
        r = byname[name]
        need(h == r['manifest_sha256'] == r['device_sha256'] == r['local_bytes_sha256'], 'historical member SHA mismatch')
        need(mode == r['manifest_mode'] == r['device_mode'], 'historical member mode mismatch')

def assemble(manifest_path, byte_dir, source_dir, out):
    need(not out.exists() and not out.is_symlink(), 'output already exists')
    lock = json.loads(read_regular(CARD / 'inputs/source-lock.json'))
    validate_lock(lock, source_dir)
    manifest_bytes = read_regular(manifest_path)
    need(sha(manifest_bytes) == lock['preimage_manifest_sha256'], 'input manifest SHA mismatch')
    manifest = json.loads(manifest_bytes)
    need(len(manifest['files']) == 9, 'expected nine preimages')
    old, metadata = {}, {}
    for row in manifest['files']:
        name = Path(row['path']).name
        need(name in INPUTS and name not in old, 'unexpected/duplicate preimage')
        expected_path = '/system/etc/init/' + name if name.endswith('.cfg') else ROOT + '/' + name
        need(row['path'] == expected_path, 'preimage target mismatch')
        data = read_regular(byte_dir / name)
        need(len(data) == row['size'] and sha(data) == row['device_sha256'] == row['local_bytes_sha256'],
             'preimage SHA/size mismatch: ' + name)
        old[name], metadata[name] = data, row
    need(set(old) == INPUTS, 'preimage set mismatch')
    sources = {}
    for name, pin in lock['sources'].items():
        data = read_regular(source_dir / name)
        need(len(data) == pin['bytes'] and sha(data) == pin['sha256'], 'candidate source pin mismatch: ' + name)
        sources[name] = data
    startup = parse_startup(old['startup.env'])
    need(startup['STARTUP_ENABLED'] == '1', 'unexpected preimage enabled state')
    need(startup['STARTUP_SERIAL'] == manifest['board'], 'startup board mismatch')
    need(old['startup.expected.sha256'] == (sha(old['startup.env']) + '\n').encode(), 'old startup pin mismatch')
    need(startup['STARTUP_MEMBERS_SHA'] == sha(old['members.tsv']), 'old members pin mismatch')
    rows = []
    for line in old['members.tsv'].decode('ascii').splitlines(keepends=True):
        match = re.fullmatch(r'([0-9a-f]{64}) ([A-Za-z0-9_.-]+) ([0-7]{3})\n', line)
        need(match is not None, 'invalid member syntax')
        h, name, mode = match.groups()
        need(name not in {r[1] for r in rows}, 'duplicate member')
        if name in old:
            need(h == sha(old[name]), 'old member pin mismatch: ' + name)
        rows.append((h, name, mode, line))
    need(len(rows) == 13, 'expected thirteen members')
    validate_members(lock, rows)
    changed_members = {'watchdog.sh', 'route-b-owner.sh', 'entry.sh'}
    need(changed_members <= {r[1] for r in rows}, 'changed member absent')
    new = {n: sources[n] for n in ('watchdog.sh', 'route-b-owner.sh')}
    entry = old['entry.sh']
    for n in ('watchdog.sh', 'route-b-owner.sh'):
        entry = replace_once(entry, sha(old[n]).encode(), sha(new[n]).encode())
    new['entry.sh'] = entry
    new['members.tsv'] = ''.join(
        line.replace(h, sha(new[n]), 1) if n in changed_members else line
        for h, n, mode, line in rows).encode()
    new['startup.env'] = replace_once(old['startup.env'], b"STARTUP_ENABLED='1'", b"STARTUP_ENABLED='0'")
    new['startup.env'] = replace_once(new['startup.env'], startup['STARTUP_MEMBERS_SHA'].encode(), sha(new['members.tsv']).encode())
    new['startup.expected.sha256'] = (sha(new['startup.env']) + '\n').encode()
    need(parse_startup(new['startup.env'])['STARTUP_ENABLED'] == '0', 'candidate is not disabled')
    # No output directory is created until all input/grammar/pin checks succeed.
    out.mkdir(parents=False, exist_ok=False)
    (out / 'candidate').mkdir()
    (out / 'rollback').mkdir()
    for n in MODIFIED:
        (out / 'candidate' / n).write_bytes(new[n])
        (out / 'rollback' / n).write_bytes(old[n])
    members = [{'name': n, 'status': 'modified' if n in changed_members else 'unmodified',
                'collection': 'public_control_bytes' if n in old else 'historical_T46P2_member_record',
                'deployment_rehash_required': True, 'mode_unchanged': mode,
                'baseline_sha256': h, 'candidate_sha256': sha(new[n]) if n in changed_members else h}
               for h, n, mode, line in rows]
    receipt = {'status': 'DISABLED_OFFLINE_OWNED_EXIT_FIX_PACKAGE', 'rollout_ready': False,
               'root_unchanged': ROOT, 'new_approval': None,
               'historical_approval_text': 'Preserved from original; not authorization of candidate',
               'inputs_manifest_sha256': sha(manifest_bytes), 'input_count': 9,
               'members': members, 'unchanged_members': 10, 'historical_member_records': 13, 'member_bytes_not_in_public_snapshot': 9,
               'source_lock_sha256': sha(read_regular(CARD / 'inputs/source-lock.json')),
               'acceptance': lock['outer_acceptance'],
               'unchanged_external_controls': {n: sha(old[n]) for n in ('boot-entry.sh', 'config-common.sh', '01_westlake_u13_toutiao.cfg')},
               'files': {n: {'candidate_sha256': sha(new[n]), 'rollback_sha256': sha(old[n]),
                            'preimage_stat_reference': metadata[n]} for n in MODIFIED}}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    patch = ''.join(''.join(difflib.unified_diff(old[n].decode().splitlines(True), new[n].decode().splitlines(True),
                                               fromfile='rollback/' + n, tofile='candidate/' + n)) for n in MODIFIED)
    (out / 'package.patch').write_text(patch)
    print(json.dumps({'status': receipt['status'], 'candidate_files': 6, 'rollback_files': 6, 'rollout_ready': False}))

def main():
    need(sys.flags.optimize == 0 and not os.environ.get('PYTHONOPTIMIZE'), 'Python optimization prohibited')
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--bytes', type=Path, required=True)
    p.add_argument('--sources', type=Path, default=CARD / 'sources')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    assemble(a.inputs, a.bytes, a.sources, a.out)

if __name__ == '__main__':
    try:
        main()
    except (Refuse, OSError, ValueError, KeyError, UnicodeError) as e:
        print('REFUSE: ' + str(e), file=sys.stderr)
        sys.exit(2)
