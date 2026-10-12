#!/usr/bin/env python3
"""Local binding/preview checkpoint. No device/VM/remote transport exists here."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def validate(package=HERE):
    binding = json.loads((package / 'bindings.json').read_text())
    errors = []
    workspaces = HERE.parents[2]
    for row in binding['sources']:
        path = package / row['copy'] if 'copy' in row else workspaces / row['source'].removeprefix('$WORKSPACES/')
        if not path.is_file():
            errors.append({'role': row['role'], 'reason': 'missing source'})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            errors.append({'role': row['role'], 'reason': 'source SHA drift'})
    for row in binding['member_layout']:
        path=package/row['source']
        if not path.is_file(): errors.append({'role':row['source'],'reason':'missing package member'})
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            errors.append({'role':row['source'],'reason':'package member SHA drift'})
        allowed={binding['runtime']+'/run.sh',binding['runtime']+'/prepare_jit50.sh',binding['stage']+'/request.bin'}
        allowed.update(x['target'] for x in binding['watchdog_aliases'])
        allowed.update(x['helper_here'] for x in binding['watchdog_aliases'])
        if row['target'] not in allowed and not row['target'].startswith(binding['new_state_root']+'/'):
            errors.append({'role':row['source'],'reason':'target outside reviewed control scope'})
    if len(binding['watchdog_aliases']) != 2 or any(x['sha256'] != binding['candidate_sha256'] for x in binding['watchdog_aliases']):
        errors.append({'role': 'watchdog aliases', 'reason': 'inconsistent candidate binding'})
    if {x['target'] for x in binding['watchdog_aliases']} != {'/data/westlake-demo/toutiao/scripts/watchdog.sh','/data/local/tmp/operator45/selfheal48/watchdog.sh'}:
        errors.append({'role':'watchdog aliases','reason':'not both exact legacy aliases'})
    if binding['attempt_watchdog']['target']!=binding['new_state_root']+'/watchdog.sh' or binding['attempt_watchdog']['sha256']!=binding['candidate_sha256']:
        errors.append({'role':'attempt watchdog','reason':'wrong independent execution copy'})
    for row in binding['watchdog_aliases']+[binding['attempt_watchdog']]:
        if row['helper_here']!=str(Path(row['target']).parent/'route-b-owner.sh'):
            errors.append({'role':'HERE/helper','reason':'helper not beside its watchdog'})
    if binding['candidate_sha256']!='9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072':
        errors.append({'role':'candidate','reason':'not accepted frozen R1'})
    if not binding['new_state_root'].startswith('/data/westlake-demo/toutiao/recovery-attempts/') or '..' in Path(binding['new_state_root']).parts:
        errors.append({'role':'new state','reason':'not an independent attempt directory'})
    return binding, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--authorization', type=Path)
    ap.add_argument('--package', type=Path, default=HERE)
    args = ap.parse_args()
    binding, errors = validate(args.package)
    if args.execute or args.authorization:
        print(json.dumps({'status': 'REJECT', 'reason': 'preview-only host CLI; no authorized deployment transport', 'device_calls': 0}))
        return 2
    result = {
        'status': 'REJECT' if errors else ('pending' if binding['pending'] else 'offline-bound'),
        'execution_enabled': False, 'device_calls': 0,
        'candidate_sha256': binding['candidate_sha256'],
        'change_preview': binding['watchdog_aliases'],
        'stop': binding['old_stop'], 'data': binding['data_policy'],
        'rollback_preview': {
            'guardian_only': {'helper':'rb_script_signal','pid':'<new receipt exact PID>','birth':'<new receipt exact birth>','script':binding['new_state_root']+'/watchdog.sh','precondition':'separate approval; root UID/system sh/exact NUL argv/PID birth; missing tr or identity refuses; NO parent/U13 signal'},
            'targets':[{'target':x['target'],'new_sha256':x['sha256'],'backup_slot':'backups/'+hashlib.sha256(x['target'].encode()).hexdigest(),'before':x['before'],'restore_order':['verify exact preimage + SHA/mode/uid/gid/SELinux label','copy temporary file, verify SHA, atomic rename, restore recorded metadata, readback','recorded absent only: remove unchanged candidate iff unmounted; otherwise refuse']} for x in binding['member_layout']],
            'preserve':['old stop','all app-data/data/webview','old run/receipts','all failed attempt evidence'],
            'restart_unsafe_watchdog':False,
        },
        'pending': binding['pending'], 'errors': errors,
    }
    print(json.dumps(result, indent=2))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
