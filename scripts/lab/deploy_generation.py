#!/usr/bin/env python3
"""Deploy an OH6.1 generation with deployment-time identity checks. Mac dispatches device I/O through a2hlab.

No compilation, APK replacement, installer update or automatic boot service.
State is per serial + boot; failed activation rolls back only mounts owned here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import tarfile
import time

SERIALS = {'5ea34a4500000000000000001123012c', '5cd1e3dd00000000000000000923012c',
           '61b0657200000000000000000324012c'}
GEN = '6cb40cd610ec29a69e320b8cc7d766ccffc675cbd7e94b709cc5d2462b9cddb0'
BRIDGE = '84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a'
APPS = [('helloworld', 'com.example.helloworld'), ('zigzag', 'com.a2hlab.bridge.zigzag'),
        ('wikipedia', 'org.wikipedia')]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(value, indent=2) + '\n'); temp.replace(path)

def load_package(package):
    m = json.loads((package / 'package.json').read_text())
    if not re.fullmatch('[0-9a-f]{64}', m['generation']): raise ValueError('invalid generation')
    targets = []
    for name, digest in m['files'].items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or (package / p).is_symlink():
            raise ValueError('unsafe package member')
        if sha(package / p) != digest: raise ValueError('package SHA mismatch: ' + name)
    receipt = 'receipts/ROUTE_A_INPUTS.json'
    if receipt in m['files'] and m['files'][receipt] != m['generation']:
        raise ValueError('generation is not bound to sealed Route-A inputs')
    for row in m['mounts']:
        source, target = row['source'], row['target']
        if source not in m['files'] and not any(x.startswith(source + '/') for x in m['files']):
            raise ValueError('unsealed mount source')
        if not re.fullmatch(r'/(system|data/app/el1/bundle/public/com\.a2hlab\.bridge\.zigzag)/[A-Za-z0-9_./-]+', target) or '..' in Path(target).parts:
            raise ValueError('unsafe mount target')
        targets.append(target)
    if len(targets) != len(set(targets)): raise ValueError('duplicate mount target')
    bridge = m['files']['payload/android/lib64/liboh_adapter_bridge.so']
    if m.get('runtime_identity') == 'deployment-only':
        if m.get('bridge_sha256') != bridge or m['live_hashes'].get('/system/android/lib64/liboh_adapter_bridge.so') != bridge:
            raise ValueError('bridge version differs from deployment manifest')
    elif bridge != BRIDGE:
        raise ValueError('wrong stage/accept-want bridge')
    return m

def check_maps(text, generation=GEN):
    found = {n: [] for n in ['libart.so', 'libopenjdkjvm.so', 'liboh_adapter_bridge.so']}
    for line in text.splitlines():
        f = line.split()
        if len(f) >= 6 and Path(f[-1]).name in found and int(f[2], 16) == 0:
            found[Path(f[-1]).name].append(f[-1])
    route = '/system/lib64/westlake/route-a/' + generation + '/'
    passed = all(found[n] == [route + n] for n in ['libart.so', 'libopenjdkjvm.so'])
    passed = passed and bool(found['liboh_adapter_bridge.so']) and set(found['liboh_adapter_bridge.so']) == {'/system/android/lib64/liboh_adapter_bridge.so'}
    return {'passed': passed, 'offset_zero_instances': found}

def rollback_order(state, boot, top_mounts):
    if state['boot_id'] != boot: raise ValueError('rollback belongs to a different boot')
    rows = []
    for row in state['mounted']:
        # mountinfo roots are relative to /data, not /.
        expected = state['remote'][len('/data'):] + '/' + row['source']
        if top_mounts.get(row['target']) != expected:
            raise ValueError('mount changed since deployment: ' + row['target'])
        rows.append(row)
    return list(reversed(rows))

def replacement_source(m, target):
    if not target.endswith('.so') and target != '/system/bin/appspawn-x':
        raise ValueError('replacement must be a declared native library or appspawn-x: ' + target)
    rows = sorted(m['mounts'], key=lambda r: len(r['target']), reverse=True)
    for row in rows:
        if target == row['target'] or target.startswith(row['target'] + '/'):
            source = row['source'] + target[len(row['target']):]
            if source in m['files']: return source
    raise ValueError('replacement target has no package file: ' + target)


def validate_replacement(old, new, target):
    if old.get('runtime_identity') != 'deployment-only' or new.get('runtime_identity') != 'deployment-only':
        raise ValueError('single-file mode requires an unlocked generation')
    if old['generation'] != new['generation'] or old['mounts'] != new['mounts'] or old['prerequisites'] != new['prerequisites']:
        raise ValueError('single-file replacement changes generation, mounts or platform')
    source = replacement_source(new, target)
    changed = {k for k in old['files'].keys() | new['files'].keys() if old['files'].get(k) != new['files'].get(k)}
    if changed != {source}: raise ValueError('replacement must change exactly one package file: ' + str(sorted(changed)))
    changed_live = {k for k in old['live_hashes'].keys() | new['live_hashes'].keys() if old['live_hashes'].get(k) != new['live_hashes'].get(k)}
    if changed_live != {target} or new['live_hashes'][target] != new['files'][source]:
        raise ValueError('replacement SHA/target manifest mismatch: ' + target)
    return source


class Deployment:
    def __init__(self, args, m, b):
        self.a, self.m, self.b = args, m, b
        self.gen = m['generation']
        self.package = args.package
        self.root = args.state_root / args.serial
        self.out = self.root / ('attempt-' + str(time.time_ns()))
        self.out.mkdir(parents=True)
        tools = Path(args.tools)
        self.board = b.Board(args.serial, str(tools / 'hdc_mac.sh'), 'mac ' + shlex.quote(str(tools / 'board_note.sh')), args.lane, self.out / 'commands')
        self.board.ready()
        self.statepath = self.root / (self.board.boot + '-' + self.gen[:12] + '.json')
        legacy = self.root / (self.board.boot + '.json')
        if not self.statepath.exists() and legacy.exists():
            old = json.loads(legacy.read_text())
            if old.get('generation') == self.gen: self.statepath = legacy
        self.d = json.loads(self.statepath.read_text()) if self.statepath.exists() else None
    def shell(self, text, **kw): return self.board.shell(text, **kw)[1]
    def hashes(self, paths):
        if not paths: return {}
        text = self.shell('sha256sum ' + ' '.join(shlex.quote(p) for p in paths))
        result = {}
        for line in text.splitlines():
            f = line.split()
            if len(f) == 2 and re.fullmatch('[0-9a-f]{64}', f[0]): result[f[1]] = f[0]
        if set(result) != set(paths): raise RuntimeError('incomplete SHA readback')
        return result
    def ps(self): return self.b.processes(self.shell('ps -A -o PID,PPID,UID,NAME'))
    def record(self): save(self.statepath, self.d)
    def top_mounts(self):
        text = self.shell('cat /proc/self/mountinfo')
        (self.out / 'mountinfo.txt').write_text(text)
        return {f[4]: f[3] for f in (l.split() for l in text.splitlines())}
    def stop(self):
        for key, pkg in APPS:
            data = self.b.parse_bundle(self.shell('bm dump -n ' + pkg), pkg)
            if not self.b.cold_stop(self.board, pkg, data['uid'], self.out, 'stop-' + key + '-' + str(time.time_ns())):
                raise RuntimeError('cold stop failed: ' + pkg)
        rows = [r for r in self.ps() if r['name'] == 'appspawn-x']
        if any(r['uid'] != 0 for r in rows): raise RuntimeError('other Android children are live; stop them before deployment')
        self.shell('begetctl stop_service appspawn-x')
        for _ in range(20):
            if not any(r['name'] == 'appspawn-x' for r in self.ps()): return
            time.sleep(.2)
        raise RuntimeError('appspawn-x did not stop')
    def start(self, digest):
        self.shell('begetctl start_service appspawn-x')
        for _ in range(20):
            rows = [r for r in self.ps() if r['name'] == 'appspawn-x' and r['uid'] == 0]
            if len(rows) == 1:
                pid = rows[0]['pid']; time.sleep(.5)
                if self.hashes([f'/proc/{pid}/exe'])[f'/proc/{pid}/exe'] != digest: raise RuntimeError('wrong live parent')
                self.shell('chown 0:6005 /dev/unix/socket/AppSpawnX && chmod 0660 /dev/unix/socket/AppSpawnX && chcon u:object_r:appspawn_socket:s0 /dev/unix/socket/AppSpawnX')
                if self.shell("stat -c '%a:%u:%g:%C' /dev/unix/socket/AppSpawnX") != '660:0:6005:u:object_r:appspawn_socket:s0': raise RuntimeError('socket identity mismatch')
                return pid
            time.sleep(.3)
        raise RuntimeError('parent failed to start')
    def verify_mounts(self):
        tops = self.top_mounts()
        for row in reversed(self.d.get('single_replacements', [])):
            if tops.get(row['target']) != row['remote'][len('/data'):]:
                raise RuntimeError('replacement mount changed externally: ' + row['target'])
            tops[row['target']] = row['previous_root']
        return rollback_order(self.d, self.board.boot, tops)

    def rollback_single(self, verify=True):
        rows = self.d.get('single_replacements', [])
        if not rows: raise RuntimeError('no single-file replacement to roll back')
        row = rows[-1]
        current = self.top_mounts().get(row['target'])
        if current not in [row['remote'][len('/data'):], row['previous_root']]:
            raise RuntimeError('replacement mount changed externally: ' + row['target'])
        old_package = Path(row['previous_package'])
        old = load_package(old_package)
        if sha(old_package / 'package.json') != row['previous_package_sha256']:
            raise RuntimeError('rollback package changed')
        self.stop()
        if current == row['remote'][len('/data'):]: self.shell('umount ' + shlex.quote(row['target']))
        old_digest = old['files'][replacement_source(old, row['target'])]
        if self.hashes([row['target']])[row['target']] != old_digest:
            raise RuntimeError('single-file rollback SHA mismatch: ' + row['target'])
        rows.pop()
        self.package, self.m = old_package, old
        self.d['package_path'] = str(old_package)
        self.d['package_sha256'] = row['previous_package_sha256']
        self.d['parent_pid'] = self.start(old['live_hashes']['/system/bin/appspawn-x'])
        self.d['status'] = 'active'; self.record()
        if verify: self.verify()

    def replace(self, target):
        if not self.d or self.d['status'] != 'active_verified':
            raise RuntimeError('single-file mode requires a verified resident generation')
        old_package = Path(self.d['package_path'])
        if old_package == self.package: raise ValueError('keep the prior package intact; use a separate updated package')
        old = load_package(old_package)
        if sha(old_package / 'package.json') != self.d['package_sha256']: raise ValueError('resident package changed')
        source = validate_replacement(old, self.m, target)
        self.verify_mounts()
        if self.hashes(list(old['live_hashes'])) != old['live_hashes']: raise RuntimeError('resident SHA mismatch before replacement')
        if self.hashes([target])[target] != old['files'][replacement_source(old, target)]:
            raise RuntimeError('declared replacement target SHA mismatch before replacement')
        remote = self.d['remote'] + '/single-' + str(time.time_ns()) + '.so'
        self.board.send(self.package / source, remote)
        if self.hashes([remote])[remote] != self.m['files'][source]: raise RuntimeError('replacement staging SHA mismatch: ' + target)
        mode = '0755' if target == '/system/bin/appspawn-x' else '0644'
        self.shell('chmod ' + mode + ' ' + remote + ' && chcon u:object_r:system_file:s0 ' + remote)
        self.stop()
        row = {'target': target, 'remote': remote, 'previous_root': self.top_mounts().get(target),
               'previous_package': str(old_package), 'previous_package_sha256': self.d['package_sha256']}
        self.d.setdefault('single_replacements', []).append(row)
        self.d['status'] = 'replacing'; self.record()  # persist intent before the bind
        try:
            self.shell('mount --bind ' + remote + ' ' + shlex.quote(target))
            self.d['package_path'] = str(self.package)
            self.d['package_sha256'] = sha(self.package / 'package.json')
            self.d['parent_pid'] = self.start(self.m['live_hashes']['/system/bin/appspawn-x'])
            self.d['status'] = 'active'; self.record()
            self.verify()
        except Exception:
            try:
                # Keep failure evidence separate from the recovery smoke test.
                self.out = self.root / ('recovery-' + str(time.time_ns())); self.out.mkdir()
                self.rollback_single()
            except Exception as error:
                self.d['rollback_error'] = str(error); self.record()
            raise

    def rollback(self):
        if not self.d or self.d['status'] == 'rolled_back': raise RuntimeError('no active deployment in this boot')
        while self.d.get('single_replacements'): self.rollback_single(verify=False)
        tops = self.top_mounts()
        pending = self.d.get('pending_mount')
        if pending:
            expected = self.d['remote'][len('/data'):] + '/' + pending['source']
            if tops.get(pending['target']) == expected:
                if pending not in self.d['mounted']: self.d['mounted'].append(pending)
            elif tops.get(pending['target']) != self.d['pending_previous_root']:
                raise RuntimeError('pending mount changed externally')
            self.d.pop('pending_mount'); self.d.pop('pending_previous_root'); self.record()
        rows = rollback_order(self.d, self.board.boot, tops)
        self.stop()
        for row in rows:
            self.shell('umount ' + shlex.quote(row['target']))
            self.d['mounted'].remove(row); self.record()
        if self.hashes(list(self.d['before'])) != self.d['before']: raise RuntimeError('rollback SHA mismatch')
        self.d['parent_pid'] = self.start(self.d['before']['/system/bin/appspawn-x'])
        self.d['status'] = 'rolled_back'; self.record()
    def verify(self):
        expected = self.m['live_hashes']
        if self.hashes(list(expected)) != expected: raise RuntimeError('active generation hashes differ')
        parents = [r for r in self.ps() if r['name'] == 'appspawn-x' and r['uid'] == 0]
        if len(parents) != 1: raise RuntimeError('no unique active appspawn parent')
        pid = parents[0]['pid']
        self.d['parent_pid'] = pid
        if self.hashes([f'/proc/{pid}/exe'])[f'/proc/{pid}/exe'] != expected['/system/bin/appspawn-x']: raise RuntimeError('parent is not this generation')
        if self.hashes(list(self.d['installer_before'])) != self.d['installer_before']: raise RuntimeError('installer changed')
        self.top_mounts()
        # Exact top mounts also prove a repeat invocation does not stack binds.
        self.verify_mounts()
        out = self.out / 'helloworld'; out.mkdir()
        pkg = APPS[0][1]; parsed = self.b.parse_bundle(self.shell('bm dump -n ' + pkg), pkg)
        if not self.b.cold_stop(self.board, pkg, parsed['uid'], out): raise RuntimeError('HelloWorld cold-stop failed')
        remote = self.d['remote'] + '/smoke-' + str(time.time_ns()); self.shell('mkdir ' + remote)
        rec = {'package': pkg}
        self.b.desktop_launch(self.board, {'package': pkg, 'launch_activity': parsed['desktop_activity']}, remote, out, rec)
        time.sleep(4)
        children = [r for r in self.ps() if r['uid'] == parsed['uid'] and r['ppid'] == pid]
        if len(children) != 1: raise RuntimeError('no unique HelloWorld child under deployed parent')
        child = children[0]['pid']; maps = self.shell(f'cat /proc/{child}/maps')
        (out / 'maps.txt').write_text(maps)
        gate = check_maps(maps, self.gen)
        paths = {f'/proc/{child}/root' + p: digest for p, digest in expected.items()}
        paths[f'/proc/{child}/exe'] = expected['/system/bin/appspawn-x']
        actual = self.hashes(list(paths)); save(out / 'sha256.json', actual)
        gate.update({'child_pid': child, 'parent_pid': pid, 'sha256_passed': actual == paths})
        save(out / 'gate.json', gate)
        if not gate['passed'] or not gate['sha256_passed']: raise RuntimeError('child maps/SHA gate failed')
        self.b.capture(self.board, remote + '/final.jpeg', out / 'final.jpeg')
        self.d['verification'] = str(out); self.d['status'] = 'active_verified'; self.record()
    def deploy(self):
        if self.d and self.d['status'] != 'rolled_back':
            if self.d['package_sha256'] != sha(self.package / 'package.json'): raise RuntimeError('different package active in this boot')
            if self.d['status'] not in ['active', 'active_verified']: raise RuntimeError('interrupted activation; run --rollback first')
            self.verify(); return
        # Read-only compatibility checks before any write.
        if self.hashes(list(self.m['prerequisites'])) != self.m['prerequisites']: raise RuntimeError('platform ABI prerequisites differ')
        for _, pkg in APPS: self.b.parse_bundle(self.shell('bm dump -n ' + pkg), pkg)
        for row in self.m['mounts']:
            if row['target'] != '/system/lib64/westlake/route-a/' + self.gen:
                self.shell('test -e ' + shlex.quote(row['target']))
        route = '/system/lib64/westlake/route-a/' + self.gen
        if route in self.top_mounts(): raise RuntimeError('generation route already mounted outside this transaction')
        # Current files under the future directory mount, plus every direct bind target.
        before_paths = ['/system/android/' + x[len('payload/android/'):] for x in self.m['files'] if x.startswith('payload/android/')]
        before_paths += [x['target'] for x in self.m['mounts'] if x['target'] not in ['/system/android', route]]
        before = self.hashes(sorted(set(before_paths)))
        installers = ['/system/lib64/libapk_installer.so', '/system/lib64/platformsdk/libapk_installer.so']
        remote = '/data/local/tmp/westlake-generation-' + self.gen[:12] + '-' + self.board.boot + '-' + str(time.time_ns())
        self.d = {'serial': self.a.serial, 'boot_id': self.board.boot, 'generation': self.gen, 'package_path': str(self.package), 'package_sha256': sha(self.package / 'package.json'), 'remote': remote, 'before': before, 'installer_before': self.hashes(installers), 'mounted': [], 'status': 'staging'}
        self.record()
        self.shell('mkdir ' + remote)
        archive = self.out / 'payload.tar'
        with tarfile.open(archive, 'w') as tar:
            for name in self.m['files']:
                if name.startswith('payload/'): tar.add(self.package / name, arcname=name)
        self.board.send(archive, remote + '/payload.tar')
        self.shell('tar -xf ' + remote + '/payload.tar -C ' + remote, timeout=180)
        staged = {remote + '/' + n: h for n, h in self.m['files'].items() if n.startswith('payload/')}
        if self.hashes(list(staged)) != staged: raise RuntimeError('staging SHA mismatch')
        self.shell('find ' + remote + '/payload -type d -exec chmod 0755 {} \\; && chmod 0755 ' + remote + '/payload/runtime/appspawn-x && chcon -R u:object_r:system_file:s0 ' + remote + '/payload')
        self.stop()
        try:
            root = next(l.split() for l in self.shell('cat /proc/mounts').splitlines() if l.split()[1] == '/')
            readonly = 'ro' in root[3].split(',')
            if readonly: self.shell('mount -o remount,rw /')
            try: self.shell('mkdir -p ' + route + ' && chcon u:object_r:system_file:s0 ' + route)
            finally:
                if readonly: self.shell('mount -o remount,ro /')
            self.d['status'] = 'activating'; self.record()
            for row in self.m['mounts']:
                self.d['pending_mount'] = row
                self.d['pending_previous_root'] = self.top_mounts().get(row['target'])
                self.record()
                self.shell('mount --bind ' + remote + '/' + row['source'] + ' ' + row['target'])
                self.d['mounted'].append(row)
                self.d.pop('pending_mount'); self.d.pop('pending_previous_root'); self.record()
            self.d['parent_pid'] = self.start(self.m['live_hashes']['/system/bin/appspawn-x'])
            self.d['status'] = 'active'; self.record()
            self.verify()
        except Exception:
            # Never write after a boot/lock/transport loss; guarded rollback refuses it.
            try: self.rollback()
            except Exception as error:
                self.d['rollback_error'] = str(error); self.record()
            raise
        archive.unlink()

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('serial', choices=sorted(SERIALS)); p.add_argument('package', type=Path)
    mode = p.add_mutually_exclusive_group(); mode.add_argument('--rollback', action='store_true'); mode.add_argument('--dry-run', action='store_true')
    p.add_argument('--replace', metavar='ABSOLUTE_TARGET', help='one-file replacement from a separately updated package; with --rollback undo the last replacement')
    p.add_argument('--lane', default=os.environ.get('WESTLAKE_LANE', 'cx-t0'))
    p.add_argument('--tools', default='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools')
    p.add_argument('--state-root', type=Path, default=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state'))
    a = p.parse_args(argv); a.package = a.package.resolve()
    m = load_package(a.package)
    if a.dry_run:
        print(json.dumps({'passed': True, 'generation': m['generation'], 'serial': a.serial, 'file_count': len(m['files']), 'mounts': m['mounts'], 'device_io': False}, indent=2)); return
    if platform.system() == 'Darwin':
        command = ['python3', str(Path(__file__).resolve()), a.serial, str(a.package), '--lane', a.lane, '--tools', a.tools, '--state-root', str(a.state_root.resolve())]
        if a.rollback: command.append('--rollback')
        if a.replace: command.extend(['--replace', a.replace])
        raise SystemExit(subprocess.call(['orb', '-m', 'a2hlab', 'bash', '-lc', shlex.join(command)]))
    sys.path.insert(0, str(a.package / 'tools'))
    import bms_batch as b
    d = Deployment(a, m, b)
    if a.rollback and a.replace:
        if not d.d or not d.d.get('single_replacements') or d.d['single_replacements'][-1]['target'] != a.replace:
            raise RuntimeError('rollback target is not the last replacement')
        d.rollback_single()
    elif a.rollback: d.rollback()
    elif a.replace: d.replace(a.replace)
    else: d.deploy()
    print(json.dumps({'state': str(d.statepath), 'evidence': str(d.out), 'status': d.d['status']}, indent=2))

if __name__ == '__main__': main()
