#!/usr/bin/env python3
"""Independent isolated HDC protocol model; never executes its recorded commands."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys

state = Path(os.environ['RECOVERY_TEST_DEVICE'])
model = json.loads(state.read_text())
arguments = sys.argv[1:]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def persist():
    state.write_text(json.dumps(model, indent=2))


def object_at(path):
    return model['objects'].get(path)


def fail(reason, code=7):
    persist()
    print(reason, file=sys.stderr)
    raise SystemExit(code)


if arguments[:2] != ['-t', model['serial']]:
    fail('serial mismatch')
model['events'].append(arguments)
if arguments[2:4] == ['file', 'recv']:
    data = bytes.fromhex(object_at(arguments[4])['hex'])
    if model.get('fault') == 'backup_partial':
        data = data[:3]
    Path(arguments[5]).write_bytes(data)
elif arguments[2:4] == ['file', 'send']:
    data = Path(arguments[4]).read_bytes()
    target = arguments[5]
    model['send_count'] = model.get('send_count', 0) + 1
    if str(Path(target).parent) not in model['directories']:
        fail('send parent directory absent', 1)
    partial = model.get('fault') == 'send_partial' and model['send_count'] == 3
    if partial:
        data = data[:7]
    model['objects'][target] = dict(exists=True, sha256=digest(data), mode='644',
                                    uid=0, gid=0, label='u:object_r:data_file:s0', hex=data.hex())
    if partial:
        fail('injected interrupted send; partial bytes retained', 1)
elif arguments[2] == 'shell':
    tokens = shlex.split(arguments[3])
    script = tokens[2].removesuffix(';')
    output = ''
    remote = 0
    if script == 'cat /proc/sys/kernel/random/boot_id':
        output = model['boot']
        if model.get('fault') == 'remote_failure':
            remote = 13
    elif '\np=' in script:
        target = shlex.split(script.split('\np=', 1)[1].split('\n', 1)[0])[0]
        observed = object_at(target)
        if model.get('fault') == 'probe_failure':
            remote = 1
        elif observed:
            output = 'EXISTS\n{mode} {uid} {gid}\n{sha256} {target}\n-rw------- 1 {uid} {gid} {label} 0 {target}'.format(**{**observed, 'target': target})
        else:
            output = 'ABSENT'
    elif script.startswith('set -eu; mkdir -p '):
        model['mkdir_count'] = model.get('mkdir_count', 0) + 1
        if model.get('fault') == 'mkdir_first_failure' and model['mkdir_count'] == 1:
            remote = 1
        else:
            target = shlex.split(script)[-1]
            model['directories'] = sorted(set(model['directories']) | {str(Path(target)), *map(str, Path(target).parents)})
    elif script.startswith('set -eu; chown '):
        values = shlex.split(script)
        target = values[4].rstrip(';')
        uid, gid = values[3].split(':')
        label = values[9]
        if model.get('fault') == 'metadata_failure' or not label.startswith('u:object_r:'):
            remote = 1
        else:
            observed = object_at(target)
            observed.update(uid=int(uid), gid=int(gid), mode=values[6], label=label)
    elif 'cfg-stage-' in script and 'mount -o ' in script:
        values = shlex.split(script)
        stage = values[values.index('cp') + 1]
        target = values[-1]
        observed = dict(object_at(stage))
        observed.update(model['cfg_metadata'])
        model['objects'][target] = observed
        if model.get('fault') == 'inert_then_fail' and observed['sha256'] == model['inert_sha']:
            remote = 1
    elif 'row=$(cat /proc/$p/stat)' in script and 'cmdline' in script:
        if model.get('fault') in ('guardian_reuse', 'guardian_uid', 'guardian_argv'):
            remote = 1
    elif script.startswith('cat ') and '/lock/owner' in script:
        output = bytes.fromhex(object_at(shlex.split(script)[1])['hex']).decode().strip()
    elif 'set -C; umask 077; : > ' in script:
        target = shlex.split(script.split(': > ', 1)[1])[0].rstrip(';')
        if str(Path(target).parent) not in model['directories']:
            remote = 1
        else:
            model['objects'][target] = dict(exists=True, sha256=digest(b''), mode='600',
                                           uid=0, gid=0, label='u:object_r:data_file:s0', hex='')
    elif 'echo GONE' in script and '/proc/' in script:
        output = 'ALIVE' if model.get('fault') == 'guardian_stuck' else 'GONE'
    elif script.startswith('set -eu; ! grep -F '):
        target = shlex.split(script)[-1]
        if model.get('fault') == 'mounted_addition':
            remote = 1
        else:
            model['objects'].pop(target, None)
    else:
        fail('UNMODELLED_SCRIPT: ' + script)
    print(output + '\nRE_REMOTE_RC=' + str(remote))
else:
    fail('UNMODELLED_OPERATION')
persist()
