import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import uuid

from prepare import HERE, NEW, OLD, REPO, SERIAL, TARGETS, save, sha


def check_serial(serial):
    if serial != SERIAL:
        raise ValueError('only approved5cd is supported; no serial prefix or other board')


def approval_path(value, approval_file):
    if not isinstance(value, str) or not value:
        raise ValueError('nonempty approval path required')
    expanded = os.path.expandvars(value)
    if '$' in expanded:
        raise ValueError('unresolved environment variable in approval path')
    path = Path(expanded)
    return path if path.is_absolute() else approval_file.parent / path


def check_approval(approval, action, boot, lane, now=None):
    if approval.get('approved_by') != 'outer(claude)' or approval.get('serial') != SERIAL:
        raise ValueError('outer5cd window approval required;61b/5ea cannot execute')
    if action not in approval.get('actions', []) or approval.get('boot_id') != boot or approval.get('lane') != lane:
        raise ValueError('action/boot/lane not authorized')
    current = now or datetime.now(timezone.utc)
    expires = datetime.fromisoformat(approval['expires_at'])
    if expires.tzinfo is None or expires <= current or not approval.get('window_evidence'):
        raise ValueError('expired/unbound window')
    for name in ['install.py', 'remote-transaction.sh', 'plan.json', 'reference.json']:
        if approval.get('files', {}).get(name) != sha(HERE / name):
            raise ValueError('approved input drift: ' + name)


def parse_probe(text, allowed):
    rows = text.splitlines()
    boot = next((line[5:] for line in rows if line.startswith('BOOT ')), '')
    if not re.fullmatch(r'[0-9a-f-]{36}', boot):
        raise ValueError('boot missing')
    if rows.count('ROOT_RO') != 1 or any(line.startswith('MOUNT_REFUSE ') for line in rows):
        raise ValueError('root not ro or nested system mount')
    metadata = []
    for index, target in enumerate(TARGETS):
        marker = 'FILE ' + target
        if rows.count(marker) != 1:
            raise ValueError('incomplete physical aliases')
        offset = rows.index(marker)
        digest, attrs, context = rows[offset + 1:offset + 4]
        if digest not in allowed or not re.fullmatch(r'0:0:(644|755):1', attrs):
            raise ValueError('alias hash/owner/mode/hardlink differs')
        if context != 'u:object_r:system_lib_file:s0 ' + target:
            raise ValueError('alias SELinux metadata differs')
        metadata.append(attrs + '\n' + context + '\n')
    return boot, metadata


def probe_command():
    return """set -eu
printf 'BOOT '; cat /proc/sys/kernel/random/boot_id
FOUND=0
while read -r dev point type options extra; do
 if test "$point" = /; then case ",$options," in *,ro,*) FOUND=1;; esac; fi
 case "$point" in /system|/system/lib64|/system/lib64/platformsdk|/system/lib64/libinstalls.z.so|/system/lib64/platformsdk/libinstalls.z.so) printf 'MOUNT_REFUSE %s\\n' "$point";; esac
done < /proc/mounts
if test "$FOUND" = 1; then printf 'ROOT_RO\\n'; fi
for TARGET in /system/lib64/libinstalls.z.so /system/lib64/platformsdk/libinstalls.z.so; do
 test -f "$TARGET" && test ! -L "$TARGET"
 printf 'FILE %s\\n' "$TARGET"
 sha256sum "$TARGET" | { read -r digest rest; printf '%s\\n' "$digest"; }
 stat -c '%u:%g:%a:%h' "$TARGET"
 ls -Zd "$TARGET"
done
"""


class Transport:
    def __init__(self, hdc, note, lane, out):
        self.hdc, self.note, self.lane, self.out = str(hdc), str(note), lane, out
        self.count = 0
        self.boot = None
        self.approval = None
        self.action = None

    def run(self, args):
        self.count += 1
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='backslashreplace', timeout=120)
        (self.out / f'{self.count:03d}.txt').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'command exit={result.returncode}; raw={self.count:03d}.txt')
        return result.stdout.strip()

    def shell(self, command):
        return self.run([self.hdc, '-t', SERIAL, 'shell', command])

    def guard(self):
        check_approval(self.approval, self.action, self.boot, self.lane)
        held = self.run(['bash', self.note, 'held', SERIAL]).split()
        if len(held) < 2 or held[0] != self.lane or not held[1].isdigit():
            raise ValueError('missing matching external board lock; keep lock on failure')
        if self.shell('cat /proc/sys/kernel/random/boot_id') != self.boot:
            raise ValueError('boot changed before mutation')

    def mutate(self, command):
        self.guard()
        return self.shell(command)

    def send(self, path, target):
        self.guard()
        self.run([self.hdc, '-t', SERIAL, 'file', 'send', str(path), target])

    def recv(self, source, target):
        self.run([self.hdc, '-t', SERIAL, 'file', 'recv', source, str(target)])

    def reference(self, installer_hashes):
        if self.shell('cat /proc/sys/kernel/random/boot_id') != self.boot:
            raise ValueError('boot drift before identity readback')
        expected = json.loads((HERE / 'reference.json').read_text())['expected_paths']
        paths = sorted(expected)
        actual = {}
        for offset in range(0, len(paths), 24):
            output = self.shell('sha256sum ' + ' '.join(map(shlex.quote, paths[offset:offset + 24])))
            for row in output.splitlines():
                digest, path = row.split(maxsplit=1)
                if not re.fullmatch(r'[0-9a-f]{64}', digest) or path in actual:
                    raise ValueError('invalid/duplicate reference readback')
                actual[path] = digest
        if set(actual) != set(expected):
            raise ValueError('incomplete319 identity readback')
        differences = {path: dict(expected=expected[path], actual=actual[path]) for path in paths
                       if actual[path] not in (installer_hashes if path in TARGETS else {expected[path]})}
        save(self.out / 'identity-readback.json', dict(files=len(actual), differences=differences, hashes=actual))
        if differences:
            raise ValueError('non-installer identity drift; no Boat/runtime cleanup is authorized')
        if self.shell('cat /proc/sys/kernel/random/boot_id') != self.boot:
            raise ValueError('boot drift during identity readback')


def transaction(transport, action, candidate, metadata, state, out):
    remote = state['remote']
    quote = shlex.quote
    if action == 'apply':
        transport.mutate(f'test ! -e {quote(remote)} && mkdir {quote(remote)}')
        for index, text in enumerate(metadata):
            path = out / f'meta-{index}.txt'
            path.write_text(text)
            transport.send(path, remote + '/' + path.name)
        transport.send(HERE / 'remote-transaction.sh', remote + '/remote-transaction.sh')
        state['status'] = 'staged'
        save(out / 'state.json', state)
        transport.mutate(f'sh {quote(remote)}/remote-transaction.sh backup {quote(remote)} {quote(transport.boot)}')
        for index in range(2):
            path = out / f'original-{index}.so'
            transport.recv(remote + f'/backup/{index}.so', path)
            if sha(path) != OLD:
                raise ValueError('persistent host backup changed; no system write')
        transport.send(candidate, remote + '/candidate.so')
    else:
        transport.send(HERE / 'remote-transaction.sh', remote + '/remote-transaction.sh')
    state['status'] = action + '_in_progress'
    save(out / 'state.json', state)
    transport.mutate(f'sh {quote(remote)}/remote-transaction.sh {action} {quote(remote)} {quote(transport.boot)}')
    transport.reference({NEW} if action == 'apply' else {OLD})
    state['status'] = action + '_physical_verified_reboot_pending'
    save(out / 'state.json', state)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['apply', 'rollback', 'reboot'], nargs='?')
    parser.add_argument('--serial', default=SERIAL)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approval', type=Path)
    parser.add_argument('--state', type=Path)
    parser.add_argument('--lane')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--hdc', type=Path)
    args = parser.parse_args(argv)
    check_serial(args.serial)
    approval = json.loads(args.approval.read_text()) if args.approval else None
    if approval is not None and approval.get('serial') != args.serial:
        raise ValueError('CLI serial differs from approval')
    if args.action is None:
        actions = approval.get('actions', []) if approval is not None else ['apply']
        if len(actions) != 1 or actions[0] not in ['apply', 'rollback', 'reboot']:
            raise ValueError('one-command invocation requires exactly one approved action')
        args.action = actions[0]
    workspaces = Path(os.environ.get('WORKSPACES', REPO.parent))
    candidate = workspaces / 'oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so'
    if sha(candidate) != NEW:
        raise ValueError('candidate archive SHA drift')
    plan = json.loads((HERE / 'plan.json').read_text())
    if not args.execute:
        print(json.dumps(dict(dry_run=True, device_access=False, action=args.action, serial=SERIAL, targets=TARGETS,
                              candidate_sha256=NEW, execution_enabled=plan['execution_enabled'], pending=plan['pending']), indent=2))
        return
    if not args.approval:
        parser.error('--execute requires --approval; this does not acquire a lock')
    args.lane = args.lane or approval.get('lane')
    check_approval(approval, args.action, approval.get('boot_id'), args.lane)
    if not args.lane:
        raise ValueError('approval lane required')
    if args.state is None and approval.get('state'):
        args.state = approval_path(approval['state'], args.approval)
    if args.action != 'apply' and args.state is None:
        raise ValueError('original transaction state path required in approval or --state')
    if args.hdc is None:
        configured = approval.get('hdc') or os.environ.get('HDC') or shutil.which('hdc')
        if not configured and sys.platform == 'darwin':
            configured = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
        if not configured:
            raise ValueError('set HDC or approval hdc to a reachable executable/wrapper')
        args.hdc = approval_path(configured, args.approval)
    if not args.hdc.is_file() or not os.access(args.hdc, os.X_OK):
        raise ValueError('HDC executable/wrapper missing or not executable')
    if args.out is None:
        args.out = approval_path(approval['out'], args.approval) if approval.get('out') else (
            HERE / '.artifacts' / ('invocation-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex))
    args.out.mkdir(parents=True, exist_ok=False)
    print('evidence=' + str(args.out), flush=True)
    note = workspaces / 'westlake-harness/scripts/lab/board_note.sh'
    transport = Transport(args.hdc, note, args.lane, args.out)
    transport.boot, transport.approval, transport.action = approval['boot_id'], approval, args.action
    transport.guard()
    boot, metadata = parse_probe(transport.shell(probe_command()), {OLD, NEW} if args.action in ['rollback', 'reboot'] else {OLD})
    if boot != transport.boot:
        raise ValueError('precheck boot drift')
    transport.reference({OLD} if args.action == 'apply' else {OLD, NEW})
    if args.action == 'apply':
        state = dict(serial=SERIAL, boot_before=boot, remote='/data/local/tmp/spare-installer-' + uuid.uuid4().hex,
                     candidate_sha256=NEW, original_sha256=OLD, metadata=metadata, approval_sha256=sha(args.approval),
                     rollback_files=['original-0.so', 'original-1.so'])
    else:
        if not args.state:
            raise ValueError('original transaction --state required')
        state = json.loads(args.state.read_text())
        if approval.get('state_sha256') != sha(args.state):
            raise ValueError('original state not bound by this action approval')
        if state.get('serial') != SERIAL or not re.fullmatch(r'/data/local/tmp/spare-installer-[a-z0-9]+', state.get('remote', '')):
            raise ValueError('foreign original state')
        if metadata != state['metadata']:
            raise ValueError('metadata drift from original state')
        if state.get('rollback_files') != ['original-0.so', 'original-1.so']:
            raise ValueError('wrong rollback inventory')
        for name in state['rollback_files']:
            if sha(args.state.parent / name) != OLD:
                raise ValueError('original host backup drift')
        if args.action == 'reboot' and state.get('status') != 'apply_physical_verified_reboot_pending':
            raise ValueError('reboot requires completed apply, not a partial transaction')
    save(args.out / 'state.json', state)
    if args.action == 'reboot':
        parse_probe(transport.shell(probe_command()), {NEW})
        state['status'] = 'reboot_requested_autonomous_acceptance_pending'
        save(args.out / 'state.json', state)
        transport.mutate('sync; reboot')
        return
    transaction(transport, args.action, candidate, metadata, state, args.out)
    print(json.dumps(dict(status=state['status'], serial=SERIAL, state=str(args.out / 'state.json'))))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print('STOP; retain lock and evidence: ' + str(error), file=sys.stderr)
        sys.exit(1)
