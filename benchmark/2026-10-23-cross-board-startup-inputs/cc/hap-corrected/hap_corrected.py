#!/usr/bin/env python3
"""T106B: read-only host-HAP mapped identity correction. Python argv lists only; 60 s total for both boards; no retry."""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path
D = Path(sys.argv[1]); REC = Path(sys.argv[2])
H = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
BOARD_NOTE = str(Path.home()/'orca/workspaces/westlake-harness/scripts/lab/board_note.sh')
WHITELIST = ('61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c')
HAP = '/data/storage/el1/bundle/entry.hap'
T0 = time.monotonic(); DL = T0 + 60
out = {'window': 'T106B', 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'budget_s': 60, 'boards': {}}
def run(raw, name, argv):
    rem = DL - time.monotonic()
    if rem < 1.5: return None, 'SKIP_BUDGET'
    env = dict(os.environ, REC_TIMEOUT=f'{min(20.0, rem - 0.5):.1f}', REC_SHOW='0')
    subprocess.run([sys.executable, str(REC), str(raw), name, '--', *argv], env=env, capture_output=True, check=False)
    rcf = raw/f'{name}.rc'
    return ((raw/f'{name}.stdout').read_text(errors='replace') if (raw/f'{name}.stdout').exists() else ''), (rcf.read_text().strip() if rcf.exists() else 'missing')
def makedev(mj, mn): return (mn & 0xff) | (mj << 8) | ((mn & ~0xff) << 12)
for serial in WHITELIST:
    b = serial[:3]; raw = D/'raw'/b; raw.mkdir(parents=True, exist_ok=True); r = {'serial': serial}; out['boards'][b] = r
    if serial not in WHITELIST or not re.fullmatch(r'[0-9a-f]{32}', serial): r['stop'] = 'serial_not_whitelisted'; continue
    o, rc = run(raw, 'held', ['bash', BOARD_NOTE, 'held', serial]); r['held_rc'] = rc
    if rc != '1' or o.strip(): r['stop'] = f'holder_present_or_unknown rc={rc}'; continue
    o, rc = run(raw, 'fresh_ps', [H, '-t', serial, 'shell', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,ARGS'])
    r['fresh_ps_rc'] = rc
    if rc != '0': r['stop'] = f'fresh_ps rc={rc}'; continue
    lines = o.splitlines(); r['boot'] = lines[0].strip() if lines else None
    hosts = [l.split(None, 1)[0] for l in lines[2:] if re.fullmatch(r'\s*\d+\s+org\.westlake\.imehost\s*', l)]
    if len(hosts) != 1 or not re.fullmatch(r'\d+', hosts[0]): r['stop'] = f'host_pid_not_unique_numeric {hosts}'; continue
    pid = hosts[0]; r['host_pid'] = pid
    q = shlex.quote(f'/proc/{pid}/root{HAP}')
    cmd = (f'cat /proc/{pid}/stat && grep -F {shlex.quote(" " + HAP)} /proc/{pid}/maps && '
           f'stat -c "STAT %d %i %s %Y %u %g %a %n" {q} && sha256sum {q} && stat -c "STAT %d %i %s %Y %u %g %a %n" {q} && cat /proc/{pid}/stat')
    o, rc = run(raw, 'hap_read', [H, '-t', serial, 'shell', cmd]); r['hap_read_rc'] = rc
    L = (o or '').splitlines()
    births = [l.split(') ', 1)[1].split()[19] for l in L if l.startswith(f'{pid} (') and ') ' in l]
    maps = [re.match(r'^[0-9a-f]+-[0-9a-f]+\s+\S+\s+[0-9a-f]+\s+([0-9a-f]+):([0-9a-f]+)\s+(\d+)\s+(\S+)$', l) for l in L]
    maps = [m for m in maps if m and m.group(4) == HAP]
    st = [l.split() for l in L if l.startswith('STAT ')]; sha = [l.split()[0] for l in L if re.match(r'^[0-9a-f]{64}\s', l)]
    r['births'] = births; r['maps_lines'] = len(maps)
    if rc == '0' and len(births) == 2 and births[0] == births[1] and maps and len(st) == 2 and sha:
        devs = {(makedev(int(m.group(1), 16), int(m.group(2), 16)), int(m.group(3))) for m in maps}
        r['maps_dev_inode'] = sorted(devs); r['stat_dev_inode'] = [int(st[0][1]), int(st[0][2])]
        r['stat_stable'] = st[0][1:7] == st[1][1:7]; r['dev_inode_match'] = (int(st[0][1]), int(st[0][2])) in devs and len(devs) == 1
        r['size'] = int(st[0][3]); r['mtime'] = int(st[0][4]); r['owner'] = f'{st[0][5]}:{st[0][6]}'; r['mode'] = st[0][7]
        r['sha256'] = sha[0]; r['result'] = 'OK' if (r['stat_stable'] and r['dev_inode_match']) else 'UNKNOWN_BINDING'
    else: r['result'] = f'UNKNOWN rc={rc} births={births} maps={len(maps)} stat={len(st)} sha={len(sha)}'
out['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); out['elapsed_s'] = round(time.monotonic() - T0, 1)
(D/'hap_corrected.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out))
