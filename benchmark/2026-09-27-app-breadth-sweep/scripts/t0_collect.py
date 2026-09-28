"""Bounded T0 collection experiment. No automatic visual verdicts."""
import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

SERIAL = '5ea34a4500000000000000001123012c'
TOOLS = '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/'
HDC = TOOLS + 'hdc_mac.sh'
W = Path('/home/dspfac/a2hlab/source-closure/verify')
ERROR = re.compile(r'[F]atal signal|[S]IGSEGV|[S]IGABRT|[c]annot locate symbol|[E]rror relocating|[s]ymbol not found|[U]nsatisfiedLink|[F]ATAL EXCEPTION')


def filter_hilog(raw, pid, start, end):
    lines = []
    for line in raw.splitlines():
        m = re.match(r'^\s*(\d+\.\d+)\s+(\d+)\s+\d+\s+', line)
        if (m and int(m[2]) == pid and start <= float(m[1]) <= end
                and 'HDC_LOG' not in line and 'ExecuteCommand' not in line and ERROR.search(line)):
            lines.append(line)
    return '\n'.join(lines) + ('\n' if lines else '')


def stack_sections(raw, pid):
    return re.findall(r'----- pid ' + str(pid) + r' at .*?----- end ' + str(pid) + r' -----', raw, re.S)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


class Board:
    def __init__(self, out):
        self.out = out

    def ready(self):
        p = subprocess.run(['mac', 'bash', '-c', TOOLS + 'board_note.sh held ' + SERIAL], capture_output=True, text=True, timeout=10)
        if p.returncode or not p.stdout.startswith('cx-t0 '):
            raise RuntimeError('board lock missing or owned by another lane')
        p = subprocess.run([HDC, 'list', 'targets'], capture_output=True, text=True, timeout=15)
        if p.returncode or SERIAL not in p.stdout.split():
            raise RuntimeError('board detached; stop further board commands')

    def shell(self, command, timeout=30, required=True):
        self.ready()
        wrapped = 'sh -c ' + shlex.quote(command) + '; t0rc=$?; printf "\\n__T0_RC__%s\\n" "$t0rc"'
        p = subprocess.run([HDC, '-t', SERIAL, 'shell', wrapped], capture_output=True, text=True, timeout=timeout)
        raw = p.stdout.replace('\r', '')
        m = re.search(r'\n__T0_RC__(\d+)\n?$', raw)
        rc = int(m[1]) if m else -1
        with (self.out / 'commands.jsonl').open('a') as f:
            f.write(json.dumps({'time': time.time(), 'command': command, 'transport_rc': p.returncode, 'remote_rc': rc}) + '\n')
        if p.returncode or m is None or '[Fail]' in raw:
            raise RuntimeError('transport failed: ' + command + ': ' + raw[-500:])
        if required and rc:
            raise RuntimeError(f'remote rc={rc}: {command}: {raw[-500:]}')
        return rc, raw[:m.start()]

    def read(self, remote, local):
        q = shlex.quote(remote)
        rc, raw = self.shell(f'if [ ! -f {q} ]; then exit 44; fi; cat {q}', required=False)
        state = 'missing' if rc == 44 else 'read_error' if rc else 'empty' if not raw else 'ok'
        if rc == 0:
            local.write_text(raw)
            filtered = '\n'.join(x for x in raw.splitlines() if 'TOUCH21-POLL' not in x)
            local.with_suffix(local.suffix + '.filtered').write_text(filtered + ('\n' if filtered else ''))
        return {'path': remote, 'status': state, 'raw_lines': len(raw.splitlines()),
                'filtered_lines': sum('TOUCH21-POLL' not in x for x in raw.splitlines()), 'file': local.name}, raw


def collect(key, run_id):
    out = Path.home() / 'a2hlab/ws' / ('out-appsweep-t0-' + run_id) / SERIAL / key
    out.mkdir(parents=True, exist_ok=False)
    b = Board(out)
    result = {'key': key, 'run_id': run_id, 'serial': SERIAL, 'status': 'interrupted',
              'review': 'pending_review', 'observations': {}, 'confirmed': []}
    save(out / 'triage.json', result)
    try:
        b.ready()
        app_src = Path.home() / 'a2hlab/app-inputs' / key
        before = {str(p.relative_to(app_src)): sha(p) for p in app_src.rglob('*') if p.is_file()}
        app_dst = out / 'app-input'
        shutil.copytree(app_src, app_dst)
        app = json.loads((app_dst / 'app-input.json').read_text())
        result.update(package=app['application']['package'], apk_sha256=app['apk_sha256'], launch_activity=app['application']['launch_activity'])
        framework = Path.home() / 'a2hlab/board' / SERIAL / 'framework-2/device-report.json'
        fw = json.loads(framework.read_text())
        save(out / 'framework.json', fw)
        result['framework_report_sha256'] = sha(framework)
        result['boot_hashes'] = {k: v['sha256'] for k, v in fw['files'].items() if k.startswith('boot/')}
        b.shell('aa force-stop org.westlake.imehost', required=False)
        b.shell("pkill -f '[a]ppspawn-x'", required=False)
        b.shell('power-shell timeout -o 3600000')
        start = float(b.shell('date +%s')[1].strip())
        result['launch_epoch'] = start
        cmd = ['python3', str(Path.home() / 'a2hlab/manifest/tools/probe_source_app.py'),
               '--workspace', str(W), '--westlake-source', str(W / 'westlake'),
               '--framework-report', str(framework), '--app-input', str(app_dst), '--app', key,
               '--hdc', HDC, '--serial', SERIAL, '--out', str(out / 'probe'),
               '--host-build', str(W / 'out/signed-host'), '--webview-input', str(W / 'out/webview-input-source')]
        b.ready()
        with (out / 'probe.stdout').open('w') as so, (out / 'probe.stderr').open('w') as se:
            p = subprocess.run(cmd, cwd=Path.home() / 'a2hlab/manifest', stdout=so, stderr=se, timeout=240)
        result['probe_rc'] = p.returncode
        if p.returncode:
            detail = (out / 'probe.stderr').read_text().strip().splitlines()
            raise RuntimeError('probe failed: ' + (detail[-1] if detail else f'rc={p.returncode}'))
        report = json.loads((out / 'probe/device-report.json').read_text())
        if not report.get('child'):
            raise RuntimeError('probe missing current child')
        pid, runtime, stage = report['child'], report['runtime'], report['stage']
        result.update(child_pid=pid, runtime=runtime, stage=stage, host_window=report['window'])
        time.sleep(30)
        rtpath = f'{runtime}/private-tmp/adapter_child_{pid}.stderr'
        obs = result['observations']
        obs['stderr'], raw = b.read(rtpath, out / 'child.pre.stderr')
        obs['proc_stderr'], _ = b.read(f'/proc/{pid}/root/data/local/tmp/adapter_child_{pid}.stderr', out / 'proc.stderr')
        obs['parent_log'], _ = b.read(stage + '/parent.log', out / 'parent.log')
        _, rs = b.shell('hidumper -s RenderService')
        (out / 'rs.txt').write_text(rs)
        obs['render_node'] = {'status': 'unresolved', 'pid': pid, 'host_window': report['window'], 'source': 'rs.txt'}
        b.shell('power-shell wakeup')
        b.shell('power-shell timeout -o 3600000')
        b.shell('uinput -T -m 600 1600 600 400 200')
        remote_dir = f'/data/local/tmp/t0sweep/{run_id}/{SERIAL}'
        b.shell('mkdir -p ' + remote_dir)
        remote = remote_dir + '/' + key + '.jpeg'
        rc, snap = b.shell('snapshot_display -f ' + remote, required=False)
        (out / 'snapshot.txt').write_text(snap)
        obs['shot'] = {'status': 'failed', 'remote': remote}
        if rc == 0:
            _, stat = b.shell('stat -c "%Y %s" ' + remote)
            mtime, size = map(int, stat.split())
            if mtime >= start and size > 0:
                b.ready()
                p = subprocess.run([HDC, '-t', SERIAL, 'file', 'recv', remote, key + '.jpeg'], cwd=out, capture_output=True, text=True, timeout=30)
                image = out / (key + '.jpeg')
                if p.returncode == 0 and image.exists() and image.stat().st_size == size:
                    obs['shot'] = {'status': 'ok', 'remote': remote, 'mtime': mtime, 'sha256': sha(image), 'file': image.name}
                elif image.exists():
                    image.unlink()
        obs['stacks'] = []
        for i in range(2):
            rc, _ = b.shell(f'test -d /proc/{pid}', required=False)
            capture = {'status': 'capture-failed', 'reason': 'child-exited', 'pid': pid}
            if rc == 0:
                capture.update(sent_epoch=time.time(), reason='no-complete-stack-within-12s')
                _, old = b.read(rtpath, out / f'quit{i}.before.stderr')
                b.shell(f'kill -QUIT {pid}')
                for _ in range(6):
                    time.sleep(2)
                    _, new = b.read(rtpath, out / f'quit{i}.after.stderr')
                    delta = new[len(old):] if new.startswith(old) else ''
                    complete = stack_sections(delta, pid)
                    if complete:
                        (out / f'quit{i}.stack.txt').write_text(complete[-1])
                        capture.update(status='ok', reason=None, file=f'quit{i}.stack.txt')
                        break
                _, paths = b.shell(f'ls -la /data/anr /proc/{pid}/root/data/anr /data/log/faultlog/temp 2>/dev/null', required=False)
                (out / f'quit{i}.destinations.txt').write_text(paths)
                time.sleep(max(0, 5 - (time.time() - capture['sent_epoch'])))
            obs['stacks'].append(capture)
        end = float(b.shell('date +%s')[1].strip()) + 1
        _, hilog = b.shell('hilog -x -v epoch', timeout=45)
        (out / 'hilog.raw.txt').write_text(hilog)
        (out / 'hilog.crash.txt').write_text(filter_hilog(hilog, pid, start, end))
        obs['stderr_final'], _ = b.read(rtpath, out / 'child.final.stderr')
        after = {str(p.relative_to(app_src)): sha(p) for p in app_src.rglob('*') if p.is_file()}
        result['app_input_unchanged'] = before == after
        save(out / 'input-hashes.json', {'before': before, 'after': after})
        result['candidate_blocker'] = {'class': 'capture-failed' if any(s['status'] != 'ok' for s in obs['stacks']) else 'no-marker', 'source': 'child.final.stderr', 'reason': 'minimal collection experiment; no root cause claim'}
        result.update(status='completed', finish_epoch=end)
    except Exception as e:
        result['error'] = str(e)
        result['candidate_blocker'] = {'class': 'capture-failed', 'reason': str(e)}
    finally:
        save(out / 'triage.json', result)
    print(json.dumps({'out': str(out), 'status': result['status'], 'error': result.get('error'), 'stacks': result['observations'].get('stacks')}), flush=True)
    return 0 if result['status'] == 'completed' else 2


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('key', choices=['wikipedia', 'markor'])
    ap.add_argument('run_id')
    args = ap.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.run_id):
        ap.error('run_id must be a single path component')
    raise SystemExit(collect(args.key, args.run_id))
