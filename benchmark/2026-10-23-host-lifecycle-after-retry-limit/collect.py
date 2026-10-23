#!/usr/bin/env python3
"""T114 read-only: 5cd host PID/birth, window-state.json stat + <=8KiB, host hilog -P PID tail (8 s), identity before/after; 60 s batch."""
import json, os, re, shlex, subprocess, sys, time, hashlib
from pathlib import Path
P = Path(sys.argv[1]); RAW = P/'raw'; REC = P/'rec.py'
H = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'; S = '5cd1e3dd00000000000000000923012c'
BN = str(Path.home()/'orca/workspaces/westlake-harness/scripts/lab/board_note.sh')
WS = '/data/app/el2/100/base/org.westlake.imehost/files/window-state.json'
T0 = time.monotonic(); DL = T0 + 60; out = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'serial': S}
def run(name, argv, cap=20.0):
    rem = DL - time.monotonic()
    if rem < 1.5: out.setdefault('skipped', []).append(name); return '', 'SKIP_BUDGET'
    env = dict(os.environ, REC_TIMEOUT=f'{min(cap, rem - 0.5):.1f}', REC_SHOW='0')
    subprocess.run([sys.executable, str(REC), str(RAW), name, '--', *argv], env=env, capture_output=True)
    f = RAW/f'{name}.stdout'; return (f.read_text(errors='replace') if f.exists() else ''), (RAW/f'{name}.rc').read_text().strip()
def ident(name):
    o, rc = run(name, [H, '-t', S, 'shell', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,ARGS'])
    L = o.splitlines(); hosts = [l.split()[0] for l in L[2:] if re.fullmatch(r'\s*\d+\s+org\.westlake\.imehost\s*', l)]
    return rc, (L[0].strip() if L else None), hosts
o, rc = run('held', ['bash', BN, 'held', S]); out['held_rc'] = rc
if rc != '1' or o.strip(): out['stop'] = 'holder'
else:
    rc, boot, hosts = ident('ident_pre'); out['boot_pre'] = boot; out['hosts_pre'] = hosts
    if rc != '0' or len(hosts) != 1 or not hosts[0].isdigit(): out['stop'] = f'host_pid_unstable {hosts}'
    else:
        pid = hosts[0]; out['host_pid'] = pid
        o, rc = run('birth_pre', [H, '-t', S, 'shell', f'cat /proc/{pid}/stat']); out['birth_pre'] = o.split(') ', 1)[1].split()[19] if ') ' in o else None
        q = shlex.quote(WS)
        o, rc = run('window_state', [H, '-t', S, 'shell', f'stat -c "STAT %d %i %s %X %Y %Z %u %g %a %n" {q} 2>&1; echo ---HEAD; head -c 8192 {q} 2>&1; echo; echo ---END; stat -c "STAT %d %i %s %X %Y %Z %u %g %a %n" {q} 2>&1'])
        out['window_state_rc'] = rc
        o, rc = run('hilog', [H, '-t', S, 'shell', f'hilog -P {pid} -z 2000 -L D,I,W,E,F -v epoch'], cap=8.0); out['hilog_rc'] = rc
        rc2, boot2, hosts2 = ident('ident_post'); out['boot_post'] = boot2; out['hosts_post'] = hosts2
        o, rc = run('birth_post', [H, '-t', S, 'shell', f'cat /proc/{pid}/stat']); out['birth_post'] = o.split(') ', 1)[1].split()[19] if ') ' in o else None
        out['identity_stable'] = boot == boot2 and hosts2 == [pid] and out['birth_pre'] == out['birth_post'] and out['birth_pre'] is not None
out['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); out['elapsed_s'] = round(time.monotonic() - T0, 1)
(P/'index.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out))
