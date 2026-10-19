#!/usr/bin/env python3
"""Read exact logging slots; never change process memory or logging settings."""
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
PLAYER = ROOT / 'benchmark/2026-10-19-toutiao-video-playback/candidate-r8/deploy-inputs/libttmplayer.so'
LIBLOG = BASE / 'video-r6-liblog/liblog.so'
PINS = {
    'libttmplayer.so': (PLAYER, '0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'),
    'libopensles_android_compat.so': (ROOT / 'benchmark/2026-10-19-toutiao-video-playback/candidate-r10/deploy-inputs/libopensles_android_compat.so', '5f591f5ed92e608a622ab4b59bb2061a846600d0ac5e5d4698405e6301ac8c3c'),
    'liblog.so': (LIBLOG, 'd8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4'),
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
    expected_path = '/data/local/tmp/asx/' + ('lib/arm64-v8a/' if name == 'libttmplayer.so' else '') + name
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
    slots = [('ANativeWindow_getFormat', 'libttmplayer.so', 4659552, 8), ('ANativeWindow_getWidth', 'libttmplayer.so', 4660048, 8), ('ANativeWindow_getHeight', 'libttmplayer.so', 4660752, 8), ('ANativeWindow_setBuffersGeometry', 'libttmplayer.so', 4661320, 8), ('ANativeWindow_lock', 'libttmplayer.so', 4662416, 8), ('ANativeWindow_release', 'libttmplayer.so', 4662456, 8), ('ANativeWindow_fromSurface', 'libttmplayer.so', 4662920, 8), ('ANativeWindow_unlockAndPost', 'libttmplayer.so', 4663136, 8)]
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
    provider_paths = sorted({r['path'] for got in result['reads'] for r in rows if r['lo'] <= int(got['value'],16) < r['hi'] and r['path'].startswith('/')})
    result['provider_files'] = {}
    for i,path in enumerate(provider_paths):
        identity = read('sha256sum /proc/'+str(a.child)+'/root'+shlex.quote(path)+'; stat -L -c %d:%i /proc/'+str(a.child)+'/root'+shlex.quote(path))
        (out / ('provider-'+str(i)+'-identity.txt')).write_text(identity)
        local=out / ('provider-'+str(i)+'.so')
        board.receive('/proc/'+str(a.child)+'/root'+path,local)
        assert hashlib.sha256(local.read_bytes()).hexdigest()==identity.split()[0]
        result['provider_files'][path]={'identity':identity,'local_file':local.name}
    result['identity_after_reads'] = 'same guarded boot/parent/child births'
    (out / 'reads.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
