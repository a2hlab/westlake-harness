#!/usr/bin/env python3
"""T106 bounded read-only collector (CC). Follows commands.disabled.json phases; per-board 90 s, batch 240 s, no retry."""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path
C = Path(sys.argv[1]); PLAN = Path(sys.argv[2]); REC = C/'tools/rec.py'
plan = json.loads((PLAN/'commands.disabled.json').read_text()); files = json.loads((PLAN/'files.json').read_text())['files']
H = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
M = Path.home()/'orca/workspaces/westlake-harness'
BOARDS = ['61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c']
T0 = time.monotonic(); BATCH_DL = T0 + 240
roles = [(r['role'], r['logical_relative_path']) for r in files if r['logical_relative_path']]
PRIO = {'host-hap-not-apk': 0, 'runtime-native': 1, 'apk': 2, 'bcp-jar': 3, 'boot-image': 4}
index = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'plan_sha256': {}, 'boards': {}}
import hashlib
for n in ('commands.disabled.json', 'files.json'): index['plan_sha256'][n] = hashlib.sha256((PLAN/n).read_bytes()).hexdigest()
def makedev(mj, mn): return (mn & 0xff) | (mj << 8) | ((mn & ~0xff) << 12)
def run(raw, name, argv, dl):
    rem = min(dl, BATCH_DL) - time.monotonic()
    if rem < 1.5: return None, 'SKIP_BUDGET'
    env = dict(os.environ, REC_TIMEOUT=f'{min(20.0, rem - 0.5):.1f}', REC_SHOW='0')
    subprocess.run([sys.executable, str(REC), str(raw), name, '--', *argv], env=env, capture_output=True)
    rc = (raw/f'{name}.rc').read_text().strip() if (raw/f'{name}.rc').exists() else 'missing'
    return (raw/f'{name}.stdout').read_text(errors='replace') if (raw/f'{name}.stdout').exists() else '', rc
for S in BOARDS:
    b = S[:3]; raw = C/'raw'/b; raw.mkdir(parents=True, exist_ok=True); bd = {'serial': S, 'steps': []}; index['boards'][b] = bd
    DL = time.monotonic() + 90
    def step(name, argv):
        out, rc = run(raw, name, argv, DL); bd['steps'].append({'name': name, 'rc': rc}); return out, rc
    out, rc = step('held', ['bash', str(M/'scripts/lab/board_note.sh'), 'held', S])
    if rc != '1' or (out or '').strip(): bd['stop'] = f'holder_present_or_unknown rc={rc}'; continue
    sh = lambda name, cmd: step(name, [H, '-t', S, 'shell', cmd])
    out, rc = sh('fresh_identity', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,PPID,UID,ARGS')
    if rc != '0': bd['stop'] = f'fresh_identity rc={rc}'; continue
    lines = out.splitlines(); bd['boot'] = lines[0].strip() if lines else None
    procs = [l.split(None, 3) for l in lines[2:] if re.match(r'\s*\d+\s', l)]
    child = [p for p in procs if len(p) == 4 and p[3].strip() == 'com.ss.android.article.news']
    host = [p for p in procs if len(p) == 4 and p[3].strip() == 'org.westlake.imehost']
    targets = [('child', child[0][0])] if len(child) == 1 else []
    if len(host) == 1: targets.append(('host', host[0][0]))
    bd['targets'] = {k: v for k, v in targets}; bd['ambiguous'] = {'child': len(child), 'host': len(host)}
    selected = []
    for tag, pid in targets:
        assert pid.isdigit()
        out, rc = sh(f'proc_{tag}', f'cat /proc/{pid}/stat && readlink /proc/{pid}/exe && od -An -v -tx1 /proc/{pid}/cmdline && cat /proc/{pid}/maps && cat /proc/{pid}/stat')
        if rc != '0': continue
        stats = [l for l in out.splitlines() if l.startswith(f'{pid} (')]
        bd[f'{tag}_stat_birth'] = [s.split(') ', 1)[1].split()[19] if ') ' in s else None for s in stats]
        seen = {}
        for l in out.splitlines():
            m = re.match(r'^[0-9a-f]+-[0-9a-f]+\s+\S+\s+[0-9a-f]+\s+([0-9a-f]+):([0-9a-f]+)\s+(\d+)\s+(/\S.*)$', l)
            if not m: continue
            path = m.group(4)
            if path.endswith(' (deleted)'): continue
            for role, rel in roles + [('host-hap-not-apk', 'org.westlake.imehost/entry.hap')]:
                if path.endswith('/' + rel):
                    seen.setdefault(path, (role, rel, int(m.group(1), 16), int(m.group(2), 16), int(m.group(3))))
        for path, (role, rel, mj, mn, ino) in seen.items():
            selected.append({'tag': tag, 'pid': pid, 'role': role, 'rel': rel, 'path': path, 'maps_dev': f'{mj:x}:{mn:x}', 'maps_dev_decimal': makedev(mj, mn), 'maps_inode': ino})
    # dedupe by path keeping first (child before host), order by priority
    uniq = {}
    for s in selected: uniq.setdefault(s['path'], s)
    sel = sorted(uniq.values(), key=lambda s: (PRIO.get(s['role'], 9), s['rel']))
    bd['mapped_selected'] = []
    for i, s in enumerate(sel):
        if DL - time.monotonic() < 10: s['result'] = 'UNKNOWN_BUDGET'; bd['mapped_selected'].append(s); continue
        q = shlex.quote(f"/proc/{s['pid']}/root{s['path']}")
        out, rc = sh(f'map{i:02d}', f'stat -c "STAT %d %i %s %Y %u %g %a %n" {q} && sha256sum {q} && stat -c "STAT %d %i %s %Y %u %g %a %n" {q}')
        s['rec'] = f'map{i:02d}'; s['rc'] = rc
        st = [l.split() for l in (out or '').splitlines() if l.startswith('STAT ')]
        sha = [l.split()[0] for l in (out or '').splitlines() if re.match(r'^[0-9a-f]{64}\s', l)]
        if rc == '0' and len(st) == 2 and sha:
            s['stat_dev'], s['stat_inode'], s['size'] = int(st[0][1]), int(st[0][2]), int(st[0][3])
            s['stable'] = st[0][1:7] == st[1][1:7]
            s['dev_inode_match'] = (s['stat_dev'] == s['maps_dev_decimal'] and s['stat_inode'] == s['maps_inode'])
            s['sha256'] = sha[0]; s['result'] = 'OK' if (s['stable'] and s['dev_inode_match']) else 'UNKNOWN_BINDING'
        else: s['result'] = f'UNKNOWN_READ rc={rc}'
        bd['mapped_selected'].append(s)
    if b == '61b':
        ph = [p for p in plan['phases'] if p['phase'] == '61b_exact_files'][0]
        if DL - time.monotonic() >= 10:
            out, rc = step('exact_61b_disk', ph['argv'])
        else: bd['steps'].append({'name': 'exact_61b_disk', 'rc': 'SKIP_BUDGET'})
    else: bd['steps'].append({'name': '5cd_exact_files', 'rc': 'NOT_RUN (plan argv null; mapped paths only)'})
    out, rc = sh('final_identity', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,PPID,UID,ARGS' + ''.join(f' && cat /proc/{p}/stat' for _, p in targets))
    if rc == '0':
        bd['final_boot'] = out.splitlines()[0].strip()
        for tag, pid in targets:
            st = [l for l in out.splitlines() if l.startswith(f'{pid} (')]
            bd[f'{tag}_final_birth'] = st[0].split(') ', 1)[1].split()[19] if st else None
    bd['elapsed_s'] = round(90 - (DL - time.monotonic()), 1)
index['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); index['batch_elapsed_s'] = round(time.monotonic() - T0, 1)
(C/'index.json').write_text(json.dumps(index, indent=1) + '\n'); print(json.dumps({b: {k: v for k, v in d.items() if k not in ('steps', 'mapped_selected')} for b, d in index['boards'].items()})); print('elapsed', index['batch_elapsed_s'])
