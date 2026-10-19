#!/usr/bin/env python3
"""Read exact media network slots; never change process memory or settings."""
import argparse
import hashlib
import json
import re
import shlex
import struct
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'scripts/lab/board_note.sh').is_file())
BASE = Path.home() / '.local/share/westlake/toutiao-resume-20261019'
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths
WORKSPACES = lab_paths.workspaces(ROOT)
PINS = {
    'libmffmpeg.so': (ROOT / 'benchmark/2026-10-19-toutiao-video-playback/candidate-r3/deploy-inputs/libmffmpeg.so', 'd2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4'),
    'libandroid_native_network_compat.so': (WORKSPACES / 'westlake-inputs/seal-artifacts-20261012/sha256/f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e', 'f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e'),
}



def map_rows(text):
    result = []
    for line in text.splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) < 5:
            continue
        lo, hi = (int(x, 16) for x in fields[0].split('-'))
        result.append({'lo': lo, 'hi': hi, 'offset': int(fields[2], 16),
                       'device': fields[3], 'inode': fields[4],
                       'path': fields[5] if len(fields) == 6 else '', 'raw': line})
    return result


def bias_for(name, rows):
    file, digest = PINS[name]
    data = file.read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, 'local ELF pin drift'
    assert data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 183
    phoff = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    segments = []
    for i in range(count):
        typ, flags, off, va, pa, fs, ms, align = struct.unpack_from('<IIQQQQQQ', data, phoff + size * i)
        if typ == 1:
            segments.append((off & ~4095, va & ~4095, (off + fs + 4095) & ~4095))
    expected_path = '/data/local/tmp/asx/' + ('lib/arm64-v8a/' if name == 'libmffmpeg.so' else '') + name
    selected = [r for r in rows if r['path'] == expected_path]
    assert selected and len({(r['device'], r['inode']) for r in selected}) == 1, 'missing or ambiguous ELF mapping'
    common = None
    explained = 0
    for row in selected:
        candidates = {row['lo'] - (va + row['offset'] - off)
                      for off, va, end in segments if off <= row['offset'] < end}
        # musl retains file-backed reservation gaps between PT_LOAD ranges.
        # Such a row supplies no bias evidence; never infer an ELF address from it.
        if not candidates:
            continue
        explained += 1
        common = candidates if common is None else common & candidates
    assert explained >= 2 and common is not None and len(common) == 1, 'ambiguous PT_LOAD bias'
    return common.pop(), expected_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--offline-maps', type=Path)
    p.add_argument('--boot')
    p.add_argument('--parent', type=int)
    p.add_argument('--parent-birth', type=int)
    p.add_argument('--child', type=int)
    p.add_argument('--child-birth', type=int)
    p.add_argument('--tag')
    a = p.parse_args()
    if a.offline_maps:
        rows = map_rows(a.offline_maps.read_text())
        print(json.dumps({n: hex(bias_for(n, rows)[0]) for n in PINS}))
        return
    assert a.boot and re.fullmatch('[0-9a-f-]{36}', a.boot)
    assert all(x and x > 0 for x in [a.parent, a.parent_birth, a.child, a.child_birth])
    assert a.tag and re.fullmatch('video-r[0-9]+-[a-z0-9-]+', a.tag)
    out = BASE / a.tag
    out.mkdir(exist_ok=False)
    sys.path.insert(0, str(ROOT / 'benchmark/2026-09-28-bms-route-deploy/batch'))
    import bms_batch as b
    board = b.Board('61b0657200000000000000000324012c',
                    '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc',
                    'bash ' + shlex.quote(str(ROOT / 'scripts/lab/board_note.sh')),
                    'outer(codex)', out / 'commands')
    board.boot = a.boot
    board.ready()
    guard = (f'set -eu; test "$(cat /proc/sys/kernel/random/boot_id)" = {shlex.quote(a.boot)}; '
             f'r=$(cat /proc/{a.parent}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {a.parent_birth}; '
             f'r=$(cat /proc/{a.child}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {a.child_birth}; '
             f'test "$2" = {a.parent}; ')
    def read(command):
        return board.shell('( ' + guard + command + ' )')[1]
    maps = read(f'cat /proc/{a.child}/maps')
    (out / 'maps-before.txt').write_text(maps)
    rows = map_rows(maps)
    biases = {n: bias_for(n, rows) for n in PINS}
    def file_identity(name, path, label):
        text = read(f'sha256sum /proc/{a.child}/root{path}; stat -L -c %d:%i /proc/{a.child}/root{path}')
        (out / (label + '-' + name + '-identity.txt')).write_text(text)
        lines = text.splitlines()
        assert len(lines) == 2 and lines[0].split()[0] == PINS[name][1], 'actual private-view ELF drift'
        device, inode = (int(v) for v in lines[1].split(':'))
        # Linux dev_t encoding; host os.major() may use the macOS encoding.
        major = ((device >> 8) & 0xfff) | ((device >> 32) & ~0xfff)
        minor = (device & 0xff) | ((device >> 12) & ~0xff)
        for row in rows:
            if row['path'] == path:
                assert tuple(int(v, 16) for v in row['device'].split(':')) == (major, minor)
                assert int(row['inode']) == inode, 'pathname bytes are not the mapped object'
    for name, (bias, path) in biases.items():
        file_identity(name, path, 'before')
    slots = [('media_getaddrinfo_GOT', 'libmffmpeg.so', 4782456, 8), ('media_freeaddrinfo_GOT', 'libmffmpeg.so', 4782944, 8), ('media_socket_GOT', 'libmffmpeg.so', 4785960, 8), ('media_connect_GOT', 'libmffmpeg.so', 4782984, 8), ('media_errno_GOT', 'libmffmpeg.so', 4784960, 8), ('media_getsockopt_GOT', 'libmffmpeg.so', 4780568, 8), ('net_real_getaddrinfo', 'libandroid_native_network_compat.so', 23816, 8), ('net_real_free_after_conversion', 'libandroid_native_network_compat.so', 23824, 8), ('net_real_free_unselected', 'libandroid_native_network_compat.so', 23832, 8), ('net_real_socket', 'libandroid_native_network_compat.so', 23840, 8), ('net_real_connect', 'libandroid_native_network_compat.so', 23848, 8)]
    result = {'boot': a.boot, 'parent': a.parent, 'parent_birth': a.parent_birth,
              'child': a.child, 'child_birth': a.child_birth,
              'biases': {n: hex(v[0]) for n, v in biases.items()},
              'reads': [], 'memory_writes': 0, 'playback': 'unknown', 'audio': 'unknown'}
    for label, name, offset, width in slots:
        address = biases[name][0] + offset
        assert address % width == 0
        assert any(r['lo'] <= address and address + width <= r['hi'] for r in rows)
        value = read(f'dd if=/proc/{a.child}/mem bs={width} skip={address // width} count=1 2>/dev/null | od -An -tx{width}').strip()
        assert re.fullmatch('[0-9a-fA-F]{' + str(width * 2) + '}', value), 'incomplete or truncated memory read'
        integer = int(value, 16)
        result['reads'].append({'label': label, 'address': hex(address), 'width': width,
                                'value': hex(integer), 'value_maps': [r['raw'] for r in rows if r['lo'] <= integer < r['hi']]})
        (out / 'reads.json').write_text(json.dumps(result, indent=2) + '\n')
    after = read(f'cat /proc/{a.child}/maps')
    (out / 'maps-after.txt').write_text(after)
    after_rows = map_rows(after)
    for name, (bias, path) in biases.items():
        assert [r for r in rows if r['path'] == path] == [r for r in after_rows if r['path'] == path], 'relevant mappings changed during reads'
        file_identity(name, path, 'after')
    values = {r['label']: int(r['value'], 16) for r in result['reads']}
    expected = {'media_getaddrinfo_GOT': biases['libandroid_native_network_compat.so'][0] + 0x23f4,
                'media_freeaddrinfo_GOT': biases['libandroid_native_network_compat.so'][0] + 0x2a00}
    result['binding_checks'] = {name: {'expected': hex(address), 'actual': hex(values[name]), 'match': values[name] == address} for name, address in expected.items()}
    # Preserve actual provider identities for non-mandatory network slots too.
    provider_paths = sorted({r['path'] for item in result['reads']
                             for r in after_rows if r['lo'] <= int(item['value'], 16) < r['hi']
                             and r['path'].startswith('/') and not r['path'].endswith(' (deleted)')})
    result['resolved_provider_files'] = {}
    for index, path in enumerate(provider_paths):
        private_path = shlex.quote(f'/proc/{a.child}/root{path}')
        identity = read(f'sha256sum {private_path}; stat -L -c %d:%i {private_path}')
        (out / f'resolved-provider-{index}.txt').write_text(identity)
        lines = identity.splitlines()
        assert len(lines) == 2 and re.fullmatch('[0-9a-f]{64}', lines[0].split()[0])
        device, inode = map(int, lines[1].split(':'))
        major = ((device >> 8) & 0xfff) | ((device >> 32) & ~0xfff)
        minor = (device & 0xff) | ((device >> 12) & ~0xff)
        assert all(int(r['inode']) == inode and tuple(int(x, 16) for x in r['device'].split(':')) == (major, minor)
                   for r in after_rows if r['path'] == path)
        result['resolved_provider_files'][path] = {'sha256': lines[0].split()[0], 'device_inode': lines[1]}
    # Native loader resets environ in this runtime: retain only selected shell assignments,
    # never claim they establish the child's effective getenv values.
    run = read(f'cat /proc/{a.parent}/root/data/local/tmp/asx/run.sh')
    result['parent_run_network_assignments'] = [line for line in run.splitlines()
        if line.startswith(('export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=', 'export WESTLAKE_ANDROID_NATIVE_INHERIT='))]
    result['zero_cached_pointer_meaning'] = 'may be uncalled; not itself a failure'
    result['identity_after_reads'] = 'same guarded boot/parent/child births'
    (out / 'reads.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not all(result['binding_checks'][name]['match'] for name in ('media_getaddrinfo_GOT', 'media_freeaddrinfo_GOT')):
        sys.exit('NETWORK_BINDING_MISMATCH: preserved reads; candidate failed, original-plan rollback required')


if __name__ == '__main__':
    main()
