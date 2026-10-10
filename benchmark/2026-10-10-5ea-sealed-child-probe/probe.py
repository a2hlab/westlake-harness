#!/usr/bin/env python3
"""Read-only, boot-bound loader path views; never starts a host or child."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths


TARGETS = (
    '/system/android/lib64/liboh_adapter_bridge.so',
    '/system/android/lib64/liboh_android_runtime.so',
    '/system/bin/appspawn-x',
)
BOOT = '/proc/sys/kernel/random/boot_id'
RECEIPT = '/data/westlake-demo/u13/receipt.env'
PROTOCOL = dict(schema='sealed-child-probe/v1', targets=list(TARGETS),
                process_fields=['stat', 'status', 'cmdline', 'attr/current', 'mountinfo', 'ns/mnt', 'exe'],
                boot_path=BOOT, receipt_path=RECEIPT,
                label_scope='targets and ancestors in each process root',
                discovery='appspawn-x roots and their direct children; explicit PID override')


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def dump(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


PROTOCOL_SHA = sha(dump(PROTOCOL).encode())


def decode_mount(value):
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)


def covering_mounts(text, target):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if '-' not in fields:
            continue
        separator = fields.index('-')
        if separator < 6 or len(fields) < separator + 4:
            continue
        mountpoint = decode_mount(fields[4])
        if not (target == mountpoint or target.startswith(mountpoint.rstrip('/') + '/')):
            continue
        options = fields[5].split(',')
        super_options = fields[separator + 3].split(',')
        rows.append(dict(id=fields[0], parent_id=fields[1], device=fields[2],
                         root=decode_mount(fields[3]), mountpoint=mountpoint,
                         options=options, optional_fields=fields[6:separator],
                         filesystem=fields[separator + 1], source=decode_mount(fields[separator + 2]),
                         super_options=super_options, noexec='noexec' in options + super_options,
                         nosuid='nosuid' in options + super_options, raw=line))
    longest = max((len(row['mountpoint']) for row in rows), default=0)
    return [row for row in rows if len(row['mountpoint']) == longest]


def process_rows(text):
    rows = {}
    for line in text.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
            rows[int(fields[0])] = dict(pid=int(fields[0]), ppid=int(fields[1]), name=fields[2])
    return rows


def identity(text, pid):
    try:
        prefix, fields = text.strip().rsplit(') ', 1)
        if int(prefix.split(' ', 1)[0]) != pid:
            return None
        tail = fields.split()
        return dict(pid=pid, ppid=int(tail[1]), starttime_ticks=int(tail[19]))
    except (ValueError, IndexError):
        return None


def select_processes(rows, host_pids=(), child_pids=()):
    if len(set(host_pids)) != len(host_pids) or len(set(child_pids)) != len(child_pids):
        raise ValueError('duplicate explicit PID')
    named = {pid for pid, row in rows.items() if row['name'].split('/')[-1] == 'appspawn-x'}
    hosts = sorted(host_pids or [pid for pid in named if rows[pid]['ppid'] not in named])
    if any(pid not in named for pid in hosts):
        raise ValueError('requested host PID absent or not appspawn-x')
    children = sorted(child_pids or [pid for pid, row in rows.items() if row['ppid'] in hosts])
    if any(pid not in rows or rows[pid]['ppid'] not in hosts for pid in children):
        raise ValueError('requested child PID absent or not a direct child of selected host')
    return hosts, children


def read_command(operation, path):
    if operation not in ('cat', 'sha256sum', 'ls', 'readlink'):
        raise ValueError('unsupported read operation')
    if not re.fullmatch(r'/[A-Za-z0-9_./+-]+', path) or '..' in Path(path).parts:
        raise ValueError('unsafe read path')
    return ('ls -ldnZ' if operation == 'ls' else operation) + ' ' + shlex.quote(path)


class HdcTransport:
    def __init__(self, executable, serial):
        self.executable, self.serial = executable, serial

    def run(self, command):
        try:
            result = subprocess.run([self.executable, '-t', self.serial, 'shell', command],
                                    capture_output=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            return 124, error.stdout or b'', error.stderr or b'transport timeout'
        except OSError as error:
            return 125, b'', str(error).encode()


class Reads:
    def __init__(self, transport, out):
        self.transport, self.out = transport, Path(out)
        (self.out / 'raw').mkdir(parents=True, exist_ok=False)
        self.items = {}

    def read(self, name, command):
        started_at = datetime.now(timezone.utc).isoformat()
        marker = '__SEALED_PROBE_RC_' + uuid.uuid4().hex + '__'
        wrapped = '( ' + command + ' ); probe_rc=$?; printf "\\n' + marker + '%s\\n" "$probe_rc"'
        host_rc, stdout, stderr = self.transport.run(wrapped)
        match = re.search(rb'\n' + marker.encode() + rb'(\d+)\r?\n\s*$', stdout)
        remote_rc = int(match[1]) if match else None
        payload = stdout[:match.start()] if match else b''
        raw = 'raw/' + name + '.stdout'
        error_raw = 'raw/' + name + '.stderr'
        (self.out / raw).write_bytes(stdout)
        (self.out / error_raw).write_bytes(stderr)
        self.items[name] = dict(command=command, shell_command=wrapped, host_exit=host_rc,
                                remote_exit=remote_rc, available=host_rc == 0 and remote_rc == 0,
                                raw=raw, raw_sha256=sha(stdout), stderr_raw=error_raw,
                                stderr_sha256=sha(stderr), started_at=started_at,
                                finished_at=datetime.now(timezone.utc).isoformat())
        if not self.items[name]['available']:
            return None
        return payload.decode('utf-8', errors='backslashreplace').strip()


def artifact(reads, prefix, root, target, mountinfo):
    visible = root + target
    digest = reads.read(prefix + '-sha', read_command('sha256sum', visible))
    listing = reads.read(prefix + '-ls', read_command('ls', visible))
    digest_match = re.match(r'^([0-9a-fA-F]{64})\s', digest or '')
    label_match = re.search(r'\bu:[^\s:]+:[^\s:]+:s[0-9][^\s]*', listing or '')
    ancestors = {}
    for index, parent in enumerate(reversed(Path(target).parents)):
        path = str(parent)
        ancestors[path] = reads.read(prefix + '-parent-' + str(index), read_command('ls', root + path))
    mounts = covering_mounts(mountinfo, target) if mountinfo is not None else []
    return dict(path=target, observed_via=visible,
                sha256=digest_match[1].lower() if digest_match else None,
                label=label_match[0] if label_match else None, ls_lnZ=listing,
                ancestors=ancestors, covering_mounts=mounts,
                complete=bool(digest_match and label_match and mounts and all(ancestors.values())),
                mounted_view_only=True)


def process(reads, pid, role, discovery):
    prefix = role + '-' + str(pid)
    proc = '/proc/' + str(pid)
    before = identity(reads.read(prefix + '-stat-before', read_command('cat', proc + '/stat')) or '', pid)
    mountinfo = reads.read(prefix + '-mountinfo', read_command('cat', proc + '/mountinfo'))
    status = reads.read(prefix + '-status', read_command('cat', proc + '/status'))
    cmdline = reads.read(prefix + '-cmdline', read_command('cat', proc + '/cmdline'))
    domain = reads.read(prefix + '-domain', read_command('cat', proc + '/attr/current'))
    namespace = reads.read(prefix + '-ns', read_command('readlink', proc + '/ns/mnt'))
    executable = reads.read(prefix + '-exe', read_command('readlink', proc + '/exe'))
    artifacts = [artifact(reads, prefix + '-file-' + str(index), proc + '/root', target, mountinfo)
                 for index, target in enumerate(TARGETS)]
    mountinfo_after = reads.read(prefix + '-mountinfo-after', read_command('cat', proc + '/mountinfo'))
    after = identity(reads.read(prefix + '-stat-after', read_command('cat', proc + '/stat')) or '', pid)
    stable = before is not None and before == after
    discovery_stable = before is not None and (pid == 1 or before['ppid'] == discovery[pid]['ppid'])
    host_verified = role != 'host' or executable == '/system/bin/appspawn-x'
    credentials = {}
    for line in (status or '').splitlines():
        if line.startswith(('Uid:', 'Gid:', 'PPid:')):
            key, value = line.split(':', 1)
            credentials[key] = value.strip()
    return dict(role=role, pid=pid, identity_before=before, identity_after=after,
                pid_stable=stable, discovery_stable=discovery_stable, domain=domain,
                cmdline=cmdline.split('\x00') if cmdline is not None else None,
                credentials=credentials, mount_namespace=namespace, executable=executable,
                mountinfo_stable=mountinfo is not None and mountinfo == mountinfo_after,
                artifacts=artifacts, complete=bool(stable and discovery_stable and host_verified
                                                  and all(key in credentials for key in ('Uid', 'Gid', 'PPid'))
                                                  and domain and namespace and executable
                                                  and mountinfo is not None and mountinfo == mountinfo_after
                                                  and all(row['complete'] for row in artifacts)))


def capture(transport, serial, out, host_pids=(), child_pids=()):
    started_at = datetime.now(timezone.utc).isoformat()
    reads = Reads(transport, out)
    boot_before = reads.read('boot-before', read_command('cat', BOOT))
    enforcing = reads.read('enforce', 'getenforce')
    ps = reads.read('process-list', 'ps -A -o PID,PPID,NAME')
    receipt = reads.read('recover-receipt', read_command('cat', RECEIPT))
    warnings = []
    rows = process_rows(ps or '')
    try:
        hosts, children = select_processes(rows, host_pids, child_pids)
    except ValueError as error:
        hosts, children = [], []
        warnings.append(str(error))
    processes = [process(reads, 1, 'init', rows)]
    processes.extend(process(reads, pid, 'host', rows) for pid in hosts)
    processes.extend(process(reads, pid, 'child', rows) for pid in children)
    if not hosts:
        warnings.append('host unavailable; no process started')
    if not children:
        warnings.append('child unavailable; NOT-COMPARABLE, not permission PASS')
    boot_after = reads.read('boot-after', read_command('cat', BOOT))
    boot_stable = bool(boot_before and re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', boot_before)
                       and boot_before == boot_after)
    receipt_fields = {}
    for line in (receipt or '').splitlines():
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', line):
            key, value = line.split('=', 1)
            receipt_fields[key] = value
    complete = bool(boot_stable and enforcing and ps and hosts and children
                    and all(row['complete'] for row in processes) and not warnings)
    code = 0 if complete else (2 if not boot_stable else 1)
    report = dict(schema=PROTOCOL['schema'], protocol=PROTOCOL, protocol_sha256=PROTOCOL_SHA,
                  tool_sha256=sha(Path(__file__).read_bytes()), serial=serial,
                  captured_at=datetime.now(timezone.utc).isoformat(), readonly=True,
                  started_at=started_at,
                  board_mutations=0, application_launches=0, boot_before=boot_before,
                  boot_after=boot_after, boot_stable=boot_stable, enforce=enforcing,
                  recover_receipt=dict(path=RECEIPT, available=receipt is not None,
                                       fields=receipt_fields, diagnostic_only=True,
                                       current_boot_match=(receipt_fields['boot_id'] == boot_before
                                                           if 'boot_id' in receipt_fields else None)),
                  selected=dict(host_pids=hosts, child_pids=children), processes=processes,
                  requested_pids=dict(host_pids=list(host_pids), child_pids=list(child_pids)),
                  warnings=warnings, observations_complete=complete,
                  unavailable_reads=[name for name, row in reads.items.items() if not row['available']],
                  exit_code=code, items=reads.items,
                  interpretation='observer reads do not prove child-domain dlopen permission or historical state')
    (Path(out) / 'probe.json').write_text(dump(report))
    return report


def load_report(path):
    path = Path(path)
    report = json.loads(path.read_text())
    if report.get('protocol') != PROTOCOL or report.get('protocol_sha256') != PROTOCOL_SHA:
        raise ValueError('NOT-COMPARABLE: protocol differs')
    for item in report['items'].values():
        for key, hash_key in [('raw', 'raw_sha256'), ('stderr_raw', 'stderr_sha256')]:
            raw = (path.parent / item[key]).resolve()
            if path.parent.resolve() not in raw.parents or sha(raw.read_bytes()) != item[hash_key]:
                raise ValueError('raw evidence path/hash mismatch: ' + item[key])
    return report


def compare(paths):
    reports = [load_report(path) for path in paths]
    if len({row['serial'] for row in reports}) != len(reports):
        raise ValueError('duplicate serial in comparison')
    matrix = []
    for report in reports:
        for row in report['processes']:
            for file in row['artifacts']:
                matrix.append(dict(serial=report['serial'], boot_id=report['boot_before'],
                                   role=row['role'], pid=row['pid'], path=file['path'],
                                   sha256=file['sha256'], label=file['label'], domain=row['domain'],
                                   mounts=file['covering_mounts'],
                                   comparable=bool(report['boot_stable'] and row['complete'])))
    differences = []
    for target in TARGETS:
        rows = [row for row in matrix if row['role'] == 'init' and row['path'] == target]
        known = [row for row in rows if row['comparable']]
        for field in ('sha256', 'label', 'mount_restrictions'):
            values = {row['serial']: (row[field] if field != 'mount_restrictions' else
                      [dict(noexec=mount['noexec'], nosuid=mount['nosuid']) for mount in row['mounts']])
                      for row in known}
            if len({dump(value) for value in values.values()}) > 1:
                differences.append(dict(role='init', path=target, field=field, values=values))
    return dict(schema='sealed-child-comparison/v1', protocol_sha256=PROTOCOL_SHA,
                complete=all(row['observations_complete'] for row in reports), matrix=matrix,
                init_differences=differences,
                unavailable=[dict(serial=row['serial'], warnings=row['warnings'],
                                  reads=row['unavailable_reads']) for row in reports
                             if not row['observations_complete']],
                interpretation='compare observed fields; no causal or permission PASS inference')


def main(argv=None, transport_factory=HdcTransport):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', action='append', default=[])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--capture', action='store_true', help='requires a separately authorized idle-board window')
    parser.add_argument('--hdc', default='hdc')
    parser.add_argument('--host-pid', type=int, action='append', default=[])
    parser.add_argument('--child-pid', type=int, action='append', default=[])
    parser.add_argument('--compare', type=Path, nargs='+')
    args = parser.parse_args(argv)
    try:
        if args.compare:
            if args.serial or args.capture or args.host_pid or args.child_pid:
                raise ValueError('--compare is offline and exclusive of capture arguments')
            value = compare(args.compare)
            print(dump(value), end='')
            return 0 if value['complete'] else 1
        if not args.serial or len(set(args.serial)) != len(args.serial):
            raise ValueError('supply distinct full OH serials')
        allowed = lab_paths.boards('oh')
        if any(serial not in allowed for serial in args.serial):
            raise ValueError('serial not in OH whitelist')
        if any(pid <= 1 for pid in args.host_pid + args.child_pid):
            raise ValueError('host/child PID must be greater than 1')
        if len(args.serial) != 1 and (args.host_pid or args.child_pid):
            raise ValueError('explicit PIDs are per-board: use one serial')
        if not args.capture:
            print(dump(dict(dry_run=True, board_access=False, serials=args.serial,
                            protocol=PROTOCOL, protocol_sha256=PROTOCOL_SHA,
                            instructions='no HDC contacted; wait for outer window authorization')), end='')
            return 0
        if args.out is None:
            raise ValueError('--capture requires --out')
        outputs, code = [], 0
        for serial in args.serial:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
            out = args.out / serial / stamp
            report = capture(transport_factory(args.hdc, serial), serial, out, args.host_pid, args.child_pid)
            outputs.append(dict(serial=serial, json=str(out / 'probe.json'), exit_code=report['exit_code']))
            code = max(code, report['exit_code'])
        print(dump(dict(readonly=True, outputs=outputs, exit_code=code)), end='')
        return code
    except (ValueError, OSError, KeyError) as error:
        print('PROBE-REFUSE: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
