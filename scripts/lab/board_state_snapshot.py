#!/usr/bin/env python3
"""Capture one read-only board state, including raw outputs and collection failures."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from selinux_label_audit import load_recipe, parse_labels, plan_targets, read_command


LAYERS = ['/system', '/chipset', '/sys_prod', '/chip_prod']
INIT_ROOTS = ['/system/etc/init', '/vendor/etc/init', '/chipset/etc/init']
COLLECTION = Path(__file__).resolve().parents[2] / 'knowledge/gates/board-state-collection.json'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


class HdcTransport:
    def __init__(self, executable, serial):
        import lab_paths
        if serial not in lab_paths.boards('oh'):
            raise ValueError('unapproved full OH serial')
        self.executable, self.serial = executable, serial

    def run(self, command):
        try:
            result = subprocess.run([self.executable, '-t', self.serial, 'shell', command],
                                    capture_output=True, timeout=120)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            return 124, error.stdout or b'', error.stderr or b'transport timeout'
        except OSError as error:
            return 125, b'', str(error).encode()


def canonical(path):
    if not re.fullmatch(r'/[A-Za-z0-9_./+-]+', path) or '..' in Path(path).parts or str(Path(path)) != path:
        raise ValueError('unsafe captured path: ' + path)
    return path


def capture(transport, serial, out, plan=None, tag=''):
    out = Path(out)
    (out / 'raw').mkdir(parents=True, exist_ok=False)
    snapshot = dict(schema_version=1, serial=serial, label=tag,
                    captured_at=datetime.now().astimezone().isoformat(timespec='seconds'),
                    readonly=True, complete=False, boot_stable=False, items={}, labels={}, sha={},
                    params={}, pids={}, errors=[], bind_targets=[], mounts=[], init_configs={})
    if not COLLECTION.is_file():
        raise ValueError('collection inventory missing: ' + str(COLLECTION))
    snapshot['collection_sha256'] = sha(COLLECTION.read_bytes())

    def item(name, command, diagnostic=False):
        try:
            code, stdout, stderr = transport.run(command)
        except (OSError, RuntimeError) as error:
            code, stdout, stderr = 125, b'', str(error).encode()
        stdout = stdout.encode() if isinstance(stdout, str) else stdout
        stderr = stderr.encode() if isinstance(stderr, str) else stderr
        relative = 'raw/' + name + '.txt'
        (out / relative).write_bytes(stdout)
        (out / ('raw/' + name + '.stderr.txt')).write_bytes(stderr)
        record = dict(cmd=command, rc=code, raw=relative, raw_sha256=sha(stdout),
                      stderr_raw='raw/' + name + '.stderr.txt', stderr_sha256=sha(stderr),
                      bytes=len(stdout), stderr_bytes=len(stderr), diagnostic=diagnostic)
        snapshot['items'][name] = record
        if not diagnostic and (code != 0 or stderr.strip()):
            snapshot['errors'].append(dict(item=name, reason='nonzero exit or stderr', rc=code))
        return stdout.decode('utf-8', errors='backslashreplace')

    snapshot['boot_id'] = item('boot_id', 'cat /proc/sys/kernel/random/boot_id').strip()
    snapshot['uptime'] = item('uptime', 'cat /proc/uptime').strip()
    snapshot['selinux_enforce'] = item('selinux_enforce', 'getenforce').strip()
    if snapshot['selinux_enforce'] not in ['Enforcing', 'Permissive', 'Disabled']:
        snapshot['errors'].append(dict(item='selinux_enforce', reason='unrecognized mode'))
    mounts = item('proc_mounts', 'cat /proc/mounts')
    item('init_mountinfo', 'cat /proc/1/mountinfo')
    for line in mounts.splitlines():
        fields = line.split()
        if len(fields) != 6:
            snapshot['errors'].append(dict(item='proc_mounts', reason='malformed mount row', text=line))
            continue
        snapshot['mounts'].append(dict(source=fields[0], target=fields[1], filesystem=fields[2], options=fields[3]))
        if fields[1] == '/system' or fields[1].startswith(('/system/', '/data/app/')):
            snapshot['bind_targets'].append(fields[1])
    snapshot['bind_targets'] = sorted(set(snapshot['bind_targets']))
    targets = {path: 'directory' for path in ['/system/android', '/system/lib64/appspawn', '/system/lib64/seccomp']}
    targets.update({'/system/bin/appspawn-x': 'file', '/system/lib64/libwestlake_thread_guard_registry.so': 'file'})
    if plan is not None:
        declared = plan_targets(plan, load_recipe())
        snapshot['plan_target_count'] = len(declared)
        snapshot['plan_sha256'] = sha(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode())
        for row in declared:
            targets[row['target']] = row['kind']
    else:
        snapshot['errors'].append(dict(item='deployment-plan', reason='56-layer target plan not supplied; coverage incomplete'))
    for index, (target, kind) in enumerate(sorted(targets.items())):
        name = 'labels_' + f'{index:03d}'
        text = item(name, read_command(dict(target=target, kind=kind)))
        try:
            for path, label in parse_labels(text, dict(target=target, kind=kind)).items():
                if path in snapshot['labels'] and snapshot['labels'][path] != label:
                    raise ValueError('label changed during overlapping reads: ' + path)
                snapshot['labels'][path] = label
        except ValueError as error:
            snapshot['errors'].append(dict(item=name, reason=str(error)))
    for index, target in enumerate(snapshot['bind_targets']):
        name = 'mount_label_' + f'{index:03d}'
        try:
            canonical(target)
            text = item(name, 'ls -Zd ' + shlex.quote(target))
            parsed = parse_labels(text, dict(target=target, kind='file'))
            for path, label in parsed.items():
                if path in snapshot['labels'] and snapshot['labels'][path] != label:
                    raise ValueError('mounted target label changed: ' + path)
                snapshot['labels'][path] = label
        except ValueError as error:
            snapshot['errors'].append(dict(item=name, reason=str(error)))
    params = item('param_ls', 'param ls')
    for line in params.splitlines():
        match = re.fullmatch(r'\s*\[?([A-Za-z0-9_.-]+)\]?\s*=\s*(.*?)\s*', line)
        if match:
            snapshot['params'][match.group(1)] = match.group(2)
    for key in ['const.cust.config_dir_layer', 'const.cust.follow_x_rules']:
        item('param_' + key.replace('.', '_'), 'param get ' + key, diagnostic=True)
    init_command = ('set -eu; for root in ' + ' '.join(INIT_ROOTS) +
                    '; do if ! test -d "$root"; then printf "ROOT_UNAVAILABLE %s\\n" "$root"; continue; fi; '
                    'files=$(find "$root" -type f -name "*.cfg"); '
                    'if [ -n "$files" ]; then printf "%s\\n" "$files" | while IFS= read -r entry; '
                    'do sha256sum "$entry"; done; fi; done')
    hashes = item('init_cfgs', init_command)
    for line in hashes.splitlines():
        if line.startswith('ROOT_UNAVAILABLE '):
            snapshot['errors'].append(dict(item='init_cfgs', reason=line))
            continue
        match = re.fullmatch(r'([a-f0-9]{64})\s+(/[^\s]+)', line)
        if match:
            snapshot['sha'][canonical(match.group(2))] = match.group(1)
        else:
            snapshot['errors'].append(dict(item='init_cfgs', reason='malformed SHA row', text=line))
    for index, target in enumerate(sorted(path for path in snapshot['sha'] if path.endswith('.cfg'))):
        name = 'init_cfg_content_' + f'{index:03d}'
        item(name, 'cat ' + shlex.quote(target))
        snapshot['init_configs'][target] = dict(sha256=snapshot['sha'][target], content_item=name)
        if snapshot['items'][name]['raw_sha256'] != snapshot['sha'][target]:
            snapshot['errors'].append(dict(item=name, reason='cfg content bytes do not match inventory SHA'))
    layer_list = snapshot['params'].get('const.cust.config_dir_layer')
    roots = LAYERS
    if layer_list:
        try:
            roots = [canonical(part) for part in layer_list.split(':')]
        except ValueError as error:
            snapshot['errors'].append(dict(item='cfg_layer_probe', reason=str(error)))
    snapshot['config_policy_layer_roots'] = roots
    probe = ('for root in ' + ' '.join(map(shlex.quote, roots)) +
             '; do printf "LAYER %s\\n" "$root"; ls -ldZ "$root/lib64/seccomp"; '
             'printf "DIR_PROBE_RC %s\\n" "$?"; ls -ldZ "$root/lib64/seccomp/libapp_filter.z.so"; '
             'printf "FILE_PROBE_RC %s\\n" "$?"; done')
    item('cfg_layer_probe', probe, diagnostic=True)
    for name, command in [
        ('seccomp_sha', 'set -eu; files=$(find /system/lib64/seccomp -type f); printf "%s\\n" "$files" | while IFS= read -r entry; do sha256sum "$entry"; done'),
        ('sandbox_json', 'set -eu; files=$(find /system/etc /system/android/etc -type f \\( -iname "*sandbox*.json" -o -iname "appspawn*.json" \\)); if [ -n "$files" ]; then printf "%s\\n" "$files" | while IFS= read -r entry; do sha256sum "$entry"; done; fi')
    ]:
        text = item(name, command)
        for line in text.splitlines():
            match = re.fullmatch(r'([a-f0-9]{64})\s+(/[^\s]+)', line)
            if match:
                snapshot['sha'][canonical(match.group(2))] = match.group(1)
            elif line.strip():
                snapshot['errors'].append(dict(item=name, reason='malformed SHA row', text=line))
    for name in ['appspawn', 'appspawn-x', 'foundation']:
        command = ('found=$(pidof ' + name + '); code=$?; if [ "$code" = 1 ] && [ -z "$found" ]; '
                   'then printf "NO_PROCESS\\n"; elif [ "$code" != 0 ]; then exit "$code"; else printf "%s\\n" "$found"; fi')
        raw = item('pids_' + name, command).strip()
        pids = [] if raw == 'NO_PROCESS' else raw.split()
        if any(not re.fullmatch(r'[1-9][0-9]*', pid) for pid in pids) or len(set(pids)) != len(pids):
            snapshot['errors'].append(dict(item='pids_' + name, reason='invalid PID list'))
            pids = []
        snapshot['pids'][name] = dict(pids=pids, procs=[])
        for pid in pids:
            prefix = 'proc_' + name + '_' + pid
            proc = dict(pid=pid, exe=item(prefix + '_exe', 'readlink /proc/' + pid + '/exe').strip(),
                        attr_current=item(prefix + '_attr', 'cat /proc/' + pid + '/attr/current').strip(),
                        mountinfo=prefix + '_mountinfo')
            if not proc['exe'].startswith('/') or not re.fullmatch(r'[^:]+:[^:]+:[^:]+:s[0-9]+(?:[:][^\s]+)?', proc['attr_current']):
                snapshot['errors'].append(dict(item=prefix, reason='process exe/domain vanished or malformed'))
            item(proc['mountinfo'], 'cat /proc/' + pid + '/mountinfo')
            proc['environ_keys'] = item(prefix + '_environ_keys',
                'set -eu; envraw=$(cat /proc/' + pid + '/environ | tr "\\000" "\\n"); '
                'printf "%s\\n" "$envraw" | cut -d= -f1 | sort -u').splitlines()
            snapshot['pids'][name]['procs'].append(proc)
    after = item('boot_id_after', 'cat /proc/sys/kernel/random/boot_id').strip()
    snapshot['boot_stable'] = bool(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', snapshot['boot_id']) and after == snapshot['boot_id'])
    if not snapshot['boot_stable']:
        snapshot['errors'].append(dict(item='boot_id_after', reason='missing/changed boot'))
    snapshot['complete'] = not snapshot['errors']
    (out / 'snapshot.json').write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n')
    return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('serial')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--hdc', default=os.environ.get('HDC') or shutil.which('hdc'))
    parser.add_argument('--label', default='')
    args = parser.parse_args(argv)
    try:
        if not args.hdc:
            raise ValueError('set HDC or --hdc; no implicit VM dispatch')
        plan = json.loads(args.plan.read_text()) if args.plan else None
        if plan is not None:
            plan_targets(plan, load_recipe())
        snapshot = capture(HdcTransport(args.hdc, args.serial), args.serial, args.out, plan, args.label)
        print(str(args.out / 'snapshot.json'))
        print('COMPLETE' if snapshot['complete'] else 'INCOMPLETE: inspect errors and raw exit codes')
        return 0 if snapshot['complete'] else 1
    except (ValueError, OSError, KeyError) as error:
        print('SNAPSHOT-REFUSE: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
