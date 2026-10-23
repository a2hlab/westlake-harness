#!/usr/bin/env python3
"""T119 addendum read-only 5cd (JIT, REQUEST paths only): host UID/GID/birth bracketed, stat+sha256 of metadata-derived dependency paths. 90 s; python argv."""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path
P = Path(sys.argv[1]); RAW = P/'raw'; REC = P/'rec.py'
H = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'; S = '5cd1e3dd00000000000000000923012c'
BN = str(Path.home()/'orca/workspaces/westlake-harness/scripts/lab/board_note.sh')
DEPS = {'JIT': '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/prepare_jit50.sh',
        'REQUEST': '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/request.bin'}
T0 = time.monotonic(); DL = T0 + 90; out = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'serial': S}
def run(name, argv):
    rem = DL - time.monotonic()
    if rem < 1.5: out.setdefault('skipped', []).append(name); return '', 'SKIP_BUDGET'
    env = dict(os.environ, REC_TIMEOUT=f'{min(20.0, rem - 0.5):.1f}', REC_SHOW='0')
    subprocess.run([sys.executable, str(REC), str(RAW), name, '--', *argv], env=env, capture_output=True)
    f = RAW/f'{name}.stdout'; return (f.read_text(errors='replace') if f.exists() else ''), (RAW/f'{name}.rc').read_text().strip()
def ident(tag):
    o, rc = run(f'ident_{tag}', [H, '-t', S, 'shell', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,ARGS'])
    L = o.splitlines(); return rc, (L[0].strip() if L else None), [l.split()[0] for l in L[2:] if re.fullmatch(r'\s*\d+\s+org\.westlake\.imehost\s*', l)]
def proc(tag, pid):
    o, rc = run(f'proc_{tag}', [H, '-t', S, 'shell', f'cat /proc/{pid}/stat && grep -E "^(Name|Uid|Gid):" /proc/{pid}/status'])
    st = [l for l in o.splitlines() if l.startswith(f'{pid} (')]; birth = st[0].split(') ', 1)[1].split()[19] if st else None
    uid = [l.split()[1:] for l in o.splitlines() if l.startswith('Uid:')]; gid = [l.split()[1:] for l in o.splitlines() if l.startswith('Gid:')]
    return {'rc': rc, 'birth': birth, 'uid': uid[0] if uid else None, 'gid': gid[0] if gid else None}
o, rc = run('held', ['bash', BN, 'held', S]); out['held_rc'] = rc
if rc != '1' or o.strip(): out['stop'] = 'holder'
else:
    rc, boot, hosts = ident('pre'); out['boot_pre'] = boot; out['hosts_pre'] = hosts
    if rc != '0' or len(hosts) != 1 or not hosts[0].isdigit(): out['stop'] = f'host_not_unique {hosts}'
    else:
        pid = hosts[0]; out['host_pid'] = pid; out['proc_pre'] = proc('pre', pid)
        out['deps'] = {}
        for k, p in DEPS.items():
            q = shlex.quote(p); o, rc = run(f'dep_{k}', [H, '-t', S, 'shell', f'stat -c "STAT %d %i %s %Y %u %g %a %F %n" {q} 2>&1; sha256sum {q} 2>&1; stat -c "STAT %d %i %s %Y %u %g %a %F %n" {q} 2>&1'])
            st = [l.split() for l in o.splitlines() if l.startswith('STAT ')]; sha = [l.split()[0] for l in o.splitlines() if re.match(r'^[0-9a-f]{64}\s', l)]
            out['deps'][k] = {'path': p, 'rc': rc, 'exists': bool(st and sha), 'sha256': sha[0] if sha else None, 'stable': (len(st) == 2 and st[0][1:8] == st[1][1:8]) if st else None,
                              'size': int(st[0][3]) if st else None, 'mtime': int(st[0][4]) if st else None, 'owner': f'{st[0][5]}:{st[0][6]}' if st else None, 'mode': st[0][7] if st else None}
        rc2, boot2, hosts2 = ident('post'); out['boot_post'] = boot2; out['hosts_post'] = hosts2; out['proc_post'] = proc('post', pid)
        out['identity_stable'] = boot == boot2 and hosts2 == [pid] and out['proc_pre']['birth'] == out['proc_post']['birth'] and out['proc_pre']['uid'] == out['proc_post']['uid']
out['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); out['elapsed_s'] = round(time.monotonic() - T0, 1)
(P/'index.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out))
