#!/usr/bin/env python3
"""T40: exact es2abc replay of the T39 host-observer candidate. No device/sign/pack/install.

Reuses T32's exact es2abc argv (--target-api-version=20 --output=X.abc EntryAbility.js) and logging style.
The pinned Linux es2abc (d20db2d4...) lives in the orb a2hlab VM. Pass --compiler as the VM-visible path or
--compiler-receipt (reads compiler.path from an explicit historical receipt); the absolute path is NOT
hard-coded here. All consistency checks use explicit if/raise (NOT assert, which `python -O`/PYTHONOPTIMIZE
strips). --raw is expanduser().resolve()d and must not already exist. Each VM command streams stdout/stderr
to files and catches OSError (-> rc + time + a separate driver-error record); a nonzero rc, local timeout, or
any check leaves an explicit INCOMPLETE/FAILED receipt and stops with no reroute. A local TIMEOUT does not
prove the remote es2abc exited and is never auto-retried; it is recorded in a separate driver-error file, not
appended to the raw stderr. ABC binaries stay in the raw dir, not in git.
"""
import argparse, hashlib, json, shlex, subprocess, sys, time
from pathlib import Path

COMPILER_SHA = 'd20db2d40cef6ae897eeb736e6023625f507f89ba67b0d6cdcb602ca0a21fb0c'
BASELINE_SHA = '9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6'
CANDIDATE_SHA = 'fc0e5ec024d34b27e56ac9841eb2cae9a5dd95de84d4da72c71418e1cfae0e56'
HAP_MEMBER = 'bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9'
HERE = Path(__file__).resolve().parent
TIMEOUT = 120

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Stop(Exception):
    def __init__(self, status, msg): self.status = status; self.msg = msg

def check(cond, status, msg):
    if not cond: raise Stop(status, msg)           # explicit, survives python -O

def run_vm(label, cmd, raw, receipt):
    """Run one VM command, streaming stdout/stderr to files. OSError/timeout -> rc + time + driver-error."""
    (raw / f'{label}.cmd.txt').write_text(cmd + '\n')
    argv = ['orb', '-m', 'a2hlab', 'bash', '-lc', cmd]
    (raw / f'{label}.argv.json').write_text(json.dumps({'argv': argv}, indent=2) + '\n')
    st = time.time(); rc = None; err = None
    try:
        with (raw / f'{label}.stdout').open('wb') as o, (raw / f'{label}.stderr').open('wb') as e:
            rc = subprocess.run(argv, stdout=o, stderr=e, timeout=TIMEOUT).returncode
    except subprocess.TimeoutExpired:
        rc = 124; err = f'local driver timeout after {TIMEOUT}s; does NOT prove the remote es2abc exited; not auto-retried'
    except OSError as ex:
        rc = 125; err = f'OSError launching orb: {ex!r}'
    for name in (f'{label}.stdout', f'{label}.stderr'):
        if not (raw / name).exists(): (raw / name).write_bytes(b'')
    (raw / f'{label}.rc').write_text(str(rc) + '\n')
    (raw / f'{label}.time.json').write_text(json.dumps({'start': st, 'end': time.time()}) + '\n')
    if err is not None:
        (raw / f'{label}.driver-error.txt').write_text(err + '\n')   # separate file, not the raw stderr
    receipt['commands'].append({'tag': label, 'rc': rc, **({'driver_error': err} if err else {})})
    return rc

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw', required=True, help='FRESH persistent raw dir (expanduser/resolve; must not exist)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--compiler', help='VM-visible es2abc path')
    g.add_argument('--compiler-receipt', help='historical receipt.json; reads compiler.path')
    a = ap.parse_args()
    raw = Path(a.raw).expanduser().resolve()         # (2) absolute before VM cd / --output
    try:
        raw.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(json.dumps({'status': 'RAW_DIR_EXISTS_REFUSED', 'raw': str(raw)}), file=sys.stderr); sys.exit(2)
    receipt = {'status': 'INCOMPLETE', 'compiler': {'sha256_expected': COMPILER_SHA}, 'commands': [], 'artifacts': {}}
    def save(): (raw / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    save()
    try:
        # (3) compiler-receipt read failure -> explicit FAILED, not a bare traceback
        if a.compiler:
            es = a.compiler
        else:
            try:
                es = json.loads(Path(a.compiler_receipt).expanduser().read_text())['compiler']['path']
            except (OSError, ValueError, KeyError) as ex:
                raise Stop('COMPILER_RECEIPT_UNREADABLE', f'{ex!r}')
        check(isinstance(es, str) and es, 'COMPILER_PATH_EMPTY', 'compiler path empty')
        check(sha(HERE / 'inputs/sources/baseline/EntryAbility.js') == BASELINE_SHA, 'BASELINE_SOURCE_SHA', 'baseline source SHA')
        check(sha(HERE / 'inputs/sources/candidate/EntryAbility.js') == CANDIDATE_SHA, 'CANDIDATE_SOURCE_SHA', 'candidate source SHA')
        rc = run_vm('compiler-sha', f'sha256sum {shlex.quote(es)}', raw, receipt); save()
        check(rc == 0, 'COMPILER_CHANNEL_REFUSED', f'compiler sha channel rc={rc}')
        got = (raw / 'compiler-sha.stdout').read_text().split()[:1]
        check(bool(got) and got[0] == COMPILER_SHA, 'COMPILER_SHA', 'compiler SHA drift/channel')
        receipt['compiler']['path'] = es; save()
        for label, phase in [('baseline-EntryAbility', 'baseline'),
                             ('candidate-EntryAbility-01', 'candidate'), ('candidate-EntryAbility-02', 'candidate')]:
            out = raw / f'{label}.abc'; cwd = HERE / 'inputs/sources' / phase
            cmd = f'cd {shlex.quote(str(cwd))} && timeout {TIMEOUT - 10} {shlex.quote(es)} --target-api-version=20 --output={shlex.quote(str(out))} EntryAbility.js'
            rc = run_vm(label, cmd, raw, receipt); save()
            check(rc == 0, 'COMPILE_FAILED', f'{label} rc={rc}')
            receipt['artifacts'][label] = {'sha256': sha(out), 'bytes': out.stat().st_size}; save()
            if label == 'baseline-EntryAbility':
                check(receipt['artifacts'][label]['sha256'] == HAP_MEMBER, 'BASELINE_ABC_MISMATCH', 'baseline ABC != HAP member')
        c1 = receipt['artifacts']['candidate-EntryAbility-01']['sha256']
        c2 = receipt['artifacts']['candidate-EntryAbility-02']['sha256']
        check(c1 == c2, 'CANDIDATE_NONDETERMINISTIC', 'candidate two runs differ')
        receipt['status'] = 'EXACT_BASELINE_AND_CANDIDATE_COMPILED'; save()
    except Stop as s:
        receipt['status'] = s.status; receipt['stop_reason'] = s.msg; save()
        print(json.dumps({'status': s.status, 'reason': s.msg}), file=sys.stderr); sys.exit(1)
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
