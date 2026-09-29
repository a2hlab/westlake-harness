#!/usr/bin/env python3
"""Item 64. Read-only hdc inventory; all outputs are written on the host."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
SERIALS = ['5ea34a4500000000000000001123012c', '5cd1e3dd00000000000000000923012c', '61b0657200000000000000000324012c']
ROOTS = ['/system/android/lib64', '/system/android/framework', '/system/lib64/westlake/route-a', '/system/lib64/appspawn']
SINGLES = ['/system/lib64/libapk_installer.so', '/system/lib64/platformsdk/libapk_installer.so', '/system/bin/appspawn-x']
BOOT = 'cat /proc/sys/kernel/random/boot_id'
UUID = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$')
HASH = re.compile(r'^([0-9a-f]{64})\s+\*?(.+)$')
TRANSPORT = re.compile(r'Connect server failed|Not match target|No target|Device not found|target.*offline', re.I)

def now():
    return datetime.now(timezone.utc).isoformat()

def hashes(text):
    return {m[2]: m[1] for line in text.splitlines() if (m := HASH.fullmatch(line.strip()))}

def stat_value(text):
    for line in text.splitlines():
        bits = line.split()
        if len(bits) == 4 and all(b.isdigit() for b in bits):
            return dict(zip(['device', 'inode', 'size', 'mtime'], map(int, bits)))
    return None

def linux_dev(device):
    return ((device >> 8) & 0xfff) | ((device >> 32) & 0xfffff000), (device & 0xff) | ((device >> 12) & 0xffffff00)

def maps_rows(text, known_names=()):
    rows = []
    for line in text.splitlines():
        bits = line.split(None, 5)
        if len(bits) != 6 or not re.fullmatch(r'[0-9a-f]+-[0-9a-f]+', bits[0]):
            continue
        path = bits[5]
        clean = path.removesuffix(' (deleted)')
        if not (clean in SINGLES or any(clean.startswith(r + '/') for r in ROOTS) or Path(clean).name in known_names):
            continue
        rows.append({'range': bits[0], 'permissions': bits[1], 'offset': bits[2],
                     'device': bits[3], 'inode': int(bits[4]), 'path': clean, 'deleted': path != clean})
    return rows

def same_inode(row, stat):
    return bool(stat and stat['inode'] == row['inode'] and linux_dev(stat['device']) == tuple(int(b, 16) for b in row['device'].split(':')))

def classify(row, mapped_stat, mapped_sha, root_stat, root_sha, stable):
    if not stable:
        return {'identity': 'process_changed', 'sha256': None}
    if mapped_sha and same_inode(row, mapped_stat):
        return {'identity': 'mapped_object_verified', 'sha256': mapped_sha}
    if root_sha and same_inode(row, root_stat) and not row['deleted']:
        return {'identity': 'process_root_inode_matched', 'sha256': root_sha}
    return {'identity': 'unverified', 'sha256': None}

def start_time(text):
    # comm can contain spaces and parentheses; fields after final ')' start at field 3.
    try:
        return text.rsplit(')', 1)[1].split()[19]
    except (IndexError, AttributeError):
        return None

class Reader:
    def __init__(self, hdc, serial, out):
        if serial not in SERIALS:
            raise ValueError('serial is not allowlisted')
        self.hdc, self.serial, self.out = hdc, serial, out
        out.mkdir(parents=True, exist_ok=False)
        self.commands = []
        self.known_names = set()

    def read(self, name, shell, timeout=60):
        argv = [self.hdc, '-t', self.serial, 'shell', shell]
        begin = now()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or b''
            stderr = e.stderr or b''
            stdout = stdout.decode(errors='replace') if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
            stderr += '\nHOST_TIMEOUT'
            rc = None
        result = {'command': argv, 'begin_utc': begin, 'end_utc': now(), 'returncode': rc,
                  'transport_ok': rc == 0 and not TRANSPORT.search(stdout + stderr),
                  'stdout': stdout, 'stderr': stderr}
        result['transport_ok'] = bool(result['transport_ok'])
        path = self.out / (name + '.json')
        path.write_text(json.dumps(result, indent=2) + '\n')
        self.commands.append(str(path))
        return result

    def process(self, pid, role, ppid):
        prefix = f'{role}-{pid}'
        begin = self.read(prefix + '-stat-before', f'cat /proc/{pid}/stat')
        maps = self.read(prefix + '-maps', f'cat /proc/{pid}/maps')
        self.read(prefix + '-exe', f'readlink /proc/{pid}/exe')
        self.read(prefix + '-mountinfo', f'cat /proc/{pid}/mountinfo')
        rows = maps_rows(maps['stdout'], self.known_names)
        unique = {(r['path'], r['device'], r['inode']): r for r in reversed(rows)}
        reads = []
        # Group reads into one shell request. Each field has a numbered marker, with
        # failures preserved rather than hidden. No remote redirection or temp files.
        commands = []
        for i, row in enumerate(unique.values()):
            reads.append(row)
            paths = {'mapped': f'/proc/{pid}/map_files/{row["range"]}', 'root': f'/proc/{pid}/root{row["path"]}'}
            for kind, path in paths.items():
                q = shlex.quote(path)
                commands.extend([f"printf 'ITEM {i} {kind} stat\\n'", f"stat -L -c '%d %i %s %Y' {q}",
                                 f"printf 'ITEM {i} {kind} hash\\n'", f'sha256sum {q}'])
        batches = []
        for i in range(0, len(commands), 160):
            batches.append(self.read(prefix + f'-mapped-files-{i//160}', '\n'.join(commands[i:i+160])))
        blocks, current = {}, None
        for batch in batches:
            for line in batch['stdout'].splitlines():
                m = re.fullmatch(r'ITEM (\d+) (mapped|root) (stat|hash)', line)
                if m:
                    current = (int(m[1]), m[2], m[3])
                    blocks[current] = []
                elif current is not None:
                    blocks[current].append(line)
        maps_after = self.read(prefix + '-maps-after', f'cat /proc/{pid}/maps')
        stable_maps = bool(maps['transport_ok'] and maps_after['transport_ok'] and rows == maps_rows(maps_after['stdout'], self.known_names))
        after = self.read(prefix + '-stat-after', f'cat /proc/{pid}/stat')
        birth = start_time(begin['stdout'])
        stable = bool(birth and birth == start_time(after['stdout']) and begin['transport_ok'] and after['transport_ok'])
        files = []
        for i, row in enumerate(reads):
            data = dict(row)
            data['offset_zero_ranges'] = [r['range'] for r in rows if (r['path'], r['device'], r['inode']) == (row['path'], row['device'], row['inode']) and int(r['offset'], 16) == 0]
            for kind in ['mapped', 'root']:
                data[kind + '_stat'] = stat_value('\n'.join(blocks.get((i, kind, 'stat'), [])))
                sums = hashes('\n'.join(blocks.get((i, kind, 'hash'), [])))
                data[kind + '_sha256'] = next(iter(sums.values()), None)
            data.update(classify(row, data['mapped_stat'], data['mapped_sha256'], data['root_stat'], data['root_sha256'], stable and stable_maps))
            files.append(data)
        return {'pid': pid, 'ppid': ppid, 'role': role, 'stable_maps': stable_maps, 'start_time': birth, 'stable_process': stable,
                'maps_nonempty': bool(rows), 'maps_line_count': len(maps['stdout'].splitlines()),
                'files': files, 'unverified_files': sum(f['identity'] not in {'mapped_object_verified', 'process_root_inode_matched'} for f in files)}

    def collect(self):
        result = {'serial': self.serial, 'begin_utc': now(), 'files': {}, 'trees': [], 'processes': [], 'status': 'blocked'}
        before = self.read('boot-before', BOOT, 20)
        boot = before['stdout'].strip()
        result['boot_before'] = boot if UUID.fullmatch(boot) else None
        if not before['transport_ok'] or not result['boot_before']:
            result['blocker'] = 'No valid boot identity: hdc transport unavailable or empty/invalid reply'
        else:
            for i, root in enumerate(ROOTS):
                reply = self.read(f'tree-{i}', f'find -L {shlex.quote(root)} -type f -exec sha256sum {{}} +')
                values = hashes(reply['stdout'])
                malformed = [x for x in reply['stdout'].splitlines() if x.strip() and not HASH.fullmatch(x.strip())]
                result['trees'].append({'root': root, 'count': len(values), 'complete': reply['transport_ok'] and not reply['stderr'].strip() and not malformed and bool(values), 'errors': malformed})
                result['files'].update(values)
            singles = self.read('single-files', 'sha256sum ' + ' '.join(map(shlex.quote, SINGLES)))
            result['files'].update(hashes(singles['stdout']))
            self.known_names = {Path(p).name for p in result['files']}
            ps = self.read('process-list', 'ps -A -o PID,PPID,NAME')
            candidates = []
            for line in ps['stdout'].splitlines():
                bits = line.split()
                if len(bits) < 3 or not bits[0].isdigit():
                    continue
                name = bits[2]
                if name == 'appspawn-x' or name == 'com.example.helloworld' or name == 'foundation':
                    role = {'appspawn-x': 'appspawn', 'com.example.helloworld': 'helloworld', 'foundation': 'foundation'}[name]
                    candidates.append((int(bits[0]), role, int(bits[1])))
            # All exact matches retained to avoid hiding duplicate parents/children.
            for pid, role, ppid in candidates:
                result['processes'].append(self.process(pid, role, ppid))
            after = self.read('boot-after', BOOT, 20)
            result['boot_after'] = after['stdout'].strip() if after['transport_ok'] else None
            result['stable_boot'] = result['boot_before'] == result['boot_after']
            # A second manifest pass detects replacement during an unlocked read.
            critical_names = {'liboh_adapter_bridge.so', 'oh-adapter-runtime.jar', 'libwestlake_android_child.z.so', 'libwestlake_android_runtime_provider.so', 'libart.so', 'libopenjdkjvm.so'}
            critical_paths = sorted(set(SINGLES) | {p for p in result['files'] if Path(p).name in critical_names})
            check = self.read('critical-after', 'sha256sum ' + ' '.join(map(shlex.quote, critical_paths)))
            result['critical_after'] = hashes(check['stdout'])
            result['critical_missing'] = [p for p in critical_paths if p not in result['critical_after']]
            result['critical_changed'] = [p for p, sha in result['critical_after'].items() if result['files'].get(p) != sha]
            roles = {p['role'] for p in result['processes'] if p['stable_process'] and p['maps_nonempty']}
            result['missing_process_roles'] = sorted({'appspawn', 'helloworld'} - roles)
            complete = result['stable_boot'] and not result['critical_changed'] and not result['critical_missing'] and all(t['complete'] for t in result['trees']) and all(p in result['files'] for p in SINGLES) and not result['missing_process_roles']
            result['status'] = 'captured' if complete else 'partial'
        result['end_utc'] = now()
        result['commands'] = self.commands
        (self.out / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new host directory; never a device path')
    parser.add_argument('--hdc', default=HDC)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        boards = list(pool.map(lambda s: Reader(args.hdc, s, args.out / s[:8]).collect(), SERIALS))
    manifest = {'task': 64, 'read_only': True, 'collector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'boards': boards}
    (args.out / 'collection.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps([{k: b.get(k) for k in ['serial', 'status', 'boot_before', 'missing_process_roles']} for b in boards], indent=2))
    return 0 if all(b['status'] == 'captured' for b in boards) else 2

if __name__ == '__main__':
    raise SystemExit(main())
