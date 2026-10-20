#!/usr/bin/env python3
"""Offline comparison of existing parent-private APK/native hash receipts."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def compare(root):
    sources, roles = [], {}
    for role in ('5cd', '61b'):
        base = root / role
        blobs = {}
        for suffix in ('argv.json', 'stdout', 'stderr', 'rc'):
            p = base / ('01-apk-so-bracket.' + suffix)
            data = p.read_bytes()
            blobs[suffix] = data
            sources.append({'alias': 'APP_PACKAGE_01/' + str(p.relative_to(root)),
                            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        assert blobs['rc'].strip() == b'0'
        assert not blobs['stderr']
        argv = json.loads(blobs['argv.json'])
        assert len(argv) == 5 and argv[1] == '-t' and argv[3] == 'shell'
        expected_serial = {'5cd': '5cd1e3dd00000000000000000923012c',
                           '61b': '61b0657200000000000000000324012c'}[role]
        assert argv[2] == expected_serial
        pids = set(re.findall(r'/proc/(\d+)/', argv[4]))
        assert len(pids) == 1
        pid = next(iter(pids))
        prefix = '/proc/' + pid + '/root/data/local/tmp/asx/'
        lines = blobs['stdout'].decode().splitlines()
        bookends, files = {}, {}
        for i, line in enumerate(lines):
            if re.fullmatch(r'[BS][01]=.+', line):
                key, value = line.split('=', 1)
                assert key not in bookends
                bookends[key] = value
            if line.startswith('## '):
                kind, path = line[3:].split(' ', 1)
                assert path.startswith(prefix) and kind in ('APK', 'SO')
                key = path[len(prefix):]
                assert key == 'toutiao.apk' if kind == 'APK' else re.fullmatch(r'lib/arm64-v8a/[^/]+\.so', key)
                sha = re.fullmatch(r'([a-f0-9]{64})\s+(.+)', lines[i + 1])
                stat = re.fullmatch(r'(\d+) (\d+) (\d+)', lines[i + 2])
                assert sha and stat and sha[2] == path and key not in files
                files[key] = {'sha256': sha[1], 'bytes': int(stat[1]),
                              'device': int(stat[2]), 'inode': int(stat[3]),
                              'stdout_line': i + 1, 'kind': kind}
        assert set(bookends) == {'B0', 'B1', 'S0', 'S1'}
        assert bookends['B0'] == bookends['B1'] and bookends['S0'] == bookends['S1']
        assert re.fullmatch(r'[a-f0-9-]{36}', bookends['B0']) and int(bookends['S0']) > 0
        assert 'toutiao.apk' in files
        # Individual command errors are redirected to stdout: reject every unparsed line.
        covered = set()
        for item in files.values():
            n = item['stdout_line'] - 1
            covered.update((n, n + 1, n + 2))
        assert all(i in covered or re.fullmatch(r'[BS][01]=.+', line) or not line
                   for i, line in enumerate(lines))
        roles[role] = {'parent_pid': int(pid), 'boot': bookends['B0'],
                       'parent_birth': int(bookends['S0']), 'bookends_equal': True,
                       'file_count': len(files), 'files': files}
    a, b = roles['5cd']['files'], roles['61b']['files']
    rows = []
    for path in sorted(a.keys() | b.keys()):
        left, right = a.get(path), b.get(path)
        equal = bool(left and right and (left['sha256'], left['bytes']) == (right['sha256'], right['bytes']))
        rows.append({'path': path, '5cd': left, '61b': right, 'sha_size_equal': equal,
                     'expected_candidate_vs_baseline_difference': path in (
                         'lib/arm64-v8a/libmffmpeg.so', 'lib/arm64-v8a/libttmplayer.so')})
    for source in sources:
        p = root / source['alias'].removeprefix('APP_PACKAGE_01/')
        assert hashlib.sha256(p.read_bytes()).hexdigest() == source['sha256'], 'source changed'
    return {'schema': 't34-app-package-peer-v1', 'scope': 'Current parent-private files; 5cd retained candidate versus 61b restored baseline, not W03-b candidate generation.',
            'identities': {r: {k: v for k, v in d.items() if k != 'files'} for r, d in roles.items()},
            'apk_equal': a['toutiao.apk']['sha256'] == b['toutiao.apk']['sha256'] and a['toutiao.apk']['bytes'] == b['toutiao.apk']['bytes'],
            'native_count_each': {r: len(d['files']) - 1 for r, d in roles.items()},
            'missing': [x['path'] for x in rows if x['5cd'] is None or x['61b'] is None],
            'unexpected_differences': [x['path'] for x in rows if not x['sha_size_equal'] and not x['expected_candidate_vs_baseline_difference']],
            'equal_unreplaced_native_count': sum(x['sha_size_equal'] and x['path'] != 'toutiao.apk' and not x['expected_candidate_vs_baseline_difference'] for x in rows),
            'unknown': ['Actual child-loaded winners and independent optimized dex files were not collected.', 'No cross-board inode equality is asserted; device/inode values identify each sampled path locally.', 'Boot and parent birth bracket the collection; they do not constitute a file-mutation lock or a new candidate-boot proof.'],
            'rows': rows}, {'alias': 'APP_PACKAGE_01', 'sources': sources}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=Path.home() / '.local/share/westlake/t34-environment-read-20261021/app-package-01')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result, sources = compare(args.source_root)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in [('diff.json', result), ('sources.json', sources)]:
        with (args.out / name).open('x') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('apk_equal', 'native_count_each', 'equal_unreplaced_native_count', 'missing', 'unexpected_differences')}))
