#!/usr/bin/env python3
"""T40 verifier: validate the exact-compile receipt; reject mismatch / missing log / failure.
No compile, device, sign, pack or install. check(root) validates <root>/results.json against the persistent
raw dir pinned in it. --negatives exercises the PRODUCTION check() and the production driver on temp copies
(mutating a baseline ABC, deleting a real log, forcing rc=7, drifting source under python -O, forcing an
OSError through the real run_vm, and a relative --raw with a bad compiler receipt); it does not re-compile.
"""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

CARD = Path(__file__).resolve().parent
HAP_MEMBER = 'bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9'
COMPILER_SHA = 'd20db2d40cef6ae897eeb736e6023625f507f89ba67b0d6cdcb602ca0a21fb0c'
LABELS = ['baseline-EntryAbility', 'candidate-EntryAbility-01', 'candidate-EntryAbility-02']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def req(c, m):
    if not c: raise ValueError(m)

def raw_dir(res):
    pins = res['raw_receipts_persistent']
    receipt_key = next(k for k in pins if k.endswith('/receipt.json'))
    return Path(receipt_key.replace('$HOME', str(Path.home()))).parent

def check(root=CARD):
    res = json.loads((root / 'results.json').read_text())
    req(res['status'] == 'EXACT_BASELINE_AND_CANDIDATE_COMPILED', 'status not compiled')
    req(res['compiler']['sha256'] == COMPILER_SHA, 'compiler SHA drift')
    raw = raw_dir(res)
    req(raw.is_dir(), 'raw dir missing')
    rec = json.loads((raw / 'receipt.json').read_text())
    req(rec['status'] == 'EXACT_BASELINE_AND_CANDIDATE_COMPILED', 'receipt not compiled')
    for k, v in res['raw_receipts_persistent'].items():
        f = Path(k.replace('$HOME', str(Path.home())))
        req(f.is_file(), f'missing raw receipt: {k}')
        req(sha(f) == v['sha256'] and f.stat().st_size == v['bytes'], f'raw receipt drift: {k}')
    for l in LABELS:
        req((raw / f'{l}.rc').read_text().strip() == '0', f'{l} rc != 0')
        for ext in ('argv.json', 'stdout', 'stderr', 'time.json', 'abc'):
            req((raw / f'{l}.{ext}').exists(), f'{l}.{ext} missing')
    b = sha(raw / 'baseline-EntryAbility.abc')
    req(b == HAP_MEMBER, 'baseline ABC does not reproduce the HAP member')
    req(res['results']['baseline_abc']['sha256'] == b == HAP_MEMBER, 'baseline results drift')
    c1 = sha(raw / 'candidate-EntryAbility-01.abc'); c2 = sha(raw / 'candidate-EntryAbility-02.abc')
    req(c1 == c2, 'candidate two runs differ')
    req(res['results']['candidate_abc_run1']['sha256'] == c1 and res['results']['candidate_abc_run2']['sha256'] == c2, 'candidate results drift')
    req(sha(root / 'inputs/sources/baseline/EntryAbility.js') == res['inputs']['baseline_EntryAbility.js']['sha256'], 'baseline source drift')
    req(sha(root / 'inputs/sources/candidate/EntryAbility.js') == res['inputs']['candidate_EntryAbility.js']['sha256'], 'candidate source drift')
    return {'status': 'PASS', 'baseline_abc': b, 'candidate_abc': c1, 'raw_receipts': len(res['raw_receipts_persistent']), 'all_rc_zero': True}

# ---- production-path negative suite (temp copies; no re-compile) ----
def _temp_root(td):
    """Copy card results+inputs and the pinned raw files into td; rewrite pins to the temp raw dir."""
    root = Path(td) / 'card'; (root / 'inputs/sources').mkdir(parents=True)
    shutil.copytree(CARD / 'inputs/sources', root / 'inputs/sources', dirs_exist_ok=True)
    res = json.loads((CARD / 'results.json').read_text())
    src_raw = raw_dir(res)
    dst_raw = Path(td) / 'raw'; dst_raw.mkdir()
    pins = {}
    for k, v in res['raw_receipts_persistent'].items():
        name = Path(k).name
        shutil.copyfile(src_raw / name, dst_raw / name)
        pins[str(dst_raw / name)] = v
    res['raw_receipts_persistent'] = pins
    (root / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
    return root, res, dst_raw

def _repin(root, res, raw, name):
    res['raw_receipts_persistent'][str(raw / name)]['sha256'] = sha(raw / name)
    res['raw_receipts_persistent'][str(raw / name)]['bytes'] = (raw / name).stat().st_size
    (root / 'results.json').write_text(json.dumps(res, indent=2) + '\n')

def negatives():
    out = check(CARD)                      # the frozen package really passes
    cases = []
    def expect_fail(name, mutate, needle):
        with tempfile.TemporaryDirectory() as td:
            root, res, raw = _temp_root(td)
            mutate(root, res, raw)
            try: check(root)
            except ValueError as e:
                req(needle in str(e), f'{name}: wrong reason {e!r}')
                cases.append({'case': name, 'production_rejected': True, 'reason': str(e)})
            else: raise ValueError(f'production check accepted: {name}')
    # 1) baseline ABC changed (repin so SHA passes, then the reproduce check must fire)
    def m_abc(root, res, raw):
        (raw / 'baseline-EntryAbility.abc').write_bytes(b'not the real abc'); _repin(root, res, raw, 'baseline-EntryAbility.abc')
        res['results']['baseline_abc']['sha256'] = sha(raw / 'baseline-EntryAbility.abc')
        (root / 'results.json').write_text(json.dumps(res, indent=2) + '\n')
    expect_fail('baseline ABC altered', m_abc, 'does not reproduce')
    # 2) a real log deleted
    expect_fail('raw log deleted', lambda root, res, raw: (raw / 'baseline-EntryAbility.stdout').unlink(), 'missing raw receipt')
    # 3) a real rc changed to 7
    def m_rc(root, res, raw):
        (raw / 'baseline-EntryAbility.rc').write_text('7\n'); _repin(root, res, raw, 'baseline-EntryAbility.rc')
    expect_fail('rc set to 7', m_rc, 'rc != 0')
    # 4) python -O + drifted source: production driver must still reject (explicit if, not assert) and not call the VM
    with tempfile.TemporaryDirectory() as td:
        drv = Path(td) / 'drv'; (drv / 'inputs/sources/baseline').mkdir(parents=True); (drv / 'inputs/sources/candidate').mkdir(parents=True)
        shutil.copyfile(CARD / 'compile_observer.py', drv / 'compile_observer.py')
        (drv / 'inputs/sources/baseline/EntryAbility.js').write_text('// drifted\n')
        (drv / 'inputs/sources/candidate/EntryAbility.js').write_text('// drifted\n')
        rr = Path(td) / 'rr'
        r = subprocess.run([sys.executable, '-O', '-B', str(drv / 'compile_observer.py'), '--raw', str(rr), '--compiler', '/nonexistent/es2abc'], capture_output=True, text=True)
        req(r.returncode != 0, 'peer1: python -O did not reject drifted source')
        req('BASELINE_SOURCE_SHA' in r.stderr, f'peer1: wrong stop reason {r.stderr!r}')
        req(not (rr / 'compiler-sha.stdout').exists(), 'peer1: VM was called despite source drift')
        cases.append({'case': 'python -O rejects drifted source before VM', 'production_rejected': True})
    # 5) OSError through the real run_vm -> rc125 + time + separate driver-error file
    sys.path.insert(0, str(CARD))
    import compile_observer as co
    orig = co.subprocess.run
    co.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError('mock launch failure'))
    try:
        with tempfile.TemporaryDirectory() as td:
            rr = Path(td); rec = {'commands': []}
            rc = co.run_vm('probe', 'true', rr, rec)
            req(rc == 125, f'OSError rc {rc}')
            req((rr / 'probe.rc').read_text().strip() == '125', 'OSError rc file')
            req((rr / 'probe.time.json').exists(), 'OSError time file')
            req((rr / 'probe.driver-error.txt').exists() and 'OSError' in (rr / 'probe.driver-error.txt').read_text(), 'OSError driver-error file')
            req(rec['commands'][-1].get('driver_error'), 'OSError not in receipt command')
            cases.append({'case': 'OSError -> rc125 + time + driver-error', 'production_rejected': True})
    finally:
        co.subprocess.run = orig
    # 6) relative --raw absolutized from cwd; bad compiler receipt -> explicit COMPILER_RECEIPT_UNREADABLE
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / 'bad.json'; bad.write_text('{"no":"compiler"}')
        r = subprocess.run([sys.executable, '-B', str(CARD / 'compile_observer.py'), '--raw', 'relraw', '--compiler-receipt', str(bad)], capture_output=True, text=True, cwd=td)
        req(r.returncode != 0, 'peer3: bad receipt not rejected')
        req('COMPILER_RECEIPT_UNREADABLE' in r.stderr, f'peer3: wrong reason {r.stderr!r}')
        req((Path(td) / 'relraw').is_dir(), 'peer2: relative --raw not absolutized to cwd')
        cases.append({'case': 'relative --raw absolutized + bad receipt handled', 'production_rejected': True})
    out['negative_cases'] = cases
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=CARD)
    ap.add_argument('--negatives', action='store_true')
    a = ap.parse_args()
    print(json.dumps(negatives() if a.negatives else check(a.root), indent=2))

if __name__ == '__main__':
    main()
