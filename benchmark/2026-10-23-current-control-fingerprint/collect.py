#!/usr/bin/env python3
"""T116 read-only control fingerprint. Python argv only. Per board 60 s, batch 120 s. Implementation files: stat+sha256 only."""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path
P = Path(sys.argv[1]); REC = P/'rec.py'
H = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
BN = str(Path.home()/'orca/workspaces/westlake-harness/scripts/lab/board_note.sh')
BOARDS = ('61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c')
CFG = '/system/etc/init/01_westlake_u13_toutiao.cfg'
CONFIG_READ = ('startup.env', 'startup.expected.sha256', 'members.tsv')   # config metadata: content read allowed
HASH_ONLY = ('entry.sh', 'config-common.sh', 'boot-entry.sh', 'watchdog.sh')  # never read content
T0 = time.monotonic(); BDL = T0 + 120; out = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'boards': {}}
STATFMT = 'STAT %d %i %s %Y %u %g %a %n'
for S in BOARDS:
    b = S[:3]; raw = P/'raw2'/b; raw.mkdir(parents=True, exist_ok=True); r = {'serial': S}; out['boards'][b] = r; DL = min(time.monotonic() + 60, BDL)
    def run(name, argv):
        rem = DL - time.monotonic()
        if rem < 1.5: r.setdefault('skipped', []).append(name); return '', 'SKIP_BUDGET'
        env = dict(os.environ, REC_TIMEOUT=f'{min(20.0, rem - 0.5):.1f}', REC_SHOW='0')
        subprocess.run([sys.executable, str(REC), str(raw), name, '--', *argv], env=env, capture_output=True)
        f = raw/f'{name}.stdout'; return (f.read_text(errors='replace') if f.exists() else ''), (raw/f'{name}.rc').read_text().strip()
    sh = lambda name, cmd: run(name, [H, '-t', S, 'shell', cmd])
    o, rc = run('held', ['bash', BN, 'held', S]); r['held_rc'] = rc
    if rc != '1' or o.strip(): r['stop'] = 'holder'; continue
    o, rc = sh('ident_pre', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime && ps -A -o PID,PPID,ARGS')
    if rc != '0': r['stop'] = f'ident rc={rc}'; continue
    r['boot_pre'] = o.splitlines()[0].strip()
    o, rc = sh('cfg', f'stat -c "{STATFMT}" {CFG} && sha256sum {CFG} && echo ---CFG && cat {CFG}'); r['cfg_rc'] = rc
    try:
        cfg = json.loads(o.split('---CFG\n', 1)[1]); r['cfg_sha256'] = [l.split()[0] for l in o.splitlines() if re.match(r'^[0-9a-f]{64}\s', l)][0]
    except Exception as e: r['stop'] = f'cfg_unparsed {e}'; continue
    svcs = [{'name': s.get('name'), 'path': s.get('path')} for s in cfg.get('services', [])]
    r['cfg_services'] = svcs
    roots = sorted({os.path.dirname(a) for s in svcs for a in (s['path'] or []) if isinstance(a, str) and a.startswith('/data/westlake-demo/toutiao/') and a.endswith('/boot-entry.sh')})
    if len(roots) != 1 or not re.fullmatch(r'/data/westlake-demo/toutiao/[A-Za-z0-9._/-]+', roots[0]): r['stop'] = f'root_not_unique {roots}'; continue
    ROOT = roots[0]; r['root'] = ROOT; bd = f"{ROOT}/boots/{r['boot_pre']}"
    if not re.fullmatch(r'[0-9a-f-]{36}', r['boot_pre']): r['stop'] = 'boot_id_malformed'; continue
    # config metadata: stat + sha + content
    cmd = ' ; '.join(f'echo "===F {d}/{n}"; stat -c "{STATFMT}" {shlex.quote(d + "/" + n)} 2>&1; sha256sum {shlex.quote(d + "/" + n)} 2>&1; echo ---BODY; head -c 16384 {shlex.quote(d + "/" + n)} 2>&1; echo; echo ---EOB' for d in (ROOT, bd) for n in CONFIG_READ)
    o, rc = sh('config_meta', cmd); r['config_meta_rc'] = rc
    members = []
    for blk in o.split('===F ')[1:]:
        head, _, rest = blk.partition('\n')
        if head.endswith('/members.tsv') and head.startswith(ROOT + '/members'):
            body = rest.split('---BODY\n', 1)[-1].split('\n---EOB', 1)[0]
            for line in body.splitlines():
                for tok in re.split(r'\s+', line.strip()):
                    if re.fullmatch(r'[A-Za-z0-9._-]+\.(sh|cfg|env|txt|tsv|sha256|json|jpeg|conf)', tok) or tok in HASH_ONLY or re.fullmatch(r'[A-Za-z][A-Za-z0-9._-]*', tok) and '.' not in tok and len(tok) > 3 and tok.lower() not in ('sha256', 'mode', 'name', 'path', 'size'):
                        members.append(tok)
    members = sorted(set(members) | set(HASH_ONLY)); r['hash_only_targets'] = members
    cmd = ' ; '.join(f'echo "===H {d}/{n}"; stat -c "{STATFMT}" {shlex.quote(d + "/" + n)} 2>&1; sha256sum {shlex.quote(d + "/" + n)} 2>&1' for d in (ROOT, bd) for n in members if re.fullmatch(r'[A-Za-z0-9._-]+', n))
    o, rc = sh('hash_only', cmd); r['hash_only_rc'] = rc
    rows = []
    for blk in o.split('===H ')[1:]:
        head, _, rest = blk.partition('\n'); st = [l.split() for l in rest.splitlines() if l.startswith('STAT ')]; sha = [l.split()[0] for l in rest.splitlines() if re.match(r'^[0-9a-f]{64}\s', l)]
        rows.append({'path': head.strip(), 'where': 'boot_copy' if '/boots/' in head else 'root', 'exists': bool(st and sha), 'sha256': sha[0] if sha else None,
                     'size': int(st[0][3]) if st else None, 'mtime': int(st[0][4]) if st else None, 'owner': f'{st[0][5]}:{st[0][6]}' if st else None, 'mode': st[0][7] if st else None})
    r['files'] = rows
    o, rc = sh('ident_post', 'cat /proc/sys/kernel/random/boot_id && cat /proc/uptime'); r['boot_post'] = o.splitlines()[0].strip() if rc == '0' and o else None
    r['same_boot'] = r['boot_pre'] == r['boot_post']; r['elapsed_s'] = round(60 - (DL - time.monotonic()), 1)
out['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); out['batch_elapsed_s'] = round(time.monotonic() - T0, 1)
(P/'index.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({b: {k: v for k, v in d.items() if k not in ('files', 'cfg_services')} for b, d in out['boards'].items()}))
