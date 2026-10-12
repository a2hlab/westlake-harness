"""Validate pinned, independently collected parameter evidence; never run commands.

The command strings exported here describe read-only observations for the outer
collector. This module only reads local pinned JSON/raw files. A matching record
is evidence validation, not a claim of fresh board access or execution authority.
"""
import hashlib
import json
import os
from pathlib import Path
import re

SCHEMA = 'exact-parameter-observation/v1'
HAP_PATH = '/data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
HOST_ROOT = '/data/app/el2/100/base/org.westlake.imehost'
HAP_SHA = 'df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a'
HOST_PACKAGE = 'org.westlake.imehost'
WINDOW_COMMAND = "hidumper -s WindowManagerService -a '-a'"
SERIALS = {'5cd1e3dd00000000000000000923012c',
           '5ea34a4500000000000000001123012c',
           '61b0657200000000000000000324012c'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
CONTROL = re.compile(r'/data/westlake-demo/toutiao/recovery-attempts/[A-Za-z0-9_.-]+\Z')


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def workspace_root(base):
    if os.environ.get('WORKSPACES'):
        return Path(os.environ['WORKSPACES']).expanduser().resolve()
    # Requests may live in an isolated temporary/output directory. The module
    # remains anchored to its checkout, just like scripts/lab/lab_paths.py.
    for start in (Path(base).resolve(), Path(__file__).resolve().parent):
        for root in [start, *start.parents]:
            if (root / 'westlake-harness').is_dir() or (root / 'westlake-inputs').is_dir():
                return root
    raise ValueError('WORKSPACES cannot be resolved')


def resolve(value, base):
    need(isinstance(value, str) and bool(value), 'evidence path missing')
    if value.startswith('$WORKSPACES/'):
        path = workspace_root(base) / value[len('$WORKSPACES/'):]
    else:
        need('$' not in value, 'unsupported evidence path variable')
        path = Path(value)
        if not path.is_absolute():
            path = Path(base) / path
    need(path.is_file() and not path.is_symlink(), 'evidence is not a regular nonsymlink file: ' + value)
    return path.resolve()


def pin(ref, base):
    need(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'evidence pin requires only path and sha256')
    need(isinstance(ref['sha256'], str) and SHA.fullmatch(ref['sha256']), 'invalid evidence SHA')
    path = resolve(ref['path'], base)
    need(digest(path) == ref['sha256'], 'evidence SHA drift: ' + ref['path'])
    return path


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate JSON field: ' + key)
        value[key] = item
    return value


def read_json(path):
    try:
        return json.loads(Path(path).read_text(), object_pairs_hook=_unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid observation JSON: ' + str(exc)) from exc


def commands(phase, pid=None):
    """Return the exact allowlist in intended capture order; never execute it."""
    need(phase in ('placement', 'running'), 'unknown observation phase')
    result = {'boot_before': 'cat /proc/sys/kernel/random/boot_id',
              'host_owner': 'stat -c %u:%g ' + HOST_ROOT,
              'host_hap': 'sha256sum ' + HAP_PATH}
    if phase == 'running':
        need(type(pid) is int and pid > 1, 'running host PID missing')
        result.update(host_status=f'cat /proc/{pid}/status',
                      host_stat=f'cat /proc/{pid}/stat',
                      host_cmdline=f'cat /proc/{pid}/cmdline',
                      window_dump=WINDOW_COMMAND)
    result['boot_after'] = 'cat /proc/sys/kernel/random/boot_id'
    return result


def _text(raw, kind):
    try:
        return raw.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('non-UTF8 raw ' + kind) from exc


def parse_status(raw, pid, uid, gid):
    fields = {}
    for line in _text(raw, 'host_status').splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        if key in {'Pid', 'Tgid', 'Uid', 'Gid'}:
            need(key not in fields, 'duplicate host status ' + key)
            fields[key] = value.split()
    for key in ('Pid', 'Tgid'):
        need(fields.get(key) == [str(pid)], 'host status ' + key + ' mismatch')
    for key, expected in [('Uid', uid), ('Gid', gid)]:
        need(fields.get(key) == [str(expected)] * 4, 'host status ' + key + ' mismatch')


def parse_birth(raw, pid):
    text = _text(raw, 'host_stat').strip()
    # comm is parenthesized and may itself contain spaces or right parentheses.
    match = re.fullmatch(r'([1-9][0-9]*) \((.*)\) ([A-Za-z]) (.*)', text)
    need(match is not None and int(match[1]) == pid, 'host stat PID/shape mismatch')
    tail = (match[3] + ' ' + match[4]).split()  # field 3 onward
    need(len(tail) >= 20 and re.fullmatch(r'[1-9][0-9]*', tail[19]), 'host stat birth missing')
    return int(tail[19])  # Linux proc stat field 22


def parse_window(raw):
    text = _text(raw, 'window_dump')
    header = ['WindowName', 'DisplayId', 'Pid', 'WinId', 'Type', 'Mode', 'Flag', 'ZOrd']
    need(any(line.split()[:8] == header for line in text.splitlines()), 'WMS column header missing')
    rows = [line.split() for line in text.splitlines() if line.split()[:1] == ['imehost0']]
    need(len(rows) == 1, 'WMS imehost0 must be unique')
    row = rows[0]
    need(len(row) >= 8 and all(re.fullmatch(r'-?[0-9]+', value) for value in row[1:8]), 'WMS imehost0 row malformed')
    pid, wid, zord = int(row[2]), int(row[3]), int(row[7])
    need(pid > 1 and wid > 0 and zord >= 0, 'WMS host/window is not visible')
    return {'host_pid': pid, 'window_id': wid, 'z_order': zord}


def validate(ref, base, expected, phase):
    """Validate all raw evidence against expected target; return normalized data.

    stdout paths resolve relative to the observation JSON. ``control_root`` is
    the requested independent destination, not a claim of on-board existence.
    Placement requires window_id=None; running requires a positive window ID.
    Optional expected host_pid/host_birth also constrain the independently
    observed identity. Synthetic records retain their flag in the result.
    """
    need(isinstance(expected, dict), 'expected parameters must be an object')
    need(phase in ('placement', 'running'), 'unknown observation phase')
    need(expected.get('serial') in SERIALS, 'unsupported expected serial')
    need(isinstance(expected.get('boot_id'), str) and BOOT.fullmatch(expected['boot_id']), 'expected boot missing')
    for key in ('host_uid', 'host_gid'):
        need(type(expected.get(key)) is int and 0 < expected[key] < 2**32, 'expected ' + key + ' missing')
    root = expected.get('control_root')
    need(isinstance(root, str) and CONTROL.fullmatch(root) and root.rsplit('/', 1)[1] not in {'.', '..'}, 'invalid independent control root')
    if phase == 'placement':
        need('window_id' in expected and expected['window_id'] is None, 'placement must have window_id=null')
    else:
        need(type(expected.get('window_id')) is int and expected['window_id'] > 0, 'running window ID missing')
    path = pin(ref, base)
    obs = read_json(path)
    need(isinstance(obs, dict) and obs.get('schema') == SCHEMA, 'wrong observation schema')
    need(type(obs.get('synthetic', False)) is bool, 'synthetic flag must be boolean')
    need(obs.get('serial') == expected['serial'], 'observation serial mismatch')
    need(obs.get('boot_before') == obs.get('boot_after') == expected['boot_id'], 'observation boot stale or unstable')
    for key in ('host_uid', 'host_gid'):
        need(type(obs.get(key)) is int and obs[key] == expected[key], 'observation ' + key + ' mismatch')
    pid = obs.get('host_pid') if phase == 'running' else None
    if phase == 'placement':
        need(all(obs.get(k) is None for k in ('host_pid', 'host_birth', 'window_id')), 'placement cannot claim live host/window')
    else:
        need(type(obs.get('host_birth')) is int and obs['host_birth'] > 0, 'observation host birth missing')
        need(type(obs.get('window_id')) is int and obs['window_id'] == expected['window_id'], 'observation window ID mismatch')
    allow = commands(phase, pid)
    readings = obs.get('readings')
    need(isinstance(readings, dict) and set(readings) == set(allow), 'missing or unknown observation readings')
    raw, normalized = {}, {}
    for kind, command in allow.items():
        row = readings[kind]
        need(isinstance(row, dict) and row.get('command') == command, 'command not allowed: ' + kind)
        for key in ('transport_rc', 'remote_rc'):
            need(type(row.get(key)) is int and row[key] == 0, kind + ' ' + key + ' failed or unknown')
        source = pin(row.get('stdout'), path.parent)
        raw[kind] = source.read_bytes()
        normalized[kind] = {'command': command, 'transport_rc': 0, 'remote_rc': 0,
                            'stdout': dict(row['stdout'])}
    for kind in ('boot_before', 'boot_after'):
        need(_text(raw[kind], kind).strip() == expected['boot_id'], 'raw ' + kind + ' mismatch')
    need(_text(raw['host_owner'], 'host_owner').strip() == f"{expected['host_uid']}:{expected['host_gid']}", 'raw host ownership mismatch')
    hap = _text(raw['host_hap'], 'host_hap').strip().split()
    need(hap == [HAP_SHA, HAP_PATH], 'raw installed HAP identity mismatch')
    birth, window = None, None
    if phase == 'running':
        parse_status(raw['host_status'], pid, expected['host_uid'], expected['host_gid'])
        birth = parse_birth(raw['host_stat'], pid)
        need(birth == obs['host_birth'], 'raw host birth mismatch')
        cmdline = raw['host_cmdline']
        need(cmdline.split(b'\0')[0] == HOST_PACKAGE.encode(), 'raw host cmdline is not exact IMEhost process')
        need(b'\0' in cmdline, 'host cmdline must retain raw NUL separators')
        window = parse_window(raw['window_dump'])
        need(window['host_pid'] == pid and window['window_id'] == expected['window_id'], 'WMS PID/window differs from proc host identity')
        for key, actual in [('host_pid', pid), ('host_birth', birth)]:
            if key in expected:
                need(type(expected[key]) is int and expected[key] == actual, 'expected ' + key + ' mismatch')
    return {'schema': 'exact-parameter-validation/v1', 'phase': phase,
            'serial': expected['serial'], 'boot_id': expected['boot_id'],
            'host_uid': expected['host_uid'], 'host_gid': expected['host_gid'],
            'control_root': root, 'control_root_basis': 'requested independent target, not an existence observation',
            'window_id': expected['window_id'], 'host_pid': pid, 'host_birth': birth,
            'window_z_order': window['z_order'] if window else None,
            'host_hap_sha256': HAP_SHA, 'observation': dict(ref), 'readings': normalized,
            'synthetic': obs.get('synthetic', False), 'device_calls': 0,
            'authority': 'recorded-evidence-validation-only'}
