#!/usr/bin/env python3
"""Activation smoke gate: prove on the board that each new fix is live before anyone starts a full sweep.

    activation_smoke.py --spec SPEC.json --serial <connect-key> --lane <lane> --out <dir>

Runs, on ONE board and one process at a time: the control apps (HelloWorld / ZigZag) plus one target app per fix,
through bms_batch.py with --hilog --shots 5,20; then launches the probe app (HelloWorld) once more and reads its
child process. PASS only when every check holds:
  * fingerprint  every run's facts.txt RUNTIME / BOOTIMAGE equals spec "expect" (the board is on the new state);
  * controls     every control key is alive at t20;
  * marker       every fix's own activation log line (regex) appears in its target app's hilog (install window
                 install-hilog.txt + launch window hilog.txt, so installer-side fixes can carry markers too);
  * single-copy  each listed library is loaded exactly once in the probe child (/proc/<pid>/maps; the same path
                 loaded at two addresses counts as two);
  * child-view   each listed file, read through /proc/<pid>/root, has the expected sha256.
Screenshots are still judged by the outer loop; this gate only says whether a full sweep is worth starting.
Exit 0 = PASS, 1 = FAIL, 2 = usage / transport error. Writes <out>/smoke-result.json.

2026-10-01 (DIGEST 12:44, user 13:0x): J9 was accepted on offline bytecode diffs and HelloWorld/ZigZag alone;
on the board two of its three fixes never activated ("[J9-NOTITLE] no current Application; not installed",
NoSuchMethodException in SelfActivityInfoSynthesis) and a 45-minute full sweep measured nothing. N10's second
ART copy was likewise only visible in the child's maps.

SPEC (JSON):
  {"expect": {"runtime_fp": "e953c0921536", "boot_fp": "4db882a81732"},
   "groups": [{"manifest": "...", "input_root": "...", "keys": ["helloworld", "zigzag"], "mode": "launch-only",
               "controls": true},
              {"manifest": "...", "input_root": "...", "keys": ["cv2-com-deva-knot"], "mode": "reinstall"}],
   "fixes": [{"id": "J10-NOTITLE", "key": "cv2-com-deva-knot", "markers": ["\\\\[J10-NOTITLE\\\\] installed"]}],
   "probe": {"package": "com.example.helloworld",
             "single_copy": ["libart.so", "libopenjdkjvm.so", "liboh_adapter_bridge.so", "liboh_android_runtime.so"],
             "files": {"/system/android/framework/oh-adapter-runtime.jar": "<sha256>"},
             "expect_copies": {"liboh_adapter_bridge.so": 2}}}   # optional: a known, accepted count other than 1
                                                                 # (states before N11 load bridge/runtime twice)
Optional probe.copy_limits provides explicit {min,max} load-base bounds for an outer-approved signed baseline;
without it, exact expect_copies/single_copy behavior is unchanged. Optional control_selftest=true requires schema2
PASS for every process of every control run; missing, unknown, selftest_error, badtag and probe_error all reject.
Paths in the spec may use $WORKSPACES / ~ ; they are expanded.
"""
import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
sys.path.insert(0, str(Path(__file__).resolve().parent))


def expand(p):
    if '$WORKSPACES' in str(p) and not os.environ.get('WORKSPACES'):
        import lab_paths
        os.environ['WORKSPACES'] = str(lab_paths.workspaces())
    p = os.path.expanduser(os.path.expandvars(str(p)))
    return p if os.path.isabs(p) else str(REPO / p)


def parse_facts(text):
    """RUNTIME / BOOTIMAGE short fingerprints and per-key alive_t20 from a bms_batch facts.txt."""
    rt = re.search(r'^RUNTIME fingerprint=(\w+)', text, re.M)
    bt = re.search(r'^BOOTIMAGE fingerprint=(\w+)', text, re.M)
    keys = {}
    for line in text.splitlines():
        m = re.match(r'(\S+)\s+shots \S+\s+alive t5=(\S+) t20=(\S+)', line)
        if m and not line.startswith(('RUNTIME', 'BOOTIMAGE', 'TOTAL', 'TOOL', 'FROZEN')):
            keys[m.group(1)] = m.group(3)
    return {'runtime_fp': rt.group(1) if rt else None, 'boot_fp': bt.group(1) if bt else None, 'alive_t20': keys}


def marker_hits(hilog_text, markers):
    return {m: len(re.findall(m, hilog_text)) for m in markers}


def copies(maps_text, libs):
    """Loaded instances per library basename, as "path@load-address".

    A load instance starts at a file-offset-0 mapping that does not directly continue the previous mapping of the same
    file. Counting distinct paths (the first version) missed the same file loaded twice in two linker namespaces:
    2026-10-01 the U8 child had liboh_adapter_bridge.so and liboh_android_runtime.so each mapped at two load addresses
    from one path, two OHWindowManagerClient singletons, and "getOhNativeWindow: unknown sessionId" -- the gate said
    "one copy" because both loads had the same path."""
    loads, last_end = {}, {}
    for line in maps_text.splitlines():
        f = line.split()
        if len(f) < 6 or not f[-1].startswith('/'):
            continue
        path, base = f[-1], os.path.basename(f[-1])
        if base not in libs:
            continue
        start, end = f[0].split('-')
        if int(f[2], 16) == 0 and last_end.get(path) != start:
            loads.setdefault(base, []).append(f'{path}@{start}')
        last_end[path] = end
    return {lib: sorted(loads.get(lib, ())) for lib in libs}


def control_crypto(spec, out):
    """Optional schema2 control gate. Errors and absent process evidence fail closed."""
    if not spec.get('control_selftest'):
        return None
    checker = REPO / 'benchmark/2026-10-03-u13-stage-a-plan/process_selftest.py'
    module_spec = importlib.util.spec_from_file_location('activation_crypto_schema2', checker)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    report = module.report(out)
    keys = {key for group in spec.get('groups', []) if group.get('controls') for key in group['keys']}
    rows = {key: [row for row in report['runs'] if row['key'] == key] for key in keys}
    return {'schema_version': 2, 'controls': rows,
            'passed': bool(keys) and all(rows.values()) and
                      all(row['status'] == 'PASS' and row['error_count'] == 0
                          for values in rows.values() for row in values)}


def evaluate(spec, runs, hilogs, probe):
    """Pure decision over collected evidence; returns (passed, checks)."""
    checks = []
    exp = spec.get('expect', {})
    for name, facts in runs.items():
        for k in ('runtime_fp', 'boot_fp'):
            if k in exp:
                checks.append({'check': 'fingerprint', 'run': name, 'field': k, 'want': exp[k], 'got': facts.get(k),
                               'ok': facts.get(k) == exp[k]})
    for g in spec.get('groups', []):
        if g.get('controls'):
            for key in g['keys']:
                got = next((f['alive_t20'].get(key) for f in runs.values() if key in f['alive_t20']), None)
                checks.append({'check': 'controls', 'key': key, 'alive_t20': got, 'ok': got == 'yes'})
    for fix in spec.get('fixes', []):
        text = hilogs.get(fix['key'])
        hits = marker_hits(text or '', fix['markers'])
        checks.append({'check': 'marker', 'fix': fix['id'], 'key': fix['key'], 'hilog_found': text is not None,
                       'hits': hits, 'ok': text is not None and all(v > 0 for v in hits.values())})
    p = spec.get('probe')
    if p:
        if probe.get('error'):
            checks.append({'check': 'probe', 'ok': False, 'error': probe['error']})
        else:
            limits_table = p.get('copy_limits') or {}
            if limits_table:
                checks.append({'check': 'copy-limits-coverage',
                               'ok': isinstance(limits_table, dict) and
                                     set(limits_table) <= set(p.get('single_copy', [])) and
                                     set(limits_table) <= set(probe.get('copies', {}))})
            want = dict(p.get('expect_copies') or {})
            for lib, paths in probe['copies'].items():
                limits = p.get('copy_limits', {}).get(lib)
                if limits is not None:
                    low, high = limits.get('min'), limits.get('max')
                    valid = type(low) is int and type(high) is int and 0 <= low <= high
                    checks.append({'check': 'copy-limits', 'lib': lib, 'paths': paths,
                                   'min': low, 'max': high,
                                   'ok': valid and low <= len(paths) <= high})
                else:
                    n = want.get(lib, 1)
                    checks.append({'check': 'single-copy' if n == 1 else 'expected-copies', 'lib': lib, 'paths': paths,
                                   'want': n, 'ok': len(paths) == n})
            for path, want in p.get('files', {}).items():
                got = probe['view'].get(path)
                checks.append({'check': 'child-view', 'path': path, 'want': want, 'got': got, 'ok': got == want})
    if spec.get('control_selftest'):
        crypto = probe.get('control_crypto') or {}
        checks.append({'check': 'control-selftest-schema2', 'report': crypto,
                       'ok': crypto.get('schema_version') == 2 and crypto.get('passed') is True})
    return all(c['ok'] for c in checks) and bool(checks), checks


def stale_session_keys(gout, dead):
    """Control keys that died only because SceneBoard reused a stale scene session.

    2026-10-01 21:10 (N11d, 5ea) and 22:15 (N11e, 61b): the first HelloWorld launch after a rollback did not spawn at
    all -- its hilog shows `WMSMain: add failed. <ability>/<package>/... (persistentId: N) already existed in array`,
    the session left over from the candidate's failed launch; aa force-stop does not drop it. A second launch works.
    Only a key that is dead AND carries that line for its own package qualifies."""
    stale = []
    for key in dead:
        for rec in gout.glob(f'*/*/{key}/record.json'):
            package = json.loads(rec.read_text()).get('package') or ''
            text = (rec.parent / 'hilog.txt').read_text(errors='replace') if (rec.parent / 'hilog.txt').exists() else ''
            if package and re.search(r'add failed\. [^\n]*/' + re.escape(package) + r'/[^\n]*already existed in array', text):
                stale.append(key)
    return stale


def run_groups(spec, args, out):
    runs, hilogs = {}, {}
    for i, g in enumerate(spec['groups']):
        def run(gout, log):
            cmd = [sys.executable, str(BATCH), '--execute', '--serial', args.serial, '--lane', args.lane,
                   '--manifest', expand(g['manifest']), '--keys', ','.join(g['keys']), '--shots', '5,20', '--hilog',
                   '--out', str(gout)]
            if g.get('input_root'):
                cmd += ['--input-root', expand(g['input_root'])]
            cmd += ['--launch-only'] if g.get('mode') == 'launch-only' else ['--reinstall']
            if args.lock_cmd:
                cmd += ['--lock-cmd', args.lock_cmd]
            with open(log, 'w') as fh:
                rc = subprocess.run(cmd, cwd=REPO, stdout=fh, stderr=subprocess.STDOUT).returncode
            facts = sorted(gout.glob('*/*/facts.txt'))
            if not facts:
                raise RuntimeError(f'group {i} produced no facts.txt (rc={rc}); see {log}')
            return parse_facts(facts[0].read_text())
        gout = out / f'group-{i}'
        facts = run(gout, out / f'group-{i}.log')
        dead = [k for k in g['keys'] if g.get('controls') and facts['alive_t20'].get(k) != 'yes']
        stale = stale_session_keys(gout, dead)
        if stale:   # one retry, recorded; the first attempt's directory stays as evidence
            gout = out / f'group-{i}-stale-session-retry'
            facts = dict(run(gout, out / f'group-{i}-stale-session-retry.log'), stale_session_retry=stale)
        runs[f'group-{i}'] = facts
        for h in gout.glob('*/*/*/hilog.txt'):
            hilogs[h.parent.name] = key_hilog(h.parent)
    return runs, hilogs


def key_hilog(key_dir):
    """Launch-window hilog plus the install-window one (installer-side fixes log during bm install, before the
    pre-launch hilog -r; bms_batch keeps that window as install-hilog.txt since 2026-10-01)."""
    parts = [key_dir / 'install-hilog.txt', key_dir / 'hilog.txt']
    return '\n'.join(p.read_text(errors='replace') for p in parts if p.exists())


def probe_child(spec, args, out):
    p = spec['probe']
    spec_b = importlib.util.spec_from_file_location('smoke_batch', BATCH)
    b = importlib.util.module_from_spec(spec_b); spec_b.loader.exec_module(b)
    pout = out / 'probe'; pout.mkdir(parents=True, exist_ok=True)
    import lab_paths
    lock_cmd = args.lock_cmd or str(lab_paths.tools() / 'board_note.sh')
    board = b.Board(args.serial, args.hdc, lock_cmd, args.lane, pout / 'commands')
    (pout / 'commands').mkdir(parents=True, exist_ok=True)
    pkg = p['package']
    _, dump = board.shell('bm dump -n ' + shlex.quote(pkg))
    data = b.parse_bundle(dump, pkg)
    if not b.cold_stop(board, pkg, data['uid'], pout, 'probe-stop'):
        return {'error': 'probe app cold stop failed'}
    remote = '/data/local/tmp/smoke-' + uuid.uuid4().hex
    board.shell('mkdir ' + remote)
    record = {'package': pkg}
    b.desktop_launch(board, {'package': pkg, 'launch_activity': data['desktop_activity']}, remote, pout, record)
    time.sleep(5)
    rows = b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1])
    parents = [r['pid'] for r in rows if r['uid'] == 0 and r['ppid'] == 1 and r['name'] == 'appspawn-x']
    # A Route B byte-copy spawner at /data/local/tmp/asx/appspawn-x also runs uid0/ppid1/NAME=appspawn-x
    # (#91 2026-10-11, same exe rule as cold_stop / verify_identity / demo_seal post-parent); count only the real
    # U13 ondemand daemon whose exe is /system/bin/appspawn-x so a running Route B feed doesn't poison parents.
    parents = [pid for pid in parents
               if board.shell(f'readlink /proc/{pid}/exe')[1].split(' (deleted)')[0].strip() == '/system/bin/appspawn-x']
    kids = [r for r in rows if r['uid'] == data['uid'] and len(parents) == 1 and r['ppid'] == parents[0]]
    if len(kids) != 1:
        return {'error': f'probe child count {len(kids)} (parents {len(parents)})'}
    pid = kids[0]['pid']
    maps = board.shell(f'cat /proc/{pid}/maps')[1]
    (pout / f'child-{pid}-maps.txt').write_text(maps)
    view = {}
    for path in p.get('files', {}):
        _, text = board.shell(f'sha256sum /proc/{pid}/root{shlex.quote(path)}', required=False)
        view[path] = text.split()[0] if text.split() else None
    board.shell('rm -rf ' + remote, required=False)
    b.cold_stop(board, pkg, data['uid'], pout, 'probe-after')
    return {'pid': pid, 'copies': copies(maps, p.get('single_copy', [])), 'view': view}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--spec', required=True, type=Path)
    ap.add_argument('--serial', required=True)
    ap.add_argument('--lane', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--hdc', default='hdc')
    ap.add_argument('--lock-cmd', default=None)
    args = ap.parse_args(argv)
    spec = json.loads(args.spec.read_text())
    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=False)
    try:
        runs, hilogs = run_groups(spec, args, out)
        probe = probe_child(spec, args, out) if spec.get('probe') else {}
        if spec.get('control_selftest'):
            probe['control_crypto'] = control_crypto(spec, out)
            (out / 'control-selftest.json').write_text(json.dumps(probe['control_crypto'], indent=2) + '\n')
    except Exception as exc:  # transport / batch errors are a FAIL with the reason recorded, never a PASS
        result = {'passed': False, 'error': f'{type(exc).__name__}: {exc}'}
        (out / 'smoke-result.json').write_text(json.dumps(result, indent=1))
        print('SMOKE ERROR:', result['error'], file=sys.stderr)
        return 2
    passed, checks = evaluate(spec, runs, hilogs, probe)
    result = {'passed': passed, 'serial': args.serial, 'spec': str(args.spec), 'runs': runs,
              'probe': {k: v for k, v in probe.items() if k != 'view'} | {'view': probe.get('view')}, 'checks': checks}
    (out / 'smoke-result.json').write_text(json.dumps(result, indent=1, ensure_ascii=False))
    for c in checks:
        print(('PASS ' if c['ok'] else 'FAIL ') + json.dumps({k: v for k, v in c.items() if k != 'ok'}, ensure_ascii=False))
    print('SMOKE', 'PASS' if passed else 'FAIL', out / 'smoke-result.json')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
